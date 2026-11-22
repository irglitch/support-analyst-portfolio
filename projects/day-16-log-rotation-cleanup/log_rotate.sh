#!/usr/bin/env bash
# log_rotate.sh — Log rotation & cleanup automation
#
# What it does: the permanent fix for a log directory that grows forever.
# A support analyst's morning disk check (see Day 14) can say "/var/log is
# full" — this tool does something about it, safely. For every log file it
# decides, under a retention policy, whether to:
#   - COMPRESS it (plain .log older than --retention-days, default 30)
#   - DELETE it   (a .log.gz archive older than --delete-days, default 90)
#   - KEEP it     (inside its retention window)
#   - SKIP it     (still being written to, or not a log file at all)
#
# Safety is the point of this tool, not a side effect:
#   - DRY-RUN BY DEFAULT. Nothing is compressed or deleted unless you pass
#     --apply. A scheduler can run the dry-run daily and alert on exit 1.
#   - An ACTIVE log (modified in the last 60 minutes) is never touched,
#     even with --retention-days 0 — compressing the file the application
#     is writing to right now would corrupt the log and the evidence.
#   - Only *.log / *.log.* files are ever acted on. Anything else in the
#     directory is listed as skipped and left alone.
#   - --dir / is refused outright, and a missing directory is an error.
#   - Manifest mode (a captured inventory) is report-only: --apply with
#     --manifest is refused, because the files listed may not exist here.
#
# Usage:
#   ./log_rotate.sh --dir DIR [--retention-days N] [--delete-days N]
#                   [--apply] [--now 'YYYY-MM-DD HH:MM'] [--out report.md]
#   ./log_rotate.sh --manifest FILE [--now 'YYYY-MM-DD HH:MM'] [--out report.md]
#   --dir DIR        Scan a real log directory (live mode)
#   --manifest FILE  Read a captured inventory instead of scanning:
#                    one line per file, "SIZE_BYTES EPOCH_MTIME PATH"
#                    (capture it with: find /var/log -type f
#                     -printf '%s %T@ %p\n' > inventory.txt)
#   --retention-days N  Compress plain logs at least N days old (default 30)
#   --delete-days N     Delete .gz archives at least N days old (default 90)
#   --apply          Actually compress/delete (default is dry-run)
#   --now '...'      Pretend "now" is this date/time (default: current time)
#                    — makes a report reproducible from a captured inventory
#   --out FILE       Write the Markdown report to FILE (default: stdout)
#
# Exit codes: 0 = all logs within policy (or --apply finished cleanly),
# 1 = dry-run found files to compress/delete (cleanup pending),
# 2 = usage/safety error, or an --apply action failed.
# Only standard Linux tools are used (find, gzip, date, awk, stat).
set -u

DIR=""
MANIFEST=""
OUT_FILE=""
NOW_STR=""
APPLY=0
RETENTION_DAYS=30
DELETE_DAYS=90
ACTIVE_SECS=3600   # a file modified within the last hour is "active"
COMPRESS_SAVING=85 # gzip on text logs: assume ~85% of the size is freed

usage() {
    echo "Usage: $0 (--dir DIR | --manifest FILE) [--retention-days N] [--delete-days N] [--apply] [--now 'YYYY-MM-DD HH:MM'] [--out FILE]"
    echo "  --dir DIR          Scan a real log directory"
    echo "  --manifest FILE    Read a captured 'SIZE EPOCH PATH' inventory instead of scanning (report-only)"
    echo "  --retention-days N Compress plain logs at least N days old (default 30)"
    echo "  --delete-days N    Delete .gz archives at least N days old (default 90)"
    echo "  --apply            Actually compress/delete (default is a dry-run that changes nothing)"
    echo "  --now '...'        Pretend now is this date/time, e.g. '2026-11-22 09:20' (default: current time)"
    echo "  --out FILE         Write the Markdown report to FILE (default: print to stdout)"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)            DIR="${2:-}"; shift 2 ;;
        --manifest)       MANIFEST="${2:-}"; shift 2 ;;
        --retention-days) RETENTION_DAYS="${2:-}"; shift 2 ;;
        --delete-days)    DELETE_DAYS="${2:-}"; shift 2 ;;
        --apply)          APPLY=1; shift ;;
        --now)            NOW_STR="${2:-}"; shift 2 ;;
        --out)            OUT_FILE="${2:-}"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

