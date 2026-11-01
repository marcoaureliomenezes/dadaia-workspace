# Job 1 — the gitflow law runs on local git (FR3, FR4, FR5)

**Status:** Draft

| task | who | AC | `W:` | owner test | outcome |
|---|---|---|---|---|---|
| J1.T1 | sr | AC4.1, AC4.4 | `tests/core/test_gitflow.py` | `tests/core/test_gitflow.py` | RED: line 32 covers work, integration, principal; their rows are pushable |
| J1.T2 | jr | AC3.1, AC4.1 to AC4.4 | `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` | `tests/core/test_gitflow.py` | REBUILD of steps 2, 4, 8-11, line 32, §2a, §3b, §4, :4, :14; J1.T1 goes green |
| J1.T3 | jr | AC5.1 | `dadaia_workspace/public/scaffold/releases/AGENTS.md` `specs/releases/AGENTS.md` `dadaia_workspace/public/templates/shipped-hashes.json` `dadaia_workspace/core/specs_version.py` | `tests/core/test_specs_version.py` | step 44 says the merge; mirror, digest and `CANON_AT[13]` re-pinned |
| J1.T4 | jr | AC5.1, AC5.2 | `dadaia_workspace/public/data/AGENTS.md` `dadaia_workspace/public/data/CONTEXT-MAP.md` `dadaia_workspace/public/data/dadaia-AGENTS.md` `dadaia_workspace/public/data/worktrees-AGENTS.md` `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md` `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md` `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py` `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` `dadaia_workspace/public/skills/dd-code-review/SKILL.md` `dadaia_workspace/public/agents/dd-code-reviewer.md` `llms-full.txt` | `tests/public/skills/dd_release_implementation` | every other shipped site states the merge; the sweep prints nothing |

Wave 1, with Job 2 (disjoint `W:`, no edge). PLAN sections 1, 2 and 5 hold the design. Order: T1, then T2, T3, T4. Each task's Definition of done is `python scripts/ci.py job`, plus the directories named in its section below. Never the full CI line.

## J1.T1 — RED

The operator's order, named in the `test(J1.T1)` commit body: "Remover o PR-only (Recomendado)" (R1), with the grill summary "Confirmar (Recomendado)" (R2). Asserts moved, listed with `path:line`: `tests/core/test_gitflow.py:154` (`"advances only by PR" in scope`), `:171` (the same string in the rule), `:170` (`== ["work"]`). None is deleted or loosened; each tightens to the new rule.

- The rule line (the one holding "pushed history"; it must still split on `force-pushing,` with `pushed history of,` before it) reads, as the pinned wording: "Rewriting the pushed history of, or force-pushing, the work, integration or principal branch is refused unless the operator authorizes that act in its own turn." Pin: the scope holds `work, integration or principal branch`, no longer holds `advances only by PR`, and names none of `job`, `backlog`, `task`, `plain`.
- The row-word check (`:170`) expects `["work", "integration", "principal"]`: the three rows whose label the rule names, no `wt/` row.
- New assert (AC4.1): the Pushable cell of the `integration` and `principal` rows starts with `Yes`; the row labels `:147-149` read stay.
- Rename the two tests so the names no longer say "or_pr" (the rule no longer says PR).
- The tests fail on today's SKILL.md for the real reason (rule still says "advances only by PR"; rows say `No`). Record the red run in the body. Run: `pytest tests/core/test_gitflow.py`.

## J1.T2 — SKILL.md

`dd-gitflow-default/SKILL.md` only; `.agents/skills/**` is reprojected by the main thread, never edited.

- **Step 2 (AC3.1).** Defines once: "ref R is `origin/R` when the repo has a remote, else the local `R`". The merge-tree property is then stated over those refs, unchanged otherwise. Step 4 keeps pointing at step 2. No bare `origin/` literal remains in steps 2 and 4.
- **Steps 8-11 (AC4.2).** One verb: merge, through a PR when the host has one. Step 10 keeps its pipeline-PR clause. Step 11 starts "After the promote merges". Step 9's "work → integration PR merged" becomes the merge. The description (:4), §1 (:14) and §4 (:85) say the same.
- **Line 32 (AC4.4).** The T1 wording, exactly.
- **§2a (AC4.1).** Integration and principal rows: Pushable `Yes`; integration advances by the merge of the work branch (step 8); principal by the integration → principal merge, or the pipeline PR the project's release pipeline opens. Row labels unchanged. The principal's "Cut from" and "bootstrap only" text stays unless it restates the birth: delete any such clause.
- **§3b (AC4.3).** Renamed the merge gate. The work → integration and integration → principal merges each require the repo's `verify:` line green and a `dd-code-reviewer` APPROVED verdict on the merged head, security lens included; when the merge goes through a PR, the main thread quotes the verdict in it. Discipline: no script, no new gate.
- **Probe, in the commit body, re-run by the reviewer.** In a scratch repo with no remote: `git fetch --all --prune` exits 0; the step's command, as written with local refs, exits 0; one real undeployed change on the integration branch reads as undeployed (a tree other than the principal's).
- Done: `pytest tests/core/test_gitflow.py tests/public/skills/dd_gitflow_default`. `rg -n "origin/" dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` prints only the clause of the step-2 definition and the step-11 remote-ref clause.

## J1.T3 — the releases law and its derived files

- `public/scaffold/releases/AGENTS.md:44`: "Promote is the integration → principal merge (`dd-gitflow-default`, step 10); `RELEASE_PY ship --specs <specs-dir>` records it …", the rest of the line unchanged.
- The tracked mirror `specs/releases/AGENTS.md` is re-rendered by the doctor's render, never hand-edited.
- `templates/shipped-hashes.json` takes the new digest; `core/specs_version.py` `CANON_AT[13]` is re-pinned (stamp 13 is unpublished). Take the value from `test_a_canon_change_bumps_the_stamp`'s computation.
- Done: `pytest tests/core tests/features/migrate tests/features/specs`.

## J1.T4 — the other sites and the sweep

- Root map `public/data/AGENTS.md`: :55 "the merge gate is discipline"; :94 "branches, merges, commit shapes". `CONTEXT-MAP.md:64`: "the merge gate". `worktrees-AGENTS.md:17`: "a promote is its merge plus `release.py ship`".
- `dadaia-AGENTS.md:25`: the sentence about the initial ref for either PR-only branch goes; the hook admits the branch contract's pushable branches; the rest of the line (denylist, canon, range scan) is unchanged.
- `RC-FLOW.md` :9 ("promote at … the merge gate") and :40; `dd-release-implementation/SKILL.md` :4, :7; `release.py` :5, :58 and `_release_tree.py:304`: "the promote merge", its PR optional. `SHIP_PR` and `--pr` stay; `test_release.py` is untouched.
- `dd-code-review/SKILL.md:61` and `dd-code-reviewer.md` :55, :57 point to the merge gate; :3, :22, :28 stay. An AI-entity edit follows `dd-ai-eng-knowhow`'s AUTHORING contract.
- Regenerate, never hand-edit: `python scripts/llms_full.py > llms-full.txt`.
- Sweep (AC5.2), count in the body, expected 0: `rg -n 'PR gate|only by PR|PR-only|only via a PR|merging the promote PR|records? the merged promote PR|names the merged promote PR' dadaia_workspace/public docs README.md llms.txt llms-full.txt`.
- Done: `pytest tests/public tests/core`.
