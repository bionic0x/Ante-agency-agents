#!/usr/bin/env bash
# Rebuild the synthetic laboratory-consortium case end to end:
# frame -> ... -> decide, then record, reconcile and calibrate.
# Every output is deterministic; `git diff --exit-code` after running proves it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
ANTE=(python3 "$ROOT/scripts/ante")
IN="$HERE/input"
OUT="${1:-$HERE/artifacts}"
LEARN="${2:-$HERE/learning}"
# The doctrine tables this chain uses are the D-004 proposal until strategy/contracts.json carries them.
CONTRACTS="$ROOT/foundation/proposals/contracts-v2.json"

rm -rf "$OUT" "$LEARN"
mkdir -p "$OUT" "$LEARN"

step() {
  local cmd="$1"; shift
  local args=("$IN/$cmd.json" --out "$OUT")
  for parent in "$@"; do args+=(--from "$OUT/$parent.json"); done
  case "$cmd" in cohere|pathology|decide) args+=(--contracts "$CONTRACTS") ;; esac
  "${ANTE[@]}" "$cmd" "${args[@]}" >/dev/null
  echo "  $cmd"
}

echo "strategy chain:"
step frame
step map frame
step cause frame map
step focus map
step options cause frame map
step react options map
step street frame map
step ach frame
step watch options
step close frame
step cohere frame cause map street
step pathology frame map
step nodal frame map cause focus options react street ach watch close cohere pathology
step decide frame cohere pathology close cause nodal

echo "run check:"
"${ANTE[@]}" run strategic-decision --artifacts "$OUT" --contracts "$CONTRACTS" > "$LEARN/run-check.json"
echo "  complete: $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["complete"])' "$LEARN/run-check.json")"

echo "learning (synthetic: excluded from calibration by design):"
LEDGER="$LEARN/ledger.jsonl"
"${ANTE[@]}" learn record "$OUT/decide.json" --ledger "$LEDGER" --runbook strategic-decision \
  --agent specialized-strategic-assurance-lead --synthetic --at 2026-10-28T15:00:00Z >/dev/null
DECISION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["artifact_sha256"])' "$OUT/decide.json")"
sed "s/@DECISION@/$DECISION/" "$HERE/observations.json" > "$LEARN/observations.json"
"${ANTE[@]}" learn reconcile "$LEARN/observations.json" --ledger "$LEDGER" --at 2026-12-15T09:00:00Z >/dev/null
"${ANTE[@]}" learn calibrate --ledger "$LEDGER" --at 2026-12-15T09:00:00Z --min-sample 30 --out "$LEARN/calibration.json" >/dev/null
"${ANTE[@]}" learn verify --ledger "$LEDGER" >/dev/null
echo "  ledger: $(wc -l < "$LEDGER" | tr -d ' ') entries, chain intact"
echo "  calibration: $(python3 -c 'import json,sys; g=json.load(open(sys.argv[1]))["groups"][0]; print(g["result"], g["n"])' "$LEARN/calibration.json")"
