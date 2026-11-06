import csv
import html
import json
import os
import random
import re
from datetime import datetime

rows = [json.loads(l) for l in open('data/eval_results.jsonl')]
v2 = [r for r in rows if r['prompt_version'] == 'triage_v2' and r['status'] == 'ok']
rng = random.Random(7)  # same sampling code as make_handscore.py, so cases line up
sample = rng.sample([r for r in v2 if r['is_fraud'] == 1], 40) + rng.sample([r for r in v2 if r['is_fraud'] == 0], 60)
rng.shuffle(sample)

CITE = re.compile(r'\[([^\]]+)\]')
UNIT = {'minute': 60, 'hour': 3600, 'day': 86400}
NUMW = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
STOP = {'risk', 'score', 'alert', 'transaction', 'amount', 'max', 'maximum', 'd', 'day', 'days', 'compared',
        'to', 'is', 'the', 'of', 'customer', 'group', 'total', 'transactions', 'count', 'history', 'in', 'a', 'an', 'and'}


def clean(t):
    return CITE.sub('', t)


def fmt(sec):
    d, r = divmod(int(sec), 86400)
    h, r = divmod(r, 3600)
    return f'{d}d {h}h {r // 60}m'


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


def analyze(r):
    o, p = r['output'], r['packet']
    prior = p['prior_alerts']
    group = p['customer']['group_txn_count_to_date']
    texts = [('summary', o['summary']), ('history_reliability', o['history_reliability']),
             ('confidence_note', o['confidence_note'])]
    esc = [('escalate', t) for t in o['reasons_to_escalate']]
    fp = [('false positive', t) for t in o['reasons_for_false_positive']]
    texts += esc + fp
    unsupported, misleading, info = [], [], []

    # 1. computed durations, checked against the real timestamps
    times = sorted(datetime.fromisoformat(a['created_at']) for a in prior)
    span = (times[-1] - times[0]).total_seconds() if len(times) >= 2 else None
    for name, t in texts:
        for m in re.finditer(r'(\d+)\s*(minute|hour|day)s?', clean(t)):
            n, unit = int(m.group(1)), m.group(2)
            if n == 30 and unit == 'day':
                continue  # the 30-day window, not a computed duration
            if span is None:
                info.append(f'{name}: duration "{m.group(0)}" cannot be checked (fewer than 2 prior alerts)')
            elif span <= n * UNIT[unit]:
                info.append(f'{name}: duration "{m.group(0)}" is TRUE (actual span {fmt(span)}), but the model computed it; note it')
            else:
                unsupported.append(f'{name}: duration "{m.group(0)}" is FALSE (actual span of prior alerts {fmt(span)})')

    for name, t in esc + fp:
        low = clean(t)
        words = re.findall(r'[A-Za-z_]+', low)
        # 2. judgment as the whole reason
        if re.search(r'\b(low|high|unusual|normal|moderate|extreme|typical|average|common|significant|elevated|modest|minor|serious|substantial)\b', low, re.I) and len(words) <= 9:
            unsupported.append(f'{name}: judgment word is the whole reason: "{low.strip()}"')
        # 5. bare numbers
        if words and all(w.lower() in STOP for w in words):
            info.append(f'{name}: bare numbers with no argument: "{low.strip()}"')

    # 3. good-news fact under escalate / bad-news fact under false positive
    for name, t in esc:
        if re.search(r'\b(below|under|less than|lower than|smaller than)\b', clean(t), re.I):
            misleading.append(f'escalate item says "below/under", which is good news filed as a worry: "{clean(t).strip()}"')
    for name, t in fp:
        if re.search(r'\b(above|exceeds?|higher than|greater than)\b', clean(t), re.I):
            misleading.append(f'false-positive item says "above/exceeds": "{clean(t).strip()}"')

    # 4. uses coarse-group counts as evidence while the history is coarse
    if group > 500:
        for name, t in esc:
            if 'history_30d.' in ' '.join(CITE.findall(t)):
                misleading.append(f'escalate item uses history_30d counts although the group has {group} transactions (coarse): "{clean(t).strip()}"')
        for name, t in fp:
            if 'customer.group_txn_count_to_date' in t and not re.search(r'coarse|shar|overlap', t, re.I):
                misleading.append(f'false-positive item treats the group count as reassurance without the coarse caveat: "{clean(t).strip()}"')

    # 7. alert-count mismatch
    for name, t in texts:
        for m in re.finditer(r'\b(\d+|' + '|'.join(NUMW) + r')\s+(?:prior\s+)?alerts?\b', clean(t), re.I):
            n = NUMW.get(m.group(1).lower(), None) or int(m.group(1)) if m.group(1).lower() in NUMW or m.group(1).isdigit() else None
            if n is not None and n not in (len(prior), len(prior) + 1):
                unsupported.append(f'{name}: says "{m.group(0)}" but the packet has {len(prior)} prior alerts')

    digest = (f'score {p["alert"]["risk_score"]:.3f} | prior alerts {len(prior)} | group size {group} | '
              f'device/email shared by {p["same_device_and_email_30d"]["distinct_customers"]} customers | '
              f'AI suggests: {o["suggested_disposition"]}')
    n_claims = sum(len(CITE.findall(t)) for _, t in texts)
    return unsupported, misleading, info, digest, n_claims, texts


