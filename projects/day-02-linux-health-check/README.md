# Day 02 — Linux Health Check Script

## 🖥️ The situation (real-world use case)

**Tuesday, 09:41.** The service desk phones: *"The app is slow — pages are taking 30
seconds to load."* No error message, no single failing screen — just "slow". Before
anyone escalates, support needs facts: is the server itself under pressure, or is the
problem in the application? Guessing costs an hour; checking takes two minutes.

## 🔧 The fix

`health_check.sh` runs the standard first-response checks in one command and produces
a one-page **Server Health Check Report** with PASS / WARN / FAIL per check:

- **CPU load** — 1-minute load average per core (over 1.0 = WARN, over 2.0 = FAIL)
- **Memory used** — over 80% = WARN, over 90% = FAIL
- **Swap used** — swapping means memory pressure, not a healthy server
- **Disk space** — every filesystem, over 80% = WARN, over 90% = FAIL
- **Top process by CPU** — a single process hogging a core is a suspect, not a mystery
- **Key services** — `payment-api`, `nginx`, `postgresql`, `file-watcher`: running, stopped, or not installed
- **Exit code** — 0 = all PASS, 1 = WARN, 2 = FAIL, so it plugs straight into monitoring or a ticket workflow

It runs **live** on a host, or against a **captured snapshot** (`--snapshot`) so the
same checks can be replayed on saved `uptime` / `free` / `df` / `ps` output —
handy when the slow server is one you can't log into right now.

## ▶️ Run it

Against the sample "slow server" snapshot (the incident scenario):

```bash
cd projects/day-02-linux-health-check
bash health_check.sh --snapshot sample_data/slow_server --out output/health_check_report.md
cat output/health_check_report.md
```

Against the healthy snapshot, for comparison:

```bash
bash health_check.sh --snapshot sample_data/healthy_server --out output/health_check_report_healthy.md
```

Live on a Linux host:

```bash
bash health_check.sh --out output/health_check_report_live.md
echo "exit code: $?"   # 0 = all PASS, 1 = WARN, 2 = FAIL
```

**Result on the sample data:** the slow server fails **3 checks** — root disk **92%
full** (FAIL), CPU load **2.10 per core** (FAIL), and the `payment-api` service is
**failed** (FAIL) — with memory at **88%** (WARN), swap in use (WARN), and the
`payment-api` process itself burning **87.4% CPU** (WARN). The "app is slow" symptom
has a concrete story: the disk is nearly full, the service is down, and the one
process still running is spinning. The healthy snapshot passes every check (exit 0).

Run the tests:

```bash
bash tests/test_health_check.sh
```

## 🛠 Skills demonstrated

Linux basics (uptime / free / df / ps / systemctl) · Bash scripting · First-response
triage · Threshold-based monitoring · Support documentation · SLA awareness

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
