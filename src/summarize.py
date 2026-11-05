import json
import re
from pathlib import Path
from typing import List

from pydantic import BaseModel

try:
    from src.evidence import build_packet
    from src.llm import complete
except ImportError:
    from evidence import build_packet
    from llm import complete

PROMPT_DIR = Path(__file__).parent / 'prompts'
DEFAULT_VERSION = 'triage_v2'


class TriageOutput(BaseModel):
    summary: str
    reasons_to_escalate: List[str]
    reasons_for_false_positive: List[str]
    history_reliability: str
    suggested_disposition: str
    confidence_note: str


def _strip_synthetic(node):
    """Remove every key starting with syn_ so the model never sees synthetic fields."""
    if isinstance(node, dict):
        return {k: _strip_synthetic(v) for k, v in node.items() if not k.startswith('syn_')}
    if isinstance(node, list):
        return [_strip_synthetic(v) for v in node]
    return node


def _extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError('no JSON object in model output')
    return json.loads(match.group(0))


def summarize_alert(alert_id, packet=None, prompt_version=DEFAULT_VERSION):
    full_packet = packet if packet is not None else build_packet(alert_id)
    # v1 saw everything (baseline); v2 sees the packet without synthetic fields
    llm_packet = full_packet if prompt_version == 'triage_v1' else _strip_synthetic(full_packet)
    system = (PROMPT_DIR / f'{prompt_version}.txt').read_text()
    user = 'Evidence packet:\n' + json.dumps(llm_packet, indent=2)

    result = {
        'alert_id': alert_id,
        'prompt_version': prompt_version,
        'packet': llm_packet,
        'raw_text': None,
        'output': None,
        'error': None,
        'input_tokens': None,
        'output_tokens': None,
        'latency_ms': None,
        'model_id': None,
    }
    try:
        r = complete(system, user, max_tokens=500)
        result.update(raw_text=r['text'], input_tokens=r['input_tokens'],
                      output_tokens=r['output_tokens'], latency_ms=r['latency_ms'],
                      model_id=r['model_id'])
        result['output'] = TriageOutput(**_extract_json(r['text'])).model_dump()
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {e}'
    return result


if __name__ == '__main__':
    import sys
    aid = int(sys.argv[1]) if len(sys.argv) > 1 else 3056
    ver = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VERSION
    out = summarize_alert(aid, prompt_version=ver)
    print(json.dumps({k: v for k, v in out.items() if k != 'packet'}, indent=2))
