import json
import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / 'data' / 'triage.duckdb'
SQL_PATH = ROOT / 'sql' / '02_evidence.sql'


def _load_queries():
    queries = {}
    for block in SQL_PATH.read_text().split('-- name: ')[1:]:
        name, sql = block.split('\n', 1)
        queries[name.strip()] = sql.strip().rstrip(';')
    return queries


QUERIES = _load_queries()


def _rows(con, name, alert_id):
    df = con.execute(QUERIES[name], [alert_id]).df()
    # to_json turns timestamps into text and missing values into null
    return json.loads(df.to_json(orient='records', date_format='iso'))


def build_packet(alert_id, con=None):
    """Return one evidence packet (a dict) for an alert. Never includes is_fraud."""
    own_con = con is None
    if own_con:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = _rows(con, 'alert_transaction', alert_id)
        if not rows:
            raise ValueError(f'alert {alert_id} not found')
        r = rows[0]
        profile = _rows(con, 'customer_profile', alert_id)[0]
        group = _rows(con, 'customer_group_size', alert_id)[0]
        return {
            'alert': {k: r[k] for k in ['alert_id', 'risk_score', 'rule_id', 'status']},
            'transaction': {k: r[k] for k in [
                'transaction_id', 'occurred_at', 'amount', 'product_cd', 'card_type',
                'card_class', 'addr1', 'email_domain', 'device_type']},
            'customer': {
                'customer_id': r['customer_id'],
                'syn_segment': profile['syn_segment'],
                'syn_account_open_date': profile['syn_account_open_date'],
                'group_txn_count_to_date': group['group_txn_count_to_date'],
            },
            'history_30d': _rows(con, 'customer_history_30d', alert_id)[0],
            'prior_alerts': _rows(con, 'prior_alerts', alert_id),
            'same_device_and_email_30d': _rows(con, 'same_device_and_email_30d', alert_id)[0],
        }
    finally:
        if own_con:
            con.close()


if __name__ == '__main__':
    alert_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3056
    print(json.dumps(build_packet(alert_id), indent=2))
