# Job 6 — package loose ends and the push-gate remedy: one several-work-branches class, specs init, doctor, privacy, layout (FR6, FR7, FR10.4)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and §1.1.

- **AC6.1.** `SeveralWorkBranches` inherits the skill's `SeveralWork` and `DadaiaError`; the core class keeps `DadaiaError` only and carries the skill's text unlabeled, so there is one class; `cli/commands/ci.py` catches it (the import adds about 22 ms, per the entry, inside the gate's cost law).
- **AC7.** `--rewrite-from` stays a flag on the existing leaf (the 30-leaf cap in `test_help.py` holds unchanged); `push-gate-check --help` names it as the remedy and states the whole-range collapse and the listed-file residual as the verb's contract; the decision carries its listed paths, so the two `isinstance(decision, GateDecision)` checks go. AC7.4 is shown gone: `_audit_only` is `branch_policy._audit_descendant` (`features/chokepoints/branch_policy.py:168`).
- **AC6.7 KEEP.** `preview = true` stays while `ruff rule PLW1514` reads "in preview" in the locked ruff 0.16.2; no task. **AC6.8.** The three `dadaia-dev-tooling` lines of `.gitattributes` are deleted (no reader; the rc-10 job that wrote them is closed history).
- **AC10.4, package side.** The `<40hex>` token of `core/workspace_layout.py:420` and the `reviewed_sha` pattern of `public/schemas/handoff-v1.schema.json` accept 64 hex. The instance projection of that schema is the main thread's `public install` after the merge.

**Gate law (rc-18).** The job's `verify:` is `python scripts/ci.py job` (median 1m52, measured in rc-17; no `verify:` change). An implementer's definition of done is that run, plus the touched test directories (`tests/core`, `tests/cli/commands`, `tests/features/specs`, `tests/features/workspace`, `tests/infrastructure/test_privacy_check.py`), plus the own-diff self-check over `git diff <base>...HEAD`: no removed `assert` line and no newly skipped test unless this file names the order, and the sweep greps. No preflight, no full CI line; CI on push is the net. A RED task fails only on its new RED tests and says which. Every task reads `.dadaia/tmp/main-thread/20261018/rc18-common.md`.

**Sweep greps.** `git grep -n 'dadaia-dev-tooling' -- .gitattributes dadaia_workspace tests` prints nothing; `git grep -n 'isinstance(decision' -- dadaia_workspace/cli` prints nothing; `git grep -n 'SeveralWork' -- dadaia_workspace` shows one class definition.

Tasks: 10 (6 jr, 4 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T1 then T2; T3 then T4; T5 then T6, T7, T8, T9 (disjoint, parallel); T10 any time. The two chains T1/T2 and T3/T4 are disjoint.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J6.T1 | sr | AC6.1, AC7.1, AC7.3 | `tests/core/test_gitflow.py`, `tests/cli/commands/test_ci.py`, `tests/features/workspace/test_onboarding.py` | RED, unit: one several-work-branches class catches the refusal in `ci.py` and onboarding; `push-gate-check --help` names `--rewrite-from`; the decision carries its listed paths; `test_onboarding.py:170-176` follows the one class |
| J6.T2 | sr | AC6.1, AC7.1, AC7.2, AC7.3 | `dadaia_workspace/core/gitflow.py`, `dadaia_workspace/cli/commands/ci.py` | REBUILD the double inheritance (`refactor(J6.T2): REBUILD SeveralWorkBranches — …`), the `ci.py` catch, the help text and the two `isinstance` deletions; net lines at most 0 |
| J6.T3 | sr | AC6.2, AC6.3 | `tests/cli/commands/test_specs.py` | RED, integration: `specs init` cuts the work branch from `origin/<work>`, else the integration branch; the `[committed]` guard refuses as designed |
| J6.T4 | jr | AC6.2, AC6.3 | `dadaia_workspace/cli/commands/specs.py`, `dadaia_workspace/infrastructure/git_subprocess.py` | the cut point and the four stale texts (help, docstring, the `[moved]` line, `work_version`'s docstring); turns T3 green |
| J6.T5 | sr | AC6.4, AC6.5, AC6.6, AC10.4 | `tests/features/specs/test_doctor_memory.py`, `tests/infrastructure/test_privacy_check.py`, `tests/core/test_workspace_layout.py`, `tests/core/test_handoff_index__handoff_schema_contract.py` | RED, unit: the "fill or delete" fix names the atom's file; the baseline's `skip_paths` are honoured and the pipeline-name test skips only the matched path; a planted `.git` under a worktree does not switch stray detection; a 64-hex sha passes both patterns |
| J6.T6 | jr | AC6.4 | `dadaia_workspace/features/specs/doctor_memory.py` | the fix text names the file; turns its T5 row green |
| J6.T7 | jr | AC6.5 | `dadaia_workspace/infrastructure/privacy_check.py` | `skip_paths` honoured, per-path skip; turns its T5 rows green |
| J6.T8 | jr | AC6.6, AC10.4 | `dadaia_workspace/core/workspace_layout.py` | stray detection ignores a planted `.git`; the `<40hex>` token takes 64 hex; turns its T5 rows green |
| J6.T9 | jr | AC10.4 | `dadaia_workspace/public/schemas/handoff-v1.schema.json` | `reviewed_sha` pattern accepts 64 hex; turns its T5 row green |
| J6.T10 | jr | AC6.7, AC6.8 | `.gitattributes` | delete lines 3, 4 and 7; no test: evidence `git grep -n dadaia-dev-tooling` prints nothing; AC6.7 closes KEEP with the ruff reading above |
| J6.T11 | sr | AC6.2 | `tests/cli/commands/test_specs.py` | review RED (`940a010f0`): the cut point on a start that tracks the scaffold and on origin-only integration |
| J6.T12 | sr | AC6.2, AC6.3 | `dadaia_workspace/cli/commands/specs.py` | REBUILD `specs init` order (`6a47511c9`): cut the work branch first, then judge and write; turns T11 green |
| J6.T13 | sr | AC6.6 | `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/features/spec_context/sweep.py`, `tests/core/test_workspace_layout__workspace_layout_zones.py` | REBUILD the worktree-gitfile decider (`3f9c5f51a`, `b40df5db4`, `fc965eca7`): one stricter predicate in `workspace_layout`; the zone fixture writes a real worktree gitdir, asserts unchanged |
| J6.T14 | sr | AC6.2, AC6.6 | `tests/cli/commands/test_specs.py`, `tests/hooks/test_pre_gate.py` | RED (`dea4b4642`): `specs init` no-switch partitions; the pre-gate fixture writes a real worktree gitdir, asserts unchanged |
| J6.T15 | sr | AC6.2 | `dadaia_workspace/cli/commands/specs.py` | `04fdd10ac`: `specs init` switches nothing when the work branch exists; a missing dir is not a git root; turns T14 green |

**Closure record (main thread, 2026-10-18).** 5 tasks landed beyond the PLAN, the rows after the planned ones, read from `git log wt/0.5.0/rc-18/wt-rc`.
