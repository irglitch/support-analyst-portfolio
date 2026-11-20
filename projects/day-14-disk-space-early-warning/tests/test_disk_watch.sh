#!/usr/bin/env bash
# Tests for disk_watch.sh — run from the project directory:
#   bash tests/test_disk_watch.sh
#
# 7 checks: filling-up snapshot fails loudly with the right numbers,
# growth forecast math is right, large directories are flagged, inode
# pressure is caught, healthy snapshot passes clean, bad input errors
# out, and live mode runs.
set -u

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1

PASS=0
FAIL=0

ok()   { PASS=$((PASS + 1)); echo "ok   - $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "FAIL - $1"; }

# --- Test 1: filling-up snapshot -> exit 2, /data FAIL, /var WARN ----------
bash disk_watch.sh --snapshot sample_data/filling_up --out /tmp/dw_filling.md
CODE=$?
REPORT=$(cat /tmp/dw_filling.md)
if [[ $CODE -eq 2 ]] && echo "$REPORT" | grep -q '| Disk /data | FAIL | 96% used' \
   && echo "$REPORT" | grep -q '| Disk /var | WARN | 88% used'; then
    ok "filling-up snapshot: exit 2, /data 96% FAIL and /var 88% WARN reported"
else
    bad "filling-up snapshot: expected exit 2 with /data FAIL + /var WARN (got exit $CODE)"
fi

# --- Test 2: growth forecast — /var fills in ~5.8 h at +2.06%/h ------------
# History: /var 64% -> 88% over 11h40m = +2.06%/h; (100-88)/2.06 = ~5.8 h
if echo "$REPORT" | grep -q 'fills in ~5.8 h at +2.06%/h' \
   && echo "$REPORT" | grep -q '| /var | 88% | +2.06%/h | ~5.8 h |'; then
    ok "filling-up snapshot: /var growth +2.06%/h, fills in ~5.8 h"
else
    bad "filling-up snapshot: expected '/var fills in ~5.8 h at +2.06%/h'"
fi

# --- Test 3: largest directories are listed and flagged --------------------
if echo "$REPORT" | grep -q '120G  /data/archives/settlements-2025  <-- large, investigate first' \
   && echo "$REPORT" | grep -q '28G  /var/log/payment-api  <-- large, investigate first' \
   && echo "$REPORT" | grep -q '6G  /var/log/nginx$'; then
    ok "filling-up snapshot: top dirs listed, 120G/28G flagged large, 6G not flagged"
else
    bad "filling-up snapshot: expected flagged large dirs (120G, 28G) and unflagged 6G"
fi

# --- Test 4: inode pressure is caught — /data at 90% is FAIL ---------------
if echo "$REPORT" | grep -q '| Inodes /data | FAIL | 90% used' \
   && echo "$REPORT" | grep -q '| Inodes /var | PASS | 45% used'; then
    ok "filling-up snapshot: inodes /data 90% FAIL, /var 45% PASS"
else
    bad "filling-up snapshot: expected inodes /data 90% FAIL"
fi

# --- Test 5: healthy snapshot -> exit 0, no WARN/FAIL ----------------------
bash disk_watch.sh --snapshot sample_data/healthy --out /tmp/dw_healthy.md
CODE=$?
REPORT_H=$(cat /tmp/dw_healthy.md)
if [[ $CODE -eq 0 ]] && ! echo "$REPORT_H" | grep -qE '\| (WARN|FAIL) \|' \
   && echo "$REPORT_H" | grep -q 'All filesystems healthy' \
   && echo "$REPORT_H" | grep -q 'fills in ~163.3 h at +0.26%/h'; then
    ok "healthy snapshot: exit 0, all PASS, /var slow growth ~163.3 h to full"
else
    bad "healthy snapshot: expected exit 0 with all PASS (got exit $CODE)"
fi

# --- Test 6: missing snapshot directory -> exit 2 with an error ------------
ERR=$(bash disk_watch.sh --snapshot sample_data/does_not_exist --out /tmp/dw_missing.md 2>&1)
CODE=$?
if [[ $CODE -eq 2 ]] && echo "$ERR" | grep -q 'Snapshot directory not found'; then
    ok "missing snapshot: exit 2 with 'Snapshot directory not found'"
else
    bad "missing snapshot: expected exit 2 with error message (got exit $CODE)"
fi

# --- Test 7: live mode runs cleanly on this host ---------------------------
bash disk_watch.sh --out /tmp/dw_live.md
CODE=$?
if [[ $CODE -ge 0 && $CODE -le 2 ]] && grep -q '## Checks' /tmp/dw_live.md \
   && grep -q 'no usage history' /tmp/dw_live.md; then
    ok "live mode: runs, writes a report, growth shown as 'no usage history' (exit $CODE)"
else
    bad "live mode: expected a clean report with exit 0-2 (got exit $CODE)"
fi

echo ""
echo "$PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
