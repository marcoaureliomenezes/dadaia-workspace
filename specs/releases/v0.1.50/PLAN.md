# PLAN — v0.1.50 — Kernel Hardening

**Status:** Aprovado

## Wave map

- **W0 — definition**: ACTIVE → v0.1.50 DEFINITION; SPEC/PLAN/TASKS authored;
  architecture + QA definition reviews; `Aprovado`; definition commit.
- **W1 — FR1 lease identity** (TDD): failing rotated-sid self-block test first
  (reproduces audit F-1), then self-recognition RENEW at the acquire seam + sid
  precedence in the hook + `active_release` veto hygiene on both sides of the seam.
- **W2 — FR2 coherence/index**: namespace-aware coherence via the by-session index;
  RENEW-branch index hygiene; doctor `--specs-dir` state isolation. TDD per FR2 tests.
- **W3 — FR3 dead-exit path**: refspec/skip push + `rmtree(onexc)` + pre-check
  ordering. TDD with fixture repos (0444 objects, mismatched upstream, empty push).
- **W4 — FR4 resolution**: verify the PINNED root cause empirically (red integration
  test on the bound-session fixture; verification recorded in the TASKS root-cause
  line), then fix at the pinned seam (thread `ancestry_pids` through the bugs CLI +
  audit sibling `resolve_specs_dir` callers) + cwd fallback root-law guard.
- **W5 — gates + ship (flat release — single ship gate, no alpha/rc segmentation)**:
  full local gates; qa review commit; security push-gate APPROVE handoff keyed to the
  pushed sha; push; CI green; PR; merge.
- **W6 — closure** (CLOSURE phase): CLOSURE.md (with `## Validations` + `## Drifts`
  — SPEC-DOC-006); bug `resolved` event; consumed-backlog removal ×2 with durable
  copies + ledger; memory updates (`sdd-gate-v3`, `context-management`,
  `workspace-doctor` if needed); catalog + lint; archive; ACTIVE → none.

## Write sets (disjoint per wave; W1/W2 share the spec_context feature but disjoint files)

| Wave | Files |
|---|---|
| W1 | `core/lock_liveness.py`, `features/spec_context/lease.py`, `features/spec_context/gate_policy.py` (`veto_release` thread-through — named by the FR1 ADR; added here for traceability per QA MINOR-1), `hooks/_common.py` (the shared sid seam), `hooks/sdd_gate.py` (caller only, if needed), their unit test files |
| W2 | `features/spec_context/session_identity.py`, `features/specs/doctor.py` (SPEC-DOC-029 seat, only if a doctor-side edit is needed), `cli/commands/specs.py` (`workspace_state_dir` isolation), their tests |
| W3 | `infrastructure/git_subprocess.py`, `features/spec_context/service.py`, their tests |
| W4 | one shared ancestry-threading CLI seam + the five `_resolve_specs_dir` wrappers (`bugs.py`, `migrate.py`, `specs.py`, `memory.py`, `newartifacts.py`) + `core/specs_resolver.py` (cwd guard), their tests, and the single root-cause-verification line in `specs/releases/v0.1.50/TASKS.md` (T-50-13) |
| W6 | `specs/releases/v0.1.50/**`, `specs/_archive/**`, `specs/memory/**`, `specs/bugs/*.jsonl`, `specs/backlog/` (removals) |

## Test strategy

- W1/W2: unit layer against fixture lease records/session trees (`tmp_path`); the
  FROZEN no-steal suite is the exact 9-path list in SPEC §5 AC-1 — those files must
  pass green with ZERO diffs; any edit to them is a scope alarm
  (`test_lease_by_session_index.py` is deliberately outside the frozen set — FR2
  extends it).
- W3: integration layer (real tmp git repos: 0444 loose objects via a real commit;
  a fixture remote with a differently-named upstream branch; `GitSubprocessClient`
  driven directly). No network.
- W4: integration (CliRunner or subprocess with a fully-fixtured workspace: bind
  marker with a synthetic ancestry chain, session record, stray root `specs/`).
- Full-suite + lint + mypy locally before push (pre-push gate re-runs them).

## Rollback

Single feature branch `feature/v0.1.50`; one commit per wave; revert = drop the
branch before merge. No state-file schema changes (the by-session index entry
cleanup is behavioral, not structural).
