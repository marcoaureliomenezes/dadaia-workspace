# Job 2 — Codex is judged by its session record (FR1, AC1.1, AC1.2)

**Status:** Draft

| task | who | AC | `W:` | owner test | outcome |
|---|---|---|---|---|---|
| J2.T1 | sr | AC1.1, AC1.2 | `tests/core/test_harness_registry__harness_registry_records.py` `tests/core/test_invocation.py` `tests/cli/commands/test_context.py` `tests/hooks/test_sdd_gate__protected_projections.py` | the four files | RED: the nine rows of `55622e7fe`, put back |
| J2.T2 | jr | AC1.1, AC1.2 | `dadaia_workspace/core/harness_registry.py` | the four files of J2.T1 | the Codex row names `"agent_type"` |

Wave 2, with Jobs 1 and 3. Definition of done for each task: `python scripts/ci.py job`, then `pytest tests/core tests/hooks tests/cli`. No new test row and no Codex branch anywhere: `governed` stays the one decider.

## J2.T1 — RED

- Apply `git diff 55622e7fe^ 55622e7fe -- tests` in reverse (`git apply -R`; `--check` passes at the tip). It restores exactly four files, nine rows, test names included:
  - the registry map: `"codex": "agent_type"`;
  - `codex-thread-no-record` and `codex-session-no-record`: `governed` `False`;
  - `codex-binds` `True, 0` and `codex-no-record-refused` `False, 1`;
  - the two Codex verdict-run rows `True`.
- Commit `test(J2.T1): …`. The body names the operator's order, ADR 0282 redo, "Trust flags in eval.yml (Recommended)" (R3), and the Codex rows it flips back. Record the red run: four files fail on the unchanged registry.
- A row outside these four that the J2.T2 value turns red is a question for the main thread (PLAN risk 6), never flipped here.

## J2.T2 — the value

- `dadaia_workspace/core/harness_registry.py`: the Codex row's `subagent_key` goes from `None` to `"agent_type"` (a one-token change; `b05088180` is the same edit). Nothing else.
- The commit body notes: `invocation.py` is untouched, and `rg -n 'trust_level|dangerously_bypass_hook_trust' dadaia_workspace/` prints nothing (AC1.5, hit count 0).
