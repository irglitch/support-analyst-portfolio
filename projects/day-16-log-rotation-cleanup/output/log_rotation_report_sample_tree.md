# Log Rotation & Cleanup Report — htch-runtime

**When:** 2026-11-22 14:30 UTC · **Mode:** live (sample_data/logs) · **Run:** dry-run — no files changed

Policy: compress plain logs older than **30 days**, delete `.gz` archives older than **90 days**. Files modified in the last 60 minutes are active and never touched. Compression saving estimated at 85% (gzip on text logs) unless the run applied the changes.

## Summary

| | Count | Size |
|---|---|---|
| Files scanned | 8 | 38.72 KB |
| To compress | 4 | 31.90 KB → Estimated freed 27.11 KB |
| To delete | 1 | 99 B freed |
| **Estimated total freed** | | **27.21 KB** (38.72 KB → ~11.51 KB after cleanup) |
| Kept within policy | 2 | |
| Active logs skipped | 1 | |
| Not log files, skipped | 0 | |

## Space by directory

| Directory | Files | Total |
|---|---|---|
| `sample_data/logs/payment-api` | 5 | 27.39 KB |
| `sample_data/logs/settlement-batch` | 1 | 7.17 KB |
| `sample_data/logs/nginx` | 1 | 2.40 KB |
| `sample_data/logs/crm-sync` | 1 | 1.76 KB |

## Actions

| Action | File | Size | Age | Detail |
|---|---|---|---|---|
| COMPRESS | `sample_data/logs/payment-api/app.log` | 12.29 KB | 45 days | log older than 30 days — gzip to app.log.gz (est. frees 10.44 KB) |
| COMPRESS | `sample_data/logs/payment-api/app.log.1` | 6.30 KB | 52 days | log older than 30 days — gzip to app.log.1.gz (est. frees 5.36 KB) |
| COMPRESS | `sample_data/logs/payment-api/error.log` | 6.14 KB | 38 days | log older than 30 days — gzip to error.log.gz (est. frees 5.22 KB) |
| COMPRESS | `sample_data/logs/settlement-batch/batch.log` | 7.17 KB | 60 days | log older than 30 days — gzip to batch.log.gz (est. frees 6.09 KB) |

| DELETE | `sample_data/logs/payment-api/app.log.2.gz` | 99 B | 120 days | archive older than 90 days — delete, frees 99 B |

| ACTIVE — skipped | `sample_data/logs/crm-sync/sync.log` | 1.76 KB | 1 min | modified 1 min ago — still being written, never rotate an active log |

| KEEP | `sample_data/logs/nginx/error.log` | 2.40 KB | 17 days | log within the 30-day retention |
| KEEP | `sample_data/logs/payment-api/access.log` | 2.56 KB | 1 day | log within the 30-day retention |


## Conclusion

**DRY-RUN — cleanup pending.** 4 log(s) to compress and 1 archive(s) to delete, freeing an estimated 27.21 KB. Nothing was changed by this run. Review the actions above, then re-run with `--apply` — or schedule the apply run — before the next batch window. See RUNBOOK.md before deleting anything that might be needed for audit.

