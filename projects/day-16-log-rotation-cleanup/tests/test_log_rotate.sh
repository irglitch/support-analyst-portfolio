#!/usr/bin/env bash
# Tests for log_rotate.sh — run from the project directory:
#   bash tests/test_log_rotate.sh
#
# 8 checks: manifest dry-run finds the right actions and numbers, the
# freed-space maths is right, the active-log guard holds, a live dry-run
# changes nothing, a live --apply really compresses/deletes and a re-run
# then passes clean, the active guard holds even with --retention-days 0,
# and the safety errors refuse bad input.
set -u

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1

PASS=0
FAIL=0

ok()   { PASS=$((PASS + 1)); echo "ok   - $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "FAIL - $1"; }

# --- Test 1: manifest dry-run -> exit 1, right action counts ---------------
bash log_rotate.sh --manifest sample_data/inventory.txt --now '2026-11-22 09:20' --out /tmp/lr_manifest.md
CODE=$?
REPORT=$(cat /tmp/lr_manifest.md)
if [[ $CODE -eq 1 ]] \
   && echo "$REPORT" | grep -q '| To compress | 4 | 24.20 GB' \
   && echo "$REPORT" | grep -q '| To delete | 2 | 4.80 GB freed' \
   && echo "$REPORT" | grep -q '| Kept within policy | 6 |' \
   && echo "$REPORT" | grep -q '| Active logs skipped | 1 |' \
   && echo "$REPORT" | grep -q '| Not log files, skipped | 1 |'; then
    ok "manifest dry-run: exit 1, 4 compress / 2 delete / 6 keep / 1 active / 1 non-log skip"
else
    bad "manifest dry-run: expected exit 1 with 4/2/6/1/1 counts (got exit $CODE)"
fi

# --- Test 2: freed-space maths — 24.20 GB x 85% + 4.80 GB = 25.37 GB ------
# Compress 9.20+6.40+5.00+3.60 = 24.20 GB, est. freed 20.57 GB; delete
# 3.60+1.20 = 4.80 GB; total 25.37 GB; 36.57 GB -> ~11.20 GB after.
if echo "$REPORT" | grep -q 'Estimated freed 20.57 GB' \
   && echo "$REPORT" | grep -q 'Estimated total freed.*25.37 GB.*36.57 GB.*11.20 GB'; then
    ok "manifest dry-run: freed maths right — 20.57 GB from compression + 4.80 GB deleted = 25.37 GB"
else
    bad "manifest dry-run: expected 20.57 GB compression saving and 25.37 GB total freed"
fi

# --- Test 3: per-directory totals + active guard in the manifest ------------
if echo "$REPORT" | grep -q '| `/var/log/payment-api` | 6 | 28.00 GB |' \
   && echo "$REPORT" | grep -q 'ACTIVE — skipped.*crm-sync/sync.log.*15 min.*modified 15 min ago' \
   && echo "$REPORT" | grep -q '| SKIP | `/var/log/README.txt` | 2.00 KB | 90 days | not a .log file'; then
    ok "manifest dry-run: payment-api totals 28.00 GB, active sync.log skipped, README.txt skipped as non-log"
else
    bad "manifest dry-run: expected payment-api 28.00 GB, active skip and README.txt skip rows"
fi

# --- Test 4: live dry-run on a copy of the sample tree changes nothing -----
rm -rf /tmp/lr_live_dry && cp -rp sample_data/logs /tmp/lr_live_dry
BEFORE=$(find /tmp/lr_live_dry -type f -printf '%p %s %T@\n' | sort)
bash log_rotate.sh --dir /tmp/lr_live_dry --out /tmp/lr_live_dry.md
CODE=$?
AFTER=$(find /tmp/lr_live_dry -type f -printf '%p %s %T@\n' | sort)
REPORT_LIVE=$(cat /tmp/lr_live_dry.md)
if [[ $CODE -eq 1 ]] && [[ "$BEFORE" == "$AFTER" ]] \
   && echo "$REPORT_LIVE" | grep -q '| To compress | 4 |' \
   && echo "$REPORT_LIVE" | grep -q '| To delete | 1 |'; then
    ok "live dry-run: exit 1, 4 compress / 1 delete, and the tree is byte-for-byte unchanged"
else
    bad "live dry-run: expected exit 1 with 4/1 actions and no changes (got exit $CODE)"
fi

# --- Test 5: live --apply really compresses/deletes, re-run passes clean ---
rm -rf /tmp/lr_live_apply && cp -rp sample_data/logs /tmp/lr_live_apply
bash log_rotate.sh --dir /tmp/lr_live_apply --apply --out /tmp/lr_apply.md
CODE_APPLY=$?
REPORT_APPLY=$(cat /tmp/lr_apply.md)
bash log_rotate.sh --dir /tmp/lr_live_apply --out /tmp/lr_apply_rerun.md
CODE_RERUN=$?
REPORT_RERUN=$(cat /tmp/lr_apply_rerun.md)
if [[ $CODE_APPLY -eq 0 ]] \
   && [[ -f /tmp/lr_live_apply/payment-api/app.log.gz ]] \
   && [[ ! -f /tmp/lr_live_apply/payment-api/app.log ]] \
   && [[ ! -f /tmp/lr_live_apply/payment-api/app.log.2.gz ]] \
   && [[ -f /tmp/lr_live_apply/crm-sync/sync.log ]] \
   && echo "$REPORT_APPLY" | grep -q 'Actual total freed' \
   && echo "$REPORT_APPLY" | grep -q 'Cleanup complete' \
   && [[ $CODE_RERUN -eq 0 ]] \
   && echo "$REPORT_RERUN" | grep -q 'All logs within policy'; then
    ok "live --apply: exit 0, logs gzipped, old archive deleted, active log untouched, re-run exit 0 clean"
else
    bad "live --apply: expected real compression/deletion and a clean re-run (apply exit $CODE_APPLY, re-run exit $CODE_RERUN)"
fi

# --- Test 6: active guard holds even with --retention-days 0 ---------------
rm -rf /tmp/lr_active && mkdir -p /tmp/lr_active
head -c 1000 /dev/zero > /tmp/lr_active/old.log
head -c 1000 /dev/zero > /tmp/lr_active/fresh.log
touch -d "2 hours ago" /tmp/lr_active/old.log
touch -d "5 minutes ago" /tmp/lr_active/fresh.log
bash log_rotate.sh --dir /tmp/lr_active --retention-days 0 --apply --out /tmp/lr_active.md
CODE=$?
if [[ $CODE -eq 0 ]] \
   && [[ -f /tmp/lr_active/old.log.gz ]] \
   && [[ -f /tmp/lr_active/fresh.log ]] \
   && [[ ! -f /tmp/lr_active/fresh.log.gz ]] \
   && grep -q 'ACTIVE — skipped.*fresh.log' /tmp/lr_active.md; then
    ok "active guard: retention 0 still never compresses a log modified 5 min ago (old.log gzipped, fresh.log untouched)"
else
    bad "active guard: fresh.log must survive --retention-days 0 --apply (got exit $CODE)"
fi

# --- Test 7: safety errors — / refused, missing dir, manifest + --apply ----
ERR_ROOT=$(bash log_rotate.sh --dir / --out /tmp/lr_root.md 2>&1); CODE_ROOT=$?
ERR_MISSING=$(bash log_rotate.sh --dir sample_data/nope --out /tmp/lr_missing.md 2>&1); CODE_MISSING=$?
ERR_MANIFEST=$(bash log_rotate.sh --manifest sample_data/inventory.txt --apply --out /tmp/lr_mapply.md 2>&1); CODE_MANIFEST=$?
if [[ $CODE_ROOT -eq 2 ]] && echo "$ERR_ROOT" | grep -q 'refusing to run log cleanup on /' \
   && [[ $CODE_MISSING -eq 2 ]] && echo "$ERR_MISSING" | grep -q 'directory not found' \
   && [[ $CODE_MANIFEST -eq 2 ]] && echo "$ERR_MANIFEST" | grep -q 'refused in manifest mode'; then
    ok "safety errors: / refused, missing dir refused, --apply with --manifest refused (all exit 2)"
else
    bad "safety errors: expected exit 2 refusals for /, missing dir and manifest --apply (got $CODE_ROOT/$CODE_MISSING/$CODE_MANIFEST)"
fi

# --- Test 8: usage error — no --dir/--manifest, and --help works -----------
ERR_USAGE=$(bash log_rotate.sh --out /tmp/lr_usage.md 2>&1); CODE_USAGE=$?
HELP=$(bash log_rotate.sh --help 2>&1); CODE_HELP=$?
if [[ $CODE_USAGE -eq 2 ]] && echo "$ERR_USAGE" | grep -q 'pass --dir DIR or --manifest FILE' \
   && [[ $CODE_HELP -eq 0 ]] && echo "$HELP" | grep -q 'Usage:'; then
    ok "usage: missing mode errors exit 2, --help prints usage and exits 0"
else
    bad "usage: expected exit 2 without a mode and exit 0 for --help (got $CODE_USAGE/$CODE_HELP)"
fi

echo ""
echo "$PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
