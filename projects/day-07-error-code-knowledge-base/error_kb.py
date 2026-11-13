#!/usr/bin/env python3
"""
Day 07 — Error Code Knowledge Base

Scenario: Friday morning, 09:20. A user calls: "Checkout is failing
with a timeout again." Every support team has seen most errors before
— the fix is usually already written down in an old ticket. The problem
is finding it: the last fix for this exact error lives in a ticket from
three weeks ago, and nobody remembers the ticket number.

This tool is a small, searchable knowledge base of past incidents. Each
entry records an error code, the system it belongs to, the symptom, the
root cause, and the fix that worked last time, with the original ticket
and how many times the error has been seen. The analyst searches by
error code or by a word from the symptom, and gets the known fix in
seconds instead of starting the investigation from zero.

Commands:
  search <query> [--out report.md]  search by error code or keyword
  list [--system NAME]              list entries, optionally one system
  stats                             totals, most-seen errors, per-system counts

Search ranking: an exact error-code match first, then a code substring
match, then keyword matches in the symptom / cause / fix. Within each
rank, entries seen most often come first — the fix that worked five
times beats the one that worked once.

Exit codes: 0 = match(es) found, 1 = no match, 2 = usage / file error.
No external dependencies. Python 3.9+.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REQUIRED_FIELDS = ("code", "system", "symptom", "cause", "fix",
                   "ticket", "resolved", "times_seen", "severity")

# Search scores — an exact code match must always outrank a keyword hit.
SCORE_EXACT_CODE = 100
SCORE_CODE_CONTAINS = 50
SCORE_SYMPTOM = 30
SCORE_CAUSE_OR_FIX = 20


def load_kb(path):
    """Load the knowledge base JSON; raise ValueError on bad data."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Knowledge base file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Knowledge base is not valid JSON: {exc}")

    entries = data.get("knowledge_base") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError("Knowledge base must be a JSON list (or an object "
                         "with a 'knowledge_base' list).")
    for i, entry in enumerate(entries):
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            raise ValueError(f"Entry {i} ({entry.get('code', '?')}) is missing "
                             f"field(s): {', '.join(missing)}")
    return entries


def score_entry(entry, query):
    """How well does this entry match the query? 0 = no match."""
    q = query.strip().lower()
    if not q:
        return 0
    code = entry["code"].lower()
    if q == code:
        return SCORE_EXACT_CODE
    if q in code:
        return SCORE_CODE_CONTAINS
    if q in entry["symptom"].lower():
        return SCORE_SYMPTOM
    if q in entry["cause"].lower() or q in entry["fix"].lower():
        return SCORE_CAUSE_OR_FIX
    return 0


def search_kb(entries, query):
    """Return [(entry, score)] sorted by score, then times seen."""
    scored = [(e, score_entry(e, query)) for e in entries]
    matches = [(e, s) for e, s in scored if s > 0]
    matches.sort(key=lambda pair: (-pair[1], -pair[0]["times_seen"],
                                   pair[0]["code"]))
    return matches


def filter_system(entries, system):
    """Entries for one system (case-insensitive), sorted by times seen."""
    wanted = system.strip().lower()
    found = [e for e in entries if e["system"].lower() == wanted]
    found.sort(key=lambda e: (-e["times_seen"], e["code"]))
    return found


