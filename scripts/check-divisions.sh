#!/usr/bin/env bash
#
# check-divisions.sh — enforce divisions.json as the source of truth.
#
# This script fails if any of the following disagree with it:
#   1. The actual top-level agent directories on disk
#   2. The runtime registry reader used by convert.sh and lint-agents.sh
#   3. Unconditional PR coverage in .github/workflows/lint-agents.yml
#   4. Every divisions.json entry has label, icon, and color
#
# convert.sh and lint-agents.sh consume divisions.json through registry.py; they
# no longer carry hand-maintained AGENT_DIRS copies.
#
# Usage: ./scripts/check-divisions.sh

set -euo pipefail

cd "$(dirname "$0")/.."

JSON="divisions.json"

# Top-level directories that are NOT divisions. Everything else at the repo
# root that is a directory is treated as a division (so a new division dir is
# caught even if nobody remembered to register it).
NON_DIVISION_DIRS=(examples scripts integrations strategy)

errors=0
fail() { echo "ERROR $*"; errors=$((errors + 1)); }

# --- sorted, newline-delimited helpers -------------------------------------

# Canonical set: object-valued keys inside the "divisions" object. Scoping to
# lines after the `"divisions": {` opener excludes the wrapper and _note.
canonical() {
  awk '/"divisions"[[:space:]]*:[[:space:]]*\{/{f=1; next} f' "$JSON" \
    | grep -oE '"[a-z0-9-]+"[[:space:]]*:[[:space:]]*\{' \
    | sed -E 's/"([a-z0-9-]+)".*/\1/' | sort -u
}

# Actual division directories: top-level dirs that contain at least one
# git-tracked file, minus the excludes and anything dot-prefixed.
actual_dirs() {
  local base
  git ls-files | awk -F/ 'NF>1{print $1}' | sort -u | while IFS= read -r base; do
    [[ "$base" == .* ]] && continue
    case " ${NON_DIVISION_DIRS[*]} " in *" $base "*) continue ;; esac
    echo "$base"
  done
}

# Compare canonical vs a candidate set; report both directions.
compare() {
  local label="$1" candidate="$2" canon
  canon="$(canonical)"
  local missing extra
  missing="$(comm -23 <(echo "$canon") <(echo "$candidate"))"
  extra="$(comm -13 <(echo "$canon") <(echo "$candidate"))"
  if [[ -n "$missing" ]]; then
    fail "$label is missing division(s) present in $JSON: $(echo "$missing" | tr '\n' ' ')"
  fi
  if [[ -n "$extra" ]]; then
    fail "$label has division(s) not in $JSON: $(echo "$extra" | tr '\n' ' ')"
  fi
}

# --- checks ----------------------------------------------------------------

[[ -f "$JSON" ]] || { echo "ERROR $JSON not found at repo root"; exit 1; }

compare "the agent directories on disk" "$(actual_dirs)"

runtime="$(python3 scripts/registry.py divisions "$JSON" 2>/dev/null | sort -u)" || true
if [[ -z "$runtime" ]]; then
  fail "scripts/registry.py could not read the canonical division registry"
else
  compare "scripts/registry.py runtime discovery" "$runtime"
fi

# A required check must run on every PR; path/branch filters can leave it pending.
WF=".github/workflows/lint-agents.yml"
if ! python3 - "$WF" <<'PYEOF'
import sys
import yaml
with open(sys.argv[1], encoding="utf-8") as source:
    workflow = yaml.safe_load(source)
triggers = workflow.get("on", workflow.get(True, {}))
if not isinstance(triggers, dict) or "pull_request" not in triggers:
    sys.exit("ERROR lint workflow must run on pull_request")
pr = triggers["pull_request"]
if pr is not None and pr != {}:
    sys.exit("ERROR required lint check must run on every PR without event filters")
PYEOF
then
  fail "$WF does not provide unconditional PR lint coverage (requires PyYAML)"
fi

# Every entry must have label, icon, and color.
while IFS= read -r div; do
  block="$(awk -v d="\"$div\"" '$0 ~ d"[[:space:]]*:[[:space:]]*\\{" {print; found=1; next} found && /\}/ {print; exit} found {print}' "$JSON")"
  for field in label icon color; do
    grep -qE "\"$field\"[[:space:]]*:" <<<"$block" \
      || fail "division '$div' in $JSON is missing \"$field\""
  done
done < <(canonical)

# Every division must contain at least one agent file: a .md whose first line is
# '---' frontmatter. This keeps docs/playbook directories out of the registry.
has_agent_file() {
  local f first
  while IFS= read -r f; do
    first="$(head -1 "$f" | tr -d '\r')"
    [[ "$first" == "---" ]] && return 0
  done < <(find "$1" -name '*.md' -type f 2>/dev/null)
  return 1
}
while IFS= read -r div; do
  if [[ ! -d "$div" ]]; then
    fail "division '$div' has no directory on disk"
  elif ! has_agent_file "$div"; then
    fail "division '$div' has no agent files (.md with '---' frontmatter) — not a real division"
  fi
done < <(canonical)

# --- result ----------------------------------------------------------------

count="$(canonical | wc -l | tr -d ' ')"
if [[ $errors -gt 0 ]]; then
  echo ""
  echo "FAILED: $errors divisions consistency error(s). $JSON is the source of truth."
  exit 1
fi
echo "PASSED: $count divisions consistent across $JSON, runtime discovery, directories, and CI."
