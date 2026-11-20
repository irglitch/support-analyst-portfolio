#!/usr/bin/env bash
# disk_watch.sh — Disk space early-warning check
#
# What it does: a support analyst's morning disk check that answers the
# question "will we run out of space today?" — not just "how full is it
# now?". For every filesystem it reports:
#   - current usage % against WARN (80%) / FAIL (90%) thresholds
#   - growth rate and estimated hours until full, from hourly history
#     (a mount at 70% growing 5%/h is more urgent than one at 88% that
#     has been flat for a week)
#   - inode usage % (a disk can be "full" on inodes while df shows space)
#   - the largest directories on the mounts that need attention
#
# Usage:
#   ./disk_watch.sh [--snapshot DIR] [--history FILE] [--out report.md]
#   --snapshot DIR   Run against captured output in DIR (df.txt,
#                    df_history.csv, du.txt, df_inode.txt) instead of live
#   --history FILE   Hourly usage history CSV for live mode
#                    (timestamp,mount,used_pct) — without it, growth shows
#                    as "no history"
#   --out FILE       Write the Markdown report to FILE (default: stdout)
#
# Exit codes: 0 = all filesystems healthy, 1 = at least one WARN,
# 2 = at least one FAIL, or a usage error.
# Only standard Linux tools are used (df, du, date, awk, sort).
set -u

SNAPSHOT_DIR=""
HISTORY_FILE=""
OUT_FILE=""

# Thresholds (tune per environment)
DISK_WARN=80      # disk used %
DISK_FAIL=90
INODE_WARN=80     # inode used %
INODE_FAIL=90
HOURS_WARN=24     # fills within 24 h -> WARN
HOURS_FAIL=4      # fills within 4 h  -> FAIL
BIG_DIR_GB=10     # flag directories at or above this size

usage() {
    echo "Usage: $0 [--snapshot DIR] [--history FILE] [--out FILE]"
    echo "  --snapshot DIR   Run against captured command output in DIR instead of live system"
    echo "  --history FILE   Hourly usage history CSV (timestamp,mount,used_pct) for live mode"
    echo "  --out FILE       Write the Markdown report to FILE (default: print to stdout)"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --snapshot) SNAPSHOT_DIR="${2:-}"; shift 2 ;;
        --history)  HISTORY_FILE="${2:-}"; shift 2 ;;
        --out)      OUT_FILE="${2:-}"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -n "$SNAPSHOT_DIR" && ! -d "$SNAPSHOT_DIR" ]]; then
    echo "Snapshot directory not found: $SNAPSHOT_DIR" >&2
    exit 2
fi
if [[ -n "$HISTORY_FILE" && ! -f "$HISTORY_FILE" ]]; then
    echo "History file not found: $HISTORY_FILE" >&2
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

band() { # band VALUE WARN FAIL -> PASS/WARN/FAIL (integer percent)
    awk -v v="$1" -v w="$2" -v f="$3" 'BEGIN {
        if (v >= f) print "FAIL"; else if (v >= w) print "WARN"; else print "PASS"
    }'
}

size_gb() { # size_gb "28G" -> size in GB (float); handles K/M/G/T
    awk -v s="$1" 'BEGIN {
        u = substr(s, length(s)); n = substr(s, 1, length(s)-1) + 0
        if (u == "T") print n * 1024
        else if (u == "G") print n
        else if (u == "M") print n / 1024
        else if (u == "K") print n / 1048576
        else print n
    }'
}

# forecast MOUNT CURRENT_PCT
# Prints one of: "nodata" | "stable" | "RATE|HOURS" (rate %/h, hours to full)
forecast() {
    local mount="$1" current="$2"
    local first_ts="" first_pct="" last_ts="" last_pct=""
    while IFS=, read -r ts m p; do
        [[ "$ts" == "timestamp" || -z "$ts" ]] && continue
        [[ "$m" != "$mount" ]] && continue
        if [[ -z "$first_ts" ]]; then first_ts="$ts"; first_pct="$p"; fi
        last_ts="$ts"; last_pct="$p"
    done <<< "$HISTORY_CSV"
    if [[ -z "$first_ts" || -z "$last_ts" || "$first_ts" == "$last_ts" ]]; then
        echo "nodata"; return
    fi
    local first_s last_s span_s
    first_s=$(date -d "$first_ts" +%s 2>/dev/null) || { echo "nodata"; return; }
    last_s=$(date -d "$last_ts" +%s 2>/dev/null)   || { echo "nodata"; return; }
    span_s=$((last_s - first_s))
    awk -v fp="$first_pct" -v lp="$last_pct" -v span="$span_s" -v cur="$current" 'BEGIN {
        hours = span / 3600
        if (hours <= 0) { print "nodata"; exit }
        rate = (lp - fp) / hours
        if (rate <= 0) { print "stable"; exit }
        ttf = (100 - cur) / rate
        if (ttf < 0) ttf = 0
        printf "%.2f|%.1f", rate, ttf
    }'
}

