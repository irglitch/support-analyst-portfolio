#!/usr/bin/env bash
# Tests for health_check.sh — run from the project directory:
#   bash tests/test_health_check.sh
#
# 5 checks: slow snapshot fails loudly, healthy snapshot passes clean,
# memory/disk/service findings are reported correctly, exit codes are right.
set -u

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1

PASS=0
FAIL=0

ok()   { PASS=$((PASS + 1)); echo "ok   - $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "FAIL - $1"; }

# --- Test 1: slow server snapshot -> exit 2, report flags disk + service ----
bash health_check.sh --snapshot sample_data/slow_server --out /tmp/hc_slow.md
CODE=$?
REPORT=$(cat /tmp/hc_slow.md)
if [[ $CODE -eq 2 ]] && echo "$REPORT" | grep -q '| Disk / | FAIL | 92% used' \
   && echo "$REPORT" | grep -q '| Service payment-api | FAIL | state: failed'; then
    ok "slow snapshot: exit 2, root disk 92% FAIL and payment-api failed reported"
else
    bad "slow snapshot: expected exit 2 with disk FAIL + service FAIL (got exit $CODE)"
fi

# --- Test 2: healthy server snapshot -> exit 0, no WARN/FAIL ---------------
bash health_check.sh --snapshot sample_data/healthy_server --out /tmp/hc_healthy.md
CODE=$?
REPORT=$(cat /tmp/hc_healthy.md)
if [[ $CODE -eq 0 ]] && ! echo "$REPORT" | grep -qE '\| (WARN|FAIL) \|' \
   && echo "$REPORT" | grep -q 'All checks passed'; then
    ok "healthy snapshot: exit 0, all checks PASS"
else
    bad "healthy snapshot: expected exit 0 with all PASS (got exit $CODE)"
fi

# --- Test 3: memory pressure is reported with the right number -------------
REPORT_SLOW=$(cat /tmp/hc_slow.md)
if echo "$REPORT_SLOW" | grep -q '| Memory used | WARN | 88% used'; then
    ok "slow snapshot: memory 88% reported as WARN"
else
    bad "slow snapshot: expected memory 88% WARN line"
fi

# --- Test 4: runaway process is flagged ------------------------------------
if echo "$REPORT_SLOW" | grep -q '| Top process CPU | WARN | /usr/local/bin/payment-api at 87.4% CPU'; then
    ok "slow snapshot: top process payment-api at 87.4% CPU flagged WARN"
else
    bad "slow snapshot: expected top-process WARN line for payment-api"
fi

# --- Test 5: CPU load per core is computed correctly ------------------------
if echo "$REPORT_SLOW" | grep -q 'load 8.42 on 4 cores = 2.10 per core'; then
    ok "slow snapshot: load per core 2.10 computed from 8.42 / 4 cores"
else
    bad "slow snapshot: expected load-per-core line 'load 8.42 on 4 cores = 2.10 per core'"
fi

# --- Test 6: live mode runs cleanly on this host --------------------------
bash health_check.sh --out /tmp/hc_live.md
CODE=$?
if [[ $CODE -ge 0 && $CODE -le 2 ]] && grep -q '## Checks' /tmp/hc_live.md \
   && ! grep -q 'Service unknown' /tmp/hc_live.md; then
    ok "live mode: runs, writes a report, no phantom 'unknown' service lines (exit $CODE)"
else
    bad "live mode: expected a clean report with exit 0-2 (got exit $CODE)"
fi

echo ""
echo "$PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
