-- Day 09 — Database Lock / Slow Session Checker
-- Run against the `sessions` table loaded from sessions.csv.
-- Thresholds (match session_checker.py):
--   long-running active session:  > 600 seconds (10 minutes)
--   idle-in-transaction holding locks: > 300 seconds (5 minutes)
--   watch list: active sessions between 120 and 600 seconds

-- 1. Headline counts: total, active, blocked, idle / idle-in-transaction,
--    longest-running session.
SELECT COUNT(*),
       SUM(state = 'active'),
       SUM(state = 'blocked'),
       SUM(state LIKE 'idle%'),
       MAX(duration_seconds)
FROM sessions;

-- 2. Blocking chains: each blocker, what it is running, how long it has
--    been running, how many sessions it is blocking, and the longest wait.
SELECT b.session_id, b.username, b.application, b.query, b.duration_seconds,
       COUNT(s.session_id), MAX(s.duration_seconds)
FROM sessions s
JOIN sessions b ON b.session_id = s.blocking_session_id
GROUP BY b.session_id
ORDER BY COUNT(s.session_id) DESC, b.duration_seconds DESC;

-- 3. Blocked sessions: who is waiting, on what, and for how long.
SELECT session_id, username, application, query, wait_event,
       duration_seconds, blocking_session_id
FROM sessions
WHERE state = 'blocked'
ORDER BY duration_seconds DESC;

-- 4. Long-running active sessions (over 10 minutes) — not blocked, just slow.
SELECT session_id, username, application, query, duration_seconds
FROM sessions
WHERE state = 'active' AND duration_seconds > 600
ORDER BY duration_seconds DESC;

-- 5. Idle-in-transaction sessions holding locks (over 5 minutes).
SELECT session_id, username, application, query, duration_seconds
FROM sessions
WHERE state = 'idle in transaction' AND duration_seconds > 300
ORDER BY duration_seconds DESC;

-- 6. Watch list: active sessions between 2 and 10 minutes — not flagged,
--    but worth a second look if the slowness continues.
SELECT session_id, username, application, query, duration_seconds
FROM sessions
WHERE state = 'active' AND duration_seconds BETWEEN 120 AND 600
ORDER BY duration_seconds DESC;
