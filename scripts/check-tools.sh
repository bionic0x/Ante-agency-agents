#!/usr/bin/env bash
# Validate tools.json schema plus explicit installer/detector/renderer coverage.
# Runtime tool lists are read from tools.json through scripts/registry.py; this
# check therefore validates implementation coverage instead of comparing copied
# arrays that should not exist.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR python3 is required for tool registry validation" >&2
  exit 1
}

python3 - <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

root = Path.cwd()
tools_path = root / "tools.json"
install_path = root / "scripts" / "install.sh"
engine_path = root / "scripts" / "convert-engine.sh"
wrapper_path = root / "scripts" / "convert.sh"
registry_path = root / "scripts" / "registry.py"
errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def function_body(text: str, name: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(name)}\(\) \{{\n(.*?)^\}}", text)
    if not match:
        fail(f"missing shell function {name}()")
        return ""
    return match.group(1)


def case_labels(body: str) -> set[str]:
    return set(re.findall(r"(?m)^\s{4,}([a-z0-9][a-z0-9-]*)\)", body))


try:
    document = json.loads(tools_path.read_text(encoding="utf-8"))
    tools = document["tools"]
except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
    print(f"ERROR tools.json: {exc}", file=sys.stderr)
    raise SystemExit(1)

if not isinstance(tools, dict) or not tools:
    print("ERROR tools.json: 'tools' must be a non-empty object", file=sys.stderr)
    raise SystemExit(1)

required = ("id", "label", "kebab", "format", "installKind", "dest", "order")
valid_kinds = {"per-agent", "roster", "plugin"}
orders: dict[int, str] = {}
for key, spec in tools.items():
    if not isinstance(spec, dict):
        fail(f"tool '{key}' must be an object")
        continue
    for field in required:
        if field not in spec:
            fail(f"tool '{key}' is missing '{field}'")
    if spec.get("kebab") != key:
        fail(f"tool '{key}' has kebab={spec.get('kebab')!r}; expected registry key")
    if not isinstance(spec.get("id"), str) or not spec.get("id"):
        fail(f"tool '{key}' must have a non-empty string id")
    if not isinstance(spec.get("label"), str) or not spec.get("label"):
        fail(f"tool '{key}' must have a non-empty string label")
    if not isinstance(spec.get("format"), str) or not spec.get("format"):
        fail(f"tool '{key}' must have a non-empty string format")
    if spec.get("installKind") not in valid_kinds:
        fail(f"tool '{key}' has invalid installKind={spec.get('installKind')!r}")
    if not isinstance(spec.get("dest"), dict):
        fail(f"tool '{key}' must have an object dest")
    order = spec.get("order")
    if not isinstance(order, int) or isinstance(order, bool) or order < 1:
        fail(f"tool '{key}' must have a positive integer order")
    elif order in orders:
        fail(f"duplicate order {order}: '{orders[order]}' and '{key}'")
    else:
        orders[order] = key

all_tools = set(tools)
converted = {key for key, spec in tools.items() if spec.get("format") != "identity"}
identity = all_tools - converted

install_text = install_path.read_text(encoding="utf-8")
engine_text = engine_path.read_text(encoding="utf-8")
wrapper_text = wrapper_path.read_text(encoding="utf-8")
registry_text = registry_path.read_text(encoding="utf-8")

install_coverage = case_labels(function_body(install_text, "install_tool"))
detect_coverage = case_labels(function_body(install_text, "is_detected"))
run_conversions_body = function_body(engine_text, "run_conversions")
render_coverage = case_labels(run_conversions_body)
if re.search(r'\btool\b.*==.*["\']hermes["\']', run_conversions_body):
    render_coverage.add("hermes")

for label, actual, expected in (
    ("install_tool dispatch", install_coverage, all_tools),
    ("is_detected dispatch", detect_coverage, all_tools),
    ("converter dispatch", render_coverage, converted),
):
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        fail(f"{label} missing registered tool(s): {' '.join(missing)}")
    if extra:
        fail(f"{label} contains unregistered tool(s): {' '.join(extra)}")

# Public entrypoints must consume the registry, not carry another supported-tool
# array. Check the structural call sites rather than whitespace-sensitive text.
if re.search(r"(?m)^ALL_TOOLS=\([^\n]*[a-z0-9-]", install_text):
    fail("scripts/install.sh still defines a populated hard-coded ALL_TOOLS array")
if re.search(r"(?m)^valid_tools=\(", wrapper_text):
    fail("scripts/convert.sh still defines a hard-coded valid_tools array")

registry_keys_body = function_body(install_text, "registry_keys")
if "registry.py" not in registry_keys_body:
    fail("scripts/install.sh registry_keys() does not invoke scripts/registry.py")
if not re.search(r"(?m)\bregistry_keys[ \t]+tools\b", install_text):
    fail("scripts/install.sh does not populate tools from registry_keys tools")
if not re.search(r"(?m)\bregistry_keys[ \t]+divisions\b", install_text):
    fail("scripts/install.sh does not populate divisions from registry_keys divisions")
if "REGISTRY=" not in wrapper_text or not re.search(
    r'python3\s+"\$REGISTRY"\s+tools\s+"\$REPO_ROOT/tools\.json"\s+--converted',
    wrapper_text,
):
    fail("scripts/convert.sh does not derive converted tools from the canonical registry")

# Registry helper itself must support the semantics consumers rely on.
for token in ("--converted", "--install-kind", "tool-field", "order"):
    if token not in registry_text:
        fail(f"scripts/registry.py is missing required tool-registry capability: {token}")

if errors:
    for error in errors:
        print(f"ERROR {error}")
    print(f"\nFAILED: {len(errors)} tool registry/coverage error(s). tools.json is canonical.")
    raise SystemExit(1)

ordered = [key for key, _spec in sorted(tools.items(), key=lambda item: item[1]["order"])]
print(
    f"PASSED: {len(all_tools)} tools validated from tools.json; "
    f"{len(converted)} converted, {len(identity)} source/identity; "
    "installer, detection and renderer coverage complete."
)
print("Canonical order: " + " ".join(ordered))
PY
