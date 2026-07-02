# TASKS — v0.1.50 — Kernel Hardening

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. One `[-]` per owner unless write
sets are disjoint (PLAN §Write sets).

## W0 — definition

- [x] T-50-01 ACTIVE → v0.1.50 DEFINITION; SPEC/PLAN/TASKS authored; architecture
  REJECT (BLOCKER F1 sid seam = hooks/_common.resolve_session_id; F2
  holder-confirmation not index-namespace; F3 four-wrapper defect class →
  centralize; F4-F7) + QA REJECT (F1 frozen 9-path no-steal suite; F2 halt-path bug
  disposition; F3 W4 write-set line; F4 flat-release gate label; F5 red-commit TDD
  ordering; F6 pid-reuse edge) — ALL amendments landed; root cause of the consumed
  bug pinned at definition time (bugs.py missing ancestry_pids); all three
  `Aprovado`; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1 lease identity (write set: `core/lock_liveness.py`, `features/spec_context/lease.py`, `hooks/sdd_gate.py`, unit tests)

- [x] T-50-10 TDD: failing rotated-sid self-block regression as its OWN red commit
  (same recorded harness pid + new sid ⇒ currently `LockHeldError`); then the third
  identity rung (RENEW) at the acquire ladder in `lease.py`; sid precedence fixed
  ONCE in `hooks/_common.resolve_session_id` (`DADAIA_SESSION_ID` override stays
  first > payload sid > inherited harness envs; eval-flow override test); `is_stale`
  sentinel tolerance (`'none'`/`''` → `None`) preserving the record-release dual
  use; pid-reuse TAKEOVER edge test. Frozen no-steal suite (SPEC §5 AC-1 list):
  zero diffs, green. Owner: software-engineer.

## W2 — FR2 coherence + index hygiene (write set: `session_identity.py`, doctor state-dir seam, tests)

- [x] T-50-11 TDD: SPEC-DOC-029 holder-confirmation coherence (a confirmed live
  holder is coherent despite `.ptr` drift; NO by-session schema change); RENEW-branch
  dangling-entry cleanup (`_index_remove` for the replaced sid); doctor `--specs-dir`
  isolated `workspace_state_dir`. Owner: software-engineer.

## W3 — FR3 dead-exit path (write set: `git_subprocess.py`, `spec_context/service.py`, tests)

- [x] T-50-12 TDD: explicit-refspec push (`HEAD:<upstream-branch>`) + empty-push skip
  (`rev-list @{u}..HEAD`); drop the non-writable rglob scan for
  `shutil.rmtree(onexc=chmod-and-retry)`; move surviving refusal pre-checks BEFORE
  the push phase. Fixture repos: 0444 git objects, mismatched upstream, nothing-to-
  push. Owner: software-engineer.

## W4 — FR4 bound-session resolution (write set: `cli/commands/bugs.py` + sibling `resolve_specs_dir` callers + `core/specs_resolver.py` cwd guard + tests + this task's root-cause line)

- [x] T-50-13 VERIFY-PINNED-CAUSE-THEN-FIX: red integration test on a bound-session
  fixture proving `bugs append` falls to cwd (verifies the definition-review pin);
  record the verification result on the line below; then CENTRALIZE
  ancestry-threading in one shared CLI seam consumed by all five
  `_resolve_specs_dir` wrappers (`bugs`, `migrate`, `specs`, `memory`,
  `newartifacts` — reference behavior: `newartifacts.py:94`), add the cwd fallback
  root-law guard (redaction-safe refusal message). Halt path per SPEC §5 AC-4
  (expected unused). Owner: software-engineer.
  - Root cause (pinned 2026-07-02 definition review; W4 verification): **VERIFIED
    by red test** `test_bugs_append_resolves_bound_context_via_ancestry_chain` —
    a deep-ancestor bind marker misses under getppid-only degraded attribution
    (bugs.py omitted `ancestry_pids`); green after the shared seam
    `cli/_specs_resolution.resolve_specs_dir_for_cli` (all five wrappers consume
    it — the omission class is structurally impossible). Halt path unused.

## W5 — gates + ship (flat release: single ship gate)

- [x] T-50-20 QA review (ship gate): REJECT → fix → APPROVE (qa-engineer,
  2026-07-02). REJECT caught: 5 old-contract pins left red at the gate (BLOCKER —
  incl. 2 surfaced only by the reviewer), a `pytest | tail` exit-code mask
  (MAJOR — suite re-run UNPIPED: 4,411 passed / 0 failed, real exit 0), and a
  PLAN write-set omission (MINOR). All remediated on stable HEAD `1c8dc70b`;
  APPROVE verified: frozen 9-path suite zero-diff, all ACs pass, ADR fidelity
  confirmed, refusal-message redaction now regression-tested. Verdict landed as
  this review commit. Owner: qa-engineer.
- [x] T-50-21 Security review (push gate): APPROVED for `873b11d2` (0 findings above
  INFO across 6 dimensions; frozen-suite zero-diff independently confirmed); handoff
  `2026-07-02T194652Z-security-reviewer-v0150-push-gate.handoff.json` validated with
  `metrics.commit_sha` = pushed sha; pre-push preflight 4/4 PASS; PR #89 38 checks
  green; squash-merged as `7b198d49`. Owner: security-reviewer + orchestrator.

## W6 — closure (CLOSURE phase)

- [x] T-50-30 CLOSURE.md authored (incl. `## Validations` + `## Drifts` —
  SPEC-DOC-006); bug `resolved --release v0.1.50` event appended (ledger: 0 open);
  consumed entries (`lease-kernel-identity-hardening`, `context-dead-exit-path`)
  archived with durable copies + `consumed_backlog.json` under
  `specs/_archive/v0.1.50/`; memory updates landed in `sdd-gate-v3`,
  `context-management`, `specs-doctor` (the 029/--specs-dir seat — `workspace-doctor`
  unchanged, no runtime-doctor behavior in scope) + catalog regenerated (25 features)
  + lint all-pass; release archived; ACTIVE → none; candidates.md R2 row marked
  shipped. Owner: product-engineer.
