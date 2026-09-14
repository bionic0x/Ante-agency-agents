#!/usr/bin/env bash
# Thin conversion orchestrator. Full rendering remains in convert-engine.sh;
# canonical single-tool runs use integration-state.py for granular freshness.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$SCRIPT_DIR/convert-engine.sh"
STATE="$SCRIPT_DIR/integration-state.py"

# Kept explicit until the registry-driven tool dispatch work lands; check-tools.sh
# verifies this subset against tools.json exactly as it did before PR #13.
valid_tools=("antigravity" "gemini-cli" "opencode" "cursor" "aider" "windsurf" "openclaw" "qwen" "zcode" "kimi" "codex" "osaurus" "hermes" "vibe" "all")

tool="all"
has_out=false
parallel=false
help=false
args=("$@")
i=0
while (( i < ${#args[@]} )); do
  case "${args[$i]}" in
    --tool)
      i=$(( i + 1 ))
      (( i < ${#args[@]} )) || { echo "ERROR: --tool requires a value" >&2; exit 1; }
      tool="${args[$i]}"
      ;;
    --out)
      has_out=true
      i=$(( i + 1 ))
      (( i < ${#args[@]} )) || { echo "ERROR: --out requires a value" >&2; exit 1; }
      ;;
    --parallel) parallel=true ;;
    --help|-h) help=true ;;
  esac
  i=$(( i + 1 ))
done

valid=false
for candidate in "${valid_tools[@]}"; do
  if [[ "$candidate" == "$tool" ]]; then valid=true; break; fi
done

# Let the historical engine preserve its exact error/help behavior for unknown
# tools, full/all conversions, explicit output directories and parallel builds.
if ! $valid || $help || [[ "$tool" == "all" ]] || $has_out || $parallel; then
  exec bash "$ENGINE" "$@"
fi

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 is required for incremental conversion state" >&2
  exit 1
}
exec python3 "$STATE" sync "$tool"
