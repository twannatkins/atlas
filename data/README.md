# ATLAS Synthetic Data

All data in this workshop is synthetic, generated with a fixed random seed (42).
No real customer data is used anywhere.

## Files

| File | Records | Description |
|------|---------|-------------|
| `synthetic/customer-master.json` | 200 | Synthetic customer records with household IDs, segments, and states |
| `synthetic/transaction-history.json` | ~3,750 | 90 days of synthetic transactions with embedded wealth-signal patterns |
| `synthetic/event-stream.json` | 31 | Pre-generated stream of wealth-eligibility events for Pattern C replay |

## Embedded Signal Counts

The transaction history contains a known number of wealth-signal transactions
(verified by the Module 4 validation gate):

| Signal Type | Count | Threshold |
|---|---|---|
| large-deposit-pattern | 12 | USD 250,000 |
| equity-event-signal | 7 | USD 100,000 |
| retirement-rollover-signal | 5 | USD 50,000 |
| business-sale-liquidity-signal | 3 | USD 500,000 |
| household-aggregation-signal | 4 | USD 1,000,000 (household combined) |

## Regenerating

To regenerate the synthetic data with the same seed:

```python
import sys
sys.path.insert(0, "notebooks/shared")
import atlas_synthetic

customers = atlas_synthetic.generate_customers(n=200)
accounts = atlas_synthetic.generate_accounts(customers)
transactions = atlas_synthetic.generate_transactions(accounts, lookback_days=90)
household_signals = atlas_synthetic.generate_household_signals(customers, accounts)
```

The output is deterministic: same seed, same data, every time.

## Format

Files are JSON for portability. The Module 4 notebook converts them to Parquet
(using pandas) before loading into S3 Iceberg tables via AWS Glue.

In production, these would be Parquet files in S3 managed by Iceberg table format
with Glue Data Catalog as the metastore.
