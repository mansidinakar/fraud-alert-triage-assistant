# Product memo: Fraud Alert Triage Assistant

## Bottom line

The assistant drafts an evidence-cited summary for each fraud alert and the analyst decides. It is good enough to demo and measure, but not good enough to pilot. Of the four PRD targets I could measure, three were missed. On the 100 alerts I reviewed by hand, only 25 summaries had every claim supported. The most useful finding is where it fails: not on the numbers, but in inference and framing, such as reading a missing value as reassurance.

## The user and the decision

The user is a Tier-1 fraud analyst clearing a queue of card-not-present alerts. For each alert they decide one of three things: escalate, request more information, or close as a false positive. Today the time goes into gathering context from several tables before they can judge. The product assembles that context into one view and drafts an explanation, but it never closes or blocks anything on its own. That is an explicit non-goal in the PRD.

## What it does

1. Builds an evidence packet per alert from SQL (transaction, customer history, same device and email activity, prior alerts). The fraud label is never included.
2. Asks Claude Haiku 4.5 for a structured summary where every statement cites packet fields.
3. Validates the output in code. On failure it tries one repair, and if that fails the analyst sees the raw evidence instead.
4. Shows the analyst the summary next to the cited evidence. No decision is pre-selected, and disagreeing with the model requires a written reason.

## Scorecard against the PRD targets

| PRD target | Result | Status |
|---|---|---|
| Time to disposition, 50% lower | No analyst time study was run | Not measured |
| Priority-queue recall, 90% or more in the top 20% | 32.8% (first-in-first-out: 22.4%), over 8,858 alerts with 2,041 confirmed fraud | **Missed** |
| Summary faithfulness, 98% or more | 25 of 100 summaries had every claim supported (95% interval 18 to 34%). At claim level, 87.6% | **Missed** |
| Analyst override rate, reported weekly | No real analysts, so no data. The screen and audit log record it | Not measured |
| Latency, p95 under 8 s | p50 4.2 s, p95 11.0 s on AWS | **Missed** |
| Cost per alert, under $0.05 | About $0.005 in model cost at list prices ($1 and $5 per million tokens, from third-party price trackers). Infrastructure cost excluded, AWS bill pending | Likely met |

## What the misses tell me

- **Queue ordering is not where the value is.** Reviewing the first 20% of the ranked queue catches 32.8% of confirmed fraud, against 22.4% in arrival order. The 90% target was set without a baseline and was unrealistic for this score. I now treat prioritization as unproven and leave it out of my claims.
- **A passing validator is not a faithfulness number.** The validator accepts outputs a human still finds unsupported, so I report the human check and the validator separately.
- **The failures are in inference.** The assistant cites a history it has itself called unreliable (37 of 100 reviewed alerts), treats a missing device type as reassurance, and miscounts. `docs/walkthrough.md` shows five examples.
- **The model leans toward escalate** (127 of 163 stored outputs). I had no ground truth to say whether that is right.

## Guardrails

- Validator plus fallback to raw evidence, so a bad summary never replaces the evidence.
- The analyst always makes the call. Overrides need a reason, and each alert gets one decision.
- Every decision is written to an audit log together with the stored output, prompt version and model id, so a result can be replayed.
- The fraud label and synthetic fields never reach the model or the API output.

## Where the build differs from the PRD

- The deployed diagram uses a server (EC2), not Lambda, and the data stayed in DuckDB on the instance instead of a database in a private subnet.
- A CloudWatch log agent was planned and skipped.
- Streamlit was chosen over React, and Claude Haiku 4.5 on Bedrock was the model.
- Whether to run a public demo or share a recorded walkthrough is still open.

## Proposed stop criteria

These are decision rules I would set before any pilot. They are proposals, not measurements, and the thresholds would be agreed with the operations manager.

- **No pilot with real analysts** until a re-run of the same 100 alerts, after the v3 changes, shows more summaries with every claim supported than the 25 measured here, and I can explain the ones that remain.
- **No time-saved claim** until a time study with real analysts exists, even a small one.
- **If v3 does not improve faithfulness**, stop adding features and test a different format, such as shorter and more structured outputs, before anything else.
- **Every close recommendation an analyst later reverses** is reviewed individually, because closing is the action that ends review.

## Next steps

1. Implement the v3 changes listed in `docs/results.md` and re-run the same 100 alerts.
2. Run a small time study with at least one real reviewer.
3. Revisit the queue-ranking target with a baseline, or drop it.
4. Replace the assumed baselines in the PRD's problem section with cited industry figures before going public.
