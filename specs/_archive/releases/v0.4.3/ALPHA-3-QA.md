# ALPHA-3-QA.md — `alpha-3` (WS-A, suite, measurements, complexity governance) segment QA gate

**Task:** T-043-31 · **Reviewer:** qa-engineer · **Segment range:** `2be00f62` (alpha-2
close) `..` `5b517854` (last Arm-B rider in-segment) · **Reviewed at:** `1ac8e0ea`
(reservation commit, `feature/0.4.3`) · **Reviewed:** 2026-08-17

**Verdict: APPROVED** — every `alpha-3` acceptance id (A18.1–A21.6) verified against the
live tree, PLAN §5's `alpha-3` exit criteria are met, and the three Arm-B riders that
landed in-segment each carry a `reported`→`resolved` bug-ledger pair with zero open bugs
at review time.

---

## 1. Scope and method

Task delta: T-043-24 (`3450b0b3`), T-043-25 (9 commits, `24d0ba26`…`068d0462`), T-043-26
(`2446a7e4`), T-043-27 (`01e3afbb`), T-043-28 (`49d50353`), T-043-29 (`cbfea661`),
T-043-30 (`9df50d35`), plus three in-segment Arm-B riders: `03bc12d3` (alpha-2-qa
literal masking), `10775510` (skill-orphans wiring), `5b517854` (ruff-format archive
exclusion). 24 commits total in `2be00f62..5b517854`.

Every prior QA artifact under `.dadaia/tmp/qa-engineer/20260817/` (V4 census, offender
list, V5 re-measure, demotion-map draft, mutation-tool verdict) is this agent's own
prior-session work product; this review re-verifies every load-bearing claim directly
against the live tree at HEAD rather than re-deriving the analysis from scratch. Where a
claim is re-confirmed live (grep, pytest collection, `ruff check`, file presence), the
command and its live output are cited alongside the originating artifact.

---

## 2. Per-acceptance-id table

