# SPEC — Release v0.7.0 — Test stewardship

**Status:** Aprovado
**Release ID:** v0.7.0
**Owner:** product-engineer
**Opened:** 2026-08-12
**Branch:** `feature/v0.7.0` (cut from `develop`)
**Consumes:** `specs/backlog/test-stewardship-standardization.md` (single picked entry, in
full — all three intents)
**Grill:** `specs/releases/v0.7.0/GRILL.md` — operator Q&A of 2026-08-12, binding
**Approval basis:** operator ruling of 2026-08-12 (D1–D4) + the grill record above.
Approved at authoring; the definition trio is reviewed at milestone (a) per the
`dadaia-gitflow` contract before `develop` is pushed.

---

## 1. Problem and context

The operator's hardest recurring problem with AI agents is not that they fail to write
tests — it is that they **never curate them**. They pile up, duplicate, generate
tautologies, leave eternal scaffolds and tombstone tests, and couple tests to
implementation. The suite stops being a signal and becomes a tax that also freezes the
architecture.

The workspace has a partial answer scattered across nine surfaces, and it contradicts
itself. Measured on 2026-08-12 by three read-only scans (GRILL §1–§2):

| # | Observed state | Evidence |
|---|---|---|
| O1 | **0 of 26** LARGE test files carry a named owner (~84 LARGE tests) | scan 2, ownership axis — RED |
| O2 | No quarantine, no rerun recording; Playwright CI runs `retries: 1` with a `list` reporter, so a **pass-on-retry is silently green**; the only flake tracking is the reactive bug ledger (5 resolved flake bugs) | `tests/e2e/panel/playwright.config.ts:35,47-49` — RED |
| O3 | `pytest-timeout` is **not installed**; there is no per-test ceiling anywhere, and the local pre-push preflight is unbounded | `pyproject.toml`; `features/ci_preflight/service.py:257` |
| O4 | 34 skips, **0** carrying a plan reference; one journey spec is permanently skipped locally | scan 2, skips axis |
| O5 | `--durations` runs only on the integration/e2e jobs; there is no wall-clock budget and no ratchet | `.github/workflows/ci.yml:251,275` |
| O6 | `tests/README.md` is a near-verbatim duplicate of `tests/AGENTS.md` — a live "no fact twice" violation | both files, Layers/No-Slop sections |
| O7 | `qa-engineer`'s frontmatter grants `tests/**`; its body forbids unit and integration tests | `public/agents/qa-engineer.md:48-52` vs `:63` |
| O8 | The coverage doctrine is split **four** ways, from "80 % minimum" to "percentage means nothing" to a ≥90 %-line-coverage audit rubric | scaffold `constitution.md:44`; `qa-engineer.md:169`; `drift-detection/SKILL.md:175-182`; `software-engineer.md:176` |
| O9 | `dadaia-release-closure` has no test section at all, and `:184` forbids the closer touching tests — demotion-at-closure has nowhere to land | `public/skills/dadaia-release-closure/SKILL.md:184` |
| O10 | The scaffold constitution carries **zero** test doctrine; the consumer memory template is 4 PT-BR bullets last touched 2026-01-01 | `public/scaffold/constitution.md`, `public/scaffold/memory/quality-assurance.md` |
| O11 | `ci_preflight` excludes `tests/performance`, a directory that no longer exists, and a unit test pins the dead flag | `features/ci_preflight/service.py:257`; `tests/unit/features/ci_preflight/test_service.py:28,34` |
| O12 | Memory is stale: ~2,100 tests claimed vs ~2,399 measured; `pytest-xdist`/`pytest-randomly` absent from the tech stack although CI runs `-n auto` | `quality-assurance.md:43`; `tech-stack.md:21` vs `ci.yml:144` |

O1–O5 are the mechanical gap. O6–O10 are the doctrine gap: the rules exist, in the wrong
number of places, saying different things. O11–O12 are the truth gap.

Under 10 % of test *files* are actually defective (scan 1). **The defect is governance, not
the suite** — which is exactly why this release ships doctrine and enforcement, and the
companion entry `test-suite-remediation-stewardship` applies it afterwards.

---

## 2. Objective

Give the workspace — and every consumer workspace it scaffolds — **one** test lifecycle
contract: a test declares its intent and its size at birth, is admitted only if it adds real
detection, is demoted at closure, is pruned by a steward's verdict with evidence, and is
never allowed to rot silently in a skip, a quarantine or an untracked flake. State it once
at law level, explain it once in a universal skill, land it once in the consumer scaffold,
and enforce the mechanically enforceable subset so the contract survives a discipline lapse.

