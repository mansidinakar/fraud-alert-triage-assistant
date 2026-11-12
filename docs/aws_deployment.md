# AWS deployment

A one-day deployment to check that the triage API and analyst screen run in a locked-down cloud setup, and to measure latency and token use on real infrastructure. It was torn down afterwards and verified empty.

## What was deployed (us-east-2)

- One EC2 instance (t4g.small, Amazon Linux 2023 arm64, 20 GB encrypted disk) running the API and the Streamlit screen as two services. DuckDB sat on the instance disk.
- One private S3 bucket with public access blocked, used only to move code and the database onto the server.
- One IAM role for the instance. Its inline policy allows only: invoking the one pinned Claude Haiku 4.5 model on Bedrock, reading and writing the one bucket, and reading the one secret. See `docs/iam_policy.json` (account ID redacted).
- The API token lived in Secrets Manager and was fetched when each service started. No keys were stored on the server. Bedrock was called through the instance role.

## Access and hardening

- The security group had no inbound rules. Nothing on the internet could connect to the instance.
- The only way in was an SSM Session Manager tunnel to the Streamlit port, so access required being signed in to the AWS account.
- Both services bound to localhost. The metadata service required IMDSv2.
- Setup files used on the server are in `deploy/` (launcher script, two service definitions, server-only requirements).

## Measured run

200 alerts, prompt `triage_v2`, run on the instance through the IAM role (4 parallel workers):

| Measure | Result |
|---|---|
| Passed validation (after repair) | 164 of 200 (82%) |
| Fell back to raw evidence | 36 of 200 |
| Latency, all 200: p50 / p95 | 4,234 ms / 10,974 ms |
| Latency, passed only: p50 / p95 | 4,055 ms / 11,535 ms |
| Tokens | 431,342 input / 116,848 output |

The 8 s p95 target in the PRD was **not met**. Latency was about the same as the run on a laptop (p95 9,889 ms there), so the delay comes from the model calls, not the network. I have not yet checked whether the slowest calls are the ones that needed a repair; that is the first thing to look at for v3.

## Cost

Filled in from Cost Explorer once charges post (about a day after teardown). See `docs/aws_cost.md`.

## Trade-offs and what was not done

- DuckDB on one instance is fine for one analyst, but it allows a single writer and no failover. A real team deployment would use a managed Postgres, at the price of more cost and a data migration.
- A CloudWatch agent for logs was planned and skipped. Service logs stayed in the system journal and were deleted with the instance.
- One instance means no high availability.
- The Bedrock model ID is pinned. Model versions get retired, so this would need a migration step later.
- Teardown deleted the instance, security group, bucket, secret and role. A check afterwards showed none of them remained.
