# Fraud Alert Triage Assistant — PRD

Nov 4, 2026

*Status: this is the original scope, written before the build. What was built and measured against these targets is in `docs/product_memo.md` and `docs/results.md`.*

## Overview

The Fraud Alert Triage Assistant helps Tier-1 fraud analysts clear transaction-monitoring alerts faster by scoring each alert, summarizing the evidence in plain language and recommending a disposition, while a human always makes the final call.

It is a portfolio project built on a real, anonymized public fraud dataset (IEEE-CIS), with a small, clearly labeled synthetic layer for fields the dataset lacks. Python runs the pipeline and API, SQL holds the alert data model, a generative AI layer writes case summaries and rationale, and AWS hosts it. The PRD is written the way a fintech product manager would scope it: problem first, measurable goals, explicit non-goals, and a staged plan.

## Problem and opportunity

Rules-based fraud monitoring is commonly described as raising more alerts than analysts can investigate carefully, with most turning out to be legitimate activity. This is an assumption in this PRD, not a cited figure. Each alert still costs analyst time, because the evidence is spread across transaction history, customer profile, device and prior-case records.

Three consequences follow:

- Analysts spend most of each alert gathering context rather than judging it.
- Queue order is first-in-first-out, so genuinely risky alerts can wait behind benign ones.
- Dispositions are written inconsistently, which makes audit and model-tuning feedback weak.

The opportunity is to order the queue by risk, assemble the evidence automatically and draft a grounded explanation, so analysts spend their time deciding rather than searching.

**Note on baselines:** the targets in this PRD were set for the public dataset and are not taken from industry benchmarks. Statements about industry alert volumes are assumptions.

## Users and personas

The primary user is the Tier-1 analyst; the other two roles shape the controls and reporting.

| Persona | Job to be done | What they need from the product |
| --- | --- | --- |
| Tier-1 fraud analyst (primary) | Clear a queue of alerts accurately and quickly | Risk-ranked queue, evidence in one view, a draft summary and suggested disposition they can accept or edit |
| Fraud operations manager | Keep queue age and backlog under control | Throughput, aging and override-rate dashboards; ability to tune routing thresholds |
| Model risk / compliance reviewer | Prove decisions are explainable and auditable | Immutable log of inputs, model version, prompt version, output and the analyst's final decision |

## Goals, non-goals and success metrics

The MVP succeeds if it cuts handling time and surfaces real fraud earlier without lowering decision quality. Targets are proposed and measured on the public dataset.

| Metric | Definition | Target |
| --- | --- | --- |
| Time to disposition | Median minutes from alert opened to disposition saved, assisted vs unassisted | 50% lower |
| Priority-queue recall | Share of confirmed-fraud alerts that land in the top 20% of the ranked queue | 90% or higher |
| Summary faithfulness | Share of sampled summaries where every claim traces to a source field | 98% or higher |
| Analyst override rate | Share of suggested dispositions changed by the analyst (tracked, not minimized: it is the feedback signal) | Reported weekly |
| Latency | p95 time from opening an alert to a rendered summary | Under 8 seconds |
| Cost per alert | Model and infrastructure cost per triaged alert | Under $0.05 |

**Non-goals for the MVP**

- Automatically closing or blocking anything without an analyst decision.
- Replacing the upstream rules engine or fraud model.
- Handling any institution's real customer data or production card networks; only a public, anonymized dataset is used.
- Covering AML or sanctions alerts; the MVP covers card-not-present fraud only.

## Scope and phasing

The MVP delivers a ranked queue with grounded summaries for one fraud type; later phases add learning from analyst feedback and wider coverage.

| Phase | In scope | Out of scope until later |
| --- | --- | --- |
| MVP | Public-data loader with synthetic enrichment, SQL schema, risk scoring, evidence assembly, LLM summary and suggested disposition, analyst review screen, audit log | Feedback-driven retraining, multiple fraud types |
| v2 | Analyst feedback loop into scoring, similar-case retrieval, manager dashboard | Real-time streaming ingestion |
| v3 | Streaming ingestion, A/B test of routing thresholds, AML alert types | Production deployment with real data |

## Functional requirements

P0 items are required for the MVP; P1 items follow if time allows.

| ID | User story | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| F1 | As an analyst, I see alerts ordered by risk score | P0 | Queue sorts by score descending; ties break by alert age |
| F2 | As an analyst, I see all evidence for an alert on one screen | P0 | Shows the transaction, 30-day customer history, device and product-code history, and prior alerts, each pulled by SQL |
| F3 | As an analyst, I get a plain-language summary of why the alert was flagged | P0 | Every claim in the summary cites a source field; no field outside the evidence packet is mentioned |
| F4 | As an analyst, I get a suggested disposition (escalate, close as false positive, request info) with a rationale | P0 | Suggestion is advisory; analyst must confirm or change it before saving |
| F5 | As a reviewer, I can reconstruct any decision | P0 | Log stores inputs, model and prompt version, output, analyst decision and timestamps |
| F6 | As an analyst, I can flag a summary as wrong | P1 | One-click flag with a reason; flagged items feed the evaluation set |
| F7 | As a manager, I see throughput, queue age and override rate | P1 | Dashboard refreshes from the dispositions table |
| F8 | As an analyst, I can see similar past cases | P1 | Top 3 prior cases by feature similarity, with their final dispositions |

