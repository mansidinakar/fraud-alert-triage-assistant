from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

RAW = Path('data/raw')
DB = Path('data/triage.duckdb')
BASE = pd.Timestamp('2017-12-01')  # assumption: document it in data_notes.md

DB.unlink(missing_ok=True)
tx = pd.read_csv(RAW / 'train_transaction.csv')
idn = pd.read_csv(RAW / 'train_identity.csv', usecols=['TransactionID', 'DeviceType'])
df = tx.merge(idn, on='TransactionID', how='left')

key = (df['card1'].fillna(-1).astype(int).astype(str) + '|' + df['card2'].fillna(-1).astype(int).astype(str) + '|' + df['addr1'].fillna(-1).astype(int).astype(str))
df['customer_id'] = pd.util.hash_pandas_object(key, index=False).astype(str)
df['occurred_at'] = BASE + pd.to_timedelta(df['TransactionDT'], unit='s')

tx_out = df.rename(columns={
    'TransactionID': 'transaction_id', 'TransactionAmt': 'amount',
    'ProductCD': 'product_cd', 'card4': 'card_type', 'card6': 'card_class',
    'P_emaildomain': 'email_domain', 'DeviceType': 'device_type', 'isFraud': 'is_fraud',
})[['transaction_id', 'customer_id', 'occurred_at', 'amount', 'product_cd', 'card_type',
    'card_class', 'addr1', 'email_domain', 'device_type', 'is_fraud']]

rng = np.random.default_rng(42)
cust = pd.DataFrame({'customer_id': df['customer_id'].unique()})
cust['syn_segment'] = rng.choice(['standard', 'premium', 'new'], size=len(cust), p=[0.7, 0.2, 0.1])
cust['syn_account_open_date'] = (BASE - pd.to_timedelta(rng.integers(30, 3000, size=len(cust)), unit='D')).date

con = duckdb.connect(str(DB))
con.execute(Path('sql/01_schema.sql').read_text())
con.register('tx_df', tx_out)
con.execute('INSERT INTO transactions SELECT * FROM tx_df')
con.register('cust_df', cust)
con.execute('INSERT INTO customers SELECT * FROM cust_df')
print(con.execute('SELECT COUNT(*), SUM(is_fraud) FROM transactions').fetchone())
print(con.execute('SELECT COUNT(*) FROM customers').fetchone())