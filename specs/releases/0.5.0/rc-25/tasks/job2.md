# Job 2 — the pre-push gate admits the principal and integration branches (FR1, FR2)

**Status:** Draft

| task | who | AC | `W:` | owner test | outcome |
|---|---|---|---|---|---|
| J2.T1 | sr | AC1.1, AC1.2, AC1.3 | `tests/features/chokepoints/test_branch_policy.py` `tests/features/chokepoints/test_push_gate.py` `tests/cli/commands/test_ci.py` `tests/e2e/test_push_gate_check.py` `tests/fixtures/fix_world.py` | the five files | RED: a push of the principal or integration head is admitted; the birth rows and the PR rows are gone |
| J2.T2 | sr | AC2.2 | `tests/features/spec_context/test_service__context_baseline.py` | itself | RED: after a birth, the local role heads exist at their tips |
| J2.T3 | sr | AC2.2 | `dadaia_workspace/features/spec_context/service.py` | `tests/features/spec_context/test_service__context_baseline.py` | REBUILD of `_publish`: local heads pushed by name; J2.T2 green, the four baseline rows still green |
| J2.T4 | jr | AC1.1, AC2.1, AC1.3 | `dadaia_workspace/features/chokepoints/branch_policy.py` `dadaia_workspace/features/chokepoints/push_gate.py` `dadaia_workspace/infrastructure/git_objects.py` | the files of J2.T1 | DELETE of the refusal and the birth; J2.T1 green; net lines < 0 |

Wave 3, with Job 1 (disjoint `W:`, no edge). ADR 0283 is accepted before J2.T1 starts (PLAN section DAG). Order is forced: T3 before T4, because T4 alone makes every baseline birth refuse (PLAN section 6, point 1). Each task's Definition of done is `python scripts/ci.py job`, plus the directories named below. Never the full CI line.

## J2.T1 — RED, the gate rows

The operator's order, named in the `test(J2.T1)` commit body: "Remover o PR-only (Recomendado)" (R1), with the grill summary "Confirmar (Recomendado)" (R2), and ADR 0283. The body lists each moved or deleted assert with `path:line`. No assert is loosened.

- `test_branch_policy.py`: move the five PR-only rows (:132-136) and the M2 `_existing_principal` rows (:137-141) to the admitted table (default and custom gitflow; create and update; matching refspec). Delete `_PR_TO_*` (:122-123), `_birth_fix` (:126-127), `_birth` (:58-64), the birth rows (:108-111), `_birth_from_any_source` and its row (:82-86, :112). Row :136 (a tag aimed at the principal) stays refused; its `named` string becomes the outside-the-gitflow text. Row :144 stays refused with the refspec text. Keep the refusal of a mismatched refspec aimed at a role branch.
- `test_ci.py` births test (:221-276): :255 and :263 stay admitted; :267-276 ("a birth carrying a new commit is refused") flips to admitted; rename it to "any push of a role branch passes the gate".
- `fix_world.py`: delete the Case at :1263 and the Skip at :1268, and the helpers `_birth_published`, `_develop_at_main` (:422-431). The worktree-verbs Skip stays, so the census holds.
- `test_push_gate.py:207`: delete the `remote_branch` fake. It is dead today: `_Raising` pushes a work ref, which the gate never asks about.
- `test_push_gate_check.py`: reword the :5 docstring and the :78 comment; add two `test_pass_matrix` rows, a push of `refs/heads/main` and of `refs/heads/develop` from the same-named head, each exit 0.
- The rows fail on today's gate for the real reason (the PR refusal): record the red run in the body.
- Done: `pytest tests/features/chokepoints tests/cli/commands/test_ci.py tests/e2e/test_push_gate_check.py tests/core/test_cli_line__refusal_fix_lines_clear_their_refusal.py`; the harness census `pytest tests/core -k cli_line`.

## J2.T2 — RED, the baseline's local heads

- One new test in `test_service__context_baseline.py`, over the empty-origin and the principal-only scenarios: after `baseline`, `refs/heads/<integration>` and `refs/heads/<principal>` exist locally, at the tips origin holds. It fails today because the push only names remote refs.
- Rows :156, :159, :162 and :187 are not touched. Record the red run. Done: `pytest tests/features/spec_context/test_service__context_baseline.py`.

## J2.T3 — `_publish`

- `service.py:632-649`: each missing role branch (integration, principal) is created as a local `refs/heads/<role>` at its tip, which is origin's principal when origin has one, else the anchor; the one atomic push then names those heads, beside the work branch. The gate sees only same-named heads.
- Never move an existing local ref. If a row cannot pass without that, stop and return the finding to the main thread (PLAN section 6, point 1). `fetch` and `push -u origin` still need `origin`: that is the SPEC's non-goal, unchanged.
- Verify the order works against today's gate too (the heads are admitted as births); the four baseline rows stay green. Done: `pytest tests/features/spec_context`.

## J2.T4 — the deletion

- `branch_policy.py`: delete the role-birth arm (:109-119) and the principal/integration PR arm (:136-139) of `_refuse_branch`, which keeps its role-None arms; delete `check_branch_policy`'s `births` parameter and the `role in (principal, integration) and local_sha in births` line; the condition becomes `role is None and not _pushable(branch)`; fix the docstring (it still says PR-only).
- `push_gate.py`: delete the `unborn`, `bootstrap` and `births` block (:194-205), the `ObjectSource.remote_branch` row (:53) and the `ObjectSource.unpublished` row (:51), now without a gate reader. `git_objects.py`: delete `remote_branch` (:690-693). Keep the module `unpublished` and the class method `GitSubprocessObjectReader.unpublished`.
- Body, counts: `rg -n 'births|bootstrap|remote_branch|PR/MR' dadaia_workspace/` prints 0 hits in the three files; `git diff --numstat` shows the three files net < 0 (SPEC goal 4). Revert-check: reverting this task turns J2.T1 red.
- Done: `pytest tests/features/chokepoints tests/features/spec_context tests/cli/commands/test_ci.py tests/infrastructure/test_git_objects.py tests/e2e/test_push_gate_check.py tests/core`.
