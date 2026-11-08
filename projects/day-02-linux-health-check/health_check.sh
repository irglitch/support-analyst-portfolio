#!/usr/bin/env bash
# health_check.sh — "App is slow" first-response health check
#
# What it does: runs the standard first-response checks a support analyst
# performs when users report an application is slow — CPU load, memory,
# swap, disk space, top processes, and key service status — then writes a
# one-page Markdown report with PASS / WARN / FAIL per check.
#
# Usage:
#   ./health_check.sh [--out report.md]              # live checks on this host
#   ./health_check.sh --snapshot sample_data/slow_server --out output/health_check_report.md
#
# Exit codes: 0 = all checks PASS, 1 = at least one WARN, 2 = at least one FAIL.
# Only standard Linux tools are used (uptime, free, df, ps, nproc, systemctl).
set -u

SNAPSHOT_DIR=""
OUT_FILE=""
SERVICES="payment-api nginx postgresql file-watcher"

# Thresholds (tune per environment)
LOAD_WARN=1.0    # 1-min load per CPU core
LOAD_FAIL=2.0
MEM_WARN=80      # memory used %
MEM_FAIL=90
SWAP_WARN=10     # swap used %
SWAP_FAIL=50
DISK_WARN=80     # disk used %
DISK_FAIL=90
CPU_PROC_WARN=80 # single process %CPU

usage() {
    echo "Usage: $0 [--snapshot DIR] [--out FILE]"
    echo "  --snapshot DIR   Run against captured command output in DIR instead of live system"
    echo "  --out FILE       Write the Markdown report to FILE (default: print to stdout)"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --snapshot) SNAPSHOT_DIR="${2:-}"; shift 2 ;;
        --out)      OUT_FILE="${2:-}"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -n "$SNAPSHOT_DIR" && ! -d "$SNAPSHOT_DIR" ]]; then
    echo "Snapshot directory not found: $SNAPSHOT_DIR" >&2
    exit 2
fi

# --- report assembly -------------------------------------------------------
REPORT=""
WORST=0   # 0 PASS, 1 WARN, 2 FAIL

add_line() { REPORT+="$1"$'\n'; }

# status: PASS / WARN / FAIL — records the check and tracks the worst result
check() {
    local name="$1" status="$2" detail="$3"
    add_line "| $name | $status | $detail |"
    case "$status" in
        WARN) [[ $WORST -lt 1 ]] && WORST=1 ;;
        FAIL) WORST=2 ;;
    esac
}

pct() { # pct PART WHOLE -> integer percent, rounded
    awk -v p="$1" -v w="$2" 'BEGIN { if (w > 0) printf "%.0f", (p / w) * 100; else print 0 }'
}

band() { # band VALUE WARN FAIL -> PASS/WARN/FAIL (float-aware)
    awk -v v="$1" -v w="$2" -v f="$3" 'BEGIN {
        if (v >= f) print "FAIL"; else if (v >= w) print "WARN"; else print "PASS"
    }'
}

# --- data gathering (live or snapshot) -------------------------------------
if [[ -n "$SNAPSHOT_DIR" ]]; then
    MODE="snapshot ($SNAPSHOT_DIR)"
    UPTIME_LINE=$(cat "$SNAPSHOT_DIR/uptime.txt")
    CORES=$(cat "$SNAPSHOT_DIR/cores.txt")
    FREE_OUT=$(cat "$SNAPSHOT_DIR/free.txt")
    DF_OUT=$(cat "$SNAPSHOT_DIR/df.txt")
    PS_OUT=$(cat "$SNAPSHOT_DIR/ps.txt")
    SERVICES_OUT=$(cat "$SNAPSHOT_DIR/services.txt")
else
    MODE="live ($(hostname))"
    UPTIME_LINE=$(uptime)
    CORES=$(nproc)
    FREE_OUT=$(free -m)
    DF_OUT=$(df -hP)
    PS_OUT=$(ps aux --sort=-%cpu | head -6)
    if command -v systemctl >/dev/null 2>&1; then
        SERVICES_OUT=""
        for svc in $SERVICES; do
            # NB: is-active prints "inactive" AND exits non-zero for a missing
            # unit, so do not use `|| echo` here — it would append a second line.
            state=$(systemctl is-active "$svc" 2>/dev/null || true)
            if [[ -z "$state" ]]; then
                state="unknown"
            elif [[ "$state" == "inactive" ]] && ! systemctl list-unit-files "$svc.service" 2>/dev/null | grep -q "^$svc\.service"; then
                state="not-installed"
            fi
            SERVICES_OUT+="$svc $state"$'\n'
        done
    else
        SERVICES_OUT="systemctl not available on this host"
    fi
fi

HOST=$(hostname)
NOW=$(date '+%Y-%m-%d %H:%M %Z')

# --- checks ----------------------------------------------------------------
add_line "# Server Health Check — $HOST"
add_line ""
add_line "**When:** $NOW · **Mode:** $MODE"
add_line ""
add_line "## Checks"
add_line ""
add_line "| Check | Status | Detail |"
add_line "|---|---|---|"

