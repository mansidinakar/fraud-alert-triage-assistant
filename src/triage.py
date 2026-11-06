import json
import sys

try:
    from src.summarize import summarize_alert
    from src.validator import validate_output
except ImportError:
    from summarize import summarize_alert
    from validator import validate_output


def _attempt(alert_id, prompt_version, feedback=None):
    r = summarize_alert(alert_id, prompt_version=prompt_version, feedback=feedback)
    if r['output'] is None:
        r['validation'] = {'errors': [r['error']], 'warnings': []}
    else:
        r['validation'] = validate_output(r['output'], r['packet'])
    r['status'] = 'ok' if not r['validation']['errors'] else 'fallback'
    return r


def triage_alert(alert_id, prompt_version='triage_v2', repair=None):
    """Summarize, validate, repair once on failure, else fall back to raw evidence.
    v1 is the single-shot baseline, so it never repairs."""
    if repair is None:
        repair = prompt_version != 'triage_v1'
    r = _attempt(alert_id, prompt_version)
    r['attempts'] = 1
    r['first_pass_status'] = r['status']

    if repair and r['status'] == 'fallback' and r['raw_text']:
        feedback = (
            '\n\nYour previous answer:\n' + r['raw_text'] +
            '\n\nIt failed validation:\n- ' + '\n- '.join(r['validation']['errors']) +
            '\n\nReturn a corrected JSON object. Remove or rewrite every flagged claim. '
            'Do not state durations or computed numbers, and cite the full field path after every sentence.'
        )
        r2 = _attempt(alert_id, prompt_version, feedback)
        for k in ('input_tokens', 'output_tokens', 'latency_ms'):
            r2[k] = (r2[k] or 0) + (r[k] or 0)
        r2['attempts'] = 2
        r2['first_pass_status'] = 'fallback'
        r = r2

    r['display'] = r['output'] if r['status'] == 'ok' else None
    return r


if __name__ == '__main__':
    alert_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3056
    r = triage_alert(alert_id)
    print('status:', r['status'], '| attempts:', r['attempts'], '| first pass:', r['first_pass_status'])
    print(json.dumps(r['validation'], indent=2))