## Data model and SQL

A relational schema in PostgreSQL (Amazon RDS) keeps evidence queries explicit and auditable. Six tables cover the MVP:

| Table | Purpose |
| --- | --- |
| customers | Customer entity derived from card and address fields, with synthetic profile attributes |
| transactions | Public-dataset transactions with product code, card type, amount, address, email domain, device id |
| alerts | One row per alert, created by thresholding a model score over transactions, with rule id and risk score |
| dispositions | Analyst decision per alert, with timestamp and analyst id |
| triage_outputs | Generated summary, suggested disposition, model id, prompt version, evidence hash |
| audit_log | Append-only record of every read and write that touches an alert |

```sql
CREATE TABLE alerts (
  alert_id        BIGSERIAL PRIMARY KEY,
  transaction_id  BIGINT NOT NULL REFERENCES transactions(transaction_id),
  customer_id     BIGINT NOT NULL REFERENCES customers(customer_id),
  rule_id         TEXT NOT NULL,
  risk_score      NUMERIC(5,4) NOT NULL,
  status          TEXT NOT NULL DEFAULT 'open',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Evidence query: 30-day history for the alert's customer
SELECT t.transaction_id, t.amount, t.product_cd, t.card_type, t.occurred_at
FROM transactions t
JOIN alerts a ON a.customer_id = t.customer_id
WHERE a.alert_id = :alert_id
  AND t.occurred_at >= a.created_at - INTERVAL '30 days'
ORDER BY t.occurred_at DESC;
```

The evidence packet sent to the model is built only from queries like the one above, so the model never sees a field the analyst cannot also see. Many IEEE-CIS columns are masked, so the packet uses only interpretable fields (amount, product code, card type, address, email domain, device) plus derived velocity counts.

## Solution architecture

*[Diagram: solution architecture, 7 components on AWS. See the PRD doc for the drawing; export it as an image for the README.]*

Synthetic data lands in S3 and a loader fills RDS. The triage API scores alerts, builds each evidence packet with SQL and calls Bedrock; analysts work only through the review UI, which also writes their dispositions back through the API.

## Generative AI design

The model explains and drafts; it does not decide. Scoring stays in Python so the ranking is deterministic and testable.

- **Grounding:** the prompt contains only the evidence packet, as labeled fields. The model must cite a field name for each claim and say "not in evidence" when something is missing.
- **Structured output:** the model returns JSON with a summary, up to three risk factors, a suggested disposition from a fixed list, and a confidence note. Python validates the schema and rejects anything else.
- **Guardrails:** a post-check verifies that every cited field exists in the packet and every number in the text matches the data; failures fall back to showing raw evidence with no summary.
- **Human in the loop:** the analyst must confirm or change the suggestion before a disposition is saved.
- **Privacy:** only anonymized public values or labeled synthetic enrichment reach the model; identifier-style fields are tokenized before the prompt is built.
- **Evaluation:** a labeled set of about 200 synthetic alerts tracks faithfulness, disposition agreement with the ground-truth label, and refusal behavior on thin evidence. Prompt and model changes ship only if the set does not regress.
- **Versioning:** prompt text and model id are stored with every output so any decision can be replayed.

## Non-functional requirements

| Area | Requirement |
| --- | --- |
| Security | Private subnets for the database, secrets in AWS Secrets Manager, least-privilege IAM roles, encryption at rest and in transit |
| Privacy | Public anonymized data plus labeled synthetic enrichment only; no real customer data; identifier-style fields tokenized before reaching the model |
| Auditability | Append-only audit_log; every output replayable from stored inputs, prompt version and model id |
| Performance | p95 under 8 seconds from alert open to rendered summary |
| Cost | Under $0.05 per triaged alert; monthly AWS budget alarm |
| Reliability | If the model call fails or fails validation, the analyst still sees the ranked queue and raw evidence |
| Observability | CloudWatch logs and metrics for latency, validation failures and token usage |

## Risks, assumptions and open questions

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Model states something not in the evidence | Medium | Field-citation requirement, post-check validator, fallback to raw evidence |
| Masked features and missing merchant names limit what summaries can say, and the synthetic layer is not real | High | Keep enrichment labeled and separate; limit claims to real fields; say so in the write-up |
| Analysts over-trust the suggestion | Medium | Require explicit confirmation; show confidence and missing evidence; track override rate |
| AWS cost creep | Low | Budget alarm, small instance sizes, cap tokens per call |

**Open questions**

- [ ] Do the Kaggle competition rules allow this use in a public portfolio? Keep the data out of the repo and load it through the Kaggle API.
- [ ] Which model on Amazon Bedrock, given cost and latency targets?
- [ ] Analyst UI: Streamlit for speed, or a small React app for polish?
- [ ] Is a public demo wanted, or a recorded walkthrough plus repo?

## Milestones and build plan

*[Diagram: build plan, 4 phases, 4 gates. See the PRD doc for the drawing.]*

Each gate is a pass-or-fail check against the metrics in the goals table, so the project can stop at any gate with a coherent deliverable.