# 1. CPU load (1-min average per core)
LOAD1=$(echo "$UPTIME_LINE" | awk -F'load average: ' '{print $2}' | awk -F',' '{print $1}' | tr -d ' ')
LOAD_PER_CORE=$(awk -v l="$LOAD1" -v c="$CORES" 'BEGIN { printf "%.2f", l / c }')
check "CPU load (1-min avg per core)" \
    "$(band "$LOAD_PER_CORE" "$LOAD_WARN" "$LOAD_FAIL")" \
    "load $LOAD1 on $CORES cores = $LOAD_PER_CORE per core"

# 2. Memory
MEM_TOTAL=$(echo "$FREE_OUT" | awk '$1 == "Mem:" {print $2}')
MEM_AVAIL=$(echo "$FREE_OUT" | awk '$1 == "Mem:" {print $7}')
MEM_USED_PCT=$(pct $((MEM_TOTAL - MEM_AVAIL)) "$MEM_TOTAL")
check "Memory used" \
    "$(band "$MEM_USED_PCT" "$MEM_WARN" "$MEM_FAIL")" \
    "$MEM_USED_PCT% used ($((MEM_TOTAL - MEM_AVAIL)) MB of $MEM_TOTAL MB)"

# 3. Swap
SWAP_TOTAL=$(echo "$FREE_OUT" | awk '$1 == "Swap:" {print $2}')
SWAP_USED=$(echo "$FREE_OUT" | awk '$1 == "Swap:" {print $3}')
SWAP_USED_PCT=$(pct "$SWAP_USED" "$SWAP_TOTAL")
check "Swap used" \
    "$(band "$SWAP_USED_PCT" "$SWAP_WARN" "$SWAP_FAIL")" \
    "$SWAP_USED_PCT% used ($SWAP_USED MB of $SWAP_TOTAL MB)"

# 4. Disk — every listed filesystem
while read -r fs size used avail usepct mount; do
    [[ "$fs" == "Filesystem" ]] && continue
    [[ "$fs" == tmpfs || "$fs" == devtmpfs ]] && continue
    PCT_NUM=${usepct%\%}
    check "Disk $mount" \
        "$(band "$PCT_NUM" "$DISK_WARN" "$DISK_FAIL")" \
        "$usepct used ($used of $size, $avail free)"
done <<< "$DF_OUT"

# 5. Top processes — flag any single process hogging CPU
TOP_PROC_LINE=$(echo "$PS_OUT" | awk 'NR > 1 {print $3, $11; exit}')
TOP_CPU=$(echo "$TOP_PROC_LINE" | awk '{print $1}')
TOP_CMD=$(echo "$TOP_PROC_LINE" | awk '{$1=""; sub(/^ /, ""); print}')
check "Top process CPU" \
    "$(band "$TOP_CPU" "$CPU_PROC_WARN" 100)" \
    "$TOP_CMD at ${TOP_CPU}% CPU"

# 6. Services
while read -r svc state; do
    [[ -z "$svc" ]] && continue
    if [[ "$state" == "active" ]]; then
        check "Service $svc" "PASS" "running"
    elif [[ "$state" == "unknown" ]]; then
        check "Service $svc" "WARN" "status could not be confirmed"
    elif [[ "$state" == "not-installed" ]]; then
        check "Service $svc" "WARN" "not installed on this host"
    else
        check "Service $svc" "FAIL" "state: $state"
    fi
done <<< "$SERVICES_OUT"

# --- details ---------------------------------------------------------------
add_line ""
add_line "## Top 5 processes by CPU"
add_line ""
add_line '```'
add_line "$PS_OUT"
add_line '```'
add_line ""
add_line "## Uptime"
add_line ""
add_line '```'
add_line "$UPTIME_LINE"
add_line '```'
add_line ""

# --- conclusion ------------------------------------------------------------
add_line "## Conclusion"
add_line ""
case "$WORST" in
    0) add_line "**All checks passed.** No resource pressure found on this host — if users still report slowness, check the application log and the database next (see RUNBOOK.md)." ;;
    1) add_line "**Warning — resource pressure building.** Nothing has failed yet, but at least one check is over its warning threshold. Investigate before it becomes an outage — start with the WARN items above (see RUNBOOK.md)." ;;
    2) add_line "**Failure — this host needs action now.** At least one check is over its failure threshold. The FAIL items above are the first suspects for the reported slowness — work them in order, then escalate with this report attached (see RUNBOOK.md)." ;;
esac
add_line ""

# --- output ----------------------------------------------------------------
if [[ -n "$OUT_FILE" ]]; then
    mkdir -p "$(dirname "$OUT_FILE")"
    printf '%s' "$REPORT" > "$OUT_FILE"
    echo "Report written to $OUT_FILE"
else
    printf '%s' "$REPORT"
fi

exit "$WORST"
