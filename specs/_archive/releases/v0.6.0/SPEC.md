# SPEC — Release v0.6.0 — Gitflow standardization

**Status:** Aprovado
**Release ID:** v0.6.0
**Owner:** product-engineer
**Opened:** 2026-08-12
**Branch:** `feature/v0.6.0` (cut from `develop`)
**Consumes:** `specs/backlog/gitflow-standardization.md` (single picked entry, in full)
**Grill:** `specs/releases/v0.6.0/GRILL.md` — operator Q&A of 2026-08-12, binding
**Approval basis:** operator ruling of 2026-08-12 + the grill record above. Approved at
authoring; the definition trio is reviewed at milestone (a) per D3 before `develop` is
pushed.

> **This SPEC supersedes the untracked 2026-08-11 v0.6.0 Draft** ("Test runtime efficiency
> + artifact hygiene"). That draft's entire scope was **consumed the same day by the bug
> flow** — bugs `test-suite-real-venv-and-ci-longpole` and
> `panel-e2e-artifacts-no-consumer`, per operator ruling: the tool was violating contracts
> it already promises (a suite building real venvs; artifacts written with no consumer),
> which is Arm B, fixed on the spot, never release material. The v0.6.0 slot was therefore
> free and is reassigned here. The stale `SPEC.md`/`PLAN.md`/`TASKS.md` were never tracked
> and are replaced wholesale; the two backlog entries they consumed
> (`test-runtime-efficiency`, `test-artifact-hygiene`) are dispositioned on the bug track,
> **not** by this release.

---

## 1. Problem and context

The workspace has a rigorous, mechanically-enforced law for *what may be written*
(`DADAIA.md` §3: path class × presence × phase × mode, one `pre_gate` entrypoint) and
essentially no law at all for *where the work is committed and how it reaches the remote*.

The entire branch model today is **one sentence**, stated twice:

> `public/data/DADAIA.md:180` — "…implemented on a single `feature/{version}` branch."

From that single sentence the following is true of the tree as it stands:

| # | Observed state | Evidence |
|---|---|---|
| O1 | No `develop` branch existed at all until the 2026-08-12 bootstrap; releases pushed **`feature/vX.Y.Z` straight to the remote** | v0.5.0 `CLOSURE.md` ship record; `ci.yml:5-9` push triggers `feature/**` and `hotfix/v*` |
| O2 | The push gate keys the security verdict on a **bare per-ref sha match**; `PushRef.local_ref` is parsed and never read | `features/chokepoints/service.py:69`, `:229-259` |
| O3 | `security-reviewer` may declare a **`full`** scan target to satisfy the push gate | `public/agents/security-reviewer.md`, scan-target section |
| O4 | Two contradictory hotfix laws coexist: `DADAIA.md` §1 Arm B (on the spot, never release material) vs `product-engineer`'s hotfix **release** lifecycle (PATCH ≥ 1, dir + SPEC from `release_hotfix.md.j2` + CLOSURE) | `public/agents/product-engineer.md` "Hotfix release lifecycle" |
| O5 | Nothing prevents a commit or a push to `main` | no chokepoint reads the ref name; no GitHub required check on PR head |
| O6 | 4 files cite a **deleted** `release-governance` rule as their authority | `dadaia-task-manager/SKILL.md:54`; `dadaia-release-closure/SKILL.md:121`; `features/specs/doctor_closure_audit.py:286`; `features/backlog/doctor.py:56` |
| O7 | 5 agents cite `constitution §11`/`§13`; the scaffold constitution has 7 unnumbered `##` sections and no §11 or §13 | `public/scaffold/constitution.md`; `software-engineer.md:268`, `project-manager.md:100`, `qa-engineer.md:69`, `security-reviewer.md:58/113/240`, `code-reviewer.md:57/113/222` |
| O8 | The scaffold release-dir regex `^[a-z][a-z0-9-]+$` **rejects `v0.6.0`** — it contradicts the `^v\d+\.\d+\.\d+$` canon it documents | `public/scaffold/releases/README.md:20` |
| O9 | `ai-engineer` states `pre-push-ci-gate.sh` is the only shell asset in `public/scripts/`; there are **5** files, **3** of them shell | `ai-engineer.md:102`, `:349` vs `public/scripts/` |

O1–O5 are the law gap. O6–O9 are citations of that same governance surface that have gone
stale — they are folded in because they live on the exact lines this release rewrites, and
touching those lines twice would be the waste.

**The bootstrap is already done** (GRILL §0): `develop` was cut from local `main` at
`acf1beef`, pushed after a diff-based security APPROVE, CI green, branch protection active
(no force push, no deletion, `enforce_admins`). This release makes the written law, the
skills, the agents and the chokepoints describe and enforce what the operator is already
doing.

---

## 2. Objective

Give the workspace **one** git contract: four branch patterns, one pushable branch, an
explicit per-stage mapping of branch → commit cadence → merge target → push trigger, a
single skill that is its only home, and **three mechanical enforcement points** so the
contract cannot be violated by discipline lapse. Retire the contradictory hotfix release
ceremony in favour of the bug doctrine plus a PATCH mint at merge. Fix, in the same pass,
every stale citation on the governance surface being rewritten.

---

## 3. Scope

### FR1 — `DADAIA.md` §5/§6 rewritten around the four-branch law

Rewrite `dadaia_workspace/public/data/DADAIA.md` §5 (Specs, tasks and memory) and §6
(Quality) so the git contract is stated **once, at law level**, and everything else defers
to FR2's skill. The law must state, and must not state twice:

1. **Four branch patterns, no fifth** — `main`, `develop`, `feature/{M.m.p}`,
   `hotfix/{M.m.p}`. `develop` is the **only pushable** branch; `feature/*` and `hotfix/*`
   are **local-only**; commit or push directly to `main` is **forbidden**; `main` advances
   **only via PR from `develop`** (GitHub-enforced).
2. **Stage placement** — backlog-definition, research and bug **registration** happen on
   `develop` with **a commit after every registration**; release-definition **and**
   release-implementation happen on `feature/{M.m.p}` cut from `develop`.
3. **Two-milestone merge cadence** — the feature branch merges into local `develop` at
   (a) definition-trio `Aprovado` and (b) ship; **each merge is followed by a diff-based
   security review of `origin/develop..develop` and a push of `develop`**.
4. **Finalization order** — **memory update → CLOSURE → archive**. A group of completed
   tasks is a commit; a release defined + reviewed is a mandatory commit + push.
5. **Hotfix PATCH-mint law** — bug fixes on `hotfix/{M.m.p}` at the **next PATCH**;
   at merge to `develop`, bump `pyproject.toml` and add a `CHANGELOG.md` entry;
   **no release ceremony** (no SPEC/PLAN/TASKS, no `specs/releases/<id>/`). The Arm B
   doctrine in §1 is unchanged and remains authoritative for the fix itself.
6. **Diff-based security gate** — the push-gate review is the `develop` delta only; a full
   scan exists **only** in the audit lane.

**Acceptance**

- A1.1 §5 and §6 state all six items above; `grep -c` for each of the four branch patterns
  in `public/data/DADAIA.md` returns **≥ 1** and the pattern set in the file is **exactly**
  those four (no `release/*`, no `bugfix/*`, no bare `feature/{version}` leftover).
- A1.2 The word-for-word git contract appears in **exactly one** place in
  `public/data/DADAIA.md`; no section restates another's rule (the "no fact stated twice"
  property the file already claims). Verified by a reviewer diff read, not by grep alone.
