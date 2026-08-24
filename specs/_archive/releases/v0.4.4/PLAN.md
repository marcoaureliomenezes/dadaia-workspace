# PLAN — Release v0.4.4 — organize the core

**Status:** Aprovado
**Amendment 1:** Aprovado (operator, 2026-08-23) (2026-08-23, the skills audit folded in — SPEC §2/§8). FR22–FR31,
tasks T-044-54 … T-044-62 and the plan lines marked *(A1)* await the operator's approval of
the delta; segments `S1 … S5` and the `rc` lane are unchanged in structure.
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

- **`S1` first** — it changes the mechanism this release integrates itself with (G4/G6);
  it also carries the HIGH marker bug (D7), on which every later segment's `[ ]/[-]/[x]`
  contract depends.
- **`S2` second** — the map must exist *before* any rename (D-6).
- **`S3` third** — the consolidation consumes both: `S1`'s pointers, `S2`'s map rows.
- **`S4` fourth** — orthogonal and additive; never entangled with work measured by deletion.
- **`S5` fifth** — bug sweep and branch hygiene (G8), both wanting a stable tree.

**Then, and only then, the `rc` lane.** A segment never reaches `develop` on its own: the
five close on the branch, and the release integrates **once**, whole, as `rc-1`. What comes
after `rc-1` is not more scope — it is what testing the merged `develop` finds about the
scope already merged.

*(A1)* **Amendment 1 does not reorder anything — it fills two segments.** `S3` grows from
"skills" to the whole AI surface (trims, disclosures, sediments, invocation model, personas,
per-prompt injection, and the double-load bug), all of it landing **before** the single
projection cycle so the golden regen is still regenerated once. `S5` **opens** with the
anti-loop pair (FR22 method, FR23 gate) so its own eight fixes are their first users. The
same principle governs both: **delete before you add**, and the measure is the diff.

Four properties are non-negotiable throughout:

1. **RED before GREEN**, on the executed path.
2. **Green at every commit** — `dadaia ci preflight`, `backlog doctor`, `specs doctor`,
   `public doctor`; no `--no-verify`.
3. **The standing order is an acceptance.** No puxadinho: no new branch, flag, second code
   path or cross-feature reach-in to make something pass. Every review verdict states the
   bug-surface delta of the feature it touched.
4. *(A1)* **The AI surface only shrinks** (A21.8): a task that grows
   `public/{agents,skills,data,entities}/**` justifies it in its commit message or is wrong.

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
| `cli` | `commands/context.py` (repo add/remove/list, create, show, list), `commands/ci.py` (help text, `gc-push-verdicts` re-key); *(A1)* `commands/bugs.py` — the `resolved`-evidence refusal | FR3, FR17, FR18, FR23 |
| *(A1)* `core` + `features/bugs` | `bug-event-v1` schema: the three evidence fields, historical events unchanged | FR23 |
| *(A1)* `hooks` | `ctx_inject` — the dispatcher preflight deleted, the ALIVE list only when unbound | FR30 |
| *(A1)* `public/agents` + `public/skills` (2nd pass) | the nine personas cut to 120–220 lines with the bug-surface axis, one pass per file; `dd-bug-fix` as method; the four trims; the five disclosures + siblings; the sediment sweep; the invocation model | FR22, FR24–FR29 |
| *(A1)* `infrastructure/public_assets` | one decision at the projection seam: which harness receives the rules-dir law mirror | FR31 |
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
       → (A1) FR25 trims → FR26 disclose → FR28 invocation → FR24+FR29 persona pass
       → FR27 sediments + citation check → FR31 double-load bug → FR30 ctx_inject
       → FR13 projection + goldens, ONCE (+AR-1 ruling) → FR14 study handoff → QA close
       ↓
S4   FR15 model+migration → FR16 alive/dead → FR17 verbs → FR18 surfaces (+superseded bug)
       → FR19 one control point → QA close
       ↓
S5   (A1) FR22 dd-bug-fix method → FR23 resolved-evidence gate
       → 8 bug tasks (Arm B, first users of both) → FR20 branch hygiene → QA close
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

**A segment close is a commit, not a merge** (SPEC D8): `S1 … S5` each end with a
`qa-engineer` review committed to `feature/0.4.4`. The order **review → closure → archive
→ ship** holds across the lane — the six-axis review on the thawed tree before `rc-1`, a
delta review per later `rc`, and only the final `rc` carrying memory, CLOSURE and archive.

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

**Two recorded mechanical limits** — the CI job that cannot run on its own PR, and the
non-editable workspace venv — are stated once in SPEC A4.4 and D-3 and carried by tasks
T-044-07 and T-044-10. Not restated here.

---

## 5. Approach per segment

**`S1` — gitflow v2.** Law first (one section, cross-references everywhere else), then the
skill (rename + rewrite in one touch, D3), then the code, then CI, then the pointer sweep —
so no pointer ever names a home that does not yet exist. The sweep is mechanical and
measured: 14 surfaces, A5.1's grep the completion proof. FR6 rides here because it edits
the same preflight script whose header FR5 trims.

