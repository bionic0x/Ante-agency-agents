# ante street — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T11:45:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `971efd81e5cfa6f25f14e5944e21c86c482864888797226b09de3c262715cf3b` |
| Artefact SHA-256 | `e7879bed3397c340448220a0a1851e49049be05d42b66da87769570ef967ffe7` |

## Lineage

- frame `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b`
- map `b21637d1efc77e244c2aab62bb67b04183105985e47b0c513b5b0d3aaaed2f14`

## Content

```json
{
  "misuse_analysis": [
    {
      "id": "urgent-share",
      "kind": "metric",
      "statement": "share of hours declared urgent",
      "purpose": "protect hours with a real external deadline",
      "misuse": [
        {
          "actor": "uni-a",
          "reuse": "relabel ordinary requests as urgent so they jump the queue",
          "effect_on_purpose": "urgent hours crowd out the requests the label was meant to protect",
          "indicator": "urgent requests without a deadline document attached",
          "countermeasure": "an urgency label counts only with the funder's deadline letter"
        },
        {
          "actor": "council",
          "reuse": "push the share down by refusing urgent labels to show the metric improving",
          "effect_on_purpose": "real deadlines are missed while the indicator looks healthy",
          "indicator": "missed external deadlines on requests that were refused the urgent label",
          "countermeasure": "report missed deadlines beside the share every cycle"
        }
      ]
    },
    {
      "id": "essential-demand",
      "kind": "metric",
      "statement": "essential demand per cycle",
      "purpose": "trigger a capacity decision before coordination stops helping",
      "misuse": [
        {
          "actor": "research-teams",
          "reuse": "split one essential booking into several smaller ones to look less dominant",
          "effect_on_purpose": "the capacity trigger fires late because demand looks fragmented",
          "indicator": "bookings by one team within the same week whose sum exceeds its declared need",
          "countermeasure": "aggregate essential demand by project, not by booking"
        }
      ]
    },
    {
      "id": "deadline-document-rule",
      "kind": "rule",
      "statement": "urgency labels require a deadline document",
      "purpose": "remove the incentive to inflate urgency",
      "misuse": [
        {
          "actor": "uni-a",
          "reuse": "obtain generic deadline letters that cover every request",
          "effect_on_purpose": "the document becomes a formality and inflation resumes",
          "indicator": "deadline letters reused across unrelated projects",
          "countermeasure": "letters name the project and the date; the coordinator samples them each cycle"
        }
      ]
    }
  ],
  "covered_metrics": [
    "essential demand per cycle",
    "share of hours declared urgent"
  ]
}
```

## Next decision

Carry each manipulation indicator into watch; cohere checks coverage.
