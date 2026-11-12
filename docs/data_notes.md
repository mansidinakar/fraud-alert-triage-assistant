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

## Customer grouping (measured Nov 5, 2026)
- The dataset has no customer ID. A customer is derived from card1 + card2 + addr1, with missing values replaced by -1 before grouping.
- Result: 41,672 customer groups. Median group size is 2 transactions, but the largest groups hold 9,900, 5,866 and 5,766 transactions, so some groups combine several real people.
- Effect: 30-day customer history is reliable for small groups and coarse for large ones. The evidence packet will include the group size so analysts can judge this.
- Bug found and fixed during Phase 2: an earlier version collapsed every row with a missing card2 or addr1 into a single fake customer. The fix is in src/load_data.py.

## Drift check (weekly fraud rate, scored period)
- Fraud rate among alerts ranges from 19.6% to 27.3% across weeks, with no sustained trend or surge.
- Fraud rate across all transactions ranges from 3.0% to 4.4% by week. The first and last weeks are partial.
- Dates use the assumed base date of 2017-12-01, so weeks are relative, not real calendar weeks.

## Data license

The transaction data comes from Kaggle's IEEE-CIS Fraud Detection competition. Its rules allow the Competition Data to be used for non-commercial purposes, including academic research and education, and they do not allow it to be published or made available to people who have not agreed to the rules. This repo uses the data for a non-commercial portfolio project and does not include it. To run the project, download the data yourself from Kaggle under the same rules.
