---
name: fullaudit-consolidated-index
audit: constitution-memory-specs-tests full audit
date: 2026-06-30
session_id: 251bb5f3
surface: specs/constitution.md + specs/memory/** + tests/ + code
coordinator: claude (operator-directed)
---

# Full Audit — Consolidated Findings (constitution · memory · specs · tests)

Operator ask: full audit of backlog/bugs + specs, with the constitution reviewed
against SDD best practices (de-slop, re-scope between constitution and memory),
a memory audit (architecture.md, quality-assurance.md, product feature atoms),
and the current architecture + test architecture understood — culminating in a
**detailed release definition**.

Five specialist auditors ran in parallel; their reports sit beside this index:

| Report | Auditor | Scope |
|---|---|---|
| `ai-engineer-constitution-audit.md` | ai-engineer | constitution §0–§14 vs SDD best-practice; lean re-outline |
| `software-architect-architecture-vs-code.md` | software-architect | current architecture from code vs architecture.md; drift |
| `product-engineer-memory-canon-audit.md` | product-engineer | memory canon staleness/gaps/placement |
| `qa-engineer-test-architecture-audit.md` | qa-engineer | tests/ vs quality-assurance.md |
| `project-auditor-drift-scorecard-triage.md` | project-auditor | 6-dim scorecard + bug/backlog triage |

## Headline

The workspace is **healthy** (project-auditor overall drift **7.2/10**; specs doctor
0 errors; test pyramid healthy at 1424 tests; AI surface clean). The single dominant
defect is that **the constitution — the supreme governing doc — is the most stale
artifact in the tree.** It still encodes a removed harness (OpenCode) and a 5-member
runtime enum as live law, contradicting both the code (`AgentRuntimeKind` = 4 members)
and its own subordinate memory atoms (which already match the code). Memory and code
agree; only the constitution lagged the v0.1.24 OpenCode-removal sweep.

Two structural problems compound it:
1. **The constitution is ~65% mechanism/vision/changelog** (three sections — §0=184,
   §8=159, §11=80 lines — are 64% of 663). Per SDD best practice (GitHub Spec-Kit: a
   constitution is a small set of immutable, *verifiable* principles; their own
   brownfield constitution is 214 lines of principle+rationale with version history in
   a separate header), dadaia's is inverted: mechanism dominates the law.
2. **Double-sourcing is the root cause.** The harness/runtime roster is independently
   re-enumerated in constitution §0/§4/§5/§8 **and** ~10 memory atoms — a §12.3
   ("no fact in two sources") self-violation. The drift is the predicted consequence:
   the duplicated copies diverged. Fixing the OpenCode *strings* without
   **single-sourcing the enum** leaves the defect live (software-architect root-cause
   gate).

## Cross-auditor convergence (high confidence)

- **OpenCode drift is real, CRITICAL, and confined to the constitution + ~10 memory
  atoms.** Confirmed independently by all five. Code enum
  (`core/models/lifecycle.py:51`): `FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS`. Layer-1
  harnesses: `{claude, codex, pi}` — PI is the **third** harness, not the fourth.
  The 9 "opencode" refs in code are intentional anti-regression guards (+2 genuinely
  stale: an academy lesson, one env-var line).
- **"Ten allowed root entries" (incl `.opencode/`) is wrong** — enforced law is **nine**
  (matches root-whitelist + AGENTS.md 6-dir law). Constitution contradicts AGENTS.md.
- **architecture.md is accurate-but-oversized** (~93 KB, changelog-narrated,
  `token_estimate` understated >2×) → split + de-narrate; it is NOT the primary stale
  doc.
- **Test architecture is healthy**; quality-assurance.md issues are gaps, not
  contradictions.
- **Governance is healthy**; the OpenCode constitution drift is currently **orphaned**
  (no backlog item owns it); `sdd-governance-v2-agents-lifecycle` is a valid but
  *different* epic (bug-telemetry JSONL + audit-disposition law).

## Disposition

A new backlog candidate owns the orphaned drift and the full re-scoping:
**`specs/backlog/specs-truth-realignment-constitution-memory.md`** (written this
session). It is the detailed release definition feeding the next release after
v0.1.41 ships. A live foreign MUTATING lease (v0.1.41 CLOSURE, session 019f14b1…,
fresh heartbeat) currently holds dadaia-workspace, so the MUTATING rewrite must run as
the next release under the PM lease — not now.

## The one open bug (carry into the release)

`lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence` (MEDIUM) — FAKE
closure runtime is accepted then blocks at closure on "missing artifact evidence".
Same FAKE-runtime-honesty class as two already-Closed siblings. Owner: software-engineer.
