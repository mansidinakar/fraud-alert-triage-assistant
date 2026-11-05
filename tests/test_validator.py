import copy
from src.validator import validate_output

PACKET = {
    'alert': {'alert_id': 1, 'risk_score': 0.2},
    'transaction': {'amount': 15.247, 'device_type': 'mobile'},
    'customer': {'group_txn_count_to_date': 40, 'syn_segment': 'standard'},
    'history_30d': {'txn_count': 5},
    'prior_alerts': [],
}

GOOD = {
    'summary': 'Amount is $15.25 [transaction.amount] on a mobile device [transaction.device_type].',
    'reasons_to_escalate': ['Mobile device used [transaction.device_type]'],
    'reasons_for_false_positive': ['Small amount of $15.25 [transaction.amount]'],
    'history_reliability': 'Only 40 transactions share this profile [customer.group_txn_count_to_date].',
    'suggested_disposition': 'request_info',
    'confidence_note': 'Limited evidence, with 5 transactions in 30 days [history_30d.txn_count].',
}


def test_good_output_passes():
    assert validate_output(GOOD, PACKET)['errors'] == []


def test_unknown_field_is_an_error():
    bad = copy.deepcopy(GOOD)
    bad['summary'] = 'Merchant looks risky [transaction.merchant].'
    assert any('unknown field' in e for e in validate_output(bad, PACKET)['errors'])


def test_wrong_number_is_an_error():
    bad = copy.deepcopy(GOOD)
    bad['summary'] = 'Amount is $99.99 [transaction.amount].'
    assert any('99.99' in e for e in validate_output(bad, PACKET)['errors'])


def test_missing_citation_is_an_error():
    bad = copy.deepcopy(GOOD)
    bad['reasons_to_escalate'] = ['Looks suspicious']
    assert any('no citation' in e for e in validate_output(bad, PACKET)['errors'])


def test_verdict_word_and_synthetic_field_are_warnings_only():
    out = copy.deepcopy(GOOD)
    out['reasons_to_escalate'] = ['Possible account compromise [customer.syn_segment]']
    result = validate_output(out, PACKET)
    assert result['errors'] == []
    assert len(result['warnings']) == 2


def test_timestamps_checked_and_derived_durations_rejected():
    packet = copy.deepcopy(PACKET)
    packet['transaction']['occurred_at'] = '2018-04-21 13:07:36'
    out = copy.deepcopy(GOOD)
    out['summary'] = 'Occurred at 2018-04-21 13:07:36 [transaction.occurred_at].'
    assert validate_output(out, packet)['errors'] == []
    out['summary'] = 'Five alerts within 24 hours [transaction.occurred_at].'
    assert any('24' in e for e in validate_output(out, packet)['errors'])
