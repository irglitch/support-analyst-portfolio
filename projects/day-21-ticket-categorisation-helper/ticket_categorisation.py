#!/usr/bin/env python3
"""Ticket Categorisation Helper — Day 21 of the support analyst portfolio.

Scenario: Friday 09:20, the morning triage queue holds eight overnight
tickets. Two arrived as low-priority "General" queries but describe a
checkout outage; one is a duplicate report of the same payment errors;
one says only "system slow" with no service named. A queue read top to
bottom by arrival time works the password reset before the outage.
Support triages first: what is it, how urgent is it really, and which
queue owns it?

This tool reads the morning queue (JSON — see sample_data/tickets.json)
and, for each ticket, scores transparent keyword rules over the subject
and description to suggest a category, a priority (from impact and
urgency signals, not from the reporter's guess), and a routing queue.
It then flags where the suggestion disagrees with what is on the
ticket — miscategorised, priority too low or too high — spots likely
duplicates (same service, shared error code or subject words), and
marks low-confidence tickets for human review instead of guessing.
Every suggestion shows the keywords that drove it, so an analyst can
agree or overrule in seconds.

Exit codes: 0 = every ticket already categorised and prioritised
correctly, 1 = actions found (re-categorise / re-prioritise / merge /
review), 2 = error (file missing / unreadable / wrong shape).

Usage:
  python3 ticket_categorisation.py sample_data/tickets.json
  python3 ticket_categorisation.py sample_data/tickets.json \\
      --out output/ticket_categorisation_report.md --generated-at "2026-11-27 09:20"
  python3 ticket_categorisation.py sample_data/tickets.json --ticket TKT-3101

Python standard library only. The tool only reads and suggests — it
never edits, merges, or closes a ticket; those calls stay with the
analyst on triage.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Category rules: category -> (routing queue, [(keyword, weight), ...]).
# Weights favour specific phrases ("settlement file") over generic
# words ("error") so a vague ticket scores low and goes to review.
CATEGORY_RULES = {
    "Incident — Application Error": ("Application Support L2", [
        ("500", 2), ("error", 1), ("failed", 1), ("crash", 2),
        ("timeout", 2), ("exception", 2), ("not working", 1),
        ("broken", 1), ("template not found", 3),
    ]),
    "Incident — Service Outage": ("Application Support L2", [
        ("down", 2), ("outage", 3), ("unavailable", 2),
        ("all customers", 3), ("nobody can", 3), ("cannot access", 2),
        ("connection refused", 3),
    ]),
    "Batch & File Transfer": ("Application Support L2", [
        ("settlement file", 3), ("batch", 2), ("file missing", 3),
        ("did not arrive", 2), ("sftp", 2), ("job failed", 2),
    ]),
    "Access Request": ("Service Desk", [
        ("password reset", 3), ("locked out", 2), ("new starter", 2),
        ("access request", 3), ("permission", 1), ("account", 1),
    ]),
    "How-To / Knowledge": ("Service Desk", [
        ("how do i", 3), ("how to", 2), ("training", 2),
        ("guidance", 2), ("where can i find", 2),
    ]),
    "Certificate & Security": ("Application Support L2", [
        ("certificate", 3), ("expires", 1), ("tls", 2), ("ssl", 2),
        ("expiry", 2),
    ]),
}

# Impact/urgency signals that drive the suggested priority.
P1_SIGNALS = ["all customers", "outage", "nobody can", "revenue",
              "checkout down", "cannot trade", "service down"]
P2_SIGNALS = ["multiple users", "team cannot", "deadline today",
              "settlement", "expires monday", "blocking"]
P4_SIGNALS = ["how do i", "how to", "training", "when convenient",
              "new starter"]

VALID_PRIORITIES = ("P1", "P2", "P3", "P4")
MIN_CONFIDENCE = 0.5   # below this, a human decides
MIN_SCORE = 2          # a single weak keyword is not a categorisation


def ticket_text(ticket):
    """Lowercased subject + description — the text the rules score."""
    return (f"{ticket.get('subject', '')} {ticket.get('description', '')}"
            ).lower()


def score_categories(text):
    """Score every category against the text.

    Returns a list of (category, queue, score, matched_keywords)
    sorted by score descending.
    """
    scored = []
    for category, (queue, rules) in CATEGORY_RULES.items():
        score, matched = 0, []
        for keyword, weight in rules:
            if keyword in text:
                score += weight
                matched.append(keyword)
        scored.append((category, queue, score, matched))
    scored.sort(key=lambda item: item[2], reverse=True)
    return scored


def suggest_priority(ticket, text):
    """Suggest a priority from impact/urgency signals.

    Returns (priority, reasons). A wide-impact outage signal beats
    everything; a how-to question is P4 however it was logged.
    """
    reasons = []
    affected = ticket.get("affected_users")
    for signal in P1_SIGNALS:
        if signal in text:
            reasons.append(f'"{signal}" — wide business impact')
    # A large affected count alone is not a P1 (a certificate expiring
    # Monday affects many users but nothing is down yet) — it takes a
    # failure signal alongside the numbers.
    failure_signals = [s for s in ("500", "timeout", "down", "outage",
                                   "connection refused", "failed")
                       if s in text]
    if isinstance(affected, int) and affected >= 100 and failure_signals:
        reasons.append(f"{affected} affected users with failure signal "
                       f"'{failure_signals[0]}'")
    if reasons:
        return "P1", reasons
    for signal in P2_SIGNALS:
        if signal in text:
            reasons.append(f'"{signal}" — time-sensitive or blocking')
    if isinstance(affected, int) and affected >= 10:
        reasons.append(f"{affected} affected users")
    if reasons:
        return "P2", reasons
    for signal in P4_SIGNALS:
        if signal in text:
            reasons.append(f'"{signal}" — no service impact')
    if reasons:
        return "P4", reasons
    return "P3", ["no wide-impact or urgency signal — standard priority"]


def categorise_ticket(ticket):
    """Categorise one ticket.

    Returns a dict with the suggested category/queue/priority, the
    confidence, the evidence, and the action flags (miscategorised,
    priority mismatch, needs review).
    """
    text = ticket_text(ticket)
    scored = score_categories(text)
    top_category, top_queue, top_score, matched = scored[0]
    total = sum(item[2] for item in scored)
    confidence = round(top_score / total, 2) if total else 0.0
    # A tie at the top is not a decision — send it to a human.
    tied = len(scored) > 1 and scored[1][2] == top_score and top_score > 0

    priority, priority_reasons = suggest_priority(ticket, text)
    current_category = ticket.get("current_category", "")
    current_priority = str(ticket.get("current_priority", "")).upper()

    needs_review = top_score < MIN_SCORE or confidence < MIN_CONFIDENCE or tied
    actions = []
    if needs_review:
        if top_score < MIN_SCORE:
            actions.append("Needs human review — too little detail to categorise "
                           "(ask the reporter which service and what symptom)")
        elif tied:
            actions.append(f"Needs human review — '{top_category}' and "
                           f"'{scored[1][0]}' score equally")
        else:
            actions.append(f"Needs human review — low confidence "
                           f"({confidence:.0%}) in '{top_category}'")
    else:
        if current_category != top_category:
            actions.append(f"Re-categorise: '{current_category or 'unset'}' → "
                           f"'{top_category}', route to {top_queue}")
    if current_priority in VALID_PRIORITIES and current_priority != priority:
        direction = ("raise" if VALID_PRIORITIES.index(priority)
                     < VALID_PRIORITIES.index(current_priority) else "lower")
        actions.append(f"{direction.capitalize()} priority: {current_priority} → "
                       f"{priority} ({'; '.join(priority_reasons)})")
    if priority == "P1" and current_priority != "P1":
        actions.append("Possible hidden P1 — work this before the rest of the queue")

    return {
        "ticket_id": ticket.get("ticket_id", "?"),
        "subject": ticket.get("subject", ""),
        "service": ticket.get("service", ""),
        "current_category": current_category,
        "current_priority": current_priority,
        "suggested_category": None if needs_review else top_category,
        "suggested_queue": None if needs_review else top_queue,
        "suggested_priority": priority,
        "confidence": confidence,
        "matched_keywords": matched,
        "priority_reasons": priority_reasons,
        "needs_review": needs_review,
        "actions": actions,
    }


def subject_tokens(subject):
    """Significant subject words, for duplicate matching."""
    stop = {"the", "a", "an", "is", "on", "for", "to", "of", "and", "in"}
    return {word for word in re.findall(r"[a-z0-9-]+", subject.lower())
            if word not in stop and len(word) > 2}


def find_duplicates(tickets):
    """Flag likely duplicate pairs: same service and a shared error
    code or two or more shared subject words.

    Returns a list of (ticket_a, ticket_b, reason) tuples.
    """
    duplicates = []
    for i, first in enumerate(tickets):
        for second in tickets[i + 1:]:
            if not first.get("service") or first.get("service") != second.get("service"):
                continue
            codes_a = set(re.findall(r"[A-Z]{2,}-\d+", ticket_text(first).upper()))
            codes_b = set(re.findall(r"[A-Z]{2,}-\d+", ticket_text(second).upper()))
            shared_codes = codes_a & codes_b
            shared_words = (subject_tokens(first.get("subject", ""))
                            & subject_tokens(second.get("subject", "")))
            if shared_codes:
                duplicates.append((first.get("ticket_id", "?"),
                                   second.get("ticket_id", "?"),
                                   f"same service ({first['service']}), shared "
                                   f"error code {', '.join(sorted(shared_codes))}"))
            elif len(shared_words) >= 2:
                duplicates.append((first.get("ticket_id", "?"),
                                   second.get("ticket_id", "?"),
                                   f"same service ({first['service']}), shared "
                                   f"subject words: {', '.join(sorted(shared_words))}"))
    return duplicates


def load_tickets(path):
    """Load and shape-check the tickets file. Raises ValueError."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tickets = data.get("tickets") if isinstance(data, dict) else None
    if not isinstance(tickets, list) or not tickets:
        raise ValueError("expected a JSON object with a non-empty 'tickets' list")
    for ticket in tickets:
        if not isinstance(ticket, dict) or "ticket_id" not in ticket:
            raise ValueError("every ticket needs a ticket_id")
    return tickets