# --- validation ------------------------------------------------------------
if [[ -n "$DIR" && -n "$MANIFEST" ]]; then
    echo "Error: pass --dir or --manifest, not both." >&2; exit 2
fi
if [[ -z "$DIR" && -z "$MANIFEST" ]]; then
    echo "Error: pass --dir DIR or --manifest FILE." >&2; usage; exit 2
fi
if [[ -n "$DIR" ]]; then
    if [[ "$DIR" == "/" ]]; then
        echo "Error: refusing to run log cleanup on / — pass a log directory such as /var/log." >&2; exit 2
    fi
    if [[ ! -d "$DIR" ]]; then
        echo "Error: directory not found: $DIR" >&2; exit 2
    fi
fi
if [[ -n "$MANIFEST" ]]; then
    if [[ ! -f "$MANIFEST" ]]; then
        echo "Error: manifest file not found: $MANIFEST" >&2; exit 2
    fi
    if [[ "$APPLY" -eq 1 ]]; then
        echo "Error: --apply is refused in manifest mode — a captured inventory is report-only, the files listed may not exist here." >&2; exit 2
    fi
fi
if ! [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]] || ! [[ "$DELETE_DAYS" =~ ^[0-9]+$ ]]; then
    echo "Error: --retention-days and --delete-days must be whole numbers of days." >&2; exit 2
fi

# --- "now" ------------------------------------------------------------------
if [[ -n "$NOW_STR" ]]; then
    NOW_EPOCH=$(date -d "$NOW_STR" +%s 2>/dev/null) || { echo "Error: cannot parse --now '$NOW_STR' (use 'YYYY-MM-DD HH:MM')." >&2; exit 2; }
    NOW_LABEL="$NOW_STR"
else
    NOW_EPOCH=$(date +%s)
    NOW_LABEL=$(date '+%Y-%m-%d %H:%M %Z')
fi

# --- helpers ---------------------------------------------------------------
human() { # human BYTES -> e.g. 9.20 GB / 850.00 MB / 12.00 KB / 512 B
    awk -v b="$1" 'BEGIN {
        if (b >= 1000000000) printf "%.2f GB", b/1000000000
        else if (b >= 1000000) printf "%.2f MB", b/1000000
        else if (b >= 1000) printf "%.2f KB", b/1000
        else printf "%d B", b
    }'
}

# --- gather the inventory --------------------------------------------------
if [[ -n "$MANIFEST" ]]; then
    MODE="manifest ($MANIFEST)"
    INVENTORY=$(cat "$MANIFEST")
else
    MODE="live ($DIR)"
    INVENTORY=$(find "$DIR" -type f \( -name '*.log' -o -name '*.log.*' \) -printf '%s %T@ %p\n' 2>/dev/null | sort -t' ' -k3)
fi

# --- classify every file ---------------------------------------------------
REPORT=""
add_line() { REPORT+="$1"$'\n'; }

COMPRESS_ROWS=""; DELETE_ROWS=""; ACTIVE_ROWS=""; KEEP_ROWS=""; SKIP_ROWS=""
N_TOTAL=0; BYTES_TOTAL=0
N_COMPRESS=0; BYTES_COMPRESS=0
N_DELETE=0; BYTES_DELETE=0
N_KEEP=0; N_ACTIVE=0; N_SKIP=0
APPLY_ERROR=0
FREED_ACTUAL=0          # measured bytes freed, --apply runs only
FREED_COMPRESS_ACTUAL=0 # measured bytes freed by compression, --apply only
declare -A DIR_COUNT DIR_BYTES