**`S2` — the map.** The JSON is authored first and seeded from the scan's §F rows; the
schema pins its shape; the constitution states the law; the enforcer lands last and must be
green at HEAD the moment it lands. `lint-skill-collisions.py` dies in the **same commit**
as the enforcer, with its `--self-test` fixtures ported, so coverage never has a gap
(D4/A9.4).

**`S3` — the AI surface.** Order inside the segment matters: fold (`dd-release-closure` →
`dd-release-implement`) before the AI fusion, because the fold's pointers are rewritten by
the fusion's pass over agents; renames after both, one commit per skill, each carrying its
map row so the `S2` enforcer is never red. *(A1)* Then the audit's content work, in the only
order that is satisfiable: **trims → disclosures → invocation model → the persona pass →
the sediment sweep, whose citation check lands last and green at HEAD** (D-10) — a check
that runs `test -e`/`--help` over every citation can only be green once the personas have
been cut, because seven of the sediments live in them. The double-load bug and the
`ctx_inject` reduction follow, both before the **single** projection cycle: the bug changes
the projected inventory, and one regen is the whole point (D11/AR-1). The study reads the
*final* inventory and produces proposals only; the audit's dispositions enter it as evidence
(A14.5), never as decisions.

**`S4` — associated repos.** Model and migration first (schema v3, backup-first,
idempotent), then lifecycle, verbs, surfaces. One accessor for "the context's repos"
(A15.3) is the structural requirement: alive, dead, show, list, export, panel and ci read
the same collection, so the `list`/`show` divergence cannot re-form (A18.3).

**`S5` — the loop, then the bugs, then the branches.** *(A1)* The segment **opens** with
FR22 (the diagnosing method) and FR23 (the `resolved`-evidence gate), so its own eight fixes
are the first work run under both — the audit's numbers (132/438 evidence-free resolutions,
24-minute median, 84–95 % re-bug) describe exactly the cadence a sweep would otherwise
repeat. The gate must be **satisfiable on the first real fix** (A23.6); if it is not, that
is a defect fixed here — no bypass flag exists. Then the eight
Arm-B tasks, whose per-bug approach TASKS carries in full: four are test-quality or
advisory-guard defects whose correct fix is **smaller** code, two are decide-then-state
defects, and two are one root — `backlog-doctor` under-validating its own document schema —
fixed **once**, in the parser. The branch hygiene runs last: tag, verify reachability per
branch, then delete.

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
| **V14** *(A1)* | **always-on tokens per session** — the law as each harness loads it + the 9 persona bodies + every always-loaded skill description; before (~8.4k) and after | A21.9 (≤ 3.5k), FR29, FR31 |
| **V15** *(A1)* | **negation census** (`never`/`do not`/`don't`/`forbidden`/`prohibited`) over `public/**`; before (160) and after | A21.9 (≤ 60), A29.4 |
| **V16** *(A1)* | **always-loaded description bytes**, before/after `disable-model-invocation` | A28.4 |
| **V17** *(A1)* | **per-skill and per-persona line counts**, before/after — the four trims, the five disclosures, the nine personas, the AI fusion | A25.5, A26.2, A29.1, A11.8 |
| **V18** *(A1)* | **injected-prefix tokens per prompt**, bound and unbound, on a **real** session | A30.1–A30.2 |
| **V19** *(A1)* | **AI-surface LOC added/deleted** over `public/{agents,skills,data,entities}/**` for the whole release | A21.8 (net-negative), CLOSURE's AI-surface accounting |

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
| *(A1)* Nothing lost in the pruning | the FR29 coverage table (per removed block, its surviving home) + A26.5's pointer check | the `S3` QA close and the six-axis review |
| *(A1)* Citations are real | FR9's citation check (`test -e` / `--help`) — machine, not inspection | `S3` close, then every commit |
| *(A1)* The Arm-B gate is satisfiable | `S5`'s first bug appends a well-formed `resolved` event on the first try (A23.6) | `S5` proceeds |
| *(A1)* The measured targets | V14–V19 at scope-complete, against SPEC A21.8–A21.11 | T-044-44 |

---

## 8. Technical risks

Carried in SPEC §6 (D-1 … D-10, AR-1, AR-2, R-1 … R-11) and not restated here. Four shape
the plan's order rather than a single task: **R-1** (`S1` changes the integration mechanism
itself, so it lands first and is proven by an executed-path probe), **R-2** (`S4` is the
only additive segment, so it is isolated and separately accounted), **R-8** (the `rc`
lane must not become a second pick) and *(A1)* **D-10** (`S3`'s citation check is green only
after the persona pass, which fixes seven of the sediments it checks).

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
7. *(A1)* The measured targets hold: AI surface **net-negative** (V19), always-on ≤ 3.5k
   (V14), negations ≤ 60 (V15), prefix ≤ 0.7k (V18), zero dead citations by check (A21.10).
