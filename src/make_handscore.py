import csv
import html
import json
import random
import re

rows = [json.loads(l) for l in open('data/eval_results.jsonl')]
v2 = [r for r in rows if r['prompt_version'] == 'triage_v2' and r['status'] == 'ok']
rng = random.Random(7)
sample = rng.sample([r for r in v2 if r['is_fraud'] == 1], 40) + rng.sample([r for r in v2 if r['is_fraud'] == 0], 60)
rng.shuffle(sample)


def flatten(node, prefix=''):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from flatten(v, f'{prefix}.{k}' if prefix else k)
    elif isinstance(node, list):
        if not node:
            yield prefix, '[]'
        for i, v in enumerate(node):
            yield from flatten(v, f'{prefix}[{i}]')
    else:
        yield prefix, node


def fields(o):
    parts = [('summary', o['summary']), ('history_reliability', o['history_reliability']),
             ('confidence_note', o['confidence_note'])]
    parts += [('escalate', t) for t in o['reasons_to_escalate']]
    parts += [('false positive', t) for t in o['reasons_for_false_positive']]
    return parts


css = ('body{font-family:system-ui;margin:24px;max-width:1300px}'
       '.case{border:1px solid #ccc;border-radius:8px;margin:18px 0;padding:14px}'
       '.g{display:grid;grid-template-columns:1fr 1fr;gap:18px}'
       'table{border-collapse:collapse;font-size:12px}td{padding:1px 8px;border-bottom:1px solid #eee;vertical-align:top}'
       'td:first-child{color:#555;white-space:nowrap}.s b{color:#555}.s p{margin:6px 0}')
out = [f'<html><head><meta charset="utf-8"><style>{css}</style></head><body><h2>Hand-scoring: 100 summaries</h2>']
with open('data/handscore.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['case', 'alert_id', 'n_claims', 'unsupported_claims', 'misleading_framing_Y_N',
                'disposition_sensible_Y_N_unsure', 'notes'])
    for i, r in enumerate(sample, 1):
        o = r['output']
        n_claims = sum(len(re.findall(r'\[[^\]]+\]', t)) for _, t in fields(o))
        w.writerow([i, r['alert_id'], n_claims, '', '', '', ''])
        ev = ''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>' for k, v in flatten(r['packet']))
        sm = ''.join(f'<p><b>{html.escape(k)}:</b> {html.escape(t)}</p>' for k, t in fields(o))
        out.append(f'<div class="case"><h3>Case {i} (alert {r["alert_id"]}) · claims: {n_claims}</h3><div class="g">'
                   f'<div><b>Evidence packet</b><table>{ev}</table></div>'
                   f'<div class="s"><b>AI summary</b>{sm}<p><b>suggested disposition:</b> {html.escape(o["suggested_disposition"])}</p></div>'
                   f'</div></div>')
out.append('</body></html>')
open('data/handscore.html', 'w').write(''.join(out))
print('wrote data/handscore.html and data/handscore.csv with', len(sample), 'cases')
