---
name: dd-code-review
description: >
  The reviewer's method: three independent axes reported side by side, never
  reranked — Standards (repo conventions + twelve Fowler smells), Spec (the diff does
  what the approved SPEC/TASKS say, nothing more), Bug-surface (the diff reduced or
  grew the touched feature's bug surface, evidenced from the ledger). Use when
  reviewing a PR, branch or commit range, or when a verdict needs the Bug-surface
  axis.
---

# dd-code-review

Three axes, run as three sequential passes (this workspace's sub-agents cannot
nest-dispatch; PM-dispatched siblings are the alternative). Findings from different
axes are reported side by side — an axis never outranks another.

## 1. When

- Reviewing a PR, branch or commit range before the candidate's PR.
- A curation, architecture or audit verdict needs the Bug-surface axis (§6).

## 2. Axis 1 — Standards

- The repo's own documented conventions come FIRST and always override the baseline.
- Skip anything tooling already enforces (ruff/mypy/import-linter findings are not review findings).
- Baseline: the twelve Fowler smells, each reported as a labelled judgement call, never a rule:
  Mysterious Name · Duplicated Code · Feature Envy · Data Clumps · Primitive Obsession ·
  Repeated Switches · Shotgun Surgery · Divergent Change · Speculative Generality ·
  Message Chains · Middle Man · Refused Bequest.
- Speak `dd-codebase-design`: a smell is usually a shallow module or a misplaced seam.
- Slop signals S1-S10, each with its diff check: [`SLOP.md`](SLOP.md) — reported inside this axis, never a fourth.

## 3. Axis 2 — Spec

- Read the approved SPEC/TASKS the diff claims to implement (`**Status:** Approved`).
- Does the diff do what they say — nothing more, nothing less?
- Scope growth beyond the task's declared write set is a finding, even when the code is good.
- Acceptance criteria without corresponding evidence (test/assertion) is a finding.

## 4. Axis 3 — Bug-surface

- Pull the touched feature's ledger slice: `dadaia bugs stats`, `dadaia bugs status --all` filtered to its surface/component.
- Answer WITH EVIDENCE: did this diff reduce, keep, or increase the feature's bug surface?
- The operator's rule applied as a review axis: a diff that GROWS the feature is a stop —
  a branch, flag, special case, second code path or cross-feature reach-in added by a fix
  is a puxadinho; name it and recommend the replace-don't-layer shape instead.
- An S4, S5 or S8 finding (`SLOP.md`) answers this axis "increased" until the finding is gone.

## 5. Reporting

- Findings carry: axis, severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), `file:line`, what the code does, fix direction (never code).
- The three axes appear side by side in the report; the verdict (`APPROVED`/`REJECTED` — the handoff schema's enum) follows the caller persona's rules.
- The Bug-surface answer is REQUIRED in every verdict — "tests green" is not a verdict.

## 6. The six lenses

One reviewer, six checklists applied on every verdict (ADR 0016); the engineer anticipates them.

- **Architecture** — root cause named; the diff shrinks or keeps the feature (`dd-codebase-design` deletion test); `dd-architecture-survey` at candidate close.
- **Security** — OWASP top 10, secrets, dependency CVEs (`pip-audit`/`npm audit`), CWE id per finding; never Fable on this lens.
- **QA** — every acceptance scenario has evidence; the pyramid holds; pruning only by a curation verdict (`dd-test-stewardship`).
- **Product** — the diff matches SPEC scope; memory atoms still tell the truth (`dd-release-implementation` MEMORY-UPDATE).
- **Audit** — `dd-audit-project` pillars over the window; findings, never fixes.
- **AI surface** — every agent, skill, rule or hook change satisfies `dd-ai-eng-knowhow` AUTHORING's fifteen rules.

## 7. References

- `dd-codebase-design` — the vocabulary the Standards and Bug-surface axes speak.
- `dd-test-stewardship` — test findings' lifecycle rules.
- Security depth / CVE / OWASP: the security lens (§6), never a fourth axis.
