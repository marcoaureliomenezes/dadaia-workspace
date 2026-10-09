# Job 3 — characterization net (FR4)

**Status:** Approved

Pins today's behaviour at the public seams before any CP job merges. Every test is green on Job 3's base (the post-Job-1 head) and stays green, unedited, on every CP job head (AC4.3). Each new file is a `test_<m>__characterization.py` beside its owner (`tests/AGENTS.md`), so AC4.3 is checkable by path: `git diff --name-only <cp-base>..<cp-head> -- '*__characterization.py'` prints nothing.

- Each test drives the seam as a user does (the CLI verb or `python3 <script>.py` from a workspace fixture) and asserts, in one test, the exit code, the exact `fix:`/`Operator action:` line and the artifact written (file bytes, ledger record or JSON), with literal expected values.
- AC4.2: J3.T3 and J3.T4 pin `BUGS.jsonl` and `_RELEASE.json` byte-for-byte after each writer verb on a fixed fixture.
- Seam coverage — the 19 owned seams of `seams-42.txt`: CP4 (`dadaia reconcile`, `context bind`, `context delete`, `context repo add`, `context repo remove`) J3.T1; CP1 (`memory.py catalog`, `memory.py generate`, `memory.py drift`, `worktree.py hash`, `verdict.py`) J3.T2; CP3 (`bugs.py append|status|resolve|supersede|reject|archive`) J3.T3 and (`release.py drift|memory|ship`) J3.T4. The listed seams whose code an rc-12 job changes (A5, ruled 2026-10-09, corrected at define review): `hook root_whitelist` and `hook ctx_inject` (Job 5), `dadaia ci push-gate-check` (J1.T11 strings), `dadaia public stage`, `dadaia public install` and `dadaia public doctor` (J5.T5 rebuilds `render_registry_tables`, which `public_assets._staged_bytes` runs for stage and for the doctor's comparison, and `codex_assets.py`), `dadaia init` (J5.T5 rebuilds `template_history.was_shipped`, reached through `print_next_step` → `onboarding._first_pass`) J3.T5.
- CP1's 5 and CP3's 9 seams stay in this net although FR6 and FR7 moved to rc-13: AC4.1 names them by owner, and the net then guards the rc-13 refactors from their first commit.
- Not a behaviour task: one test-only dispatch per task, no RED (nothing is fixed).

| task | AC | `W:` | outcome |
|---|---|---|---|
| J3.T1 | AC4.1 | `tests/cli/commands/test_reconcile__characterization.py`, `tests/cli/commands/test_context__characterization.py` | CP4 seams (5) |
| J3.T2 | AC4.1 | `tests/public/skills/dd_spec_navigator/scripts/test_memory__characterization.py`, `tests/public/skills/dd_gitflow_default/scripts/test_worktree__characterization.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict__characterization.py` | CP1 seams (5) |
| J3.T3 | AC4.1, AC4.2 | `tests/public/skills/dd_bug_resolution/scripts/test_bugs__characterization.py` | CP3 `bugs.py` seams (6) and the `BUGS.jsonl` byte pin |
| J3.T4 | AC4.1, AC4.2 | `tests/public/skills/dd_release_implementation/scripts/test_release__characterization.py` | CP3 `release.py` seams (3) and the `_RELEASE.json` byte pin |
| J3.T5 | AC4.1 | `tests/hooks/test_root_whitelist__characterization.py`, `tests/hooks/test_ctx_inject__characterization.py`, `tests/cli/commands/test_ci__characterization.py`, `tests/cli/commands/test_public__characterization.py`, `tests/cli/commands/test_init__characterization.py` | touched seams: `root_whitelist`, `ctx_inject`, `ci push-gate-check`, `public stage`, `public install`, `public doctor`, `init` |
