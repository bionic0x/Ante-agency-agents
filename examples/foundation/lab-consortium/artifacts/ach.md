# ante ach — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T10:15:00Z |
| Verdict | — |
| Independence | SELF |
| Input SHA-256 | `65a595bdfd969e45d23400025273624731257a3dfc21d069ab214e0e12dc8d67` |
| Artefact SHA-256 | `6cdf6215377003bf082dfbc621f288f5572a21f7ba096449b5afcec140894287` |

## Lineage

- frame `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b`

## Claims

| Id | Status | Claim | Source | Date | Limit |
|---|---|---|---|---|---|
| dup-check | EVIDENCE | Reconciliation found 4 duplicate reservations out of 61. | reservation-reconciliation-2026-10-26 | 2026-10-26 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |
| tech-report | EVIDENCE | Technical staff report that essential demand is close to capacity. | technical-staff-note-2026-10-25 | 2026-10-25 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |
| tech-report-echo | EVIDENCE | The council minutes repeat the technical note on near-capacity demand. | council-minutes-2026-10-27 | 2026-10-27 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |
| model-summary | HYPOTHESIS | An assistant summary concluded that priorities are the main problem. | ante draft of 2026-10-27 | 2026-10-27 | Synthetic didactic data (Marco, Appendix E); not an observation of any real institution. |

## Content

```json
{
  "hypotheses": [
    {
      "id": "structural-scarcity",
      "statement": "Essential demand exceeds capacity."
    },
    {
      "id": "unresolved-priorities",
      "statement": "Conflicts come from the absence of shared priorities."
    },
    {
      "id": "bad-records",
      "statement": "Duplicate or stale reservations inflate demand."
    }
  ],
  "evidence": [
    {
      "id": "e-demand",
      "description": "110 hours requested against 90 ordinary",
      "claim": "demand-110",
      "source_id": "reservation-export",
      "depends_on": []
    },
    {
      "id": "e-dups",
      "description": "4 duplicates in 61 reservations",
      "claim": "dup-check",
      "source_id": "reconciliation",
      "depends_on": []
    },
    {
      "id": "e-tech",
      "description": "technical note on near-capacity demand",
      "claim": "tech-report",
      "source_id": "technical-staff",
      "depends_on": []
    },
    {
      "id": "e-minutes",
      "description": "council minutes on near-capacity demand",
      "claim": "tech-report-echo",
      "source_id": "council-minutes",
      "depends_on": [
        "e-tech"
      ]
    },
    {
      "id": "e-summary",
      "description": "assistant summary blaming priorities",
      "claim": "model-summary",
      "source_id": "ante-draft",
      "depends_on": []
    }
  ],
  "matrix": {
    "e-demand": {
      "structural-scarcity": "C",
      "unresolved-priorities": "C",
      "bad-records": "C"
    },
    "e-dups": {
      "structural-scarcity": "N",
      "unresolved-priorities": "N",
      "bad-records": "C"
    },
    "e-tech": {
      "structural-scarcity": "C",
      "unresolved-priorities": "I",
      "bad-records": "I"
    },
    "e-minutes": {
      "structural-scarcity": "C",
      "unresolved-priorities": "I",
      "bad-records": "I"
    },
    "e-summary": {
      "structural-scarcity": "I",
      "unresolved-priorities": "C",
      "bad-records": "N"
    }
  },
  "future_indicators": [
    {
      "hypothesis": "structural-scarcity",
      "indicator": "essential demand above 90 hours with criteria applied"
    },
    {
      "hypothesis": "bad-records",
      "indicator": "demand falls after weekly reconciliation"
    }
  ],
  "confidence": {
    "verbal": "moderate",
    "interval": [
      0.4,
      0.65
    ]
  },
  "analysis": {
    "counted_evidence": [
      "e-demand",
      "e-dups",
      "e-tech",
      "e-minutes"
    ],
    "excluded_self_produced": [
      "e-summary"
    ],
    "source_groups": [
      [
        "e-minutes",
        "e-tech"
      ]
    ],
    "inconsistency_raw": {
      "structural-scarcity": 0,
      "unresolved-priorities": 2,
      "bad-records": 2
    },
    "inconsistency_by_source_group": {
      "structural-scarcity": 0,
      "unresolved-priorities": 1,
      "bad-records": 1
    },
    "least_inconsistent": [
      "structural-scarcity"
    ],
    "non_diagnostic": [
      "e-demand"
    ],
    "sensitive_evidence": [],
    "interpretation": "Ratings are judgements, not probabilities. The least-inconsistent set is conditional on the matrix; corroborate the sensitive evidence first."
  }
}
```

## Findings

- **WARN** `SELF_CORROBORATION` evidence[4].claim: rests on a system-produced claim; listed but not counted
- **WARN** `SHARED_SOURCE` evidence: e-minutes, e-tech share a source or depend on each other; counted once

## Next decision

Record the leading hypothesis with its confidence and indicators.
