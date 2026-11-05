-- name: alert_transaction
SELECT a.alert_id, a.risk_score, a.rule_id, a.status,
       t.transaction_id, t.customer_id, t.occurred_at, t.amount,
       t.product_cd, t.card_type, t.card_class, t.addr1,
       t.email_domain, t.device_type
FROM alerts a
JOIN transactions t ON t.transaction_id = a.transaction_id
WHERE a.alert_id = ?;

-- name: customer_history_30d
SELECT COUNT(*) AS txn_count,
       SUM(h.amount) AS total_amount,
       MAX(h.amount) AS max_amount,
       COUNT(DISTINCT h.device_type) AS distinct_device_types,
       COUNT(DISTINCT h.email_domain) AS distinct_email_domains
FROM alerts a
JOIN transactions t ON t.transaction_id = a.transaction_id
JOIN transactions h ON h.customer_id = t.customer_id
WHERE a.alert_id = ?
  AND h.occurred_at >= t.occurred_at - INTERVAL '30 days'
  AND h.occurred_at < t.occurred_at;

-- name: prior_alerts
SELECT p.alert_id, p.created_at, p.risk_score, p.rule_id
FROM alerts a
JOIN alerts p ON p.customer_id = a.customer_id
             AND p.created_at < a.created_at
             AND p.alert_id <> a.alert_id
WHERE a.alert_id = ?
ORDER BY p.created_at DESC
LIMIT 5;

-- name: same_device_and_email_30d
SELECT COUNT(*) AS txn_count,
       COUNT(DISTINCT h.customer_id) AS distinct_customers
FROM alerts a
JOIN transactions t ON t.transaction_id = a.transaction_id
JOIN transactions h ON h.device_type = t.device_type
                   AND h.email_domain = t.email_domain
                   AND h.transaction_id <> t.transaction_id
                   AND h.occurred_at >= t.occurred_at - INTERVAL '30 days'
                   AND h.occurred_at < t.occurred_at
WHERE a.alert_id = ?;

-- name: customer_profile
SELECT c.syn_segment, c.syn_account_open_date
FROM alerts a
JOIN transactions t ON t.transaction_id = a.transaction_id
JOIN customers c ON c.customer_id = t.customer_id
WHERE a.alert_id = ?;

-- name: customer_group_size
SELECT COUNT(*) AS group_txn_count_to_date
FROM alerts a
JOIN transactions t ON t.transaction_id = a.transaction_id
JOIN transactions g ON g.customer_id = t.customer_id
                   AND g.occurred_at <= t.occurred_at
WHERE a.alert_id = ?;
