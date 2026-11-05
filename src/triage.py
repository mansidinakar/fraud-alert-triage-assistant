import json
import sys

try:
    from src.summarize import summarize_alert
    from src.validator import validate_output
except ImportError:
    from summarize import summarize_alert
    from validator import validate_output


def triage_alert(alert_id, prompt_version="triage_v2"):
    """Summarize, validate, and decide: show the AI summary or fall back to raw evidence."""
    r = summarize_alert(alert_id, prompt_version=prompt_version)
    if r['output'] is None:
        r['validation'] = {'errors': [r['error']], 'warnings': []}
    else:
        r['validation'] = validate_output(r['output'], r['packet'])
    r['status'] = 'ok' if not r['validation']['errors'] else 'fallback'
    r['display'] = r['output'] if r['status'] == 'ok' else None
    return r


if __name__ == '__main__':
    alert_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3056
    r = triage_alert(alert_id)
    print('status:', r['status'])
    print(json.dumps(r['validation'], indent=2))
