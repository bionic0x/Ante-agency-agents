#!/usr/bin/env bash
# Reproduce the release gate locally. Requires Python 3.11+ and PyYAML.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import yaml, tomllib' || {
  echo 'Use Python 3.11+ and: python3 -m pip install -r scripts/requirements-validation.txt' >&2
  exit 1
}
for script in scripts/*.sh; do bash -n "$script"; done
python3 scripts/test-changed-agent-files.py
python3 scripts/test-agent-privileges.py
python3 scripts/test-agent-capabilities.py
python3 scripts/check-agent-privileges.py
python3 scripts/test-openclaw-import-provenance.py
python3 scripts/test-kimi-adapter.py
for check in lint-agents check-divisions check-tools check-runbooks check-hermes-config-rewrite; do
  bash "scripts/$check.sh"
done
python3 scripts/build-catalog.py --check
python3 scripts/test-runbook-contracts.py
python3 scripts/check-strategy-vocabulary.py
python3 scripts/test-nexus-instance.py
python3 scripts/test-nexus-evaluation.py
python3 scripts/nexus-instance.py validate examples/nexus/strategic-decision.instance.json >/dev/null
python3 scripts/check-htp-gate0.py
python3 scripts/test-htp-gate0.py
python3 scripts/check-hermes-plugin.py
python3 scripts/test-hermes-plugin.py
python3 scripts/test-incremental-conversion.py
python3 scripts/test-host-acceptance.py
bash scripts/test-convert-frontmatter.sh
bash scripts/test-agent-selection.sh
python3 scripts/test-install-functional.py
bash scripts/test-install.sh
bash scripts/test-convert-outputs.sh "$@"
echo 'PASSED: complete release gate'
