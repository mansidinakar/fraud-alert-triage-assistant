# Data notes

## Source
IEEE-CIS Fraud Detection (Kaggle competition, Vesta Corporation, 2019).
Files used: train_transaction.csv and train_identity.csv, joined on TransactionID.
The raw data is not stored in this repo; it is downloaded through the Kaggle API.

## What it contains
- 590,540 transactions, 394 columns (transactions) and 144,233 identity rows (41 columns).
- Fraud rate: 3.5% (isFraud = 1).
- Identity data covers about 24% of transactions.
- TransactionDT is a seconds offset spanning about 183 days, not a real date.
  For display only, an assumed base date of 2017-12-01 is used.

## Known limitations
- Dataset is from 2019 and many columns are masked (C1-C14, D1-D15, V1-V339), so features cannot be explained in plain business terms.
- No merchant names or categories.
- No customer ID. A customer is derived from card1 + card2 + addr1 and is an approximation.

## Synthetic fields
Anything not in the original data is prefixed `syn_` (for example account open date).
These fields are generated for demonstration and are never presented as real data.
