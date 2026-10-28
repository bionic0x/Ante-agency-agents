# ante close — lab-consortium

| Field | Value |
|---|---|
| Decision time | 2026-10-28T12:30:00Z |
| Verdict | — |
| Independence | — |
| Input SHA-256 | `a4fe2a4c950bbbf2fff47931b7548a15e7289954b0b75a0c3bd6e3cd172927be` |
| Artefact SHA-256 | `b5437d8d4c3692706913991c729d868c65a977e90bd6898cb8ae673e52489b8f` |

## Lineage

- frame `f3f11099665d17b689e605f8d9cf131a04e864ece52a0137d9187b5df392b28b`

## Content

```json
{
  "termination_contract": {
    "type": "conservation",
    "achieved": "Priority hours are protected each week and deferrals land in confirmed later slots under a rule all three members adopted.",
    "outstanding": "The external-capacity option remains unverified and is kept as a contingency with an owner and a trigger.",
    "accountable": "The consortium council answers for the rule; the laboratory director runs it with ordinary staff.",
    "on_breach": "A member that books outside the rule loses priority for that slot; repeated breaches go to the council, which may suspend the trial.",
    "conservation_resources": "Half a day of coordinator time per week and the booking system's existing audit log.",
    "revision_conditions": "Review after three cycles, or earlier if essential demand exceeds 90 hours twice in a row."
  },
  "transition": [
    {
      "step": "Council adopts the criteria and the appeal path",
      "exposure": "members defer hours before seeing others comply",
      "guarantee": "deferrals are recorded and reversible after cycle 1",
      "verification": "booking log reconciled against the rule each week"
    }
  ]
}
```

## Next decision

Run the seven coherence tests on the whole plan (ante cohere).
