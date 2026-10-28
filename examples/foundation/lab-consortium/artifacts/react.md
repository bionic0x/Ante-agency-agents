# ante react — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T11:30:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `b93c068f911c0ae1c3c5a13defd622a1206f65a8a9b8092b9f146a803164f3d6` |
| Artefact SHA-256 | `9844e5d9294464d2c9b7ff1236b48d2c159dbbf34b3d5663fbb3c20d31676df0` |

## Lineage

- map `b21637d1efc77e244c2aab62bb67b04183105985e47b0c513b5b0d3aaaed2f14`
- options `9e9841d3467008035df11b3b98bc8de06047e87464fef85ed1bd75054acb7530`

## Content

```json
{
  "reactions": [
    {
      "id": "a-overbooks",
      "actor": "uni-a",
      "kind": "opposition",
      "against_option": "shared-criteria",
      "description": "A classifies more requests as urgent to keep its hours.",
      "incentive": "A bears most deferrals under the rule",
      "information_revealed": "urgent share rising without new external deadlines",
      "capacity_required": "evidence check of deadlines by the coordinator",
      "activation_signal": "urgent hours rise without new deadline letters",
      "contingent_decision": "adjust",
      "changes_choice": false
    },
    {
      "id": "b-swaps",
      "actor": "research-teams",
      "kind": "cooperation",
      "against_option": "shared-criteria",
      "description": "Teams of B and C swap slots directly, making most coordination unnecessary.",
      "incentive": "faster access than waiting for coordination",
      "information_revealed": "conflicts resolved before they reach the coordinator",
      "capacity_required": "a swap log the council can audit",
      "activation_signal": "coordinator receives fewer than two conflicts a week",
      "contingent_decision": "adjust",
      "changes_choice": true
    },
    {
      "id": "funder-deadline",
      "actor": "council",
      "kind": "third_party_shift",
      "against_option": "shared-criteria",
      "description": "A funder advances a deadline, raising essential demand above 90 hours.",
      "incentive": "external reporting calendar",
      "information_revealed": "essential demand exceeding ordinary capacity",
      "capacity_required": "activate the external-capacity evaluation",
      "activation_signal": "essential demand above 90 hours for one cycle",
      "contingent_decision": "pause",
      "changes_choice": true
    }
  ]
}
```

## Next decision

Tie each indicator to a response before acting (ante watch).
