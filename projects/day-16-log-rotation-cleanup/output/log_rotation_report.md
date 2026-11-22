# Log Rotation & Cleanup Report — htch-runtime

**When:** 2026-11-22 09:20 · **Mode:** manifest (sample_data/inventory.txt) · **Run:** dry-run — no files changed

Policy: compress plain logs older than **30 days**, delete `.gz` archives older than **90 days**. Files modified in the last 60 minutes are active and never touched. Compression saving estimated at 85% (gzip on text logs) unless the run applied the changes.

## Summary

| | Count | Size |
|---|---|---|
| Files scanned | 14 | 36.57 GB |
| To compress | 4 | 24.20 GB → Estimated freed 20.57 GB |
| To delete | 2 | 4.80 GB freed |
| **Estimated total freed** | | **25.37 GB** (36.57 GB → ~11.20 GB after cleanup) |
| Kept within policy | 6 | |
| Active logs skipped | 1 | |
| Not log files, skipped | 1 | |

## Space by directory

| Directory | Files | Total |
|---|---|---|
| `/var/log/payment-api` | 6 | 28.00 GB |
| `/var/log/settlement-batch` | 2 | 4.80 GB |
| `/var/log/nginx` | 2 | 2.30 GB |
| `/var/log/crm-sync` | 2 | 1.35 GB |
| `/var/log` | 2 | 120.00 MB |

## Actions

| Action | File | Size | Age | Detail |
|---|---|---|---|---|
| COMPRESS | `/var/log/payment-api/app.log` | 9.20 GB | 45 days | log older than 30 days — gzip to app.log.gz (est. frees 7.82 GB) |
| COMPRESS | `/var/log/payment-api/app.log.1` | 6.40 GB | 52 days | log older than 30 days — gzip to app.log.1.gz (est. frees 5.44 GB) |
| COMPRESS | `/var/log/payment-api/error.log` | 5.00 GB | 38 days | log older than 30 days — gzip to error.log.gz (est. frees 4.25 GB) |
| COMPRESS | `/var/log/settlement-batch/batch.log` | 3.60 GB | 60 days | log older than 30 days — gzip to batch.log.gz (est. frees 3.06 GB) |

| DELETE | `/var/log/payment-api/app.log.2.gz` | 3.60 GB | 120 days | archive older than 90 days — delete, frees 3.60 GB |
| DELETE | `/var/log/settlement-batch/batch.log.1.gz` | 1.20 GB | 110 days | archive older than 90 days — delete, frees 1.20 GB |

| ACTIVE — skipped | `/var/log/crm-sync/sync.log` | 950.00 MB | 15 min | modified 15 min ago — still being written, never rotate an active log |

| KEEP | `/var/log/payment-api/access.log` | 2.90 GB | 1 day | log within the 30-day retention |
| KEEP | `/var/log/payment-api/app.log.3.gz` | 900.00 MB | 70 days | archive within the 90-day retention |
| KEEP | `/var/log/nginx/access.log` | 1.50 GB | 2 days | log within the 30-day retention |
| KEEP | `/var/log/nginx/error.log` | 800.00 MB | 17 days | log within the 30-day retention |
| KEEP | `/var/log/crm-sync/sync.log.1` | 400.00 MB | 25 days | log within the 30-day retention |
| KEEP | `/var/log/auth.log` | 120.00 MB | 12 days | log within the 30-day retention |

| SKIP | `/var/log/README.txt` | 2.00 KB | 90 days | not a .log file — left alone |


## Conclusion

**DRY-RUN — cleanup pending.** 4 log(s) to compress and 2 archive(s) to delete, freeing an estimated 25.37 GB. Nothing was changed by this run. Review the actions above, then re-run with `--apply` — or schedule the apply run — before the next batch window. See RUNBOOK.md before deleting anything that might be needed for audit.

