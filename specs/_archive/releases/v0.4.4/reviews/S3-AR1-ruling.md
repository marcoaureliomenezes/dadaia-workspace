# AR-1 Ruling — byte-goldens-over-inventory as a mechanism (S3)

**Release:** v0.4.4 · **Segment:** S3 · **Task:** T-044-22 (A13.5, SPEC §6 AR-1)
**Author:** software-architect · **Date:** 2026-08-24
**Mandate:** rule on the MECHANISM — two byte goldens
(`tests/unit/infrastructure/_golden/install_target_resolution_v0158.json`,
`doctor_all_four_v0158.json`) encode the entire projected file inventory, plus three
further tests coupled to the same inventory — not on the T-044-21 regen itself. Standing
order applied: permanent architecture review, oriented by bug history.

**Verdict: (c) SPLIT THE INVENTORY OUT OF THE BYTE GOLDEN** — small, stable byte golden
for policy; derived inventory check so renames self-heal. All work beyond the regen
already done is **intake** for the operator's backlog, not v0.4.4 scope (SPEC §4.3).
**Interim law until the intake lands:** the T-044-21 regen protocol (multiset diff,
every line FR-attributed in the commit body, `panel_runtime_validation_v0158.json`
byte-identical or it is a defect) is the documented regen discipline — commit 43feb5f6
and the V7 evidence (`.dadaia/tmp/software-engineer/20260824/V7-golden-multiset-diff.md`)
are the reference execution.

---

## 1. The architectural defect, named

One golden artifact fuses two concerns of opposite volatility:

- **Policy (low-churn, behavior-bearing):** per-target install routing (`all`/`agents`/
  `claude`/`codex`/`kimi-code`), doctor line grammar and prefixes, panel runtime
  accept/reject bodies. This is what the goldens were built to lock (v0.1.58 T-58-10,
  "captured BEFORE the FR1 refactor" — that refactor-proof purpose is long complete).
- **Inventory (high-churn data):** the concrete roster of projected skill/agent files,
  which changes on every legitimate rename/consolidation and is owned by
  `dadaia_workspace/public/**`, not by any code path under test.

Because both live in one byte artifact, every roster change forces a full regen — and a
regen is exactly where an unintended policy change can hide, mitigated only by manual
ceremony. Three more tests hardcode copies of the same inventory
(`tests/e2e/features/test_public_pipeline.py` EXPECTED_SKILLS,
`tests/integration/test_public_assets.py` path constants,
`tests/integration/scripts/test_check_skill_orphans.py` roster model), plus a fourth
coupled surface sharing the doctor golden
(`tests/unit/infrastructure/test_public_assets_profile.py::test_absent_profile_doctor_byte_equals_all_four_golden`).
This is build-on-a-stale-layer: the inventory half of a completed refactor-lock kept
accreting consumers instead of being retired.

## 2. Evidence table — the bug history of this surface

| Ledger event (`specs/bugs/bugs.jsonl`) | Release | What it proves |
|---|---|---|
| `v025-public-assets-missing-golden-and-architecture-map-updates` (resolved) | v0.2.5 | Recurrence 1 of the stale-inventory class — golden/asset sync missed. |
| `install-target-doctor-goldens-stale-after-v043-skill-additions` (MEDIUM, resolved) | v0.4.3 | Recurrence 2 — alpha-1 skill additions landed without regen; an innocent task (T-043-10) had to prove innocence via git-stash bisection. The discipline was already the rule and was not followed. |
| `test-public-assets-stale-grill-me-name` (resolved 2026-08-24) | v0.4.4 | Recurrence 3 — T-044-20 rename landed in `public/skills`, hardcoded test path stayed stale. Cross-agent seam: `ai-engineer` made the rename but `tests/**` is out of its write scope; bug had to be filed for `software-engineer`. |
| `test-public-pipeline-stale-skill-roster` (resolved 2026-08-24) | v0.4.4 | Recurrence 4 — 25 stale EXPECTED_SKILLS entries; same root cause, same seam, same session. |
| `dadaia-md-projected-twice-into-claude-code-context` (resolved) | v0.4.4 | The byte goldens legitimately CAUGHT a real projection-behavior change (FR31): 3 anticipated golden failures were the signal, deferred to T-044-21's single regen. The policy half earns its keep. |
| `upgrade-never-refreshes-uncustomised-scoped-law-projection` (resolved) | v0.4.3 | Golden gained exactly one attributable line — precise change visibility; AND the fix itself is this codebase's own derived-oracle precedent (`shipped-hashes.json` + `was_shipped()`). |
| `skill-orphan-checker-misses-disable-model-invocation` (resolved) | v0.4.4 | The orphan checker's own roster model went structurally blind after FR28 — a third independent copy of inventory assumptions drifting. |
| Commit 43feb5f6 + V7 multiset diff | v0.4.4 | The discipline, executed at its best: every ±line FR-attributed (FR10/11/12/26/31), panel golden sha256-identical. This is the ceiling of option (a) — and it took a dedicated task, a snapshot dir, and a Counter-diff to achieve. |

