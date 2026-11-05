CREATE TABLE customers (
  customer_id VARCHAR PRIMARY KEY,
  syn_segment VARCHAR,
  syn_account_open_date DATE
);
CREATE TABLE transactions (
  transaction_id BIGINT PRIMARY KEY,
  customer_id VARCHAR,
  occurred_at TIMESTAMP,
  amount DOUBLE,
  product_cd VARCHAR,
  card_type VARCHAR,
  card_class VARCHAR,
  addr1 DOUBLE,
  email_domain VARCHAR,
  device_type VARCHAR,
  is_fraud INTEGER
);
CREATE TABLE alerts (
  alert_id BIGINT PRIMARY KEY,
  transaction_id BIGINT,
  customer_id VARCHAR,
  rule_id VARCHAR,
  risk_score DOUBLE,
  status VARCHAR,
  created_at TIMESTAMP
);
CREATE TABLE dispositions (
  alert_id BIGINT,
  analyst_id VARCHAR,
  decision VARCHAR,
  reason VARCHAR,
  decided_at TIMESTAMP
);
CREATE TABLE triage_outputs (
  alert_id BIGINT,
  summary_json VARCHAR,
  suggested_disposition VARCHAR,
  model_id VARCHAR,
  prompt_version VARCHAR,
  evidence_hash VARCHAR,
  created_at TIMESTAMP
);
CREATE TABLE audit_log (
  event_id BIGINT,
  alert_id BIGINT,
  actor VARCHAR,
  action VARCHAR,
  logged_at TIMESTAMP
);