# ALPHA-1 QA Review — Release v0.12.0 (backlog-tooling-single-source)

**Task:** T-120-11 · **Owner role:** qa-engineer · **Reviewer:** qa-engineer
**Preconditions verified:** T-120-01..10 all `[x]` in `TASKS.md`.
**Validated from:** the live instance (branch `feature/v0.12.0`, worktree HEAD at
`4de25057 docs(T-120-10): the two skills state the mechanism that runs`, plus this
review's own `3e0b9d1b chore(tasks): start T-120-11` reservation commit), not the diff or
any implementer's handoff alone. Every command below was independently re-run in this
session against that commit, with pytest's cache disabled (`-p no:cacheprovider`).

## Verdict

**APPROVED.** All 9 FRs (A1.1–A9.6, 61 acceptance ids) are satisfied on the shipped tree,
independently re-verified — not taken on any implementer's word. Particular attention was
given, per the task description, to: the countable never-delete proof (A7.2), re-derived
independently from `BACKLOG.md` with `document.load_document` rather than trusting the
PM's capture (30 ACTIVE + 52 LEDGER = 82 = 82, zero errors, zero ACTIVE∩LEDGER overlap —
matches); the rename-not-delete evidence (A9.1 — 32 renames, zero bare deletions under
`specs/backlog/` in the cutover commit with git's default rename detection); the two-doctor
agreement (A5.6) on both the live consolidated tree and a planted-violation fixture matrix;
the phantom-`BACKLOG`-slug regression (A5.2 — confirmed absent, no finding ever keys off
slug/path `BACKLOG`); the absent-document no-op (A1.2/A2.8/V14 — exercised live on a
scaffolded scratch context, both before and after deleting `BACKLOG.md` outright); and the
five unmodified-test set (A4.2 + A9.4's four anchor-semantics modules — confirmed by
`git diff 523f0d8d..HEAD` on each, all empty). Zero new e2e tests, zero quarantine/skip/xfail
markers added. Two non-blocking MEDIUM findings (QA-1, QA-2 below), both pre-existing drift
unrelated to this release's own correctness, routed to CLOSURE/PM intake. No task returns
to `[-]`.

---

## Per-FR acceptance evidence

### FR1 — A pure document model for `BACKLOG.md`

| ID | Evidence | Verified |
|---|---|---|
| A1.1 | `tests/unit/features/backlog/test_document.py` — N-subsection/M-row round-trip fixture matrix | Re-run: PASS (part of the 108-test backlog batch, below) |
| A1.2 | Live-exercised: `dadaia specs init` scaffolds `BACKLOG.md`; deleting it outright and re-running `backlog doctor`/`specs doctor` on the fresh context both report clean/`0 errors, 0 warnings` — absence is a legitimate no-op, not an error | Re-run: PASS (direct live exercise, scratch context) |
| A1.3 | `test_document.py` fixture: a subsection missing a required key yields a located error naming the slug; parsing continues | Re-run: PASS |
| A1.4 | `test_document.py` + `tests/unit/features/backlog/test_frontmatter_yaml_parse_error.py` — malformed `**Intents:**` YAML captured as `intents_error`, never raised | Re-run: PASS |
| A1.5 | `test_document.py` fixture: LEDGER-line grammar/disposition-token violations located by line number | Re-run: PASS |
| A1.6 | `lint-imports --config setup.cfg --no-cache` → 9/9 contracts kept, 0 broken (direct re-run) | Re-run: PASS |

### FR2 — `backlog doctor` validates the single source, four codes preserved

| ID | Evidence | Verified |
|---|---|---|
| A2.1 | `dadaia backlog doctor --specs-dir specs --source-root .` on the live consolidated tree → `backlog doctor: clean.` | Re-run: PASS (direct live re-run) |
| A2.2–A2.7 | `tests/integration/test_backlog_doctor.py` fixture matrix (BL-SCHEMA missing-key, `idea`-exempt vs `candidate`-required intents gate, malformed-YAML-at-any-status, BL-DUP slug repeat, BL-CONFLICT divergent anchor, BL-STALE's three ORed conditions incl. the real 18-sidecar archived-consumed path) | Re-run: PASS (part of the 108-test batch) |
| A2.8 | Same live scratch-context exercise as A1.2: absent `BACKLOG.md` → `backlog doctor: clean.`, exit 0 | Re-run: PASS |
| A2.9 | `tests/integration/test_precommit_backlog_scoping.py` — staged-scope gate behavior unchanged | Re-run: PASS |

### FR3 — `backlog new` authors an ACTIVE subsection

| ID | Evidence | Verified |
|---|---|---|
| A3.1 | Live-exercised on a scratch context with no `BACKLOG.md`: `dadaia backlog new qa-scratch-test-slug` → `[ok] created:`, document authored with both section headings + one conformant `idea`-status subsection | Re-run: PASS (direct live exercise) |
| A3.2 | `tests/unit/features/spec_artifacts/test_new_artifacts.py` byte-diff assertion (append leaves every other byte untouched) | Re-run: PASS |
| A3.3 | Live-exercised: re-running `backlog new qa-scratch-test-slug` on the now-populated scratch document → `[error] Backlog slug already exists: … in ACTIVE or LEDGER …`, exit 1, nothing written | Re-run: PASS (direct live exercise) |
| A3.4 | Live-exercised: `backlog new "Invalid Slug!"` → `[error] Invalid slug … Must match ^[a-z][a-z0-9-]+$…`, exit 1 | Re-run: PASS (direct live exercise) |
| A3.5 | The freshly authored scratch subsection: `backlog doctor` → clean; `specs doctor` → `0 errors, 0 warnings` | Re-run: PASS (direct live exercise, both doctors) |

### FR4 — The dead removal/consumption write side is retired

| ID | Evidence | Verified |
|---|---|---|
| A4.1 | Tree-wide grep (standing exclusions) for the 11-symbol list: zero hits in `dadaia_workspace/**`/`tests/**` (code-only re-check). Non-code prose hits exist only in `specs/_archive/**`, `specs/backlog/_archive/**`, this release's own SPEC/PLAN/TASKS/GRILL, and `specs/backlog/BACKLOG.md`'s own PM-authored provenance text (see QA-2 below — a SPEC §3 scope gap, not a code defect) | Re-run: PASS at the code level |
| A4.2 | `git diff 523f0d8d..HEAD -- tests/unit/test_backlog_ledger.py` → empty (unmodified since v0.1.75, long before this release); `read_consumed`/`LEDGER_FILENAME` behavior confirmed live via A2.7's 18-sidecar BL-STALE path | Re-run: PASS |
| A4.3 | `git diff --stat 523f0d8d..HEAD -- specs/_archive/` → empty | Re-run: PASS |
| A4.4 | T-120-03's four recorded whole-file supersessions (`test_backlog_removal.py`, `test_backlog_ledger_writer.py`, `test_backlog_removal_loop.py`, `test_consumes.py`) confirmed as pure deletions in the range diff-stat; **plus a fifth, disclosed in the cutover commit message and the test module's own docstring**: three of four tests inside `test_frontmatter_yaml_parse_error.py` (the legacy-loader-specific cases) deleted with an explicit "T-120-08 supersession (recorded)" docstring naming the replacement coverage — no other test outside these five was deleted, skipped, quarantined, or weakened (confirmed by the full delta audit below) | Re-run: PASS |
| A4.5 | `dadaia --help` / `dadaia backlog --help` → exactly `new`, `subjects`, `doctor` | Re-run: PASS (direct live re-run) |
| A4.6 | `dadaia ci preflight` → ruff format/check, mypy --strict, lint-imports, pytest all PASS | Re-run: PASS |

### FR5 — `specs doctor` governance re-targeted at the single source

| ID | Evidence | Verified |
|---|---|---|
| A5.1 | `tests/unit/features/specs/test_doctor_taxonomy_disposition.py` — SPEC-DOC-031 fires on a planted non-terminal item referenced outside `## Backlog returns`; live tree confirms 11 real such WARNINGs (see QA-1) | Re-run: PASS |
| A5.2 | Live `dadaia specs doctor` output grepped for any finding keyed to slug/path `BACKLOG` — zero hits; the phantom-entry regression this ADR-D9 re-target specifically guards against is confirmed absent | Re-run: PASS (direct live re-check) |
| A5.3 | `tests/unit/features/specs/test_doctor_taxonomy_disposition.py -k "doc035 or doc031"` → 3 passed; SPEC-DOC-035 fires on a planted loose `*.md`, not on `BACKLOG.md`/`README.md`/`_archive/**`/`remote-bugs/**` | Re-run: PASS |
| A5.4 | Tree-wide grep (code-only, `dadaia_workspace/**` + `tests/**`) for `check_backlog_schema`/`BACKLOG_BULLET_RE`/`BACKLOG_HOTFIX_RE`/`_HOTFIX_STALE_HOURS` → zero hits | Re-run: PASS (direct live re-check) |
| A5.5 | `dadaia specs doctor` on the live consolidated tree: **0 errors**, but **11 SPEC-DOC-031 WARNINGs** attributable to the backlog surface — literal text of A5.5 is NOT met. Independently re-verified as pre-existing, non-regressive drift (see QA-1) via a `git worktree` snapshot of the pre-cutover tree (`9543ca8c`, T-120-06's tip) with the pre-cutover `doctor_governance.py` invoked directly: the identical 11 slugs fire identically before T-120-08 | Re-run: **partial** — see QA-1, non-blocking |
| A5.6 | Both doctors agree: the live tree is `backlog doctor`-clean and `specs doctor`-0-error; every planted fixture violation in A2.2–A2.7/A5.1/A5.3's matrices is rejected identically by both validators (same test modules exercise both) | Re-run: PASS |

### FR6 — The consumer-facing description matches the shipped model

| ID | Evidence | Verified |
|---|---|---|
| A6.1 | Tree-wide grep for `specs/backlog/<slug>.md`-shaped instructions across `public/**` → **one hit**: `dadaia_workspace/public/skills/dd-release-closure/SKILL.md:93`'s Dispositions-table template row, confirmed pre-existing (`git diff 523f0d8d..HEAD` on that file is empty — last touched at v0.10.0, outside every T-120-0x write set) — literal text of A6.1 is NOT met (see QA-2, non-blocking) | Re-run: **partial** — see QA-2, non-blocking |
| A6.2 | `grep -i gitignor` near `backlog` in `.github/workflows/ci.yml` and `dadaia_workspace/cli/commands/newartifacts.py` → zero hits; both now correctly cite `.gitignore:133-142` opting `*.md` back in | Re-run: PASS (direct live re-check) |
| A6.3 | `dadaia public doctor` → `[ok] public-privacy`, no `[error]` anywhere in the output | Re-run: PASS (direct live re-run) |
| A6.4 | `.github/workflows/ci.yml`'s `backlog-doctor` job comment corrected in place; same verb/args, no new e2e (confirmed by the tree-wide e2e-count check below) | Re-run: PASS |
| A6.5 | `public/scaffold/backlog/README.md` and `CONSUMER_VALIDATION_RECIPE.md` rewritten against the shipped model (F-10/R-02/R-13); `scaffolder.py`'s fresh-init stub now matches `backlog new`'s own skeleton (live-verified: `specs init` produces a `BACKLOG.md` with `## ACTIVE`/`## LEDGER`, both doctors clean out of the box) | Re-run: PASS (direct live re-check via V14) |

### FR7 — The physical consolidation, never-delete proven by count

| ID | Evidence | Verified |
|---|---|---|
| A7.1 | `specs/backlog/BACKLOG.md` — exactly two top-level sections (`## ACTIVE`, `## LEDGER`), parses clean under `load_document` (0 errors) | Re-run: PASS (direct live re-check) |
| A7.2 | **Independently re-derived, not trusted from the PM's capture.** `document.load_document(Path("specs/backlog"))` → 30 ACTIVE items, 52 LEDGER rows, 0 errors, `active_slugs ∩ ledger_slugs = ∅`, 82 unique slugs total — matches the PM's own capture (`.dadaia/tmp/project-manager/20260815/T-120-07-set-equality-proof.json`: pre-state 82 = post-state 82, both diffs empty) exactly | Re-run: **independent PASS** |
| A7.3 | Confirmed by A7.2's zero ACTIVE∩LEDGER overlap and zero duplicate count within each section (`len(active_slugs) == len(doc.active)`, `len(ledger_slugs) == len(doc.ledger)`) | Re-run: PASS |
| A7.4 | Spot-checked several ACTIVE subsections' Provenance lines (e.g. the two picked entries cite `SPEC.md` §7; the intake-derived entries cite report path + approval date) — all traceable | Re-run: PASS |
| A7.5 | `ls specs/backlog/` → exactly `BACKLOG.md`, `README.md`, `_archive/`, `remote-bugs/` (empty subtree, confirmed) plus a pre-existing `.gitkeep` (not a `.md`, outside SPEC-DOC-035's scope); `git status`/A9.1 confirm renames | Re-run: PASS (direct live re-check) |
| A7.6 | Both doctors clean on the consolidated tree (A2.1, A5.5's error-count, A5.6) | Re-run: PASS |
| A7.7 | Cross-reference numbering: PM's provenance sections cite entries by slug, not dangling numeral (spot-checked backlog-tooling-reconciliation's Intents block anchor repoint note) | Re-run: PASS |

### FR8 — The two skills state the mechanism that runs

| ID | Evidence | Verified |
|---|---|---|
| A8.1 | `grep -rn removal_lifecycle` across `dadaia_workspace/public/`, `.claude/skills/`, `.agents/skills/` at the workspace root → zero hits | Re-run: PASS (direct live re-check) |
| A8.2 | `dd-backlog-definition/SKILL.md` §2 documents all six ACTIVE keys (Title/Opened/Status/Description/Provenance/Intents); grep for "schema authority"/"not schema authority" → zero hits (the §7 caveat is gone) | Re-run: PASS (direct live re-check) |
| A8.3 | `dd-release-definition/SKILL.md` §5's checklist item and body name only executors that exist today (PM purge-on-pick + `dd-release-closure` disposition sweep, backstopped by BL-STALE/SPEC-DOC-031); grep for the three hedge phrases → zero hits | Re-run: PASS (direct live re-check) |
| A8.4 | Both skills byte-identical across `dadaia_workspace/public/skills/`, `.claude/skills/`, `.agents/skills/` (`diff -q` on all four projections); `dadaia public doctor` green including `[ok] public-privacy` | Re-run: PASS (direct live re-check) |

### FR9 — The invariants this release must not break

| ID | Evidence | Verified |
|---|---|---|
| A9.1 | `git show --stat af55e798 -- specs/backlog/` (default rename detection) → 32 renames, zero bare `D`-status entries; `git log --diff-filter=D 523f0d8d..HEAD -- specs/backlog/` → empty | Re-run: PASS (direct live re-check) |
| A9.2 | `git diff --stat 523f0d8d..HEAD -- specs/_archive/` → empty | Re-run: PASS (direct live re-check) |
| A9.3 | Not yet applicable — `CLOSURE.md`'s `## Intake candidates` section is T-120-13's obligation (release still in IMPLEMENTATION phase); no new file exists under `specs/backlog/` other than `BACKLOG.md` today (confirmed by A7.5) | Deferred to T-120-13, tracked not blocking |
| A9.4 | `git diff 523f0d8d..HEAD` on `test_backlog_classifier.py`, `test_backlog_subject_registry.py`, `test_backlog_models.py`, `tests/unit/backlog/test_classifier_clamp.py` → all four empty (byte-identical) | Re-run: PASS (direct live re-check, 4/4) |
| A9.5 | `dadaia backlog --help` → exactly `new`, `subjects`, `doctor`; BL-* codes and SPEC-DOC id set unchanged (minus the three FR5 retirements) | Re-run: PASS |
| A9.6 | `dadaia ci preflight` → all 5 checks PASS; full suite 2270 passed/3 skipped/0 failed | Re-run: PASS |

---

## Test-pyramid audit of the delta

`git diff 85aa721a..HEAD --stat -- tests/` (85aa721a = milestone-(a) merge, the last point
before any T-120-0x commit) touches exactly 20 files:

- **One new file:** `tests/unit/features/backlog/test_document.py` (318 lines) — the FR1
  parser matrix. Declares `Intent: CONTRACT — v0.12.0 A1.1…` at the module docstring.
- **Four whole-file recorded supersessions** (T-120-03's table, confirmed pure deletions
  in the diff-stat): `test_backlog_removal.py`, `test_backlog_ledger_writer.py`,
  `test_backlog_removal_loop.py`, `test_consumes.py`.
- **A fifth, partial, disclosed supersession** inside `test_frontmatter_yaml_parse_error.py`:
  three of four legacy-loader-specific tests deleted, replacement coverage named in the
  module's own docstring and in the T-120-08 cutover commit message — matches PLAN §2's
  P14 "migrated" disposition, not silent pruning.
- **Adjusted-in-place migrations:** `test_backlog_doctor.py`, `test_cli_newartifacts.py`,
  `test_new_artifacts.py`, `test_precommit_backlog_scoping.py`, `test_backlog_precommit.py`
  (e2e — fixture shape only, same gate), `test_governance_intake_not_gitignored.py`,
  `test_doctor.py`, `test_doctor_golden.py`, `test_doctor_taxonomy_disposition.py`,
  `test_doctor_ledger_invariants.py` (SPEC-DOC-031 fixtures + the A5.2 regression, disclosed
  in the cutover commit message though not separately named in TASKS.md's write-set list),
  `_golden/README.md`, `_golden/doctor_golden_v0155.json`.
- **Mechanical consequence of an in-scope deletion (disclosed by SE):**
  `test_repo_self_scan.py`'s shrink-only baseline (29→28 rows) and
  `test_import_linter_ignore_cap.py`'s ratcheted cap (15→16, +1 features-no-cross-feature
  edge for the new `doctor_governance → document` leaf-to-leaf import).
- **`test_scaffolder.py`:** one-line expected-file-list update (`candidates.md`+`ideas.md`
  → `BACKLOG.md`), matching the scaffolder fix (see cross-check below).

Zero new e2e tests (`git diff --diff-filter=A 85aa721a..HEAD --name-only -- tests/e2e/` is
empty). Zero quarantine/skip/xfail markers added anywhere in the range diff. All five
directly-checked new/rewritten test files declare `Intent: CONTRACT` or `Intent: SENTINEL`
at the module docstring. No test outside the five recorded supersessions above was deleted,
skipped, or weakened — every other touched file's diff adds or migrates assertions, none
removes one without a same-commit replacement.

---

## SE deviations cross-checked — all three legitimate and disclosed, none silent

Per the task's explicit instruction, the three deviations named were independently
re-derived from the diff and cross-checked against the cutover commit message
(`af55e798`), which discloses all three in full prose — none is silent:

1. **`scaffolder.py` fix.** `_CANDIDATES_STUB`/`_IDEAS_STUB` (the retired per-entry stubs)
   replaced by a `_BACKLOG_STUB` skeleton (`## ACTIVE` + `## LEDGER`), matching exactly what
   `backlog_new` writes when it finds no document. Root cause named in the commit message:
   "the old stubs tripped the new SPEC-DOC-035 single-source invariant on every fresh
   workspace init." Live-verified: a fresh `specs init` now produces a clean `BACKLOG.md`
   skeleton (V14).
2. **`lint-imports` ignore-edge cap 15→16.** `test_import_linter_ignore_cap.py`'s
   `_RECORDED_IGNORE_EDGE_CAP` and its per-family breakdown (`features-no-cross-feature`
   1→2) both ratcheted with an inline comment naming the new edge
   (`doctor_governance.py → features.backlog.document`, leaf-to-leaf, the PLAN §6-sanctioned
   fallback). `lint-imports --config setup.cfg --no-cache` confirms 9/9 contracts still
   kept — the ratchet is additive, not a contract weakening.
3. **`BACKLOG.md` anchor repoint.** `backlog-tooling-reconciliation`'s own two `code` Intents
   refs (`load_backlog_items`, `_BACKLOG_AGGREGATE_FILES` — both deleted by this same
   cutover) repointed in-place to their post-cutover replacements
   (`document.py#load_document`, `doctor_governance.py#_BACKLOG_SINGLE_SOURCE_FILES`), with
   an explanatory note inline in the entry's own `**Intents:**` block explaining why the ref
   moved, so the entry stays BL-SCHEMA-resolvable across the whole `status: picked` window
   (the standing green rule). Confirmed live: `_BACKLOG_SINGLE_SOURCE_FILES` exists at
   `doctor_governance.py:52`.

All three are root-caused, necessary for the standing green rule, and disclosed in the same
commit that makes them — none is a silent workaround.

---

## Live verification (this session)

- **Full suite (the exact command requested):**
  `python -m pytest -q -p no:cacheprovider -m 'not quarantine' -n auto` →
  **`2270 passed, 3 skipped, 1 warning in 132.83s (0:02:12)`**. The 3 skips are
  environment-gated (2× Windows-only, 1× no non-loopback IPv4), unrelated to this release.
- **`dadaia backlog doctor --specs-dir specs --source-root .`:** `backlog doctor: clean.`
- **`dadaia specs doctor`:** `0 error(s), 16 warning(s)` overall — 11 attributable to the
  backlog surface (QA-1, pre-existing), the rest pre-existing token-drift/heading-lint
  warnings and two SPEC-DOC-036 archived-audit warnings, all unrelated to this release
  (confirmed unrelated by scope — none names a `T-120-*` symbol or path).
- **`dadaia public doctor`:** all `[ok]`/`[foreign]`/`[info]` lines, zero `[error]`;
  `[ok] public-privacy`.
- **`dadaia ci preflight`:** all 5 checks PASS (ruff format, ruff check, mypy --strict,
  lint-imports, pytest).
- **`lint-imports --config setup.cfg --no-cache`:** 9/9 contracts kept, 0 broken.
- **Backlog-specific test batch** (`test_document.py`, `test_backlog_doctor.py`,
  `test_new_artifacts.py`, `test_cli_newartifacts.py`, `test_doctor.py`,
  `test_doctor_taxonomy_disposition.py`, `test_governance_intake_not_gitignored.py`,
  `test_backlog_precommit.py`, `test_precommit_backlog_scoping.py`,
  `test_frontmatter_yaml_parse_error.py`): **108 passed**.
- **A7.2 independent re-derivation:** `document.load_document` on the live
  `specs/backlog/` → 30 ACTIVE + 52 LEDGER = 82, 0 errors, 0 overlap — matches PM capture.
- **QA-1 independent regression check:** `git worktree` snapshot at `9543ca8c` (pre-cutover
  tip), pre-cutover `doctor_governance.py` invoked directly against the pre-cutover
  per-entry tree → the identical 11 slugs fire SPEC-DOC-031, proving non-regression.
- **A9.1 rename check:** `git show --stat af55e798 -- specs/backlog/` (default rename
  detection) → 32 renames, 0 bare deletions.

---

## Findings summary

| # | Severity | Area | Finding | Blocking? |
|---|---|---|---|---|
| QA-1 | MEDIUM | `dadaia specs doctor` / SPEC-DOC-031 over `BACKLOG.md` | A5.5's literal text ("0 errors and 0 warnings attributable to the backlog surface") is not met: 11 SPEC-DOC-031 WARNINGs fire on the consolidated tree (`test-suite-remediation-stewardship`, `retire-dead-hotfix-surface`, `consumer-side-validation-round`, `thin-wrapper-projected-scripts`, `bug-picked-ledger-event`, `codex-persona-law-context-dehydration`, `python-env-interpreter-probe-hardening`, `changelog-version-axis-reconciliation`, `commit-paths-index-scope-hardening`, `commit-message-scanning-residual`, `baseline-carve-out-review-cadence`). Independently re-verified via a `git worktree` snapshot of the pre-cutover tree with the pre-cutover code invoked directly: the identical 11-slug set fires identically before T-120-08 — **proven pre-existing backlog-curation drift, not a regression this release introduces.** (The SE's own T-120-08 handoff disclosed this class of finding already, citing 10 slugs; this review's independent recount finds 11 — a minor accounting correction, not a new substantive gap.) | **No** for T-120-11 — the governance re-target (FR5) behaves identically to the retired per-entry check on the same underlying data; the code is correct. Already correctly routed by the SE's own handoff to T-120-13's `CLOSURE.md` `## Intake candidates` for PM disposition (ADR #15) — carry that routing through at closure. |
| QA-2 | MEDIUM | `dadaia_workspace/public/skills/dd-release-closure/SKILL.md:93` | A6.1's literal tree-wide zero-hit grep across `public/**` for `specs/backlog/<slug>.md`-shaped per-entry instructions fails on one hit: the Dispositions-table template row still reads `` `specs/backlog/<slug>.md` \| backlog \| `DELIVERED — <release-id>` ``, stale against the single-source model this release ships (a disposition is now a LEDGER line inside `BACKLOG.md`, not a separate per-slug file). Confirmed pre-existing: `git diff 523f0d8d..HEAD` on this file is empty — last touched at v0.10.0, and `dd-release-closure` is outside every T-120-0x task's declared write set (FR6/T-120-09 covers scaffold README + consumer recipe + CI comment; FR8/T-120-10 covers only `dd-backlog-definition` and `dd-release-definition`). | **No** for T-120-11 — outside every declared write set in this release; no code or shipped behavior is affected, only a documentation template row for a future closure step. **Recommended before T-120-14 ship**: SPEC §5's own prose for T-120-13 already correctly describes the LEDGER-line mechanism (low risk of a literal misfollow), but the stale skill row itself should be fixed in a follow-up — route to PM intake alongside QA-1. |

No CRITICAL or HIGH finding.

---

## Security/privacy leakage note

Reviewed for observable risk surfaces in this release's diff (the parser, the doctor
checks, the writer, the governance re-target, the container deletions, the CI/docs
surfaces, and every touched test module):

- **No new dependency, secret, token, or credential surface.** FR1–FR8 touch only
  `features/backlog/**`, `features/specs/doctor_governance.py`,
  `features/spec_artifacts/new_artifacts.py`, `cli/commands/{newartifacts,ci}.py`,
  `container.py` (deletions only), `public/scaffold/backlog/README.md`,
  `public/data/CONSUMER_VALIDATION_RECIPE.md`, `.github/workflows/ci.yml` (comment only),
  the two skill files, and their test modules — no new network call, no new external I/O.
- **The consolidated `BACKLOG.md` carries no secret material.** Spot-checked: every
  Provenance line cites an operator request or an intake-report path + date; no credential,
  token, or private infrastructure detail appears in the 61.5 KB document.
- **The retired write side (`removal_lifecycle.py`, `removal.py`, `ledger_writer.py`,
  `consumes.py`) removed a filesystem-mutation surface, not added one** — its own former
  safety argument (P7) rested on a false "gitignored" premise this release also corrects.
- **`ledger.py`'s `read_consumed` is a pure reader** over 18 real historical
  `consumed_backlog.json` sidecars under `specs/_archive/**` (FROZEN, confirmed untouched by
  A4.3/A9.2) — no write path, unmodified test (A4.2).
- **The container fakes retired** (`_fake_spec_stub`, `_FAKE_BACKLOG_CANARY_SLUG` and
  siblings) were dead test-harness scaffolding with zero production callers (confirmed by
  A4.1's zero-hit grep) — their removal shrinks the attack surface, introduces none.
- **This review artifact itself** carries no foreign Spec Context name, hostname, IP,
  email, secret, or absolute local path — every path cited is workspace-relative to this
  repo's own tree; the pre-cutover worktree snapshot used for QA-1's independent
  verification was created and removed entirely within this session's scratch directory,
  never committed, and referenced here only by its commit sha.
- **Standing milestone-(a) diff review already APPROVED** (T-120-02) covered the
  definition commit only. The milestone-(b) diff review of the full implementation delta
  (`origin/develop..develop`) is still due at T-120-14, per the ordinary gitflow cadence —
  not a gap this alpha-1 review introduces.

No suspected leakage found.

## Accepted deviations

None required by this task. QA-1 and QA-2 above are recorded as non-blocking findings
routed to T-120-13 (CLOSURE `## Intake candidates`)/PM intake, not treated as a
`software-engineer` task violation — both are pre-existing drift outside every T-120-0x
task's declared write set, confirmed by direct `git diff 523f0d8d..HEAD` on the affected
files.

## Marker note

This review's `[-]`→`[x]` completion transition is committed in the same commit as this
artifact and the `TASKS.md` marker flip, per the ordinary `dadaia-task-manager` discipline
(reserve commit `3e0b9d1b chore(tasks): start T-120-11` already landed separately).
