# TASKS — Release: 0.5.0

**Status:** Draft
**Owner:** dd-software-engineer

Candidate 6 — W2 (ADR 0140). Paths as in PLAN (`f/` features, `pub/` public). Each write set includes its tests; a DEL's dead tests leave in the same commit.
Every task is made in its own `worktree.py new` impl worktree, opened when its `blocked by:` tasks are merged, and lands by `worktree.py merge`; PLAN §5 is the schedule.
`Δ` = estimated lines, prod / tests.

## Candidate 6 — W2

### Green base

- [ ] **T-050-111 — Derived docs re-recorded after P-27.** `W:` `docs/bug-ledger-lessons.md`
  `blocked by:` none · `delivers:` `feature/0.5.0` green on `test_docs_derived_from_memory.py`: Lessons 2–4 re-record their `QUALITY` markers, prose corrected only where P-27's removal made it false (MEMORY-UPDATE step 7); AC2.15 re-checked (`grep -c '^### P-27' specs/memory/QUALITY.md` = 0, landed by 3ca0585a) · `RED:` `pytest tests/contract/test_docs_derived_from_memory.py` (red today) · Δ 0 / 0.

### Deletions and small units — step 2

- [ ] **T-050-112 — The tracked-directory set is the one surface decider.** `W:` `pub/skills/dd-bug-resolution/scripts/_bugs_write.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`, `pub/entities/behavior-map.json`
  `blocked by:` T-050-111 · `delivers:` AC2.17; after this the operator can run `bugs.py append --surface .github`; FR `bugs-append-refuses-the-dot-directory-its-fix-offers` · `RED:` `pytest tests/unit/skills/test_bug_resolution_bugs_script.py` (a `.github` row; an untracked name still refused with close matches) · Δ −1 / +3.
- [ ] **T-050-113 — The venv guard judges only the dadaia CLI.** `W:` `hooks/venv_guard.py`, `tests/unit/hooks/test_venv_guard.py`, `tests/unit/hooks/test_pre_gate.py`
  `blocked by:` T-050-111 · `delivers:` AC2.9 (code; the law clause is T-050-120); DEL `pip-guard-fix-routes-project-installs-into-the-tool-venv` (ADR 0134); pip rows rewritten to ALLOW · `RED:` `pytest tests/unit/hooks/test_venv_guard.py tests/unit/hooks/test_pre_gate.py` · Δ −6 / −10.
- [ ] **T-050-114 — `context dead` fails when its hold fails.** `W:` `f/spec_context/service.py`, `tests/integration/test_context_dead_holds.py`
  `blocked by:` T-050-111 · `delivers:` AC2.11; FR `context-dead-ignores-the-hold-refusal` · `RED:` `pytest tests/integration/test_context_dead_holds.py` (a refused hold: exit non-zero, context ALIVE) · Δ +4 / +8.
- [ ] **T-050-115 — One deleter; the SessionStart lane seeds level 1.** `W:` `core/workspace_layout.py`, `f/workspace/service.py`, `f/spec_context/doctor.py`, `tests/integration/test_cli_init.py`, `tests/integration/test_doctor_fix_lines_clear_their_finding.py`, `tests/unit/features/spec_context/test_doctor_gc.py`
  `blocked by:` T-050-111 · `delivers:` AC2.2, AC2.4, AC2.10, AC2.12 (doctor and SessionStart lanes); FR `bug-proposal-handoff-reaped-without-a-hold`; after this an expired handoff is held in `.dadaia/reaped/` and listed until its hold expires · `RED:` `pytest tests/unit/features/spec_context/test_doctor_gc.py tests/integration/test_cli_init.py tests/integration/test_doctor_fix_lines_clear_their_finding.py` · Δ +5 / +6.
