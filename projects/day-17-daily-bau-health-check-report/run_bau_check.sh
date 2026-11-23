#!/usr/bin/env bash
# run_bau_check.sh — Day 17 of the support analyst portfolio.
#
# Daily entry point for the BAU health check. Two modes:
#
#   ./run_bau_check.sh
#       Report from the snapshot in sample_data/ (or the directory in $1).
#       This is the reproducible path — the same inputs always give the
#       same report, which is what the committed output/ report uses.
#
#   ./run_bau_check.sh --live [service ...]
#       Collect a live snapshot on this Linux host first, then report on
#       it: disk usage from `df`, service state from `systemctl is-active`
#       (or `pgrep` when systemd is not available). Live values that
#       cannot be measured (latency, uptime, growth) are left blank, and
#       the report shows them as "—" rather than inventing a number.
#       SLA, files and certificates still come from sample_data/ — a live
#       collector for those needs the real ticket/file/cert systems, and
#       this script does not pretend to reach them.
#
# Exit code is the report's verdict: 0 GREEN, 1 AMBER, 2 RED.
# Usage: ./run_bau_check.sh [--live [service ...]] [input_dir] [out_file]

set -u
cd "$(dirname "$0")"

LIVE=0
if [[ "${1:-}" == "--live" ]]; then
    LIVE=1
    shift
fi

INPUT_DIR="${1:-sample_data}"
OUT_FILE="${2:-output/bau_report.md}"
AS_OF="${AS_OF:-}"

collect_live() {
    local snap_dir="$1"
    shift
    mkdir -p "$snap_dir"

    # --- disks: df -P (POSIX output, one line per filesystem) ---
    {
        echo "mount,total_gb,used_pct,inodes_pct,growth_pct_per_hour"
        df -P --output=target,size,pcent 2>/dev/null | tail -n +2 | while read -r mount size_kb pcent; do
            total_gb=$(awk -v kb="$size_kb" 'BEGIN { printf "%.1f", kb / 1048576 }')
            used="${pcent%\%}"
            inodes_pct=$(df -i -P --output=target,pcent 2>/dev/null \
                | awk -v m="$mount" '$1 == m { gsub(/%/, "", $2); print $2 }')
            echo "$mount,$total_gb,$used,${inodes_pct:-},"
        done
    } > "$snap_dir/disks.csv"

    # --- services: systemctl if present, else pgrep, else UNKNOWN ---
    {
        echo "service,status,latency_ms,latency_threshold_ms,uptime_pct,uptime_sla_pct,failed_probes,last_error,down_since"
        for svc in "$@"; do
            state="UNKNOWN"
            if command -v systemctl >/dev/null 2>&1 \
                && systemctl list-unit-files "$svc.service" 2>/dev/null | grep -q "^${svc}\."; then
                if systemctl is-active --quiet "$svc" 2>/dev/null; then
                    state="UP"
                else
                    state="DOWN"
                fi
            elif pgrep -f "$svc" >/dev/null 2>&1; then
                state="UP"
            fi
            failed=0
            [[ "$state" == "DOWN" ]] && failed=1
            echo "$svc,$state,,,,,,$failed,,"
        done
    } > "$snap_dir/services.csv"

    # SLA, files and certificates have no live source on this host —
    # carry the snapshot copies so the report still covers all five areas.
    for f in sla.csv files.csv certs.csv; do
        cp "sample_data/$f" "$snap_dir/$f"
    done
}

if [[ "$LIVE" == 1 ]]; then
    SERVICES=("$@")
    if [[ ${#SERVICES[@]} -eq 0 ]]; then
        # Default: the services in the sample inventory.
        mapfile -t SERVICES < <(tail -n +2 sample_data/services.csv | cut -d, -f1)
    fi
    SNAP_DIR="$(mktemp -d)"
    trap 'rm -rf "$SNAP_DIR"' EXIT
    collect_live "$SNAP_DIR" "${SERVICES[@]}"
    INPUT_DIR="$SNAP_DIR"
    OUT_FILE="output/bau_report_live.md"
fi

ARGS=(--input-dir "$INPUT_DIR" --out "$OUT_FILE")
if [[ -n "$AS_OF" ]]; then
    ARGS+=(--as-of "$AS_OF")
fi

python3 bau_report.py "${ARGS[@]}"