---

## 3. Scope

### FR1 — New universal skill `dadaia-test-stewardship`: the single operational home

Create `dadaia_workspace/public/skills/dadaia-test-stewardship/SKILL.md` as a **universal**
skill — read natively by every entry harness, no per-harness derivation, no
`public/entities/registry.json` entry (the `dadaia-gitflow` precedent). It is the only place
the doctrine is explained operationally, and it is invoked whenever a test is created,
reviewed, demoted or pruned.

Mandatory content, organized as the source report's groups A–H:

1. **A — Intent taxonomy.** CONTRACT (permanent, asserts an AC or a bug), SENTINEL
   (permanent, the single integration test of a seam), SCAFFOLD (temporary, expires with its
   task/release), QUARANTINE (flaky under investigation). Declared in the module docstring as
   `Intent: <KIND> — <AC id | bug-id | task-id>` (GRILL P3). **An undeclared test is
   SCAFFOLD** — the default is to die, not to stay.
2. **B — Admission filter.** A new test enters the permanent suite only if it (i) compiles
   and runs, (ii) is deterministic, (iii) adds real detection — covers uncovered behavior
   **or** kills a mutant no current test kills. Prohibited: change-detector tests,
   tautologies (expected value computed by re-running the code under test), reflex-regenerated
   snapshots.
3. **C — Size tiers.** SMALL = `tests/unit` + `tests/contract`; MEDIUM = `tests/integration`;
   LARGE = `tests/e2e` (Python journeys + browser). Assert at the cheapest tier that detects
   the failure; a larger tier requires a written justification in the test. Every LARGE
   carries a named owner.
4. **D — Demotion.** At task/release closure each LARGE that validated a feature either
   yields or names (`file:line`) equivalent SMALL/MEDIUM coverage, and is then deleted or
   kept as the **single SENTINEL** of its seam. Deleting coverage without the map is
   cheating; deleting it with the map is engineering.
5. **E — Deletion criteria (a–f)** and the **tombstone ban**: a test whose central assertion
   is the *absence* of something removed validates a historical event, not a live behavior.
   Plus the separation of powers: the implementer never prunes to go green.
6. **F — Flake and quarantine pipeline.** Flaky → out of the critical path immediately +
   a registered bug, in the same act. Escalation 30 d → `disabled`; 30 clean days →
   restored; `disabled` + 1 release without a plan → deleted. Diagnostic reruns bounded at 3.
7. **G — Artifact hygiene.** Failure-gated capture by default; outputs outside the repo;
   probes/generators/one-off release scripts are SCAFFOLD.
8. **H — Health, cadence and measurement.** Three always-visible metrics (flake rate,
   wall-clock trend, failure→defect ratio); the full audit fires on a **trigger**
   (wall-clock +25 % without equivalent new behavior, flake over ceiling, LARGE over cap,
   quarantine full), never on a calendar; mutation testing 1×/release as the judge of
   detection value.
