# TASKS — Release v0.6.0 — Gitflow standardization

**Status:** Aprovado
**Release ID:** v0.6.0
**Segment:** `alpha-1`
**Owner:** product-engineer
**Source PLAN:** `specs/releases/v0.6.0/PLAN.md`
**Source SPEC:** `specs/releases/v0.6.0/SPEC.md`
**Grill:** `specs/releases/v0.6.0/GRILL.md`
**Branch:** `feature/v0.6.0` (cut from `develop`)

> Supersedes the untracked 2026-08-11 TASKS of the same release id (T-60-01..09, test
> runtime efficiency) — scope consumed by the bug flow the same day.

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **The law is edited at source only.** `dadaia_workspace/public/data/DADAIA.md` is the one
  editable copy; the four projections are `0444` and PROTECTED. Every text task ends with
  `dadaia public stage` → `dadaia public install --target all` → `dadaia public doctor`.
  Hand-editing a projection is a process violation, never a shortcut.
- **Reference, never restate.** After T-060-02, the branch model is explained operationally
  in exactly one file. Every removal from a tier-2 surface must be answerable with "it now
  lives at `dadaia-gitflow` line N". The A2.3 grep is the proof and it is run twice — by the
  author and by QA.
- **RED before GREEN, with evidence.** T-060-04's tests are written first and their failing
  output is captured for CLOSURE. A gate test that never failed proves nothing.
- **Nothing is loosened.** The pre-push CI preflight ladder and the tag carve-out are copied
  through verbatim. This release adds a rule.
- **A group of completed tasks = a commit** (D5). Not one commit per file.
- **This release ships by its own rules.** Milestone (a) already fired: the definition trio
  is `Aprovado`, merged to local `develop`, security-reviewed on
  `origin/develop..develop`, and `develop` pushed. Milestone (b) is T-060-08.
- **Parallelism.** `T-060-04` (package code + tests) may hold a concurrent `[-]` with
  `T-060-03` (`public/**` text) — disjoint write sets. Everything else is sequential. Never
  two `[-]` outside that one sanctioned pair.
- **The self-lockout rules are not negotiable:** `pr-source-guard` becomes a *required*
  check only after the first merge (T-060-09), and T-060-04 must prove the **allow** path as
  rigorously as the refuse paths.

---

- [x] **T-060-01 — `dadaia-gitflow`: the single home of the git contract**

**Owner role:** ai-engineer · **Commit:** `feat(T-060-01): add dadaia-gitflow universal skill`

**Preconditions:** none. **First task of the release** — nothing may defer to a skill that
does not exist.

**Write set:** `dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md` (**new file, sole
write**). No other file. Projections are produced by T-060-02's chain, not hand-written.

**Description:** Author the universal skill (read natively by every entry harness; **not** a
per-harness derivation, so no `public/entities/registry.json` entry). Required content, per
SPEC FR2:

1. The **four-branch table** — pattern, lives-where, pushable yes/no, cut-from, merges-into:
   `main` (remote+local, not pushable, PR from `develop` only), `develop` (the only pushable
   branch), `feature/{M.m.p}` (local-only), `hotfix/{M.m.p}` (local-only).
2. The **stage-by-stage table** — exactly **seven** rows (backlog-definition, bug-register,
   bug-fix/hotfix, release-definition, release-implementation, ship, closure/archive) ×
   **four** columns (branch, commit cadence, merge target, push trigger).
3. The **two merge milestones** — (a) definition trio `Aprovado`, (b) ship — each followed,
   in order, by a diff-based security review of `origin/develop..develop` and a push of
   `develop`.
4. The **hotfix PATCH-mint rule** — next PATCH; at merge to `develop`, `pyproject.toml`
   version bump **+** `CHANGELOG.md` entry in the same commit; **no release ceremony**.
5. An explicit **mechanical vs discipline** split, naming the three enforcement mechanisms
   (pre-push ref refusal, branch-name validation, `pr-source-guard`) so a reader knows which
   violations are refused and which are merely caught in review.

**Done criterion:**
- File exists with valid frontmatter; **≤ 150 lines** (A2.4).
- Stage table has exactly 7 rows and 4 contract columns; every stage of `DADAIA.md` §1's two
  arms has a row (A2.2).
- The hotfix row states the PATCH mint and the two bumped files, and states that no
  `specs/releases/**` directory is created (A7.1).
