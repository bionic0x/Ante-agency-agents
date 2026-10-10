"""Worst-case input tokens for images and PDFs (audit follow-up to T4).

Request bytes bound the tokens of the text they encode, but not of media:

* An image is billed in visual tokens, ceil(width/28) * ceil(height/28), downscaled to at
  most `max_image_tokens` (4,784 on high-resolution models). A tiny, highly compressible
  PNG can declare a large canvas, so its bytes say nothing about its cost.
* A PDF page is billed as extracted text plus an image of the page. Page streams are
  compressed, so neither the page count nor the text volume can be bounded from the
  bytes without a full PDF parser. The only sound bound is the model's input limit.

`input_bound` returns an upper bound for the request's input tokens. It never parses
more than an image's fixed-size header; anything it cannot read is charged the cap.
"""
from __future__ import annotations

import base64
import binascii
import math
import struct

PATCH = 28
DEFAULT_MAX_IMAGE_TOKENS = 4784       # high-resolution tier (Claude 4.7 and later)
DEFAULT_MAX_INPUT_TOKENS = 1_000_000  # largest context window offered; lower it per deployment
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_DEPTH = 32


def _png_tokens(data: str, cap: int) -> int:
    """Visual tokens for a PNG from its IHDR (always the first chunk); `cap` if unreadable.
    Downscaling only ever lowers the count, so the native size is an upper bound."""
    try:
        head = base64.b64decode(data[:44], validate=False)  # 44 chars -> 33 bytes: signature + IHDR
    except (binascii.Error, ValueError):
        return cap
    if len(head) < 24 or not head.startswith(PNG_SIGNATURE) or head[12:16] != b"IHDR":
        return cap
    width, height = struct.unpack(">II", head[16:24])
    if width < 1 or height < 1:
        return cap
    return min(cap, math.ceil(width / PATCH) * math.ceil(height / PATCH))


class _Tally:
    def __init__(self, max_image_tokens: int):
        self.cap = max_image_tokens
        self.image_tokens = 0
        self.images = 0
        self.pdf = False

    def blocks(self, blocks, depth: int = 1) -> None:
        if depth > MAX_DEPTH or not isinstance(blocks, list):
            return  # policy.check_request refuses these shapes before metering
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            source = block.get("source") if isinstance(block.get("source"), dict) else {}
            if kind == "image":
                self.images += 1
                data = source.get("data")
                self.image_tokens += _png_tokens(data, self.cap) if isinstance(data, str) else self.cap
            elif kind == "document":
                if source.get("type") == "base64":
                    self.pdf = True  # base64 documents are PDFs; any other media type is charged the same way
                elif source.get("type") == "content":
                    self.blocks(source.get("content"), depth + 1)
            elif kind in ("tool_result", "search_result"):
                self.blocks(block.get("content"), depth + 1)


def input_bound(request: dict, body_bytes: int, margin: int, *, max_image_tokens: int = DEFAULT_MAX_IMAGE_TOKENS,
                max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS) -> tuple[int, bool]:
    """(upper bound on input tokens, whether media raised it above the text bound).

    Text: at most one token per request byte, plus `margin`. Each image adds its visual
    tokens on top (its base64 bytes are already counted, which only over-estimates).
    Any PDF, or any total above the model's input limit, is bounded by that limit."""
    tally = _Tally(max_image_tokens)
    for message in request.get("messages") or []:
        if isinstance(message, dict):
            tally.blocks(message.get("content"))
    tally.blocks(request.get("system"))
    text_bound = body_bytes + margin
    if tally.pdf:
        return max_input_tokens, True
    bound = min(max_input_tokens, text_bound + tally.image_tokens)
    return bound, tally.images > 0