while read -r size epoch path; do
    [[ -z "$size" || -z "$epoch" || -z "$path" ]] && continue
    epoch=${epoch%%.*}  # find %T@ prints a float; keep whole seconds
    N_TOTAL=$((N_TOTAL + 1))
    BYTES_TOTAL=$((BYTES_TOTAL + size))
    dir=${path%/*}; [[ -z "$dir" || "$dir" == "$path" ]] && dir="/"
    DIR_COUNT["$dir"]=$(( ${DIR_COUNT["$dir"]:-0} + 1 ))
    DIR_BYTES["$dir"]=$(( ${DIR_BYTES["$dir"]:-0} + size ))

    base=${path##*/}
    age_secs=$((NOW_EPOCH - epoch))
    [[ $age_secs -lt 0 ]] && age_secs=0
    age_days=$((age_secs / 86400))
    age_label="${age_days} days"
    [[ $age_days -eq 1 ]] && age_label="1 day"
    if [[ $age_days -eq 0 ]]; then
        if [[ $age_secs -lt 60 ]]; then age_label="just now"; else age_label="$((age_secs / 60)) min"; fi
    fi

    # 1. Not a log file at all — never acted on (only appears in manifest
    #    mode; live mode only finds *.log files in the first place).
    if [[ "$base" != *.log && "$base" != *.log.* ]]; then
        N_SKIP=$((N_SKIP + 1))
        SKIP_ROWS+="| SKIP | \`$path\` | $(human "$size") | $age_label | not a .log file — left alone |"$'\n'
        continue
    fi
    # 2. Active — modified in the last hour, the app may be writing to it
    #    right now. Never rotated, whatever the retention setting is.
    if [[ $age_secs -lt $ACTIVE_SECS ]]; then
        N_ACTIVE=$((N_ACTIVE + 1))
        if [[ $age_secs -lt 60 ]]; then MOD_WHEN="modified just now"; else MOD_WHEN="modified $age_label ago"; fi
        ACTIVE_ROWS+="| ACTIVE — skipped | \`$path\` | $(human "$size") | $age_label | $MOD_WHEN — still being written, never rotate an active log |"$'\n'
        continue
    fi
    # 3. Compressed archive — delete once it is past the archive window.
    if [[ "$base" == *.gz ]]; then
        if [[ $age_days -ge $DELETE_DAYS ]]; then
            N_DELETE=$((N_DELETE + 1))
            BYTES_DELETE=$((BYTES_DELETE + size))
            if [[ "$APPLY" -eq 1 ]]; then
                if rm -f -- "$path"; then
                    FREED_ACTUAL=$((FREED_ACTUAL + size))
                    DELETE_ROWS+="| DELETED | \`$path\` | $(human "$size") | $age_label | archive older than ${DELETE_DAYS} days — deleted, freed $(human "$size") |"$'\n'
                else
                    APPLY_ERROR=1
                    DELETE_ROWS+="| ERROR | \`$path\` | $(human "$size") | $age_label | delete failed — file left in place, investigate permissions |"$'\n'
                fi
            else
                DELETE_ROWS+="| DELETE | \`$path\` | $(human "$size") | $age_label | archive older than ${DELETE_DAYS} days — delete, frees $(human "$size") |"$'\n'
            fi
        else
            N_KEEP=$((N_KEEP + 1))
            KEEP_ROWS+="| KEEP | \`$path\` | $(human "$size") | $age_label | archive within the ${DELETE_DAYS}-day retention |"$'\n'
        fi
        continue
    fi
    # 4. Plain log — compress once it is past the retention window.
    if [[ $age_days -ge $RETENTION_DAYS ]]; then
        N_COMPRESS=$((N_COMPRESS + 1))
        BYTES_COMPRESS=$((BYTES_COMPRESS + size))
        est_freed=$(( size * COMPRESS_SAVING / 100 ))
        if [[ "$APPLY" -eq 1 ]]; then
            if gzip -f -- "$path" 2>/dev/null; then
                new_size=$(stat -c%s -- "$path.gz" 2>/dev/null || echo 0)
                freed=$(( size - new_size ))
                FREED_COMPRESS_ACTUAL=$((FREED_COMPRESS_ACTUAL + freed))
                FREED_ACTUAL=$((FREED_ACTUAL + freed))
                COMPRESS_ROWS+="| COMPRESSED | \`$path\` | $(human "$size") | $age_label | log older than ${RETENTION_DAYS} days — gzipped to ${base}.gz, freed $(human "$freed") |"$'\n'
            else
                APPLY_ERROR=1
                COMPRESS_ROWS+="| ERROR | \`$path\` | $(human "$size") | $age_label | gzip failed — file left in place, investigate permissions |"$'\n'
            fi
        else
            COMPRESS_ROWS+="| COMPRESS | \`$path\` | $(human "$size") | $age_label | log older than ${RETENTION_DAYS} days — gzip to ${base}.gz (est. frees $(human "$est_freed")) |"$'\n'
        fi
    else
        N_KEEP=$((N_KEEP + 1))
        KEEP_ROWS+="| KEEP | \`$path\` | $(human "$size") | $age_label | log within the ${RETENTION_DAYS}-day retention |"$'\n'
    fi
