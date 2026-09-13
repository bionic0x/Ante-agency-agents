# HTP Gate 0 — Solana + Arbitrum One

This directory is the operational package for the dual-network Gate 0 runbook.

## Concrete mapping

- `agent-mapping.md` — G1/P1/S1/D1/E1-SOL/E1-ARB/D3 assignments and authority boundaries.

## Chain overlays

- `overlays/solana.md`
- `overlays/arbitrum.md`

## E1 ↔ S1 handoff

- `handoff-e1-s1.md`

## Six Gate 0 artifacts

1. `gate0/01-object-non-object.md`
2. `gate0/02-jurisdiction-activity.md`
3. `gate0/03-threat-model.md`
4. `gate0/04-domain-map.md`
5. `gate0/05-claim-registers.yaml`
6. `gate0/06-mvp-falsifiers.md`

## Concrete instances

### 2026-09-13 — Kamino Lend + Aave V3.7

`instances/2026-09-13-kamino-aave/`

- Solana: Kamino Lend Main Market, SOL/USDC.
- Arbitrum One: Aave V3.7, WETH/native USDC.
- Static manifests frozen to pinned primary-source revisions.
- First E1-SOL→S1 review: **BLOCKED** pending live reserve/oracle/account snapshot and a concrete SOL-ORD execution surface.
- First E1-ARB→S1 review: **CHANGES_REQUESTED**; static deployment accepted, runtime risk/oracle/recovery policy still pending.
- No production or benchmark authority granted.

## Runbook

- `../runbooks/scenario-htp-gate0-solana-arbitrum.md`
- Registry: `../runbooks.json` → `htp-gate0-solana-arbitrum`

## Status

The generic package remains **Gate 0 pending** until an instance satisfies its closeout requirements. The current Kamino/Aave instance is **HOLD** after the first chain-specific security handoffs.

The two networks share document structure, evidence vocabulary and review mechanics only. Solana evidence, security acceptance, legal classification, thresholds, metrics or Gate status do not transfer to Arbitrum One, and vice versa, without an explicit transfer proposition and chain-specific verification.
