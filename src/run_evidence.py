from pathlib import Path
import random
import duckdb

con = duckdb.connect('data/triage.duckdb', read_only=True)
text = Path('sql/02_evidence.sql').read_text()
queries = {}
for block in text.split('-- name: ')[1:]:
    name, sql = block.split('\n', 1)
    queries[name.strip()] = sql.strip().rstrip(';')

ids = [r[0] for r in con.execute('SELECT alert_id FROM alerts').fetchall()]
for alert_id in random.sample(ids, 3):
    print('=' * 60)
    print('ALERT', alert_id)
    for name, sql in queries.items():
        df = con.execute(sql, [alert_id]).df()
        print('--', name, '->', len(df), 'row(s)')
        print(df.to_string(index=False))
