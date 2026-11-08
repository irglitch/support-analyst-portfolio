# Server Health Check — htch-runtime

**When:** 2026-11-08 14:23 UTC · **Mode:** snapshot (sample_data/healthy_server)

## Checks

| Check | Status | Detail |
|---|---|---|
| CPU load (1-min avg per core) | PASS | load 0.42 on 4 cores = 0.10 per core |
| Memory used | PASS | 35% used (2766 MB of 7976 MB) |
| Swap used | PASS | 0% used (0 MB of 2047 MB) |
| Disk / | PASS | 41% used (21G of 50G, 29G free) |
| Disk /data | PASS | 30% used (30G of 100G, 70G free) |
| Top process CPU | PASS | /usr/local/bin/payment-api at 8.2% CPU |
| Service payment-api | PASS | running |
| Service nginx | PASS | running |
| Service postgresql | PASS | running |
| Service file-watcher | PASS | running |

## Top 5 processes by CPU

```
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
appuser   4821  8.2 22.1 4123456 1762344 ?      Sl   08:12  45:12 /usr/local/bin/payment-api
appuser   3902  4.1  8.4 1234567  670123 ?      Sl   07:58  12:03 /usr/local/bin/file-watcher
postgres  2210  2.0 15.2 2345678 1212345 ?      S    06:00  08:44 postgres: main process
root      1102  0.4  0.4  234567   34567 ?      Ss   06:00  00:12 /usr/sbin/nginx -g daemon off;
root         1  0.1  0.2  123456   12345 ?      Ss   May22  00:45 /sbin/init
```

## Uptime

```
 09:12:03 up 14 days,  3:21,  2 users,  load average: 0.42, 0.55, 0.61
```

## Conclusion

**All checks passed.** No resource pressure found on this host — if users still report slowness, check the application log and the database next (see RUNBOOK.md).