- A1.3 The four projections (`DADAIA.md` at the workspace root, `.claude/rules/`,
  `.codex/`, `.kimi-code/`) are **byte-identical** to source and mode `0444` after
  re-projection; `dadaia public doctor` reports `[ok] public-privacy` and **zero drift**.
- A1.4 Always-on token count of `DADAIA.md` does not grow by more than **+400 tokens** over
  its pre-release measurement (the file is the always-on prefix; the N-1 deviation at
  v0.3.0 already records it at ~3.5k against a ≤3k aspiration — this release must not make
  that worse than marginally). Measured before and after, both numbers in CLOSURE.

### FR2 — New universal skill `dadaia-gitflow`: the single home of the git contract

Create `dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md` as a **universal** skill
(read natively by every entry harness; no per-harness derivation). It is the **only** place
the git contract is explained in operational detail, and it is invoked whenever git is
used.

Mandatory content:

- The four-branch table (pattern, lives-where, pushable yes/no, cut-from, merges-into).
- A **stage-by-stage table** with one row per lifecycle stage — **backlog-definition**,
  **bug-register**, **bug-fix/hotfix**, **release-definition**, **release-implementation**,
  **ship**, **closure/archive** — and one column each for: **branch**, **commit cadence**,
  **merge target**, **push trigger**.
