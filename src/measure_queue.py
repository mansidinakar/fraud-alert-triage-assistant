import math
from pathlib import Path
import duckdb
from triage_queue import get_queue

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'triage.duckdb'
con = duckdb.connect(str(DB_PATH), read_only=True)

df = con.execute("""
SELECT a.alert_id, a.created_at, t.is_fraud
FROM alerts a JOIN transactions t ON t.transaction_id = a.transaction_id
""").df()
label = dict(zip(df['alert_id'], df['is_fraud']))
total_fraud = int(df['is_fraud'].sum())

queue_order = [r['alert_id'] for r in get_queue()]
fifo_order = df.sort_values(['created_at', 'alert_id'])['alert_id'].tolist()

print('alerts:', len(df), '| confirmed-fraud alerts:', total_fraud,
      '| fraud rate in alerts:', round(df['is_fraud'].mean(), 4))
print()
print('Share of queue reviewed | recall (ranked queue) | recall (first-in-first-out)')
for pct in [0.05, 0.10, 0.20, 0.30, 0.50]:
    n = math.ceil(len(df) * pct)
    q = sum(label[a] for a in queue_order[:n]) / total_fraud
    f = sum(label[a] for a in fifo_order[:n]) / total_fraud
    print(f'{int(pct * 100):>22}% | {q:>21.3f} | {f:>26.3f}')

print()
print('Weekly fraud rate: alerts vs all transactions (from the first alert date on)')
weekly = con.execute("""
WITH start AS (SELECT MIN(created_at) AS s FROM alerts)
SELECT date_trunc('week', t.occurred_at) AS week,
       COUNT(*) AS all_txns,
       ROUND(AVG(t.is_fraud), 4) AS all_fraud_rate,
       COUNT(a.alert_id) AS alerts,
       ROUND(SUM(CASE WHEN a.alert_id IS NOT NULL THEN t.is_fraud END) * 1.0
             / NULLIF(COUNT(a.alert_id), 0), 4) AS alert_fraud_rate
FROM transactions t
LEFT JOIN alerts a ON a.transaction_id = t.transaction_id
WHERE t.occurred_at >= (SELECT s FROM start)
GROUP BY 1 ORDER BY 1
""").df()
print(weekly.to_string(index=False))