- No content in the skill duplicates a `DADAIA.md` §5/§6 sentence verbatim — the law states,
  the skill operates.

---

- [x] **T-060-02 — `DADAIA.md` §5/§6 rewrite + projection**

**Owner role:** ai-engineer · **Commit:** `refactor(T-060-02): four-branch law in DADAIA.md §5/§6`

**Preconditions:** T-060-01 `[x]` (the law delegates to the skill; the skill must exist).

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (**source only**). Projections
(`DADAIA.md` at root, `.claude/rules/DADAIA.md`, `.codex/DADAIA.md`,
`.kimi-code/DADAIA.md`) are **regenerated, never edited** — they are `0444` and PROTECTED.

**Description:** Rewrite §5 (Specs, tasks and memory) and §6 (Quality) to state the six
law-level items of SPEC FR1 **once each**, delegating operational detail to
`dadaia-gitflow`: the four patterns with `develop` as the only pushable branch and `main`
via PR only; stage placement (backlog/research/bug-registration on `develop` with a commit
per registration; definition **and** implementation on `feature/{M.m.p}`); the two-milestone
merge cadence with its mandatory post-merge sequence; finalization order **memory → CLOSURE
→ archive**; the hotfix PATCH-mint law with **no ceremony**; the **diff-based** push-gate
review with full scans surviving only in the audit lane.

Then run the projection chain: `dadaia public stage` → `dadaia public install --target all`
→ `dadaia public doctor`.

**Measure the always-on token count before the edit and after.** This file is injected on
every turn in the workspace; growth is paid forever. Cap: **+400 tokens** (A1.4). Report both
numbers regardless of the outcome.

**Done criterion:**
- §5/§6 carry all six items; the branch-pattern set in the file is **exactly** the four
  (no `release/*`, `bugfix/*`, or bare `feature/{version}` remnant) (A1.1).
- The contract appears in exactly one place in the file; no section restates another
  (A1.2 — reviewer diff read, not grep alone).
- `dadaia public doctor` → `[ok] public-privacy`, **zero drift**, four `0444`
  byte-identical `DADAIA.md` copies; `dadaia-gitflow` present in `.claude/skills/`,
  `.agents/skills/`, `.codex/`, `.kimi-code/` (A1.3, A2.1).
- Token before/after pair captured for CLOSURE; growth ≤ +400.
- `dadaia specs doctor` exits 0.

---

- [ ] **T-060-03 — Tier-2 dedup + hygiene on the `public/` surface**

**Owner role:** ai-engineer · **Commit:** `refactor(T-060-03): defer git contract to dadaia-gitflow; fix stale citations`

**Preconditions:** T-060-02 `[x]`. **May hold a concurrent `[-]` with T-060-04** (disjoint
write sets: `public/**` text vs package code + tests).

**Write set:** `dadaia_workspace/public/skills/{project-orchestration,dadaia-task-manager,dadaia-release-closure,dadaia-release-definition}/SKILL.md`;
`dadaia_workspace/public/agents/{product-engineer,security-reviewer,code-reviewer,project-manager,software-engineer,qa-engineer,ai-engineer}.md`;
`dadaia_workspace/public/scaffold/releases/README.md`;
`dadaia_workspace/public/scaffold/constitution.md` **only if** FR6.2 resolution (a) is
chosen. **Explicitly not in this write set:** the two Python citation sites
(`features/specs/doctor_closure_audit.py:286`, `features/backlog/doctor.py:56`) — they are
package files and belong to T-060-04, which keeps this pair disjoint.

**Description:** Two jobs in one pass, because they are the same files.

**(1) The ten deferrals** (SPEC FR3 table): `project-orchestration` cadence table +
`feature/{version}` mention; `dadaia-task-manager` (commit cadence + branch placement by
reference — this file also carries the `release-governance` citation at `:54`);
`dadaia-release-closure` (finalization order stated as **memory → CLOSURE → archive**; the
`release-governance` citation at `:121`); `dadaia-release-definition` (definition happens on
`feature/{M.m.p}`; milestone (a) obligation); `security-reviewer` (push-gate `scan_target`
**diff-only**, `full` only in the audit lane); `code-reviewer` (PR base `develop` → `main`);
and the forbidden-action lists of `project-manager`, `software-engineer`, `qa-engineer`,
`ai-engineer` (never push a non-`develop` ref; never commit to `main`).

