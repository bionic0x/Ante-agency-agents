# ante watch — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T12:00:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `afd9ec964fd3ab54c9657d9ed4ee09e31d18ee0bd0bb7e663305ec778bc28f52` |
| Artefact SHA-256 | `fef0d6e6e31dd61bfd09c336adbe4fa35088f052228011df20186529eda8c617` |

## Lineage

- options `9e9841d3467008035df11b3b98bc8de06047e87464fef85ed1bd75054acb7530`

## Content

```json
{
  "thresholds": [
    {
      "id": "urgent-share",
      "indicator": "share of hours declared urgent without a new deadline",
      "kind": "leading",
      "threshold": "above 10% in a cycle",
      "response": "adjust",
      "owner": "consortium coordinator",
      "effect_lag": "one cycle"
    },
    {
      "id": "essential-over-capacity",
      "indicator": "essential demand",
      "kind": "leading",
      "threshold": "above 90 hours in two consecutive cycles",
      "response": "pause",
      "owner": "consortium council",
      "effect_lag": "immediate"
    },
    {
      "id": "reserve-consumed",
      "indicator": "incident reserve used for ordinary work",
      "kind": "lagging",
      "threshold": "reserve fully consumed twice in a cycle",
      "response": "terminate",
      "owner": "technical staff lead",
      "effect_lag": "one week"
    }
  ],
  "reserve": {
    "what": "10 instrument hours per week",
    "contingency": "equipment failure or a proven emergency",
    "time_to_engage": "same day",
    "cost_of_not_using": "10 hours of deferrable demand wait one more week"
  },
  "culmination": {
    "signal": "coordination meetings grow while conflicts no longer fall",
    "review_question": "Is more coordination still reducing conflicts, or has the problem become capacity?"
  }
}
```

## Next decision

Write the termination contract before committing (ante close).
