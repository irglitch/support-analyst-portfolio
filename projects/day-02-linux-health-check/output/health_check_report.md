# Server Health Check — htch-runtime

**When:** 2026-11-08 14:23 UTC · **Mode:** snapshot (sample_data/slow_server)

## Checks

| Check | Status | Detail |
|---|---|---|
| CPU load (1-min avg per core) | FAIL | load 8.42 on 4 cores = 2.10 per core |
| Memory used | WARN | 88% used (7018 MB of 7976 MB) |
| Swap used | WARN | 25% used (512 MB of 2047 MB) |
| Disk / | FAIL | 92% used (46G of 50G, 4.0G free) |
| Disk /data | PASS | 30% used (30G of 100G, 70G free) |
| Top process CPU | WARN | /usr/local/bin/payment-api at 87.4% CPU |
| Service payment-api | FAIL | state: failed |
| Service nginx | PASS | running |
| Service postgresql | PASS | running |
| Service file-watcher | PASS | running |

## Top 5 processes by CPU

```
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
appuser   4821 87.4 22.1 4123456 1762344 ?      Sl   08:12  45:12 /usr/local/bin/payment-api
appuser   3902 12.3  8.4 1234567  670123 ?      Sl   07:58  12:03 /usr/local/bin/file-watcher
postgres  2210  6.1 15.2 2345678 1212345 ?      S    06:00  08:44 postgres: main process
root      1102  1.2  0.4  234567   34567 ?      Ss   06:00  00:12 /usr/sbin/nginx -g daemon off;
root         1  0.1  0.2  123456   12345 ?      Ss   May22  00:45 /sbin/init
```

## Uptime

```
 09:12:03 up 14 days,  3:21,  2 users,  load average: 8.42, 7.10, 5.33
```

## Conclusion

**Failure — this host needs action now.** At least one check is over its failure threshold. The FAIL items above are the first suspects for the reported slowness — work them in order, then escalate with this report attached (see RUNBOOK.md).

