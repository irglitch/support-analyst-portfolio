# Disk Space Early-Warning Report — htch-runtime

**When:** 2026-11-20 14:25 UTC · **Mode:** snapshot (sample_data/healthy)

Thresholds: disk WARN at 80%, FAIL at 90%; a mount that fills within 24 h is WARN, within 4 h is FAIL.

## Checks

| Check | Status | Detail |
|---|---|---|
| Disk / | PASS | 41% used (21G of 50G, 29G free) · stable — no growth in the history window |
| Disk /var | PASS | 58% used (116G of 200G, 84G free) · fills in ~163.3 h at +0.26%/h |
| Disk /data | PASS | 63% used (315G of 500G, 185G free) · stable — no growth in the history window |
| Inodes / | PASS | 20% used (655360 of 3276800 inodes) |
| Inodes /var | PASS | 30% used (3932160 of 13107200 inodes) |
| Inodes /data | PASS | 40% used (13107200 of 32768000 inodes) |

## Growth forecast (from hourly history)

| Mount | Now | Growth | Fills in |
|---|---|---|---|
| / | 41% | 0%/h | stable |
| /var | 58% | +0.26%/h | ~163.3 h |
| /data | 63% | 0%/h | stable |

## Largest directories

No mount is over its warning threshold, so no directory scan was run.

## Conclusion

**All filesystems healthy.** No mount is over its warning threshold and none is forecast to fill within 24 hours. Re-run at the next morning check — a mount that starts growing will show up here before it becomes an outage.

