# SPEC — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-28
**Origin:** bugs:gitflow-requires-a-remote-and-a-pr-host

---

## Bug window review

**Window:** every record closed after rc-24's window review (rc-24 born 2026-10-25T21:25:46Z, `_RELEASE.json` log), read in `BUGS.jsonl` at `34b8d8e64`: 48 resolved, 1 superseded, none rejected. Each fix is found by its id line (`git log -E --grep '^(fix|refactor)\(bugs\): '`), checked against its record's `fix_sha`; net lines are `git show --numstat`. `bugs.py stats` reports no REBUILD due on any unit these fixes touch.

| fix (ids) | fix commit, net | reading | verdict |
|---|---|---|---|
| gitflow-law-refuses-the-release-pr-the-releases-law-promotes | `4a473a049` (−1); RED `9a17177ac` | Widened the principal's PR source and pinned the PR-only refusal in five exact rows. It kept the refusal that accepted ADR 0214 forbids. | REBUILD: the symptom patch this pick removes (FR1, FR4). |
| gitflow-step2-reads-a-principal-only-commit-as-undeployed-work, promote-and-release-pr-each-name-two-things, reviewer-memory-stop-omits-the-shape3-mirror | `75be1ad08` (+1, law) | Step 2's merge-tree property is right, but it wrote `origin/` refs after ADR 0214. Step 10 names each PR once. The persona points to §3a. | Step 2 and step 10: REBUILD by FR3 and FR4 (the property and the one-home structure stay; `origin/` and "PR" go). Persona: KEEP. |
| gitflow-step4-reads-pr-merge-commits-as-a-stale-work-branch, slop-verify-commands-escape-their-pipes-and-never-match | `24065591c` (+14) | Step 4 points to step 2's one property, which is right, and inherits its `origin/` refs. SLOP moves to one fenced block. | Step 4: REBUILD by FR3. SLOP: KEEP. |
| capabilities-tells-consumers-credentials-live-in-a-workspace-env-file, releases-law-makes-the-candidate-pr-a-routine-step, sr-persona-tells-the-engineer-to-write-into-repos | `2aedcf5eb` (0); RED `131c37a30` | A dead key deleted; the candidate PR given one home (step 8); one write-target statement. | KEEP. The one home is where FR4 rewrites the PR. |
| ledger-commands-…-cannot-run-as-written, memory-update-restates-…, rc-flow-makes-the-candidate-pr-routine-…, code-review-audit-lens-… | `353d8376a` (+8); RED `14c9c7649` | The commands gained `--specs`, and restated rules point home. Two child bugs followed in the same scan (next row). | KEEP. The chain converged (next row). |
| stated-ledger-commands-omit-required-arguments-…, specs-canon-renders-retired-files-as-live-members, memory-law-sends-stale-memory-… | `a9d4fe9f2` (+14); RED `6271ea372` | The presence rule is deleted for a parse under each script's own parser. `CanonEntry.display` is one field on the one table, and the doctor's admitted set is unchanged. | KEEP. One decider; there is no second list. |
| repo-docs-state-ledger-commands-the-scan-never-reads | `ee6d43294` (0, docs); RED `a7b1312b4` | The same scan reaches `docs/*.md`. | KEEP |
| onboarding-names-the-refused-bind-to-an-ungoverned-session; its child hook-names-the-refused-bind-when-the-session-record-is-unreadable | `0c4015df0` (+22), `4f3ef29af` (+21); REDs `e79d2b89e`, `5e1902205`, `e956e4c1e` | A child bug after a REBUILD. The child moved the decision into one `core.invocation.refused_bind_fix` that every printer asks, and the cli copies are deleted. Changed test rows (`8f02a1b78`, `1153a15ed`) name the main thread's ruling. | KEEP. Two rounds converged on one decider; the growth buys it. |
| memory-catalog-generate-wipes-or-crashes-…; child memory-catalog-render-rewrites-the-blank-lines-…; memory-index-created-from-two-templates, memory-cli-text-misstates-the-catalog-writer | `6c059657e` (−1), `46a6eae2d` (+1), `348d5c076` (−8); REDs `4643c770d`, `fe79b9c4c`, `43d6add8b` | Exact-heading predicate; separator only on append; the second template deleted. The fixture change `ed33978e9` names its ruling. | KEEP. It ends in a deletion. |
| first-pass-done-while-the-product-index-keeps-the-scaffold-text | `618036644` (+4, +3 data); RED `b37d50c2e` | `if name == _INDEX` keys on the one memory file with a generated section and asks that section's owner (`load_owner`, the existing seam). It does not re-implement the boundary. | KEEP |
| memory-law-calls-the-product-index-generated-… | `da1bc8f8c` (0); RED `812607d01` | One statement, in the scoped memory law. | KEEP |
| memory-window-skips-commits-landed-between-candidates | `c5160721d` (+8); RED `4b39f7dc4` | One reader (`by_subject`) opens the window. | KEEP |
| reviewer-persona-disowns-…, jr-persona-lacks-the-skills-…, sr-persona-carries-unpaired-prohibitions | `a6ab86746` (+1) | Persona text and two grants. | KEEP |
| subagent-text-routes-alerts-to-the-operator-…, personas-restate-one-prohibition-… | `1e9dfcb16` (−5); RED `fc4bf8431` | One routing rule for five personas. | KEEP |
| doctor-fix-help-says-nothing-else-is-auto-fixed-…, skill-script-help-takes-the-docstring-first-line-… | `e50a3885b` (+13); RED `ddb50c5e6` | Three help descriptions become one owner, and eight scripts share one expression. | KEEP |
| hook-lane-cost-test-counts-one-more-op-on-a-loaded-ci-runner | `f5db5f5fa` (+10, tests); RED `72eeeeb72` | The counter counts the workspace's own ops. The deleted cold-cache env pin was a setting, not an assert, and a `> 0` assert was added. | KEEP |
| root-map-claims-the-verdict-act-on-codex-…; child verdict-act-guard-test-reads-a-catch-all-… (superseding codex-pre-gate-never-sees-a-shell-call-…) | `cbd7c8107` (+19, guard test), `51762f1ed` (0) | The law now states the code's condition. The child corrected the guard's predicate. | KEEP |
| pre-push-refusal-misnames-the-pushable-set-and-advises-a-raw-merge | `ed36aed70` (−2); RED `b50697f51` | REBUILD of the outside-the-gitflow arm, which survives this pick. | KEEP |
| worktrees-law-lists-the-tests-tmp-check-…, sync-conflict-fix-line-…, release-events-says-the-carry-note-… | `6a2cef7d1` (0); RED `328ccc0e6` | Law matches code; one fix line; one `startswith`. | KEEP |
| law-states-the-context-binding-rungs-wrong, context-map-…, histo-record-schema-…, knowhow-… (2) | `ee514e6b3` (−1); RED `7ab5b62a0` | Law and schema follow the code. | KEEP |
| gitflow-shapes-omit-three-operator-ordered-writes; gitflow-hotfix-shape-cannot-carry-the-specs-mirror-… | `698a5fa63` (+1), `92d8c1eb6` (0) | §3a rows only. | KEEP |
| reports-validate-calls-a-missing-content-hash-a-mismatch | `530b20cb6` (+2); RED `21500837f` | One decider, two cases. | KEEP |

