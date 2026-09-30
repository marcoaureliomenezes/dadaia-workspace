# TASKS — Release: 0.5.0

**Status:** Approved
**Owner:** dd-software-engineer

Candidate 5 — worktrees and bind (ADR 0140). Paths as in PLAN (`f/` features, `pub/` public, `wt.py` = `pub/skills/dd-gitflow-default/scripts/worktree.py`).
Each write set includes its tests; a DEL's dead tests leave in the same commit. T-050-95 and T-050-96 are written by hand on the work branch (the old flow); from T-050-97 on every task is made in its own
`wt.py new` impl worktree, opened when its `blocked by:` tasks are merged, and lands by `wt.py merge` (AC1.14, ADR 0141); PLAN §5 is the schedule.
`Δ` = estimated package lines.

## Candidate 5 — worktrees and bind

### Worktrees first — the tool before the refusal that names it

- [x] **T-050-95 — `worktree.py new` and `list`.** `W:` `wt.py` (`KINDS`/`kind_for` included), `tests/integration/test_worktree_new.py`
  `blocked by:` none · `delivers:` AC1.7; after this the operator can run `worktree.py new dadaia-workspace --kind impl` · `RED:` `pytest tests/integration/test_worktree_new.py` · Δ +220 (`wt.py`).
- [x] **T-050-96 — `worktree.py merge` and `clean`.** `W:` `wt.py`, `tests/integration/test_worktree_lifecycle.py`, `tests/integration/test_worktree_merge_requires_review.py`, `tests/integration/test_worktree_merge_allowed_sets.py`
  `blocked by:` T-050-95 · `delivers:` AC1.8 · `RED:` `pytest tests/integration/test_worktree_lifecycle.py tests/integration/test_worktree_merge_requires_review.py tests/integration/test_worktree_merge_allowed_sets.py` · Δ +140 (`wt.py`).

- [-] **T-050-106 — Level-1 root canon: `worktrees/` and `.dadaiaignore` (ADR 0145).** `W:` `core/workspace_layout.py`, `hooks/root_whitelist.py`, `f/spec_context/doctor.py`, `f/spec_context/gate_policy.py`, `pub/data/AGENTS.md`, `CONTEXT.md`, `docs/concepts.md`, `tests/unit/core/test_workspace_layout_zones.py`, `tests/unit/hooks/test_root_whitelist.py`, `tests/unit/test_spec_context_doctor_root.py`, `tests/integration/test_gate_allow_iff_doctor_keeps.py`, `tests/unit/features/spec_context/test_sweep.py`, `tests/contract/test_every_block_carries_a_fix.py`
  `blocked by:` T-050-96 · `delivers:` AC1.6 (root slice), ADRs 0092-0094 core; by hand on the work branch (bootstrap, like T-050-95/96) · `RED:` `pytest tests/unit/core/test_workspace_layout_zones.py tests/unit/test_spec_context_doctor_root.py` · Δ ≈ 0.

### Scope — the first task made in a worktree

- [ ] **T-050-97 — One `scope()` decider, the gate rewrite, bind without a mint.** `W:` `core/invocation.py`, `core/workspace_layout.py`, `f/spec_context/gate_policy.py`, `hooks/sdd_gate.py`, `cli/commands/context.py`, `tests/unit/features/spec_context/test_gate_policy.py`, `tests/unit/hooks/test_sdd_gate.py`, `tests/integration/test_one_bind.py`, `tests/contract/test_core_file_io_purity.py`, `tests/contract/test_zone_registry.py`
  `blocked by:` T-050-106 · `delivers:` AC1.14 starts (made in a `wt.py new` worktree, landed by `wt.py merge`); AC1.1, AC1.6, AC1.2 (bind refusal clause); DEL `unbound-native-session-writes-freely-into-repos`, `additive-globs-hand-kept-beside-the-canon` · `RED:` `pytest tests/unit/features/spec_context/test_gate_policy.py tests/unit/hooks/test_sdd_gate.py` with the `:83` row and the ledger rows rewritten to refusals · Δ −45.

### Worktrees in use — step 3 (with T-050-97), step 4, step 5 (PLAN §5)

- [ ] **T-050-98 — Parallel merges.** `W:` `wt.py`, `tests/integration/test_worktree_parallel_merge.py`
  `blocked by:` T-050-96 · `delivers:` AC1.9 · `RED:` `pytest tests/integration/test_worktree_parallel_merge.py` · Δ +20 (`wt.py`).
