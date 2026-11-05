import random
import duckdb
import pytest
from src.evidence import build_packet, DB_PATH

REQUIRED = ['alert', 'transaction', 'customer', 'history_30d',
            'prior_alerts', 'same_device_and_email_30d']


def _alert_ids(n):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    ids = [r[0] for r in con.execute('SELECT alert_id FROM alerts').fetchall()]
    con.close()
    random.seed(7)
    return random.sample(ids, n)


def test_packets_have_all_groups():
    for alert_id in _alert_ids(20):
        p = build_packet(alert_id)
        for key in REQUIRED:
            assert key in p, f'alert {alert_id} missing {key}'
        assert p['alert']['alert_id'] == alert_id
        assert 'txn_count' in p['history_30d']
        assert 'group_txn_count_to_date' in p['customer']
        assert isinstance(p['prior_alerts'], list)


def test_no_label_leak():
    for alert_id in _alert_ids(5):
        assert 'is_fraud' not in str(build_packet(alert_id))


def test_unknown_alert_raises():
    with pytest.raises(ValueError):
        build_packet(99999999)