# --- data gathering (live or snapshot) -------------------------------------
if [[ -n "$SNAPSHOT_DIR" ]]; then
    MODE="snapshot ($SNAPSHOT_DIR)"
    DF_OUT=$(cat "$SNAPSHOT_DIR/df.txt")
    HISTORY_CSV=$(cat "$SNAPSHOT_DIR/df_history.csv" 2>/dev/null || echo "")
    DU_OUT=$(cat "$SNAPSHOT_DIR/du.txt" 2>/dev/null || echo "")
    INODE_OUT=$(cat "$SNAPSHOT_DIR/df_inode.txt" 2>/dev/null || echo "")
else
    MODE="live ($(hostname))"
    DF_OUT=$(df -hP)
    if [[ -n "$HISTORY_FILE" ]]; then
        HISTORY_CSV=$(cat "$HISTORY_FILE")
    else
        HISTORY_CSV=""
    fi
    DU_OUT=""   # filled in below, only for mounts that need attention
    INODE_OUT=$(df -iP 2>/dev/null || echo "")
fi

HOST=$(hostname)
NOW=$(date '+%Y-%m-%d %H:%M %Z')

# --- checks ----------------------------------------------------------------
add_line "# Disk Space Early-Warning Report — $HOST"
add_line ""
add_line "**When:** $NOW · **Mode:** $MODE"
add_line ""
add_line "Thresholds: disk WARN at ${DISK_WARN}%, FAIL at ${DISK_FAIL}%; a mount that fills within ${HOURS_WARN} h is WARN, within ${HOURS_FAIL} h is FAIL."
add_line ""
add_line "## Checks"
add_line ""
add_line "| Check | Status | Detail |"
add_line "|---|---|---|"

# Forecast summary lines, collected while checking each mount
FORECAST_LINES=""
# Mounts needing a directory scan (WARN or FAIL)
FLAG_MOUNTS=""

