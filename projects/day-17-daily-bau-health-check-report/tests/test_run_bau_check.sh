#!/usr/bin/env bash
# Tests for run_bau_check.sh — the Day 17 wrapper.
# Run from the project directory: bash tests/test_run_bau_check.sh
set -eu
cd "$(dirname "$0")/.."

fail() { echo "FAIL: $1" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. Default (snapshot) mode writes a report and exits 2 on the RED sample data.
AS_OF=2026-11-23T09:20 ./run_bau_check.sh sample_data "$TMP/bau_report.md" > "$TMP/out.txt" || code=$?
code=${code:-0}
[[ "$code" == 2 ]] || fail "snapshot mode exit code was $code, expected 2 (RED)"
grep -q "Overall: 🔴 RED" "$TMP/bau_report.md" || fail "report has no RED verdict"
grep -q "notification-service" "$TMP/bau_report.md" || fail "report misses the down service"

# 2. --live mode collects a real snapshot on this host and still reports.
AS_OF=2026-11-23T09:20 ./run_bau_check.sh --live > "$TMP/live.txt" || code=$?
code=${code:-0}
[[ "$code" == 0 || "$code" == 1 || "$code" == 2 ]] || fail "live mode exit code $code is not 0/1/2"
[[ -s output/bau_report_live.md ]] || fail "live report was not written"
grep -q "Disk space" output/bau_report_live.md || fail "live report has no disk section"
# The live report reflects this machine, not the portfolio scenario —
# it is a test artefact, not a committed output.
rm -f output/bau_report_live.md

echo "run_bau_check.sh tests: PASS"
