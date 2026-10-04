#!/usr/bin/env bash
# Thin conversion orchestrator. The renderer remains in convert-engine.sh;
# canonical single-tool refreshes use granular integration state.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENGINE="$SCRIPT_DIR/convert-engine.sh"
STATE="$SCRIPT_DIR/integration-state.py"
REGISTRY="$SCRIPT_DIR/registry.py"

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 is required for the tool registry" >&2
  exit 1
}

CONVERTED_TOOLS=()
while IFS= read -r tool; do
  [[ -n "$tool" ]] && CONVERTED_TOOLS+=("$tool")
done < <(python3 "$REGISTRY" tools "$REPO_ROOT/tools.json" --converted)
[[ ${#CONVERTED_TOOLS[@]} -gt 0 ]] || {
  echo "ERROR: no converted tools found in tools.json" >&2
  exit 1
}

# The installer refresh path is exactly: convert.sh --tool <tool>. Intercept only
# that shape. Every other invocation is delegated untouched so help, errors,
# --out benchmarks, full/all builds and parallel behavior stay in the engine.
if [[ $# -eq 2 && "$1" == "--tool" && "$2" != "all" ]]; then
  requested="$2"
  valid=false
  for candidate in "${CONVERTED_TOOLS[@]}"; do
    if [[ "$candidate" == "$requested" ]]; then valid=true; break; fi
  done
  if $valid; then
    exec python3 "$STATE" sync "$requested"
  fi
fi

exec bash "$ENGINE" "$@"