## 3. The three options against the ledger

| Option | Recurrences of the 4-bug stale-inventory class it would have prevented | What it loses |
|---|---|---|
| (a) keep-with-discipline | **0 mechanically.** v0.4.3 happened because the already-existing discipline was skipped mid-release; the two v0.4.4 bugs live in the three coupled tests, which the golden-regen ceremony does not even touch; the cross-write-scope seam (renamer ≠ test owner) defeats discipline structurally. | Nothing — which is the problem: it fixes nothing structurally. |
| (b) replace byte goldens with structural assertion | All 4. | The policy byte-lock that demonstrably caught real regressions (FR31 double-projection; one-line change visibility; the panel byte-identity check T-044-21 itself used to prove "no defect"). Over-correction: deletes a proven detector. |
| **(c) split** | **All 4** — inventory expectation derives from the `dadaia_workspace/public/**` source tree, so a rename self-heals in the same commit that performs it — **while keeping** the policy byte-lock where the ledger shows it catching real bugs. | Only the "roster changed at all" alarm, which is the noise being removed; `git diff` on `public/**` carries that information natively. |

Non-tautology note on the derived oracle: expectation is derived from the source tree
(`dadaia_workspace/public/**`), asserted against install()/doctor() **output** — the two
independent ends of the projection pipeline. A stage/manifest drop, a target-routing
bug, or a projection omission still fails; per-target routing rules remain hand-pinned
as policy. Internal precedent: `shipped-hashes.json`/`was_shipped()` (v0.4.3), which
ended the TREE-5 freeze-both blindness the same way.

## 4. Bug-surface statement (FR24 / standing order)

**The mechanism as it stands INCREASES the bug surface**: 4 registered recurrences of
one class across v0.2.5 → v0.4.4, **2 in this release alone**, each resolution a
constant-update that restored test truth for the instance but left the structural cause
— N hardcoded copies of one inventory spread across write-scope boundaries — fully
live. **Option (c) reduces it**: deletes N−1 inventory copies, collapses the regen
ceremony for roster churn to zero, and keeps (shrunken and stable) the byte-lock on the
policy surface. The diff of the intake work is net-deleting in expectation-copies — it
satisfies the standing order's prefer-deletion test; options (a) and (b) do not (one
adds ceremony, the other deletes a working detector).

**Gate verdicts (§0.1):** Root-cause gate — PASS for T-044-21/43feb5f6 (the regen was
disciplined, complete, and honest; the panel golden byte-identity was proven, not
assumed) with the explicit finding that the two v0.4.4 stale-fixture resolutions are
instance-correct but class-incomplete; the class closes only via the intake below.
Architecture-fidelity gate — PASS: SPEC A13/AR-1 represents the mechanism accurately
and itself demanded this ruling.

## 5. Disposition

**Disposition:** verdict (c) recorded; regen law until then = T-044-21 protocol (§ top).
**Intake for the operator's backlog (NOT v0.4.4 scope, SPEC §4.3):**
- **INTAKE-AR1-1 — split the inventory out of the byte goldens:** derived-roster oracle
  (scan `dadaia_workspace/public/**` as the expectation; assert install()/doctor()
  coverage through hand-pinned per-target routing rules); policy-only byte golden
  retained (panel golden untouched; doctor line grammar / routing pinned over a fixed
  synthetic fixture set). Blast radius: `tests/unit/infrastructure/test_install_target_goldens.py`,
  `tests/unit/infrastructure/test_public_assets_profile.py`,
  `tests/helpers/golden_platform.py`. Zero production-code change.
- **INTAKE-AR1-2 — one oracle for the coupled trio:** derive
  `tests/e2e/features/test_public_pipeline.py` EXPECTED_SKILLS, the
  `tests/integration/test_public_assets.py` path assertions, and
  `tests/scripts/check_skill_orphans.py`'s roster source from the same single oracle,
  eliminating the cross-write-scope drift seam that produced both v0.4.4 bugs.
