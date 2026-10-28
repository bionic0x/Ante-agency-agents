# Proposals awaiting the owner

Changes this branch prepared but must not make itself, because they touch
protected paths or settle a doctrinal conflict.

| File | Decision | What applying it does |
|---|---|---|
| `contracts-v2.json` | D-004 | Gives `strategy/contracts.json` the machine tables for the seven coherence tests and fourteen pathologies (today the strategy commands read them from here with `--contracts`). The owner chooses between the two existing wordings of test 1 and pathology 9. |
| `ci-wiring.patch` | D-017 | Adds the foundation checks and the published self-test to `scripts/verify-release.sh` and a job to `.github/workflows/check-runbooks.yml`. Apply with `git apply` in a commit labelled `protected:`. |
