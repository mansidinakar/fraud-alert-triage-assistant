from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / 'data' / 'triage.duckdb'

QUEUE_SQL = """
SELECT alert_id, transaction_id, customer_id, risk_score, status, created_at
FROM alerts
WHERE status = ?
ORDER BY risk_score DESC, created_at ASC, alert_id ASC
"""


def get_queue(limit=None, status='open', con=None):
    """Return alerts as a list of dicts: highest risk first, older alert first on ties."""
    own_con = con is None
    if own_con:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        sql = QUEUE_SQL + (f' LIMIT {int(limit)}' if limit else '')
        return con.execute(sql, [status]).df().to_dict('records')
    finally:
        if own_con:
            con.close()


if __name__ == '__main__':
    for row in get_queue(limit=10):
        print(row['alert_id'], round(row['risk_score'], 4), row['created_at'])