done <<< "$INVENTORY"

# --- totals ----------------------------------------------------------------
# Dry-run / manifest: the freed figure is an ESTIMATE (gzip on text logs is
# assumed to leave ~15% of the original size). --apply runs measure the
# real freed bytes during the classification loop (FREED_ACTUAL).
EST_FREED_COMPRESS=$(( BYTES_COMPRESS * COMPRESS_SAVING / 100 ))
EST_FREED_TOTAL=$(( EST_FREED_COMPRESS + BYTES_DELETE ))
if [[ "$APPLY" -eq 1 ]]; then
    FREED_LABEL="Actual"
    FREED_COMPRESS_SHOWN="$FREED_COMPRESS_ACTUAL"
    FREED_TOTAL_SHOWN="$FREED_ACTUAL"
else
    FREED_LABEL="Estimated"
    FREED_COMPRESS_SHOWN="$EST_FREED_COMPRESS"
    FREED_TOTAL_SHOWN="$EST_FREED_TOTAL"
fi
AFTER_BYTES=$(( BYTES_TOTAL - FREED_TOTAL_SHOWN ))

# --- report ----------------------------------------------------------------
HOST=$(hostname)
if [[ "$APPLY" -eq 1 ]]; then RUN_LABEL="APPLY — files were compressed/deleted"; else RUN_LABEL="dry-run — no files changed"; fi

add_line "# Log Rotation & Cleanup Report — $HOST"
add_line ""
add_line "**When:** $NOW_LABEL · **Mode:** $MODE · **Run:** $RUN_LABEL"
add_line ""
add_line "Policy: compress plain logs older than **${RETENTION_DAYS} days**, delete \`.gz\` archives older than **${DELETE_DAYS} days**. Files modified in the last 60 minutes are active and never touched. Compression saving estimated at ${COMPRESS_SAVING}% (gzip on text logs) unless the run applied the changes."
add_line ""
add_line "## Summary"
add_line ""
add_line "| | Count | Size |"
add_line "|---|---|---|"
add_line "| Files scanned | $N_TOTAL | $(human "$BYTES_TOTAL") |"
add_line "| To compress | $N_COMPRESS | $(human "$BYTES_COMPRESS") → $FREED_LABEL freed $(human "$FREED_COMPRESS_SHOWN") |"
add_line "| To delete | $N_DELETE | $(human "$BYTES_DELETE") freed |"
add_line "| **$FREED_LABEL total freed** | | **$(human "$FREED_TOTAL_SHOWN")** ($(human "$BYTES_TOTAL") → ~$(human "$AFTER_BYTES") after cleanup) |"
add_line "| Kept within policy | $N_KEEP | |"
add_line "| Active logs skipped | $N_ACTIVE | |"
add_line "| Not log files, skipped | $N_SKIP | |"
add_line ""
add_line "## Space by directory"
add_line ""
add_line "| Directory | Files | Total |"
add_line "|---|---|---|"
DIR_SUMMARY=$(for d in "${!DIR_COUNT[@]}"; do
    printf '%s\t%s\t%s\n' "${DIR_BYTES[$d]}" "$d" "${DIR_COUNT[$d]}"
done | sort -nr)
while IFS=$'\t' read -r b d c; do
    [[ -z "$b" ]] && continue
    add_line "| \`$d\` | $c | $(human "$b") |"
