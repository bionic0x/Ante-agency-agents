#!/usr/bin/env bash
#
# check-runbooks.sh — enforce that strategy/runbooks.json stays in sync with the
# real agent roster AND satisfies the NEXUS strategic contract.
#
# The Agency Agents app reads strategy/runbooks.json to turn a scenario into a
# one-click team deploy. A deployable scenario must not be only a list of agents:
# it must state the governing object, explicit non-object, accountable decision
# owner, mandatory artifacts, termination criteria, and an independent Strategic
# Assurance Lead.
#
# This check fails when:
#   1. runbooks.json is invalid JSON or structurally incomplete
#   2. a roster slug does not match a real agent file
#   3. a scenario document or required artifact path does not exist
#   4. a runbook slug is duplicated
#   5. strategic metadata is missing or empty
#   6. the Strategic Assurance Lead is absent from a runbook roster
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
import subprocess
import sys

JSON_PATH = "strategy/runbooks.json"
ASSURANCE_SLUG = "specialized-strategic-assurance-lead"
NON_DIVISION = {"integrations", "examples", "strategy", "scripts", ".github"}
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

schema_version = str(data.get("schema_version", ""))
if not schema_version.startswith("2."):
    errors.append(
        f"schema_version must be 2.x for the strategic runbook contract; got {schema_version!r}"
    )

# Real slugs = filename stems of tracked agent .md files under division dirs.
tracked = subprocess.check_output(["git", "ls-files", "*/*.md"]).decode().splitlines()
real = {
    os.path.basename(path)[:-3]
    for path in tracked
    if path.split("/")[0] not in NON_DIVISION
}

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
    "roster",
)

seen_slugs = set()
total_refs = 0
total_artifacts = 0

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
    if slug in seen_slugs:
        errors.append(f"duplicate runbook slug '{slug}'")
    seen_slugs.add(slug)

    doc = rb.get("doc")
    if doc:
        if not isinstance(doc, str) or not doc.strip():
            errors.append(f"runbook '{rid}': doc must be a non-empty path string")
        elif not os.path.isfile(doc):
            errors.append(f"runbook '{rid}': doc path does not exist: {doc}")

    artifacts = rb.get("required_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"runbook '{rid}': required_artifacts must be a non-empty array")
        artifacts = []

    if len(artifacts) != len(set(artifacts)):
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
            if agent_slug not in real:
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
    f"{total_artifacts} required artifacts — all resolve and every runbook "
    f"satisfies the NEXUS v2 strategic contract."
)
PYEOF