- [ ] **T-050-99 — Hygiene: doctor listing, closure and `context dead` holds.** `W:` `f/spec_context/doctor.py`, `f/spec_context/service.py`, `hooks/ctx_inject.py`, `pub/skills/dd-release-implementation/scripts/_release_phase.py`, `tests/integration/test_context_dead_holds.py`, `tests/integration/test_reaper_spares_linked_worktrees.py`, `tests/integration/test_release_closure_refuses_open_worktree.py`
  `blocked by:` T-050-96 · `delivers:` AC1.10 · `RED:` `pytest tests/integration/test_context_dead_holds.py tests/integration/test_reaper_spares_linked_worktrees.py tests/integration/test_release_closure_refuses_open_worktree.py` · Δ +25.
- [ ] **T-050-100 — Bind injection, fenced roots, corrupt session records.** `W:` `hooks/ctx_inject.py`, `hooks/sdd_gate.py`, `core/workspace_resolver.py`, `core/session_store.py`, `f/spec_context/doctor.py`, `tests/e2e/features/test_ctx_inject_bind_boundary.py`, `tests/unit/hooks/test_sdd_gate.py`, `tests/unit/core/test_session_store.py`
  `blocked by:` T-050-97, T-050-99 · `delivers:` AC1.2, AC1.3, AC1.4; FR `fenced-roots-env-disables-the-gate`, `corrupt-session-record-never-collected` · `RED:` `pytest tests/integration/test_one_bind.py tests/e2e/features/test_ctx_inject_bind_boundary.py tests/unit/hooks/test_sdd_gate.py tests/unit/core/test_session_store.py` · Δ +10.
- [ ] **T-050-101 — One venv in worktrees.** `W:` `AGENTS.md` (repo root), `tests/integration/test_worktree_venv.py`
  `blocked by:` T-050-96 · `delivers:` AC1.11 · `RED:` `pytest tests/integration/test_worktree_venv.py` · Δ 0.
- [ ] **T-050-102 — Correlation at registration; the schedule check.** `W:` `pub/skills/dd-bug-resolution/scripts/_bugs_write.py`, `pub/skills/dd-bug-resolution/scripts/bugs.py`, `pub/skills/dd-backlog-definition/scripts/_backlog_write.py`, `pub/skills/dd-backlog-definition/scripts/backlog.py`, `pub/skills/dd-release-implementation/scripts/_release_check.py`, `tests/unit/scripts/test_bugs_correlation.py`, `tests/unit/scripts/test_backlog_correlation.py`, `tests/unit/scripts/test_release_check_schedule.py`
  `blocked by:` T-050-96 · `delivers:` AC1.12 (F011); `release.py check` refuses a PLAN without §Parallel schedule or with overlapping `W:` in one step (ADR 0141) · `RED:` `pytest tests/unit/scripts/test_bugs_correlation.py tests/unit/scripts/test_backlog_correlation.py tests/unit/scripts/test_release_check_schedule.py` · Δ +60.

### Law, migration, closure

- [ ] **T-050-103 — One home per rule.** `W:` `pub/data/AGENTS.md`, `pub/scaffold/worktrees/AGENTS.md`, `pub/scaffold/releases/AGENTS.md`, `pub/skills/dd-*/SKILL.md` (the seven worktree lines, the `dd-code-review` per-kind rows, `dd-gitflow-default` §3a, `dd-bug-resolution` RED commit, `dd-release-definition` §5 schedule), `specs/releases/AGENTS.md`, `specs/ADRs/decisions.jsonl` (0027 title; union), `CONTEXT.md`, `tests/contract/test_worktree_law_homes.py`
  `blocked by:` T-050-96 · `delivers:` AC1.5, AC1.13 (F053–F057, F008, F074, F084); ADR 0141 law (releases law line 31 → one impl worktree per task); `public doctor` clean · `RED:` `pytest tests/contract/test_worktree_law_homes.py` · Δ 0.
- [ ] **T-050-104 — Migrate the old worktrees.** `W:` git refs only (no file) · `blocked by:` T-050-96
  `delivers:` AC1.15 (F068, F085) · `RED:` `git -C repos/dadaia-workspace worktree list --porcelain` names a path outside `worktrees/` · Δ 0.
- [ ] **T-050-105 — Measure and hand to closure.** G1 counts logged, `worktree.py` size apart, G2–G4 run; per step planned vs measured width, the critical path walked, every rebase conflict (ADR 0141 point 6). `W:` handoff · `blocked by:` T-050-95..104
  `delivers:` AC1.16 inputs (the memory pass and `_RELEASE.json` are dd-product-engineer's) · `RED:` n/a.