done <<< "$DIR_SUMMARY"
add_line ""
add_line "## Actions"
add_line ""
add_line "| Action | File | Size | Age | Detail |"
add_line "|---|---|---|---|---|"
[[ -n "$COMPRESS_ROWS" ]] && add_line "$COMPRESS_ROWS"
[[ -n "$DELETE_ROWS" ]] && add_line "$DELETE_ROWS"
[[ -n "$ACTIVE_ROWS" ]] && add_line "$ACTIVE_ROWS"
[[ -n "$KEEP_ROWS" ]] && add_line "$KEEP_ROWS"
[[ -n "$SKIP_ROWS" ]] && add_line "$SKIP_ROWS"
add_line ""
add_line "## Conclusion"
add_line ""
if [[ "$APPLY_ERROR" -eq 1 ]]; then
    add_line "**Cleanup finished with errors.** At least one compress/delete action failed — see the ERROR rows above. The files were left in place; check permissions and ownership on those paths, then re-run."
elif [[ "$APPLY" -eq 1 ]]; then
    if [[ $((N_COMPRESS + N_DELETE)) -eq 0 ]]; then
        add_line "**Nothing to do — all logs within policy.** The run found no file past its retention window, so nothing was compressed or deleted."
    else
        add_line "**Cleanup complete.** $N_COMPRESS log(s) compressed and $N_DELETE archive(s) deleted. Re-run the tool to confirm: the next run should report nothing to do (exit 0). Schedule this as a weekly job so the directory never grows back to a disk incident — see RUNBOOK.md."
    fi
elif [[ $((N_COMPRESS + N_DELETE)) -gt 0 ]]; then
    add_line "**DRY-RUN — cleanup pending.** $N_COMPRESS log(s) to compress and $N_DELETE archive(s) to delete, freeing an estimated $(human "$FREED_TOTAL_SHOWN"). Nothing was changed by this run. Review the actions above, then re-run with \`--apply\` — or schedule the apply run — before the next batch window. See RUNBOOK.md before deleting anything that might be needed for audit."
else
    add_line "**All logs within policy.** No file is past its retention window, so there is nothing to compress or delete. Re-run at the next morning check — a log directory that starts growing again will show up here before it becomes a disk incident (see Day 14)."
fi
add_line ""

# --- exit code ---------------------------------------------------------------
if [[ "$APPLY_ERROR" -eq 1 ]]; then
    WORST=2
elif [[ "$APPLY" -eq 1 ]]; then
    WORST=0
elif [[ $((N_COMPRESS + N_DELETE)) -gt 0 ]]; then
    WORST=1
else
    WORST=0
fi

# --- output ------------------------------------------------------------------
if [[ -n "$OUT_FILE" ]]; then
    mkdir -p "$(dirname "$OUT_FILE")"
    printf '%s' "$REPORT" > "$OUT_FILE"
    echo "Report written to $OUT_FILE"
else
    printf '%s' "$REPORT"
fi

exit "$WORST"
