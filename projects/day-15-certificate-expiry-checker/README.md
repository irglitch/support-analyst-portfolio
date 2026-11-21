# Day 15 — Certificate Expiry Checker

## 📟 The situation (real-world use case)

**Saturday, 09:20.** The weekend on-call rota starts, and the last thing
anyone wants is a Monday-morning outage nobody saw coming. A TLS
certificate that expires unnoticed takes a service down with no warning:
users see "connection not secure", partner integrations stop handshaking,
and the overnight settlement file never arrives. Support keeps a
certificate inventory, and this morning's check is: *which certificates
expire soon, who owns them, and is anything already expired?*

## 🔧 The fix

`cert_expiry_checker.py` reads the certificate inventory (CSV) and
produces a one-page **Certificate Expiry Report**:

- Days remaining for every certificate, against WARN (≤ 30 days) /
  CRITICAL (≤ 14 days) thresholds
- **EXPIRED** certificates listed first — an expired certificate is an
  incident, not a reminder
- Certificates sorted worst-first, with the owning team named, so the
  renewal ticket goes to the right people without a hunt
- Exit codes for a scheduler: `0` all OK, `1` warning only,
  `2` critical or expired — so the check can run weekly and alert on its own
- Optional `--host` mode checks a live host's real certificate with the
  Python standard-library `ssl` module (no extra dependencies)

## ▶️ Run it

```bash
cd projects/day-15-certificate-expiry-checker
python3 cert_expiry_checker.py sample_data/certificates.csv --as-of 2026-11-21 --out output/certificate_expiry_report.md
cat output/certificate_expiry_report.md
```

**Result on the sample data (reference date 2026-11-21):** 7 certificates
checked — 🔴 **1 EXPIRED**, 🔴 **1 CRITICAL**, 🟡 **2 WARNING**, 🟢 **3 OK**.
The settlement file-transfer certificate
(`sftp.partnerbank.example.com`) expired **2 days ago** (2026-11-19) — that
is the incident to raise first. The Payment Gateway API certificate
(`api.payments.example.com`) expires in **2 days, on Monday 2026-11-23** —
it must be renewed before the weekend is over. SSO (19 days) and the
Customer Portal (24 days) need renewal tickets raised now. Exit code `2`.

Check one live host as well:

```bash
python3 cert_expiry_checker.py --host example.com
```

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

Certificate / TLS lifecycle awareness · Preventive monitoring · Threshold
and alert design (exit codes for schedulers) · Python scripting (stdlib
`ssl`/`csv`) · Escalation with a named owner and a deadline · Support
documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
