# Closure: Release — v0.12.0 — backlog-tooling-single-source

**Status:** Aprovado
**Release ID:** v0.12.0
**Owner:** product-engineer
**Closed:** 2026-08-15
**Branch:** `feature/v0.12.0` (cut from `develop` at `523f0d8d`; branch contract: `dadaia-gitflow`)
**Source SPEC:** `specs/releases/v0.12.0/SPEC.md` · **Source PLAN:** `specs/releases/v0.12.0/PLAN.md`
**Grill:** `specs/releases/v0.12.0/GRILL.md` (P1–P15, ADRs D1–D10)
**QA close of the flat increment:** `ALPHA-1-QA.md` (APPROVED, 61/61 acceptance ids A1.1–A9.6)
**Picked set:** two backlog entries — `backlog-tooling-reconciliation` (#30, carrying intake
item **2-2** as an approved merge) and `backlog-md-physical-consolidation` (#31). **No bug and
no audit was picked**, because the ledger carried **zero** open bugs at pick time (the two
v0.9.0-window LOWs closed by `hotfix/0.7.1`, merged at `d15bdf4e`, the commit this branch was
cut from) and both 2026-07 audits were archived fully dispositioned by v0.8.0. Pick-time
priority (`DADAIA.md` §5) is satisfied with nothing outranking.

---

## Summary

v0.12.0 makes the backlog what the law has said it is since v0.10.0. Three releases carried a
doctrine that existed only as text: `DADAIA.md` §5, the `dd-backlog-definition` schema and the
`sdd-bug-backlog-governance` memory atom all described one `specs/backlog/BACKLOG.md` with an
`ACTIVE` section and a `LEDGER` section, while the tree held 31 per-entry files plus a
hand-maintained `candidates.md` index and every backlog verb, the pre-commit gate, the CI job
and four `specs doctor` checks read and wrote that per-entry model end to end. The gap had
already started costing: the index had drifted from the files it indexed (31 files against 30
rows), the canonical skill had to carry a note telling readers not to treat the shipped CLI as
schema authority, and a required release-definition step — the `**Consumes:**` declaration —
pointed at a producer with no caller since the workflow engine was deleted in v0.3.0. This
release closes the gap from both ends in one pass, and it does so atomically: the physical
consolidation and the tooling cutover ride a single commit, because either one alone leaves a
tree the doctors reject.

What shipped. `features/backlog/document.py` parses the document into a typed ACTIVE/LEDGER
model — five required keys per subsection plus an optional `Intents` block, a four-field LEDGER
grammar, every error captured as a located diagnostic rather than raised, and an absent file
read as an empty model so a scaffolded context with no backlog is a clean no-op rather than an
error. `backlog doctor` validates that model with its four codes unchanged in identity, message
and severity, with BL-STALE re-defined to the one thing it can now mean: an ACTIVE item that is
already consumed or dispositioned. `backlog new` appends a conformant subsection instead of
creating a file, and refuses a slug present in either section. `specs doctor` re-targets
SPEC-DOC-031 at the ACTIVE subsections and turns SPEC-DOC-035 into the single-source invariant —
any item file left loose under `specs/backlog/` is drift — while `check_backlog_schema` retires
and takes SPEC-DOC-012, 022 and 023 with it. In the same pass the dead write side is deleted
rather than resurrected: `removal_lifecycle.py`, `removal.py`, `ledger_writer.py`,
`consumes.py`, their container builders and the dead driving fakes, on the finding that the
module's defined behaviour — rewrite an item down or archive-then-unlink it — contradicts the
never-delete law it was built to serve. The two skills now describe the mechanism that actually
runs, and the consumer-facing README, validation recipe and CI comment describe the model
consumers actually get.

The property this release had to prove is that nothing was lost. 31 live files, 30 index rows,
46 archived files and 20 LEDGER lines fold into one document, and the proof is countable rather
than asserted: the sorted slug set before the fold equals the sorted slug set after it, **82 =
82**, both differences empty — captured by the PM and then re-derived independently by QA
through the shipped parser rather than trusted from the capture. Every file that left
`specs/backlog/` left by `git mv`: 32 renames, zero bare deletions, zero modifications under
FROZEN `specs/_archive/`. Nine acceptance families, 61 ids, all verified by QA against the
tree it reviewed; **2,270 passed / 3 skipped** at that QA close and **2,275 / 3** on the shipped
tree, after the pre-ship review remediation added five tests; both doctors clean; zero new e2e
tests and zero new CLI verbs, hooks or scripts. This closure is also the first to execute the
disposition sweep on the new shape: its own two picked entries leave `ACTIVE` and gain `LEDGER`
lines in the same commit, taking the document from 30+52 to **28+54** — the same 82 slugs.

One thing this closure records that the first attempt at it did not: **the close was reopened.**
The pre-PR `code-reviewer` pass returned APPROVE with zero CRITICAL and zero HIGH and two MEDIUMs,
one of them a real parser-hardening gap in the module this release shipped. Rather than ship a
known defect and file it, the archive commit was reset, the fix landed pre-ship at `a76d55bf`, and
this document was re-authored against the corrected figures — see
`## Drifts › reopened-close-for-review-remediation`.

## Tasks completed

Every task from T-120-01 to T-120-11 reached `[x]` with its acceptance ids satisfied; T-120-12
landed at `f446b9ce` and T-120-13 completes with this commit. **`product-engineer` has no
shell**, so every per-task SHA below was filled by the dispatcher or transcribed from an
artifact that records it (`ALPHA-1-QA.md`, the implementer handoffs) — never guessed by the
closer.

**Every row was then verified against the log by the pre-PR `code-reviewer` pass**, which
resolved each SHA to its actual subject. Two rows were carrying a subject the dispatcher had
paraphrased rather than transcribed — T-120-01 and T-120-12 — and both now read the real commit
subject; the reviewer confirmed every other row exact. The four rows that carried both a filled
SHA and a leftover `(sha owed)` marker (T-120-01, T-120-04, T-120-05, T-120-09) are cleaned: the
marker is a request, and a request that has been answered is deleted, not kept beside its answer.
No history was rewritten in this release — the one reset is the reopened close, recorded under
`## Drifts › reopened-close-for-review-remediation`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-120-01 | [git] Definition content committed on `feature/v0.12.0` (trio + GRILL + two pick flips + `candidates.md`), `ACTIVE.md` → `IMPLEMENTATION` | `daee2f75` — `docs(T-120-01): v0.12.0 definition — backlog tooling single-source cutover` |
| T-120-02 | [git] Milestone (a): merge into `develop`, diff-based security review, push | merge `85aa721a`; APPROVED handoff `2026-08-15T204611Z-security-reviewer-v0.12.0-definition-push` |
| T-120-03 | FR4 — retire the dead removal/consumption write side and the dead fakes | `2384309e` — `refactor(T-120-03): delete the uncalled backlog removal/consumption write side` |
| T-120-04 | FR1 — `features/backlog/document.py`, the single-source parser | `f4e47854` — `feat(T-120-04): parse BACKLOG.md into a typed ACTIVE/LEDGER model` |
| T-120-05 | FR2 — the four BL-* checks over the document model (unwired) | `060a3982` — `feat(T-120-05): run BL-SCHEMA/DUP/CONFLICT/STALE over the ACTIVE/LEDGER model` |
| T-120-06 | FR3 — `backlog new` authors an ACTIVE subsection | `9543ca8c` — `feat(T-120-06): backlog new appends an ACTIVE subsection to BACKLOG.md` (the pre-cutover tip QA used for its independent QA-1 regression snapshot) |
| T-120-07 | FR7a — `BACKLOG.md` authored from the live tree, content only, uncommitted | no commit **by design**; content committed by T-120-08. Evidence: `.dadaia/tmp/project-manager/20260815/T-120-07-set-equality-proof.json`; handoff `2026-08-15T215423Z-project-manager-T-120-07-backlog-consolidation` |
| T-120-08 | THE CUTOVER — wiring, loader deletion, governance re-target, document, `git mv` (one commit) | `af55e798` — `feat(T-120-08): cut the backlog over to single-source BACKLOG.md`; 54 files, 32 renames, 0 bare deletions |
| T-120-09 | FR6 — scaffold README, consumer recipe, CI job comment, docstring | `18bd6dcd` — `docs(T-120-09): describe the single-source backlog to consumers`; handoff `2026-08-15T224640Z-software-engineer-T-120-08-T-120-09` |
| T-120-10 | FR8 — the two skills state the mechanism that runs | `4de25057` — `docs(T-120-10): the two skills state the mechanism that runs`; handoff `2026-08-15T225930Z-ai-engineer-T-120-10` |
| T-120-11 | `qa-engineer` review of the increment (alpha-1 close) — **APPROVED**, 61/61 ids | reserve `3e0b9d1b`, done `e199491f`; artifact `ALPHA-1-QA.md` + handoff `2026-08-15T231133Z-qa-engineer-v0.12.0-alpha1` |
| T-120-12 | Memory update in the CLOSURE phase — two atoms + the catalog's two `token_estimate` fields | `f446b9ce` — `docs(T-120-12): memory — single-source backlog as shipped truth`. Survived the reopen: only the archive commit was reset |
| T-120-13 | CLOSURE, dispositions, archive, version bump | this file, on the **re-close** commit; the first attempt (`9d079389`) was reset for pre-ship review remediation and its disposition sweep is re-executed here. Final sha assigned by the dispatcher at commit time |
| T-120-14 | [git] Milestone (b): ship — code review, merge, security review, push, PR `develop` → `main`, CI green | **Pending ship.** Archives `[ ]` **by design** — the ship task cannot flip its own marker after T-120-13 moves the directory into FROZEN `specs/_archive/`. **Fifth occurrence** of the same flat-release canon gap (v0.8.0, v0.9.0, v0.10.0, v0.11.0, here); already owned by the live backlog entry `flat-release-ship-task-evidence`, so it is **not** re-raised as a new intake candidate. **Partly executed already:** the six-axis `code-reviewer` pass ran against `85aa721a..9d079389` and returned **APPROVE**, and its one code-level MEDIUM was remediated at `a76d55bf` before ship. What remains is the merge, the diff-based security review, the push, the PR and CI. Completion evidence lives in the milestone-(b) merge commit, the two reviewer handoffs, the PR and CI |

## Validations

V1–V14 are PLAN §9's validation plan, one row each. Every figure below was independently re-run
by `qa-engineer` at T-120-11 against the tree at `4de25057`, with pytest's cache disabled — not
taken from an implementer's report. Where the pre-ship remediation at `a76d55bf` moved a figure,
both figures are carried with their run named; nothing is silently overwritten.

**Suite figure, stated once so the three runs are never confused.** Three counts exist in this
release's evidence, and two of them are the same number for different reasons — which is exactly
why each is labelled by its run:

1. **`9543ca8c`, the pre-cutover tip** (after T-120-06): **2,275 passed / 3 skipped**. Appears
   only in the T-120-03…06 implementer handoff.
2. **`4de25057`…`9d079389`, the QA-reviewed tree**: **2,270 passed / 3 skipped / 0 failed**. The
   cutover deleted one whole test module's worth of coverage and three legacy-loader tests inside
   a fourth. **This is the figure every V-row below carries**, because this is the tree QA ran
   against.
3. **`a76d55bf`, the shipped tree**: **2,275 passed / 3 skipped / 0 failed** — 2,270 plus the five
   tests the M1 remediation added. It coincides numerically with (1) and shares no tree with it;
   a reader matching on the number alone will match the wrong run.

The 3 skips are the same environment-gated three in all runs (2 Windows-only, 1 needing a
non-loopback IPv4).

| Description | Command | Evidence |
|-------------|---------|----------|
| V1 — Preflight on every commit (A4.6, A9.6) | `dadaia ci preflight` | All 5 checks PASS: `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest`. QA-reviewed tree: **`2270 passed, 3 skipped, 1 warning in 132.83s`** under `-m 'not quarantine' -n auto -p no:cacheprovider`; re-run green after the M1 remediation at **2,275 / 3 / 0** (row R5). Captures `.dadaia/tmp/software-engineer/20260815/T-120-08-full-pytest-rerun.txt`, `…/T-120-09-full-pytest.txt` |
| V2 — Backlog gate, live tree (A2.1, A7.6) | `dadaia backlog doctor --specs-dir specs --source-root .` | `backlog doctor: clean.` — zero findings, exit 0, on the consolidated 30-ACTIVE/52-LEDGER document. Capture `.dadaia/tmp/software-engineer/20260815/T-120-08-V2-backlog-doctor.txt`; QA re-ran it live |
| V3 — Backlog gate, planted violations (A2.2–A2.7) | fixture tree per A2.2–A2.7, exit 1 with the expected codes | `tests/unit/features/backlog/test_document.py` (new, 318 lines) + `tests/integration/test_backlog_doctor.py`, inside the **108-passing** backlog-specific batch QA re-ran. Each planted case fires exactly the expected code: missing key → BL-SCHEMA naming the slug; `candidate` without intents → BL-SCHEMA while the same item at `idea` fires nothing; malformed intents YAML → BL-SCHEMA at any status including `idea`; repeated slug → BL-DUP; shared anchor with differing change → BL-CONFLICT; ACTIVE slug also carrying a LEDGER line → BL-STALE, LEDGER-only → nothing; ACTIVE slug in an archived `consumed_backlog.json` → BL-STALE over the 18 real sidecars |
| V4 — Specs doctor (A5.1–A5.5, A7.6) | `dadaia specs doctor` | **0 errors, 17 warnings on the shipped tree**, of which **12 are SPEC-DOC-031** on the backlog surface — **pre-existing curation debt, not a regression**; see `## Drifts › spec-doc-031-warning-debt-unmasked-not-caused` and QA-1 under `## Intake candidates`. **The pre-archive measurement is 16 / 11** (`4de25057`, T-120-08/09 captures); the 12th warning is `spec-doc-031-citation-classes` and is **caused by this closure's own archive move** — `git mv`-ing `specs/releases/v0.12.0/` into `_archive/` turns this release's SPEC and CLOSURE into archived documents, and an archived document naming a non-terminal ACTIVE slug is exactly SPEC-DOC-031's evidence source. Every closure reproduces this, one warning per non-terminal slug it names. A5.5's literal "0 warnings attributable to the backlog surface" is therefore **not met**, recorded rather than rounded into a pass. The remaining 5 are pre-existing token-drift/heading-lint and two SPEC-DOC-036 archived-audit warnings, none naming a `T-120-*` symbol or path. Captures `…/T-120-08-V4-specs-doctor.txt`, `…/T-120-08-V4-specs-doctor-final.txt`, `…/T-120-09-V-specs-doctor.txt`; shipped-tree figure re-measured by `code-reviewer` at `9d079389` |
| V5 — Two-doctor agreement, R-13 (A5.6) | both doctors over the same consolidated tree and over a planted-violation tree | Agreement confirmed on **both** trees: every tree `backlog doctor` accepts, `specs doctor` accepts; every planted ACTIVE-schema violation is rejected by `backlog doctor` with an ERROR and `specs doctor` never contradicts it. QA exercised the planted-violation fixture matrix directly, not by inference |
| V6 — Dead-surface zero-hit (A4.1) | `grep -rn` for the A4.1 symbol list under the SPEC §3 standing exclusions | **Zero hits** for `removal_lifecycle`, `BacklogRemovalLifecycle`, `consume_at_release_definition`, `remove_at_closure`, `apply_removal`, `write_consumed`, `parse_consumes_line`, `shipped_anchors_for`, `build_backlog_removal_lifecycle`, `_fake_spec_stub`, `_FAKE_BACKLOG_CANARY_SLUG`. `read_consumed` and `LEDGER_FILENAME` survive with `tests/unit/test_backlog_ledger.py` **unmodified** (`git diff 523f0d8d..HEAD` empty) |
| V7 — Retired-check zero-hit (A5.4) | `grep -rn` for the A5.4 symbol list | **Zero hits in all code** (`dadaia_workspace/**`, `tests/**`) for `check_backlog_schema`, `BACKLOG_BULLET_RE`, `BACKLOG_HOTFIX_RE`, `_HOTFIX_STALE_HOURS`. Two **prose** hits outside code are disclosed rather than suppressed: `specs/backlog/BACKLOG.md` (the PM-authored OD-2 provenance text — this release's own document quoting the symbol it retires) and `specs/assets/architecture/doctor-decomposition.md`, a pre-existing stale diagram already stale before this release on an unrelated axis. Listed under `## Intake candidates` |
| V8 — Never-delete count (A7.2) | slug-set difference both ways, pre vs post, captured under `.dadaia/tmp/<agent>/<YYYYMMDD>/` | **82 = 82, both differences empty.** Pre-state = 31 live files ∪ 30 index rows ∪ 46 `_archive/` files ∪ 20 LEDGER lines ∪ the terminal tables; post-state = 30 ACTIVE + 52 LEDGER. Capture `.dadaia/tmp/project-manager/20260815/T-120-07-set-equality-proof.json` (sorted sets, both diffs, and the canonicalization map for the nine `20260815-` archival prefixes). **Independently re-derived by QA** through `document.load_document` on the live tree rather than trusted from the capture: 30 ACTIVE, 52 LEDGER, 0 parse errors, `active ∩ ledger = ∅`, 82 unique — exact match |
| V9 — Rename-not-delete (A9.1, A9.2, A4.3) | `git log --diff-filter=D -- specs/backlog/` over the range; `git diff --stat` over `specs/_archive/` | `git show --stat af55e798 -- specs/backlog/` with git's default rename detection → **32 renames, zero bare `D` entries**; `git log --diff-filter=D 523f0d8d..HEAD -- specs/backlog/` → **empty**; `git diff --stat 523f0d8d..HEAD -- specs/_archive/` → **empty**. QA re-checked all three live |
| V10 — Import purity (A1.6) | `lint-imports --config setup.cfg --no-cache` | **9 contracts kept, 0 broken.** `document.py` imports nothing from `cli`, `infrastructure` or `hooks`. One sanctioned ignore edge was added — `doctor_governance.py → features.backlog.document`, leaf-to-leaf, the PLAN §6 fallback — ratcheting `_RECORDED_IGNORE_EDGE_CAP` 15 → 16 with an inline comment naming it. Additive, not a contract weakening; see `## Drifts › ratchets-moved-by-in-scope-deletions` |
| V11 — Projection (A6.3, A8.4) | `dadaia public stage` → `install --target all` → `doctor` | Green, including **`[ok] public-privacy`**; zero `[error]` lines. Both edited skills byte-identical across `dadaia_workspace/public/skills/`, `.claude/skills/` and `.agents/skills/` (4 projections verified) |
| V12 — Consumer recipe (A6.5) | F-10, R-02, R-13 walked on a scaffolded context | F-10 plants its malformed item as an ACTIVE subsection and is caught; R-02's retired consumed-backlog-ledger clause is gone, replaced by the assertion that the declared `**Consumes:**` slug resolves to an ACTIVE subsection; R-13's gate-is-a-validator rule holds over the new shape (V5). A reader following the three verbatim reaches a passing result with no manual repair |
| V13 — CI (A6.4) | the `backlog-doctor` job green on the consolidated tree; full workflow green on the PR | **Due at T-120-14 (milestone b), not a gap here.** The job name, verb and arguments are unchanged (`dadaia backlog doctor --specs-dir specs --source-root .`), and V2 is that exact command green on the exact tree the job will run against. The full-workflow green is the ship task's evidence |
| V14 — Fresh-context no-op (A1.2, A2.8, A3.1, A3.5) | `specs init` into a temp dir, then both doctors | **PASS, live-exercised on a scratch context.** `dadaia specs init` scaffolds a clean `BACKLOG.md` skeleton (`## ACTIVE` + `## LEDGER`) that both doctors accept out of the box; deleting the document outright and re-running both still reports clean / `0 errors, 0 warnings` — absence is a legitimate no-op, not an error. This is also the check that caught the scaffolder stub defect (see `## Drifts`) |

Five evidence rows that are not PLAN §9 validations but govern this closure. R4 and R5 are the
pre-ship pair that reopened it:

| Description | Source | Evidence |
|-------------|--------|----------|
| R1 — QA verdict on the increment | `qa-engineer`, T-120-11 | **APPROVED** — 61/61 acceptance ids A1.1–A9.6 independently re-verified at `4de25057`; 0 CRITICAL, 0 HIGH, 2 non-blocking MEDIUM (QA-1, QA-2), both proven pre-existing. `specs/releases/v0.12.0/ALPHA-1-QA.md` + handoff `2026-08-15T231133Z-qa-engineer-v0.12.0-alpha1` |
| R2 — Milestone-(a) security review | `security-reviewer`, T-120-02 | **APPROVED** over `origin/develop..develop` for the definition delta, keyed to the pushed tip; push gate exit 0 with no `--no-verify`. Handoff `2026-08-15T204611Z-security-reviewer-v0.12.0-definition-push` |
| R3 — Anchor-semantics and ledger preservation (A4.2, A9.4) | QA direct diff | Five test modules confirmed **byte-unmodified** since `523f0d8d`: `test_backlog_ledger.py`, `test_backlog_classifier.py`, `test_backlog_subject_registry.py`, `test_backlog_models.py`, `tests/unit/backlog/test_classifier_clamp.py` |
| R4 — Pre-PR six-axis code review (T-120-14, first half) | `code-reviewer`, over `git diff 85aa721a..9d079389` — 16 commits, 85 files, +3,658/−2,117 | **APPROVE**. **0 CRITICAL, 0 HIGH**, 2 MEDIUM, 7 LOW, 3 INFO across all six axes (the handoff's `metrics` and its `findings[]` array agree at 7 LOW; a briefing that quoted 6 undercounted by one). Six gates re-run locally by the reviewer rather than trusted (`ruff format --check`, `ruff check`, `mypy --strict` over 263 files, `lint-imports` 9/9 kept, 172 targeted tests, both doctors); the 82 = 82 never-delete identity re-derived independently through the shipped parser (28 ACTIVE / 54 LEDGER / 0 parse errors / `active ∩ ledger = ∅`); rename-not-delete re-verified (32 renames, zero `D` entries, zero modifications under `_archive/`); privacy sweep of the 56.9 KB document, every v0.12.0 archive document and the whole `public/` diff found nothing. Handoff `.dadaia/handoff/dadaia-workspace/2026-08-15T233757Z-code-reviewer-v0.12.0-prepr.handoff.json`. Both MEDIUMs are dispositioned in this document: M1 fixed at R5, M2 corrected in V4 and in the drift below |
| R5 — M1 remediation, pre-ship (fence-aware parsing) | `software-engineer`, commit **`a76d55bf`** | Root-cause fix, not a guard: `_fenced_ranges()` scans the document once and pairs each opening fence with the next marker of the same character and length ≥ its own (CommonMark same-char/at-least-as-long close), and `_top_level_sections`/`_parse_active` filter their heading matches through `_outside_fences` — so a `##`/`###` line inside a fenced span is content, never structure. An unclosed fence at EOF is now a located `DocumentError` folded into BL-SCHEMA, so the model can never silently shrink. **5 tests added**, 4 of them fence-aware RED→GREEN (the reviewer's exact repro; a fenced `###` spawning no phantom item; a 4-backtick outer fence not closed by a nested 3-backtick example; the unclosed-fence-at-EOF backstop) plus 1 pinning writer ↔ scaffolder ↔ parser agreement (`scaffolder._BACKLOG_STUB == new_artifacts._BACKLOG_DOCUMENT_SKELETON`, and the scaffolded skeleton round-trips `load_document` with zero errors — the LOW that asked for V14's manual observation to become a ratchet). Post-fix full gate: **`2275 passed, 3 skipped`**, 0 failed; `mypy --strict` 263 files clean; `lint-imports` 9/9. **Live document identical before and after: 30 ACTIVE / 52 LEDGER / 0 errors** — the fix changes no live parse. Handoff `.dadaia/handoff/dadaia-workspace/2026-08-15T235605Z-software-engineer-v0.12.0-m1-fence-aware.handoff.json` |

## Drifts

### spec-doc-031-warning-debt-unmasked-not-caused

**Description:** A5.5 asks for `specs doctor` reporting **0 errors and 0 warnings attributable
to the backlog surface** on the consolidated tree. It reports 0 errors and **11 SPEC-DOC-031
WARNINGs before this closure archives itself, 12 after** — the shipped figure is **0 errors, 17
warnings, 12 SPEC-DOC-031**. The eleven that are pre-existing curation debt:
`test-suite-remediation-stewardship`, `retire-dead-hotfix-surface`,
`consumer-side-validation-round`, `thin-wrapper-projected-scripts`, `bug-picked-ledger-event`,
`codex-persona-law-context-dehydration`, `python-env-interpreter-probe-hardening`,
`changelog-version-axis-reconciliation`, `commit-paths-index-scope-hardening`,
`commit-message-scanning-residual`, `baseline-carve-out-review-cadence`. Each is an ACTIVE item
left at a non-terminal status while an archived SPEC or CLOSURE names its slug outside a
`## Backlog returns` section.

**The twelfth is `spec-doc-031-citation-classes`, and this closure causes it.** The mechanism is
structural rather than a defect: `git mv`-ing `specs/releases/v0.12.0/` into `_archive/` turns
this release's own SPEC and CLOSURE into *archived documents*, and both name that slug — the SPEC
in its scope reasoning, this file under `## Dispositions › Explicit non-flips` — while the entry
itself stays ACTIVE at `candidate`. An archived document naming a non-terminal ACTIVE slug **is**
SPEC-DOC-031's evidence source, so the warning is the check working. **Every closure reproduces
this**, one new warning per non-terminal slug it names, and a closure that measures its
`specs doctor` figure before its own archive move will always understate it by exactly that count.
The first draft of this document measured at `4de25057` and stated 16 / 11 as the shipped figure;
the pre-PR review re-measured at `9d079389` and found 17 / 12. The corrected pair is what this
document now carries, in V4 and here.

**Resolution:** Recorded as **not met**, not rounded into a pass, and the eleven proven
**pre-existing** twice over rather than argued. The implementer ran the pre-cutover
`doctor_governance.py` against a `git archive` snapshot of the parent commit and saw the same
class fire (citing 10 slugs); QA then repeated the check independently in a `git worktree`
snapshot at `9543ca8c` with the pre-cutover code invoked directly, and counted **11** — the
accounting correction is QA's, and **11 is the pre-existing-debt figure this document carries;
12 is the shipped-tree figure**, the difference being this closure's own archive move. The
re-target did not create the warnings: it reads the same live data through a new surface and
reports the same drift. The right fix is **backlog curation**, which is `project-manager`'s lane
and needs an operator disposition per entry — it is not an implementer's ad-hoc edit inside a
release that did not pick those eleven entries. Routed to `## Intake candidates` as **QA-1**,
with the twelfth slug added there. The severity matters to the judgement: SPEC-DOC-031
is WARNING-only by ADR-6 because it has a known false-positive class, so neither doctor's exit
code moves and no gate is weakened by leaving it standing.

The self-inflicted twelfth carries its own lesson, and it is the v0.9.0 lesson axis: **a
closure's stated numbers must resolve against the tree it closes**, not against the tree it was
drafted on. The cheap standing fix is a note in `dd-release-closure` that archiving adds one
SPEC-DOC-031 per non-terminal slug the release names, so the next closer measures after the move
or states the delta — listed under `## Intake candidates`.

**Memory updates:** `specs/memory/product/sdd/specs-doctor.md` — the check inventory now states
what SPEC-DOC-031 iterates and that it is WARNING. Neither the eleven-item debt nor the
archive-move increment is product truth; both are recorded here and nowhere in memory.

### picked-entry-anchor-repoint-across-the-cutover

**Description:** Both picked entries bind typed `intents[]` to code subjects, and this release
**deletes** several of the subjects its own picked entries name. Two separate points in the
release hit it. At T-120-03, `backlog-tooling-reconciliation`'s per-entry file carried an intent
bullet pointing at `removal_lifecycle.py#BacklogRemovalLifecycle` — a module that task was
deleting — which would have made `backlog doctor` fire BL-SCHEMA (unresolvable subject)
permanently on a `picked`, non-`idea` entry, breaking the standing green rule for every
subsequent commit. At T-120-08 the same entry, now an ACTIVE subsection, still named
`preview.load_backlog_items` and `_BACKLOG_AGGREGATE_FILES`, both deleted by that same cutover.

**Resolution:** Both fixed in the commit that caused them, and both disclosed at the time.
T-120-03 removed exactly the one dangling bullet — title, status, description, acceptance and
every other intent untouched — and added a dated note to the entry's own pick-provenance section
explaining the removal for the PM and the operator (`2384309e`). T-120-08 **repointed** rather
than removed: `document.py#load_document` and
`doctor_governance.py#_BACKLOG_SINGLE_SOURCE_FILES` are the exact post-cutover replacements for
the two deleted anchors, each carrying an inline note inside the `**Intents:**` block saying why
the ref moved (`af55e798`, disclosed in the commit message; QA confirmed
`_BACKLOG_SINGLE_SOURCE_FILES` exists at `doctor_governance.py:52`). The cost worth naming: both
edits are `software-engineer` writing inside `specs/backlog/**`, which is `project-manager`
surface, and the release's own ownership rule (SPEC §2, "no agent writes outside its lane") bent
for them. It bent for a real reason — a picked entry must stay BL-SCHEMA-resolvable across the
whole picked window and the only commit that can keep it resolvable is the one that moves the
anchor — but a cross-lane edit made under green-gate pressure is exactly the kind that gets made
silently, and these were not: each rides its own commit message and its own handoff finding, and
the PM reviewed them. The structural lesson is that an entry which binds intents to code the
release deletes has a lane problem built into it from definition; the fix belongs in how picked
entries are written, not in the implementer's discretion.

**Memory updates:** none — an intra-release anchor repoint is not current product truth. The
surviving general fact, that BL-SCHEMA fires on an unresolvable subject for any item at
`candidate` or beyond, is already recorded in `sdd-bug-backlog-governance.md`.

### frontmatter-yaml-partial-supersession

**Description:** TASKS' recorded-supersession table named **four** whole test modules deleted
because their subject no longer exists. The shipped delta carries a **fifth**, partial
supersession that the table did not predict: three of the four tests inside
`tests/unit/features/backlog/test_frontmatter_yaml_parse_error.py` were deleted at the cutover
because they exercised the per-entry loader path specifically, leaving the module alive with its
document-model coverage.

**Resolution:** Disclosed, not silent — named in the T-120-08 cutover commit message and in the
module's own docstring, and independently confirmed by QA's test-pyramid audit of the delta as
matching PLAN §2's "migrated" disposition rather than pruning-to-go-green. It is recorded here
as a **fifth supersession** in `## Test dispositions` so the release's own count is 5, not the 4
TASKS declared. Stating it plainly: the SPEC's standing rule is that any deletion outside the
four recorded supersessions requires a `qa-engineer` verdict with evidence, and this deletion
was made by the implementer before that verdict existed. What makes it acceptable rather than a
violation is that the verdict arrived and was affirmative — QA reviewed the exact three deleted
tests against their replacement coverage and confirmed nothing was weakened — but the order was
disclose-then-verify, not verify-then-delete. The cheap fix for next time is to enumerate
partial supersessions in TASKS at definition, which is only possible if the definition reads the
test modules and not just the production modules.

**Memory updates:** none — test-module inventory is not memory's subject.

### scaffolder-stub-tripped-the-new-single-source-invariant

**Description:** `dadaia specs init` scaffolded `candidates.md` and `ideas.md` stubs into
`specs/backlog/`. The moment SPEC-DOC-035 became the single-source invariant, **every fresh
workspace init produced a tree that immediately failed its own validator** — the scaffolder was
shipping the drift the new check exists to detect.

**Resolution:** Fixed at the root inside the cutover commit rather than exempted:
`_CANDIDATES_STUB` and `_IDEAS_STUB` are replaced by a single `_BACKLOG_STUB` skeleton
(`## ACTIVE` + `## LEDGER`) that matches byte-for-byte what `backlog_new` writes when it finds no
document, so the producer and the validator agree by construction — R-13's rule applied to the
scaffolder, not just to the CLI. Live-verified at V14 on a scratch context. The alternative —
adding `candidates.md`/`ideas.md` to SPEC-DOC-035's exclusion list — would have kept a green
gate while shipping consumers a broken first experience, which is the failure class
`DADAIA.md` §6 names: an internal gate that diverges from real consumer behaviour is itself a
bug. Worth naming as a definition miss: neither the SPEC nor the PLAN listed `scaffolder.py` in
any write set, and the release only found it because a validation step actually ran `specs init`
instead of reasoning about it.

**Memory updates:** none beyond `sdd-bug-backlog-governance.md`'s statement of what
`specs/backlog/` now holds — the scaffolder producing a conformant skeleton is the same fact
seen from the other side.

### ratchets-moved-by-in-scope-deletions

**Description:** Two shrink-only or cap-bounded ratchets moved as mechanical consequences of
in-scope deletions. `tests/integration/test_repo_self_scan.py`'s `_TESTS_SCOPE_BASELINE` lost a
row (29 → 28, home-abs-path 14 → 13) because `tests/unit/test_backlog_ledger_writer.py` — one of
the four recorded supersessions — was deleted; the baseline's own docstring mandates the shrink,
and left unshrunk `test_every_baseline_row_still_produces_a_hit` fails.
`tests/contract/test_import_linter_ignore_cap.py`'s `_RECORDED_IGNORE_EDGE_CAP` moved **up**,
15 → 16 (`features-no-cross-feature` 1 → 2), for the new leaf-to-leaf edge
`doctor_governance.py → features.backlog.document`.

**Resolution:** Both recorded rather than absorbed, because they move in opposite directions and
only one is unambiguously benign. The self-scan shrink is the ratchet working exactly as
designed — a baseline that can only go down went down, and the test that would have failed is
the one proving no row was orphaned. The import cap going **up** is a deliberate, argued
exception carrying an inline comment naming the edge, and `lint-imports` still reports 9/9
contracts kept, so no contract was weakened; but a cap that rises is a cap that can be raised
again, and the honest framing is that this release spent one unit of a budget rather than
discovering a free one. The edge itself is the PLAN §6-sanctioned fallback: `specs doctor`'s
governance check must read the backlog document model, and the alternative — duplicating the
parser inside `features/specs` — is worse than one recorded leaf-to-leaf import.

**Memory updates:** none — `architecture.md` states that import-linter contracts cap deliberate
legacy exceptions, which is unchanged; it does not carry the cap's numeric value, and should not.

### stray-capture-path-self-caught

**Description:** During implementation a validation capture was briefly composed toward a
`.dadaia/` path resolved from a cwd inside `repos/dadaia-workspace/` rather than from the
workspace root — the exact failure `DADAIA.md` §4 names as corrupting context resolution for
every tool that walks the tree, and which this workspace has already registered as a drift bug
in another context.

**Resolution:** Self-caught by the implementer and corrected in the same session, before any
commit. Verified at closure: **no `.dadaia/` directory exists anywhere inside the repo working
tree**, and every capture this release cites resolves under the workspace-level
`.dadaia/tmp/{software-engineer,project-manager,qa-engineer}/20260815/`. Recorded rather than
dropped for the same reason v0.11.0 recorded its reservation slip: it was caught by the agent
that made it, with no reviewer and no hook in the path — the gate's root whitelist governs the
workspace root, not a repo-local `.dadaia/` — so "nothing was watching" is precisely the
condition under which this discipline decays. The mitigation already exists in law and in the
handoff-emitter skill's Step 0 (resolve the workspace root by walking up to the first ancestor
that **already** contains `.dadaia/`, and never create one); what this occurrence adds is
evidence that the rule needs re-reading whenever an agent runs with its cwd inside a repo, which
is most of the time.

**Memory updates:** none — a corrected working-tree slip is not product truth. The invariant it
touches is already law (`DADAIA.md` §4) and already enforced by `specs doctor`'s structural
check on a repo-local `.dadaia/`.

### t-120-07-folding-adjudications

**Description:** Folding 31 files plus a 30-row index into one document surfaced four
irregularities the source material could not resolve mechanically. The PM adjudicated each while
authoring the document and disclosed all four; they are recorded here because each is a judgement
call that a later reader could otherwise mistake for a transcription error.

**Resolution:**

- **`tag-push-carve-out-reachability` resolves to LEDGER only** (grill P6). It was the 31st live
  file against 30 index rows — the drift that proved the double-write was already costing. Its
  work shipped in v0.9.0 and it already carried a `DELIVERED · v0.9.0` LEDGER row, so
  materializing an ACTIVE subsection for it would have manufactured a live candidate out of
  finished work. The file was flipped terminal and archived with the other 31 moves; the LEDGER
  row is the record.
- **Nine `20260815-` archival prefixes canonicalized.** Archived files carried date-prefixed
  names whose slugs differ from the slug the same item carries in the index or the ledger. A
  canonicalization map — captured inside the set-equality proof, not applied silently — resolves
  each prefixed name to its canonical slug so the 82 = 82 identity is an identity between *items*
  and not between *filenames*. Without the map the count would have been trivially satisfiable by
  double-counting the same item under two names, which is the exact way a never-delete proof
  fails while looking green.
- **Two workflow-era entries carry no version.** `workflow-model-governance-operator-profiles-and-context-overlays`
  and `workflow-step-handoff-data-plane-cleanup` were terminal in their own frontmatter but named
  no release, because the workflow engine that owned them was demolished in v0.3.0. They take
  `DELIVERED · workflow-engine era, terminal frontmatter (engine removed v0.3.0)` in the
  release-or-reason field — the grammar's third field accepts a reason precisely so a record
  without a version is not forced to invent one.
- **A third standing notice travelled to `_archive/`.** T-120-07 restated exactly two live
  standing notices in the document preamble (the pick-precedence notice and the undecided
  panel-telemetry operator question). The third — the git commit-identity de-personalisation
  question, PM decision record 3 — travelled into `_archive/` with `candidates.md` and is no
  longer on the live surface. That is the correct default for a PM decision record, but a live
  operator question is a different thing from a decision record, and this one is arguably still
  live. Surfaced under `## Intake candidates` so the operator can rule or direct a restatement,
  rather than being resolved by the closer.

**Memory updates:** none — folding adjudications are release-time judgement, not product truth.
The general rule they exercise, that nothing is deleted and an item leaves `ACTIVE` only by
gaining a LEDGER line, is already in `sdd-bug-backlog-governance.md`.

### t-120-08-single-commit-reservation-exception

**Description:** `dadaia-task-manager` asks for one `[-]` at a time and an isolated
`chore(tasks): start <id>` reservation commit before the work. T-120-08 is a **dual-owner**
task — `project-manager` sequenced with `software-engineer` inside one commit — and its write
set spans production Python, the governance checks, the test fixtures, a brand-new
`specs/backlog/BACKLOG.md` and 32 `git mv` renames. It landed as a single commit by explicit
design (ADR D1, TASKS' own "this is the release's serialization point"), which necessarily means
the marker discipline around it is one reservation covering two agents' work.

**Resolution:** The exception is **ratified in advance by the SPEC and TASKS**, not taken
unilaterally at implementation time, and that is the whole difference between an exception and a
violation. The reason is structural rather than convenient: the tooling cannot be pointed at a
document that does not exist, the document cannot be committed while a per-entry loader is still
live to parse it (grill P3/P4), and the governance re-target must ride the same commit or emit
spurious WARNINGs (grill P4, ADR D9) — so any split produces a commit where the doctors
disagree, which the standing green rule forbids and which would then block the pre-commit gate
for every later commit. The cost is real and is named: the largest, highest-risk commit of the
release is also the one with the least granular marker trace and the least reviewable diff, and
the mitigation was to land every pure module and its tests in earlier commits (T-120-04…06) so
the cutover carries only wiring, deletions and renames. That mitigation worked — the diff is
dominated by renames — but the general shape stands as a caution: a task whose atomicity
requirement crosses an ownership boundary buys correctness with traceability, and should be
rare.

**Memory updates:** none.

### reopened-close-for-review-remediation

**Description:** This closure was written, committed and archived once already, at `9d079389`.
The pre-PR six-axis `code-reviewer` pass then read that archived tree and returned **APPROVE**
with 0 CRITICAL, 0 HIGH — and **2 MEDIUMs**, one of which was a real defect in the module this
release exists to ship: `document.py`'s section splitting was not fence-aware, so a `##` line
inside a fenced example in an ACTIVE Description silently truncated `## ACTIVE` and dropped every
later item with `errors == ()`. The second MEDIUM was the stated-figure staleness corrected above.
Both landed on a release that was, by its own ordering, already finished — and the code MEDIUM had
landed on an artifact under FROZEN `specs/_archive/`, where the reviewer's own recommendation was
necessarily "do not edit; carry it in the PR body".

**This is the third occurrence of the same shape** — v0.9.0, v0.11.0, and here. The ordering that
produces it is structural: T-120-13 archives the release, and T-120-14's pre-PR review is the
first reader of the finished closure. A reviewer who finds anything then is reviewing a document
it may not touch, and a code defect it can only route forward.

**Resolution:** The archive commit was **reset** and the close reopened, rather than shipping a
known defect with a note. That is the right call and the reasoning is worth stating, because the
cheaper path was available and was refused: M1 is a silent-under-coverage failure in a parser
whose module docstring promises "diagnostic, never throwing", reachable by exactly the activity
the document is curated by — a PM hand-editing `BACKLOG.md`, where 23 of the live items already
carry fenced YAML spans. Shipping it would have meant the release that made the backlog a single
document also shipped the way to lose half of it silently. `DADAIA.md` §6 names the standard:
root cause on the executed path, RED test, fix, GREEN. The remediation did exactly that at
`a76d55bf` — four fence-aware RED→GREEN tests including the reviewer's exact repro, an unclosed
fence at EOF now surfacing as a located `DocumentError` folded into BL-SCHEMA rather than a
silently shrunken model, and the live document verified byte-identical in parse before and after
(30 ACTIVE / 52 LEDGER / 0 errors). The LOW asking for a writer↔scaffolder↔parser agreement pin
rode the same commit, converting V14's one-off manual observation into a standing test.

The costs are named rather than absorbed. **First**, a reset of an archive commit is history
rewriting on a local branch — permissible only because `feature/v0.12.0` is local-only and
unpushed by the four-branch contract (`dadaia-gitflow`), and it would have been forbidden had the
close already merged into `develop`. **Second**, this document's evidence had to be re-derived
against a moved tree: the suite count, the `specs doctor` pair and the disposition sweep were all
measured against `9d079389` and are now stated against the re-close, which is precisely the class
of error the reopen was called to fix, so each is labelled by the run that produced it.
**Third**, the reviewer's remaining findings did not get the same treatment — they are routed to
`## Intake candidates` as residuals, because a reopen that expands to absorb every LOW is not a
reopen, it is a new release.

The structural lesson is the one already owned by the live backlog entry
`flat-release-ship-task-evidence` and is **not** re-raised here: a flat release archives before
its own ship review reads the closure, and every finding after that point costs either a reset or
a lie. The alternative — reviewing the closure *before* the archive move — is a TASKS-template
change, not this document's to make.

**Memory updates:** none — a reopened close is release-time process, not product truth. The fix
itself **is** product truth and is already carried by
`specs/memory/product/sdd/sdd-bug-backlog-governance.md`'s statement that parsing is diagnostic
and never-throwing, which the fence-aware fix makes true in the one case where it was not.

### missing-reservation-trace-for-t-120-12-13

**Description:** `dadaia-task-manager` requires an isolated `chore(tasks): start <id>` commit
flipping `[ ]` → `[-]` **before** the work, so that a reservation is observable to a parallel
session. Reservation commits exist for T-120-03, 04, 05, 06, 09, 10 and 11; they are absent for
T-120-08 (a disclosed exception, see the drift above) and — undisclosed until now — for
**T-120-12 and T-120-13**, the two `product-engineer` tasks of this closure. The markers
themselves are correct at every point; what is missing is the trace.

The cause is plain and worth recording exactly: `product-engineer` was **dispatched straight into
the work** — the briefing named the task and the phase, and authoring began without the marker
flip first riding its own commit. The closer has no shell, so its marker flips are staged and
committed by the dispatcher along with the artifact they accompany, which collapses reservation
and completion into one commit by default. Nothing blocked it: the SDD gate reads no `TASKS.md`,
and the pre-commit hook warns without refusing, so the only enforcement this rule has ever had is
the agent's own discipline plus a reviewer's eye — and it was a reviewer's eye that caught it.

**Resolution:** Recorded here as a real gap, not argued away. It is genuinely low-consequence in
this instance — the two tasks are strictly serial, single-owner, and no parallel session existed
to be misinformed — but the argument "no one was watching, so it did not matter" is the same
argument that retires the rule, and this release already recorded one drift
(`stray-capture-path-self-caught`) on exactly that reasoning. The honest framing: a shell-less
agent cannot make a reservation commit *itself*, so for `product-engineer` tasks the discipline
is really an obligation on the **dispatcher** to commit the flip before relaying the work. That
is a small, mechanical fix and it belongs with the ship-task marker gap it rhymes with, in the
live entry `flat-release-ship-task-evidence` — so it is folded there rather than raised as a new
intake candidate.

This drift also **corrects a claim TASKS carried**. The T-120-13 header asserted that the
T-120-12/13 reservation-trace absence was "disclosed in CLOSURE Drifts" when no such drift
existed — a forward reference to a disclosure that had not been written. The reviewer verified
the `## Drifts` section and found only the T-120-08 exception. The claim is now true: this is
that drift, and the TASKS note is repointed to it by name.

**Memory updates:** none — marker discipline is process, already stated in `dadaia-task-manager`.

## Memory updates

All memory writes landed in the CLOSURE phase (`ACTIVE.md` set to `phase: CLOSURE` **before**
the first write) and **before** this file, holding the finalization order memory → CLOSURE →
archive. They rode `f446b9ce` and are **untouched by the reopen** — only the archive commit was
reset, so the atoms below are on the branch exactly as described and are not re-written by the
re-close. Every SPEC §5 row is discharged below, file by file, including the rows that resolve to
"no change". No atom gained a `Changelog`, `History`, `Histórico` or `Versions` section, and none
narrates a past version — the pre-consolidation shape is described nowhere in memory, only here
and in `_archive/`.

- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — the `## Backlog` section's
  pending-consolidation paragraph ("the physical backlog has not been consolidated yet … the
  `dadaia backlog` verbs still read and write that per-entry model") is **replaced** by the
  shipped truth, in four paragraphs: what `specs/backlog/` now holds (`BACKLOG.md`, `README.md`,
  `_archive/`, plus `remote-bugs/` where it exists) and that `_archive/` is the historical store;
  the `document.py` model — five required subsection keys plus optional `Intents`, the four-field
  LEDGER grammar, diagnostic never-throwing parsing, absent document as an empty model; the four
  BL-* codes with BL-STALE's three ORed conditions and the `idea` intents exemption, plus
  `backlog new`'s append-and-refuse contract, the pre-commit and CI wirings, and `specs doctor`'s
  two WARNING backstops (SPEC-DOC-031 over ACTIVE subsections, SPEC-DOC-035 as the single-source
  invariant with its exclusions); and the `**Consumes:**` mechanism stated **once** — provenance,
  executed by purge-on-pick at definition and the closure sweep, with `read_consumed` surviving
  only as a pure reader and a BL-STALE input. `## Runtime State` drops the per-entry-files clause
  and names `specs/backlog/_archive/` as the historical store. `token_estimate` 950 → 1300;
  `tldr` and `summary` **unchanged** — both were already written against the single-source
  doctrine and remain accurate, which is why the catalog needs no `tldr`/`summary` edit.
  `last_updated` already 2026-08-15. This atom is the one `ai-engineer` flagged as stale at
  T-120-10; this write is that fix.
- `specs/memory/product/sdd/specs-doctor.md` — the governance-checks bullet is rewritten from
  "backlog status vocabulary and archive consumption" to the post-re-target inventory: the two
  backlog checks, both WARNING, with SPEC-DOC-031's iteration surface and its
  `## Backlog returns` carve-out and SPEC-DOC-035's single-source invariant and exclusions; the
  explicit statement that no check reads `BACKLOG.md` as a per-slug entry, so no finding is ever
  keyed to a phantom `BACKLOG` slug (the A5.2 regression, recorded as a property rather than as a
  test name); and the statement that there is **no** per-entry frontmatter schema check any more —
  the entry schema is `backlog doctor`'s BL-* codes over the document model, and specs doctor
  holds no second opinion. That last sentence is how the retirement of SPEC-DOC-012/022/023 is
  recorded as current truth: memory says what the inventory **is**, never what it used to
  contain. `token_estimate` 212 → 355; `last_updated` 2026-08-07 → 2026-08-15; `tldr`/`summary`
  unchanged and still accurate.
- `specs/memory/product/catalog.json` — the `token_estimate` fields of the two touched entries
  updated to match their atoms' frontmatter (950 → 1300, 212 → 355). No slug added, removed or
  re-ranked; no `tldr` or `summary` changed, so `index.md` needs no ripple. **Owed to the
  dispatcher, and only half discharged at the first close:** both new `token_estimate` values are
  the closer's estimates against the generator's `round(words × 1.35)` formula, not measured —
  `product-engineer` has no shell. `generate-memory-catalog.py` **was** re-run (`generated_at`
  `19:14:04Z` → `23:26:01Z`, catalog now mirroring the atoms), but the generator **copies
  frontmatter rather than recomputing it**, so `sdd-bug-backlog-governance.md`'s declared `1300`
  still stands against the linter's computed **≈1845 — 42% drift against its own 20% threshold**,
  and is one of the 17 `specs doctor` warnings. `specs-doctor.md`'s 355 measured accurate and
  reports `[OK]`. **Still owed at the re-close:** run `lint-memory-atoms.py`'s computed value into
  the atom frontmatter, then re-run the catalog generator — a mechanical dispatcher step, not a
  closer edit, and the drift *class* (a generator that mirrors an unmeasured field) is listed
  under `## Intake candidates`. A fabricated exact figure would still be worse than a declared
  estimate.
- `specs/memory/architecture.md` — **no change**, as SPEC §5 predicted, and checked rather than
  assumed. The atom names no `features/backlog/**` module, no doctor check id and no import-linter
  cap value: its backlog sentence is "Backlog and bugs own intake consistency and event-sourced
  bug state", which is layer-level and stays true across the cutover. No layer rule, port,
  dependency direction or runtime-state entry moved; the one new module is a pure `features/`
  leaf and the one new ignore edge is a recorded exception of a kind the atom already describes
  generically.
- `specs/memory/tech-stack.md` — **no change:** no dependency, command or language version moved;
  `document.py` is stdlib-only.
- `specs/memory/product/index.md` — **no change:** no feature added, removed or re-ranked, and
  the catalog table renders `tldr`, which did not change for either atom. (Contrast v0.10.0 and
  v0.11.0, where a changed `tldr` forced this ripple.)
- `specs/memory/quality-assurance.md` — **no change:** the test-stewardship doctrine was applied,
  not amended. The atom's suite census is not touched by this release's closure; it is a separate
  standing drift already owned elsewhere and is not silently corrected here.

## Dispositions

This release picked **two backlog entries and no bug and no audit**. The bug ledger carried
**zero** open bugs at pick time and none was registered during implementation; both 2026-07
audits were archived fully dispositioned by v0.8.0. The sweep is therefore complete with two
rows, no bug row and no audit row — nothing was silently dropped.

**This is the first disposition sweep executed on the single-source shape.** Under the retired
per-entry model a disposition was a frontmatter flip inside `specs/backlog/<slug>.md`; under the
shipped model it is a `LEDGER` line, and the entry's `ACTIVE` subsection is removed in the same
commit. Both were executed here, in this closure's own commit, against
`specs/backlog/BACKLOG.md`:

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/BACKLOG.md` › LEDGER line `backlog-tooling-reconciliation` (#30) | backlog | `DELIVERED — v0.12.0` | FR1–FR6 + FR8; A1.1–A1.6, A2.1–A2.9, A3.1–A3.5, A4.1–A4.6, A5.1–A5.6, A6.1–A6.5, A8.1–A8.4 verified (`ALPHA-1-QA.md`); V1–V7, V10–V12. Includes intake item **2-2**, delivered by FR4's retirement + FR8's checklist rewrite |
| `specs/backlog/BACKLOG.md` › LEDGER line `backlog-md-physical-consolidation` (#31) | backlog | `DELIVERED — v0.12.0` | FR7; A7.1–A7.7 verified; V8's 82 = 82 countable never-delete proof, independently re-derived by QA; V9's 32-renames/zero-deletions evidence |

Both lines read exactly `<slug> · DELIVERED · v0.12.0 · 2026-08-15` in the `dd-backlog-definition`
§2 grammar, and both ACTIVE subsections are gone from the same file in the same commit. The
document's own preamble arithmetic was updated with them: **30 ACTIVE + 52 LEDGER → 28 ACTIVE +
54 LEDGER**, the same **82** slugs, none added and none removed — the never-delete identity
survives its first closure, which is the property FR7 was picked to establish. The file still
round-trips `document.load_document`; the dispatcher's pre-commit `backlog doctor` run is the
mechanical confirmation, and BL-STALE would fire loudly on either slug if a subsection had been
left behind beside its new LEDGER line.

**The sweep text is unchanged, but the edit itself was executed twice.** It landed first in
`9d079389`, was reverted with that commit by the reopen, and is **re-executed identically here**,
riding the re-close commit — the same two subsections removed, the same two LEDGER lines
appended, the same preamble arithmetic. This is stated because the reopen returned
`BACKLOG.md` to 30 + 52 on disk, so a reader diffing the branch mid-reopen would have found the
sweep missing while this document described it as done; the 28 + 54 figure above is the state the
re-close commit carries, and `code-reviewer` independently re-derived exactly that shape through
the shipped parser at `9d079389` (28 ACTIVE, 54 LEDGER, 0 parse errors, `active ∩ ledger = ∅`,
82 unique slugs). One consequence worth naming: a disposition sweep is the one part of a closure
that is a **file edit rather than a document claim**, so it is also the one part a reset can undo
silently while the closure still asserts it. Re-verifying the counts against the tree — not
against this text — is the check that catches it.

Explicit non-flips, so a later reader does not read them as an incomplete sweep:

- **`retire-dead-hotfix-surface` (#4) stays ACTIVE at `candidate`.** SPEC-DOC-022 and 023
  disappeared as a *side effect* of retiring `check_backlog_schema`, but the `cli/commands/specs.py`
  hotfix verb and the `release_hotfix`/`closure_hotfix` templates are untouched and the entry is
  not picked. It must be rewritten **down to that residual** by the PM — **OD-2**, listed under
  `## Intake candidates`. `product-engineer` does not edit an unpicked entry, and the closer
  creates no backlog entry.
- **`test-suite-remediation-stewardship` (#2)** — untouched (SPEC §4.5). This release added
  **zero** e2e tests, so the LARGE census did not grow.
- **`spec-doc-031-citation-classes` (#10)** — untouched. Its citation-class refinement is a
  *semantic* change to SPEC-DOC-031; this release only re-pointed the check's iteration surface
  and left its ADR-6 false-positive class exactly as defined. It is the entry that would
  eventually retire most of QA-1's eleven warnings.
- **`bugs-jsonl-whole-blob-per-append` (idea)** — untouched (SPEC §4.6); `specs/bugs/**` is
  outside this release entirely.
- **`tag-push-carve-out-reachability`** — resolved to a **LEDGER-only** record by FR7, not a
  disposition of this release: its work shipped in v0.9.0 and it already carried that row. See
  `## Drifts › t-120-07-folding-adjudications`.
- **No bug status was flipped and no `dadaia bugs append` event was emitted by this release's
  scope.** Zero bugs open at pick time, zero registered during implementation.

## Test dispositions

No demotion, no quarantine expiry and no SCAFFOLD expiry occurred. The QA-reviewed suite ran
**2,270 passed / 3 skipped / 0 failed** and the shipped suite runs **2,275 / 3 / 0** — the five
added by the M1 remediation (R5). The e2e census is unchanged — `git diff --diff-filter=A`
over the range shows **zero** added files under `tests/e2e/`, exactly as TASKS' standing rule
required, and zero `quarantine`, `skip` or `xfail` markers were added anywhere in the range diff.
One new test module was added (`tests/unit/features/backlog/test_document.py`, 318 lines,
declaring `Intent: CONTRACT — v0.12.0 A1.1…` at its docstring); every other added test lives
inside a pre-existing module and declares its intent and size at birth. QA audited the whole
`tests/` delta (20 files) file by file rather than sampling.

**The five remediation tests are additions, not dispositions**, so they carry no row in the table
below — nothing was deleted, demoted, skipped or replaced to accommodate them. Four extend
`test_document.py` (fence-aware sectioning: the reviewer's exact repro RED→GREEN, a fenced `###`
spawning no phantom item, a longer outer fence not closed by a shorter nested one, and an
unclosed fence at EOF surfacing a diagnostic rather than a shrunken model); the fifth,
`test_scaffolder.py::test_scaffolded_backlog_skeleton_pins_writer_and_round_trips_load_document`,
is the SMALL contract test that pins `scaffolder._BACKLOG_STUB` equal to
`new_artifacts._BACKLOG_DOCUMENT_SKELETON` and round-trips the scaffolded skeleton through
`load_document`. That last one converts V14's manual observation into a standing ratchet, which
is the disposition-relevant fact: the release ends with **one fewer** manually-verified property
than it had at the QA close.

**Five supersessions, not four.** TASKS declared four whole-module supersessions; the shipped
delta carries a fifth, partial one, disclosed at the time and confirmed by QA — see
`## Drifts › frontmatter-yaml-partial-supersession`.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| supersession (1/5) | `tests/unit/test_backlog_removal.py` (whole module) | none needed — subject `features/backlog/removal.py` deleted by FR4; behaviour removed, not moved | TASKS T-120-03 table; `2384309e`; A4.1 zero-hit (V6) |
| supersession (2/5) | `tests/unit/test_backlog_ledger_writer.py` (whole module) | none needed — subject `features/backlog/ledger_writer.py` deleted by FR4 | TASKS T-120-03 table; `2384309e`; V6 |
| supersession (3/5) | `tests/integration/test_backlog_removal_loop.py` (whole module) | BL-STALE over the new shape — `tests/integration/test_backlog_doctor.py` (A2.6, A2.7) | TASKS T-120-03 table; `2384309e`; V3 |
| supersession (4/5) | `tests/unit/backlog/test_consumes.py` (whole module) | none needed — subject `features/backlog/consumes.py` deleted by FR4; `**Consumes:**` becomes provenance text (FR8) | TASKS T-120-03 table; `2384309e`; V6 |
| supersession (5/5, partial) | 3 of 4 tests inside `tests/unit/features/backlog/test_frontmatter_yaml_parse_error.py` | the module survives with document-model coverage; replacement named in its own docstring and in the cutover commit message | `af55e798`; QA test-pyramid audit of the delta (`ALPHA-1-QA.md`) |
| ratchet (not a deletion) | `tests/integration/test_repo_self_scan.py` `_TESTS_SCOPE_BASELINE` 29 → 28 rows | shrink-only baseline following supersession 2/5; the module's own docstring mandates the shrink | `2384309e`; `## Drifts › ratchets-moved-by-in-scope-deletions` |
| ratchet (not a deletion) | `tests/contract/test_import_linter_ignore_cap.py` `_RECORDED_IGNORE_EDGE_CAP` 15 → 16 | additive, inline-commented, 9/9 contracts still kept | `af55e798`; V10 |
| migration (not a deletion) | 12 modules adjusted in place (`test_backlog_doctor.py`, `test_new_artifacts.py`, `test_cli_newartifacts.py`, `test_precommit_backlog_scoping.py`, `test_backlog_precommit.py`, `test_governance_intake_not_gitignored.py`, `test_doctor*.py` family, `test_scaffolder.py`, the `_golden/` fixtures) | fixture shape migrated to the document model; every diff adds or migrates assertions, none removes one without a same-commit replacement | QA file-by-file delta audit |
| demotion | none | none — no LARGE test was replaced, removed or demoted; zero e2e tests added or deleted | `git diff --diff-filter=A … tests/e2e/` empty |
| quarantine expiry | none | none — no quarantine marker added, expired or restored | full-suite count 2270/3/0 at the QA close, 2275/3/0 shipped, both under `-m 'not quarantine'` |
| SCAFFOLD expiry | none | none — every added test declares `Intent: CONTRACT` or `Intent: SENTINEL` at birth | QA grep of every changed test file |

**Nothing was pruned, skipped or disabled to reach green.** Five test modules were confirmed
**byte-unmodified** since the branch base (`test_backlog_ledger.py` for A4.2; the four
anchor-semantics modules for A9.4), which is the load-bearing proof that the retirement took no
live control with it and that the classifier/registry semantics were preserved rather than
re-fitted. QA re-ran the suite itself and its count matches the implementer's, which is what
makes the 2,270 checkable rather than asserted; the shipped 2,275 is the same suite plus the five
remediation tests, re-run green at `a76d55bf`.

## Open decisions restated

**OD-1 — does the backlog keep typed `intents[]`?** Restated here, unresolved, so the operator's
eventual ruling has one current reference point. This release took the **conservative** reading
(ADR D7): `intents[]` survives as an **optional** `**Intents:**` key on each ACTIVE subsection,
carrying the same typed YAML in a fenced span, and the whole anchor machinery —
`subject_registry.py`, `classifier.py`, `cli/anchors.py`, the alias map and the
`backlog subjects` verb — is untouched, its four test modules passing unmodified. 25 of the 30
consolidated items carried an intents block, **23 of the 28 that remain after this closure's
sweep** — both picked entries were intents-bearing. The open question is whether the backlog *should*
carry typed intents at all, or whether an entry is prose plus a disposition and the anchor
binding belongs only to release definition. Arguments on both sides are now concrete rather than
theoretical: intents are what makes BL-SCHEMA able to catch an entry naming a subject that no
longer exists (it did so twice in this very release — see the anchor-repoint drift), and they are
also what made two picked entries need cross-lane edits mid-cutover to stay resolvable. **If the
operator rules that the backlog carries no typed intents, that retirement is its own release**
(SPEC §4.1) — it is not a closure edit and it is not folded into any picked entry.

**OD-2 — `retire-dead-hotfix-surface` (#4) must be rewritten down to its residual.** Recorded by
the PM at T-120-07 as an appended note on the entry, not executed. It is listed under
`## Intake candidates` because the rewrite is `project-manager` curation on an unpicked entry.

## Intake candidates

Residuals discovered during this release, **listed** for the PM's operator-facing intake report
(ADR #15, `dd-backlog-definition` §5). This closure creates **no** backlog entry and flips no
backlog status outside the two picked entries of its own sweep.

### To be adjudicated

No prior operator ruling covers these; the PM's next intake report presents each for approval,
rejection or discard.

- **QA-1 (MEDIUM) — twelve SPEC-DOC-031 warnings on the backlog surface, eleven of them
  pre-existing.** `test-suite-remediation-stewardship`, `retire-dead-hotfix-surface`,
  `consumer-side-validation-round`, `thin-wrapper-projected-scripts`, `bug-picked-ledger-event`,
  `codex-persona-law-context-dehydration`, `python-env-interpreter-probe-hardening`,
  `changelog-version-axis-reconciliation`, `commit-paths-index-scope-hardening`,
  `commit-message-scanning-residual`, `baseline-carve-out-review-cadence` — each an ACTIVE item
  at a non-terminal status while an archived release names its slug. Proven pre-existing twice
  (implementer snapshot, QA `git worktree` re-verification at `9543ca8c`); WARNING-only, so no
  exit code moves. **The twelfth is `spec-doc-031-citation-classes`**, added by this closure's own
  archive move — v0.12.0's SPEC and CLOSURE become archived documents naming that still-ACTIVE
  slug — and it belongs to the same disposition set, so the PM adjudicates twelve slugs, not
  eleven. **PM lane** — curation debt needing an operator disposition per entry, not an
  implementer fix, and the standing reason A5.5's literal text is unmet. The overlap is now
  direct rather than adjacent: the twelfth slug **is** entry #10, whose citation-class refinement
  would retire much of this class semantically rather than per-entry — adjudicate the two
  together, and note that #10 is now warning about itself.
- **QA-2 (MEDIUM) — `dd-release-closure/SKILL.md:93` still teaches the per-entry disposition
  shape.** The Dispositions-table template row reads
  `` `specs/backlog/<slug>.md` | backlog | `DELIVERED — <release-id>` ``, stale against the model
  this release ships: a disposition is now a LEDGER line inside `BACKLOG.md`. Confirmed
  pre-existing (`git diff 523f0d8d..HEAD` on the file is empty; last touched at v0.10.0) and
  outside every T-120-0x declared write set — FR6 covered the scaffold README, the consumer
  recipe and the CI comment; FR8 covered only `dd-backlog-definition` and `dd-release-definition`.
  **`ai-engineer` lane.** Worth flagging its urgency honestly: this closure is the *first*
  execution of the sweep on the new shape and it had to read past the template's own row to do it
  correctly, which is exactly the misfollow risk a stale template carries. Recommended before
  ship, but it is a documentation row, not shipped behaviour, and it belongs to a lane this
  release cannot write in. **Fold in a second edit to the same skill:** a standing note that a
  closure's own archive move adds one SPEC-DOC-031 warning per non-terminal slug the release
  names, so the next closer measures `specs doctor` *after* the move or states the delta — the
  exact trap this closure fell into (see the drift above), and one every closure will reproduce.
- **OD-2 — `retire-dead-hotfix-surface` (#4) rewritten down to its residual.** SPEC-DOC-022/023
  and `check_backlog_schema` are gone as a side effect of FR5; what remains of #4 is the
  `cli/commands/specs.py` hotfix verb and the `release_hotfix`/`closure_hotfix` templates, which
  are dead surface under the D4 revocation. The entry currently describes work that is partly
  already done. **PM lane** — rewrite-down on an unpicked entry (`dd-release-definition` §5's
  full-slug-granularity rule: a partially-shipped item is never declared consumed; it is rewritten
  to its residual by hand).
  **The rewrite-down must record an aggravation this release caused**, found by the pre-PR review
  (LOW): `dadaia specs hotfix open` reads `specs/backlog/candidates.md`
  (`cli/commands/specs.py:391`) as a pre-condition. Before v0.12.0 `specs init` scaffolded that
  file, so the check sometimes found it; after the cutover the file is never created and this
  repo's copy is archived, so the verb now prints
  `[WARNING] specs/backlog/candidates.md not found — cannot verify ## Hotfixes pendentes.`
  on **every** invocation in **every** workspace — occasional warning → **unconditional** one, on
  a consumer-facing verb. Worse, a user who complies by creating the file is then flagged by this
  release's own new SPEC-DOC-035 single-source invariant: the advice is now self-contradicting.
  The verb is dead surface under the D4 revocation, which is why the fix is #4's residual and not
  a patch here; the cheapest interim, if #4 stays unpicked, is dropping the `candidates.md`
  pre-condition block, since the file class it audits no longer exists.
- **The third standing notice no longer appears on the live surface.** The git commit-identity
  de-personalisation question (PM decision record 3) travelled into `specs/backlog/_archive/` with
  `candidates.md` at the cutover. T-120-07 restated exactly two live notices in `BACKLOG.md`'s
  preamble (pick-precedence, the undecided panel-telemetry bug question) and left this one
  archived. **Operator call:** rule on it, or direct the PM to restate it in the `BACKLOG.md`
  preamble at a later curation touch. Listed rather than restated by the closer, because
  `specs/backlog/**` prose is PM surface and reviving an archived operator question is a curation
  decision, not a closure one.
- **A stale architecture asset still names a retired symbol.** `specs/assets/architecture/doctor-decomposition.md`
  contains `check_backlog_schema` and was already stale before this release on an unrelated axis
  (SPEC-DOC-029 / `spec_context.lease`). Not a code hit — A5.4's zero-hit holds across
  `dadaia_workspace/**` and `tests/**` — and outside every write set here. **`software-architect`
  or PM lane**, whenever that diagram is next refreshed. LOW.

The five below are the pre-PR review's remaining findings — the ones the reopen deliberately did
**not** absorb (see `## Drifts › reopened-close-for-review-remediation`). Each is listed with the
reviewer's own severity, none is a ship blocker, and none was touched by `a76d55bf`. Two further
findings are dispositioned elsewhere in this document rather than here: the `specs hotfix open`
guaranteed-warning residual is folded into **OD-2** above, and the two task-table subject
mismatches plus the four stale `(sha owed)` markers are **corrected in place** under
`## Tasks completed`.

- **The `document.py` → `preview` private-import direction is inverted.** (review INFO)
  `document.py:34` imports the underscore-private `_format_yaml_error` from `preview.py`, while
  `preview.py:95-110` declares a structural `_IntentBearing` Protocol precisely so it need **not**
  import `document.ActiveItem` back. The Protocol call is right and well executed — structural
  typing removes the concrete-type coupling without duplicating the binder, and `mypy --strict`
  passes over 263 files. The residue is that one leaf reaches into another leaf's private surface:
  the underscore says "nobody's API" and the import uses it as one. Cheapest fix, only if either
  module is reopened: lift the formatter into a shared `features/backlog/_yaml_errors.py` leaf, or
  drop the underscore and export it. **`software-engineer` or `ai-engineer` lane**, no urgency.
- **`token_estimate` drift is a class, not an instance.** (review LOW)
  `sdd-bug-backlog-governance.md` declares `1300`; the linter computes **≈1845** — 42% against its
  own 20% threshold — and `catalog.json` mirrors the declared value because the generator **copies
  frontmatter rather than recomputing it**. The prior value drifted comparably (950 declared vs
  ≈1301 computed = 37%), so this is not a one-off closer error: any atom whose `token_estimate` is
  hand-estimated stays wrong until someone runs the linter, and the catalog faithfully propagates
  the wrong number. **The dispatcher normalizes this instance mechanically at the re-close**
  (see `## Memory updates`); what is listed here is the *class* — either the generator recomputes
  the field, or `specs doctor` should fail rather than warn on an atom whose declared estimate the
  linter can measure. **`software-engineer` lane**, LOW.
- **Two DEAD-marker comments still point readers at `backlog/candidates.md`.** (review LOW,
  pre-existing) `features/telemetry/store/schema.py:93` and `:102` read "# DEAD: replaced by
  canonical workflow reader in panel-r3; do not extend; see backlog/candidates.md". That index is
  now archived under `specs/backlog/_archive/candidates.md`; the live pointer is
  `specs/backlog/BACKLOG.md`. Outside every T-120-0x write set and not worth a commit of its own —
  repoint or drop the two comments the next time that module is touched. **`software-engineer`
  lane**, LOW.
- **`dd-release-definition` §5 describes the closure sweep with the wrong verb.** (review INFO)
  The new executor table says the sweep "flips each fully-consumed slug's `## LEDGER` line", but
  the mechanism this same release ships **adds** a LEDGER line and **removes** the ACTIVE
  subsection — an item never has a LEDGER line to flip while it is still ACTIVE, and BL-STALE
  fires precisely when it does. The same paragraph paraphrases SPEC-DOC-031 as "an archived
  SPEC/CLOSURE that still names a slug the ledger shows unconsumed", where the check actually keys
  off a **non-terminal ACTIVE item** whose slug an archived document names. The §5 rewrite is a
  large net improvement and this is wording, not doctrine — but it is wording inside the one skill
  a release-definer follows literally. **`ai-engineer` lane**; fold into the same pass that
  resolves QA-2, so all three skill surfaces state the ACTIVE → LEDGER mechanism identically.
- **`load_document` costs ≈145 ms on the live 57 KB document, ~99% of it PyYAML.** (review LOW)
  Measured over 20 runs; cProfile attributes ~1.24 s of a 1.38 s five-call run to 115
  `yaml.safe_load` calls (23 per parse) under pure-Python PyYAML. **No pathological regex** — the
  reviewer ran the sectioning patterns over 8× the document in 50 ms with no nested-quantifier
  backtracking, which is the question a new parser most deserves and it answers clean. The cost
  lands at pre-commit frequency because `backlog doctor` parses once and `specs doctor`'s
  SPEC-DOC-031 parses again through the new sanctioned edge — ≈0.3 s per backlog-touching commit,
  half of it waste, since SPEC-DOC-031 reads only `slug` and `status` and never touches `intents`.
  Grows linearly with intents-bearing ACTIVE items (23 of 28 today). Fixes if it ever becomes a
  complaint: prefer `yaml.CSafeLoader` when the C extension is available, or give `load_document`
  a slug/status-only mode for the governance caller. **`software-engineer` lane**, LOW.

### Pre-approved intake

**None.** No operator-ratified deferral was taken during this release: the two open decisions are
*recorded, not blocking* (SPEC §8), and OD-2 is an unresolved rewrite rather than an approved
entry.

### Checked and closed — deliberately not listed

- **The `backlog_new_cmd` docstring residual**, raised in the T-120-03…06 handoff as stale prose
  ("Create `specs/backlog/<slug>.md` with canonical frontmatter stub") and routed for folding.
  **Verified fixed at closure**: `cli/commands/newartifacts.py` now reads "Append one
  `## ACTIVE` subsection for <slug> to specs/backlog/BACKLOG.md", with the create-when-absent
  behaviour and the FR3/ADR #14 citation. Folded into the cutover as recommended; recorded here
  so a reader of that handoff sees it was closed rather than dropped.
- **The flat-release ship-task marker gap** (T-120-14 archiving `[ ]`), now on its **fifth**
  occurrence. Already owned by the live ACTIVE entry `flat-release-ship-task-evidence`; not
  re-raised.

## Version bump decision

**Bump `pyproject.toml` `0.8.0` → `0.9.0` (minor) and add the `[0.9.0]` `CHANGELOG.md` entry in
the same commit.** This is ADR D3, ratified with the SPEC. Recorded here as **owed to the
dispatcher**, since `product-engineer` has no shell.

1. **Behavioural change for every consumer, backward-compatible in intent but not in shape.** The
   backlog verbs, the pre-commit gate, the CI job and four `specs doctor` checks all ship inside
   the wheel. A consumer workspace that upgrades gets a `backlog new` that writes a different
   file, a `backlog doctor` that reads a different file, and a `specs doctor` that now flags
   loose per-entry files as drift. Added and corrected behaviour with a documented migration
   surface is a minor under the package's `0.x` scheme.
2. **Not a patch, because this is not a hotfix.** Law §5 binds PATCH-with-CHANGELOG to a hotfix
   merge; minting another PATCH would misfile two consumed backlog entries as a fix.
3. **The two version axes stay distinct** (ADR-2). `v0.12.0` is the SDD release identity; `0.9.0`
   is the package version. Precedent chain: v0.9.0 → 0.6.0, v0.10.0 → 0.7.0, v0.11.0 → 0.8.0.

**The `[0.9.0]` entry must name the symbols that actually shipped, not the ones the picked entry
proposed.** This is v0.11.0's LOW6 lesson applied in advance — that release drafted a CHANGELOG
entry naming two identifiers (`skipped_oversized`/`skipped_binary`) that existed only in a
backlog proposal, and a reviewer caught it. The real names here:

- **`dadaia_workspace/features/backlog/document.py`**, and its entry point **`load_document`** —
  the single-source parser. Say `BACKLOG.md`, `## ACTIVE`, `## LEDGER` in the consumer's own
  vocabulary.
- **The four codes, unchanged in identity and severity: `BL-SCHEMA`, `BL-DUP`, `BL-CONFLICT`,
  `BL-STALE`** — with BL-STALE **re-defined** to "an ACTIVE item already consumed or
  dispositioned" (three ORed conditions). A consumer whose `backlog doctor` starts firing
  BL-STALE where it did not before needs that sentence.
- **`SPEC-DOC-035` is now the single-source invariant** — a loose item `*.md` directly under
  `specs/backlog/` is drift, WARNING, excluding `_archive/` and `remote-bugs/`. **`SPEC-DOC-031`**
  is re-targeted at the ACTIVE subsections, unchanged in severity and evidence source. **Three
  check ids are retired: `SPEC-DOC-012`, `SPEC-DOC-022`, `SPEC-DOC-023`**, with
  `check_backlog_schema`.
- **Four modules deleted:** `features/backlog/removal_lifecycle.py`, `removal.py`,
  `ledger_writer.py`, `consumes.py` (plus `container.build_backlog_removal_lifecycle`).
  `features/backlog/ledger.py`'s **`read_consumed`** is explicitly **kept**.
- **`dadaia backlog new` now appends an ACTIVE subsection** and creates the document when absent;
  the verb list (`new`, `subjects`, `doctor`) and the CLI contract are unchanged. `specs init`
  scaffolds a conformant `BACKLOG.md` skeleton instead of `candidates.md` + `ideas.md`.
- **Parsing is fence-aware** (`a76d55bf`, pre-ship): a `##`/`###` line inside a fenced span is
  content, never document structure, so a fenced markdown example in a Description cannot truncate
  `## ACTIVE`; an unclosed fence at end-of-file surfaces as a **BL-SCHEMA ERROR** rather than a
  silently shrunken model. This one is worth a consumer-facing sentence even though no released
  version ever shipped the defect — it is the property a PM hand-editing the document depends on.

The pre-existing CHANGELOG version-axis incoherence is tracked as the live ACTIVE entry
`changelog-version-axis-reconciliation` and is **not** re-raised here: write the entry in the
file's current shape.

## Archive decision

**MOVE** — `specs/releases/v0.12.0/` moves to `specs/_archive/releases/v0.12.0/` via `git mv`,
executed by the dispatcher, in the same commit that carries this file. `ACTIVE.md` is then set to
`release: none` / `phase: none`: no release follows immediately, and the next pick is the PM's.
At that pick the queue is bugs-and-audits-first by law — **zero** open bugs, zero undispositioned
audits — so fresh backlog leads, from a 28-item `ACTIVE` section, with this closure's **ten**
intake candidates due for adjudication before any of them can be picked. Five of the ten arrived
from the pre-PR review after the release was first closed, which is itself the argument for
adjudicating them before the next pick rather than carrying them forward silently.

Two properties of the move are worth stating because this release is the one that made them
matter. First, `git mv` creates no new blob, so every file moving into `_archive/` is invisible
to the push-range denylist scan by the FROZEN↔rename invariant — the same invariant that carried
32 backlog renames at the cutover without a single new object. Second, **this document is not
covered by that invariant**: it is authored into the archive directory, so it is an ordinary new
blob the gate reads like any other. It was written under the redaction-at-authoring doctrine —
every path cited is workspace-relative, and no foreign Spec Context name, repo slug, hostname, IP
address, email or absolute local path was transcribed into it, including from the capture files
it quotes.

After the move, nothing under `specs/_archive/` is edited again — including T-120-14's `[ ]`
marker, which archives open by design (see `## Tasks completed`). The ordering that produces that
gap, and the related one where T-120-13 archives before T-120-14's pre-PR review reads the
closure, is unchanged from v0.11.0 and is not re-raised here: it is already a live backlog entry,
and a TASKS-template change is not this document's to make. This release did, however, pay that
ordering's price in full: the pre-PR review read an archived closure it was forbidden to correct,
and the only honest way out was to reset the archive commit and write this document again — third
occurrence of the pattern, and the strongest evidence yet that the entry is worth picking.
