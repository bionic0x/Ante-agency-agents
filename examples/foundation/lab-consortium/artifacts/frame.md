# ante frame — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T09:00:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `dcbf016f1dd916afed380643e0e8833035cd77a936643c2b0c1d4f4398ba243b` |
| Artefact SHA-256 | `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b` |

## Claims

| Id | Status | Claim | Source | Date | Limit |
|---|---|---|---|---|---|
| cap-100 | EVIDENCE | Effective weekly capacity after maintenance is 100 hours. | lab-maintenance-log-w43 | 2026-10-20 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |
| demand-110 | EVIDENCE | Universities A, B and C request 50, 40 and 20 hours: 110 in total. | reservation-export-2026-10-21 | 2026-10-21 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |
| priority-50 | EVIDENCE | 50 requested hours carry a confirmed external deadline. | funder-deadline-letters | 2026-10-22 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |

## Content

```json
{
  "case": {
    "id": "lab-consortium",
    "title": "Shared laboratory access across universities A, B and C"
  },
  "end_state": {
    "statement": "A shared infrastructure the three members still consider worth sustaining, with priority projects completed on time.",
    "observable_condition": {
      "indicator": "priority projects completed within their external deadline",
      "threshold": "all projects with a confirmed deadline in the trial period",
      "observed_by": "consortium council minutes and funder confirmations"
    },
    "horizon": "three allocation cycles"
  },
  "minimum_acceptable": {
    "statement": "Priority hours protected and deferred hours rescheduled where confirmed slack exists.",
    "observable_condition": {
      "indicator": "priority hours delivered per week",
      "threshold": "50 of 50",
      "observed_by": "laboratory booking record"
    }
  },
  "beneficiaries": [
    "research teams of A, B and C",
    "funders relying on deadlines"
  ],
  "cost_bearers": [
    "teams whose deferrable hours move to later weeks",
    "technical staff running coordination"
  ],
  "limits": [
    {
      "kind": "ethical",
      "statement": "No allocation by bargaining power; criteria apply equally to all members."
    },
    {
      "kind": "cost",
      "statement": "No consumption of the 10-hour incident reserve for ordinary allocation."
    }
  ],
  "termination_criteria": [
    "Allocation works with ordinary means for three cycles without extraordinary meetings",
    "Escalate to capacity expansion if essential demand exceeds 90 hours in two consecutive cycles"
  ],
  "basis": [
    "cap-100",
    "demand-110",
    "priority-50"
  ]
}
```

## Next decision

Map actors, authority and dependencies against this end state (ante map).
