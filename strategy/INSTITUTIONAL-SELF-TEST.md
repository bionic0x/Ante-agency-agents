# Institutional Self-Test

> **Status**: Operating check derived from the *Marco Teórico General de la Estrategia* (developed edition, 12 September 2026), chapter VIII §13. Where the seven coherence tests examine a **plan**, this examines the **organization that produces plans** — including this repository.

Technical validation and proposal review do not establish whether the agency can hear a warning, preserve an objection, or resist its own metrics. This review requires evidence of those functions in use.

The release owner records this review before release and whenever governance changes. This is a human evidence review; CI does not execute or certify these predicates.

Each row is a predicate. Record `PASS` only with dated evidence of functioning in the declared scope, `FAIL` with evidence of failure, or `NOT_DEMONSTRATED` when evidence is insufficient. Missing evidence is not a demonstrated failure. There is no partial credit or score to sum.

| # | Failure | Institutional response | Test of functioning |
|---|---|---|---|
| 1 | The warning does not arrive | Escalation channel with a named recipient and a deadline | A critical risk reaches someone who can pause or accept it |
| 2 | Synthesis erases uncertainty | A format that preserves assumptions, alternatives, and confidence | The summary permits reconstruction of the original judgement |
| 3 | Hierarchy fixes the conclusion | Independent prior analysis and adversarial review | The strong alternative is presented before the decision, not after |
| 4 | Dissent is diluted | Mandatory record of objection and response | The record names the evidence, the disagreement, and who accepts the residual risk |
| 5 | Continuity operates by default | Stopping criteria and burden of proof fixed in advance | Leaving the validated range requires express authorization, not silence |
| 6 | The anomaly is normalized | Cumulative threshold and trend review | Repetition triggers examination of the model, not another exception |
| 7 | The metric substitutes the end | Indicators of result, harm, and gaming | Improving the number requires preserving the declared causal relation |
| 8 | The outcome rewrites the memory | Prior dated record of expectations and decisions | Evaluation compares what happened against the dated prediction |

## How to run it against this repository

For each row record the scope, evidence reference and date, result, reviewer, unresolved gap, accountable owner, and next review trigger. If an owner has not been designated, state that explicitly; an agent role name is not an appointment.

### Repository baseline — 2026-09-14, main at `2976cdb`

This baseline inspects repository artifacts and the recorded PR #7/#8 checks. It does not observe a completed institutional exercise. All eight predicates remain `NOT_DEMONSTRATED` for agency-wide operating effectiveness:

| # | Available evidence | Evidence still required |
|---|---|---|
| 1 | The control plane defines escalation and decision-owner roles | A dated critical warning, named authorized recipient, deadline and response |
| 2 | The claim register and SDR preserve status and confidence fields | A completed analysis-to-summary comparison showing uncertainty survives |
| 3 | The control plane separates author, reviewer and owner roles | Prior contrary analysis plus evidence of access, authority, incentives and effective pause capability |
| 4 | The SDR contains objection, response and residual-risk fields | A completed decision record preserving an actual objection and its disposition |
| 5 | Runbooks state stopping criteria; structured contracts are being adopted | A dated pre-commitment limit and a recorded response to leaving it |
| 6 | Runbooks and templates describe revision triggers | A trend record showing repeated anomalies changed the model or decision |
| 7 | PR #7/#8 logs support bounded installer, conversion and catalog claims | Evidence tying operational metrics to the superior outcome, including harm and gaming checks |
| 8 | Git history and CI logs date code changes and test outcomes | Prior dated strategic expectations compared with observed outcomes in the same scope |

The release owner must name the accountable reviewer and decide how each gap affects the proposed release. These unknowns prohibit a claim of institutional certification; they do not erase the narrower technical results that CI actually measured.

### Historical provenance claim: correction and scope

The supplied patch asserted that an old release workflow wrote zero lint errors without running the linter. At `2d4bff0`, that workflow contains a call to `scripts/verify-release.sh` before writing hard-coded provenance values. Establishing which tests actually ran requires the script version and execution logs from that run. Hard-coded values alone do not prove the linter was skipped or establish failures of rows 7 and 8.

PR #7 removed that obsolete bootstrap workflow. PR #8 made catalog and conversion drift checks strict before merge. Neither change by itself proves institutional functioning. Likewise, a dissent field in a template is evidence of a recording mechanism, not evidence that dissent was preserved in practice.

## What this check does not do

It does not score the organization, and it does not convert into a percentage. Rows interact — an inadequate metric (7) produces local successes that feed commitment escalation, and that escalation makes criticism read as disloyalty, which closes the channel in row 1. Repair the relation that holds the set together, not each symptom in isolation.

A passing row is not a permanent property. Each one describes a capability that decays when attention moves elsewhere, which is why this file is run per release rather than certified once.
