# ante map — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T09:30:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `8e9359fdf49309a71a052f7685a7547b1ac9f67684ad9ef8cfec232a1d1e968d` |
| Artefact SHA-256 | `b21637d1efc77e244c2aab62bb67b04183105985e47b0c513b5b0d3aaaed2f14` |

## Lineage

- frame `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b`

## Claims

| Id | Status | Claim | Source | Date | Limit |
|---|---|---|---|---|---|
| a-inflates | ATTRIBUTED_INTENT | University A will inflate requests if it anticipates cuts. | council-minutes-2026-09 | 2026-09-30 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |

## Content

```json
{
  "actors": [
    {
      "id": "council",
      "kind": "decider",
      "preference": "Keep the consortium intact with minimal conflict.",
      "representation": "Acts for the three member universities under the consortium agreement.",
      "commitment_capacity": "Can adopt allocation criteria; cannot add capacity without member budgets.",
      "affected_by": "Loses legitimacy if criteria favour the strongest member.",
      "basis": []
    },
    {
      "id": "uni-a",
      "kind": "resource_holder",
      "preference": "Maximise hours for its own projects.",
      "representation": "Its research office represents A's teams.",
      "commitment_capacity": "Can commit its teams to the criteria; cannot commit funders.",
      "affected_by": "Bears most deferred hours under a priority rule.",
      "basis": [
        "a-inflates"
      ]
    },
    {
      "id": "technical-staff",
      "kind": "executor",
      "preference": "Predictable schedules and protected maintenance windows.",
      "representation": "Represents the laboratory's operating capacity.",
      "commitment_capacity": "Commits hours actually usable; cannot decide priorities.",
      "affected_by": "Absorbs coordination workload.",
      "basis": [
        "cap-100"
      ]
    },
    {
      "id": "research-teams",
      "kind": "affected",
      "preference": "Access when their experiments need it.",
      "representation": "Each team speaks for its own project only.",
      "commitment_capacity": "Can accept a slot; cannot reallocate others.",
      "affected_by": "Delays fall on them directly.",
      "basis": [
        "demand-110"
      ]
    }
  ],
  "dependencies": [
    {
      "id": "usable-hours",
      "actor": "technical-staff",
      "resource": "usable instrument hours",
      "criticality": "critical",
      "substitutes": [
        "compatible external laboratory"
      ],
      "substitution_time": "four to six weeks to qualify an external lab"
    }
  ],
  "third_parties": [
    {
      "actor": "council",
      "role": "arbiter"
    }
  ],
  "formal_vs_effective": "Formally the council decides; in practice informal bookings by senior teams pre-empt the calendar."
}
```

## Next decision

State the causal hypothesis and its rival (ante cause).