# carry over anything already scored by hand
old = {}
if os.path.exists('data/handscore.csv'):
    for row in csv.DictReader(open('data/handscore.csv')):
        old[row['case']] = row
if os.path.exists('data/handscore_prescreen.csv'):
    for row in csv.DictReader(open('data/handscore_prescreen.csv')):
        if row['unsupported_claims'] or row['misleading_framing_Y_N']:
            old[row['case']] = row

css = ('body{font-family:system-ui;margin:24px;max-width:1300px}.case{border:1px solid #ccc;border-radius:8px;margin:18px 0;padding:14px}'
       '.g{display:grid;grid-template-columns:1fr 1fr;gap:18px}table{border-collapse:collapse;font-size:12px}'
       'td{padding:1px 8px;border-bottom:1px solid #eee;vertical-align:top}td:first-child{color:#555;white-space:nowrap}'
       '.s p{margin:6px 0}.hint{background:#fff6e0;border-left:4px solid #e0a000;padding:8px 12px;margin:8px 0;font-size:13px}'
       '.clean{background:#eef8ee;border-left:4px solid #5a5;padding:8px 12px;margin:8px 0;font-size:13px}.dg{color:#444;font-size:13px}')
out = [f'<html><head><meta charset="utf-8"><style>{css}</style></head><body><h2>Pre-screened hand-scoring (hints are suggestions, you decide)</h2>']
with open('data/handscore_prescreen.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['case', 'alert_id', 'n_claims', 'auto_unsupported', 'auto_misleading',
                'unsupported_claims', 'misleading_framing_Y_N', 'disposition_sensible_Y_N_unsure', 'notes'])
    flagged = 0
    for i, r in enumerate(sample, 1):
        uns, mis, info, digest, n_claims, texts = analyze(r)
        prev = old.get(str(i), {})
        w.writerow([i, r['alert_id'], n_claims, len(uns), 'Y' if mis else 'N',
                    prev.get('unsupported_claims', ''), prev.get('misleading_framing_Y_N', ''),
                    prev.get('disposition_sensible_Y_N_unsure', ''), prev.get('notes', '')])
        flagged += bool(uns or mis)
        ev = ''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>' for k, v in flatten(r['packet']))
        sm = ''.join(f'<p><b>{html.escape(k)}:</b> {html.escape(t)}</p>' for k, t in texts)
        hints = ''.join(f'<div class="hint"><b>Likely unsupported:</b> {html.escape(h)}</div>' for h in uns)
        hints += ''.join(f'<div class="hint"><b>Likely misleading:</b> {html.escape(h)}</div>' for h in mis)
        hints += ''.join(f'<div class="hint"><b>Note:</b> {html.escape(h)}</div>' for h in info)
        if not (uns or mis):
            hints = '<div class="clean">No automatic flags for unsupported or misleading. Still read each sentence, then expect 0 / N.</div>' + hints
        out.append(f'<div class="case"><h3>Case {i} (alert {r["alert_id"]}) · claims: {n_claims} · auto: {len(uns)} unsupported, '
                   f'{"Y" if mis else "N"} misleading</h3>{hints}<div class="dg"><b>Evidence digest for the disposition call:</b> {html.escape(digest)}</div>'
                   f'<div class="g"><div><b>Evidence packet</b><table>{ev}</table></div>'
                   f'<div class="s"><b>AI summary</b>{sm}<p><b>suggested disposition:</b> {html.escape(r["output"]["suggested_disposition"])}</p></div></div></div>')
out.append('</body></html>')
open('data/handscore_hints.html', 'w').write(''.join(out))
print(f'{len(sample)} cases written; {flagged} have automatic flags; {len(sample) - flagged} have none')
print('\nCalibration, cases 1-6 (auto_unsupported / auto_misleading):')
for row in list(csv.DictReader(open('data/handscore_prescreen.csv')))[:6]:
    print(f"  case {row['case']}: {row['auto_unsupported']} / {row['auto_misleading']}")
