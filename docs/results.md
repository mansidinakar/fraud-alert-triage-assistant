# Results

All figures were measured on the IEEE-CIS data with the pipeline in this repo (Claude Haiku 4.5 on Amazon Bedrock, temperature 0). Where a number is weak, the limitation is stated next to it.

## 1. Validator results (200 alerts)

| | v1 baseline | v2 strict prompt |
|---|---|---|
| Passed validator on first try | 8.5% | 39.0% |
| Passed after one repair attempt | n/a | 81.5% (163/200) |

v2 latency: p50 4256 ms, p95 9889 ms. The PRD target is p95 <= 8 s, so this target is missed before AWS deployment. On AWS EC2 (200 alerts) it was p50 4234 ms, p95 10974 ms, so the target is still missed.

The validator checks that every cited path exists, that numbers and dates appear in the evidence packet, and that every field carries a citation. It cannot check whether a statement is true or fairly framed.

## 2. Human faithfulness check (100 validated v2 outputs)

One reviewer scored 100 outputs, with AI-assisted adjudication on the first pass. Rubric: count wrong or unsupported statements in the summary, history_reliability, escalate and false-positive lines.

- Claim-level faithfulness: 87.6% (112 unsupported of 902 claims). The PRD defines the 98% target per summary (every claim supported), and by that definition 25 of 100 summaries passed, so it is missed.
- Summaries with zero unsupported claims: 25/100 (95% CI 18%-34%).
- Summaries judged misleading in framing: 66/100 (95% CI 56%-75%). See section 3 for why this label is low-reliability.
- Suggested disposition judged sensible from the evidence alone: 33 yes, 67 unsure, 0 no. There is no ground truth for this, so it is weak evidence.

The validator accepted all 100 of these outputs, yet only 25 had no unsupported claim. A validator pass rate overstates how faithful the summaries are.

## 3. Reliability of the human labels

Ten cases (seed 11) were re-scored blind on the same day.

- Unsupported-claim counts: exact match 2/10, within one claim 6/10, mean absolute difference 1.20. The totals matched (16 vs 16).
- Misleading Y/N: agreement 5/10, Cohen's kappa -0.09.

With n=10 these are noisy, and the first pass was adjudicated with AI help while the second was solo. The misleading label is not reproducible, so it is reported but not relied on. A second reviewer was not used.

## 4. Code-counted failure patterns

Counted by fixed rules over the saved v2 outputs that passed the validator. Counts are per alert, and one alert can have several patterns. "Exact" means a fixed rule; "proxy" means a keyword rule that needs manual confirmation.

| Pattern | Sample (n=100) | All validated v2 (n=163) | Type |
|---|---|---|---|
| Says "coarse" when the customer group has 500 or fewer transactions | 37 (28%-47%) | 59 (29%-44%) | Exact |
| Says history is coarse or shared, then escalates on history_30d | 37 (28%-47%) | 66 (33%-48%) | Exact rule, spot-checked on 3 alerts |
| Judgment word (low, moderate, modest, small, routine) inside a reason | 31 (23%-41%) | 47 (22%-36%) | Proxy |
| States a computed duration despite the prompt banning it | 13 (8%-21%) | 17 (7%-16%) | Exact |
| Adds USD or $ (the evidence has no currency) | 3 (1%-8%) | 11 (4%-12%) | Exact |
| Comparison words (lowest, highest, matches, below all) | 11 (6%-19%) | 18 (7%-17%) | Proxy |
| "N prior alerts" differs from the number of prior alerts | 2 (1%-7%) | 4 (1%-6%) | Proxy |
| Mentions device when device_type is missing | 6 (3%-12%) | 9 (3%-10%) | Exposure, not proven error |
| Two or more prior alerts with identical risk_score | 31 (23%-41%) | 53 (26%-40%) | Input data property |

Percent ranges are 95% Wilson intervals. Computed durations are not always false; they are counted because the prompt banned them.

## 5. Limitations

- One reviewer, small re-score, and no second reviewer (sections 2 and 3).
- Disposition quality has no ground truth.
- The sample is drawn from outputs that passed the validator, so it says nothing about the 37 alerts that fell back to raw evidence.
- Latency misses the 8 s p95 target before AWS deployment.
- Near-duplicate prior alerts come from the synthetic alert history, not from the model.

## 6. Planned v3 changes

- Code checks for "coarse" on small groups, computed durations, currency, and comparison claims.
- Reject output where history is called coarse or shared and history_30d is still used as an escalate reason.
- Treat a missing device as missing, not as clean.
- Deduplicate near-identical prior alerts before building the packet.
- Re-run the same 100 alerts and compare the pattern counts before and after.
