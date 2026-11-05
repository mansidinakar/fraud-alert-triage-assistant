# Results

All numbers below were measured by the scripts in this repo. Sample sizes are stated next to each result.

## Alert model (model_v1)
- Model: scikit-learn HistGradientBoostingClassifier on explainable columns (amount, addr1, hour, day of week, product, card type, card class, email domain, device type).
- Split by time: first 70% of the time range for training (413,378 rows), last 30% scored (177,162 rows).
- Fraud rate: 3.52% in training, 3.46% in the scored period.
- ROC AUC: 0.7909. PR AUC: 0.1878.
- Alerts = top 5% of scores in the scored period: 8,858 alerts.
- Fraud rate inside alerts: 23.04% (about 6.7x the scored-period rate).
- Share of scored-period fraud captured by alerts: 33.3%.
