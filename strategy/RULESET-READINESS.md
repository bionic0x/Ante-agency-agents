# Main ruleset readiness — proposed, not applied

Reviewed against `d910af7` plus the manifest correction in PR #27. This is a
repository-content review, not a readback of live GitHub settings. The historical
ruleset ID `23156139` must be confirmed by an administrator before any update.

## Drift decision

Keep strict drift validation on both PRs and main. Changes to agents, converters
or source contracts must include the reviewed manifest delta in the same PR:

```bash
bash scripts/test-convert-outputs.sh --update
git diff -- scripts/convert-outputs.sha256
bash scripts/test-convert-outputs.sh
```

After merging or rebasing main into a branch, regenerate from the combined tree
and review the keys again. Do not take either side of a manifest conflict wholesale.
`--drift=advisory` remains a local diagnostic, not the CI acceptance policy. There
is no post-merge direct-push regeneration step. A contributor or maintainer can
correct drift on the PR branch before merge; this is not an intrinsic deadlock.

## Required contexts checked against workflow definitions

| Context | Workflow |
| --- | --- |
| Validate agent frontmatter and structure | lint-agents.yml |
| divisions.json is the single source of truth | check-divisions.yml |
| runbook rosters reference real agent slugs | check-runbooks.yml |
| tools.json is the single source of truth | check-tools.yml |
| install.sh hermes config rewrite | check-hermes-config-rewrite.yml |
| install.sh behavior (ubuntu-latest) | test-install.yml |
| install.sh behavior (macos-latest) | test-install.yml |

All six workflows have `pull_request` and `push` triggers without path filters.
The installer matrix expands to the two required names. Adding a step to the
existing tools job adds no required context. This static match does not establish
that GitHub currently enforces the payload or that a runner will be available.

## Administration decision remains pending

The proposed payload targets only `refs/heads/main`, requires PRs and seven
up-to-date successful checks, disallows deletion and force pushes, and has no
bypass actors. It requires zero approving reviews: CI is the mandatory approval
gate; human peer review is not. Existing review threads must still be resolved.

A broken workflow is often repairable in its own PR because PR checks execute
the proposed workflow. Administrative recovery is needed only when the required
context cannot be produced by such a repair (for example, unavailable external
infrastructure). Decide the administrator recovery procedure before activation;
this review adds no emergency bypass. Inspect the newest SHA when concurrency
cancels an older run; cancellation alone does not mean the newest run is stuck.

An administrator should back up and inspect the live ruleset, confirm its ID,
inventory overlapping repository/inherited rulesets, and only then apply the
reviewed payload through the procedure in OPERATIONS.md. Matching names do not
replace a ruleset: verify the ID and read back the effective configuration.

Operational acceptance remains **NOT_DEMONSTRATED**. Under an ordinary actor,
confirm work-branch creation/update/deletion succeeds, incomplete or failed checks
block merging to main, direct pushes to main fail, and deletion/force updates to
main are denied. Destructive rejection tests should first use a disposable
repository with equivalent rules; do not risk deleting main merely to test a
protection that has not yet been demonstrated.

No repository setting is changed by this document or by the drift documentation
correction. Apply nothing until the repository owner explicitly authorizes it.
