# TASKS — Release v0.4.2 — residual-convergence

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-16 (resolva todos — goal directive)
**Release ID:** v0.4.2
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.2/SPEC.md`
**Source PLAN:** `specs/releases/v0.4.2/PLAN.md`
**Branch:** `feature/0.4.2` (cut from `develop` at `36412845`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release; one implementation increment closed by T-042-17 (the
`alpha-1` close), then the pre-PR review, then closure, then ship.

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Task order — the review-before-archive canon (FR5 / ADR R3), dogfooded

```
implementation (T-042-03…16) → QA alpha-1 (T-042-17) → CODE REVIEW (T-042-18)
    → memory (T-042-19) → CLOSURE + archive (T-042-20) → ship (T-042-21)
```

The six-axis review is its **own task and runs before the archive move**, so any finding lands
on a thawed tree. Only ship steps follow the archive. This ordering is the canon FR5 writes
into the skills; this release is its first executor.

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]** or carrying a command is
  executed by the dispatcher, `software-engineer`, `ai-engineer` or `qa-engineer`.
  `product-engineer` authors text only.
- **Shell-less reservation obligation (FR5).** When the dispatcher relays work for a shell-less
  sub-agent, it commits that sub-agent's `[ ]`→`[-]` flip **before** relaying the next work
  item. Applies to T-042-19 and T-042-20.
- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN.** Every behavioural task writes its failing test first and observes it
  failing for the real reason.
- **Test intent at birth.** `Intent: CONTRACT — v0.4.2 <A-id>` or `Intent: SENTINEL — <seam>`.
  **Zero new e2e tests.**
- **Never prune to go green.** The only permitted deletions are T-042-03's recorded
  supersessions. Anything else needs a `qa-engineer` verdict with evidence.
- **Deletion beats addition (R5).** A task that can remove code removes it; net lines are
  expected to fall.
- **Lane discipline.** `ai-engineer` performs **every** skill/persona/projected-asset edit;
  `project-manager` performs any backlog-file mechanics after T-042-01; `product-engineer`
  writes only specs and memory. The one dual-owner task is T-042-19, sequenced inside one
  commit.
- **One `[-]` at a time.** No sanctioned parallel pair in this release — several tasks share
  `git_objects.py`, `document.py` or `dd-release-closure/SKILL.md`.
- **A group of completed work is one commit** — stage exactly the task's write set, never `-A`.
- **Reservation is observable.** Flip `[ ]`→`[-]` and commit `chore(tasks): start <id>` before
  the work (`dadaia-task-manager`).

## Acceptance and evidence map

| Task | Entry | Acceptance ids | Evidence |
|---|---|---|---|
| T-042-01 | — | — | definition commit sha; `ACTIVE.md` reads `IMPLEMENTATION` |
| T-042-02 | — | OD-3 (V12) | pushed `develop` sha + APPROVED security handoff + `bugs status` output |
| T-042-03 | #4 | A12.1–A12.5 | V6 zero-hit output, commit sha |
| T-042-04 | #38 | A1.1–A1.7 | V1 + V5 + V7 output, commit sha |
| T-042-05 | #42 | A11.1–A11.4 | V10 budget output, commit sha |
| T-042-06 | #10 | A14.1–A14.5 | V3 count before/after, commit sha |
| T-042-07 | #43 | A2.1, A2.2, A2.4, A2.5 (code half) | parity-test output, commit sha |
| T-042-08 | #39 | A4.1–A4.4 | V11 output + zero-diff `core/redaction.py` |
| T-042-09 | #40 | A7.1–A7.3 | tree-order fixture output, commit sha |
| T-042-10 | #41 | A8.1–A8.4 | RED-then-GREEN output, commit sha |
| T-042-11 | #24 (partial) | A10.1–A10.4 | fixture output + baseline diff |
| T-042-12 | #45 | A9.1–A9.4 | V9 output, commit sha |
| T-042-13 | #44 | A3.1, A3.2 | V1 + grep output |
| T-042-14 | #44, flat-release | A3.3, A3.4, A5.1, A5.2, A5.4 | V4 output + skill diff |
| T-042-15 | intake-signal-calibration | A6.1, A6.2 | V4 output + skill/persona diff |
| T-042-16 | #11 | A13.1, A13.2 | V13 capture + `CHANGELOG.md` diff |
| T-042-17 | all | every id + A15.1–A15.5 | `qa-engineer` APPROVED artifact |
| T-042-18 | all | A5.3 | `code-reviewer` APPROVED artifact on a **thawed** tree |
| T-042-19 | #43, #39, #40, #44, #11 | SPEC §5, A2.3 | memory diff; `specs doctor` green |
| T-042-20 | all picked | closure obligations, A6.3, A13.3 | `CLOSURE.md` under `_archive/` |
| T-042-21 | — | — | PR merged to `main`; CI green |

---

- [ ] **T-042-01 — [git] Commit the definition content on `feature/0.4.2`**

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-042-01): v0.4.2 definition — residual-convergence`

