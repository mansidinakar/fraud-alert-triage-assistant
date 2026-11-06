import duckdb

con = duckdb.connect('data/triage.duckdb', read_only=True)
df = con.execute(
    'SELECT a.alert_id, CAST(t.is_fraud AS INTEGER) AS is_fraud '
    'FROM alerts a JOIN transactions t USING (transaction_id)'
).df()

fraud = df[df.is_fraud == 1].sample(60, random_state=42)
legit = df[df.is_fraud == 0].sample(140, random_state=42)
eval_set = (
    fraud.assign(group='fraud').pipe(lambda f: __import__('pandas').concat([f, legit.assign(group='not_fraud')]))
    .sample(frac=1, random_state=42)
    .reset_index(drop=True)
)
eval_set.to_csv('data/eval_set.csv', index=False)
print(eval_set.group.value_counts())
print('saved', len(eval_set), 'alerts to data/eval_set.csv')
