# SPEC — Release v0.4.4 — organize the core

**Status:** Draft
**Release ID:** v0.4.4
**Owner:** product-engineer
**Opened:** 2026-08-23
**Created:** 2026-08-23
**Branch:** `feature/0.4.4` (cut from `develop` — **recorded exception**, §2 E-1; branch contract: `dadaia-gitflow`, renamed by FR2)
**Consumes:** spec-context-associated-repos, gitflow-contract-v2-consolidation, rules-skills-governance-map, core-skills-consolidation
**Picked set:** the **four** `## ACTIVE` backlog entries (all four fully consumed) **plus
the 11 open bugs** at pick time. Ten bugs are solved in-release as Arm B on
`feature/0.4.4`; one (`context-list-current-branch-stale-for-alive-repo`) is
**superseded** by `spec-context-associated-repos` (§7). No audit is outstanding — both
2026-07 audits are archived and fully dispositioned (v0.8.0).
**Grill (mandatory, done):** `.dadaia/handoff/dadaia-workspace/2026-08-23T181855Z-claude-grill-me-v0.4.4.handoff.json`
— 18 questions over 2 rounds, frontier empty, operator confirmed. Its 18 ADR lines are
ratified below as **G1–G13** and its 7 inspection facts as **I1–I7**. None is re-litigated
here.

---

## 1. Problem and context

Four entries entered the backlog on 2026-08-23 in one operator session. They are not four
features — they are one act: **the core entities of this workspace are disorganized, and
the disorder is measurable.**

- The **git contract** is restated in ≥14 places and contradicts itself in two
  (`.dadaia/tmp/claude/20260823/gitflow-inventory.md`): the enforcement regex requires
  `feature/v…` while the law, the skill and every real branch use `feature/{M.m.p}`;
  `dd-release-implement` L43 tells the implementer to push a branch the law calls
  local-only. Neither divergence was ever caught, because the only code path that would
  catch them never runs.
- There is **no declared relation between a rule and the skill that operates it**. 25
  skills exist against 9 law sections; nothing says which skill operates which rule, so
  duplication accretes and no check can see it.
- The **skill surface itself is slop**: four AI-harness skills say overlapping things,
  `dd-release-closure` is a detached half of `dd-release-implement`, and each skill is one
  long `SKILL.md` far above the size of the pattern the operator adopted
  (the skills reference clone (`mattpocock/skills`)).
- A **Spec Context Project owns exactly one repo**, so a product spanning several
  repositories cannot be modelled at all — the operator must split the specs or fall back
  to submodules the tool cannot see.

**Why now.** The operator's standing order (permanent architecture review oriented by bug
history) makes this the first-class work: every one of the four is a *reduction* — fewer
statements of the same law, fewer skills, one map, one repo model. Nothing here adds a
capability the workspace did not promise; three of the four take surface away.

**Theme.** This is a **patch** release: it organizes core entities, it does not add
product capability. The one genuinely new capability (`associated repos`) exists to
*remove* the workaround the operator is forced into today.

---

## 2. Objective, and the decisions that shape it

Ship, in one release on `feature/0.4.4`, implemented as **five segments `S1 … S5`** and
matured through the **`rc` lane** (D8), such that at ship:

1. the git contract is stated **twice and only twice** — one `DADAIA.md` section and one
   skill — and the mechanical enforcers agree with it byte for byte;
2. every skill maps to exactly one law topic through **one JSON map** with **one**
   deterministic enforcer;
3. the skill set is smaller (25 → 21) and no skill was created that the consolidation did
   not require;
4. a Spec Context Project owns one main repo plus N associated repos, on one control
   point;
5. every open bug at pick time is closed or superseded;
6. `origin` carries only `main`, `develop` and archive tags.

Ownership is split by artifact class (`DADAIA.md` §2) and never crossed: `ai-engineer`
owns every skill, persona, rule, hook-surface and projected-asset edit; `software-engineer`
owns production Python, CLI, doctors, CI YAML and tests; `qa-engineer` owns test verdicts
each segment close and the release close; `code-reviewer` and `security-reviewer` run at
scope-complete (before the `rc-1` merge) and again on every later `rc` delta;
`software-architect` rules on the two architecture-review items named in §6;
`project-manager` dispatches and relays; `product-engineer` authors this definition, the
memory window and the closure.

### G1–G13 — the grill ADRs, ratified as given

| ADR | Decision |
|---|---|
| **G1** | **ONE release v0.4.4**, branch `feature/0.4.4`, cut once from `develop` as a **recorded exception** — `main` lacks the `develop` delta and the operator holds the 0.4.3 ship; **v2 takes effect at this ship**. |
| **G2** | Branch patterns: `main`, `develop`, `feature/{M.m.p}` **only** — no `v` prefix, no suffix. **No hotfix for now**; any other branch kind exists only on an explicit operator request. |
| **G3** | `feature/{v}` is cut **from `main`**; exactly **one** live feature branch; at deploy of `{v}`, delete `feature/{v}` and cut `feature/{v+1}` **in the same step**; bugs are fixed on the live feature branch in any phase, without ceremony. |
| **G4** | `develop` advances **only by PR** from `feature/{v}`: PR #1 when SPEC+PLAN+TASKS are `Aprovado`; every later merge of the implemented, validated, gate-green release **burns `rc-N`**. `main` advances only by PR from `develop`, at the final `rc`. |
| **G5** | **No alpha, no beta**: only `rc-N` and final. `rc-N` lives in the specs (`ACTIVE.md` phase + TASKS segments), **never** in a branch name. `rc` scope = fixes/adjustments of the current release, never new backlog. |
| **G6** | Pre-push/chokepoints **fully rewritten to v2**, nothing stale: `feature/*` push = local preflight + valid name; `develop`/`main` take no direct push; the **security verdict becomes a PR gate** (a CI job requiring an APPROVED `security-reviewer` handoff covering the PR head sha, on `feature→develop` and `develop→main`); CI runs on `feature/*` pushes and on PRs. |
| **G7** | Uniqueness, deletion and start-of-work rules are **discipline and guidance in the skill** (highly recommended, not deterministic); the CI/CD automation suggestion is documented for consumers. |
| **G8** | Remote slop branches (`chore/*` ×7, `feature/pi-fourth-harness-v1`, `feature/v0.1.10`, `feature/0.1.5 … 0.4.2` ×6): **tag `archive/<name>`, then delete** — "no fifth pattern". |
| **G9** | rules→skills map: **JSON owned by dadaia-workspace + a deterministic architecture test gating every deploy**; key = the **bold topic** of `DADAIA.md`; one skill per topic; every skill has a topic, not every topic has a skill; rule = concise statements, skill = complement, **no overlap**. |
| **G10** | An orphan skill is **fused or retired** by default; the law gains a topic only for genuinely always-on behavior. |
| **G11** | Skills: renames `dadaia-gitflow`→`dd-gitflow-default`, `dadaia-grill-me`→`dd-grill-me`, `dadaia-cli`→`dd-cli-library` (verified against the current CLI), `project-orchestration`→`dd-manager-orchestration`, `dadaia-workspace-doctor`→`dd-workspace-doctor`; `dd-release-closure` **folded into** `dd-release-implement`; `ai-harness-codex` + `ai-harness-claude-code` + `ai-context-engineering` + `harness-primitives` → **`dd-ai-eng-knowhow`**, a folder with `SKILL.md` + references/scripts following the skills reference clone (`mattpocock/skills`); the **9 remaining skills** get a **study task** proposing Update/Fuse/Retire/Merge per skill — **the operator decides before any execution**. |
| **G12** | Skill size/shape follows the skills reference clone (`mattpocock/skills`) (`writing-for-agents`, `SKILL-MECHANICS`, `invocation`). |
| **G13** | Associated repos: **one main repo per context** is the sole source of specs/bind/memory/releases/backlog; associated repos follow ALIVE/DEAD, are cloned clean with no scaffold, and their own specs (if any) are **ignored** by the spec context. |

