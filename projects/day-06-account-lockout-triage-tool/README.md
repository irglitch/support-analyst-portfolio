# Day 06 — Account Lockout Triage Tool

## 📟 The situation (real-world use case)

**Thursday, 09:20 — the helpdesk phone rings.** *"I can't log in — it
says my account is locked."* It's the most common first-line support
call there is, and the fix depends entirely on *why* the user is locked
out. Guessing wrong wastes everyone's time: resetting a password that
already expired doesn't help, unlocking an account that was disabled
for a leaver is a security incident waiting to happen, and telling a
user to "try again" when their authenticator is broken just burns
another attempt.

## 🔧 The fix

`lockout_triage.py` reads an account export and the login-attempt log
and checks the likely causes **in order** for every user (or one user
with `--user`), producing a one-page **Account Lockout Triage Report**:

1. **Account DISABLED** — do not re-enable; refer to the identity team
   with manager approval
2. **Account LOCKED** — how many failed attempts, when it locked, and
   from which device (failures clustering on one source usually mean a
   stale saved password on that device)
3. **Password EXPIRED** — the user needs a reset, not an unlock
4. **MFA failing after a correct password** — the password is fine, the
   authenticator is the problem
5. **Repeated failures (5+ in the last hour)** — lockout is imminent;
   stop retrying and reset first
6. **Password EXPIRING SOON (within 7 days)** — warn now, avoid
   tomorrow's lockout call
7. **RESOLVED** — a failure followed by a success is a typo, not a
   lockout
8. **NO LOGIN ATTEMPTS** — verify the basics: right username, right
   system, caps lock, VPN

The tool never unlocks or resets anything itself — it tells the
analyst exactly what to do next, and who needs to do it. **Exit codes
a scheduler can use:** 0 = nobody needs action, 1 = user-actionable
(reset / MFA / expiring), 2 = admin action needed (locked / disabled).

## ▶️ Run it

```bash
cd projects/day-06-account-lockout-triage-tool
python3 lockout_triage.py sample_data/accounts.csv sample_data/login_attempts.csv --out output/triage_report.md
cat output/triage_report.md
```

Triage one caller only:

```bash
python3 lockout_triage.py sample_data/accounts.csv sample_data/login_attempts.csv --user priya.k
```

**Result on the sample data (checked at 09:20):** 🔴 ADMIN ACTION
NEEDED — 2 users need the identity team: **priya.k** is locked (5
failed logins, 3 of them from the Mobile mail app — a stale saved
password — locked at 09:05, password itself still valid until
2026-12-20) and **chen.l** is disabled (last login 2026-10-30, do not
re-enable). 3 more are helpdesk-fixable: **sam.r**'s password expired
yesterday, **ana.m**'s password works but MFA failed 3 times in a row,
and **jordan.p**'s password expires in 3 days. **alex.d** already got
in (typo) and **mia.t** has no login attempts at all — check the
basics before assuming a lockout.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

First-line support triage · Account lockout diagnosis · Identity &
access basics (lockout vs expiry vs MFA vs disabled) · CSV data
handling · Python scripting · Support documentation · Escalation with
evidence

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
