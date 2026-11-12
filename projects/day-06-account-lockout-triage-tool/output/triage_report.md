# Account Lockout Triage Report

**Sources:** `accounts.csv, login_attempts.csv`  
**Checked at:** 2026-11-12 09:20  
**Overall status:** 🔴 ADMIN ACTION NEEDED — locked or disabled account(s)  
**Users checked:** 7 · **Admin action needed:** 2 · **User action needed:** 3 · **No action:** 2

## Checks, in order

1. Account disabled → 2. Account locked → 3. Password expired → 4. MFA failing after a correct password → 5. Repeated failures (5+ in the last hour) → 6. Password expiring within 7 days → 7. Resolved (failure, then a success) → 8. No login attempts at all.

## Triage results

### 🔴 Chen Li (`chen.l`) — Account disabled

- **Attempts in log:** 0 (0 failed)
- **Evidence:** Account status is 'disabled' in the account export; last successful login 2026-10-30 09:12.
- **Next step:** Do NOT re-enable. Refer to the identity team with manager approval — a disabled account is usually a leaver or a security hold.

### 🔴 Priya Kapoor (`priya.k`) — Account locked

- **Attempts in log:** 6 (5 failed)
- **Evidence:** 5 failed login(s) before the lock, 3 of them from 'Mobile mail app'.
- **Evidence:** Account locked at 09:05 after the failures.
- **Evidence:** Password is still valid (expires 2026-12-20), so this is a lockout, not an expiry.
- **Next step:** Verify the caller's identity, then ask the identity team to unlock. After the unlock, clear the stale saved password on the device the failures came from, or it will lock again within minutes.

### 🟠 Sam Reynolds (`sam.r`) — Password expired

- **Attempts in log:** 2 (2 failed)
- **Evidence:** Password expired on 2026-11-11 (1 day(s) ago).
- **Evidence:** 2 login attempt(s) rejected with 'password expired'.
- **Next step:** Reset the password (self-service reset link, or a helpdesk reset). An unlock will not help — the password itself has expired.

### 🟠 Ana Martins (`ana.m`) — MFA failing after a correct password

- **Attempts in log:** 4 (3 failed)
- **Evidence:** Password accepted (1 successful login(s)), then 3 MFA failure(s) in a row.
- **Next step:** Password is fine — the authenticator is the problem. Check the phone's clock/time sync, then re-enrol MFA or issue a temporary bypass code.

### 🟡 Jordan Patel (`jordan.p`) — Password expiring soon

- **Attempts in log:** 1 (0 failed)
- **Evidence:** Password expires in 3 day(s) (2026-11-15).
- **Next step:** Ask the user to change the password today, before it expires and turns into tomorrow's lockout call.

### 🟢 Alex Dube (`alex.d`) — Resolved — failed attempt, then logged in

- **Attempts in log:** 2 (1 failed)
- **Evidence:** 1 failed attempt(s), then a successful login at 08:56.
- **Next step:** No action. It was a typo or a mistyped password; the user is in.

### ⚪ Mia Thompson (`mia.t`) — No login attempts recorded

- **Attempts in log:** 0 (0 failed)
- **Evidence:** No login attempts for this user in the log — nothing has actually hit the system yet.
- **Next step:** Verify the basics first: right username, right system/URL, caps lock off, VPN connected. The 'lockout' may be the wrong login page.

## What to do now

**🔴 Admin action needed — identity team:**
- **priya.k** (account locked): Verify the caller's identity, then ask the identity team to unlock. After the unlock, clear the stale saved password on the device the failures came from, or it will lock again within minutes.
- **chen.l** (account disabled): Do NOT re-enable. Refer to the identity team with manager approval — a disabled account is usually a leaver or a security hold.

**🟠 User action needed — helpdesk can fix:**
- **sam.r** (password expired): Reset the password (self-service reset link, or a helpdesk reset). An unlock will not help — the password itself has expired.
- **ana.m** (mfa failing after a correct password): Password is fine — the authenticator is the problem. Check the phone's clock/time sync, then re-enrol MFA or issue a temporary bypass code.
- **jordan.p** (password expiring soon): Ask the user to change the password today, before it expires and turns into tomorrow's lockout call.

## Triage conclusion (auto-summary)

2 user(s) need the identity team — start with **chen.l** (account disabled). 3 more user(s) can be fixed at the helpdesk (first: **sam.r**). Verify the caller's identity before any unlock or reset.

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
