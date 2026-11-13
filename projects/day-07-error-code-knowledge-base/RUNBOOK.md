# Runbook — Error Code Knowledge Base (Day 07)

## 1. Verify before you escalate (5 minutes)
- **A KB hit is a lead, not a diagnosis.** The symptom may look the
  same but the cause may be new — check the evidence before applying
  the old fix. For a timeout, confirm *which* timeout: a gateway
  timeout (PAY-3002) and a database connection timeout (DB-1045) need
  opposite fixes, and applying the wrong one wastes the call.
- Check the entry's date and ticket: a fix from six months ago may
  refer to a system that has since moved, been patched, or been
  retired. If the ticket says the fix was a workaround, say so in
  your ticket.
- If the top match's fix does not work within one attempt, stop and
  re-investigate — do not keep retrying a fix that worked last time
  but is failing now. That is exactly how a new incident gets
  mislabelled as a repeat.
- If the search returns nothing, try a shorter word from the error
  message, or `list --system <name>` to browse. A no-match is
  information too: this error may genuinely be new.

## 2. Escalate with facts, not feelings
Paste into the ticket / team channel:
- **Error code + KB entry + ticket** — e.g. "Checkout timeout matches
  PAY-3002 (INC-1048, seen 6x): vendor status page showed degraded
  service last time"
- **What you already tried from the KB** — "checked the vendor status
  page — currently green, so this is not the known vendor outage"
- **What you did NOT do** — "did not restart the app — DB-1045's fix
  says the pool exhausts again if you restart before clearing the
  batch sessions"
- **If it is a new error** — "no KB entry for this code; opening a new
  incident and will write the entry up once the cause is confirmed"

Escalation path: a **P1 KB hit whose fix fails** goes to the owning
team (database / payments / web) with the KB entry and the ticket
attached — they need to know the known fix was tried and failed. A
**new error with no KB entry** is a normal investigation; escalate on
its own severity, not on the lack of a KB hit.

## 3. Communicate
- Tell the user what you found in plain language: "We've seen this
  timeout before — last time it was the payment provider, and here's
  what we're checking first" beats "I've raised a ticket".
- If the KB fix works, tell the user it was a known issue with a known
  fix — that builds confidence. If it doesn't work, say so honestly:
  "The usual fix didn't work this time, so we're investigating it as
  a new cause."
- When the business asks "how often does this happen?", the KB has
  the answer: the times-seen count and the last-fixed date are the
  frequency, not a guess.

## 4. After recovery
- **Update the entry.** If the fix worked, bump `times_seen` and the
  `resolved` date — a stale count understates how often the error
  really hits. If a different fix worked, add the new cause and fix
  as a note (or a second entry) instead of overwriting the old one —
  the same code can have two causes.
- **Add the new errors.** Every incident that had no KB entry when it
  arrived gets an entry after the fix, with the code, symptom, cause,
  fix, ticket, and date. A knowledge base that only grows when someone
  remembers to update it dies within a month — make the entry part of
  closing the ticket.
- Re-run the search after the update — the entry should now be
  findable by the code *and* by the words the user actually used.

## 5. RCA prompts
- Which error has the highest `times_seen` — PAY-3002 at 6 — and why
  hasn't its root cause been permanently fixed? A KB entry that keeps
  growing is a problem record waiting to be written, not a success.
- Are the same codes recurring after a fix that was marked permanent?
  If so, the fix was a workaround — flag it for the owning team.
- Which systems have the most entries? If one system dominates the
  base, that is where the next monitoring or fix effort belongs.
- Problem record: an error seen 5+ times with the same cause is a
  known error — link the KB entry to a problem ticket so the permanent
  fix gets tracked instead of the workaround being repeated.
