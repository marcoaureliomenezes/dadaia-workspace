# Job 10 — a refusal must not move the bind every writer of a session shares (bug `subagent-bind-rebinds-the-parent-session-across-contexts`)

**Status:** Draft

Wave 3, waits on — (no shared path; waves 1 and 2 are full). Paths are repository-relative to `repos/dadaia-workspace/`; `P/` = `dadaia_workspace/`. Design and evidence: PLAN §1 (cause D), §2 (Job 10).

- **Structural cause.** Subagents inherit the parent's session id (`.dadaia/AGENTS.md:30`, §2), so they share one record (`P/core/session_store.py:40-49`) and one bind (`P/core/invocation.py:195-209`, `resolve_bind`). The scope refusal (`P/features/spec_context/gate_policy.py:139`) prints `context bind <owner>` (`:146`) for any session with an id; running it rewrites the one record, so every concurrent writer in the previously bound context is then refused. The bug recurs the resolved `spec-navigator-subagent-rebinds-parent`, whose fix did not touch the refusal's own fix line.
- **Shape (T2).** When the session already has a bind (`context` set), the refusal's one fix is an agent act: hand the write back to the main thread, which alone binds, and only when no sibling writes in the bound context; it names no `context bind` command a subagent could run. When the session has no bind (`context` None, with an id), `context bind <owner>` stays: there is nothing to steal. The id-less branch (`relaunch … DADAIA_CONTEXT`) is unchanged. First, T2 reads whether the hook payload names the acting agent and records the answer in its hand-back: a per-actor bind is the heavier option and is not built here.
- **Lineage.** `caused_by=T-050-97` is already set (a REBUILD): `refactor(bugs): subagent-bind-rebinds-the-parent-session-across-contexts — REBUILD the scope refusal's fix: …`, with the `caused_by:`/`evidence:`/`prior diffs read:`/`rebuild:` block; the main thread resolves in this job's `wt-main`.
- **Contract tests that stay green, unloosened:** the rest of `tests/features/spec_context/test_gate_policy.py`, `test_gate_policy__law_states_what_the_code_does.py`, `tests/core/test_invocation__one_bind.py`, `tests/e2e/features/test_ctx_inject_bind_boundary.py`, and the tests that feed every block's fix back through the gate. R-E (PLAN §3): the case at `test_gate_policy.py:89` flips in T1's `test(` commit, naming the main thread's ruling 5.

**Gate law.** `verify:` is `python scripts/ci.py job`, no change. Definition of done: that run, `tests/features/spec_context`, `tests/core`, `tests/hooks`, `tests/e2e/features/test_ctx_inject_bind_boundary.py`, the own-diff self-check, the sweep greps. Reproject after the merge (PLAN §2).

**Sweep greps.** `git grep -n '"bind"' -- dadaia_workspace/features/spec_context/gate_policy.py` prints only the unbound branch's line; `git grep -n "context bind" -- dadaia_workspace/features/spec_context/gate_policy.py` prints docstring lines only, no fix.

Tasks: 2 (2 sr). T2 after T1.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J10.T1 | sr | AC9.2 | `tests/features/spec_context/test_gate_policy.py` | RED, unit. A write into context B by a session bound to A refuses with a fix that is not `context bind B` and names the main thread as the binder (fails today: `:89`); a session with an id and no bind still gets `context bind B` (`:90`, unchanged); an id-less one still gets the relaunch act; a second write by a sibling into A stays allowed after the first refusal (the state the old fix destroyed). R-E: `:89` flips, ruling named in the `test(` commit |
| J10.T2 | sr | AC9.2 | `dadaia_workspace/features/spec_context/gate_policy.py` | REBUILD the scope refusal's fix: the Shape above; owner `test_gate_policy.py`; net lines at most 0 |
