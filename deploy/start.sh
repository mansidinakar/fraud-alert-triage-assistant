#!/bin/bash
cd /home/ssm-user/app
source .venv/bin/activate
export AWS_REGION=us-east-2
export API_TOKEN=$(aws secretsmanager get-secret-value --secret-id fraud-triage/api-token --region us-east-2 --query SecretString --output text)
exec "$@"