**`product-engineer.md` is the delicate one.** It carries a full hotfix *release* lifecycle:
PATCH≥1 release dir, SPEC from `release_hotfix.md.j2`, `closure_hotfix.md.j2`,
`dadaia specs hotfix open`, a condensed 7-phase flow, a status ladder. **All of it is
revoked** (D4). The rewrite must state the revocation **explicitly** — a reader who knows
the old law must find its retirement, not silence — and must say where the record now lives
(the append-only bug ledger + the `CHANGELOG.md` entry at merge), so nobody "restores" the
ceremony as a perceived regression.

**(2) The hygiene sites:** `scaffold/releases/README.md:20` regex `^[a-z][a-z0-9-]+$` →
`^v\d+\.\d+\.\d+$` (the current expression **rejects `v0.6.0`**), plus its `ACTIVE.md`
block updated to the v2 schema (`release:` / optional `segment:` / `phase:`);
`ai-engineer.md:102` and `:349` → the real `public/scripts/` inventory (5 files, 3 shell:
`certify-dadaia-workspace.sh`, `pre-commit-presence-gate.sh`, `pre-push-ci-gate.sh`);
the **constitution §11/§13 gap** — the scaffold constitution has 7 unnumbered `##` sections
and no §11/§13, while `software-engineer:268`, `project-manager:100`, `qa-engineer:69`,
`security-reviewer:58/113/240`, `code-reviewer:57/113/222`, `product-engineer` and
`project-auditor:267` cite them. Choose **one** resolution — add the sections, or re-anchor
every citation — and apply it **uniformly**. A mixed outcome fails.

Re-project at the end (same chain as T-060-02).

**Done criterion:**
- **A2.3 relocation grep clean:** every hit on the four branch-pattern literals under
  `dadaia_workspace/public/` is inside `dadaia-gitflow/SKILL.md`, inside `DADAIA.md` §5/§6,
  or a reference to the skill. Any other hit is a stop condition.
- `product-engineer.md` contains **no** `release_hotfix`, `closure_hotfix`, or
  `specs hotfix open`, and no hotfix section prescribing a SPEC (A3.2).
- `security-reviewer.md` push-gate section admits exactly one scan target; `full` appears
  only in the audit-lane section (A3.3). `code-reviewer.md` states `develop` → `main` with
  no `feature/*` → `main` path (A3.4).
- Every `constitution §N` citation in `public/agents/**` resolves to a section that exists in
  `public/scaffold/constitution.md` (A6.2 — extract cited §N, intersect, expect empty diff).
- `scaffold/releases/README.md` states the canon regex and the v2 `ACTIVE.md` block (A6.3);
  `ai-engineer.md` matches `ls public/scripts/` (A6.4).
- **No agent frontmatter allowlist widened** (A3.5, diff-read).
- `dadaia public doctor` + `dadaia specs doctor` both exit 0 (A6.5).

---

- [-] **T-060-04 — Chokepoint enforcement, TDD (RED before GREEN)**

**Owner role:** software-engineer · **Commits:** `test(T-060-04): RED contract tests for develop-only push policy` then `feat(T-060-04): develop-only push, branch-name validation, develop-diff verdict`

**Preconditions:** T-060-02 `[x]` (the law must name the patterns the code enforces).
**May hold a concurrent `[-]` with T-060-03.**

**Write set:** `dadaia_workspace/features/chokepoints/service.py`;
`dadaia_workspace/cli/commands/ci.py` (`push_gate_check`, `:227-244`);
`tests/contract/**` + `tests/unit/features/chokepoints/**` (new/extended);
`dadaia_workspace/features/specs/doctor_closure_audit.py:286` and
`dadaia_workspace/features/backlog/doctor.py:56` (**comment-only** — the two Python
`release-governance` citations, reworded to cite `DADAIA.md` §5 or `dadaia-gitflow`).
No `public/**` file, no workflow YAML (that is T-060-05).

**Description:** Two commits, in this order — the RED commit is not optional.

**RED.** Write the contract tests first, covering all seven cases of A4.1: push
`refs/heads/main` → **refused**; push `refs/heads/feature/v0.6.0` → **refused**; push
`refs/heads/develop` with an APPROVED handoff covering `origin/develop..develop` →
**allowed**; push `refs/heads/develop` with **no covering** handoff → **refused**; **tag
push → allowed** (the existing `PushRef.is_tag` carve-out, `:82` — publishing depends on
it); branch named `bugfix/whatever` → **refused**; each of the four permitted patterns →
**accepted** by the name validator. **Capture the failing output** — A4.4 requires the RED
evidence in CLOSURE.

