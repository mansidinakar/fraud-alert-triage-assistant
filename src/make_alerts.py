from pathlib import Path
import duckdb
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score

con = duckdb.connect(str(Path('data/triage.duckdb')))
df = con.execute('SELECT * FROM transactions').df()

df['hour'] = df['occurred_at'].dt.hour
df['dow'] = df['occurred_at'].dt.day_of_week
cat_cols = ['product_cd', 'card_type', 'card_class', 'email_domain', 'device_type']
for c in cat_cols:
    df[c] = df[c].astype('category')
features = ['amount', 'addr1', 'hour', 'dow'] + cat_cols

# time split: first 70% of the time range trains, last 30% is scored
cutoff = df['occurred_at'].quantile(0.7)
train = df[df['occurred_at'] <= cutoff]
test = df[df['occurred_at'] > cutoff].copy()

model = HistGradientBoostingClassifier(categorical_features='from_dtype', random_state=42)
model.fit(train[features], train['is_fraud'])
test['risk_score'] = model.predict_proba(test[features])[:, 1]

roc = roc_auc_score(test['is_fraud'], test['risk_score'])
pr = average_precision_score(test['is_fraud'], test['risk_score'])

# top 5% of scores become alerts
n_alerts = int(len(test) * 0.05)
top = test.nlargest(n_alerts, 'risk_score').sort_values('occurred_at').reset_index(drop=True)
alerts_df = pd.DataFrame({
    'alert_id': range(1, len(top) + 1),
    'transaction_id': top['transaction_id'],
    'customer_id': top['customer_id'],
    'rule_id': 'model_v1',
    'risk_score': top['risk_score'],
    'status': 'open',
    'created_at': top['occurred_at'],
})
con.execute('DELETE FROM alerts')
con.register('alerts_df', alerts_df)
con.execute('INSERT INTO alerts SELECT * FROM alerts_df')

print('train rows:', len(train), '| scored rows:', len(test))
print('fraud rate train:', round(train['is_fraud'].mean(), 4), '| scored:', round(test['is_fraud'].mean(), 4))
print('ROC AUC:', round(roc, 4), '| PR AUC:', round(pr, 4))
print('alerts:', len(alerts_df), '| fraud rate in alerts:', round(top['is_fraud'].mean(), 4))
print('share of scored-period fraud captured by alerts:', round(top['is_fraud'].sum() / test['is_fraud'].sum(), 4))
print('alerts in database:', con.execute('SELECT COUNT(*) FROM alerts').fetchone()[0])