**Overfitting check.** Every changed assert names its ruling. No special case keys on a test value. The growing fixes (`0c4015df0` with `4f3ef29af`, `e50a3885b`, `cbd7c8107`) each collapse copies into one home. The REBUILD verdicts (`4a473a049`, and the `origin/` and PR parts of `75be1ad08` and `24065591c`) are the open bug this candidate picks. Their surface is the one 44d9f4a1f patched, the fix of `public-law-teaches-the-private-pipeline`, which left the refusal in place. No new bug is proposed.

## 1. Problem

The operator's words (grill handoff `2026-10-28T012556Z-main-rc25-grill`, AskUserQuestion):

- R1, the rule that stands (2026-10-27): "Remover o PR-only (Recomendado)". ADR 0214 is followed as written. The pre-push gate stops refusing direct pushes of the principal and integration branches. The PR becomes the host's own branch protection, which is the user's choice. The refusal's tests are rewritten on this order, and the client-side guard against an agent pushing the principal is lost.
- R2, the summary (2026-10-28): "Confirmar (Recomendado)".

Accepted ADR 0036 decides "Every other push to those branches stays refused with its fix". Accepted ADR 0214 decides the library requires of a user's repo "only the lines it declares itself and local git, never a remote, CI, a PR host". The shipped library holds both decisions:

