# Daily Reconciliation Summary — 2026-11-16

**Source file:** source_settlements.csv  ·  **Ledger file:** ledger_settlements.csv

## Verdict: ⚠️ BREAKS FOUND — 3 break(s) worth $214.99

Do not close the day until Finance clears the breaks listed below.

## Totals

- **Source rows:** 18 (total $2,550.19)
- **Ledger rows:** 18 (total $2,575.20)
- **Matched exactly:** 16 transactions
- **Net difference (ledger − source):** $25.01
- **Total value of breaks:** $214.99
- **Largest single break:** Missing in source TXN-5210 — $120.00

## Breaks — send these to Finance

- **Amount mismatch:** TXN-5203 — source $250.00, ledger $245.00 (difference $-5.00)
- **Missing in ledger:** TXN-5207 — $89.99 in the source file, never posted to the ledger
- **Missing in source:** TXN-5210 — $120.00 in the ledger with no source record

Amounts are compared on transaction ID using exact decimal arithmetic. A transaction that appears in only one system is a break, not a rounding difference — chase it by ID, not by total.