def kb_stats(entries):
    """Totals, most-seen errors, and per-system counts."""
    total_seen = sum(e["times_seen"] for e in entries)
    by_system = Counter(e["system"] for e in entries)
    by_severity = Counter(e["severity"] for e in entries)
    most_seen = sorted(entries, key=lambda e: (-e["times_seen"], e["code"]))[:3]
    return {
        "entries": len(entries),
        "systems": len(by_system),
        "total_seen": total_seen,
        "by_system": dict(sorted(by_system.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "most_seen": most_seen,
    }


def format_entry(entry, score=None):
    lines = [
        f"### {entry['code']} — {entry['symptom']}",
        "",
        f"- **System:** {entry['system']} · **Severity:** {entry['severity']} · "
        f"**Seen:** {entry['times_seen']} time(s) · **Last fixed:** "
        f"{entry['resolved']} ({entry['ticket']})",
        f"- **Cause:** {entry['cause']}",
        f"- **Fix that worked:** {entry['fix']}",
    ]
    if score is not None:
        lines.append(f"- **Match:** {'exact error code' if score >= SCORE_EXACT_CODE else 'error code contains the query' if score >= SCORE_CODE_CONTAINS else 'keyword in the symptom' if score >= SCORE_SYMPTOM else 'keyword in the cause or fix'}")
    lines.append("")
    return lines


def build_search_report(query, matches, source_name):
    lines = [
        "# Error Code Knowledge Base — Search Report",
        "",
        f"**Knowledge base:** `{source_name}`  ",
        f"**Search:** `{query}`  ",
        f"**Matches:** {len(matches)}",
        "",
    ]
    if not matches:
        lines += [
            "No entry matches this query. That does not mean the error is new — "
            "try a shorter word from the error message, or the system name with "
            "`list --system`. If it really is new, write it up after the fix so "
            "the next analyst finds it here.",
            "",
        ]
    else:
        lines += [
            "Entries are ranked: exact error-code match first, then code "
            "substring, then keyword in the symptom / cause / fix. Within each "
            "rank, the fix seen most often comes first.",
            "",
            "## Matches",
            "",
        ]
        for entry, score in matches:
            lines += format_entry(entry, score)
        lines += [
            "## What to do with the top match",
            "",
            f"1. Try the fix for **{matches[0][0]['code']}** first — it worked "
            f"{matches[0][0]['times_seen']} time(s) before.",
            "2. If the fix works, note the ticket number in your ticket so the "
            "next analyst can trace it back.",
            "3. If the fix does NOT work, do not keep retrying it — the symptom "
            "may look the same but the cause may be new. Escalate with the "
            "evidence and add a new entry once the real cause is found.",
            "",
        ]
    lines += ["Next steps, escalation path and RCA prompts: see `RUNBOOK.md`."]
    return "\n".join(lines) + "\n"


def print_stats(stats):
    print(f"Knowledge base: {stats['entries']} entries across "
          f"{stats['systems']} systems, seen {stats['total_seen']} times in total.")
    print("\nEntries per system:")
    for system, count in stats["by_system"].items():
        print(f"  {system}: {count}")
    print("\nEntries per severity:")
    for severity, count in stats["by_severity"].items():
        print(f"  {severity}: {count}")
    print("\nMost-seen errors (the ones worth memorising):")
    for entry in stats["most_seen"]:
        print(f"  {entry['code']} ({entry['system']}) — {entry['times_seen']} "
              f"time(s), last fixed {entry['resolved']} ({entry['ticket']})")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Error Code Knowledge Base — search past-incident fixes.")
    parser.add_argument("kb", help="Knowledge base JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search by error code or keyword")
    p_search.add_argument("query", help="Error code (e.g. ORA-12154) or keyword (e.g. timeout)")
    p_search.add_argument("--out", help="Write the Markdown report to this file")

    p_list = sub.add_parser("list", help="List entries, optionally one system")
    p_list.add_argument("--system", help="Show only this system")

    sub.add_parser("stats", help="Totals, most-seen errors, per-system counts")

    args = parser.parse_args(argv)

    try:
        entries = load_kb(args.kb)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.command == "search":
        matches = search_kb(entries, args.query)
        report = build_search_report(args.query, matches, Path(args.kb).name)
        if args.out:
            Path(args.out).write_text(report, encoding="utf-8")
            print(f"Report written to {args.out}")
        else:
            print(report)
        if matches:
            top = matches[0][0]
            print(f"Top match: {top['code']} — {top['symptom']} "
                  f"(seen {top['times_seen']}x, {top['ticket']}). "
                  f"Fix: {top['fix']}")
            return 0
        print(f"No match for '{args.query}'. Try a shorter word from the "
              "error message, or `list --system <name>`.")
        return 1

    if args.command == "list":
        shown = filter_system(entries, args.system) if args.system else sorted(
            entries, key=lambda e: (e["system"], e["code"]))
        if args.system and not shown:
            print(f"No entries for system '{args.system}'. Systems in the "
                  f"knowledge base: {', '.join(sorted({e['system'] for e in entries}))}.")
            return 1
        for entry in shown:
            print(f"{entry['code']:10} {entry['system']:15} "
                  f"seen {entry['times_seen']}x  {entry['symptom']}")
        print(f"\n{len(shown)} entr{'y' if len(shown) == 1 else 'ies'} shown.")
        return 0

    if args.command == "stats":
        print_stats(kb_stats(entries))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
