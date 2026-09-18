#!/usr/bin/env bash
#
# check-runbooks.sh — enforce that strategy/runbooks.json stays in sync with the
# real agent roster AND satisfies the NEXUS strategic contract.
#
# The Agency Agents app reads strategy/runbooks.json to turn a scenario into a
# one-click team deploy. A deployable scenario must not be only a list of agents:
# it must state the governing object, explicit non-object, accountable decision
# owner, mandatory artifacts, termination criteria, and a separate Strategic
# Assurance Lead.
#
# This check fails when:
#   1. runbooks.json is invalid JSON or structurally incomplete
#   2. a roster slug does not match a real agent file
#   3. a scenario document or required artifact path does not exist
#   4. a runbook slug is duplicated
#   5. strategic metadata is missing or empty
#   6. the Strategic Assurance Lead is absent from a runbook roster
#   7. termination_criteria is a placeholder rather than a criterion
#   8. a runbook lacks a structured termination_contract answering all four
#      closure questions, or the contract is malformed
#
# On termination: a non-empty string is not a termination criterion. The source
# doctrine (Marco Teorico General de la Estrategia, XII.9) holds that before
# closing, the authority must be able to say what was achieved, what remains
# outstanding, who answers for it, and what happens on breach. Every runbook
# therefore carries those four answers as a structured `termination_contract`.
# `conservation_resources` and `revision_conditions` are supported extensions.
#
# Uses python3; no jq required.

set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 is required for the runbooks check." >&2
  exit 2
}

python3 - <<'PYEOF'
import json
import os
import runpy
from pathlib import Path
import sys

JSON_PATH = "strategy/runbooks.json"
ASSURANCE_SLUG = "specialized-strategic-assurance-lead"
NON_DIVISION = {"integrations", "examples", "strategy", "scripts", "evidence", ".github"}
errors = []

if not os.path.isfile(JSON_PATH):
    print(f"ERROR {JSON_PATH} not found")
    sys.exit(1)