**GREEN.** Implement at the natural seam: `PushRef.local_ref` is parsed at
`features/chokepoints/service.py:69` and read nowhere today. Add (i) the develop-only ref
policy, (ii) the four-pattern branch-name validator, (iii) the **develop-diff-keyed**
verdict replacing the bare per-ref sha match in `push_gate_decision` (`:229-259`), and wire
through `cli/commands/ci.py::push_gate_check`. Every refusal message names the rule, the
permitted value, and the corrective action (A4.2) — asserted in the tests.

The subtle risk is a **false pass**: "does this APPROVED handoff cover the delta" is
semantically richer than sha equality, and its failure mode is invisible. The
non-covering-handoff refusal test is the one that matters most.

**Done criterion:**
- All seven A4.1 cases pass; A4.2 message content asserted in tests, not merely observed.
- RED evidence (pre-fix failing output) captured for CLOSURE (A4.4).
- CI preflight ladder and tag carve-out byte-unchanged (A4.5); `RELEASE_SEMVER_RE` untouched
  (A7.2, `git diff` on its module shows no pattern change).
- `mypy --strict` clean; `ruff format --check` + `ruff check` clean;
  `lint-imports --config setup.cfg --no-cache` → contracts kept, **0 broken** (A4.3).
- Full suite green: `pytest -p no:cacheprovider -q`.
- `grep -rn "release-governance" dadaia_workspace/` → 0 citation hits;
  `install_helpers.py:222` (a retired-filename **sweep list**, not a citation) remains and is
  named as such for CLOSURE (A6.1).
- **Live wiring demonstration:** on this instance, an attempted push of `main` and of a
  `feature/*` ref is actually **refused** by the installed hook, output captured. The suite
  proves the function; only the demonstration proves the wiring.

---

- [ ] **T-060-05 — CI: `pr-source-guard` + retire the local-only push triggers**

**Owner role:** software-engineer · **Commit:** `ci(T-060-05): pr-source-guard; retire feature/hotfix push triggers`

**Preconditions:** T-060-04 `[x]` — the hook and the CI check must encode the **same** four
patterns; writing this first would create two sources of truth for the pattern set.

**Write set:** `.github/workflows/ci.yml` only. **Not** `.github/workflows/release.yml` —
publishing is out of scope and tag pushes keep their carve-out.

**Description:**
1. **Add `pr-source-guard`**: on `pull_request` targeting `main`, fail when
   `github.event.pull_request.head.ref != 'develop'`, with an error message naming the rule.
   Do not interpolate `head.ref` into a shell command unquoted — it is attacker-influenceable
   on a fork PR; read it from `env:` and compare in the script.
2. **Retire the push triggers** `feature/**` and `hotfix/v*` (`ci.yml:5-9`) — those branches
   are local-only, so a push trigger on them is dead configuration that also advertises a
   forbidden workflow. Retire the now-unreachable push-triggered `hotfix-branch-name` job
   (`:403-418`) with them; its PATCH≥1 pattern knowledge lives in T-060-04's validator, at
   the boundary that actually exists.
3. **Demonstrate the guard once**: a scratch PR to `main` from a non-`develop` head must
   **fail** `pr-source-guard`; record the run URL. Then confirm a `develop`-headed PR passes.

**Do not** add `pr-source-guard` to `main`'s required checks here — that is T-060-09, after
the first merge (R2). A required check that has never run blocks every PR, including this
one.

**Done criterion:**
- Scratch PR with non-`develop` head fails `pr-source-guard`; run URL captured (A5.1).
- `develop`-headed PR passes `pr-source-guard` (A5.2).
- `ci.yml` push triggers are exactly `main` and `develop`; no `feature/**`, no `hotfix/v*`;
  **no job remains whose `if:` can never be true** (A5.3).
- `head.ref` is never interpolated into a shell string; it is passed via `env:`.
- Every CI job green on the branch's push path.

---

- [ ] **T-060-06 — QA `alpha-1`: validate the contract on the live instance**

**Owner role:** qa-engineer · **Commit:** `test(T-060-06): alpha-1 QA review committed to the branch`

