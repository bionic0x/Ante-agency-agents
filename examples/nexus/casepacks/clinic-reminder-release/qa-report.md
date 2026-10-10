# Release QA report — Larkfield Booking 5.8.0 (synthetic)

Prepared by: QA, Larkfield Health Group (fictional)
Date: 6 October 2026

| Gate | Result |
|---|---|
| Automated tests | 412 of 412 passed |
| Regression suite (booking, cancellation, rescheduling) | PASS |
| Performance (p95 booking time under 1.2 s) | PASS, 0.84 s |
| Accessibility (WCAG 2.2 AA, booking flow) | PASS |
| SMS and push delivery (staging, 3 carriers) | PASS, all messages delivered |
| Security scan | PASS, no high or critical findings |

**Overall: PASS. QA has no objection to release.**

Scope note: message tests check that reminders are delivered on time and that
the date, time and links are correct. Message wording is owned by Product.