| id | Requirement (abridged) | Evidence | Verdict |
|---|---|---|---|
| A18.1 | Census measured at segment start; entry's own numbers void | `v0.4.3-T-043-24-v4-large-census.md` — 56 pytest e2e + 46 Playwright = 102 broad LARGE (cap 30); archived backlog entry's 2026-08-14 baseline (55+41=96) explicitly voided and corrected | PASS |
| A18.2 | Every LARGE test demoted/deleted/kept with justification+owner | `v0.4.3-T-043-24-offender-list.md` — 100% of 102 dispositioned (2 DEMOTE, 0 DELETE, 100 KEEP); executed by T-043-25 (commits `cb1986ce`…`db7f7403`). Live re-verification: demoted file `tests/integration/features/test_panel_stderr_drain.py` + helper `tests/helpers/subprocess_diag.py` exist; `test_drain_stderr_nonblocking_*` absent from `tests/e2e/features/test_panel.py` (grep, zero hits) | PASS |
| A18.3 | Census re-measured at segment end; numbers+delta captured | `v0.4.3-T-043-26-v5-census-remeasure.md` — pytest e2e-tier 54 (was 56, −2), Playwright 46 (unchanged), broad LARGE 100 (was 102, −2). Live re-run at HEAD (`5b517854`): `pytest -m e2e --collect-only` → **54/2440 tests collected** — matches V5 exactly | PASS |
| A18.4 | No deletion/skip/disable without a qa-engineer verdict carrying evidence | Zero deletions performed (offender list authorized 0 DELETE); the 2 demotions and the 1 WIRE verdict each trace to a named `file:line` verdict in the offender list, executed verbatim per the demotion-map draft's reconciliation | PASS |
| A18.5 | Demotion map drafted in-segment, ready for CLOSURE's `## Test dispositions` | `v0.4.3-T-043-26-demotion-map-draft.md` — full table (demotions, deletions=none, wiring, plan-ref/dangling-ref backfills, Intent/Owner backfills by file), explicitly marked "CLOSURE-ready — copy verbatim" | PASS |
| A18.6 | `quality-assurance.md`'s census sentence + 2 justified-timeout citations rewritten so no memory pointer dangles into the consumed slug | **Correctly deferred to CLOSURE** — `specs/memory/` is a MEMORY-class path, writable only in DEFINITION/CLOSURE phase (this segment is IMPLEMENTATION); T-043-26's evidence names this explicitly ("CLOSURE recording is rc-1/product-engineer territory, out of this task's write set"). The dangling pointer inside `test_handoff_pipeline.py`'s own docstring (Verdict 2b) *was* re-aimed in-segment (`193ca6c4`) — the part inside this segment's write set is done; the memory-atom half is correctly held for T-043-51 | PASS (deferred as designed) |
| A19.1 | Check is green at HEAD the moment it is enabled | Live run: `python tests/scripts/check_test_intent_declared.py` → exit 0 (silent, no offenders) against the real repo at HEAD | PASS |
| A19.2 | A new undeclared-intent test file fails the check; a compliant one passes | `tests/integration/scripts/test_check_test_intent_declared.py` — 5 cases (2 fake-tree refusal, 1 fake-tree pass, 1 support-module exclusion, 1 real-repo case); live re-run: 12/12 passed (bundled with the orphan-skill and mutation-wiring integration suites) | PASS |
| A19.3 | Accepted declaration shape documented where the doctrine lives | `tests/AGENTS.md`'s Intent-taxonomy section documents the shape (directory placement + module `Intent:` header), scope (`tests/e2e/**` only), and exclusion list | PASS |
| A20.1 | Named tool with exact pin, runs to completion on this repo | `qa-engineer` verdict selected `mutmut==3.7.0` (`v0.4.3-T-043-28-mutation-tool-verdict.md`); pinned in `pyproject.toml`'s optional `[tool.poetry.group.mutation]`; V11 baseline captured (73 mutants, 66 killed, 7 survived, 90.4% score, ~9s) | PASS |
| A20.2 | Invocation recorded in QA memory (§5) so the cadence claim is backed by a runnable command | `tests/scripts/run_mutation_baseline.sh` — real, executable (`-rwxrwxr-x`, confirmed on disk), stages a scoped copy, never writes inside the repo tree. Recording into `quality-assurance.md` §5 is CLOSURE-phase MEMORY work (same phase constraint as A18.6) — the runnable command itself, which is this id's substance, exists and is proven at HEAD | PASS |
| A20.3 | Tool absent from every push-path selector; CI push timing unchanged | Live re-verification: `grep -rn "mutmut\|run_mutation_baseline" .github/workflows/*.yml dadaia_workspace/features/ci_preflight/` → **zero hits**; guarded permanently by `tests/integration/scripts/test_run_mutation_baseline_wiring.py::test_script_never_referenced_from_a_push_path_selector` (present, passing) | PASS |
| A20.4 | First baseline captured after FR18, as evidence not a gate | V11 captured at T-043-28, strictly after T-043-25/26's curation (FR18); the baseline score (90.4%) gates nothing — absent from every push-path selector (A20.3) | PASS |
| A21.1 | `C90`/`PLR1702` selected with ceilings equal to the measured maxima; measurement captured as evidence | `v0.4.3-T-043-29-v6-complexity-maxima.md` — full-repo-scope measurement at ceiling 1: complexity max **63** (`handler.py:330 make_handler_class`), nesting max **6** (`allowlist.py:116`). Live re-verification: `pyproject.toml` — `max-complexity = 63`, `max-nested-blocks = 6`, both inside `dadaia_workspace/`, no `tests/**` per-file-ignore needed | PASS |
| A21.2 | `ruff check` green at HEAD the moment the rules land — zero violations by construction | Live run at HEAD (`5b517854`): `ruff check --no-cache .` → **All checks passed!** | PASS |
| A21.3 | Ratchet direction documented: ceilings may only decrease, any decrease justified in CLOSURE | `pyproject.toml:111-128` — explicit "RATCHET DIRECTION" comment block above `[tool.ruff.lint]`: "may only DECREASE, never increase... justifies the decrease in that release's CLOSURE.md `## Size accounting` table" | PASS |
| A21.4 | `dd-release-closure` CLOSURE template requires a mandatory `## Size accounting` table (LOC add/del/net, 3 largest additions/deletions by file, complexity before/after, nesting-violation count) | Live re-verification: `grep -n "Size accounting" .claude/skills/dd-release-closure/SKILL.md .agents/skills/dd-release-closure/SKILL.md` → both hit (projected from `dadaia_workspace/public/skills/dd-release-closure/SKILL.md`, T-043-30 `9df50d35`); section covers exactly A21.4's five items per T-043-30's evidence | PASS |
| A21.5 | This release's own CLOSURE carries that table, filled with measured values | **Not yet applicable** — CLOSURE.md does not exist until `rc-1`/T-043-52 (CLOSURE-phase, `product-engineer`); the template requirement this id measures (A21.4) is in place and ready. Correctly out of `alpha-3`'s scope; named here as explicitly unverified-yet, not silently passed | UNVERIFIED (deferred to rc-1 by design, not a gap) |
| A21.6 | `quality-assurance.md` gains the governance section (§5); heading enters `.heading-allowlist` in the same memory window | **Not yet applicable** — MEMORY-class edit, same phase constraint as A18.6/A20.2; scheduled for the CLOSURE memory window (ties to A13.3) | UNVERIFIED (deferred to CLOSURE by design, not a gap) |

