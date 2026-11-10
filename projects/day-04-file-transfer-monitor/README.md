# Day 04 — File Transfer Monitor

## 📟 The situation (real-world use case)

**Tuesday, 07:30.** The daily settlement file from the payment processor is due
every morning by **07:00** — finance reconciles against it, and the downstream
batch job cannot start without it. It's now 07:30 and nobody has called yet,
but the file isn't in the drop folder. If support waits for finance to notice,
the batch is already late and the SLA clock is running. The morning checklist
also covers three other files: a CRM customer feed (due 06:30), FX rates
(due 06:00), and the overnight audit log (due 07:00). Checking each one by hand
— log in to the transfer system, list the folder, eyeball the timestamps and
sizes — takes 15–20 minutes every morning, and a zero-byte file *looks* like
it arrived.

## 🔧 The fix

`file_transfer_monitor.py` checks the morning's expected files against the
transfer log and the real drop folder, and produces a one-page
**File Transfer Status Report**:

- **Per-file status:** OK / LATE / MISSING / EMPTY / SMALL (undersized —
  a truncated transfer)
- **Disk verification** (`--drop-dir`): a file in the transfer log but not
  on disk is flagged MISSING, and a size mismatch between log and disk is
  flagged — the log alone can't be trusted
- **Unexpected files** are listed separately, so a new feed (or a misdirected
  file) doesn't slip past unnoticed
- **Overall status + exit code** a scheduler or monitoring check can use:
  `0` all OK · `1` warning (late/undersized) · `2` alert (missing/empty)

## ▶️ Run it

```bash
cd projects/day-04-file-transfer-monitor
python3 file_transfer_monitor.py sample_data/expected_files.csv \
    sample_data/transfer_log_20261110.csv --now 07:30 \
    --drop-dir sample_data/incoming --out output/transfer_status_report.md
cat output/transfer_status_report.md
```

**Result on the sample data:** 🔴 **ALERT (exit 2)** — 4 files checked, only 1 OK.
The critical `settlement_20261110.csv` is **MISSING** (due 07:00, no arrival
recorded), `audit_log_20261110.csv` arrived as a **zero-byte file**
(EMPTY — a failed transfer), and `rates_20261110.csv` is **LATE**
(arrived 06:47 against a 06:00 deadline). Only `customer_feed_20261110.csv`
is OK (06:12, 651 B). An unexpected file, `promo_codes_20261110.csv`,
arrived without being in the manifest and needs confirming with the sender.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

File transfer monitoring · Batch / settlement-file support · SLA awareness ·
Checking before escalating · Python scripting · Support documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