**Preconditions:** `GRILL.md`, `SPEC.md`, `PLAN.md`, `TASKS.md` authored and carrying
`**Status:** Aprovado`. Working tree on `feature/0.4.2`.

**Write set (staging only — content already authored by `product-engineer`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.4.2/{GRILL,SPEC,PLAN,TASKS}.md`,
`specs/backlog/BACKLOG.md` (purge-on-pick: 13 ACTIVE subsections removed, #24 rewritten to its
residual).

**Description:** Stage exactly those paths and commit — the pick and the SPEC ride one commit
(`DADAIA.md` §5). Set `ACTIVE.md` phase from `DEFINITION` to `IMPLEMENTATION` in the same
commit. The pre-commit backlog gate fires (backlog paths are staged) and must pass.

**Done criterion:** one commit containing exactly those paths; `ACTIVE.md` reads
`release: v0.4.2` / `phase: IMPLEMENTATION`; `dadaia backlog doctor` and `dadaia specs doctor`
clean.

**Parallelism:** none — first task.

---

- [ ] **T-042-02 — [git] Milestone (a): confirm the pick, merge, security review, push**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`

**Preconditions:** T-042-01 `[x]`.

**Write set:** git refs only (`develop`), plus the security-reviewer handoff under
`.dadaia/handoff/dadaia-workspace/` and the `bugs status` capture under
`.dadaia/tmp/<agent>/<YYYYMMDD>/`.

**Description:** First run **V12** — `dadaia bugs status` — and capture the output, confirming
the SPEC's zero-open-bugs claim (OD-3); a non-zero count stops the milestone and returns to
`product-engineer` for a pick amendment. Then, per `dadaia-gitflow` milestone (a), in order:
merge `feature/0.4.2` into local `develop`; run a **diff-based** `security-reviewer` review of
`origin/develop..develop`; push `develop`.

**Done criterion:** `bugs status` captured and consistent with SPEC §7; `develop` pushed;
APPROVED handoff covering the pushed delta; CI green.

**Parallelism:** none.

---

- [ ] **T-042-03 — FR12: delete the dead hotfix-release surface**

**Owner role:** software-engineer · **Commit:**
`refactor(T-042-03): delete the revoked hotfix-release scaffolding surface`

**Preconditions:** T-042-02 `[x]`.

**Write set:** `dadaia_workspace/cli/commands/specs.py` (drop `hotfix_app`, `hotfix_open` and
the `candidates.md` pre-condition block), `dadaia_workspace/features/specs/scaffolder.py`
(drop `scaffold_hotfix_release`, `_HOTFIX_TASKS_STUB`), delete
`dadaia_workspace/public/templates/release_hotfix.md.j2` and `closure_hotfix.md.j2`,
`tests/unit/features/specs/test_scaffolder.py` (hotfix cases),
`tests/unit/infrastructure/_golden/doctor_all_four_v0158.json` (regenerated, never hand-edited),
plus the refreshed projections.

**Description:** Deletion only — nothing is moved or reimplemented. `_render_template` stays
(other callers). `core/specs_version.py` and `features/specs/doctor_release.py` mention
hotfixes only in comments about branch names — leave them; that law is live.

**Recorded supersessions (no silent pruning):**

| Deleted test | Deleted subject | Replacement coverage |
|---|---|---|
| the hotfix cases in `tests/unit/features/specs/test_scaffolder.py` | `scaffold_hotfix_release` | none needed — behaviour removed, not moved |

**Done criterion:** A12.1–A12.5 hold; V6 zero-hit; `dadaia public doctor` green including
`[ok] public-privacy`; `dadaia ci preflight` green.

**Parallelism:** none.

---

- [ ] **T-042-04 — FR1: one backlog grammar seam, write-then-verify**

**Owner role:** software-engineer · **Commit:**
`refactor(T-042-04): the backlog writer shares the parser's grammar and verifies its own write`

**Preconditions:** T-042-03 `[x]`.

**Write set:** `dadaia_workspace/features/backlog/document.py` (promote the fence-aware
insertion helper to public API), the new writer home under `dadaia_workspace/features/backlog/`,
`dadaia_workspace/features/spec_artifacts/new_artifacts.py` (shrinks to `release_new`),
`dadaia_workspace/cli/commands/newartifacts.py` (import site),
`tests/unit/features/backlog/test_document.py`,
`tests/unit/features/spec_artifacts/test_new_artifacts.py`,
`tests/integration/cli/test_cli_newartifacts.py`.

**Description:** Per PLAN §4. RED first: a `BACKLOG.md` whose Description quotes a fenced
example containing `## LEDGER` must show the pre-fix writer splicing **into the fence**. Then
move the writer, take the insertion point from the parser's fence-aware structure, delete the
three private regexes, add write-then-verify, `fullmatch` and the redacted diagnostic. No new
`setup.cfg` import edge (A1.6).

**Done criterion:** A1.1–A1.7 hold; V5 + V7 clean; the v0.12.0 byte-diff and slug-uniqueness
tests pass unmodified in their new location.

**Parallelism:** none.

---

- [ ] **T-042-05 — FR11: bisect fence filter + CSafeLoader**

**Owner role:** software-engineer · **Commit:**
`perf(T-042-05): bisect the fence filter and use CSafeLoader when available`

**Preconditions:** T-042-04 `[x]` (same module).

**Write set:** `dadaia_workspace/features/backlog/document.py`,
`tests/unit/features/backlog/test_document.py`.

**Description:** Per PLAN §4. `_outside_fences` bisects over sorted fenced-range starts;
`load_document` selects `yaml.CSafeLoader` when importable. **No** second parse mode (D7). Add
the 140 KB budget regression with generous headroom and a fallback-loader test.

**Done criterion:** A11.1–A11.4 hold; every existing parser test passes unmodified.

**Parallelism:** none.

---

- [ ] **T-042-06 — FR14: SPEC-DOC-031 counts consumption, not conversation**

**Owner role:** software-engineer · **Commit:**
`fix(T-042-06): SPEC-DOC-031 keys on consumption-asserting evidence`

**Preconditions:** T-042-05 `[x]`.

**Write set:** `dadaia_workspace/features/specs/doctor_governance.py`,
`tests/unit/features/specs/test_doctor*.py` and the governance golden fixtures.

**Description:** Per PLAN §4. Capture `dadaia specs doctor`'s SPEC-DOC-031 count **before**
the change. Rewrite `_archive_consumption_hits` to read only the archived SPEC's
`**Consumes:**` declaration (with continuation lines) and the archived CLOSURE's
`## Dispositions` rows. Delete `_BACKLOG_RETURNS_HEADING_RE` and its branch. Id, message shape,
WARNING severity and the ACTIVE-iteration surface are unchanged. Capture the count **after**.

**Done criterion:** A14.1–A14.5 hold; the twelve documented false positives are gone; the
before/after counts are captured for CLOSURE.

**Parallelism:** none. **Blocks T-042-14** (the skill pass restates this check).

---

- [ ] **T-042-07 — FR2 (code half): the catalog computes `token_estimate`**

**Owner role:** software-engineer · **Commit:**
`refactor(T-042-07): compute token_estimate in the catalog; retire the drift check`

**Preconditions:** T-042-06 `[x]`.

**Write set:** `dadaia_workspace/features/specs/catalog.py`,
`dadaia_workspace/public/scripts/generate-memory-catalog.py`,
`dadaia_workspace/public/scripts/lint-memory-atoms.py`,
`dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json` (drop from
`required` only — `properties` waits for T-042-19),
`tests/integration/scripts/test_generate_memory_catalog.py`,
`tests/contract/cli/test_cli_memory_catalog.py`,
`tests/integration/scripts/test_lint_memory_atoms_cli.py`, plus refreshed projections.

**Description:** Per PLAN §4 and D5. The computation moves into the package and is used by
both generators; a parity test pins them to byte-identical output. The lint drift check and its
duplicate estimator are **deleted**. The frontmatter key stays valid-but-optional until the
closure half, so the tree is green in between (A2.5).

**Done criterion:** A2.1, A2.2, A2.4 hold; `specs doctor` green with the key still present.

**Parallelism:** none.

---

- [ ] **T-042-08 — FR4: the masker shares the detector's matchers**

**Owner role:** software-engineer · **Commit:**
`fix(T-042-08): gate masking predicate is the detector's own; refusals carry no raw path`

**Preconditions:** T-042-07 `[x]`.

**Write set:** `dadaia_workspace/features/chokepoints/denylist_scan.py` (export the matcher
factory), `dadaia_workspace/features/chokepoints/service.py` (`_PathMasker`, the git-failure
refusal branch), `dadaia_workspace/core/protocols/git_object_reader.py`
(`GitObjectReadError.path`), `dadaia_workspace/infrastructure/git_objects.py` (structured raise
sites), the existing chokepoints test modules.

**Description:** Per PLAN §4 and D3. `core/redaction.py` and `cli/redact.py` are **not**
edited — parity is achieved by sharing the detector's matchers, so the CLI stays byte-identical
by construction. RED first with the upper-cased/hyphenated path fixture.

**Done criterion:** A4.1–A4.4 hold; `git diff dadaia_workspace/core/redaction.py` is empty;
V11 green.

**Parallelism:** none.

---

- [ ] **T-042-09 — FR7: no amnesty for a multi-path blob (fail-closed)**

**Owner role:** software-engineer · **Commit:**
`fix(T-042-09): a blob reachable at more than one path receives no amnesty`

**Preconditions:** T-042-08 `[x]` (same adapter file).

**Write set:** `dadaia_workspace/infrastructure/git_objects.py`, the existing amnesty test
module.

**Description:** Per PLAN §4 and D4/R1. Compute the multi-path sha set from the `rev-list`
candidates and withhold `prior_text` for those shas. **The matcher is not touched** — verify by
diff. Add the tree-order-independence fixture (same content at two paths, both name orderings).

**Done criterion:** A7.1–A7.3 hold; every v0.11.0 amnesty test passes unmodified.

**Parallelism:** none.

---

- [ ] **T-042-10 — FR8: narrow the fail-soft width**

**Owner role:** software-engineer · **Commit:**
`fix(T-042-10): a scan-path degradation is typed or counted, never silent`

**Preconditions:** T-042-09 `[x]` (same adapter file).

**Write set:** `dadaia_workspace/infrastructure/git_objects.py`,
`dadaia_workspace/container.py` (registry-load degradation signal),
`dadaia_workspace/cli/commands/ci.py` (the one stderr note), the existing `git_objects` and
push-gate test modules.

**Description:** Per PLAN §4, three sub-items. RED first on a nonexistent oid and a tree sha.
The intentional EPIPE-after-cap close stays the only swallowed shape. A malformed registry
emits exactly one note and the scan proceeds.

**Done criterion:** A8.1–A8.4 hold.

**Parallelism:** none.

---

- [ ] **T-042-11 — FR10: privacy baseline v5 — the declared-support platforms**

**Owner role:** software-engineer · **Commit:**
`fix(T-042-11): baseline v5 covers macOS and Windows home paths`

**Preconditions:** T-042-10 `[x]`.

**Write set:** `dadaia_workspace/infrastructure/data/privacy_baseline.json`, the existing
privacy-baseline test module, `tests/integration/test_repo_self_scan.py`
(`_TESTS_SCOPE_BASELINE` rows for this task's own fixtures — listed in the commit message),
plus refreshed projections if the baseline is projected.

**Description:** Per PLAN §4, D9 and D10. Two new single-line patterns with placeholder
carve-outs, `version` → `5`, `_header.excludes` extended with both rationales and the `/root`
boundary. Fixtures use synthetic non-identifying names; every new `_TESTS_SCOPE_BASELINE` row
is enumerated in the commit message so QA can verify the delta exactly.

**Done criterion:** A10.1–A10.4 hold; `dadaia public doctor` green including
`[ok] public-privacy`.

**Parallelism:** none.

---

- [ ] **T-042-12 — FR9: the self-scan sentinel sees archive-authored blobs**

**Owner role:** software-engineer · **Commit:**
`test(T-042-12): scan archive paths whose blob is new at HEAD`

**Preconditions:** T-042-11 `[x]` (the baseline must be final before the delta is measured).

**Write set:** `tests/integration/test_repo_self_scan.py`.

**Description:** Per PLAN §4. Keep the archive prefixes excluded, then add back archive paths
whose blob sha is absent from `HEAD^`'s tree (one `git ls-tree -r HEAD^`). `HEAD^` unavailable
⇒ today's behaviour. Two fixtures in a temporary repo: a planted authored file (fails) and a
`git mv`'d file (passes).

**Done criterion:** A9.1–A9.4 hold; V9 green on this repo at HEAD.

**Parallelism:** none.

---

- [ ] **T-042-13 — FR3 (code half): leaf import and DEAD markers**

**Owner role:** software-engineer · **Commit:**
`refactor(T-042-13): export the YAML error formatter; repoint the DEAD markers`

**Preconditions:** T-042-12 `[x]`.

**Write set:** `dadaia_workspace/features/backlog/preview.py`,
`dadaia_workspace/features/backlog/document.py`,
`dadaia_workspace/features/telemetry/store/schema.py`, the affected test modules.

**Description:** `_format_yaml_error` becomes public API (or moves to a shared leaf) and
`document.py` imports a public name — no module imports a sibling leaf's underscore symbol. The
two telemetry DEAD markers stop pointing at the archived `backlog/candidates.md`.

**Done criterion:** A3.1, A3.2 hold.

**Parallelism:** none.

---

- [ ] **T-042-14 — FR3 (skills) + FR5: the shipped mechanism and the review-before-archive canon**

**Owner role:** ai-engineer · **Commit:**
`docs(T-042-14): skills state the shipped sweep and the review-before-archive order`

**Preconditions:** T-042-06 `[x]` (SPEC-DOC-031's semantics must be shipped before they are
restated) **and** T-042-13 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-release-closure/SKILL.md`,
`dadaia_workspace/public/skills/dd-release-definition/SKILL.md`,
`dadaia_workspace/public/skills/dd-release-implement/SKILL.md`,
`dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md`,
`dadaia_workspace/public/agents/product-engineer.md`, plus refreshed projections.

**Description:** Per SPEC FR3(1–3) and FR5. The disposition template row stops naming a
per-entry file; both skills state *adds a LEDGER line, removes the ACTIVE subsection*; the
SPEC-DOC-031 paraphrase matches what T-042-06 shipped; the archive-move measurement note is
folded in. The ordering canon (review → closure → archive → ship) is stated in
`dd-release-implement` §4 and `dd-release-closure`'s finalization paragraph; the shell-less
dispatcher reservation obligation is stated once in `dadaia-task-manager`. The PE persona's
file tree drops `candidates.md`. Then `stage` → `install --target all` → `doctor`.

**Done criterion:** A3.3, A3.4, A5.1, A5.2, A5.4 hold; no contradicting third statement remains
in `public/**`.

**Parallelism:** none — shares files with T-042-15.

---

- [ ] **T-042-15 — FR6: intake signal calibration**

**Owner role:** ai-engineer · **Commit:**
`docs(T-042-15): record-only observations terminate in CLOSURE; only defects reach intake`

**Preconditions:** T-042-14 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-release-closure/SKILL.md` (the
`## Intake candidates` contract + the new **Record-only observations** heading),
`dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md` (§5),
`dadaia_workspace/public/agents/{code-reviewer,security-reviewer,qa-engineer,project-auditor}.md`,
plus refreshed projections.

**Description:** Per SPEC FR6 and ADR R4. Three-way routing stated identically in every
surface: record everything (never-silent); record-only observations terminate in the CLOSURE
record or the reviewer handoff; only actionable defects (LOW+ with a concrete fix surface) are
compiled for operator adjudication. The personas keep their never-silent obligation explicit.

**Done criterion:** A6.1, A6.2 hold; `dadaia public doctor` green.

**Parallelism:** none.

---

- [ ] **T-042-16 — FR13: the CHANGELOG version-axis preamble**

**Owner role:** software-engineer · **Commit:**
`docs(T-042-16): reconcile the CHANGELOG to the single published version axis`

**Preconditions:** T-042-15 `[x]`.

**Write set:** `CHANGELOG.md`, plus the V13 capture under `.dadaia/tmp/<agent>/<YYYYMMDD>/`.

**Description:** Run **V13** — read the published version list for `dadaia-workspace` from the
package index — and capture it. Then insert one preamble block under the file header stating
which headers were minted internally and never published, mapping them to their internal
spec-release ids, and declaring one-section-per-published-version from `0.4.2` onward. **No
existing heading is renamed, renumbered or removed.** The `[0.4.2]` section itself is written
at T-042-20.

**Done criterion:** A13.1, A13.2 hold; `git diff CHANGELOG.md` shows only the added preamble.

**Parallelism:** none.

---

- [ ] **T-042-17 — `qa-engineer` review of the increment (alpha-1 close)**

**Owner role:** qa-engineer · **Commit:** review artifact committed to the branch
(`specs/releases/v0.4.2/ALPHA-1-QA.md`)

**Preconditions:** T-042-03…T-042-16 all `[x]`.

**Write set:** `specs/releases/v0.4.2/ALPHA-1-QA.md`, `.dadaia/handoff/dadaia-workspace/`,
`.dadaia/tmp/qa-engineer/<YYYYMMDD>/`.

**Description:** Verify the increment against SPEC FR1–FR15 acceptance id by id, running
PLAN §6's V1–V11 and capturing every command's output. Give particular weight to: the
detector-implies-masker fixture set (A4.1) and the zero-diff `core/redaction.py` (A4.3); the
tree-order-independence of the amnesty fixture (A7.1) and the unmodified matcher (A7.3); the
RED-for-the-real-reason evidence on the two FR8 cases (A8.1); the `_TESTS_SCOPE_BASELINE` delta
being **exactly** T-042-11's enumerated rows and nothing else (A10.3/D9); the SPEC-DOC-031
before/after counts (A14.4); and that no new `setup.cfg` import edge appeared (A1.6). Confirm
every added test declares intent and size at birth and that no test outside T-042-03's recorded
supersession was deleted, skipped or weakened. Apply the redaction-at-authoring doctrine to the
artifact, and route findings per the FR6 calibration this release ships.

**Done criterion:** APPROVED verdict enumerating every acceptance id, or REJECTED returning
named defects to the implementer.

**Parallelism:** none.

---

- [ ] **T-042-18 — `code-reviewer` six-axis review of the delta (BEFORE archive — R3)**

**Owner role:** code-reviewer · **Commit:** review artifact committed to the branch
(`specs/releases/v0.4.2/PRE-PR-REVIEW.md`)

**Preconditions:** T-042-17 `[x]` with APPROVED.

**Write set:** `specs/releases/v0.4.2/PRE-PR-REVIEW.md`, `.dadaia/handoff/dadaia-workspace/`.

**Description:** The six-axis pre-PR review of the whole release delta, run **while the release
directory is still thawed** — this is the ordering FR5 makes canon and this task is its first
execution. Point the review explicitly at: the FR1 function move and its CLI rewire; the FR4
predicate sharing (does the masker now strictly cover the detector?); the FR7 adapter-only
amnesty change; the FR8 error-surface widening; and the FR14 evidence narrowing (is any genuine
consumption class now invisible?). Any finding is remediated on the thawed tree and re-reviewed
— no reopen of an archived release is ever required. Route findings per FR6.

**Done criterion:** APPROVED verdict on the same commit QA approved (or on the remediated
commit, re-approved by both).

**Parallelism:** none.

---

- [ ] **T-042-19 — Memory window: atoms, diagram, and FR2's memory half (CLOSURE phase)**

**Owner role:** product-engineer (memory + assets) + software-engineer (schema/code half),
sequenced inside **one** commit · **Commit:**
`docs(T-042-19): memory — one axis, calibrated intake, fail-closed amnesty, computed estimates`

**Preconditions:** T-042-18 `[x]` with APPROVED. `ACTIVE.md` phase set to `CLOSURE`
**before writing** — the gate allows `specs/memory/**` writes in `DEFINITION` and `CLOSURE`
only. The dispatcher commits this task's `[-]` flip before relaying the work (FR5).

**Write set:** `specs/memory/product/sdd/sdd-gate-v3.md`,
`specs/memory/product/sdd/sdd-bug-backlog-governance.md`,
`specs/memory/product/sdd/specs-doctor.md`,
`specs/memory/product/distribution/pypi-distribution.md`, `specs/memory/architecture.md`,
`specs/assets/architecture/doctor-decomposition.md`, every `specs/memory/**/*.md` atom (the
`token_estimate:` key removal), `specs/memory/product/catalog.json` (regenerated),
`dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json` (remove
`token_estimate` from `properties`), plus refreshed projections.

**Description:** State the product as it is **now**, per SPEC §5 — no changelog, no history, no
version narrative. Sequence inside the single commit: (1) strip the frontmatter key from every
atom; (2) remove it from the schema's `properties`; (3) regenerate `catalog.json`; (4) apply
the five atom content updates and the diagram refresh. Running both doctors before committing
is part of the done criterion, not an afterthought.

**Done criterion:** A2.3 holds (V8 zero-hit); `dadaia specs doctor` green on the memory checks;
no forbidden section added; SPEC §5 satisfied file by file.

**Parallelism:** none.

---

- [ ] **T-042-20 — CLOSURE, calibrated dispositions, archive, version confirmation**

**Owner role:** product-engineer (text) + software-engineer/dispatcher (**[git]** steps) ·
**Commit:** `docs(T-042-20): close release v0.4.2`

**Preconditions:** T-042-19 `[x]`. The dispatcher commits this task's `[-]` flip before
relaying the work (FR5).

**Write set:** `specs/releases/v0.4.2/CLOSURE.md` (new), `specs/releases/ACTIVE.md`,
`specs/backlog/BACKLOG.md` (13 `DELIVERED — v0.4.2` LEDGER lines), `CHANGELOG.md` (the
`[0.4.2]` section), `pyproject.toml` (confirm `0.4.2`), plus the release-directory move.

**Description:** In the finalization order **memory → CLOSURE → archive**:

1. Record the T-042-19 memory writes under `## Memory updates`.
2. Write `CLOSURE.md` per `dd-release-closure`: summary, tasks + commit SHAs, validations
   V1–V14 as evidence triples, drifts, `## Dispositions` (the 13 picked entries →
   `DELIVERED — v0.4.2` **LEDGER lines, with their ACTIVE subsections already removed at
   T-042-01**; state explicitly that **no bug and no audit** was picked, and that #24 was a
   partial pick that stays ACTIVE), and `## Test dispositions` (T-042-03's recorded
   supersession). Then the **calibrated** residual routing this release ships (FR6/R4): a
   **Record-only observations** section that terminates there, and an `## Intake candidates`
   section carrying only actionable defects. Restate **OD-1…OD-4**.
3. **[git]** Confirm `pyproject.toml` reads `0.4.2` and add the `[0.4.2]` `CHANGELOG.md`
   section above the T-042-16 preamble's explanation.
4. **[git]** `git mv specs/releases/v0.4.2 specs/_archive/releases/v0.4.2`; set `ACTIVE.md` to
   `release: none` / `phase: none`.

**Done criterion:** `CLOSURE.md` complete under `specs/_archive/releases/v0.4.2/`; A6.3 and
A13.3 hold; `ACTIVE.md` no longer points at `v0.4.2`; both doctors green.

**Parallelism:** none.

---

- [ ] **T-042-21 — [git] Milestone (b): ship**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit + PR

**Preconditions:** T-042-20 `[x]`.

**Write set:** git refs only, plus the security-reviewer handoff.

**Description:** Per `dadaia-gitflow` milestone (b) — with the six-axis review already
**done** at T-042-18, on a thawed tree (R3): merge `feature/0.4.2` into local `develop`; run
the diff-based `security-reviewer` review of `origin/develop..develop`, asked specifically to
confirm that no backlog record left the tree other than by the declared purge-on-pick (whose
provenance is SPEC §7) and that nothing under `specs/_archive/**` was modified; push `develop`
with **no `--no-verify`**; open PR `develop` → `main`; watch CI until every job is green;
merge.

**Done criterion:** PR merged to `main`; CI green; `feature/0.4.2` no longer needed.

**Parallelism:** none — last task.