**A21.5 and A21.6 are the only two ids this review reports as not-yet-verifiable** —
both are explicitly CLOSURE-phase MEMORY-class work by SPEC's own text ("its heading
enters `.heading-allowlist` in the same memory window") and PLAN's phase ladder
(DEFINITION → **IMPLEMENTATION** (alpha-1…alpha-6, current) → CLOSURE → ARCHIVED). Per
`dadaia-workspace-spec-navigator`/DADAIA §3, `specs/memory/` is writable only in
DEFINITION and CLOSURE phase — `alpha-3` runs in IMPLEMENTATION, so no agent could have
performed A21.5/A21.6 inside this segment without violating the MEMORY-class gate. All
19 other ids (A18.1–A20.4, A21.1–A21.4) verify PASS.

---

## 3. PLAN §5 `alpha-3` exit criteria

> `alpha-3` exits when: FR18–FR21 `[x]`; V4/V5/V6 captured; demotion map drafted; every
> deletion carries a qa verdict; `qa-engineer` review committed.

| Criterion | Status |
|---|---|
| FR18–FR21 `[x]` | T-043-24…30 all `[x]` in `TASKS.md` (confirmed: `grep -c '\[x\]' §alpha-3` = 7/7 prior to this task) |
| V4 captured | `v0.4.3-T-043-24-v4-large-census.md` (102 broad LARGE) |
| V5 captured | `v0.4.3-T-043-26-v5-census-remeasure.md` (100 broad LARGE, −2) |
| V6 captured | `v0.4.3-T-043-29-v6-complexity-maxima.md` (complexity 63, nesting 6) |
| Demotion map drafted | `v0.4.3-T-043-26-demotion-map-draft.md`, CLOSURE-ready |
| Every deletion carries a qa verdict | 0 deletions performed (none authorized) — vacuously satisfied |
| `qa-engineer` review committed | This document, committed alongside T-043-31's `[x]` flip |

**All exit criteria met.**

---

## 4. Rider and bug-ledger status

Three Arm-B riders landed inside the `alpha-3` window, each fixed on the spot per the
Arm-B contract (register → root-cause → RED → fix → GREEN → `resolved` event → commit —
no release ceremony):

