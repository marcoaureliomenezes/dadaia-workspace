# PLAN — Release v0.4.4 — organize the core

**Status:** Draft
**Release ID:** v0.4.4
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.4/SPEC.md`
**Branch:** `feature/0.4.4` (cut from `develop` — recorded exception E-1; branch contract:
`dadaia-gitflow`, renamed `dd-gitflow-default` by FR2)
**Segments:** `S1 … S5` — internal work boundaries, each closed by a `qa-engineer` review
**committed on the branch**, no merge, no PR (SPEC D8).
**Candidates:** `rc-1 … rc-N` (G5 — no alpha, no beta). `rc-1` burns when the **whole**
scope is implemented, validated, gate-green and closed by QA, and is merged into `develop`;
`rc-2 … rc-N` are adjustment rounds on that same scope found by testing the merged
`develop`; the final `rc` carries CLOSURE + archive and ships. If nothing is found, the
final `rc` **is** `rc-1`.

---

## 1. Strategy

One ordering principle: **install the mechanism before you use it, and delete before you
add.** Every segment either removes a statement, removes a file, or replaces two paths with
one; the single additive segment (`S4`) is isolated at the end of the implementation
ladder so its LOC is accounted for on its own.

The order is not a preference — each boundary is a constraint:

- **`S1` first** because it changes the mechanism this release integrates itself with
  (G4/G6): once it is live, every merge into `develop` is a PR from `feature/0.4.4`. It
  also carries the HIGH marker bug (D7), because every later segment depends on the
  `[ ]/[-]/[x]` contract being trustworthy.
- **`S2` second** because the map must exist *before* any rename, or `S3` would land
  skills the enforcer cannot place (D-6).
- **`S3` third** because the consolidation consumes both: it collapses gitflow pointers
  written in `S1` and registers each renamed skill in the map from `S2`.
- **`S4` fourth** because it is orthogonal and additive; it must not be entangled with
  the governance work whose measure is deletion.
- **`S5` fifth** — the residual bug sweep and the branch hygiene that G8 mandates, both
  of which want a stable tree.

**Then, and only then, the `rc` lane.** A segment never reaches `develop` on its own: the
five close on the branch, and the release integrates **once**, whole, as `rc-1`. What comes
after `rc-1` is not more scope — it is what testing the merged `develop` finds about the
scope already merged.

Three properties are non-negotiable throughout:

1. **RED before GREEN**, on the executed path.
2. **Green at every commit** — `dadaia ci preflight`, `backlog doctor`, `specs doctor`,
   `public doctor`; no `--no-verify`.
3. **The standing order is an acceptance.** No puxadinho: no new branch, flag, second code
   path or cross-feature reach-in to make something pass. Every review verdict states the
   bug-surface delta of the feature it touched.

---

## 2. Layers affected

| Layer | Modules / paths | FRs |
|---|---|---|
| `public/data` | `DADAIA.md` (source only — projected law is PROTECTED) | FR1, FR8, FR11 |
| `public/skills` | `dd-gitflow-default` (ex `dadaia-gitflow`), `dd-release-implement`, retired `dd-release-closure`, new `dd-ai-eng-knowhow` (retiring four), `dd-grill-me`, `dd-cli-library`, `dd-manager-orchestration`, `dd-workspace-doctor`, plus pointer-only edits to `dd-release-definition`, `dd-bug-fix`, `dd-bug-registration`, `dadaia-task-manager` | FR2, FR5, FR10–FR13 |
| `public/agents`, `public/entities` | seven personas; `registry.json`; **new** `rules-skills-map.json` + schema | FR5, FR7, FR12 |
| `public/scripts` | `pre-push-ci-gate.sh` header → pointer; **retire** `lint-skill-collisions.py` | FR5, FR9 |
| `public/scaffold` | `constitution.md` (new core-law section) | FR8 |
| `features/chokepoints` | `service.py` (`_PERMITTED_BRANCH_RES`, `_PUSHABLE_BRANCH`, `push_gate_decision`), denylist scan untouched in behaviour | FR3 |
| `features/spec_context` | context model consumers, alive/dead lifecycle | FR15–FR19 |
| `features/migrate` | `state_v2.py` → registry v2→v3 migration | FR15 |
| `features/export`, `features/panel` | `ExportService`, `PanelContext` | FR18 |
| `core` | `models/spec_context.py` (`SpecContextProject`) | FR15 |
| `cli` | `commands/context.py` (repo add/remove/list, create, show, list), `commands/ci.py` (help text, `gc-push-verdicts` re-key) | FR3, FR17, FR18 |
| `.github/workflows` | `ci.yml` triggers, `pr-source-guard`, verdict PR gate | FR4 |
| `scripts`/preflight | `lint-imports` joins the preflight sequence | FR6 |
| `tests` | unit / contract / integration only — **zero new e2e** without a named qa exception | all |
| `specs/constitution.md` | new core-law section (operator-confirmed) | FR8 |
| `specs/memory/**` | closure window only | SPEC §5 |
| `pyproject.toml`, `CHANGELOG.md` | `0.4.3 → 0.4.4` + `[0.4.4]`, at ship | final `rc` |

**Layer rules hold unchanged:** `features/**` imports neither `cli`, `infrastructure` nor
`hooks`; `core/**` stays stdlib-pure; `lint-imports` green with **no new** accepted edge —
and, after FR6, green locally as well as in CI.

---

## 3. Execution order

```
W0   definition commit → milestone (a), v1 mechanic (E-1/D2):
       merge feature/0.4.4 → develop · security review origin/develop..develop · push develop
       ↓
S1   HIGH marker bug (D7) → FR1 law → FR2 skill(+rename) → FR3 chokepoint → FR4 CI
       → FR5 pointer collapse → FR6 preflight parity → venv reinstall (D-3)
       → QA close + AR-2 ruling, committed on the branch
       ↓
S2   FR7 map JSON+schema → FR8 constitution (operator-confirmed) → FR9 enforcer
       (+ retire lint-skill-collisions) → QA close
       ↓
S3   FR10 fold closure → FR11 dd-ai-eng-knowhow → FR12 renames (one commit each)
       → FR13 projection + goldens (+AR-1 ruling) → FR14 study handoff → QA close
       ↓
S4   FR15 model+migration → FR16 alive/dead → FR17 verbs → FR18 surfaces (+superseded bug)
       → FR19 one control point → QA close
       ↓
S5   8 bug tasks (Arm B) → FR20 branch hygiene → QA close
       ↓
     scope complete: full gates → code review (thawed) → security review → QA closes
     the release
       ↓
rc-1 PR feature/0.4.4 → develop  [milestone (b), first v2 merge]
       ↓
rc-2…rc-N  test the merged develop → adjustment/fix/improvement on THIS scope
       → fixed on feature/0.4.4 → QA close → PR again (one rc per merge)
       ↓
final rc  memory window → CLOSURE → archive → version bump → PR → develop
       → ship develop→main → publish 0.4.4 → delete feature/0.4.4 + cut feature/0.4.5
```

**Sanctioned parallelism.** At most one pair per segment, declared in TASKS with disjoint
write sets. Everywhere else: **one `[-]` at a time**.

**A segment close is a commit, not a merge.** `S1 … S5` each end with a `qa-engineer`
review **committed to `feature/0.4.4`** — no PR, no `rc` burned, nothing reaching
`develop`. The release integrates once, whole, at `rc-1` (G4 milestone (b)). The order
**review → closure → archive → ship** holds across the lane: the six-axis review runs on
the thawed tree before `rc-1`, every later `rc` delta gets its own delta review, and only
the final `rc` carries the memory window, CLOSURE, the archive move and the ship.

---

## 4. The enforcement inversion, named precisely

This is the delta **`S1`** installs. It is stated here once; TASKS references it.

| Surface | Before | After |
|---|---|---|
| `features/chokepoints/service.py` `_PERMITTED_BRANCH_RES` | `^main$`, `^develop$`, `^feature/v\d+\.\d+\.\d+$`, `^hotfix/v\d+\.\d+\.[1-9]\d*$` | `^main$`, `^develop$`, `^feature/\d+\.\d+\.\d+$` — **no `v`**, **no hotfix row** |
| `features/chokepoints/service.py` `_PUSHABLE_BRANCH` | `"develop"` | `feature/{M.m.p}` is pushable; `develop` and `main` are refused, the message naming the PR path |
| `features/chokepoints/service.py` `push_gate_decision` | branch policy → denylist scan → security verdict | branch policy → denylist scan (**kept**: the feature push is now the first publication to `origin`); the **security-verdict step is deleted**, not disabled |
| `cli/commands/ci.py` | `push-gate-check` help/messages describe a develop push; `gc-push-verdicts --sha <landed develop tip>` | help/messages describe the v2 policy and the PR path; `gc-push-verdicts` re-keyed to the **merged PR head sha** (D5) |
| `.github/workflows/ci.yml` triggers | `push: [main, develop]`, `pull_request: [main]` | `push: [main, develop, feature/**]`, `pull_request: [develop, main]` |
| `.github/workflows/ci.yml` `pr-source-guard` | one rule: `main` accepts only `develop` | same job, two rules: `main` accepts only `develop`; `develop` accepts only `feature/{M.m.p}` |
| security verdict | pre-push hook, keyed on the pushed `develop` tip | **CI PR-gate job**, keyed on the **PR head sha**, on `feature→develop` and `develop→main` |
| `DADAIA.md` | `alpha-N → rc-N`; `develop` the only pushable ref; hotfix stage | **`rc-N` only**; `feature/{M.m.p}` pushable, `develop`/`main` PR-only; hotfix retired (G2) |

**rc burn.** Each merge of the implemented, validated, gate-green release into `develop`
burns one `rc-N` (G4) — the first is `rc-1`, after `S5`. `rc-N` never appears in a branch
name (G5), and a segment never burns one (SPEC D8).

**Two recorded mechanical limits** (both in SPEC A4.4 / D-3):
1. a CI job added on a branch does not run on the PR that introduces it — the `rc-1` PR is
   the PR that brings the verdict gate to `develop`, so the gate is advisory there and
   required from `rc-2`; making it *required* is a repo setting, and
   `gh api PATCH required_status_checks` clobbers the list, so it is re-supplied whole;
2. the workspace venv is not an editable install — `S1`'s chokepoint is not live until
   `.dadaia/.venv` is reinstalled, which is a step of `S1`'s close, verified by an
   executed-path refusal probe on both edges.

---

## 5. Approach per segment

**`S1` — gitflow v2.** Law first (one section, cross-references everywhere else), then the
skill (rename + rewrite in one touch, D3), then the code, then CI, then the pointer sweep —
so that at no point does a pointer name a home that does not yet exist. The pointer sweep is
mechanical and measured: the scan lists 14 surfaces, and A5.1's grep is the completion
proof. FR6 rides here because it edits the same preflight script the header of which FR5
trims.

**`S2` — the map.** The JSON is authored first and seeded from the scan's §F rows; the
schema pins its shape; the constitution states the law; the enforcer lands last and must be
green at HEAD the moment it lands. `lint-skill-collisions.py` dies in the **same commit**
as the enforcer, with its `--self-test` fixtures ported, so coverage never has a gap
(D4/A9.4).

**`S3` — skills.** Order inside the segment matters: fold (`dd-release-closure` →
`dd-release-implement`) before the AI fusion, because the fold's pointers are rewritten by
the fusion's pass over agents; renames after both, one commit per skill, each carrying its
map row so the `S2` enforcer is never red; then one projection cycle with the golden
regen; then the study, which reads the *final* inventory. The study produces proposals
only — nothing in the nine is touched.

**`S4` — associated repos.** Model and migration first (schema v3, backup-first,
idempotent), then lifecycle, then verbs, then surfaces. One accessor for "the context's
repos" (A15.3) is the structural requirement: every consumer — alive, dead, show, list,
export, panel, ci — reads the same collection, so the `list`/`show` divergence the
superseded bug reports cannot re-form (A18.3).

**`S5` — bugs and branches.** Eight Arm-B tasks (the HIGH marker bug landed in `S1`, D7).
Four of them
(`atomic-writer-drift-guard`, `crlf-fixture`, `no-ratchet-against-frozen-clock`,
`read-only-atom-honouring`) are test-quality or advisory-guard defects whose correct fix is
**smaller** code, not a new guard: the drift guard is replaced by a behavioural battery, the
CRLF fixture gains an explicit `newline=`, the frozen-clock ratchet is one source-scan
contract test in a shape the repo already uses, and the read-only guard is either documented
as advisory or moved after the no-change determination. Two
(`migration-normalises-crlf-atoms`, `symlinked-specs-root`) are decide-then-state defects:
choose the behaviour, state it once, pin it with a test. Two are doctor defects with a
shared root — `backlog-doctor` under-validating its own document schema — and are fixed
**together**, in the document parser, not with two independent checks. The branch hygiene
runs last: tag, verify reachability per branch, then delete.

**The `rc` lane — integrate, then mature, then ship.** Scope-complete first: full gates →
`code-reviewer` (six axes, thawed tree) → `security-reviewer` (the delta) → `qa-engineer`
closes the release; that is the trigger for **`rc-1`**, the PR `feature/0.4.4 → develop`
(milestone (b)). The merged `develop` is then **tested** — by the operator, by QA, by
anyone — and each finding on **this** scope becomes an adjustment worked on
`feature/0.4.4`, QA-closed and merged again: `rc-2`, `rc-3`, … one per merge, each with its
own delta code+security review. No new backlog ever enters an `rc` (SPEC A21.7): a demand
outside this scope is backlog for a later release. When a candidate is accepted, that
**final `rc`** carries the memory window (SPEC §5, one pass per atom, the two mandatory
atoms first) → CLOSURE → `git mv` archive → `pyproject 0.4.4` + `CHANGELOG [0.4.4]` → PR to
`develop` → ship `develop → main`, CI green, publish `0.4.4`, then — in the **same step**
(G3) — delete `feature/0.4.4` and cut `feature/0.4.5` from `main`.

---

## 6. Measurement plan

`product-engineer` has no shell. Each value below is produced by a named task step, captured
under `.dadaia/tmp/<agent>/<YYYYMMDD>/`, and cited as CLOSURE evidence.

| # | Measurement | Where used |
|---|---|---|
| V1 | `dadaia bugs status` at pick | SPEC §7's 11-bug claim |
| V2 | `specs doctor` + `backlog doctor` baseline | final-`rc` delta |
| V3 | grep census of branch-model statements, before and after `S1` | A1.1, A5.1, A5.4 |
| V4 | executed-path refusal probe: `feature/*` allowed, `develop`/`main` refused | A3.1, D-3 |
| V5 | `SKILL.md` byte totals per skill, before and after `S3` | A11.4, A2.5, G12 ceiling |
| V6 | skills inventory before/after (25 → 21) + map coverage | A7.2, A12.2 |
| V7 | golden multiset diff for the regen | A13.3 |
| V8 | registry v2→v3 migration round-trip on a real v2 registry | A15.1–A15.2 |
| V9 | `public doctor` `[ok]`/`[drift]`/`[missing]` counts | A13.1 |
| V10 | branch inventory on `origin` and locally, before and after `S5` | A20.2, A20.3 |
| V11 | production LOC added/deleted per segment | A21.4, `## Size accounting` |
| V12 | `dadaia bugs status` at closure (expect zero open from the picked set) | disposition sweep |
| V13 | `SPEC-DOC-031` count **after** the archive move | closure standing note |

---

## 7. Validation plan

| What | How | Gate |
|---|---|---|
| Every FR's acceptance ids | the owning task's own RED→GREEN evidence | task `[x]` |
| Segment integrity | `qa-engineer` review **committed on the branch** at each `S1 … S5` close | next segment opens |
| Release closed by QA | `qa-engineer` release verdict over the whole scope | the `rc-1` PR |
| Enforcement surface count | `software-architect` AR-2 ruling at `S1` close | `S2` opens |
| Golden mechanism | `software-architect` AR-1 ruling at `S3` | `S4` opens |
| Delta security | `security-reviewer` on each PR's head sha (advisory at `rc-1`, required after) | PR merge |
| Six-axis review | `code-reviewer` on the thawed tree at scope-complete, then per `rc` delta | the `rc-1` PR / archive |
| `rc` legitimacy | every `rc-N ≥ 2` names the defect on this scope it answers | CLOSURE `rc` ledger (A21.7) |
| Memory atomicity | `dadaia specs doctor` after the memory window | before CLOSURE commit |
| Consumer truth | `dadaia public doctor` + projection byte-diff | every segment with a `public/**` edit |

---

## 8. Technical risks

Carried in SPEC §6 (D-1 … D-9, AR-1, AR-2, R-1 … R-8) and not restated here. Three shape
the plan's order rather than a single task: **R-1** (`S1` changes the integration mechanism
itself, so it lands first and is proven by an executed-path probe), **R-2** (`S4` is the
only additive segment, so it is isolated and separately accounted) and **R-8** (the `rc`
lane must not become a second pick).

---

## 9. Definition of done

1. Every task in `TASKS.md` is `[x]`.
2. Every FR's acceptance ids hold, with evidence.
3. The scope-complete trio is APPROVED and every later `rc` delta re-reviewed, each verdict
   stating the bug-surface delta of what it reviewed.
4. Memory reflects the product as it is after this release; the two mandatory atoms are
   rewritten, not patched.
5. `CLOSURE.md` carries the disposition sweep, size accounting, test dispositions, the GC
   sweep, the `rc` ledger and the AR-1/AR-2 rulings.
6. The release directory is archived, `0.4.4` is published, `feature/0.4.4` is deleted and
   `feature/0.4.5` is cut from `main` in the same step.
