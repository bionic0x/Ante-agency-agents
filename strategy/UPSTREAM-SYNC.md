# Upstream provenance and synchronization

## Sources and evidence

The OpenClaw community capability source is
[mergisi/awesome-openclaw-agents](https://github.com/mergisi/awesome-openclaw-agents),
not the OpenClaw runtime repository. Importing its templates does not establish
compatibility with any particular runtime release.

The current source pin is
[05820c51125e86a979432e21651d34dc9b14621f](https://github.com/mergisi/awesome-openclaw-agents/commit/05820c51125e86a979432e21651d34dc9b14621f).
The importer is [import-openclaw-community.py](../scripts/import-openclaw-community.py);
the per-source reconciliation is [unified-agency-sources.json](unified-agency-sources.json).
Attribution is retained in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
The [architecture contract](UNIFIED-AGENCY-ARCHITECTURE.md) explains normalization,
aliasing, authority boundaries, and adapter-specific behavior.

### Verification record — 2026-09-14

Compared the registry at repository commit
[6a506f1](https://github.com/bionic0x/Ante-agency-agents/commit/6a506f174747fd34d1efc542f4fe316e32dd28a9)
against the pinned source's recursive Git tree and `agents.json`:

| Check | Observed result |
|---|---|
| Source `agents/**/SOUL.md` discovery | 196 files |
| Registry source paths and Git blob IDs | All 196 matched the pinned tree; no missing or mismatched entries |
| Reconciliation | 186 imports + 10 aliases = 196 source templates |
| Imported canonical destination paths | All 186 exist in this repository |
| Upstream manifest | 199 entries: 194 in agent discovery scope + 5 under `configs/ollama/` |
| Agent files omitted from upstream manifest | `agents/marketing/geo-agent/SOUL.md` and `agents/marketing/hackernews-agent/SOUL.md` |

The five Ollama configuration templates exist upstream but are outside the
importer's `agents/` discovery scope. The registry field
`manifest_paths_missing_from_tree` records a difference against that scoped
discovery set; it does not mean those paths are absent from the whole Git tree.

That historical review established source-tree reconciliation and canonical
destination existence. The importer is now stricter for every future preview or
sync: `--source-ref` must be a full 40-hex commit SHA, the recursive tree supplies
the expected blob IDs, and the exact downloaded bytes for `agents.json` and every
discovered `SOUL.md` must hash to those IDs using Git's blob-object format before
UTF-8 decoding or normalization. A mismatch, failed read or decode failure aborts
before any canonical agent, source registry or stale path is written.

Byte identity with the pinned tree does not prove semantic equivalence of every
normalized profile, that aliases are the best possible semantic match, that the
source is safe, or successful authenticated OpenClaw execution. No original
import PR is inferred from a provenance header.
[PR #6](https://github.com/bionic0x/Ante-agency-agents/pull/6) added Mispriced CMO
and catalog work; [PR #7](https://github.com/bionic0x/Ante-agency-agents/pull/7)
hardened installation and validation. The OpenClaw import predates both.

## Versioning policy

Updates are manual, reviewed, and pinned to a full commit SHA. There is no
automatic sync, floating `main` import, or promised quarterly cadence.
A maintainer initiates an update when needed and owns its review.

Each sync PR must record the old and new source commits, why the update is
needed, discovery/import/alias counts, manifest discrepancies, failed reads,
removed paths, and semantic changes to normalized profiles. Review alias
decisions and local edits explicitly: rerunning the importer can rewrite
normalized profiles and remove stale imported paths.

Use a clean branch or worktree. Resolve the intended upstream revision to a full
SHA, then run the import preview before applying:

```bash
# Set this to the specific full source commit selected for review.
OPENCLAW_SOURCE_SHA=05820c51125e86a979432e21651d34dc9b14621f
python3 scripts/import-openclaw-community.py --source-ref "$OPENCLAW_SOURCE_SHA" --root . --dry-run
python3 scripts/import-openclaw-community.py --source-ref "$OPENCLAW_SOURCE_SHA" --root .
git diff --stat
python3 -m pip install -r scripts/requirements-validation.txt
python3 scripts/build-catalog.py
bash scripts/test-convert-outputs.sh --update
bash scripts/verify-release.sh
```

The preview performs the same source-byte verification as the applying run; it
must not write canonical files. Inspect the complete diff, preserve required
license notices, reconcile the registry and build metadata with the chosen pin,
and commit the generated catalog and manifest in the same PR. A verified preview
is not approval of the semantic diff.

Catalog freshness and converted-output drift must pass on the PR before merge.
Do not defer regeneration until the push to `main`. Host/runtime compatibility
needs a separately recorded smoke test with the actual installed runtime version,
authentication state, selected profile, invocation, and observed result.
