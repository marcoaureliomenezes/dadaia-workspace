release: none
phase: none
---

# Active release: none

**v0.1.46** — *SDD Governance v2 (bugs as event-sourced JSONL)* — is **CLOSED and ARCHIVED**
at `specs/_archive/releases/v0.1.46/` (CLOSURE.md). It fixed the long-standing bug-format
rot: JSONL was mandated for v0.1.15 and never delivered, so 99 `.md` bug files accreted.
This release shipped the event-sourced JSONL bug store + `dadaia bugs append|status|stats`
CLI, ran the one-time migration (99 `.md` → 18 JSONL streams, all `.md` archived to
`specs/bugs/_archive/`), rewrote the `bug-registration-guardrail` rule for the JSONL contract
(R-1 pair), added the `_archive` FROZEN gate-class + doctor SPEC-DOC-033/034/035/036 + the
audit-disposition law, and swept OpenCode-as-live from the product memory. Shipped via PR #82
(`f2fd4e22`), all 35 CI green; qa + security APPROVED.

No release is currently active.

**Follow-up — v0.1.47:** the audit-disposition **data** sweep (T-46-21 descope valve) —
disposition the ~14 undisposed audits, normalize the off-canon backlog statuses
(SPEC-DOC-031), and dedupe the HTML-report bug cluster. The now-live SPEC-DOC-035/036 doctor
warnings are the enforcing mechanism for this slipped work.
