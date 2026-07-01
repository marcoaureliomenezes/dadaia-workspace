release: none
phase: none
---

# Active release: none

**v0.1.45** — *panel redesign* — is **CLOSED and ARCHIVED** at
`specs/_archive/releases/v0.1.45/` (CLOSURE.md). It rebuilt the panel: the Workflows tab
leads with per-workflow diagram cards whose expand is a legible fluxogram + formatted
per-step cards + inline per-step model pickers (codex/pi toggle + profile dropdown incl.
`pi-openrouter-kimi-high` → `kimi-2.7` selectable/savable); the **Agentic tab was deleted
entirely** (with its Kanban + personas sub-views); modern token-anchored restyle; pi model
openness. Shipped via PR #80 (`0bcc2e69`), all 35 CI checks green (incl. E2E panel
Playwright). Also folded the SPEC-DOC-016 archive-grandfathering that unblocked pushes.

No release is currently active.

**Next — v0.1.46 (SDD Governance v2):** the `sdd-governance-v2-agents-lifecycle` EPIC
(FEAT-GOV-V2-01), scoped by the 2026-07-01 compliance audit
(`specs/audits/20260701T135346Z-6145b869/`). Pillars: (1) **bugs → event-sourced JSONL**
(`specs/bugs/<ts>.jsonl`, `dadaia bugs append|status|stats` CLI, event schema, doctor
invariant, one-time `*.md`→JSONL migration) + **rewrite the `bug-registration-guardrail`
rule for JSONL** (same release, or the drift regrows); (2) the `_archive` FROZEN taxonomy +
audit-disposition law; (3) the **OpenCode product-memory sweep** (~11 atoms still describe
OpenCode as live, removed v0.1.24); (4) disposition cleanup (archive 76 closed bugs,
disposition ~14 audits, normalize statuses).
