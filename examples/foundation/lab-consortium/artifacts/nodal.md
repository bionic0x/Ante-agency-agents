# ante nodal — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T13:30:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `9ab10f0f885c9c17b9bb160e685330f8e0891ef8f13bba2ae0d86091e62bb844` |
| Artefact SHA-256 | `c8a966827d82d262c3fc774dcf48d2799be0387c1355e97fdf86358d57e73756` |

## Lineage

- ach `6cdf6215377003bf082dfbc621f288f5572a21f7ba096449b5afcec140894287`
- cause `2456016bc2caa97e0e59231577425b55f42c6179fa30b1bd2760e18cd339e927`
- close `b5437d8d4c3692706913991c729d868c65a977e90bd6898cb8ae673e52489b8f`
- cohere `5599a450119c14fcc49771fb679cb478ba739e6ce96cbd01bf50d18b660bebf9`
- focus `f93ef843113c69d4824768b05a8d38b40879a6b01c8b7f150a19139f1a7f03cf`
- frame `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b`
- map `b21637d1efc77e244c2aab62bb67b04183105985e47b0c513b5b0d3aaaed2f14`
- options `9e9841d3467008035df11b3b98bc8de06047e87464fef85ed1bd75054acb7530`
- pathology `666b8f3af454d8f5cde4441fe5993042330f9c0c3fe9d91c3daf13f9ef71718f`
- react `9844e5d9294464d2c9b7ff1236b48d2c159dbbf34b3d5663fbb3c20d31676df0`
- street `e7879bed3397c340448220a0a1851e49049be05d42b66da87769570ef967ffe7`
- watch `fef0d6e6e31dd61bfd09c336adbe4fa35088f052228011df20186529eda8c617`

## Content

```json
{
  "irreversibility": "medium",
  "weight": 1.5,
  "thresholds": {
    "corroborate": 4.0,
    "check": 2.0
  },
  "artefacts_examined": [
    "ach:6cdf62153770",
    "cause:2456016bc2ca",
    "close:b5437d8d4c36",
    "cohere:5599a450119c",
    "focus:f93ef843113c",
    "frame:f3f11099665d",
    "map:b21637d1efc7",
    "options:9e9841d34670",
    "pathology:666b8f3af454",
    "react:9844e5d92944",
    "street:e7879bed3397",
    "watch:fef0d6e6e31d"
  ],
  "load_bearing_claims": [
    {
      "id": "demand-110",
      "status": "EVIDENCE",
      "origin": "external",
      "stated_in": "frame",
      "load": 5,
      "score": 7.5,
      "required_verification": "corroborate",
      "cited_by": [
        "map:actors[3].basis",
        "cause:basis",
        "ach:evidence[0].claim",
        "options:options[0].assumptions",
        "cohere:tests.legitimacy.evidence"
      ],
      "blocking": false
    },
    {
      "id": "cap-100",
      "status": "EVIDENCE",
      "origin": "external",
      "stated_in": "frame",
      "load": 4,
      "score": 6.0,
      "required_verification": "corroborate",
      "cited_by": [
        "map:actors[2].basis",
        "options:options[1].assumptions",
        "cohere:tests.conversion.evidence",
        "cohere:tests.exit.evidence"
      ],
      "blocking": false
    },
    {
      "id": "a-inflates",
      "status": "ATTRIBUTED_INTENT",
      "origin": "external",
      "stated_in": "map",
      "load": 3,
      "score": 4.5,
      "required_verification": "corroborate",
      "cited_by": [
        "cohere:tests.epistemic.evidence",
        "cohere:tests.interactive.evidence",
        "pathology:pathologies.metric_substitution.evidence"
      ],
      "blocking": true
    },
    {
      "id": "slack-20",
      "status": "ASSUMPTION",
      "origin": "owner",
      "stated_in": "cause",
      "load": 3,
      "score": 4.5,
      "required_verification": "corroborate",
      "cited_by": [
        "options:options[2].assumptions",
        "cohere:tests.causal.evidence",
        "cohere:tests.epistemic.evidence"
      ],
      "blocking": true
    },
    {
      "id": "priority-50",
      "status": "EVIDENCE",
      "origin": "external",
      "stated_in": "frame",
      "load": 2,
      "score": 3.0,
      "required_verification": "check",
      "cited_by": [
        "cohere:tests.conversion.evidence",
        "cohere:tests.purpose.evidence"
      ],
      "blocking": false
    }
  ],
  "routine_claims": [
    "cohesion-hypothesis",
    "dup-check",
    "model-summary",
    "tech-report",
    "tech-report-echo"
  ],
  "blocking": [
    "a-inflates",
    "slack-20"
  ]
}
```

## Findings

- **WARN** `LOAD_BEARING_UNVERIFIED` a-inflates: carries the plan unverified: corroborate it or accept it as a named risk in decide
- **WARN** `LOAD_BEARING_UNVERIFIED` slack-20: carries the plan unverified: corroborate it or accept it as a named risk in decide

## Next decision

Corroborate a-inflates, slack-20 and re-run nodal, or accept them as named risks in decide; PROCEED is refused until then.
