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

- Reviewing a PR, branch or commit range before the pre-PR checkpoint.
- A qa-engineer or software-architect verdict needs the Bug-surface axis.

## 2. Axis 1 — Standards

- The repo's own documented conventions come FIRST and always override the baseline.
- Skip anything tooling already enforces (ruff/mypy/import-linter findings are not review findings).
- Baseline: the twelve Fowler smells, each reported as a labelled judgement call, never a rule:
  Mysterious Name · Duplicated Code · Feature Envy · Data Clumps · Primitive Obsession ·
  Repeated Switches · Shotgun Surgery · Divergent Change · Speculative Generality ·
  Message Chains · Middle Man · Refused Bequest.
- Speak `dadaia-codebase-design`: a smell is usually a shallow module or a misplaced seam.

## 3. Axis 2 — Spec

- Read the approved SPEC/TASKS the diff claims to implement (`**Status:** Aprovado`).
- Does the diff do what they say — nothing more, nothing less?
- Scope growth beyond the task's declared write set is a finding, even when the code is good.
- Acceptance criteria without corresponding evidence (test/assertion) is a finding.

## 4. Axis 3 — Bug-surface

- Pull the touched feature's ledger slice: `dadaia bugs stats`, `dadaia bugs status --all` filtered to its surface/component.
- Answer WITH EVIDENCE: did this diff reduce, keep, or increase the feature's bug surface?
- The operator's rule applied as a review axis: a diff that GROWS the feature is a stop —
  a branch, flag, special case, second code path or cross-feature reach-in added by a fix
  is a puxadinho; name it and recommend the replace-don't-layer shape instead.

## 5. Reporting

- Findings carry: axis, severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), `file:line`, what the code does, fix direction (never code).
- The three axes appear side by side in the report; the verdict (APPROVE/REQUEST_CHANGES/COMMENT) follows the caller persona's rules.
- The Bug-surface answer is REQUIRED in every verdict — "tests green" is not a verdict.

## 6. References

- `dadaia-codebase-design` — the vocabulary the Standards and Bug-surface axes speak.
- `dadaia-test-stewardship` — test findings' lifecycle rules.
- Security depth / CVE / OWASP: `security-reviewer`'s lane, never re-run here.
