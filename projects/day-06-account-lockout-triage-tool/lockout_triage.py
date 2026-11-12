#!/usr/bin/env python3
"""
Day 06 — Account Lockout Triage Tool

Scenario: Thursday morning, 09:20. The helpdesk phone rings: "I can't
log in — it says my account is locked." A locked-out user is the most
common first-line support call, and the fix depends entirely on *why*
they are locked out. Guessing wrong wastes everyone's time: resetting
a password that already expired doesn't help, and unlocking an account
that is disabled for a leaver is a security incident waiting to happen.

The tool reads two exports — an account list and the login-attempt log —
and checks the likely causes in order for every user (or one user with
--user), producing a triage report: the most likely cause, the evidence
for it, and the next step. It never unlocks or resets anything itself;
it tells the analyst exactly what to do next.

Checks, in order:
  1. Account DISABLED — needs the identity team / manager approval.
     The helpdesk must not re-enable it.
  2. Account LOCKED — how many failed attempts, when it locked, and
     from which device (a stale saved password on a phone is the usual
     suspect when the failures cluster on one source).
  3. Password EXPIRED — the user needs a reset, not an unlock.
  4. MFA failures AFTER a correct password — the password is fine, the
     authenticator is the problem.
  5. Repeated failures (5+ in the last hour) — lockout is imminent;
     stop retrying and reset the password first.
  6. Password EXPIRING SOON (within 7 days) — warn now, avoid
     tomorrow's lockout call.
  7. RESOLVED — a failure followed by a success is a typo, not a lockout.
  8. NO LOGIN ATTEMPTS — verify the basics: right username, right
     system, caps lock, VPN connected.

Input files (in sample_data/):
  accounts.csv:      username, full_name, status, password_expiry, mfa_enabled, last_login
  login_attempts.csv: timestamp, username, result, reason, source

Usage:
  python3 lockout_triage.py sample_data/accounts.csv sample_data/login_attempts.csv --out output/triage_report.md
  python3 lockout_triage.py sample_data/accounts.csv sample_data/login_attempts.csv --user priya.k
  python3 lockout_triage.py sample_data/accounts.csv sample_data/login_attempts.csv --now 2026-11-12T09:20 --out output/triage_report.md

Exit codes: 0 = nobody needs action, 1 = user-actionable (reset / MFA /
expiring soon), 2 = admin action needed (locked / disabled account).
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_NOW = "2026-11-12T09:20"
REPEATED_FAILURE_THRESHOLD = 5        # failures in the last hour
REPEATED_FAILURE_WINDOW = timedelta(hours=1)
EXPIRING_SOON_DAYS = 7
MFA_FAILURE_THRESHOLD = 2

# cause -> (label, emoji, needs_admin, action)
CAUSES = {
    "DISABLED": ("Account disabled", "🔴", True,
                 "Do NOT re-enable. Refer to the identity team with manager approval — "
                 "a disabled account is usually a leaver or a security hold."),
    "LOCKED": ("Account locked", "🔴", True,
               "Verify the caller's identity, then ask the identity team to unlock. "
               "After the unlock, clear the stale saved password on the device the "
               "failures came from, or it will lock again within minutes."),
    "EXPIRED": ("Password expired", "🟠", False,
                "Reset the password (self-service reset link, or a helpdesk reset). "
                "An unlock will not help — the password itself has expired."),
    "MFA": ("MFA failing after a correct password", "🟠", False,
            "Password is fine — the authenticator is the problem. Check the phone's "
            "clock/time sync, then re-enrol MFA or issue a temporary bypass code."),
    "REPEATED_FAILURES": ("Repeated failures — lockout imminent", "🟠", False,
                          "Tell the user to STOP retrying and reset the password now. "
                          "One more wrong attempt locks the account."),
    "EXPIRING_SOON": ("Password expiring soon", "🟡", False,
                      "Ask the user to change the password today, before it expires "
                      "and turns into tomorrow's lockout call."),
    "RESOLVED": ("Resolved — failed attempt, then logged in", "🟢", False,
                 "No action. It was a typo or a mistyped password; the user is in."),
    "NO_ATTEMPTS": ("No login attempts recorded", "⚪", False,
                    "Verify the basics first: right username, right system/URL, caps "
                    "lock off, VPN connected. The 'lockout' may be the wrong login page."),
    "UNCLEAR": ("Failures but no clear cause", "🟡", False,
                "Escalate to the identity team with the attempt log — do not keep "
                "guessing, and do not unlock blind."),
}


def parse_time(value):
    return datetime.fromisoformat(value.strip())


def load_accounts(path):
    accounts = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            accounts.append({
                "username": row["username"].strip(),
                "full_name": row["full_name"].strip(),
                "status": row["status"].strip().lower(),
                "password_expiry": datetime.fromisoformat(row["password_expiry"].strip()).date(),
                "mfa_enabled": row["mfa_enabled"].strip().lower() == "yes",
                "last_login": parse_time(row["last_login"]),
            })
    return accounts


def load_attempts(path):
    attempts = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            attempts.append({
                "timestamp": parse_time(row["timestamp"]),
                "username": row["username"].strip(),
                "result": row["result"].strip().lower(),
                "reason": row["reason"].strip().lower(),
                "source": row["source"].strip(),
            })
    return attempts


def triage_user(account, attempts, now):
    """Check the likely causes in order; return a triage dict."""
    user_attempts = sorted(
        (a for a in attempts if a["username"] == account["username"]),
        key=lambda a: a["timestamp"],
    )
    failures = [a for a in user_attempts if a["result"] == "failure"]
    recent_failures = [a for a in failures if now - a["timestamp"] <= REPEATED_FAILURE_WINDOW]
    mfa_failures = [a for a in failures if a["reason"] == "mfa failed"]
    locked_attempts = [a for a in user_attempts if a["result"] == "locked"]
    successes = [a for a in user_attempts if a["result"] == "success"]
    evidence = []

    def finish(cause, extra_evidence=()):
        label, emoji, needs_admin, action = CAUSES[cause]
        return {
            "username": account["username"],
            "full_name": account["full_name"],
            "cause": cause,
            "label": label,
            "emoji": emoji,
            "needs_admin": needs_admin,
            "action": action,
            "evidence": list(evidence) + list(extra_evidence),
            "attempts": len(user_attempts),
            "failures": len(failures),
        }

    # 1. Disabled
    if account["status"] == "disabled":
        evidence.append(f"Account status is 'disabled' in the account export; "
                        f"last successful login {account['last_login'].strftime('%Y-%m-%d %H:%M')}.")
        return finish("DISABLED")

    # 2. Locked
    if account["status"] == "locked":
        sources = Counter(a["source"] for a in failures)
        top_source, top_count = sources.most_common(1)[0] if sources else ("unknown", 0)
        evidence.append(f"{len(failures)} failed login(s) before the lock, "
                        f"{top_count} of them from '{top_source}'.")
        if locked_attempts:
            evidence.append(f"Account locked at {locked_attempts[-1]['timestamp'].strftime('%H:%M')} "
                            f"after the failures.")
        evidence.append("Password is still valid "
                        f"(expires {account['password_expiry'].isoformat()}), so this is a "
                        "lockout, not an expiry.")
        return finish("LOCKED")

    # 3. Password expired
    if account["password_expiry"] < now.date():
        expired_reasons = [a for a in failures if a["reason"] == "password expired"]
        evidence.append(f"Password expired on {account['password_expiry'].isoformat()} "
                        f"({(now.date() - account['password_expiry']).days} day(s) ago).")
        if expired_reasons:
            evidence.append(f"{len(expired_reasons)} login attempt(s) rejected with "
                            "'password expired'.")
        return finish("EXPIRED")

    # 4. MFA failing after a correct password
    if len(mfa_failures) >= MFA_FAILURE_THRESHOLD and successes:
        evidence.append(f"Password accepted ({len(successes)} successful login(s)), then "
                        f"{len(mfa_failures)} MFA failure(s) in a row.")
        return finish("MFA")

    # 5. Repeated failures — lockout imminent
    if len(recent_failures) >= REPEATED_FAILURE_THRESHOLD:
        sources = Counter(a["source"] for a in recent_failures)
        top_source, top_count = sources.most_common(1)[0]
        evidence.append(f"{len(recent_failures)} failed login(s) in the last hour, "
                        f"{top_count} from '{top_source}'.")
        return finish("REPEATED_FAILURES")

    # 6. Password expiring soon
    days_left = (account["password_expiry"] - now.date()).days
    if 0 <= days_left <= EXPIRING_SOON_DAYS:
        evidence.append(f"Password expires in {days_left} day(s) "
                        f"({account['password_expiry'].isoformat()}).")
        return finish("EXPIRING_SOON")

    # 7. Resolved — failure, then a success
    if successes and failures and successes[-1]["timestamp"] > failures[-1]["timestamp"]:
        evidence.append(f"{len(failures)} failed attempt(s), then a successful login at "
                        f"{successes[-1]['timestamp'].strftime('%H:%M')}.")
        return finish("RESOLVED")

    # 8. No login attempts at all
    if not user_attempts:
        evidence.append("No login attempts for this user in the log — nothing has "
                        "actually hit the system yet.")
        return finish("NO_ATTEMPTS")

    # Fallback
    evidence.append(f"{len(failures)} failed attempt(s) with no matching pattern above.")
    return finish("UNCLEAR")


def triage_all(accounts, attempts, now, username=None):
    results = []
    for account in accounts:
        if username and account["username"] != username:
            continue
        results.append(triage_user(account, attempts, now))
    return results


def exit_code(results):
    if any(r["needs_admin"] for r in results):
        return 2
    if any(r["cause"] not in ("RESOLVED", "NO_ATTEMPTS") for r in results):
        return 1
    return 0


def overall_status(results):
    if any(r["needs_admin"] for r in results):
        return "🔴 ADMIN ACTION NEEDED — locked or disabled account(s)"
    if any(r["cause"] not in ("RESOLVED", "NO_ATTEMPTS") for r in results):
        return "🟠 USER ACTION NEEDED — reset / MFA / expiring password"
    return "🟢 NO LOCKOUTS — nothing needs action"


def build_report(results, now, source_names):
    admin = [r for r in results if r["needs_admin"]]
    user_action = [r for r in results if not r["needs_admin"]
                   and r["cause"] not in ("RESOLVED", "NO_ATTEMPTS")]
    fine = [r for r in results if r["cause"] in ("RESOLVED", "NO_ATTEMPTS")]
    order = {"DISABLED": 0, "LOCKED": 1, "EXPIRED": 2, "MFA": 3,
             "REPEATED_FAILURES": 4, "EXPIRING_SOON": 5, "UNCLEAR": 6,
             "RESOLVED": 7, "NO_ATTEMPTS": 8}
    results = sorted(results, key=lambda r: order[r["cause"]])

    lines = [
        "# Account Lockout Triage Report",
        "",
        f"**Sources:** `{', '.join(source_names)}`  ",
        f"**Checked at:** {now.strftime('%Y-%m-%d %H:%M')}  ",
        f"**Overall status:** {overall_status(results)}  ",
        f"**Users checked:** {len(results)} · **Admin action needed:** {len(admin)} · "
        f"**User action needed:** {len(user_action)} · **No action:** {len(fine)}",
        "",
        "## Checks, in order",
        "",
        "1. Account disabled → 2. Account locked → 3. Password expired → "
        "4. MFA failing after a correct password → 5. Repeated failures "
        "(5+ in the last hour) → 6. Password expiring within 7 days → "
        "7. Resolved (failure, then a success) → 8. No login attempts at all.",
        "",
        "## Triage results",
        "",
    ]
    for r in results:
        lines += [
            f"### {r['emoji']} {r['full_name']} (`{r['username']}`) — {r['label']}",
            "",
            f"- **Attempts in log:** {r['attempts']} ({r['failures']} failed)",
        ]
        for e in r["evidence"]:
            lines.append(f"- **Evidence:** {e}")
        lines += [
            f"- **Next step:** {r['action']}",
            "",
        ]
    lines += [
        "## What to do now",
        "",
    ]
    if admin:
        lines.append("**🔴 Admin action needed — identity team:**")
        for r in admin:
            lines.append(f"- **{r['username']}** ({r['label'].lower()}): {r['action']}")
        lines.append("")
    if user_action:
        lines.append("**🟠 User action needed — helpdesk can fix:**")
        for r in user_action:
            lines.append(f"- **{r['username']}** ({r['label'].lower()}): {r['action']}")
        lines.append("")
    if not admin and not user_action:
        lines.append("No lockouts need action — see the per-user notes above.")
        lines.append("")
    lines += [
        "## Triage conclusion (auto-summary)",
        "",
    ]
    worst = results[0] if results else None
    if worst and worst["needs_admin"]:
        lines.append(
            f"{len(admin)} user(s) need the identity team — start with "
            f"**{worst['username']}** ({worst['label'].lower()}). "
            + (f"{len(user_action)} more user(s) can be fixed at the helpdesk "
               f"(first: **{user_action[0]['username']}**). " if user_action else "")
            + "Verify the caller's identity before any unlock or reset."
        )
    elif user_action:
        lines.append(
            f"No locked or disabled accounts. {len(user_action)} user(s) need a "
            f"reset or MFA fix — start with **{user_action[0]['username']}** "
            f"({user_action[0]['label'].lower()})."
        )
    else:
        lines.append("Nobody is locked out — the calls so far are typos or wrong-system "
                     "confusion. Keep the basics checklist handy.")
    lines += ["", "Next steps, escalation path and RCA prompts: see `RUNBOOK.md`."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Account Lockout Triage Tool — check the likely causes in order.")
    parser.add_argument("accounts", help="Account export CSV")
    parser.add_argument("attempts", help="Login attempts CSV")
    parser.add_argument("--user", help="Triage one username only")
    parser.add_argument("--now", default=DEFAULT_NOW,
                        help="Check time as ISO datetime (default: %(default)s)")
    parser.add_argument("--out", help="Write the Markdown report to this file")
    args = parser.parse_args(argv)

    now = parse_time(args.now)
    accounts = load_accounts(args.accounts)
    attempts = load_attempts(args.attempts)
    results = triage_all(accounts, attempts, now, args.user)
    if not results:
        print(f"No account found for user '{args.user}'." if args.user
              else "No accounts in the export.")
        return 3
    report = build_report(results, now,
                          [Path(args.accounts).name, Path(args.attempts).name])

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)
    print(f"Overall: {overall_status(results)} "
          f"({sum(1 for r in results if r['needs_admin'])} admin, "
          f"{sum(1 for r in results if not r['needs_admin'] and r['cause'] not in ('RESOLVED', 'NO_ATTEMPTS'))} user-action, "
          f"{sum(1 for r in results if r['cause'] in ('RESOLVED', 'NO_ATTEMPTS'))} no action)")
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