### I1–I7 — the grill's inspection facts, carried as context

| # | Fact |
|---|---|
| **I1** | CI runs only on push `main`/`develop` and PR→`main`; pre-push refuses `feature/*` pushes; the chokepoints regex requires `feature/v…` while law and real branches use `feature/{M.m.p}`. |
| **I2** | `public/entities/registry.json` already holds personas/behaviors/rules/universal with a `schema_version`. |
| **I3** | `DADAIA.md` has 9 `##` sections for 25 skills; each skill today is a single `SKILL.md`, median size far above `mattpocock/skills`' 74 lines. |
| **I4** | `SpecContextProject` carries one `repo_slug`/`repo_url`; registry schema is v2. |
| **I5** | `pyproject.toml` is already `0.4.3`; PyPI latest is `0.4.2`; `specs/_archive/releases/v0.4.3/` exists → id collision, **resolved by the operator as v0.4.4**. |
| **I6** | Nothing consumes the old `refine-specs.html` report — handoff-first holds. |
| **I7** | `specs doctor` has no live-vs-archive duplicate-release-id rule; `DADAIA.md` law says `alpha-N → rc-N`, to be replaced by `rc-N` only. |

### D1–D8 — authoring decisions taken by `product-engineer`

| ADR | Decision | Reason |
|---|---|---|
| **D1** | One document set at `releases/v0.4.4/`; `ACTIVE.md` carries **no `segment:` line**. The `S1 … S5` segments and the `rc` lane live as blocks inside this release's `TASKS.md`. | A non-`none` `segment:` routes `SPEC-DOC-004`/`TREE-6` into `releases/<id>/<segment>/`; duplicated per-segment document sets would recreate the duplication this release exists to remove (v0.4.3 D1, ratified, holds). |
| **D2** | **E-1, the recorded exception.** `feature/0.4.4` is cut from `develop`, and **milestone (a) of this release follows the v1 mechanic** — merge `feature/0.4.4` into local `develop`, diff-based security review of `origin/develop..develop`, push `develop`. | v2's inverted chokepoint does not exist until FR3 lands; under today's installed hook a `feature/*` push is **refused**, so the definition PR of G4 is mechanically impossible before `S1` lands. **Every merge into `develop` from `rc-1` onward follows v2** (push `feature/0.4.4`, PR → `develop`). This is the bootstrap, stated once, and it expires the moment `S1` is live. |
| **D3** | The `dadaia-gitflow` → `dd-gitflow-default` **rename happens in `S1`**, in the same touch as its v2 rewrite — not in `S3` with the other renames. | One touch per file. Renaming in `S3` would rewrite the same folder twice and invalidate every pointer FR5 just repointed. |
| **D4** | **One enforcer, not two.** The map's contract test (FR9) absorbs every invariant `lint-skill-collisions.py` asserts, and that script is **retired** with its `DECLARED_OVERLAPS` table. | G9 makes the JSON the single declaration; a second hard-coded table is the duplication class this release removes. Coverage is *moved*, never dropped (A9.4). |
| **D5** | The **`dadaia ci gc-push-verdicts` verb survives**, re-keyed from the pushed `develop` tip to the **merged PR head sha**. | The verdict artifacts still exist locally and still need their ledger line; re-keying is a semantic change inside one existing path, not a new path. |
| **D6** | Under v2, **every agent stage runs on `feature/{v}`** — backlog definition, research and bug registration included. `develop` and `main` are pull/merge/PR targets only. | G3's "an agent never works on any branch other than `feature/{v}`" plus G4's PR-only `develop` leave no other coherent placement: a local commit on `develop` could never be pushed. Today's `DADAIA.md` §5 stage rows say `develop`; FR1/FR2 rewrite them. G3's same-step cut of `feature/{v+1}` guarantees a live branch always exists to receive that work. |
| **D7** | The HIGH bug `sdd-artifact-linter-mutates-task-markers` is **reproduced first, in `S1`**, ahead of the rest of the bug sweep. | Its claim is that a post-write linter silently flips `[ ]`/`[-]`/`[x]` markers and `**Status:**` tokens — the machine contract every later segment of this release runs on. It is settled before the release depends on it. |
| **D8** | **A segment is not an `rc`.** The scope is implemented as **five segments `S1 … S5`**, each closed by a `qa-engineer` review **committed on `feature/0.4.4`** — no merge, no PR, no `rc` burned. **`rc-1` burns only when the whole scope (S1–S5) is implemented, validated, gate-green and closed by QA**, and is merged into `develop` by the v2 PR — that is milestone (b). **`rc-2 … rc-N`** are adjustment rounds over that same scope — fixes, adjustments and improvements found by **testing the merged `develop`** (operator, QA, anyone) — worked on `feature/0.4.4` and merged again, one `rc` per merge. The **final `rc` ships** (`develop → main`); if no adjustment is found, the final `rc` **is** `rc-1`. | Operator ruling, verbatim: *"Não é possível ficar pegando backlog para uma mesma release. Exemplo RC1 para 1 backlog, rc2 para outro backlog. rcs são derivados de análises do que foi implementado numa release, mergeado na develop, não entregue na main — ajustes, fixes e melhorias em cima do release atual"* and *"2 milestones: PR quando Release definition é aprovada e PR quando [a release] é fechada pelo QA — quando releases são finalizadas"*. An `rc` is a **state of the merged release**, never a slice of its scope; a segment is an internal work boundary that never reaches `develop` on its own. |