9. **A §10 parameter table**, carried as **declared adjustable defaults** (D3's package),
   with an explicit statement that a consumer workspace re-parameterizes without forking the
   doctrine.
10. **Decision tables**: the S-16 deletion criteria as a table; the flaky flow F as a table;
    a tombstone/SCAFFOLD/quarantine disposition table an agent can execute without prose.

**Acceptance**

- A1.1 The skill exists at the canonical path with valid frontmatter and is projected to
  `.claude/skills/`, `.agents/skills/`, `.codex/` and `.kimi-code/` by
  `dadaia public install --target all`; `dadaia public doctor` reports `[ok] public-privacy`
  and zero drift.
- A1.2 All eight groups A–H are present as named sections, plus the parameter table and at
  least three decision tables. No group is represented by a single sentence.
- A1.3 The parameter table carries all seven D3 values verbatim, each labelled as an
  adjustable default, and states the abstract LARGE default (12–15/module) **and** this
  repo's value (30) as separate facts.
- A1.4 The skill is **≤ 250 lines**. It is a protocol with decision tables, not an essay.
- A1.5 **No statement in the skill is copied verbatim from `DADAIA.md` §6.** The law states;
  the skill operates. Verified by a reviewer diff read.

### FR2 — `DADAIA.md` §6: the five-point increment, the scoping sentence, the carve-out

Edit **only** `dadaia_workspace/public/data/DADAIA.md` (the four projections are `0444` and
PROTECTED). §6 (Quality) gains a minimal test-lifecycle block stating, once each:

1. Every test declares its **intent** and its **size** at birth; an undeclared test is
   SCAFFOLD and expires.
2. **Demotion is a step of release closure** — each LARGE that validated a feature yields or
   names cheaper equivalent coverage, then is deleted or kept as the seam's single SENTINEL.
3. **The implementer never prunes to go green.** Deleting, skipping or disabling a test is a
   `qa-engineer` verdict carrying `file:line` evidence, executed by `software-engineer`.
4. **Tombstone tests and expired SCAFFOLD are slop.**
5. **Test-artifact capture is failure-gated** (where artifacts are written is already §4 —
   do not restate it).

Plus exactly two sentences elsewhere:

- **Scoping sentence** — the never-delete law of §5 covers **bugs and backlog only**; tests
  are prunable under the stewardship criteria. Without it, §5 reads as a blanket ban and the
  doctrine contradicts the law.
- **Quarantine carve-out**, inside *Push green* — a `quarantine`-marked test is outside the
  gating selectors **by design**; it requires a registered bug and expires. A green run with
  quarantined tests is green; an **unregistered pass-on-retry is a failure**. Without it,
  quarantine reads as a green-with-exclusions violation.

Everything operational defers to FR1's skill.

**Acceptance**

- A2.1 §6 states all five points and both sentences; each appears **exactly once** in the
  file (reviewer diff read, not grep alone).
- A2.2 Always-on token count of `DADAIA.md` grows by **≤ +400 tokens** over its pre-release
  measurement. Both numbers recorded in CLOSURE regardless of outcome.
- A2.3 The four projections (workspace root, `.claude/rules/`, `.codex/`, `.kimi-code/`) are
  byte-identical to source and mode `0444` after re-projection; `dadaia public doctor` green.
- A2.4 No operational detail leaks into the law: the law names no timeout value, no
  quarantine cap, no flake percentage, no marker name. Those live in FR1 and FR5.
- A2.5 A grep for the never-delete law returns exactly one statement, now scoped, and no
  surface in `public/` reads it as covering tests.

### FR3 — Consumer surface: constitution article, `tests/AGENTS.md` template, memory template

The doctrine must reach a workspace that this library scaffolds, not just this repo.

1. **`public/scaffold/constitution.md` — new numbered article §8 "Disciplina de Testes"**
   (GRILL P1; free slots were 8/10/12). Law-level, PT-BR to match the file, ≤ 12 lines:
   intent + size declared at birth; admission requires real detection; demotion at closure;
   pruning is a steward verdict, never the implementer's; tombstone/expired-SCAFFOLD are
   slop; artifacts failure-gated. It **points at** `dadaia-test-stewardship` for the
   protocol and states that the numeric parameters are project-adjustable.
2. **New public template `dadaia_workspace/public/templates/tests-AGENTS.md`** — the scoped
   rule file a consumer repo receives, structured as FR4's rewritten `tests/AGENTS.md` but
   parameterized (placeholders for the tier timeouts, the LARGE cap and the wall-clock
   baseline) and with no dadaia-workspace-specific path or number.
3. **Wire the template into repo scaffolding** — `features/spec_context/service.py`, at the
   existing `templates/repo-AGENTS.md` seam (`:387-390`): copy to `<repo>/tests/AGENTS.md`
   **only when `<repo>/tests/` exists and `<repo>/tests/AGENTS.md` does not** (GRILL P2).
   Never create a `tests/` directory.
4. **`public/scaffold/memory/quality-assurance.md`** — doctrine sync: the consumer memory
   template gains the layer→size mapping and a pointer to the skill and to constitution §8.
   It receives a **pointer, not a copy** (C10).

**Acceptance**

- A3.1 `public/scaffold/constitution.md` contains a `## 8. Disciplina de Testes` article;
  the section-number set becomes {1..9, 11, 13, 14} with no duplicate and no renumbering of
  any existing section.
- A3.2 Every `constitution §N` citation across `public/agents/**` and `public/skills/**`
  still resolves after the edit (the v0.6.0 A6.2 check re-run: extract cited §N, intersect
  with the scaffold's section set, expect an empty difference).
- A3.3 `public/templates/tests-AGENTS.md` exists, contains **zero** dadaia-workspace-specific
  literals (no `dadaia_workspace`, no `2:38`, no `30`-as-this-repo's-cap) — parameters appear
  as placeholders with the abstract defaults; `dadaia public doctor` reports
  `[ok] public-privacy`.
- A3.4 Contract/unit tests prove the scaffolding wiring: repo **with** `tests/` and no
  `tests/AGENTS.md` → file created from the template; repo with an **existing**
  `tests/AGENTS.md` → untouched (byte-identical); repo **without** `tests/` → no directory
  created, no file written. RED before GREEN.
- A3.5 `public/scaffold/memory/quality-assurance.md` carries the mapping + both pointers and
  no copy of the protocol; its frontmatter `last_updated` is refreshed.

### FR4 — Single-home edits per the conflict map (C1–C12): edit, never append

Every concept lands in exactly one home; every other surface loses it or points at it.

| Surface | Change | Conflict |
|---|---|---|
| `tests/AGENTS.md` | **"Good Test Standard" rewritten** as the intent taxonomy + admission filter + the deletion criteria; the existing tombstone bullet **extended in place** (S-17's full form: removed feature returns 404, module became a stub, directory/repo was removed, old migration no longer exists); a tier table with the timeout values and the LARGE-owner rule; the two new markers documented | C1, C3, C5 |
| `tests/README.md` | **Collapsed to `## Commands` + one pointer line** to `tests/AGENTS.md`. Its Layers and No-Slop-Policy sections are **deleted**, not summarized | C11 |
| `public/agents/qa-engineer.md` | Steward duties **verdict-only**: issues delete/demote/quarantine verdicts carrying S-16 `file:line` evidence; never executes the pruning commit. Frontmatter `write_allowlist` narrowed from `tests/**` to `tests/e2e/**` + `specs/releases/**/ALPHA-*-QA.md` + reports + handoff (P8). Coverage stance aligned (C13) | C9, C12, C13 |
| `public/agents/software-engineer.md` | One note: **executes** qa-engineer curation verdicts, with the verdict's evidence quoted in the commit message; never prunes on its own initiative. Slop-test discipline points at `tests/AGENTS.md` instead of restating admission rules. Coverage stance aligned (C13) | C9, C3, C13 |
| `public/skills/dadaia-release-closure/SKILL.md` | **New block**: demotion + disposition at closure — the S-15 map (deleted LARGE → the cheaper test that replaces it, `file:line`), quarantine/SCAFFOLD expiry sweep, and where each lands in `CLOSURE.md`. `:184` **amended**: the closer does not *write* tests; it **records dispositions** | C4 |
| `public/skills/drift-detection/SKILL.md` | **Dimension E rewritten off line coverage** onto detection quality: intent declared, demotion performed, flake within ceiling, quarantine within cap and not expired, LARGE owned. Line coverage appears only as the CI floor, never as a score anchor | C8, C13 |
| `public/skills/project-orchestration/SKILL.md` | **Citation only** — the review cadence references `dadaia-test-stewardship` for the curation step. No doctrine text added | C-map |

**Acceptance**

- A4.1 **Relocation grep clean.** For each of the taxonomy terms (`SENTINEL`, `SCAFFOLD`,
  `QUARANTINE`, `tombstone`, `demotion`), every hit under `dadaia_workspace/public/`,
  `tests/AGENTS.md` and `tests/README.md` resolves to (i) `dadaia-test-stewardship`,
  (ii) the `DADAIA.md` §6 law statement, (iii) `tests/AGENTS.md`, or (iv) a **reference** to
  one of those. Any fifth kind of hit is a stop condition. Run twice — by the author and
  independently by QA.
- A4.2 `tests/README.md` contains a `## Commands` section, one pointer line, and **nothing
  else**; the strings deleted from it exist in `tests/AGENTS.md`.
- A4.3 `qa-engineer.md`'s frontmatter allowlist contains no `tests/**` wildcard; the body and
  the frontmatter agree on every path (diff-read by `ai-engineer`). **No other agent's
  allowlist widens** as a side effect.
- A4.4 `dadaia-release-closure/SKILL.md:184`'s prohibition no longer forbids the closer from
  recording test dispositions, and the new block names the exact CLOSURE sections that carry
  the demotion map and the expiry sweep.
- A4.5 `drift-detection` Dimension E contains **no** line-coverage percentage in any score
  anchor.
- A4.6 `dadaia public doctor` and `dadaia specs doctor` both exit 0 after the pass.

### FR5 — Mechanical enforcement (TDD where testable)

The enforceable subset of D3. Every rule below lands as a RED test first.

1. **`pytest-timeout` dependency + tiered defaults.** Add the dev dependency; in
   `tests/conftest.py`, extend the existing `pytest_collection_modifyitems`
   (`:118-141`, the `_PATH_MARKERS` table) to apply `pytest.mark.timeout(N)` by layer —
   unit **10 s** / contract **30 s** / integration **60 s** / e2e **120 s** — **only when the
   test does not already declare an explicit `timeout` marker**. An explicit marker always
   wins; a test that needs more time is mis-tiered, and the tier is what gets fixed.
2. **Two new markers, six surfaces, one atomic change (M1).** Add `flaky` and `quarantine`
   to: `pyproject.toml` `markers`; `tests/conftest.py` (`quarantine` requires a bug id —
   a collection-time error otherwise); `tests/AGENTS.md`; `specs/memory/tech-stack.md`;
   the `.github/workflows/ci.yml` `-m` selectors; and
   `features/ci_preflight/service.py`'s base args. **Every gating selector excludes
   `quarantine`.**
3. **Playwright flake becomes loud (P7).** Record retry status in CI (JSON reporter written
   outside the repo alongside `list`) and add a step that fails the job on a
   `passed`-after-`retry > 0` result **unless** that test is registered — quarantined with a
   bug id. `retries: 1` stays; what changes is that the retry is no longer invisible.
4. **`--durations` + the budget ratchet (P6).** Add `--durations=25` to the unit job and the
   unit+contract coverage job; set each pytest job's `timeout-minutes` to ≈1.5× the frozen
   baseline (preflight quick 2:38, preflight full ~5:30, panel E2E 1:10) so the ceiling is a
   reviewable diff. Raising one requires a justification recorded in CLOSURE.
5. **Retire the dead `--ignore=tests/performance`** in `features/ci_preflight/service.py:257`
   and its pin in `tests/unit/features/ci_preflight/test_service.py:28,34` — the directory
   does not exist. Both files are in the same write set; a dead flag removed without its pin
   is a red suite.
6. **Heading allowlist (M2).** Append `Flake Policy` and `Test Health` to
   `specs/memory/.heading-allowlist`, and add the two headings that are already live but
   un-allowlisted (`Root Cause, Always`, `Satisfiable Diagnostics`).
7. **LARGE cap: measured, WARN-only (P5).** The cap is declared in `tests/AGENTS.md` and in
   the skill and is **reported**, not enforced red, in this release. Turning it into a
   failure is the companion release's step, once the count is achievable.

**Acceptance**

- A5.1 A unit test asserts the tier→timeout mapping for all four layers **and** that an
  explicit `@pytest.mark.timeout(N)` is not overridden. RED evidence captured pre-fix.
- A5.2 A test asserts that a `quarantine`-marked test without a bug id fails at collection
  with an actionable message naming the required form.
- A5.3 All six marker surfaces list `flaky` and `quarantine`; a contract test pins the
  marker set of `pyproject.toml` against `tests/conftest.py`'s known markers so the six
  cannot drift apart silently again.
- A5.4 Every gating selector (`ci.yml` pytest jobs + `ci_preflight`) excludes `quarantine`;
  demonstrated by a quarantined sample test that runs in an explicit `-m quarantine`
  invocation and does **not** run in the gating ones.
- A5.5 An unregistered pass-on-retry **fails** the panel E2E job — demonstrated once on this
  branch with a deliberately flaky throwaway spec, output recorded in CLOSURE, spec removed
  in the same task.
- A5.6 `--ignore=tests/performance` appears nowhere in `dadaia_workspace/` or `tests/`; the
  ci_preflight unit test passes with the flag gone.
- A5.7 `specs/memory/.heading-allowlist` contains the four headings; `dadaia specs doctor`
  exits 0.
- A5.8 Full quality ladder green: `pytest -p no:cacheprovider -q`, `ruff format --check`,
  `ruff check`, `mypy --strict`, `lint-imports --config setup.cfg --no-cache`.

### FR6 — Memory truth

`specs/memory/` describes the product as it is **after** this release. Written in the
CLOSURE phase (the memory path class is phase-gated).

- `specs/memory/quality-assurance.md`:
  - **new h2 `Flake Policy`** — quarantine markers and caps, the escalation ladder, the
    registered-bug requirement, the push-green carve-out;
  - **new h2 `Test Health`** — the three health metrics, the trigger-based audit, the
    mutation cadence, the frozen wall-clock baselines;
  - **`Layers` gains the layer→size mapping** (SMALL = unit+contract, MEDIUM = integration,
    LARGE = e2e) and the intent taxonomy **mapping only** — the taxonomy prose stays in
    `tests/AGENTS.md` (C1);
  - **`CI` gains** the tiered timeouts, the `quarantine` exclusion, `--durations`, and the
    `timeout-minutes` ceilings;
  - stale facts refreshed: the test count (~2,100 → the measured figure at closure).
- `specs/memory/tech-stack.md`: `pytest-timeout` added; `pytest-xdist` and `pytest-randomly`
  added (they are already in use via `-n auto`); the marker list updated to include `flaky`
  and `quarantine`.
- `specs/memory/product/distribution/public-asset-distribution.md`: the universal-skill
  roster gains `dadaia-test-stewardship`; the template roster gains `tests-AGENTS.md`.
- `specs/memory/architecture.md`: **expected minor** — the `spec_context` `alive()` scaffold
  inventory gains the `tests/AGENTS.md` copy. Stated explicitly either way.
- `specs/memory/product/{index.md,catalog.json}`: **regenerated, never hand-edited**, if any
  atom's `tldr`/`summary` moved.

**Acceptance**

- A6.1 Both new h2s exist, are in the heading allowlist, and contain **no changelog
  narrative** ("we used to…"); `dadaia specs doctor` exits 0.
- A6.2 Every number in memory matches a number that is actually in force (timeouts, caps,
  ceilings, baselines, test count) — cross-checked against `pyproject.toml`,
  `tests/conftest.py`, `ci.yml` and `tests/AGENTS.md` by QA, not by the author alone.
- A6.3 `tech-stack.md` lists `pytest-timeout`, `pytest-xdist`, `pytest-randomly` and the full
  marker set; the claim is verifiable against `pyproject.toml`.
- A6.4 No memory atom restates the protocol — each points at `dadaia-test-stewardship`
  (the "reference, never restate" invariant, A4.1's grep covers it).

### FR7 — Coverage-doctrine reconciliation (C13): one stance, four edits

The workspace currently says four different things about coverage. It will say one:

> **The 80 % floor on `unit or contract` remains a CI gate. Coverage is a by-product metric
> of real tests — never an acceptance target, never a reason to write a test, and never a
> score anchor for audit. Detection quality is judged by behavior and by mutation, not by
> lines executed.**

Edits (each site is corrected in place — no new paragraph anywhere):

| Site | Current | Becomes |
|---|---|---|
| `public/scaffold/constitution.md:44` | "Cobertura mínima: **80 %** para código novo." | The floor as a **CI gate**, explicitly labelled a by-product metric, pointing at §8 |
| `public/agents/qa-engineer.md:169` | "Coverage percentage means nothing if the tests don't catch real regressions." | The single stance, phrased as the rejection criterion it belongs to |
| `public/skills/drift-detection/SKILL.md:175-182` | Line-coverage score anchors (≥90 % = 10 … <50 % = 1) | Detection-quality anchors (FR4) — line coverage appears only as "the CI floor holds" |
| `public/agents/software-engineer.md:176` | "Coverage is a by-product of real tests, never a target you fabricate tests to hit." | Kept as the canonical phrasing; the other three align **to it** |

`public/agents/code-reviewer.md:144` (Axis 3) is checked for a numeric target; it currently
states none and is left unchanged unless the check finds one.

**Acceptance**

- A7.1 A grep for coverage statements across `dadaia_workspace/public/` returns exactly four
  sites, and all four express the same stance; no fifth site introduces a different one.
- A7.2 No score anchor anywhere in `public/` grades a project by line-coverage percentage.
- A7.3 The 80 % CI gate itself is **unchanged** — `ci.yml:174`'s `--cov-fail-under=80` is
  byte-identical after this release. This is a doctrine reconciliation, not a gate change.

---

## 4. Out of scope (non-goals)

- **No suite remediation.** The 6 tombstones, the tautology/change-detector families, the
  0/26 LARGE ownership, the orphan `check_skill_orphans.py`, the permanently-skipped journey
  spec, the duplicated panel readiness helpers and the artifact residue are the companion
  entry `specs/backlog/test-suite-remediation-stewardship.md`. It stays `candidate` and is
  **not** dispositioned by this release. Named offenders appear in GRILL §2 as justification
  only.
- **No mutation-testing tool integration.** The **cadence** (1×/release, off the push path)
  is declared; choosing and wiring the tool (mutmut / cosmic-ray / other) is its own task and
  is returned to the backlog.
- **No hard LARGE-cap enforcement.** The cap is declared and measured; it becomes a failure
  in the companion release, when the count can satisfy it (P5, Satisfiable Diagnostics).
- **No mechanical enforcement of the intent docstring.** 384 existing files are
  non-compliant; a check that no legal action can currently satisfy is a defect in the check.
  Declared as law now, enforced in the companion release (P9) — backlog return.
- **No consumer migration.** Existing consumer workspaces are untouched. The template and the
  constitution article reach a workspace at scaffold time; retrofitting an already-scaffolded
  consumer is not written here.
- **No marker-taxonomy expansion beyond two.** `flaky` and `quarantine` only. Every added
  marker costs six coordinated surfaces.
- **No change to the 80 % coverage gate, to `retries: 1`, or to the `pre_gate` path-class
  model.** FR7 reconciles what the workspace *says* about coverage; FR5 makes a retry
  *visible*. Neither loosens a gate.
- **No new lock, lease or blocking mechanism.** The NO-LOCKS DOCTRINE stands.

---

## 5. Dependencies and risks

**Dependencies.** One new dev dependency: `pytest-timeout`. `pytest-xdist` and
`pytest-randomly` are *documented*, not added — they are already in use. `DADAIA.md` is
PROTECTED and projected `0444`: the source is `dadaia_workspace/public/data/DADAIA.md` and
the chain is `dadaia public stage` → `dadaia public install --target all` →
`dadaia public doctor`.

**Ordering (binding).** FR1 lands **first** — nothing may defer to a skill that does not
exist. FR2 follows (the law delegates to it). FR3 follows FR2 (agents cite the new
constitution §N; the citation must resolve). FR4 follows FR3. FR5 needs only FR1 and may run
parallel to FR4 (disjoint write sets: package/CI code vs `public/**` + `tests/*.md` text).
FR6 runs in the CLOSURE phase. FR7's edits ride inside FR3 and FR4's files — no independent
task.

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Marker-set drift** — six surfaces must move together (M1); one missed surface silently mis-selects the suite | A5.3 pins the marker set with a contract test comparing `pyproject.toml` to `conftest.py`; the six surfaces are one atomic task with an explicit write set naming all six |
| R2 | **Quarantine reads as "green with exclusions"** — a reader concludes the push-green law was loosened | The carve-out sentence is mandatory (FR2) and is paired with P7: an *unregistered* flake **fails**. Quarantine costs a registered bug and expires; it is stricter than silence, not laxer |
| R3 | **`DADAIA.md` token cap** — the always-on prefix is already ~3.5 k against a ≤3 k aspiration | A2.2 caps growth at +400 tokens with before/after in CLOSURE; A2.4 forbids any operational number in the law |
| R4 | **Agent truncation** — this release's tasks are long and text-heavy; a sub-agent that runs out of turns leaves a half-edited governance surface | Every dispatch carries an economy directive: read only the named files, edit in place, no exploratory greps beyond the named acceptance checks. Tasks are sized to one surface family each; T-070-04 is explicitly the largest and may be split at execution time without a spec change |
| R5 | **Tiered timeouts break a legitimately slow test** at 10 s/30 s | The mapping never overrides an explicit `@pytest.mark.timeout` (A5.1). The first full-suite run under timeouts is the evidence; any test that trips is either mis-tiered (fix the tier) or genuinely slow (explicit marker + justification) — never a raised default |
| R6 | **The dead `--ignore=tests/performance` is removed without its pin**, reddening the suite | Both files are in the same write set (FR5.5) and named in the task |
| R7 | **The relocation pass deletes a rule instead of relocating it** | A4.1's grep proves relocation, not deletion; A4.2 requires the strings removed from `tests/README.md` to exist in `tests/AGENTS.md`; QA re-runs the grep independently |
| R8 | **The constitution renumbering breaks 5+ agents' `§N` citations** | A3.2 re-runs v0.6.0's A6.2 check: no existing section is renumbered, only §8 is inserted |
| R9 | **The flaky-detection CI step becomes flaky itself** (parsing a report that is absent on a clean run) | The step must treat "no JSON report" as a hard error, not a pass — asserted in A5.5's demonstration |
| R10 | **A consumer repo without `tests/` gets a directory created by the scaffolder** | A3.4 pins all three cases, including the no-`tests/` case where nothing is written |
| R11 | **The doctrine ships and is never applied**, becoming shelf-ware | The companion backlog entry is named in CLOSURE with its blocking dependency discharged, and the release's own CI now measures the LARGE cap, the flake rate and the durations — the numbers become visible the day this ships |

---

## 6. Memory atoms affected at closure

- `specs/memory/quality-assurance.md` — **primary.** New `Flake Policy` and `Test Health`
  h2s; `Layers` gains the layer→size mapping; `CI` gains timeouts, quarantine exclusion,
  durations and ceilings; the stale test count is refreshed.
- `specs/memory/tech-stack.md` — `pytest-timeout` added; `pytest-xdist`/`pytest-randomly`
  documented; marker list updated.
- `specs/memory/product/distribution/public-asset-distribution.md` — universal-skill roster
  gains `dadaia-test-stewardship`; template roster gains `tests-AGENTS.md`.
- `specs/memory/architecture.md` — **expected minor**: `spec_context` `alive()` scaffold
  inventory gains the conditional `tests/AGENTS.md` copy. Stated explicitly either way.
- `specs/memory/product/{index.md,catalog.json}` — **regenerated, never hand-edited**, if any
  atom's `tldr`/`summary` moved.

Memory describes the product after this release. The before/after of the doctrine lives in
CLOSURE and in this SPEC, never in an atom.

---

## 7. Acceptance criteria (release-level)

1. **All seven FRs' sub-criteria (A1.1–A7.3) met**, each with its stated evidence in CLOSURE.
   A criterion asserted without evidence is not met.
2. **One home.** The doctrine is explained operationally in exactly one file
   (`dadaia-test-stewardship/SKILL.md`), stated at law level in exactly one place
   (`DADAIA.md` §6), carried to consumers in exactly two (scaffold constitution §8 +
   `templates/tests-AGENTS.md`), and referenced everywhere else — proven by A4.1's grep,
   run twice.
3. **The four-way coverage split is gone**: all coverage statements in `public/` express one
   stance, and no audit rubric grades by line percentage (A7.1, A7.2).
4. **Mechanically enforced**: tiered per-test timeouts active; `quarantine` excluded from
   every gating selector and requiring a bug id; an unregistered pass-on-retry demonstrated
   to **fail** the panel E2E job; `--durations` and the `timeout-minutes` ceilings in place;
   the dead `--ignore=tests/performance` gone.
5. **The consumer gets it**: a scaffolded repo with a `tests/` directory receives
   `tests/AGENTS.md`, and the scaffold constitution carries §8 — both proven by test, not by
   inspection.
6. **Green everywhere**: `pytest -p no:cacheprovider -q` (full suite, under the new
   timeouts); `ruff format --check`; `ruff check`; `mypy --strict`;
   `lint-imports --config setup.cfg --no-cache`; `dadaia doctor`, `dadaia specs doctor`,
   `dadaia public doctor` all exit 0 on this live instance.
7. **The release ships by its own rules** (`dadaia-gitflow`): milestone (a) — definition trio
   `Aprovado`, merged to local `develop`, diff-based security APPROVE of
   `origin/develop..develop`, `develop` pushed; milestone (b) — same sequence at ship, then
   PR `develop` → `main`, every CI job green, merge. Any deviation is a finding, not a
   footnote.
8. **CLOSURE carries** the `## Dispositions` table flipping
   `specs/backlog/test-stewardship-standardization.md` to **`DELIVERED — v0.7.0`** with each
   of its three intents mapped to the FR that consumed it; an explicit statement that
   `specs/backlog/test-suite-remediation-stewardship.md` remains `candidate` and is
   **unblocked** by this release; the `DADAIA.md` token before/after pair; the RED-before-GREEN
   evidence for FR5 and FR3.3; the flake-detection demonstration output; the measured baseline
   numbers (test count, LARGE count, wall-clock) as the frozen reference; and the backlog
   returns (mutation tool choice, intent-docstring enforcement, and any orphan surface found).
