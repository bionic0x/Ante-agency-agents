# Changelog

## Review follow-up — 2026-09-14

- Make stale catalog and converted-output manifests fail pull-request CI, matching
  the existing main-push checks. Regeneration must be committed before merge.
- Document the checked OpenClaw source pin, 196 source-path/blob matches, import
  and alias counts, upstream manifest scope differences, and manual sync policy.
- Add a worked Mispriced CMO handoff to marketing, sales and product, with owner
  acceptance, evidence limits, stopping rules and installation commands.
- Add a historical division-count comparison and runbook index to the README.
- Clarify checked-in validation dependencies, simulated Hermes test boundaries
  and Solana specialist governance outside HTP.

## Consolidation and functional installation

[PR #6](https://github.com/bionic0x/Ante-agency-agents/pull/6) introduced the
11-agent Mispriced CMO division, two runbooks and the generated complete catalog,
taking the roster from 476 to 487 agents across 19 divisions and eight runbooks.
It also repaired damaged headings and consolidated doctrine references.

[PR #7](https://github.com/bionic0x/Ante-agency-agents/pull/7), merged as
`6a506f174747fd34d1efc542f4fe316e32dd28a9`, hardened filtered installation,
parallel argument handling, failure propagation, destination handling,
conversion freshness and Hermes lifecycle validation; added runbook selection
and release verification; and removed obsolete bootstrap machinery.

The 186 normalized community imports and 10 aliases predate those two PRs.
They derive from `mergisi/awesome-openclaw-agents` at
`05820c51125e86a979432e21651d34dc9b14621f`.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and
[strategy/UPSTREAM-SYNC.md](strategy/UPSTREAM-SYNC.md) for verification limits.