def build_report(results, duplicates, generated_at):
    """Build the Markdown triage report. Returns (markdown, action_count)."""
    lines = [
        "# Ticket Categorisation Report",
        "",
        f"Generated: {generated_at} · Tickets reviewed: {len(results)}",
        "",
    ]
    action_count = sum(1 for r in results if r["actions"]) + len(duplicates)
    hidden_p1 = [r for r in results
                 if r["suggested_priority"] == "P1" and r["current_priority"] != "P1"]
    if action_count:
        lines.append(f"## 🔴 Actions needed — {action_count} item(s)")
        lines.append("")
        if hidden_p1:
            lines.append(f"⚠️ **{len(hidden_p1)} possible hidden P1(s)** — "
                         "work these before the rest of the queue.")
            lines.append("")
    else:
        lines.append("## 🟢 Queue clean — every ticket is categorised and "
                     "prioritised correctly")
        lines.append("")

    for result in results:
        flag = "🔴" if result["actions"] else "🟢"
        lines.append(f"### {flag} {result['ticket_id']} — {result['subject']}")
        lines.append("")
        lines.append(f"- Service: {result['service'] or 'not stated'} · "
                     f"Currently: {result['current_category'] or 'unset'} / "
                     f"{result['current_priority'] or 'unset'}")
        if result["needs_review"]:
            lines.append(f"- Suggestion: **human review** "
                         f"(confidence {result['confidence']:.0%}, "
                         f"matched: {', '.join(result['matched_keywords']) or 'nothing'})")
        else:
            lines.append(f"- Suggestion: **{result['suggested_category']}** → "
                         f"{result['suggested_queue']} · "
                         f"**{result['suggested_priority']}** "
                         f"(confidence {result['confidence']:.0%}, "
                         f"matched: {', '.join(result['matched_keywords'])})")
        for action in result["actions"]:
            lines.append(f"- ▶ {action}")
        lines.append("")

    if duplicates:
        lines.append("## Possible duplicates — merge or link, do not work twice")
        lines.append("")
        for first, second, reason in duplicates:
            lines.append(f"- **{first}** ↔ **{second}** — {reason}")
        lines.append("")

    lines.append("## Ranked action list")
    lines.append("")
    ranked = sorted(results, key=lambda r: (
        0 if (r["suggested_priority"] == "P1" and r["current_priority"] != "P1") else 1,
        VALID_PRIORITIES.index(r["suggested_priority"])))
    step = 1
    for result in ranked:
        for action in result["actions"]:
            lines.append(f"{step}. **{result['ticket_id']}** — {action}")
            step += 1
    for first, second, reason in duplicates:
        lines.append(f"{step}. **{first} / {second}** — confirm the duplicate "
                     f"({reason}), link the reports, keep one master ticket")
        step += 1
    if step == 1:
        lines.append("No actions — the queue is triaged correctly.")
    lines.append("")
    lines.append("*Suggestions only — the analyst on triage confirms every "
                 "change before it is applied to the ticket.*")
    lines.append("")
    return "\n".join(lines), action_count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ticket Categorisation Helper")
    parser.add_argument("tickets_file", help="JSON file of tickets to triage")
    parser.add_argument("--out", help="write the report to this path")
    parser.add_argument("--generated-at", default="2026-11-27 09:20",
                        help="timestamp printed on the report")
    parser.add_argument("--ticket", help="re-check a single ticket, e.g. TKT-3101")
    args = parser.parse_args(argv)

    try:
        tickets = load_tickets(args.tickets_file)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: cannot read tickets file: {error}", file=sys.stderr)
        return 2

    if args.ticket:
        tickets = [t for t in tickets if t.get("ticket_id") == args.ticket]
        if not tickets:
            print(f"Error: ticket {args.ticket} not found", file=sys.stderr)
            return 2

    results = [categorise_ticket(ticket) for ticket in tickets]
    duplicates = find_duplicates(tickets) if not args.ticket else []
    report, action_count = build_report(results, duplicates, args.generated_at)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(report)
    return 1 if action_count else 0


if __name__ == "__main__":
    sys.exit(main())