# 1. Disk usage + growth forecast, every listed filesystem
while read -r fs size used avail usepct mount; do
    [[ "$fs" == "Filesystem" ]] && continue
    [[ "$fs" == tmpfs || "$fs" == devtmpfs ]] && continue
    PCT_NUM=${usepct%\%}
    PCT_STATUS=$(band "$PCT_NUM" "$DISK_WARN" "$DISK_FAIL")

    FC=$(forecast "$mount" "$PCT_NUM")
    case "$FC" in
        nodata)
            GROWTH_STATUS="PASS"
            GROWTH_NOTE="no usage history — growth unknown"
            FORECAST_LINES+="| $mount | $usepct | no history | — |"$'\n'
            ;;
        stable)
            GROWTH_STATUS="PASS"
            GROWTH_NOTE="stable — no growth in the history window"
            FORECAST_LINES+="| $mount | $usepct | 0%/h | stable |"$'\n'
            ;;
        *)
            RATE=${FC%%|*}
            TTF=${FC##*|}
            FORECAST_LINES+="| $mount | $usepct | +${RATE}%/h | ~${TTF} h |"$'\n'
            if awk -v t="$TTF" -v f="$HOURS_FAIL" 'BEGIN { exit !(t < f) }'; then
                GROWTH_STATUS="FAIL"
            elif awk -v t="$TTF" -v w="$HOURS_WARN" 'BEGIN { exit !(t < w) }'; then
                GROWTH_STATUS="WARN"
            else
                GROWTH_STATUS="PASS"
            fi
            GROWTH_NOTE="fills in ~${TTF} h at +${RATE}%/h"
            ;;
    esac

    # Mount status is the worse of its usage band and its growth band
    if [[ "$PCT_STATUS" == "FAIL" || "$GROWTH_STATUS" == "FAIL" ]]; then
        MOUNT_STATUS="FAIL"
    elif [[ "$PCT_STATUS" == "WARN" || "$GROWTH_STATUS" == "WARN" ]]; then
        MOUNT_STATUS="WARN"
    else
        MOUNT_STATUS="PASS"
    fi
    if [[ "$MOUNT_STATUS" != "PASS" ]]; then
        FLAG_MOUNTS+="$mount"$'\n'
    fi

    check "Disk $mount" "$MOUNT_STATUS" \
        "$usepct used ($used of $size, $avail free) · $GROWTH_NOTE"
done <<< "$DF_OUT"

# 2. Inode usage — a filesystem can be "full" on inodes while df shows space
if [[ -n "$INODE_OUT" ]]; then
    while read -r fs inodes iused ifree iusepct mount; do
        [[ "$fs" == "Filesystem" ]] && continue
        [[ "$fs" == tmpfs || "$fs" == devtmpfs ]] && continue
        PCT_NUM=${iusepct%\%}
        check "Inodes $mount" \
            "$(band "$PCT_NUM" "$INODE_WARN" "$INODE_FAIL")" \
            "$iusepct used ($iused of $inodes inodes)"
    done <<< "$INODE_OUT"
fi

# --- growth forecast table -------------------------------------------------
add_line ""
add_line "## Growth forecast (from hourly history)"
add_line ""
add_line "| Mount | Now | Growth | Fills in |"
add_line "|---|---|---|---|"
add_line "$FORECAST_LINES"

# --- largest directories ---------------------------------------------------
add_line "## Largest directories"
add_line ""
if [[ -z "$FLAG_MOUNTS" ]]; then
    add_line "No mount is over its warning threshold, so no directory scan was run."
elif [[ -n "$SNAPSHOT_DIR" ]]; then
    add_line "Largest directories from the snapshot (flagged at ${BIG_DIR_GB}G and above — investigate these first):"
    add_line ""
    add_line '```'
    while read -r size path; do
        [[ -z "$size" ]] && continue
        GB=$(size_gb "$size")
        if awk -v g="$GB" -v b="$BIG_DIR_GB" 'BEGIN { exit !(g >= b) }'; then
            add_line "$size  $path  <-- large, investigate first"
        else
            add_line "$size  $path"
        fi
    done <<< "$DU_OUT"
    add_line '```'
else
    add_line "Directory scan for the mounts over threshold (top 5 per mount):"
    add_line ""
    add_line '```'
    while read -r mount; do
        [[ -z "$mount" ]] && continue
        add_line "--- $mount ---"
        DU_LIVE=$(du -sh "$mount"/* 2>/dev/null | sort -rh | head -5)
        while read -r size path; do
            [[ -z "$size" ]] && continue
            GB=$(size_gb "$size")
            if awk -v g="$GB" -v b="$BIG_DIR_GB" 'BEGIN { exit !(g >= b) }'; then
                add_line "$size  $path  <-- large, investigate first"
            else
                add_line "$size  $path"
            fi
        done <<< "$DU_LIVE"
    done <<< "$FLAG_MOUNTS"
    add_line '```'
fi
add_line ""

# --- conclusion ------------------------------------------------------------
add_line "## Conclusion"
add_line ""
case "$WORST" in
    0) add_line "**All filesystems healthy.** No mount is over its warning threshold and none is forecast to fill within ${HOURS_WARN} hours. Re-run at the next morning check — a mount that starts growing will show up here before it becomes an outage." ;;
    1) add_line "**Warning — disk pressure building.** At least one mount is over its warning threshold or is forecast to fill within ${HOURS_WARN} hours. Nothing has failed yet, but clear space or rotate logs on the WARN mounts today — see RUNBOOK.md before the next batch window." ;;
    2) add_line "**Failure — a filesystem needs action now.** At least one mount is over its failure threshold or fills within ${HOURS_FAIL} hours. Work the FAIL items above in order, start with the largest directories listed, and escalate with this report attached (see RUNBOOK.md). If a mount hits 100%, writes fail, logs stop, and the batch on that mount stops with it." ;;
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