try:
    with open(JSON_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
except json.JSONDecodeError as exc:
    print(f"ERROR {JSON_PATH} is not valid JSON: {exc}")
    sys.exit(1)

if not isinstance(data, dict):
    print("ERROR runbook registry must be an object")
    sys.exit(1)

schema_version = str(data.get("schema_version", ""))
if not schema_version.startswith("2."):
    errors.append(
        f"schema_version must be 2.x for the strategic runbook contract; got {schema_version!r}"
    )

# Resolve against the same canonical catalog used by the installer.
try:
    catalog = runpy.run_path("scripts/build-catalog.py")
    _, agents, _ = catalog["collect"]()
    real = {a["slug"] for a in agents}
    vocabulary = json.loads(Path("strategy/contracts.json").read_text(encoding="utf-8"))
except (OSError, ValueError, KeyError, TypeError) as exc:
    print(f"ERROR cannot load canonical catalog/contracts: {exc}")
    sys.exit(1)

runbooks = data.get("runbooks")
if not isinstance(runbooks, list) or not runbooks:
    print(f"ERROR {JSON_PATH} has no non-empty 'runbooks' array")
    sys.exit(1)

required_fields = (
    "slug",
    "title",
    "mode",
    "doc",
    "governing_object",
    "non_object",
    "decision_owner",
    "required_artifacts",
    "termination_criteria",
    "termination_contract",
    "roster",
)

PLACEHOLDERS = {"", "tbd", "todo", "n/a", "na", "none", "-", "--", "pending", "unknown"}
TERMINATION_KEYS = ("achieved", "outstanding", "accountable", "on_breach")
OPTIONAL_TERMINATION_KEYS = ("conservation_resources", "revision_conditions")

seen_slugs = set()
total_refs = 0
total_artifacts = 0
contracts = 0

for rb in runbooks:
    if not isinstance(rb, dict):
        errors.append(f"runbook entry is not an object: {rb!r}")
        continue

    rid = rb.get("slug", "<no slug>")

    for field in required_fields:
        if field not in rb:
            errors.append(f"runbook '{rid}' is missing required field {field!r}")

    for field in (
        "slug",
        "title",
        "mode",
        "governing_object",
        "non_object",
        "decision_owner",
        "termination_criteria",
    ):
        value = rb.get(field)
        if field in rb and (not isinstance(value, str) or not value.strip()):
            errors.append(f"runbook '{rid}': {field!r} must be a non-empty string")

    slug = rb.get("slug")
    if not isinstance(slug, str):
        errors.append(f"runbook entry: slug must be a string")
        continue
    if slug in seen_slugs:
        errors.append(f"duplicate runbook slug '{slug}'")
    seen_slugs.add(slug)

    doc = rb.get("doc")
    if "doc" in rb:
        if not isinstance(doc, str) or not doc.strip():
            errors.append(f"runbook '{rid}': doc must be a non-empty path string")
        elif not os.path.isfile(doc):
            errors.append(f"runbook '{rid}': doc path does not exist: {doc}")

    artifacts = rb.get("required_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"runbook '{rid}': required_artifacts must be a non-empty array")
        artifacts = []

    if len([a for a in artifacts if isinstance(a, str)]) != len(set(a for a in artifacts if isinstance(a, str))):
        errors.append(f"runbook '{rid}': required_artifacts contains duplicates")

    for artifact in artifacts:
        total_artifacts += 1
        if not isinstance(artifact, str) or not artifact.strip():
            errors.append(f"runbook '{rid}': invalid required_artifact {artifact!r}")
        elif not os.path.isfile(artifact):
            errors.append(f"runbook '{rid}': required artifact does not exist: {artifact}")

    roster = rb.get("roster")
    if not isinstance(roster, list) or not roster:
        errors.append(f"runbook '{rid}': roster must be a non-empty array")
        roster = []

    all_agents = []
    for group in roster:
        if not isinstance(group, dict):
            errors.append(f"runbook '{rid}': roster group is not an object")
            continue
        group_name = group.get("group", "?")
        agents = group.get("agents")
        if not isinstance(agents, list) or not agents:
            errors.append(f"runbook '{rid}' / group '{group_name}': agents must be non-empty")
            continue
        for agent_slug in agents:
            total_refs += 1
            all_agents.append(agent_slug)
            if not isinstance(agent_slug, str) or agent_slug not in real:
                errors.append(
                    f"runbook '{rid}' / group '{group_name}': slug '{agent_slug}' "
                    "does not match any agent .md filename stem"
                )

    if ASSURANCE_SLUG not in all_agents:
        errors.append(
            f"runbook '{rid}': mandatory assurance agent '{ASSURANCE_SLUG}' is absent"
        )

    # Catch the most obvious objective-proxy mistake mechanically. This is not
    # a semantic strategy validator; it simply prevents empty or identical framing.
    # A termination criterion that says nothing is worse than a missing field: it
    # passes the check and reports closure discipline the runbook does not have.
    term = rb.get("termination_criteria")
    if isinstance(term, str):
        if term.strip().casefold() in PLACEHOLDERS:
            errors.append(
                f"runbook '{rid}': termination_criteria is a placeholder ({term.strip()!r}), not a criterion"
            )

    contract = rb.get("termination_contract")
    if "termination_contract" not in rb:
        # required_fields already records the missing field; keep one structural
        # error per omission rather than adding a second error for the same defect.
        pass
    elif not isinstance(contract, dict):
        errors.append(f"runbook '{rid}': termination_contract must be an object")
    else:
        contracts += 1
        for key in (*TERMINATION_KEYS, *(key for key in OPTIONAL_TERMINATION_KEYS if key in contract)):
            value = contract.get(key)
            if key not in contract:
                errors.append(f"runbook '{rid}': termination_contract is missing {key!r}")
            elif not isinstance(value, str) or value.strip().casefold() in PLACEHOLDERS:
                errors.append(
                    f"runbook '{rid}': termination_contract.{key} must be a non-placeholder string"
                )
        unknown = set(contract) - set(TERMINATION_KEYS) - set(OPTIONAL_TERMINATION_KEYS)
        if unknown:
            errors.append(
                f"runbook '{rid}': termination_contract has unknown key(s): {', '.join(sorted(unknown))}"
            )

    if not isinstance(rb.get("mode"), str) or rb.get("mode") not in vocabulary["runbook_modes"]:
        errors.append(f"runbook '{rid}': mode is not a recognized NEXUS mode")
    owner = rb.get("decision_owner")
    if isinstance(owner, str) and owner.strip().casefold() in PLACEHOLDERS:
        errors.append(f"runbook '{rid}': decision_owner is a placeholder")

    obj = rb.get("governing_object")
    non = rb.get("non_object")
    if isinstance(obj, str) and isinstance(non, str):
        if obj.strip().casefold() == non.strip().casefold():
            errors.append(f"runbook '{rid}': governing_object and non_object are identical")

if errors:
    print(
        f"FAILED: {len(errors)} runbook consistency/strategy error(s). "
        f"{JSON_PATH} must satisfy the NEXUS v2 contract.\n"
    )
    for error in errors:
        print(f"  ERROR {error}")
    sys.exit(1)

print(
    f"PASSED: {len(runbooks)} runbooks, {total_refs} agent slug references, "
    f"{total_artifacts} required artifacts, {contracts}/{len(runbooks)} termination contracts "
    f"— references and required metadata are structurally valid; closure adequacy requires human review."
)
PYEOF
