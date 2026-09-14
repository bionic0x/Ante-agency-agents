#!/usr/bin/env bash
# Thin conversion orchestrator. The renderer from PR #12 is preserved byte-for-
# byte in convert-engine.sh; only canonical single-tool refreshes are incremental.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$SCRIPT_DIR/convert-engine.sh"
STATE="$SCRIPT_DIR/integration-state.py"

# Explicit until the registry-driven dispatch work lands; check-tools.sh keeps
# enforcing this converter subset against tools.json.
valid_tools=("antigravity" "gemini-cli" "opencode" "cursor" "aider" "windsurf" "openclaw" "qwen" "zcode" "kimi" "codex" "osaurus" "hermes" "vibe" "all")

# The installer refresh path is exactly: convert.sh --tool <tool>. Intercept only
# that shape. Every other invocation is delegated untouched so help, errors,
# --out benchmarks, full/all builds and parallel behavior remain historical.
if [[ $# -eq 2 && "$1" == "--tool" && "$2" != "all" ]]; then
  tool="$2"
  valid=false
  for candidate in "${valid_tools[@]}"; do
    if [[ "$candidate" == "$tool" ]]; then valid=true; break; fi
  done
  if $valid; then
    command -v python3 >/dev/null 2>&1 || {
      echo "ERROR: python3 is required for incremental conversion state" >&2
      exit 1
    }
    exec python3 "$STATE" sync "$tool"
  fi
fi

exec bash "$ENGINE" "$@"
