# ante options — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T11:00:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `c766a254d000031588658125133ddc929d59d136464234de20f4157bdcbeb074` |
| Artefact SHA-256 | `9e9841d3467008035df11b3b98bc8de06047e87464fef85ed1bd75054acb7530` |

## Lineage

- cause `2456016bc2caa97e0e59231577425b55f42c6179fa30b1bd2760e18cd339e927`
- frame `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b`
- map `b21637d1efc77e244c2aab62bb67b04183105985e47b0c513b5b0d3aaaed2f14`

## Content

```json
{
  "options": [
    {
      "id": "continuity",
      "kind": "continuity",
      "mechanism": "first-come bookings and ad hoc negotiation",
      "viable": true,
      "resources": "no extra coordination",
      "reversibility": "high",
      "distribution_of_effects": "favours teams with informal access",
      "sustainability": "conflict recurs weekly",
      "assumptions": [
        "demand-110"
      ]
    },
    {
      "id": "central",
      "kind": "alternative",
      "mechanism": "a central office allocates every booking weekly",
      "viable": true,
      "resources": "permanent administrative capacity and an appeal path",
      "reversibility": "medium",
      "distribution_of_effects": "uniform rule, concentrated decision power",
      "sustainability": "depends on a permanent coordinator",
      "assumptions": [
        "cap-100"
      ]
    },
    {
      "id": "shared-criteria",
      "kind": "alternative",
      "mechanism": "common priority criteria applied by each university, joint coordination of conflicts only",
      "viable": true,
      "resources": "initial coordination effort; ordinary operation afterwards",
      "reversibility": "high",
      "distribution_of_effects": "deferrals fall on deferrable work, by rule",
      "sustainability": "self-applying if criteria are accepted",
      "assumptions": [
        "slack-20"
      ]
    },
    {
      "id": "external",
      "kind": "alternative",
      "mechanism": "move part of the demand to a compatible external laboratory",
      "viable": false,
      "why_not_viable": "compatibility, cost and qualification time are not verified",
      "resources": "contract and transfer costs",
      "reversibility": "medium",
      "distribution_of_effects": "cost sharing disputed",
      "sustainability": "bridge only",
      "assumptions": []
    }
  ],
  "criteria": [
    "contribution to purpose",
    "legitimacy",
    "reversibility",
    "reserve preserved"
  ],
  "comparison": {
    "continuity": {
      "contribution to purpose": "low: priority work competes with everything",
      "legitimacy": "low: rewards informal access",
      "reversibility": "high",
      "reserve preserved": "no: reserve absorbed by conflicts"
    },
    "central": {
      "contribution to purpose": "medium: orders scarcity, moves conflict to the centre",
      "legitimacy": "medium-low without accessible appeal",
      "reversibility": "medium",
      "reserve preserved": "yes if capped at 90 hours"
    },
    "shared-criteria": {
      "contribution to purpose": "high if criteria are accepted",
      "legitimacy": "high when members take part",
      "reversibility": "high: bounded trial",
      "reserve preserved": "yes: rule separates allocation from contingency"
    },
    "external": {
      "contribution to purpose": "high if compatible; unverified",
      "legitimacy": "medium: cost sharing open",
      "reversibility": "medium",
      "reserve preserved": "yes, if not double-counted"
    }
  },
  "preferred": {
    "option": "shared-criteria",
    "reason": "acts on priorities and record quality, keeps the reserve and stays reversible",
    "conditional_on": [
      "essential demand stays within 90 ordinary hours",
      "the council enforces the rule on senior teams"
    ]
  }
}
```

## Next decision

Test the options against competent reactions (ante react).
