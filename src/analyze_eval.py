import json
import re
from collections import Counter

import numpy as np

PRICE_IN, PRICE_OUT = 1.00, 5.00  # USD per million tokens, Haiku 4.5 (verify in the Bedrock model catalog)
rows = [json.loads(l) for l in open('data/eval_results.jsonl')]


def category(e):
    e = e or ''
    if 'no citation' in e: return 'missing citation'
    if 'unknown field' in e: return 'unknown field path'
    if 'timestamp' in e or 'date' in e: return 'date/timestamp not in evidence'
    if 'number' in e: return 'number not in evidence'
    return 'parse/other: ' + e[:50]


for ver in ['triage_v1', 'triage_v2']:
    rs = [r for r in rows if r['prompt_version'] == ver]
    n = len(rs)
    print(f'\n===== {ver}  (n={n}) =====')
    first_ok = sum(r['first_pass_status'] == 'ok' for r in rs)
    final_ok = sum(r['status'] == 'ok' for r in rs)
    repaired = sum(r['first_pass_status'] == 'fallback' and r['status'] == 'ok' for r in rs)
    print(f'first-pass validated: {first_ok}/{n} = {first_ok/n:.1%}')
    print(f'validated after repair: {final_ok}/{n} = {final_ok/n:.1%}  (repair rescued {repaired})')

    lat = np.array([r['latency_ms'] for r in rs if r['latency_ms']])
    print(f'latency ms: mean {lat.mean():.0f} | p50 {np.percentile(lat,50):.0f} | p95 {np.percentile(lat,95):.0f}')
    single = np.array([r['latency_ms'] for r in rs if r['latency_ms'] and r['attempts'] == 1])
    if len(single):
        print(f'  single-attempt only: p50 {np.percentile(single,50):.0f} | p95 {np.percentile(single,95):.0f}')
    tin = sum(r['input_tokens'] or 0 for r in rs)
    tout = sum(r['output_tokens'] or 0 for r in rs)
    cost = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
    print(f'tokens/alert: in {tin/n:.0f}, out {tout/n:.0f} | est. cost/alert ${cost/n:.5f} (total ${cost:.2f})')

    cats = Counter()
    for r in rs:
        if r['status'] == 'fallback':
            for e in (r['validation']['errors'] or []):
                cats[category(e)] += 1
    print('final-fallback error types (count of errors):', dict(cats.most_common()))
    warn = Counter()
    for r in rs:
        for w in r['validation']['warnings']:
            warn[re.sub(r'^[^:]+: ', '', w)] += 1
    print('top warnings:', dict(warn.most_common(5)))

    for label, name in [(1, 'confirmed fraud'), (0, 'not fraud')]:
        g = [r for r in rs if r['is_fraud'] == label]
        ok = [r for r in g if r['status'] == 'ok']
        esc = sum(r['output']['suggested_disposition'] == 'escalate' for r in ok)
        print(f'{name}: n={len(g)}, validated {len(ok)/len(g):.1%}, '
              f'escalate suggested on {esc}/{len(ok)} validated ({esc/max(len(ok),1):.1%})')
