import json
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

try:
    from src.triage import triage_alert
except ImportError:
    from triage import triage_alert

OUT = Path('data/eval_results.jsonl')
VERSIONS = ['triage_v1', 'triage_v2']
KEEP = ['alert_id', 'prompt_version', 'status', 'error', 'validation', 'output',
        'packet', 'input_tokens', 'output_tokens', 'latency_ms', 'model_id', 'attempts', 'first_pass_status']
lock = threading.Lock()


def done_keys():
    if not OUT.exists():
        return set()
    keys = set()
    for line in OUT.read_text().splitlines():
        r = json.loads(line)
        keys.add((r['alert_id'], r['prompt_version']))
    return keys


def run_one(alert_id, is_fraud, version):
    for attempt in range(3):
        r = triage_alert(alert_id, prompt_version=version)
        if r.get('error') and 'hrottl' in r['error']:
            time.sleep(5 * (attempt + 1))
            continue
        break
    rec = {k: r.get(k) for k in KEEP}
    rec['is_fraud'] = is_fraud  # for analysis only; never sent to the model
    with lock:
        with OUT.open('a') as f:
            f.write(json.dumps(rec, default=str) + '\n')
    return rec


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    es = pd.read_csv('data/eval_set.csv')
    if n:
        es = es.head(n)
    done = done_keys()
    tasks = [(int(a), int(f), v) for a, f in zip(es.alert_id, es.is_fraud)
             for v in VERSIONS if (int(a), v) not in done]
    print(f'{len(tasks)} calls to run ({len(done)} already done)')
    count = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for rec in ex.map(lambda t: run_one(*t), tasks):
            count += 1
            if count % 20 == 0:
                print(f'  {count}/{len(tasks)}')
    rows = [json.loads(l) for l in OUT.read_text().splitlines()]
    print(Counter((r['prompt_version'], r['status']) for r in rows))