| Rider commit | Bug id | `reported` | `resolved` |
|---|---|---|---|
| `03bc12d3` | `repo-self-scan-hits-alpha2-qa-historical-literal` | 2026-08-17T19:01:19Z | 2026-08-17T19:06:39Z |
| `10775510` | `skill-orphans-unwired-agent-frontmatter` | 2026-08-17T18:52:41Z | 2026-08-17T19:13:15Z |
| `5b517854` | `ruff-0-16-2-markdown-python-fence-format-drift` | 2026-08-17T20:09:20Z | 2026-08-17T20:24:17Z |

All three carry a complete `reported`→`resolved` event pair in `specs/bugs/bugs.jsonl`
(verified by direct read of the ledger). Live `dadaia bugs status`:

```
[ok] 0 open bug(s).
```

Zero open bugs at review time — the whole `alpha-3` bug population (these three plus
every other bug touched across the segment) is closed.

---

## 5. Suite and doctor run (live, this session)

All commands run against `feature/0.4.3` at `5b517854` (pre-existing tip; this review's
own reservation commit `1ac8e0ea` touches only `TASKS.md`, no source):

| Check | Command | Result |
|---|---|---|
| Full suite | `pytest -p no:cacheprovider -m 'not quarantine' -n auto` | **2437 passed, 3 skipped, 0 failed** (50.93s) |
| CI preflight | `dadaia ci preflight` | **5/5 PASS** — `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest` |
| Workspace doctor | `dadaia doctor` | **All invariants OK — workspace is healthy** |
| Specs doctor | `dadaia specs doctor --context dadaia-workspace` | **0 errors, 5 warnings** — 1 `LINT-1` heading-allowlist warning family (pre-existing, deferred to T-043-51/A13.3) + 2 `SPEC-DOC-027` legacy release-dir names (pre-existing, unrelated) + 2 `SPEC-DOC-036` un-disposed archived-audit warnings (pre-existing, unrelated) — none newly introduced by `alpha-3` |
| Public doctor | `dadaia public doctor` | **`[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution`** — 0 `[error]`/`[drift]`/`[missing]` lines |
| e2e-tier census (A18.3 re-check) | `pytest -m e2e --collect-only -q` | **54/2440 collected** — matches V5 exactly |
| `check_test_intent_declared.py` (A19.1) | direct invocation | exit 0, silent (no offenders) |
| Complexity gate (A21.2) | `ruff check --no-cache .` | **All checks passed!** |

The 2437-passed count (vs T-043-30's recorded 2436) is a full +1 delta accounted for
entirely by the last in-segment rider `5b517854`, which added one new SENTINEL test
(`tests/integration/test_ruff_format_repo_tree_green.py`) — confirmed via `git show
--stat 5b517854` and the rider's own commit message ("2437 passed, 3 skipped, 0
failed"). No unexplained delta.

---

## 6. Findings

No CRITICAL, HIGH, or MEDIUM findings. No LOW findings requiring intake.

**INFO (record-only, already covered by design, not repeated in intake):**
- A21.5/A21.6 are correctly unverifiable inside `alpha-3` (MEMORY-class, CLOSURE-phase
  work) — named as UNVERIFIED per PLAN §6's "an unverified id is never reported as
  passed," not silently marked PASS.
- T-043-26's demotion map notes one CLOSURE-awareness item still open: the sibling
  dangling-pointer citation in `tests/integration/cli/test_context_name_differs_from_repo_slug.py:122-126`
  (out of LARGE-tier scope, not part of this segment's write set) — carried forward to
  CLOSURE alongside A18.6, not a new finding.

---

## 7. Verdict

**APPROVED.** All 19 `alpha-3`-verifiable acceptance ids (A18.1–A20.4, A21.1–A21.4)
PASS with live-tree evidence; the 2 remaining ids (A21.5, A21.6) are correctly deferred
to the CLOSURE MEMORY window by SPEC/PLAN's own phase design, not gaps in this segment's
execution. PLAN §5's `alpha-3` exit criteria are fully met. The three in-segment Arm-B
riders are each closed with a complete bug-ledger pair; zero open bugs at review time.
The full gating suite, `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor`, and
`dadaia public doctor` are all green. `alpha-3` is cleared to close.