- [ ] **T-050-118 — A missing venv reaches the agent once per session.** `W:` `infrastructure/runtime_transforms/hook_wrappers.py`, `tests/integration/gate/test_hook_interpreter.py`, `tests/contract/test_hook_behaviour_coverage.py`
  `blocked by:` T-050-111 · `delivers:` AC2.7; FR `missing-venv-hook-disarms-the-gate-invisibly`; each dialect's SessionStart channel measured first, a dialect without one handed to T-050-120's list · `RED:` `pytest tests/integration/gate/test_hook_interpreter.py tests/contract/test_hook_behaviour_coverage.py` (the missing-venv case per harness, stderr assertion rewritten) · Δ +8 / 0.

### Root canon and DEC-11 — steps 3 and 4

- [ ] **T-050-116 — `.dadaiaignore` judges four places.** `W:` `core/workspace_layout.py`, `f/spec_context/doctor.py`, `hooks/root_whitelist.py`, `tests/unit/hooks/test_root_whitelist.py`, `tests/unit/test_spec_context_doctor_root.py`
  `blocked by:` T-050-115 · `delivers:` AC2.1 (ADR 0132; F076 pinned by the harness-directory row); `_scan_root` and `_scan_dadaia_top` become one walk · `RED:` `pytest tests/unit/hooks/test_root_whitelist.py tests/unit/test_spec_context_doctor_root.py` (stray entry at each place, the same entry under a glob, an unledgered `.claude/` file, a DEAD context's worktree) · Δ +10 / +12.
- [ ] **T-050-119 — Playwright MCP output under `.dadaia/mcps/`.** `W:` `infrastructure/runtime_config.py`, `tests/integration/test_tool_caches_stay_in_the_tmp_zone.py`
  `blocked by:` T-050-111 · `delivers:` AC2.14 (ADR 0156); the operator's own `env` keys kept · `RED:` `pytest tests/integration/test_tool_caches_stay_in_the_tmp_zone.py` (the owner of the env merge) · Δ +2 / +3.
- [ ] **T-050-117 — PROTECTED floor in code; the protected section.** `W:` `core/workspace_layout.py`, `f/spec_context/gate_policy.py`, `hooks/sdd_gate.py`, `CONTEXT.md`, `tests/unit/features/spec_context/test_gate_policy.py`, `tests/unit/hooks/test_pre_gate.py`
  `blocked by:` T-050-113, T-050-116 · `delivers:` AC2.3, AC2.5 (ADR 0133, F082 via 0114); DEL `gate-protects-nothing-without-install-ledger`; F015's gate half; the floor ⊆ init ∪ install contract row; the term Protected section · `RED:` `pytest tests/unit/features/spec_context/test_gate_policy.py tests/unit/hooks/test_pre_gate.py` (no ledger: five refusals; a protected glob under `repos/<r>/` and `worktrees/<r>/<name>/` in each dialect; an unprotected sibling allowed) · Δ +20 / +15.

### Law and closure

- [ ] **T-050-120 — One statement of the fail-open paths; onboarding writes; the 0138 lane.** `W:` `pub/data/AGENTS.md`, `pub/scaffold/memory/AGENTS.md`, `pub/scaffold/ADRs/AGENTS.md`, `docs/quickstart.md`, `docs/getting-started.md`, `tests/contract/test_law_states_what_the_code_does.py`, `pub/entities/behavior-map.json`
  `blocked by:` T-050-113, T-050-117, T-050-118 · `delivers:` AC2.6, AC2.8, AC2.9 (law), AC2.13, AC2.16 (the closure re-render of `specs/*/AGENTS.md` rides T-050-121); the fourth fail-open gap, an id-less unbound session under `worktrees/<r>/` (ADR 0116, grill Q5), in the same list; F080; commits cite ADR 0134 and ADR 0154 (law lines deleted, ADR 0151 M3) · `RED:` `pytest tests/contract/test_law_states_what_the_code_does.py` · Δ 0 / +6.
- [ ] **T-050-121 — Measure and hand to closure.** `W:` handoff · `blocked by:` T-050-111..120
  `delivers:` G1 readout (prod/test lines at start and end, `.dadaia/reaped/` size), G2–G4 run, G3 re-run of every open bug, AC2.12 verified end to end, planned vs measured width per step and every rebase conflict; inputs to the closure memory pass (F149) and G6 · `RED:` n/a.
