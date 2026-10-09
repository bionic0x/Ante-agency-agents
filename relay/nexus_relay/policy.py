"""Model request policy: what the container may ask the model provider to do.

The container has no network, but the Messages API can act on the network itself:
server-side tools (web search, web fetch, code execution), remote MCP servers
(`mcp_servers`), URL and Files-API content sources and code-execution containers all
make the provider reach out or read account data on the agent's behalf. Any of them
would turn the model API into an egress channel and incur charges the meter cannot see.

So the proxy forwards only what it understands: an allowlist of request fields, client
tools (executed inside the container), content blocks with inline sources, and betas
outside the capability families that enable provider-side actions. Everything else is
refused, never stripped, so the agent gets a clear error instead of silently different
behaviour.
"""
from __future__ import annotations

from typing import Iterable

# Fields that change neither where the provider reaches nor the price per token. Pricing
# modifiers (`service_tier`, `speed`, `inference_geo`) stay out: the meter prices every token
# at the configured rate, so a request must not be able to raise it.
MESSAGES_FIELDS = frozenset({
    "model", "messages", "max_tokens", "system", "stop_sequences", "stream", "temperature",
    "top_p", "top_k", "tools", "tool_choice", "metadata", "thinking", "context_management", "output_config",
})
COUNT_TOKENS_FIELDS = frozenset({"model", "messages", "system", "tools", "tool_choice", "thinking",
                                 "context_management", "output_config"})

# Tools whose `type` names a client tool: the provider only returns a tool_use block and the
# agent executes it locally, inside the container.
CLIENT_TOOL_PREFIXES = ("custom", "bash_", "text_editor_", "computer_", "memory_")

CONTENT_BLOCK_TYPES = frozenset({
    "text", "image", "document", "tool_use", "tool_result", "thinking", "redacted_thinking", "search_result",
})
INLINE_SOURCE_TYPES = frozenset({"base64", "text", "content"})

# Beta families that enable provider-side actions, account data access or a different price.
DENIED_BETA_PREFIXES = ("mcp-client", "files-api", "code-execution", "web-fetch", "web-search", "skills",
                        "container", "agent-", "managed-agents", "fast-mode")

MAX_DEPTH = 32


class PolicyViolation(ValueError):
    pass


def _check_source(source, where: str) -> None:
    if not isinstance(source, dict):
        raise PolicyViolation(f"{where}: source must be an object")
    kind = source.get("type")
    if kind not in INLINE_SOURCE_TYPES:
        raise PolicyViolation(f"{where}: source type {kind!r} is not allowed (only inline content; "
                              "URL and file sources make the provider fetch data)")
    if kind == "content":
        _check_blocks(source.get("content"), f"{where}.content", 1)


def _check_blocks(blocks, where: str, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise PolicyViolation(f"{where}: content nested too deeply")
    if isinstance(blocks, str) or blocks is None:
        return
    if not isinstance(blocks, list):
        raise PolicyViolation(f"{where}: content must be a string or a list of blocks")
    for i, block in enumerate(blocks):
        here = f"{where}[{i}]"
        if not isinstance(block, dict):
            raise PolicyViolation(f"{here}: block must be an object")
        kind = block.get("type")
        if kind not in CONTENT_BLOCK_TYPES:
            raise PolicyViolation(f"{here}: block type {kind!r} is not allowed")
        if kind in ("image", "document"):
            _check_source(block.get("source"), f"{here}.source")
        if kind == "tool_result":
            _check_blocks(block.get("content"), f"{here}.content", depth + 1)
        if kind == "search_result":
            _check_blocks(block.get("content"), f"{here}.content", depth + 1)


def _check_tools(tools) -> None:
    if tools is None:
        return
    if not isinstance(tools, list):
        raise PolicyViolation("tools must be a list")
    for i, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise PolicyViolation(f"tools[{i}] must be an object")
        kind = tool.get("type", "custom")
        if not isinstance(kind, str) or not kind.startswith(CLIENT_TOOL_PREFIXES):
            raise PolicyViolation(f"tools[{i}]: tool type {kind!r} runs on the provider's side and is not allowed")


def check_request(path: str, request: dict, extra_fields: Iterable[str] = ()) -> None:
    """Raise PolicyViolation unless every part of the request is understood and local-only."""
    allowed = (MESSAGES_FIELDS if path == "/v1/messages" else COUNT_TOKENS_FIELDS) | frozenset(extra_fields)
    unknown = sorted(set(request) - allowed)
    if unknown:
        raise PolicyViolation(f"request fields not allowed by relay policy: {', '.join(unknown)}")
    messages = request.get("messages", [])  # absent: the provider rejects it; nothing to forward on
    if not isinstance(messages, list):
        raise PolicyViolation("messages must be a list")
    for i, message in enumerate(messages):
        if not isinstance(message, dict):
            raise PolicyViolation(f"messages[{i}] must be an object")
        _check_blocks(message.get("content"), f"messages[{i}].content", 1)
    _check_blocks(request.get("system"), "system", 1)
    _check_tools(request.get("tools"))


def check_betas(header: str | None) -> None:
    """Raise PolicyViolation for any `anthropic-beta` value in a denied family."""
    if not header:
        return
    for beta in (b.strip().lower() for b in header.split(",")):
        if beta and beta.startswith(DENIED_BETA_PREFIXES):
            raise PolicyViolation(f"anthropic-beta {beta!r} enables provider-side actions and is not allowed")