---

## 3. Scope

**Standing rules for every segment.**

- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN.** Every behavioural task writes its failing test first and observes
  it failing for the real reason (`DADAIA.md` §6).
- **The standing order is an acceptance, not a preference.** Every task must leave the
  touched feature **smaller or equal** in surface: a fix that adds a branch, a flag, a
  second code path or a cross-feature reach-in is rejected. Every review verdict in this
  release must state, with bug-history evidence, whether the change reduced or increased
  the bug surface of the feature it touched. "Tests green" is not a verdict.
- **Measurement rule.** `product-engineer` has no shell. Every number this release asserts
  is produced by a named task step run by an agent with a shell and captured under
  `.dadaia/tmp/<agent>/<YYYYMMDD>/`.
- **Zero-hit greps** exclude `specs/_archive/**`, `specs/bugs/**`, `specs/backlog/**`,
  `specs/releases/v0.4.4/**`, `CHANGELOG.md` and `.dadaia/{reports,handoff,tmp}/**`.
- **Test intent at birth**, per `dadaia-test-stewardship`. **Zero new `tests/e2e/**`**
  without a named `qa-engineer` exception recorded in that segment's QA artifact.

---

### Segment `S1` — the gitflow contract, v2 (entry `gitflow-contract-v2-consolidation`)

Everything else in this release rides this segment: the map (`S2`) maps the gitflow topic
first, the skills consolidation (`S3`) collapses gitflow pointers, and every merge into
`develop` from `rc-1` onward uses the v2 mechanic this segment installs.

#### FR1 — One law section states the git contract, and nothing else does

`DADAIA.md` §3 (git chokepoints), §5 (Branches / Releases / Hotfixes) and §6 (Push green)
collapse into **one gitflow section** carrying the v2 contract of G2–G7: three branch
patterns; `feature/{M.m.p}` cut from `main`; one live feature branch; delete at deploy and
cut the next in the same step; `develop` and `main` PR-only; `rc-N` in the specs, never in
a branch name; the start-of-work protocol by pointer; the CI/CD automation suggestion. The
`alpha-N → rc-N` maturation sentence becomes **`rc-N`** only (I7). Every other `DADAIA.md`
mention of the branch model becomes a cross-reference to that section.

**Acceptance**
- A1.1 Exactly one `DADAIA.md` section states the branch model; every other mention is a
  named cross-reference, proven by grep.
- A1.2 The word `alpha` no longer appears in `DADAIA.md` as a release-maturation stage.
- A1.3 `hotfix/` appears in `DADAIA.md` only as a retired pattern reachable by explicit
  operator request (G2) — no stage, no cadence, no PATCH-mint rule.
- A1.4 The stage placement rows read `feature/{M.m.p}` for backlog definition, research and
  bug registration (D6); no stage names `develop` as a working branch.
- A1.5 The law is edited at `dadaia_workspace/public/data/DADAIA.md` (source only) and
  projected; the projected copies are byte-identical to the source.

#### FR2 — `dd-gitflow-default` is the one operational home of the contract

`dadaia-gitflow` is renamed `dd-gitflow-default` (G11, D3) and rewritten to the v2
contract: the branch table, the stage contract, the **start-of-work protocol** (fetch;
diff `main` vs `develop`; identify the live `feature/{v}`; detect a `feature/{v}` created
before `develop` last moved), the branch-creation rule, the uniqueness and deletion rules
(discipline per G7), explicit anti-slop/anti-stale-branch guidance, and an
"automate this in CI/CD" section for consumers. Shape follows G12.

**Acceptance**
- A2.1 The skill folder is `dd-gitflow-default/`; no `dadaia-gitflow` path survives in the
  tree, the manifest, the registry or any projection.
- A2.2 The skill states the start-of-work protocol, the uniqueness rule, the
  delete-after-deploy rule and the same-step cut of `feature/{v+1}` — each exactly once.
- A2.3 The skill carries the CI/CD suggestion section addressed to a consumer operator.
- A2.4 The skill states which of its rules are **mechanical** and which are **discipline**
  (G7), and the mechanical list matches FR3/FR4 exactly.
- A2.5 `SKILL.md` obeys the size/shape ceiling FR9's enforcer pins (G12); anything longer
  is disclosed to a sibling file in the same folder.

#### FR3 — The chokepoint enforces v2, inverted

`features/chokepoints/service.py`: `_PERMITTED_BRANCH_RES` becomes **three** patterns —
`^main$`, `^develop$`, `^feature/\d+\.\d+\.\d+$` — with **no `v`** and **no `hotfix`** row
(G2). `_PUSHABLE_BRANCH` inverts: a `feature/{M.m.p}` ref is pushable; `develop` and `main`
are **refused** with a message naming the PR path. The **range-scoped denylist scan stays
on the feature push** — under v2 that push is the first publication to `origin` — and the
**security verdict leaves the pre-push hook** (FR4). Every refusal keeps naming the rule,
the permitted value and the corrective action.

**Acceptance**
- A3.1 RED-then-GREEN: a `feature/0.0.0` push is allowed and a `develop` push is refused,
  both by the executed path, with the refusal naming the PR.
- A3.2 No regex anywhere in the package or CI matches `feature/v…`; one pattern source
  survives (grep-proven).
- A3.3 The denylist scan runs on a `feature/*` push range and refuses on a hit; the tag
  carve-out is unchanged.
- A3.4 The pre-push hook no longer reads a security handoff; the removed code is
  **deleted**, not disabled behind a flag.
- A3.5 `dadaia ci push-gate-check --help` and every decision message state the v2 policy;
  the corrected-command hint names the PR path (D5's verb keeps its own `--help` cadence
  contract, re-keyed to the PR head sha).
- A3.6 Net production LOC for this FR is **≤ 0** (the inversion replaces rules, it does not
  add them) — measured, and justified in CLOSURE if it is not.

#### FR4 — The security verdict is a PR gate; CI sees the feature branch

`.github/workflows/ci.yml`: triggers extend to `push: feature/**` and `pull_request:
[develop, main]`. The `pr-source-guard` job's condition extends to guard **both** edges —
`main` accepts a PR only from `develop`, `develop` accepts a PR only from
`feature/{M.m.p}` — in the **same job**, not a second one. A **security-verdict PR gate**
job requires an APPROVED `security-reviewer` handoff whose covered sha equals the **PR head
sha**.

**Acceptance**
- A4.1 A push to `feature/0.4.4` triggers the full CI matrix.
- A4.2 A PR to `develop` from any head other than `feature/{M.m.p}` fails `pr-source-guard`;
  a PR to `main` from any head other than `develop` still fails it; one job, two rules.
