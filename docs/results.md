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

## Ranked queue vs first-in-first-out (Phase 3)
Sample: 8,858 alerts in the scored period, of which 2,041 are confirmed fraud. One time split, one model run.

| Share of queue reviewed | Recall, ranked queue | Recall, first-in-first-out |
|---|---|---|
| 5% | 10.4% | 5.5% |
| 10% | 17.6% | 13.1% |
| 20% | 32.8% | 22.4% |
| 30% | 43.3% | 33.5% |
| 50% | 63.2% | 53.0% |

- PRD target: 90% of confirmed fraud in the top 20% of the queue. Measured: 32.8%. Target missed.
- Reading: ranking gives about 1.5x the fraud caught at 20% reviewed. The gain is modest because alerts are already the model's top 5% of scores, so the queue only reorders alerts that were already flagged.
- The target was set before any data was measured and is not realistic for this dataset and model.