- `features/chokepoints/branch_policy.py:136-139` refuses every direct push of the principal or integration branch with "open a PR/MR … on your git host".
- `dd-gitflow-default` SKILL.md:39-40 say both advance "only by PR".
- Step 2 (SKILL.md:20, which step 4 reuses) runs `git merge-tree --write-tree origin/B origin/A`. On a repo with no remote, that command exits 1 with "origin/develop - not something we can merge" (the bug's repro).

Scorecard round 10 (`agentic-scorecard/20261027T0803Z/r10-official_min.md`), judge B, scores dd-gitflow-default S10 = 8 and set C1 = 8 on this bug, so the ship gate fails and 0.5.0 continues with rc-25. CICD-AUTOMATION.md:3 already states the intended contract: "the branch contract runs on local git and the repo's tracked `verify:` line alone".

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | the scorecard cells this bug holds pass | dd-gitflow-default S10 ≥ 9 and set C1 ≥ 9, from both judges | the next scorecard over the library sources |
| 2 | the gitflow runs on local git | step 2's command, as written, exits 0 on a repo with no remote | the probe in the J1 commit body, re-run at review |
| 3 | no shipped refusal or law requires a PR host | zero hits for the sweep of AC5.2 | `rg` at review |
| 4 | the gate shrinks | `branch_policy.py`, `push_gate.py`, `git_objects.py` and `spec_context/service.py` net < 0 together | `git diff --numstat <rc-25 base>..E` |

## 3. Non-goals

- **The adjacent ADR 0214 sites.** These are `infrastructure/git_subprocess.py:259-266` `published()` (reader `features/workspace/onboarding.py:136-142`), baseline's `fetch --prune --tags origin` (`service.py:573`) and `push --atomic -u origin` (`service.py:649`), and `dead()`'s refusal of a remote-less repo (`service.py:731`, `git_subprocess.py:176-183`). They stay out of rc-25 (as-is Q7, grill summary item 7). The main thread inspects each one and registers it as a bug if it breaks ADR 0214. FR2 changes only the refspec baseline pushes, never whether it needs `origin`.
- **A client-side guard against a force-push or a non-fast-forward of the principal or integration.** The rule stays law (AC4.4), as a deletion of those refs already is, since `branch_refs` excludes deletions (R1: "loses the client-side guard").
- **A new gate on the merge.** That covers a verdict-bound push, a `worktree merge` lane kind for the work-branch merges, and any script that checks a PR (as-is Q1 B and C). The merge gate stays discipline, as §3b is today.
- **The other two r10 defects**, `root-map-protected-class-names-only-the-law-files` and `orchestration-restates-the-hotfix-exemption`. They take one hotfix lane, outside this candidate.
- **`release.py ship --pr`.** It stays optional, as it already is. Only its help text changes (AC5.1).
- **Another context's own law.** `repos/dd-chain-explorer/specs/constitution.md:121` ("main advances only by PR") is that user's choice, and the main thread only flags it.

## 4. Requirements

**Wave ranking:**

1. Law, skills and dev loop: FR3, FR4 and FR5, the gitflow law and every site that restates it (Job 1).
2. Shared foundation: none.
3. Features and bugs: FR1 and FR2, the gate code and the baseline publish (Job 2). Its write set is disjoint from Job 1's, and the PLAN's DAG decides the edge.
4. Promote-facing: FR6, at closure.

The tests the operator's order rewrites (R1: "the refusal's tests are rewritten on this order"; R2 lists them) are these. Each change lands in a `test(<id>)` commit that names R1 and ADR 0283:

- `tests/features/chokepoints/test_branch_policy.py`. The five PR-only rows (:132-136) and the M2 `_existing_principal` rows (:137-141) move to the admitted table. The `_PR_TO_*` (:122-123) and `_birth_fix` (:126-127) literals, the `_birth` helper (:58-64), the birth rows (:108-111), and `_birth_from_any_source` with its row (:82-86, :112) are deleted. Row :136, a tag aimed at the principal, stays refused with the outside-the-gitflow text.
- The births test in `tests/cli/commands/test_ci.py` (:221-276). :255 and :263 stay admitted, and :267-276 ("a birth carrying a new commit is refused") flips to admitted.
- `tests/fixtures/fix_world.py`. The Case and Skip at :1262-1269 and the helpers at :422-431 (`_birth_published`, `_develop_at_main`) are deleted.
- `tests/core/test_gitflow.py`. :154 and :171 ("advances only by PR") and :170 (`== ["work"]`) are repinned to the new history-rewrite line.
- `tests/public/skills/dd_release_implementation/scripts/test_release.py:586`, which pins `SHIP_PR` (`_release_phase.py:116`).
- `tests/e2e/test_push_gate_check.py`, its :5 docstring and :78 comment.
- `tests/features/chokepoints/test_push_gate.py:207`. The `remote_branch` fake leaves with its protocol row.

### FR1 — the pre-push gate admits the principal and integration branches (R1)

- AC1.1 A push of `refs/heads/<principal>` or `refs/heads/<integration>` from the same-named local head is admitted:
  - on a creation and on an update;
  - on the default gitflow and on a custom one;
  - whether or not the push publishes new objects.

  Test: unit, `test_branch_policy.py`'s admitted table and the `test_ci.py` births test; E2E, `tests/e2e/test_push_gate_check.py`.
- AC1.2 Each of these stays refused with its existing message and fix:
  - a refspec whose local ref differs from the remote ref, including one aimed at a role branch;
  - a non-head (a tag) aimed at a role branch, with the outside-the-gitflow message;
  - a ref outside the gitflow;
  - the denylist and canon scans of the pushed range.

  Test: unit, `test_branch_policy.py` and `test_push_gate.py`, with existing rows only.
- AC1.3 No program prints "is never pushed directly — it advances only via a PR" or "open a PR/MR … on your git host". `_refuse_branch` keeps only its role-None arms. Test: unit, since the five PR-only rows flip (AC1.1); the fix-line harness drops the PR Skip row.

### FR2 — the bootstrap birth is deleted, and baseline pushes ordinary heads (R2 item 2; main-thread ruling on the pre-mortem)

- AC2.1 These have zero readers in `dadaia_workspace/`:
  - `check_branch_policy`'s `births` parameter and its `role in (principal, integration) and local_sha in births` line;
  - push_gate.py's `unborn`, `bootstrap` and `births` block (:194-205);
  - `ObjectSource.remote_branch` and `git_objects.py` `remote_branch`;
  - the role-birth refusal, with its `push origin refs/remotes/origin/<other>:<ref>` fix line (branch_policy.py:109-119).

  The PLAN names the remaining readers of `unpublished` before anything is deleted. Test: unit, for the rewritten rows above; the commit body carries the zero-reader `rg` count.
- AC2.2 `context baseline`'s `_publish` (`features/spec_context/service.py:632-649`) creates each missing role branch as the local `refs/heads/<role>` at its tip, which is origin's principal when origin has one, else the anchor. It then pushes those heads by name, beside the work branch, in one atomic push. The gate sees only same-named heads and keeps one rule. Test: integration. The baseline rows of `tests/features/spec_context/test_service__context_baseline.py` at :156 (empty origin), :159, :162 (principal-only births) and :187 stay green unchanged, and they fail if AC2.1 lands without AC2.2.
- AC2.3 The gate shrinks (goal 4). Test: none, because it is a size criterion; `git diff --numstat` is read at review.

### FR3 — steps 2 and 4 read a repo with no remote (R2 item 3)

- AC3.1 Step 2 defines once that "ref R is `origin/R` when the repo has a remote, else the local `R`". It then states the merge-tree property over those refs, and step 4 keeps pointing at step 2. No bare `origin/` literal remains in steps 2 and 4. Test: none, because no program reads the line (`rg merge-tree tests dadaia_workspace` prints 0 hits). The J1 commit body carries a probe, which the reviewer re-runs: on a repo with no remote, `git fetch --all --prune` and the step's command, as written with local refs, both exit 0, and a real undeployed change still reads as undeployed.

### FR4 — the merge, through a PR only when the host has one, advances integration and principal (R1; R2 items 1, 4, 5)

- AC4.1 In §2a, the integration and principal rows are pushable ("Yes"). Integration advances by the merge of the work branch (step 8). Principal advances by the integration → principal merge, or by the pipeline PR the project's own release pipeline opens. Each merge goes through a PR when the host has one. The row labels that `test_gitflow.py:147-149` reads stay. Test: unit, `tests/core/test_gitflow.py`, which parses the rows.
- AC4.2 Steps 8 to 11 name one verb: merge, through a PR when the host has one. Step 10 keeps its pipeline-PR clause, and step 11 starts "After the promote merges". The description (:4), §1 (:14) and §4 (:85) say the same. Test: none, because no program reads these lines; they are read at review.
- AC4.3 §3b becomes the merge gate. The work → integration merge and the integration → principal merge each require the repo's `verify:` line green and a `dd-code-reviewer` APPROVED verdict on the merged head, security lens included. When the merge goes through a PR, the main thread quotes the verdict in it. The gate stays discipline, with no script and no new gate. Test: none, because the gate is discipline and no program checks it (R2 item 1).
- AC4.4 The history-rewrite line (SKILL.md:32) covers the work, integration and principal branches as law: rewriting their pushed history or force-pushing them is refused unless the operator authorizes the act in its own turn. Test: unit, `tests/core/test_gitflow.py` :154, :170 and :171, repinned on R1.

### FR5 — no other shipped law requires a PR host (R2)

- AC5.1 Each site states the merge:
  - root map `public/data/AGENTS.md` :55 says "the merge gate is discipline", and :94;
  - `public/data/CONTEXT-MAP.md:64`;
  - `public/data/dadaia-AGENTS.md:25`, projected to `.dadaia/AGENTS.md`: the PR-only and initial-ref sentence goes, and the pre-push hook admits the branch contract's pushable branches;
  - `public/data/worktrees-AGENTS.md:17` says "a promote is its merge plus `release.py ship`";
  - `public/scaffold/releases/AGENTS.md:44` says "Promote is the integration → principal merge (step 10)". Its tracked mirror `specs/releases/AGENTS.md` is re-rendered by the doctor, and the shipped-hashes digest and the `CANON_AT[13]` re-pin ride the commit (shape 3);
  - `dd-release-implementation` RC-FLOW.md :9 ("promote at … the merge gate") and :40, and SKILL.md :4 and :7;
  - the help text of `scripts/release.py` :5 and :58 and the fix line of `_release_tree.py:304` say "the promote merge", whose PR is optional. `SHIP_PR` (`_release_phase.py:116`) is already conditional; if the PLAN rewords it, `test_release.py:586` is repinned on R1;
  - `dd-code-review` SKILL.md:61;
  - `dd-code-reviewer.md` :55 and :57, which repoint to the merge gate. A reviewer still reviews a PR where the host has one, so :3, :22 and :28 stay.

  `llms-full.txt` is regenerated, never hand-edited, and every projection is reprojected and doctor-verified. Test: unit, the existing canon-digest test (`tests/core/test_specs_version.py:41`); every other line has no test, because no program reads it.
- AC5.2 After Job 1, `rg -n 'PR gate|only by PR|PR-only|only via a PR|merging the promote PR|records? the merged promote PR|names the merged promote PR' dadaia_workspace/public docs README.md llms.txt llms-full.txt` prints nothing. Test: none, because a text grep is not behaviour; the grep runs at review.

### FR6 — memory (closure)

- AC6.1 The closure memory pass (`MEMORY-UPDATE.md`) does two things:
  - It lists ADR 0283 beside 0036 in `specs/memory/ARCHITECTURE.md:148` once 0283 is accepted.
  - It rewrites the atoms that state the PR-only rule or the birth: `sdd/sdd-gate-v3.md`, `sdd/release-lifecycle.md` and `agents/agent-comms.md`, each checked against the code.

  The derived `docs/getting-started.md` :171 and :174 state the merge (shape 9). Test: none; `memory.py check` and `doctor` exit 0.

### Replaces

- The PR-only refusal of a direct push of the principal or integration branch, with its fix "open a PR/MR … on your git host" (`branch_policy.py:136-139`). FR1 replaces it.
- The ADR 0036 bootstrap birth: the `births`, `bootstrap` and `unborn` computation (`push_gate.py:194-205`), `ObjectSource.remote_branch`, `git_objects.remote_branch`, and the role-birth refusal and its fix (`branch_policy.py:109-119`). FR2 replaces it.
- Baseline's birth refspecs `<origin/principal or anchor>:refs/heads/<role>` (`service.py:646`), which only the birth exemption admitted. FR2 replaces them with local heads pushed by name (AC2.2).
- The `origin/`-only step 2 and 4 test (SKILL.md:20, :22). FR3 replaces it.
- "Advances only by PR" as how integration and principal move, and §3b's "Both PR edges" as the gate's subject. FR4 replaces both.

## 5. Constraints and risks

- **ADR 0283 comes first.** 0283 amends 0036, whose `measured_by` test FR1 and FR2 rewrite. The operator accepts it in this `wt-rc`'s define, with SPEC and PLAN, before any Job 2 task (grill summary item 6).
- **The lost guard.** Once FR1 lands, nothing client-side stops an agent from pushing or force-pushing the principal. AC4.4 keeps the rule as law. On the library's own repo, GitHub branch protection is the developer's guard, outside the library.
- **The baseline break.** If AC2.1 lands without AC2.2, every role-branch birth in `context baseline` is refused as outside the gitflow (pre-mortem 1). Both ride Job 2, and the baseline rows are its integration net.
- **Projections.** `.agents/skills/**` and `.dadaia/AGENTS.md` are reprojected and doctor-verified, never hand-edited.
- **The ship gate.** Goal 1 is measured by the scorecard before the promote, never in the rc close path. The two other r10 defects ride their own lane, and that lane must land for the scorecard to pass.
- **Size.** Job 2 shrinks the gate (about −35 source lines by the as-is estimate, before AC2.2's lines). Job 1 rewords law in place.
- **A stale developer comment.** `.github/workflows/ci.yml:3-5` holds a developer-only "PR only" comment. Nothing reads it, and the PLAN may refresh it.

## 6. Open questions

None for the operator: R1 and R2 rule the scope, and the main thread ruled the baseline publish (pre-mortem 1). The PLAN states two facts: the remaining readers of `unpublished` (AC2.1) and the probe of AC3.1.