**Preconditions:** T-060-01..05 all `[x]`.

**Write set:** `specs/releases/v0.6.0/ALPHA-1-QA.md` (the review, committed to the branch per
the segment protocol) + `.dadaia/handoff/dadaia-workspace/`. **No source file, no `public/`
file.** A finding is reported, never fixed here.

**Description:** Validate from the **live instance**, not from the diff:

1. The four `DADAIA.md` projections' bytes **and** modes (`0444`, byte-identical to source);
   `dadaia-gitflow` present in all four projection roots.
2. The **refusals**: a `main` push and a `feature/*` push are refused by the *installed*
   hook, with actionable messages; a `develop` push with a covering APPROVED verdict is
   allowed; a `develop` push with a non-covering handoff is refused. Capture each output.
3. `pr-source-guard`: the red run and the green run, by URL.
4. `dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor` — all exit **0**.
5. The full quality ladder: `pytest -p no:cacheprovider -q`, `ruff format --check`,
   `ruff check`, `mypy --strict`, `lint-imports --config setup.cfg --no-cache`.
6. **Re-run the A2.3 relocation grep independently.** A dedup pass audited only by its own
   author is not audited. Every hit must resolve to the skill, the law, or a reference.
7. Spot-check that `product-engineer.md` no longer prescribes a hotfix SPEC and that
   `security-reviewer.md` no longer admits a full push-gate scan (SPEC §7 item 4).

**Done criterion:** SPEC §7 items 1–6 verified with evidence per item; the `alpha-1` review
committed to the branch. Any missed target is reported as a **finding with its evidence**,
never rounded into a pass. A REJECTED verdict returns the offending task to `[-]` and is
preserved verbatim in the review file as the historical record.

---

- [ ] **T-060-07 — Review + diff-based security verdict**

**Owner role:** code-reviewer + security-reviewer (verdicts); software-engineer applies any
required fix · **Commit:** fixes only, each returning its task to `[-]`

**Preconditions:** T-060-06 `[x]` with a PASS verdict.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (verdict handoffs). No source file except
a fix a reviewer requires.

**Description:** Six-axis code review. The security review is **diff-based on
`origin/develop..develop`** — this release's own rule, applied to itself; a full scan here
would be the first violation of the law being shipped. Surfaces that matter:

- **The new refusal logic** — can it be bypassed? does it fail **open** on a malformed
  stdin line (`parse_push_refs` skips malformed lines today, `:86`) — and is failing open on
  an unparseable ref the right posture for a *policy* gate?
- **The CI job** — `head.ref` is fork-controlled input; confirm it never reaches a shell
  string unquoted.
- **The meta-risk** — this release edits its own gate. Confirm the gate cannot be made
  permanently unsatisfiable (the `quality-assurance.md` "Satisfiable Diagnostics" law: every
  refusal must be clearable by an action the product accepts).

**Done criterion:** code-review **APPROVE**; `security-reviewer` **APPROVED** handoff whose
verdict covers the `origin/develop..develop` delta about to be pushed. Any
`REQUEST_CHANGES`/`REJECTED` returns the named task to `[-]`.

---

- [ ] **T-060-08 — Milestone (b): merge to `develop`, push, PR to `main`, CI green**

**Owner role:** software-engineer · **Commit:** merge commit + any CI fix

**Preconditions:** T-060-07 `[x]` with both verdicts APPROVE.

**Write set:** git refs only (`develop` merge + push; PR). No spec file, no source file
except a fix CI demands (each returning its task to `[-]`).

**Description:** Execute the ship milestone **by the rules this release writes** — the first
real exercise of the model:

1. Merge `feature/v0.6.0` → **local `develop`**.
2. Diff-based security review of `origin/develop..develop` (T-060-07's verdict must cover
   the merged delta; if the merge changed it, the verdict is re-issued).
3. **Push `develop`** — and this push must pass the very chokepoint T-060-04 installed. If
   it is refused, that is a **defect in this release**, fixed at cause, never bypassed.
4. Open PR `develop` → `main`. Watch CI until **every** job is green; read the failing log,
   fix the cause, push again, keep watching.
5. Merge the PR.

**Done criterion:** `develop` pushed and accepted by the installed gate; every CI job green
on `develop` and on the PR (A5.5); `pr-source-guard` green on a `develop` head; PR merged.
The push refusal path is **not** worked around — if the gate refuses a legitimate push, the
gate is wrong and is fixed.

