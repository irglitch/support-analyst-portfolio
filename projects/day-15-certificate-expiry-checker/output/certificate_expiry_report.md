# Certificate Expiry Report

Checked: 7 certificate(s) · Reference date: 2026-11-21
Thresholds: WARNING ≤ 30 days · CRITICAL ≤ 14 days

## Summary

- 🔴 EXPIRED: **1**
- 🔴 CRITICAL (≤ 14 days): **1**
- 🟡 WARNING (≤ 30 days): **2**
- 🟢 OK: **3**

**Overall: 🔴 EXPIRED**

## Needs action

| Hostname | Service | Environment | Expires | Days left | Status | Owner |
|---|---|---|---|---|---|---|
| sftp.partnerbank.example.com | Settlement file transfer (SFTP) | Production | 2026-11-19 | -2 | 🔴 EXPIRED | Platform team |
| api.payments.example.com | Payment Gateway API | Production | 2026-11-23 | 2 | 🔴 CRITICAL | Payments team |
| sso.internal.example.com | Single Sign-On | Production | 2026-12-10 | 19 | 🟡 WARNING | Identity team |
| portal.customer.example.com | Customer Portal | Production | 2026-12-15 | 24 | 🟡 WARNING | Web team |

## OK — no action needed

| Hostname | Service | Expires | Days left | Owner |
|---|---|---|---|---|
| vpn.internal.example.com | VPN Gateway | 2027-01-30 | 70 | Network team |
| wiki.internal.example.com | Internal Wiki | 2027-03-02 | 101 | IT support |
| smtp.relay.example.com | Email Relay | 2027-05-18 | 178 | Platform team |

## What to do next

- EXPIRED: treat as an incident — the service is already failing for anyone validating the certificate. Escalate to the certificate owner immediately.
- CRITICAL: raise the renewal ticket today and confirm the renewal date with the owner. If it expires over a weekend, act before Friday.
- WARNING: raise the renewal ticket and add the expiry to the team calendar.

*Practice scenario with sample data, built for this portfolio — not employer work.*
