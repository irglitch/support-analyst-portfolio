# Disk Space Early-Warning Report — htch-runtime

**When:** 2026-11-20 14:25 UTC · **Mode:** snapshot (sample_data/filling_up)

Thresholds: disk WARN at 80%, FAIL at 90%; a mount that fills within 24 h is WARN, within 4 h is FAIL.

## Checks

| Check | Status | Detail |
|---|---|---|
| Disk / | PASS | 62% used (31G of 50G, 19G free) · stable — no growth in the history window |
| Disk /var | WARN | 88% used (176G of 200G, 24G free) · fills in ~5.8 h at +2.06%/h |
| Disk /data | FAIL | 96% used (480G of 500G, 20G free) · stable — no growth in the history window |
| Inodes / | PASS | 20% used (655360 of 3276800 inodes) |
| Inodes /var | PASS | 45% used (5898240 of 13107200 inodes) |
| Inodes /data | FAIL | 90% used (29491200 of 32768000 inodes) |

## Growth forecast (from hourly history)

| Mount | Now | Growth | Fills in |
|---|---|---|---|
| / | 62% | 0%/h | stable |
| /var | 88% | +2.06%/h | ~5.8 h |
| /data | 96% | 0%/h | stable |

## Largest directories

Largest directories from the snapshot (flagged at 10G and above — investigate these first):

```
120G  /data/archives/settlements-2025  <-- large, investigate first
90G  /data/archives/settlements-2024  <-- large, investigate first
28G  /var/log/payment-api  <-- large, investigate first
18G  /var/lib/postgresql  <-- large, investigate first
6G  /var/log/nginx
```

## Conclusion

**Failure — a filesystem needs action now.** At least one mount is over its failure threshold or fills within 4 hours. Work the FAIL items above in order, start with the largest directories listed, and escalate with this report attached (see RUNBOOK.md). If a mount hits 100%, writes fail, logs stop, and the batch on that mount stops with it.