---

- [ ] **T-060-09 — `pr-source-guard` becomes a required check**

**Owner role:** software-engineer · **Commit:** none (GitHub branch-rule change; recorded in
CLOSURE)

**Preconditions:** T-060-08 `[x]` — **strictly after the first merge** (R2). A required check
that has never run blocks every PR, including this release's own.

**Write set:** GitHub branch protection on `main` (no repository file). Recorded in CLOSURE.

**Description:** Add `pr-source-guard` to `main`'s required-checks list, so a PR to `main`
from any head other than `develop` is **mechanically unmergeable** rather than merely red.
This is the third of the three mechanical enforcement points (D7) and the one that closes
`main`.

**Done criterion:** `pr-source-guard` appears in `main`'s required checks; the
after-first-merge ordering is recorded in CLOSURE (A5.4); a subsequent non-`develop`-headed
PR is blocked from merging, not just failing.

---

- [ ] **T-060-10 — Memory update → CLOSURE → archive (in that order)**

**Owner role:** product-engineer · **Commit:** `docs(T-060-10): v0.6.0 closure, memory atoms, dispositions`

**Preconditions:** T-060-01..09 all `[x]`. **`ACTIVE.md` phase set to `CLOSURE` before any
memory write** — the memory path class is phase-gated.

**Write set:** `specs/memory/product/sdd/sdd-bug-backlog-governance.md`;
`specs/memory/product/sdd/sdd-gate-v3.md`; `specs/memory/quality-assurance.md`;
`specs/memory/product/distribution/public-asset-distribution.md`;
`specs/memory/architecture.md`; `specs/memory/product/{index.md,catalog.json}` **only if** an
atom's frontmatter `tldr`/`summary` moved (**regenerated** by the catalog generator, never
hand-edited); `specs/releases/v0.6.0/CLOSURE.md`; `specs/releases/ACTIVE.md`;
`specs/backlog/gitflow-standardization.md` (terminal disposition); `CHANGELOG.md`.

**Description:** The order is the law (D5): **memory update → CLOSURE → archive.**

**Memory** describes the product *as it is now*, with no changelog and no "we used to push
from feature branches":
- `sdd-bug-backlog-governance.md` — the four-branch topology, stage placement, the
  two-milestone cadence, the hotfix PATCH-mint law, the diff-based push verdict.
- `sdd-gate-v3.md` — git chokepoints: pre-push now enforces develop-only refs, branch-name
  patterns, and a develop-diff-keyed verdict on top of the CI preflight; pre-commit stays
  warn-only.
- `quality-assurance.md` — CI: `pr-source-guard` as a required check; the retired
  `feature/**`/`hotfix/v*` push triggers.
- `public-asset-distribution.md` — the universal-skill roster gains `dadaia-gitflow`
  (universal, **not** derived — no registry entry).
- `architecture.md` — the chokepoint inventory sentence: `pre-push-ci-gate.sh` now covers
  "CI, branch policy, and develop-diff security verdict".
- `tech-stack.md` — **state explicitly that it is unchanged**, and why (no dependency, no
  Python version, no harness roster, no packaging contract moved).

**CLOSURE** carries: the `## Validations` evidence triples; the `## Dispositions` table
flipping `specs/backlog/gitflow-standardization.md` to **`DELIVERED — v0.6.0`** with **all
six** of its intents mapped to the FR that consumed each; the `DADAIA.md` token before/after
pair; T-060-04's **RED-before-GREEN evidence**; both live refusal demonstrations; the
`pr-source-guard` red-run URL and the required-check ordering; a statement that the
superseded 2026-08-11 draft's backlog entries (`test-runtime-efficiency`,
`test-artifact-hygiene`) are dispositioned on the **bug** track and were neither picked nor
re-dispositioned here; and any backlog return (e.g. retiring the now-dead
`dadaia specs hotfix open` verb).

**Archive** last: `ACTIVE.md` phase → `ARCHIVED`, then request
`git mv specs/releases/v0.6.0 specs/_archive/releases/v0.6.0` from software-engineer
(product-engineer has no shell), then repoint `ACTIVE.md`.

**Done criterion:** memory states current truth with no changelog section; `dadaia specs
doctor` exits 0; CLOSURE complete with the `## Dispositions` table and every evidence item
above; `ACTIVE.md` repointed; the `git mv` requested with the exact command.
