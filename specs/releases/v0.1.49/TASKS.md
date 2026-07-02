# TASKS — v0.1.49 — Intake Integrity

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. One `[-]` per owner unless write
sets are disjoint (PLAN §Write sets).

## W0 — definition

- [x] T-49-01 ACTIVE → v0.1.49 DEFINITION; SPEC/PLAN/TASKS authored; architecture + QA
  definition reviews applied (both REJECT verdicts' amendments landed: AC-1 exact
  count 31/30, FR3 scoped to linted scaffold atoms with the single verified gap
  `Padrões de qualidade`, FR2 fixture-only tests + live probe as closure AC, W1/W5
  phase-disjoint note); all three `Aprovado`; definition commit. Owner:
  product-engineer (orchestrated).

## W1 — FR1 backlog repository truth (write set: `.gitignore`, `specs/backlog/` index)

- [x] T-49-10 Add the `specs/backlog/` opt-in block to `.gitignore` (mirror the bugs
  block: negate dir, re-ignore contents, negate `*.md`, `_archive/`, `_archive/*.md`);
  `git add specs/backlog` (live entries + candidates.md + `_archive/*.md`); verify
  AC-1 (`check-ignore` negative, `ls-files` == 31) and that the commit passes the
  pre-commit chokepoint with BL-* firing. Owner: software-engineer.

## W2 — FR2 fail-closed invariant derivation (write set: `subject_registry.py`, its unit tests)

- [x] T-49-11 TDD: add regression tests — `.py`-docstring INV token → UNRESOLVED;
  `tests/`-only INV token → UNRESOLVED; memory-doc INV token (INV-4 style) →
  resolves; then drop the `source_root` leg from `_derive_invariant_anchors` (and its
  argument from the call site). Verify AC-2 on the live tree. Owner: software-engineer.

## W3 — FR3 heading allowlist extension (write set: `lint-memory-atoms.py`, script unit tests)

- [x] T-49-12 TDD: merge-behavior tests (absent file → curated; present → union;
  malformed lines ignored) + scaffold-coverage test (every `##` in
  `public/scaffold/memory/*.md` allowlisted); implement `.heading-allowlist` merge +
  Group S; `dadaia public stage && install --target all && public doctor` exit 0.
  Verify AC-3. Owner: software-engineer.

## W4 — gates + ship

- [x] T-49-20 QA review (alpha gate): APPROVE (qa-engineer, 2026-07-02). All ACs
  verified with live evidence: AC-1 31 tracked / .gitkeep ignored; AC-2 exactly
  INV-1..INV-6; AC-3 58 tests green + live lint 28 OK/0 WARN; projection doctor
  exit 0; no scope creep; 3 INFO findings (gitignore asymmetry note for a future
  release; broader-is-stronger scaffold glob; privacy pre-scan clean — formal
  clearance routed to T-49-21). Verdict landed as this review commit.
  Owner: qa-engineer.
- [ ] T-49-21 Security review (push gate): OWASP/secret/dep review of the diff; emit
  APPROVE handoff with `metrics.commit_sha` = pushed sha; push; watch CI to green;
  open PR; merge after every job is green. Owner: security-reviewer (verdict) +
  orchestrator (push/PR/CI watch).

## W5 — closure (CLOSURE phase)

- [ ] T-49-30 CLOSURE.md (evidence triples); `dadaia bugs append --event resolved
  --release v0.1.49` for `backlog-gitignored-governance-vacuous` and
  `backlog-subject-registry-invariant-content-scan`; remove consumed
  `memory-heading-allowlist-extension.md` with durable copy under
  `specs/_archive/v0.1.49/consumed-backlog/`; memory updates
  (`sdd-bug-backlog-governance`, `specs-doctor`) + catalog regenerate + lint; archive
  `specs/releases/v0.1.49/` → `specs/_archive/releases/`; ACTIVE → none.
  Owner: product-engineer.