- A4.3 The verdict gate fails a PR with no APPROVED handoff covering the PR head sha, and
  passes with one.
- A4.4 **Recorded limit:** a workflow job added on a feature branch does not run on the PR
  that introduces it. `rc-1`'s PR is the first PR this release opens (milestone (a) uses
  the v1 mechanic, D2), and it is the PR that *brings* the job to `develop` — so the
  verdict gate is **advisory on the `rc-1` PR** and required from `rc-2` onward. Making it
  a **required check** is a repository setting applied by the operator/dispatcher;
  `gh api PATCH required_status_checks` **clobbers** the list, so the full list is
  re-supplied.
- A4.5 The v1 push-time verdict path is deleted from the hook, its tests replaced by PR-gate
  tests — no dual path survives.

#### FR5 — Every other surface becomes a pointer

The branch model stops being restated in: eight agent personas (`ai-engineer`,
`project-manager`, `qa-engineer`, `software-engineer`, `code-reviewer`,
`security-reviewer`, `product-engineer`) and `entities/registry.json` mandates; the dd-*
skills (`dd-release-definition`, `dd-release-implement`, `dd-bug-fix`,
`dd-bug-registration`, `dadaia-task-manager`); `scripts/pre-push-ci-gate.sh`'s header
comments; `cli/commands/ci.py`'s docstring. Each becomes **one pointer line**. The
`dd-release-implement` L43 contradiction ("push implementation commits to
`feature/{M.m.p}`") is resolved by the v2 contract, which makes that push correct — the
line is replaced by the pointer regardless.

**Acceptance**
- A5.1 Outside `DADAIA.md`'s gitflow section and `dd-gitflow-default`, no file states a
  branch pattern, a pushability rule or a merge milestone — grep-proven over the tree.
- A5.2 Every one of the 14 scanned surfaces carries a pointer naming both homes.
- A5.3 `dd-bug-fix` no longer instructs a `hotfix/{M.m.p}` cut (G2); Arm B runs on the live
  `feature/{v}` (G3).
- A5.4 Net documentation lines removed across the 14 surfaces is **negative** — measured.

#### FR6 — The local preflight stops lying about CI equivalence *(bug, Arm B)*

Bug `prepush-gate-omits-import-boundary-contracts-ci-runs` (MEDIUM). The preflight calls
itself CI-equivalent and omits `lint-imports`, so a cross-feature import passes locally and
fails in CI. **Decision: parity** — `lint-imports --config setup.cfg` joins the existing
preflight sequence (one command in an existing list, no new code path). Under v2 the
feature push is the PR-opening act; a red CI on a pushed branch is exactly the loop the
standing order forbids.

**Acceptance**
- A6.1 RED: a cross-feature import passes the preflight at HEAD. GREEN: the same import is
  refused by the preflight, by the executed path.
- A6.2 The preflight's advertised check list and CI's gating list are the same set, pinned
  by a test that fails when either side gains a check the other lacks.
- A6.3 A `resolved` event with `--resolution-evidence` is appended and the bug is `Closed`.

---

### Segment `S2` — the rules→skills governance map (entry `rules-skills-governance-map`)

#### FR7 — One JSON map, owned by dadaia-workspace

A new `dadaia_workspace/public/entities/rules-skills-map.json` (next to `registry.json`,
I2) with a versioned schema. **Key = the bold topic of `DADAIA.md`** (G9), e.g.
`§5 **Branches**`, `§6 **Test lifecycle**`; each row is
`{topic, section, skills[], justification}`. One skill per topic; two only when that row
carries a justification. **Every skill has a topic; not every topic has a skill.** Seeded
with the gitflow row first, then the rows the 2026-08-23 scan already identified.

**Acceptance**
- A7.1 The map validates against its own schema, and the schema is versioned.
- A7.2 Every skill on disk appears in exactly one row; a row naming two skills carries a
  non-empty justification.
- A7.3 The gitflow row names `dd-gitflow-default` and the law's gitflow section.
- A7.4 The map is the **only** place a section↔skill relation is declared (D4).

#### FR8 — The map is core law

A new section in `specs/constitution.md` **and** in the scaffold template
`dadaia_workspace/public/scaffold/constitution.md`: every always-on rule is a section of
`DADAIA.md` and is mapped to the skill that operates it; the JSON map is the single
controlled source; the enforcer is a deterministic test; rule = concise statement, skill =
complement, **no overlap** (G9); an orphan skill is fused or retired, and the law gains a
topic only for genuinely always-on behavior (G10).

**Acceptance**
- A8.1 Both constitutions carry the section; the workspace's own edit is made **only with
  explicit operator confirmation** (approval of this SPEC is that confirmation, recorded in
  §8).
- A8.2 `DADAIA.md` §9 points at the map as the authority for which skill operates which
  rule, instead of listing skills ad hoc.
- A8.3 No third statement of the rule exists.

#### FR9 — One deterministic enforcer, gating every deploy

A contract test (in the gating pytest selector, so it runs in the preflight **and** in CI —
"gating every deploy", G9) reads the map, `public/data/DADAIA.md` and the on-disk skills
inventory and fails when: a mapped topic does not exist in the law; a skill on disk maps to
no topic; a topic names a skill that does not exist; two skills share a topic without a
justification; a `SKILL.md` exceeds the declared line ceiling (G12); or two non-universal
skills have an **undeclared activation overlap**. `lint-skill-collisions.py` is **retired**
(D4).

**Acceptance**
- A9.1 The test is green at HEAD the moment it lands (satisfiable-diagnostics law).
- A9.2 Six mutation fixtures — one per failure mode — each turn the test red.
- A9.3 `lint-skill-collisions.py` and its `DECLARED_OVERLAPS` are deleted, with its
  projections and manifest entries.
- A9.4 **Coverage is moved, not dropped:** the retired script's `--self-test` fixtures are
  ported and pass against the new test.
- A9.5 Net production LOC for FR7+FR9 combined is **≤ 0** against the retired script.

---

### Segment `S3` — core skills consolidation (entry `core-skills-consolidation`)

#### FR10 — `dd-release-closure` is folded into `dd-release-implement`

`dd-release-implement` absorbs the CLOSURE template, the memory-update protocol, the
evidence triples, the disposition sweep, the artifact GC sweep and the archive move, and is
re-authored to the G12 pattern: a short ordered `SKILL.md` whose steps each end on a
checkable criterion, with the closure detail disclosed to sibling files in the same folder.
The `dd-release-closure` folder is **deleted**; every pointer to it is repointed.

**Acceptance**
- A10.1 No `dd-release-closure` path survives anywhere (tree, manifest, registry,
  projections, agents, memory) — grep-proven.
- A10.2 Every closure obligation that existed in the retired skill is present in
  `dd-release-implement` or a sibling file it names — proven section by section.
- A10.3 This release's own closure (at the final `rc`) is executed **from the folded skill**.

#### FR11 — One AI-harness skill: `dd-ai-eng-knowhow`

`ai-harness-codex`, `ai-harness-claude-code`, `ai-context-engineering` and
`harness-primitives` are replaced by **one folder** `dd-ai-eng-knowhow/` — a short
`SKILL.md` plus reference siblings and **links** to the official Codex / Claude Code
documentation, never a copy of it. `DADAIA.md` §2's "ai-engineer alone invokes the
`ai-harness-*` and `ai-context-engineering` skills — every other agent uses
`harness-primitives`" is rewritten to name the one skill. The harness-literacy layer that
every agent needs survives as the short top layer of that skill, reachable by every agent;
the depth stays `ai-engineer`'s.

**Acceptance**
- A11.1 The four folders are deleted; one folder replaces them.
- A11.2 No vendor documentation is reproduced — external knowledge is a link.
- A11.3 Every agent that referenced `harness-primitives` points at the one skill, with the
  literacy-vs-depth boundary stated once.
- A11.4 Total `SKILL.md` bytes across the AI surface fall by **≥ 60 %** — measured before
  and after.

#### FR12 — The four remaining renames, and `dd-grill-me` ratified

`dadaia-grill-me`→`dd-grill-me`, `dadaia-cli`→`dd-cli-library` (**verified against the
current CLI** — a verb the skill names that no longer exists is a defect fixed here),
`project-orchestration`→`dd-manager-orchestration`,
`dadaia-workspace-doctor`→`dd-workspace-doctor`. The `ai-engineer` uplift of `dd-grill-me`
already present in the worktree (design tree / frontier / rounds, with its disclosed
sibling files) is **ratified and landed** as the first worked example of G12.

**Acceptance**
- A12.1 Each rename lands with its map row (FR7), its manifest entry, its registry entry
  and its projections, in **one** commit per skill — no window in which the enforcer is red.
- A12.2 No old skill name survives in any file — grep-proven.
- A12.3 `dd-cli-library` names only verbs the current CLI exposes, proven by a check against
  the live command tree.
- A12.4 `dd-grill-me` carries its sibling reference files and its `SKILL.md` is within the
  ceiling.

#### FR13 — Projection truth for skills that are folders

Skills now carry sibling files. `dadaia public stage` / `install --target all` /
`doctor` must project every sibling to all four harness targets, the manifest must track
them, and the byte-golden inventories must be regenerated for a **reviewed, deliberate**
change.

**Acceptance**
- A13.1 `dadaia public doctor` reports `[ok] public-privacy`, `[ok] entities-derivation` and
  `[ok] model-resolution`, with zero `[drift]`/`[missing]`.
- A13.2 Every sibling file of every consolidated skill exists in `.claude/`, `.agents/`,
  `.codex/` and `.kimi-code/`, byte-identical to the source.
- A13.3 The install goldens are regenerated with `UPDATE_INSTALL_GOLDENS=1` and **every**
  regenerated line is explained in the commit message as a consequence of a named FR;
  a multiset diff proves no unexplained line moved.
- A13.4 The inventory-coupled tests outside the golden pair
  (`tests/e2e/features/test_public_pipeline.py`, `tests/integration/test_public_assets.py`,
  `tests/integration/scripts/test_check_skill_orphans.py`) are green without weakening an
  assertion.
- A13.5 **Architecture-review item (§6 AR-1)** — `software-architect` rules on
  byte-golden-over-inventory as a mechanism.

#### FR14 — The study: what happens to the remaining nine skills

`architect-core-workflow`, `dadaia-task-manager`, `dadaia-handoff-emitter`,
`dadaia-step0-memory-bootstrap`, `dadaia-test-stewardship`, `dadaia-workspace-spec-reviewer`,
`dadaia-workspace-spec-navigator`, `dadaia-workspace-manager`, `dev-server-registry` are
**studied, not changed**: for each, a proposal of **Update / Fuse / Retire / Merge** with
the evidence (staleness, overlap with another skill, its map topic or the absence of one,
size against the G12 ceiling). Emitted as a handoff for the operator. **Execution is out of
scope for v0.4.4** (§4).

**Acceptance**
- A14.1 Nine proposals, one per skill, each naming exactly one of the four verbs with
  evidence and a blast radius.
- A14.2 Each proposal names the skill's map topic (FR7) or states that it is an orphan —
  G10's default disposition applies to every orphan named.
- A14.3 No skill in the study is modified in this release beyond its rename-free map row.
- A14.4 The handoff is emitted and validates.

---

### Segment `S4` — spec-context associated repos (entry `spec-context-associated-repos`)

#### FR15 — The model, and its migration

`SpecContextProject` gains an ordered `associated_repos` collection (slug + url each) next
to the single main `repo_slug`/`repo_url`; **main stays unique** and is the only specs/bind
target (G13, I4). The registry schema bumps **v2 → v3** with a backup-first, idempotent
migration — the schema-drop law: a schema change ships its migration.

**Acceptance**
- A15.1 A v2 registry migrates to v3 with a backup, and re-running the migration is a no-op.
- A15.2 A v3 registry with zero associated repos is behaviourally identical to its v2 form.
- A15.3 The model change adds **no second repo-resolution path**: every consumer resolves
  "the context's repos" through one accessor.

#### FR16 — ALIVE/DEAD covers every repo

`context alive` clones/keeps the main repo **and** every associated repo under `repos/`,
idempotently, reporting each. `context dead` git-syncs and removes **all** of them,
refusing exactly as today when any is dirty or unpushed. Associated repos are cloned
**clean, with no scaffold**, and their own `specs/` (if any) are ignored by the context.

**Acceptance**
- A16.1 `alive` on a context with N associated repos leaves N+1 repos on disk; re-running
  changes nothing.
- A16.2 `dead` refuses when **any** repo is dirty or unpushed, naming which one.
- A16.3 An associated repo receives no scaffold and no `specs/` bind; its own `specs/` is
  never read by context resolution, doctor or memory injection.
- A16.4 A context-resolution walk from inside an associated repo resolves the **context**,
  not a second context.

#### FR17 — The verbs

`context repo add <ctx> <slug> [--url]`, `context repo remove <ctx> <slug>`,
`context repo list <ctx>`, and a repeatable `--associated <slug>[=<url>]` on
`context create`.

**Acceptance**
- A17.1 Each verb is idempotent and fails loudly on an unknown context or slug.
- A17.2 `remove` never deletes an on-disk repo silently — it states what it leaves behind.
- A17.3 Adding the main repo's own slug as associated is refused.

#### FR18 — The surfaces agree *(covers the superseded bug)*

`context show` renders main + associated (slug, url, on-disk, live branch) in table and
`--json`; `context list` shows an associated count (list in `--json`). **`list` and `show`
never disagree on `current_branch`** — the acceptance of bug
`context-list-current-branch-stale-for-alive-repo`, which this entry supersedes (§7).
Export/import carry associated repos (url + branch); the panel card lists main + associated;
`ci` foreign-slug derivation covers the full set.

**Acceptance**
- A18.1 For an ALIVE repo whose checkout moved, `list` and `show` report the **same**
  `current_branch`; where a stored snapshot is still meaningful it is exposed under a
  distinct name, never as `current_branch`.
- A18.2 The bug's own repro (alive → checkout another branch → `list` vs `show`) is a RED
  test that goes GREEN, and the bug is `Closed` with `superseded_by: spec-context-associated-repos`.
- A18.3 One branch-resolution implementation serves both verbs — the divergence is removed
  structurally, not by adding a refresh call to `list`.
- A18.4 Export → import round-trips a context with associated repos.
- A18.5 The panel renders main + associated for a context with and without associated repos.

#### FR19 — One place of control

Specs, bind, memory, releases and backlog resolve **only** from the main repo (G13).

**Acceptance**
- A19.1 A bind to a context with associated repos injects the **main** repo's memory only.
- A19.2 `specs doctor`, `backlog doctor` and the SDD gate see exactly one `specs/` tree per
  context, proven with an associated repo that carries its own `specs/`.

---

### Segment `S5` — the bug sweep and branch hygiene

Eight bugs (the ninth, the HIGH marker bug, lands first in `S1` per D7), each Arm B on
`feature/0.4.4` (reproduce → RED → root-cause fix → GREEN → `resolved` → commit), each
carrying the standing order's requirement that the diff does not grow the feature. Full
list and dispositions: §7.

#### FR20 — `origin` carries only the permitted patterns

Every remote slop branch is tagged `archive/<name>` and deleted (G8): `chore/*` ×7,
`feature/pi-fourth-harness-v1`, `feature/v0.1.10`, and the six stale
`feature/0.1.5 … 0.4.2`. Local `hotfix/0.4.3` is deleted too (its work is already merged
and published in `CHANGELOG [0.4.3]`).

**Acceptance**
- A20.1 Every deleted branch is reachable by its `archive/<name>` tag, proven per branch
  before deletion.
- A20.2 After the sweep `origin` carries `main`, `develop`, `feature/0.4.4` and archive tags
  — nothing else.
- A20.3 No local branch outside the three permitted patterns survives.
- A20.4 The tag push uses the tag carve-out; no `--no-verify`.

---

### The `rc` lane — `rc-1 … rc-N` (D8)

Not a scope block: the lane is what happens to the **whole** scope once `S1 … S5` are
done.

- **`rc-1`** — the scope is gate-green, QA has closed the release and the trio has run;
  `feature/0.4.4` is merged into `develop` by PR (milestone (b)). That merged `develop`
  **is** `rc-1`.
- **`rc-2 … rc-N`** — each round is an adjustment, fix or improvement **on the current
  scope**, discovered by testing the merged `develop` (operator, QA, anyone). It is worked
  on `feature/0.4.4`, closed by QA, and merged again — one `rc` per merge. **No new backlog
  ever enters an `rc`**: a demand that is not this scope goes to the backlog for a later
  release, and a defect in this scope's own delta is fixed here.
- **The final `rc`** carries the memory window, `CLOSURE.md` and the archive move, and then
  ships `develop → main`. If no adjustment is found, the final `rc` **is** `rc-1`.

#### FR21 — The invariants this release must not break

- A21.1 `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor`,
  `dadaia backlog doctor` and `dadaia public doctor` green; `specs doctor` **0 errors**.
- A21.2 Layer rules hold: `features/**` imports neither `cli`, `infrastructure` nor `hooks`;
  `core/**` stays stdlib-pure; `lint-imports` green with **no new** accepted edge — and now
  it is green **locally too** (FR6).
- A21.3 No harness projection changes except where an FR requires it, proven by byte-diff.
- A21.4 **Production LOC net for the release is negative** — this release organizes; only
  `S4` legitimately adds. Measured in CLOSURE's `## Size accounting`; a positive net
  requires a written justification per contributing FR.
- A21.5 Residual budget: **zero actionable intake candidates**; `## ACTIVE` empty; every
  picked bug terminal.
- A21.6 Complexity ceilings (`C90`, `PLR1702`) unchanged or **lowered** — never raised.
- A21.7 **Every `rc` holds A21.1–A21.6**, and every `rc-N ≥ 2` traces to a defect or
  adjustment **on this scope**, named with where it was found on `develop`. An `rc` that
  carries scope not declared in §3 is a law violation, not a round.

---

## 4. Out of scope (non-goals)

1. **Hotfix branches** (G2). The pattern is retired for now; Arm B runs on the live
   `feature/{v}`. Reinstating `hotfix/{v+1}` requires an explicit operator request.
2. **Creating any skill beyond the consolidation.** `dd-ai-eng-knowhow` is a fusion of four;
   nothing else is born (G11).
3. **Executing the nine remaining skills' dispositions** (FR14). The study produces
   proposals; the operator decides; execution belongs to a later release.
4. **A second gitflow skill.** One law section, one skill — a second would have to be
   justified through the map (FR7) first.
5. **Rewriting Codex / Claude Code documentation** into `dd-ai-eng-knowhow` (G11) — links
   only.
6. **Re-litigating the version number** (I5, §7 lineage). v0.4.4 is the operator's ruling.
7. **The archived `specs/_archive/releases/v0.4.3/`** — untouched, frozen, quoted only.
8. **Any FR not listed in §3.** Nothing discovered mid-release is added without an operator
   ruling at the moment of discovery. The standing exception is a **bug**, fixed on the spot
   as Arm B (`DADAIA.md` §1) — never backlog demand.
9. **A registry schema beyond v3** and any multi-main-repo model (G13: one main, always).

---

## 5. Memory files affected at closure

Written in the CLOSURE phase only, one authoring pass per atom.

| File | Change | When |
|---|---|---|
| **`specs/memory/product/sdd/sdd-gate-v3.md`** | **mandatory rewrite** — "Git Chokepoints" restated to v2: three patterns, no `v`, `feature/{M.m.p}` pushable, `develop`/`main` PR-only, denylist scan on the feature push, the security verdict relocated to the PR gate, `gc-push-verdicts` re-keyed to the PR head sha (D5); the branch model itself becomes a **pointer** to the law's gitflow section | CLOSURE |
| **`specs/memory/product/sdd/sdd-bug-backlog-governance.md`** | **mandatory rewrite** — "Branches And Stage Placement" collapses to a pointer; stage rows move to `feature/{M.m.p}` (D6); "Merge Cadence" re-expressed as PR-only `develop`, `rc-N` ladder, no `alpha`; the hotfix row retired | CLOSURE |
| `specs/memory/quality-assurance.md` | CI triggers (`feature/**` + PRs to `develop`/`main`), the two-edge `pr-source-guard`, the verdict PR gate, preflight/CI check parity (FR6) | CLOSURE |
| `specs/memory/architecture.md` | the agent-surface branch/push rows collapse to one pointer line each; the rules→skills map named as the authority | CLOSURE |
| `specs/memory/product/agents/agentic-entities.md` | the consolidated skill inventory; the derivation law gains the topic→skill invariant; the retired collision lint | CLOSURE |
| `specs/memory/product/agents/agent-orchestration.md` | the `DADAIA.md` §2 AI-skill line rewritten to `dd-ai-eng-knowhow`; the §9 map pointer | CLOSURE |
| `specs/memory/product/distribution/public-asset-distribution.md` | skills are folders with sibling files; the consolidated set projected to four targets; retired folders no longer projected | CLOSURE |
| `specs/memory/product/platform/context-management.md` | main + associated repo model, ALIVE/DEAD over the full set, the new verbs | CLOSURE |
| `specs/memory/product/philosophy/spec-context-project.md` | one main repo is the sole source of specs/bind/memory (G13) | CLOSURE |
| `specs/memory/product/platform/repos-catalog.md` | the repos on disk mirror the context's full repo set | CLOSURE |
| `specs/memory/product/panel/panel.md` | the context card lists main + associated | CLOSURE |
| `specs/memory/product/sdd/specs-doctor.md` | only if a doctor rule changed — otherwise "no change", with the reason | CLOSURE |
| `specs/memory/product/distribution/pypi-distribution.md` | the 0.4.4 published lineage (§7) | CLOSURE |
| `specs/memory/product/index.md` + `catalog.json` | regenerated; `index.md` touched only if catalog order or membership changed | CLOSURE |
| `specs/memory/tech-stack.md` | only if a dependency changed — otherwise "no change", with the reason | CLOSURE |

### Closure obligations (not implementation FRs)

- **Disposition sweep.** Four `LEDGER` lines (`DELIVERED · v0.4.4`); ten bugs `Closed`; one
  bug `Closed` + `superseded_by: spec-context-associated-repos`.
- **`## Size accounting`** with measured values; A21.4's negative net or its justification.
- **Test dispositions**: every demotion, quarantine expiry and SCAFFOLD expiry.
- **Record-only vs intake** sections, per the calibrated routing.
- **Artifact GC sweep** after the evidence pointers are final.
- **Standing-order verdict record.** CLOSURE states, per segment, whether the bug surface of
  each touched feature went down — with bug-history evidence, not test results.
- **`rc` ledger.** CLOSURE lists every `rc` burned, what was found on `develop` that
  motivated each `rc-N ≥ 2`, who found it, and its fix — the evidence that no `rc` carried
  new scope (A21.7).
- **AR-1 / AR-2 rulings** (§6) recorded with their disposition.
- **The v0.4.3 git-identity question (R9)** is restated for the operator, not decided.

---

## 6. Dependencies and risks

| # | Item | Status / mitigation |
|---|---|---|
| D-1 | `product-engineer` has no shell | every git, CLI and measurement step is an explicit TASKS entry owned by the dispatcher, `software-engineer`, `ai-engineer` or `qa-engineer` |
| D-2 | **Bootstrap:** v2's chokepoint does not exist until `S1` | E-1/D2 — milestone (a) uses the v1 mechanic once; every merge from `rc-1` onward uses v2 |
| D-3 | **The installed venv is not editable** — `S1`'s chokepoint code is not live until the workspace venv is reinstalled | an explicit task step reinstalls into `.dadaia/.venv` and re-verifies with `dadaia --version` + a refusal probe before `S2` opens |
| D-4 | **A CI job added on a branch does not run on its own PR** (A4.4) | the verdict gate is advisory on the `rc-1` PR, required from `rc-2`; the required-checks list is re-supplied whole (PATCH clobbers) |
| D-5 | **`S1` before everything** — `S2` maps the gitflow topic, `S3` collapses gitflow pointers, and every merge into `develop` uses the v2 mechanic | segment order + TASKS preconditions |
| D-6 | **`S2` before `S3`** — every rename in `S3` must land with its map row, and the enforcer must exist first | segment order; A12.1 forbids a red-enforcer window |
| D-7 | **FR13's golden regen is deliberate** and must not mask an unintended change | multiset diff + per-line explanation (A13.3) + AR-1 |
| D-8 | **FR8 writes `specs/constitution.md`** — operator-confirmation-only | approval of this SPEC is the confirmation, recorded in §8 |
| D-9 | Only one sanctioned parallel pair exists per segment, declared in TASKS; everywhere else **one `[-]` at a time** | TASKS |
| **AR-1** | **Architecture review — byte goldens over a file inventory are fragile by construction.** Two goldens (`install_target_resolution_v0158.json`, `doctor_all_four_v0158.json`) encode the *entire projected file inventory*, so every legitimate skill rename or sibling file forces a regen, and a regen is exactly where an unintended change hides. Three further tests couple to the same inventory. | `software-architect` rules in `S3`: keep-with-discipline, replace with a structural assertion, or split the inventory out of the byte golden. The ruling is recorded in CLOSURE; work beyond the regen is intake, not scope creep |
| **AR-2** | **Architecture review — the enforcement surface must shrink, not move.** FR3+FR4 relocate the verdict from the hook to CI and FR9 retires a lint. The risk is ending with *both* a hook remnant and a CI job. | `software-architect` states, at `S1`'s close, the before/after count of enforcement points and refuses any dual path (A3.4, A4.5, D4) |
| R-1 | **`S1` changes the mechanism this release uses to integrate itself.** A defect there blocks every later segment and the whole `rc` lane | `S1` lands first, is proven by an executed-path refusal probe on both edges, and the venv reinstall (D-3) is part of its close |
| R-2 | **`S4` is the only additive segment** (schema v3, new verbs, panel/export) and carries the release's positive LOC | one accessor (A15.3), migration backup-first, each verb independently revertible; A21.4 accounts for it explicitly |
| R-8 | **The `rc` lane can be abused as a second pick** — an operator or agent testing `develop` may propose work that is not this scope | A21.7 + the CLOSURE `rc` ledger: every `rc-N ≥ 2` names the defect on this scope it answers; anything else is backlog demand for a later release (§4.8) |
| R-3 | **The HIGH bug may not reproduce here** — it was re-filed from another repo's ledger, and no post-write markdown formatter exists in this package's hooks | D7: reproduce first, in `S1`. A negative result is closed **with evidence** naming every product-owned writer of `specs/releases/**/*.md`, plus a contract test pinning that none mutates markers or `**Status:**` — never a silent drop |
| R-4 | **Renames are wide** — every rename touches manifest, registry, projections, goldens, agents, memory and the map | one commit per skill (A12.1); the enforcer is never left red between commits |
| R-5 | **The consolidated AI skill can lose agent-wide literacy** if depth and literacy are fused carelessly | A11.3 pins the boundary: a short top layer every agent may read, the depth reserved to `ai-engineer` |
| R-6 | **Slop-branch deletion is irreversible** if a tag is missed | A20.1 proves reachability **per branch before** deleting it |
| R-7 | **Publishing skips a number** (§7 lineage) | stated once in the SPEC and in the CHANGELOG; the operator's ruling is not re-derived |

---

## 7. Traceability and provenance

| Record | Provenance | Disposition in this release |
|---|---|---|
| `gitflow-contract-v2-consolidation` | operator request 2026-08-23 + scan `.dadaia/tmp/claude/20260823/gitflow-inventory.md` | **picked** · FR1–FR5 · `DELIVERED · v0.4.4` |
| `rules-skills-governance-map` | operator request 2026-08-23 | **picked** · FR7–FR9 · `DELIVERED · v0.4.4` |
| `core-skills-consolidation` | operator request 2026-08-23; pattern source the skills reference clone (`mattpocock/skills`) | **picked** · FR10–FR14 · `DELIVERED · v0.4.4` |
| `spec-context-associated-repos` | operator request 2026-08-23 | **picked** · FR15–FR19 · `DELIVERED · v0.4.4` |
| bug `sdd-artifact-linter-mutates-task-markers` (HIGH) | re-filed 2026-08-23 (misfiled from another ledger, audit SDD-27) | **solved in release, Arm B on `feature/0.4.4`** · `S1`, first (D7) · R-3 governs a negative reproduction |
| bug `prepush-gate-omits-import-boundary-contracts-ci-runs` (MEDIUM) | software-engineer, 2026-08-18 | **solved in release, Arm B** · `S1` · FR6 · **not superseded**: the picked entry's intents cover branch policy, not preflight parity |
| bug `backlog-doctor-silent-on-duplicate-top-level-sections` (MEDIUM) | project-manager, 2026-08-23 | **solved in release, Arm B** · `S5` |
| bug `context-list-current-branch-stale-for-alive-repo` (LOW) | operator session, 2026-08-23 | **SUPERSEDED by `spec-context-associated-repos`** — that entry's `context list` intent names this bug and reworks the same surface; its acceptance is carried by **FR18/A18.1–A18.3**, which is the structural fix rather than a refresh call. `superseded` event appended at definition; `Closed` at the sweep |
| bug `atomic-writer-drift-guard-is-brittle-and-covers-only-two-of-eight-writers` (LOW) | security-reviewer, 2026-08-19 | **solved in release, Arm B** · `S5` |
| bug `backlog-doctor-rejects-deferred-status-documented-by-skill` (LOW) | project-manager, 2026-08-23 | **solved in release, Arm B** · `S5` |
| bug `crlf-fixture-makes-a-windows-assertion-pass-for-the-wrong-reason` (LOW) | security-reviewer, 2026-08-19 | **solved in release, Arm B** · `S5` |
| bug `migration-normalises-crlf-atoms-to-lf-contradicting-its-byte-preserve-wording` (LOW) | security-reviewer, 2026-08-19 | **solved in release, Arm B** · `S5` |
| bug `no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` (LOW) | security-reviewer, 2026-08-19 | **solved in release, Arm B** · `S5` |
| bug `read-only-atom-honouring-is-advisory-and-root-bypasses-it` (LOW) | security-reviewer, 2026-08-19 | **solved in release, Arm B** · `S5` |
| bug `symlinked-specs-root-is-followed-by-migration-and-repair` (LOW) | security-reviewer, 2026-08-19 | **solved in release, Arm B** · `S5` |
| Audits | `specs/audits/_archive/` | **none outstanding** |

**Pick tally.** 4 backlog entries (all four declared in `**Consumes:**`, all fully
consumed) + 11 bugs = **10 fixed in-release** + **1 superseded**. No bug is dropped.

**Purge-on-pick (`dd-backlog-definition` §2).** All four `## ACTIVE` subsections leave
`specs/backlog/BACKLOG.md` in the **same commit** that creates this SPEC, executed by
`project-manager`; this section is the provenance record that removal requires. Their
`LEDGER` lines are written at the closure disposition sweep.

**Version lineage — stated once.** `pyproject.toml` reads `0.4.3` at the branch cut
(minted by the `hotfix/0.4.3` Arm B merge, `CHANGELOG [0.4.3]`), and PyPI's latest
published version is `0.4.2` (I5). The published+1 rule would mint `0.4.3`, which collides
with that local mint **and** with the archived release directory `specs/_archive/releases/
v0.4.3/`. **Operator ruling (G1): this release is `v0.4.4`.** So: `pyproject.toml`
`0.4.3 → 0.4.4`; PyPI `0.4.2 → 0.4.4`; **`0.4.3` is retired unpublished** and keeps its
CHANGELOG section as a local-only mint; the archived `v0.4.3` release directory is not
touched. The release id **is** the package version — one axis, unchanged.

**Recorded exception E-1 (G1, D2).** `feature/0.4.4` was cut from `develop`, not `main`,
because `main` lacks the `develop` delta and the operator holds the 0.4.3 ship. Milestone
(a) of this release therefore runs the v1 mechanic once (D2). **From the `rc-1` merge
onward, and for every release after this one, v2 governs**: `feature/{v}` is cut from `main`, `develop`
advances only by PR, and the exception is not repeatable.

---

## 8. Approval

Approving this SPEC ratifies, as written: **G1–G13** (the grill's operator decisions),
**D1–D8** (the authoring decisions — **D8 defines what an `rc` is**), the **E-1 recorded
exception** and its expiry once `S1` is live,
the **version lineage** of §7, the **supersession** of
`context-list-current-branch-stale-for-alive-repo`, and — explicitly, per D-8 — the
**edit to `specs/constitution.md`** that FR8 requires.

**Status:** Draft — awaiting the operator. SPEC, PLAN and TASKS must all carry
`**Status:** Aprovado` before milestone (a) fires.