- The two merge milestones and the mandatory post-merge sequence (diff security review →
  push `develop`).
- The hotfix PATCH-mint rule (pyproject bump + CHANGELOG at merge; no release ceremony).
- What is mechanically enforced vs what is discipline, naming the three FR4/FR5
  mechanisms — so a reader knows which violations will be refused and which will merely be
  caught in review.

**Acceptance**

- A2.1 The skill exists at the canonical path, carries valid frontmatter, and is projected
  to `.claude/skills/dadaia-gitflow/`, `.agents/skills/dadaia-gitflow/`, `.codex/`, and
  `.kimi-code/` by `dadaia public install --target all`; `dadaia public doctor` green.
- A2.2 The stage table has **exactly seven** stage rows and **four** contract columns; no
  stage in the lifecycle lacks a row (checked against `DADAIA.md` §1's two arms).
- A2.3 **Reference, never restate** (`ai-context-engineering` invariant I4): after FR3,
  **no other file** under `dadaia_workspace/public/` explains the branch model
  operationally — every other surface links to `dadaia-gitflow`. Verified by grepping the
  four branch-pattern literals across `public/`: every remaining hit is either inside
  `dadaia-gitflow/SKILL.md`, inside `DADAIA.md` §5/§6 (the law-level statement), or a
  reference *to* the skill.
- A2.4 The skill is ≤ 150 lines. It is a contract table, not an essay.

### FR3 — Tier-2 dedup: every restatement defers to `dadaia-gitflow`

Update every tier-2 surface that currently restates or contradicts the git contract:

| Surface | Change |
|---|---|
| `public/skills/project-orchestration/SKILL.md` | cadence table + `feature/{version}` mention → the four-branch model, referencing the skill |
| `public/skills/dadaia-task-manager/SKILL.md` | commit cadence (task-group = commit) + branch placement by reference; drop the restatement |
| `public/skills/dadaia-release-closure/SKILL.md` | finalization order stated as **memory → CLOSURE → archive**; ship/merge milestone by reference |
| `public/skills/dadaia-release-definition/SKILL.md` | definition happens on `feature/{M.m.p}`; milestone (a) commit+push obligation by reference |
| `public/agents/product-engineer.md` | **hotfix section rewritten** — the PATCH≥1-with-SPEC release ceremony is **deleted** and replaced by: bugs are Arm B, hotfix mints the next PATCH at merge, PE authors **no** hotfix SPEC/PLAN/TASKS and creates **no** release directory for a hotfix |
| `public/agents/security-reviewer.md` | push-gate `scan_target` is **diff-only**; `full` survives **only** in the audit-lane dispatch |
| `public/agents/code-reviewer.md` | PR base corrected: `develop` → `main` (was feature → main) |
| `public/agents/project-manager.md`, `software-engineer.md`, `qa-engineer.md`, `ai-engineer.md` | forbidden-action lists updated to the new push model (never push a non-`develop` ref; never commit to `main`) |

**Acceptance**

- A3.1 All ten surfaces updated; each contains a reference to `dadaia-gitflow` and **zero**
  operational restatement of the branch model (A2.3's grep is the mechanical check).
- A3.2 `product-engineer.md` contains **no** occurrence of `release_hotfix`,
  `closure_hotfix`, or `specs hotfix open`, and no "Hotfix release lifecycle" section
  prescribing a SPEC. The revocation is explicit in the file, not implied by omission.
- A3.3 `security-reviewer.md` push-gate section admits exactly one scan target
  (`diff`/`origin/develop..develop`); the audit-lane section is the only place `full`
  appears.
- A3.4 `code-reviewer.md` states the PR base pair as `develop` → `main` with no
  `feature/*` → `main` path remaining.
- A3.5 No agent's frontmatter allowlist widens as a side effect of these edits (diff-checked
  by `ai-engineer`).

### FR4 — Mechanical chokepoint enforcement (TDD)

Implement in `dadaia_workspace/features/chokepoints/service.py` (+ its wiring in
`dadaia_workspace/cli/commands/ci.py`, `push_gate_check`):

1. **Develop-only push refusal** — any pushed ref other than `refs/heads/develop` is
   **refused** with an actionable message naming the permitted ref and the reason. Tag
   pushes keep their existing carve-out (`PushRef.is_tag`) — the release-publish pipeline
   depends on it and this release does not change publishing.
2. **Branch-name pattern validation** — a local branch name outside the four permitted
   patterns is refused, with the pattern set in the message.
3. **Develop-diff-keyed security verdict** — the verdict is satisfied by an APPROVED
   `security-reviewer` handoff covering the **`origin/develop..develop`** delta being
   pushed, replacing the bare per-ref sha match. `PushRef.local_ref` (parsed at `:69`,
   unused today) is the insertion point.

**TDD is mandatory:** every rule lands as a RED contract test first, in
`tests/contract/` / `tests/unit/features/chokepoints/`, failing for the real reason, then
the implementation, then GREEN.

**Acceptance**

- A4.1 Contract tests exist and pass for: push of `refs/heads/main` → **refused**; push of
  `refs/heads/feature/v0.6.0` → **refused**; push of `refs/heads/develop` with an APPROVED
  develop-delta handoff → **allowed**; push of `refs/heads/develop` with no matching
  handoff → **refused**; tag push → **allowed** (unchanged); branch named
  `bugfix/whatever` → **refused**; each of the four permitted patterns → **accepted** by
  the name validator.
- A4.2 Each refusal message names (i) which rule fired, (ii) the permitted value, (iii) the
  corrective action. Asserted in the tests, not merely observed.
- A4.3 `mypy --strict` clean; `ruff format --check` + `ruff check` clean;
  `lint-imports --config setup.cfg --no-cache` → contracts kept, **0 broken**.
- A4.4 The full suite is green, and the new tests are **proven RED before GREEN** — the
  RED evidence (failing output, pre-fix) is recorded in CLOSURE. A test that never failed
  proves nothing.
- A4.5 No net loosening: the pre-push CI preflight (`ruff format --check`, `ruff check`,
  `mypy --strict`, `pytest`) is preserved verbatim.

### FR5 — CI and GitHub: `pr-source-guard`, retired push triggers, required check

1. **New CI job `pr-source-guard`** — on `pull_request` targeting `main`, **fails** when
   `github.event.pull_request.head.ref != 'develop'`, with an error message naming the
   rule.
2. **Retire the `feature/**` and `hotfix/v*` push triggers** (`ci.yml:5-9`) — those
   branches are local-only, so a push trigger on them is dead configuration that also
   advertises a forbidden workflow. The push-triggered `hotfix-branch-name` job
   (`ci.yml:403-418`) is retired with them; its PATCH≥1 pattern knowledge moves to FR4's
   branch-name validator, which runs at the real boundary.
3. **Flip `pr-source-guard` into `main`'s required checks** *after* the first PR merges
   with the job present (a required check that has never run blocks every PR, including
   this release's own).

**Acceptance**

- A5.1 A PR to `main` whose head is not `develop` **fails** `pr-source-guard` —
  demonstrated once on a scratch PR, run URL recorded in CLOSURE.
- A5.2 A PR to `main` whose head **is** `develop` passes `pr-source-guard`.
- A5.3 `ci.yml` push triggers list exactly `main` and `develop`; no `feature/**`, no
  `hotfix/v*`; no job remains whose `if:` can never be true.
- A5.4 `pr-source-guard` appears in `main`'s required-checks list **after** the first merge;
  the ordering is recorded in CLOSURE (this is a sequencing acceptance, not a nice-to-have).
- A5.5 Every CI job green on `develop` after the milestone-(b) push.

### FR6 — Hygiene: stale citations, contradictory regex, false claim

1. **4 dangling `release-governance` citations** → reworded to cite `DADAIA.md` §5 or
   `dadaia-gitflow`: `public/skills/dadaia-task-manager/SKILL.md:54`,
   `public/skills/dadaia-release-closure/SKILL.md:121`,
   `dadaia_workspace/features/specs/doctor_closure_audit.py:286`,
   `dadaia_workspace/features/backlog/doctor.py:56`.
2. **Constitution §11/§13 citations reconciled** — the scaffold constitution has seven
   unnumbered sections and no §11/§13, while 5+ agents cite them. Resolve **one** of two
   ways, and only one: (a) add the sections to `public/scaffold/constitution.md` so the
   citations resolve, or (b) re-anchor every citation to a real authority. Whichever is
   chosen must be applied **uniformly** — a mixed outcome is a fail.
3. **`public/scaffold/releases/README.md:20`** regex `^[a-z][a-z0-9-]+$` → the canon
   `^v\d+\.\d+\.\d+$` (the current expression rejects `v0.6.0`, i.e. the very release
   authoring the fix). Also correct the `ACTIVE.md` format block there to include the
   optional `segment:` line, which schema v2 already carries.
4. **`ai-engineer.md:102` and `:349`** — the "only `pre-push-ci-gate.sh` remains" claim is
   false: `public/scripts/` holds 5 files, 3 shell. State the real inventory.

**Acceptance**

- A6.1 `grep -rn "release-governance" dadaia_workspace/ ` returns **0** hits outside
  `specs/` history (`install_helpers.py:222`'s retired-filename entry is a migration
  sweep list, not a citation — it stays and is named as such in CLOSURE).
- A6.2 Every `constitution §N` citation in `public/agents/**` resolves to a section that
  exists in `public/scaffold/constitution.md`. Mechanically checkable: extract every cited
  §N, intersect with the scaffold's section set, expect an empty difference.
- A6.3 `public/scaffold/releases/README.md` states `^v\d+\.\d+\.\d+$` and its `ACTIVE.md`
  block matches the v2 schema (`release:` / optional `segment:` / `phase:`).
- A6.4 `ai-engineer.md` names the actual `public/scripts/` inventory; a reviewer diffing
  the file against `ls public/scripts/` finds no discrepancy.
- A6.5 `dadaia specs doctor` and `dadaia public doctor` both exit **0** on this live
  instance after the pass.

### FR7 — Hotfix version law encoded

Encode the PATCH-mint rule as the workspace's stated behaviour: at hotfix merge into
`develop`, `pyproject.toml` `version` is bumped to the minted PATCH and a `CHANGELOG.md`
entry is written in the same commit. `RELEASE_SEMVER_RE` and the `^v\d+\.\d+\.\d+$` canon
are **untouched** — the version *format* is already right; what is new is *when and by whom
a PATCH is minted*.

**Acceptance**

- A7.1 The rule is stated in `dadaia-gitflow` (bug-fix/hotfix row: commit cadence + merge
  target + the two files bumped) and in `DADAIA.md` §5 item 5 — and **nowhere else**.
- A7.2 `RELEASE_SEMVER_RE` and every consumer of it are byte-unchanged by this release
  (`git diff` on the defining module shows no change to the pattern).
- A7.3 No `specs/releases/**` directory is created for a hotfix by any surface after this
  release; `product-engineer.md` explicitly forbids it (A3.2).

---

## 4. Out of scope (non-goals)

- **No workflow engine.** Nothing here assembles prompts, advances gates, or runs a
  lifecycle. Arm A stays agent-dispatched against the SDD documents (`DADAIA.md` §1). A
  "gitflow runner" is explicitly not built.
- **No lock reintroduction.** The NO-LOCKS DOCTRINE stands: races are surfaced, never
  prevented. Branch policy is a **ref/name** policy at the push boundary — it is not a
  lease, not ownership, and it never blocks a write or waits on another session.
- **No consumer-repo migration.** This release standardizes the `dadaia-workspace` context
  only. One consumer repo already runs gitflow natively and needs nothing; other consumer
  repos are untouched, and no migration verb is written.
- **No change to publishing.** `release.yml`, the OIDC trusted-publishing flow, tag pushes,
  and the PyPI `0.2.x` version scheme are untouched. Tag pushes keep their carve-out.
- **No change to the `pre_gate` path-class model.** §3's ADDITIVE/MEMORY/MUTATING/
  FROZEN/PROTECTED classification is unchanged; this release adds a *push*-boundary rule,
  not a write-boundary rule.
- **No re-dispositioning of the superseded draft's backlog entries.**
  `test-runtime-efficiency` and `test-artifact-hygiene` are closed on the bug track
  (`test-suite-real-venv-and-ci-longpole`, `panel-e2e-artifacts-no-consumer`); this release
  neither picks nor re-dispositions them, and says so in CLOSURE.
- **No history rewrite.** Existing `feature/*` remote branches and the v0.5.0 ship record
  are historical fact; nothing is force-pushed or renamed to make the past conform.
- **`dadaia specs hotfix open` CLI removal** is *not* in scope as a code deletion — FR3
  removes the agent-level ceremony that invokes it; retiring the verb itself is a backlog
  return if it is then dead surface.

---

## 5. Dependencies and risks

**Dependencies.** No new Python dependency; no new action beyond `pr-source-guard`'s
inline shell. `DADAIA.md` is PROTECTED and projected `0444` — the source of truth is
`dadaia_workspace/public/data/DADAIA.md` and the projection chain is
`dadaia public stage` → `dadaia public install --target all` → `dadaia public doctor`.

**Ordering (binding).** FR1+FR2 (law + skill) land **before** FR3, because FR3's edits are
"defer to the skill" and the skill must exist to be deferred to. FR6 rides with FR3 (same
files, same pass). FR4 is independent code and may run parallel to FR3/FR6 (disjoint write
set). FR5's step 3 (required check) is **strictly after** the first merge. FR7 is text
inside FR1/FR2's files and carries no independent task.

| # | Risk | Mitigation |
|---|---|---|
| R1 | `DADAIA.md` is PROTECTED + `0444`; an agent edits the projection and the change is lost or drift is faked | Edit **only** `public/data/DADAIA.md`; re-project; `public doctor` must report zero drift and four `0444` byte-identical copies (A1.3). Hand-editing a projection is a process violation, not a shortcut |
| R2 | A required `pr-source-guard` that has never run blocks **every** PR, including this release's | FR5 step 3 is explicitly sequenced after the first merge (A5.4) |
| R3 | Develop-only push refusal locks the operator out of a legitimate push (tag, hotfix of the gate itself) | Tag carve-out preserved verbatim (A4.1); the refusal message names the corrective action; the gate's own bugs are fixable because the hook is bypassable by the operator, by design |
| R4 | The develop-diff-keyed verdict is subtler than a sha match and could pass on a stale handoff | Contract tests assert refusal when the handoff does not cover the delta being pushed (A4.1); the RED-before-GREEN evidence is required (A4.4) |
| R5 | The token cost of the law grows — `DADAIA.md` is the always-on prefix and already exceeds its aspiration (deviation N-1) | A1.4 caps growth at +400 tokens with before/after numbers in CLOSURE; the operational detail lives in the skill (loaded on demand), not in the law |
| R6 | The dedup pass (FR3) removes a rule instead of relocating it | A2.3's grep proves relocation, not deletion: every branch-pattern hit must resolve to the skill, the law, or a reference. A reviewer confirms each removal has a home |
| R7 | Retiring the `feature/**`/`hotfix/v*` push triggers removes CI coverage for work in progress | Coverage moves to the `develop` push + the PR to `main`; the pre-push CI preflight already runs the full ladder locally before any push, so no work reaches the remote unvalidated |
| R8 | Constitution §11/§13 reconciliation is chosen differently by different agents, leaving a mixed state | FR6.2 requires **one** uniform resolution across all citations; a mixed outcome fails A6.2 |
| R9 | Revoking the hotfix ceremony leaves bugs with no record of what shipped | Nothing is lost: the bug ledger (`specs/bugs/bugs.jsonl` events) plus the `CHANGELOG.md` entry at merge are the record, and both already exist. The ceremony was the redundant layer |
| R10 | `develop` and `feature/v0.6.0` diverge across the two milestones and the second merge conflicts in the very files this release rewrites | Milestone (a) merges the definition trio early, so the definition is on `develop` before implementation starts; implementation then rebases/merges from `develop` before milestone (b) |

---

## 6. Memory atoms affected at closure

- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — **primary.** The branch
  topology, stage placement, two-milestone cadence, hotfix PATCH-mint law, and the
  diff-based push verdict are all this atom's subject matter. Rewritten to current truth.
- `specs/memory/product/sdd/sdd-gate-v3.md` — the **git chokepoints** section: pre-push now
  enforces develop-only refs, branch-name patterns, and a develop-diff-keyed verdict, in
  addition to the CI preflight. Pre-commit stays warn-only.
- `specs/memory/quality-assurance.md` — **CI** section: the `pr-source-guard` required
  check and the retirement of the `feature/**`/`hotfix/v*` push triggers.
- `specs/memory/product/distribution/public-asset-distribution.md` — the universal-skill
  roster gains `dadaia-gitflow` (universal, not derived).
- `specs/memory/architecture.md` — **expected: minor.** The chokepoint script inventory
  sentence (`public/scripts/pre-push-ci-gate.sh` — "CI and exact-commit security verdict")
  becomes "CI, branch policy, and develop-diff security verdict". No layer boundary moves;
  stated explicitly either way.
- `specs/memory/tech-stack.md` — **expected: no change** (no dependency, no Python version,
  no harness roster, no packaging contract moves). Stated explicitly either way, as the
  closure protocol requires.
- `specs/memory/product/{index.md,catalog.json}` — **regenerated, never hand-edited**, if
  any atom's `tldr`/`summary` frontmatter moves.

Memory describes the product after this release. The before/after of the branch model lives
in CLOSURE and in this SPEC, never in an atom.

---

## 7. Acceptance criteria (release-level)

1. **All seven FRs' acceptance sub-criteria (A1.1–A7.3) met**, each with its stated
   evidence in CLOSURE. A criterion asserted without evidence is not met.
2. **One home:** the branch model is explained operationally in exactly one file
   (`dadaia-gitflow/SKILL.md`), stated at law level in exactly one place
   (`DADAIA.md` §5/§6), and referenced everywhere else — proven by the A2.3 grep across
   `dadaia_workspace/public/`.
3. **Mechanically enforced:** pushes of `main` and of a `feature/*` ref are **refused** by
   the real installed chokepoint on this live instance (demonstrated, output in CLOSURE);
   a PR to `main` from a non-`develop` head **fails** `pr-source-guard` (run URL in
   CLOSURE).
4. **The contradiction is gone:** no surface in the tree prescribes a hotfix SPEC, a hotfix
   release directory, or a full push-gate scan.
5. **Zero stale citations:** A6.1 + A6.2 + A6.3 + A6.4 all clean.
6. **Green everywhere:** `pytest -p no:cacheprovider -q` full suite; `ruff format --check`;
   `ruff check`; `mypy --strict`; `lint-imports --config setup.cfg --no-cache`;
   `dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor` all exit 0 on this live
   instance.
7. **The release ships by its own rules:** milestone (a) — definition trio `Aprovado`,
   merged to local `develop`, diff-based security APPROVE of `origin/develop..develop`,
   `develop` pushed; milestone (b) — same sequence at ship, then PR `develop` → `main`,
   every CI job green, merge. Any deviation is a finding, not a footnote.
8. **CLOSURE carries** the `## Dispositions` table flipping
   `specs/backlog/gitflow-standardization.md` to `DELIVERED — v0.6.0` with every one of its
   six intents mapped to the FR that consumed it, plus the `DADAIA.md` token before/after,
   the RED-before-GREEN evidence for FR4, and both demonstrated-refusal outputs.
