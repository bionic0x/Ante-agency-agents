# ante focus — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T10:30:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `0e72f693ab92635ee5729d00ffec22927fd3c542ec473c9c6fe58311181aeb20` |
| Artefact SHA-256 | `f93ef843113c69d4824768b05a8d38b40879a6b01c8b7f150a19139f1a7f03cf` |

## Lineage

- map `b21637d1efc77e244c2aab62bb67b04183105985e47b0c513b5b0d3aaaed2f14`

## Claims

| Id | Status | Claim | Source | Date | Limit |
|---|---|---|---|---|---|
| cohesion-hypothesis | HYPOTHESIS | Acceptance of one allocation criterion is what keeps the three members cooperating. | council discussion 2026-10-27 | 2026-10-27 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |

## Content

```json
{
  "system": {
    "name": "consortium laboratory access",
    "scope": "weekly allocation of instrument hours among A, B and C",
    "horizon": "three allocation cycles"
  },
  "candidate": {
    "id": "shared-criteria",
    "description": "The members' acceptance of one allocation criterion that holds the cooperation together.",
    "kind": "cohesion"
  },
  "capabilities": [
    {
      "id": "allocate",
      "verb": "allocate",
      "description": "turn requests into a usable weekly schedule"
    }
  ],
  "requirements": [
    {
      "id": "accepted-priority",
      "capability": "allocate",
      "description": "a priority rule every member accepts as fair"
    }
  ],
  "vulnerabilities": [
    {
      "id": "informal-bookings",
      "requirement": "accepted-priority",
      "feasible_path": "senior teams bypass the calendar through informal bookings",
      "compensable_within_horizon": false
    }
  ],
  "matrix": {
    "scope": "allocation inside the consortium for three cycles",
    "dependency": "without accepted criteria every week reopens the dispute",
    "transmission": "each bypass reduces trust and invites defensive over-booking",
    "substitution": {
      "alternatives": [
        "central weekly allocation by the council"
      ],
      "time": "one cycle to switch, at a legitimacy cost"
    },
    "conversion": "accepted criteria convert existing hours into predictable access",
    "revision": "if conflicts persist with criteria applied, the dependency is capacity, not cohesion"
  },
  "decisive_point": {
    "statement": "Council adoption of an appealable priority rule before cycle 1.",
    "enables": "members can plan against a known rule"
  },
  "schwerpunkt": {
    "focus": "Protect the 50 deadline-bound hours every week.",
    "renunciations": [
      "no 100% occupancy target",
      "no guarantee for deferrable hours in the week requested"
    ],
    "minimums": [
      "10-hour incident reserve kept",
      "every deferral has a confirmed later slot"
    ]
  },
  "own_dependencies": [
    "technical staff time for coordination",
    "council willingness to enforce the rule on its senior members"
  ],
  "basis": [
    "cohesion-hypothesis"
  ]
}
```

## Next decision

Design options that differ in mechanism (ante options).
