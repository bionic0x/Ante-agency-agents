# ante pathology — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T13:15:00Z |
| Verdict | — |
| Independence | SEPARATED_CONTEXT |
| Input SHA-256 | `47c3ed00a869e9522e287a6784496a0e00dd474af579f01545060ccd31951262` |
| Artefact SHA-256 | `666b8f3af454d8f5cde4441fe5993042330f9c0c3fe9d91c3daf13f9ef71718f` |

## Lineage

- frame `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b`
- map `b21637d1efc77e244c2aab62bb67b04183105985e47b0c513b5b0d3aaaed2f14`

## Content

```json
{
  "pathologies": {
    "level_inversion": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "nominal_objective": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "imaginary_centre": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "concept_confusion": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "dispersion": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "frictionless_plan": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "disoriented_speed": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "denied_culmination": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "reflex_symmetry": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "illegitimate_victory": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "intent_attribution": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "metric_substitution": {
      "status": "DETECTED",
      "evidence": [
        "a-inflates"
      ],
      "false_positive_check": "urgency labels could rise for real deadlines; the watch threshold checks for new deadline letters",
      "note": "the urgency label can be gamed to win hours"
    },
    "escalation_of_commitment": {
      "status": "NOT_DETECTED",
      "evidence": [],
      "false_positive_check": "not applicable when not detected",
      "note": "examined against the frame, options and watch artefacts; no mechanism present"
    },
    "chronic_personalization": {
      "status": "NOT_ASSESSED",
      "evidence": [],
      "false_positive_check": "n/a",
      "note": "requires observing how exceptions are granted over more than one cycle"
    }
  },
  "detected": [
    {
      "id": "metric_substitution",
      "mechanism": "Incentives change the record or the conduct to improve the number.",
      "correction": "Review the relation between measure, mechanism and result."
    }
  ],
  "not_assessed": [
    "chronic_personalization"
  ],
  "doctrine_sha256": "36a1bfe3db41383471e3541b8d3f2acdcea13afe7a23e415db6694a663595f63"
}
```

## Next decision

Address metric_substitution in the decision conditions (ante decide).
