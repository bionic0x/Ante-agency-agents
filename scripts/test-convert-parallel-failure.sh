#!/usr/bin/env bash
# A failed parallel converter must expose its buffered error and clean up.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURE="$(mktemp -d "${TMPDIR:-/tmp}/agency-convert-failure.XXXXXX")"
trap 'rm -rf "$FIXTURE"' EXIT

# A one-division roster with no agents makes this fast. Hermes intentionally
# lacks its builder.
mkdir -p "$FIXTURE/repo/scripts" "$FIXTURE/repo/engineering"
printf '{"divisions": {"engineering": {}}}\n' > "$FIXTURE/repo/divisions.json"
cp "$SCRIPT_DIR/convert.sh" "$SCRIPT_DIR/lib.sh" "$SCRIPT_DIR/registry.py" "$SCRIPT_DIR/convert-engine.sh" "$SCRIPT_DIR/integration-state.py" "$FIXTURE/repo/scripts/"
cp "$SCRIPT_DIR/../tools.json" "$FIXTURE/repo/"  # runtime registries (scripts/registry.py)

status=0
TMPDIR="$FIXTURE" "$FIXTURE/repo/scripts/convert.sh" \
  --tool all --parallel --jobs 2 --out "$FIXTURE/output" \
  > "$FIXTURE/run.log" 2>&1 || status=$?

[[ "$status" -ne 0 ]] || { echo "parallel conversion unexpectedly succeeded" >&2; exit 1; }
grep -Fq 'build-hermes-plugin.py' "$FIXTURE/run.log" || {
  echo "parallel converter error was hidden in its buffered output" >&2
  exit 1
}
if find "$FIXTURE" -mindepth 1 -maxdepth 1 -type d -name 'agency-convert-parallel.*' | grep -q .; then
  echo "parallel conversion left its buffered output directory behind" >&2
  exit 1
fi

# The same empty-roster fixture succeeds once its one missing converter exists.
printf 'import sys\n' > "$FIXTURE/repo/scripts/build-hermes-plugin.py"
TMPDIR="$FIXTURE" "$FIXTURE/repo/scripts/convert.sh" \
  --tool all --parallel --jobs 2 --out "$FIXTURE/output" \
  > "$FIXTURE/success.log" 2>&1
grep -Fq 'Done. 15 tools' "$FIXTURE/success.log"

echo "PASS: parallel converter reports failure and cleans buffered logs"
