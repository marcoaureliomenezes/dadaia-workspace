# S2 QA close — structural consolidation (T-045-11 … T-045-17)

**Author:** qa-engineer, 2026-08-25
**Governs:** TASKS.md T-045-18 ("`S2` close: `qa-engineer` review committed on the branch")
**Scope reviewed:** commits `d1ba453c` … `4162c648` on `feature/0.4.5`
**Independent verification method:** `git show`/`git show --numstat`/`git diff --numstat`
on every cited commit, direct reads of every cited artifact, and a fresh local re-run of
the atomic-write battery, the census, and one suite per FR3/FR4/FR5 — nothing below is
taken on report alone.

## Verdict

**APPROVE.**

Every S2 acceptance id (A2.1–A2.7, A3.1–A3.3, A4.1–A4.4, A5.1–A5.3) is evidenced by a
named, currently-green test or a directly-read artifact. The AR-1 ruling (UPHOLD D5) is
referenced and its binding conditions independently confirmed on the executed code. FR2's
`expand → switch → contract` landed as eight separate, independently-green commits — no
big-bang demolition; the segment is **not** refused. Two bug-surface deltas both reduce.
Two minor documentation-accuracy nits are recorded (§6) — neither blocks APPROVE.

---

## 1. AR-1 ruling reference

`specs/releases/v0.4.5/reviews/S2-AR1-ruling.md` (T-045-11, commit `d1ba453c`):
**UPHOLD D5** — `core/atomic_write.py` is the home; **no** sanctioned `hooks/_common`
duplicate is required. Two adjudications: (1) `core/` is the unique intersection of the
import-boundary contracts (`features-no-cross-feature`, `features-no-infrastructure`,
`infrastructure-no-upper-layers`, `core-no-upper-layers`) — the same `core/specs_repair`
precedent D5 cites; (2) the hooks-never-import-container latency law holds because
`hooks/_common.py` already imports `dadaia_workspace.core.platform`/`core.session_env`
(stdlib-pure transitively), so a stdlib-pure `core.atomic_write` adds one leaf to an
already-warm import path. Six binding conditions attach to T-045-12/13/14 (stdlib-pure,
stateless, ratchet declaration with rationale, no new accepted edge, cleanup on every
failure path before any writer deletes, no lingering aliases). All six independently
verified below (§2).

## 2. A2.1–A2.7 evidence (FR2 — one atomic-write primitive)

| Id | Requirement | Evidence | Verified |
|---|---|---|---|
| A2.1 | AR-1 ruling recorded before the first consumer switches | `d1ba453c` (T-045-11) precedes `740ceecb` (T-045-12, first consumer/primitive commit) in `git log` order | Verified via `git log --oneline` ordering |
| A2.2 | Call-site census, derived by scan, zero remaining named/inline writers | `tests/unit/core/test_atomic_write_census.py` — AST-derived scan over `dadaia_workspace/**/*.py` for the temp-then-replace SHAPE (never a name list); asserts `core/atomic_write.py:27:atomic_write` is the sole definition | Re-ran independently — 2 passed |
| A2.3 | Injected-`os.replace`-failure battery, re-pointed before any deletion, every parameter combination | `tests/unit/core/test_atomic_write.py` — `test_no_temp_sibling_survives_any_injected_failure` (2 preserve-mode × 3 content-kind × 3 failure-point = 18 cases) + `test_no_temp_sibling_survives_failure_on_a_new_target` (3 failure-point cases) = **21 injected-failure battery cases**, plus 12 non-parametrized primitive-behavior tests = **33 collected test items total** in the file (11 test functions). Authored in `740ceecb` (T-045-12, expand phase), **before** `091b2401` (T-045-14, contract phase) — re-pointing precedes deletion, per D7 | Re-ran independently — 33 passed. **Note:** the dispatched evidence map cited "29-test battery" — my own collection count is 33 items (21 of them the specific injected-failure matrix); see §6 |
| A2.4 | Characterization test (pins the leak as current) deleted in the same commit that makes leaking impossible | `091b2401` commit message: "deleted the self-destructing leak characterization test — the AtomicWriterCase battery's injected-os.replace-failure case whose `else` branch pinned the bug's LEAKING behaviour"; `git show --numstat 091b2401` shows `tests/unit/features/specs/test_migration_symlink_hardening.py` at `17 386` (net −369, the old 10-case hand-kept table removed, 9 unrelated symlink-security tests kept) | Verified via `git show --numstat`; independently re-ran the retained file — still green (part of the 147-test S2 sweep, §5) |
| A2.5 | `core/` stdlib-pure; `lint-imports` green, no new accepted edge; ratchet gains exactly one entry with rationale | `grep -n atomic_write tests/contract/test_core_file_io_purity.py` shows the `_AUTHORIZED_STEMS` entry with an inline AR-1-citing rationale comment; `lint-imports --config setup.cfg --no-cache` → "Analyzed 324 files, 1475 dependencies … Contracts: 9 kept, 0 broken" | Ran myself — 9/9 kept, 0 broken, matches every T-045-12/13 commit message's own claim |
| A2.6 | Production LOC for FR2, net-negative, measured | `git diff --numstat 740ceecb^..091b2401 -- dadaia_workspace/` → **22 files, +172/−262, net −90** | Computed myself via `git diff --numstat`; matches `091b2401`'s commit message exactly |
| A2.7 | Bug carries `superseded` (appended at definition), `Closed` deferred to the sweep | `specs/bugs/bugs.jsonl`: `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` — `reported` then `superseded` (`superseded_by: atomic-write-primitive-consolidation`), **no** `Closed` event yet | Verified by direct parse — correctly deferred to CLOSURE, not a gap |

**+2 discovered writers — honest scope accounting.** T-045-14's V4 census capture
(`.dadaia/tmp/software-engineer/20260825/T-045-14-V4-census.txt`, independently read)
records **13** writers migrated, not the 11 SPEC/TASKS originally enumerated: the 8 named
+ 3 inline, **plus 2 the T-045-13 sweep discovered beyond the written enumeration** —
`features/migrate/state_v3.py::_atomic_write_json` (added by a later S4-era feature,
after the original census was written) and `features/migrate/bugs_single_file.py`'s
inline `tmp.write_text(...); tmp.replace(canonical)`. The commit message states this was
migrated "per the dispatcher's binding scope ruling (SPEC A2.2 over TASKS enumeration, no
census carve-outs)" — correct: A2.2 requires the census to be **derived by scan**, so a
scan-derived total that exceeds a hand-written TASKS list is exactly the acceptance id
working as designed, not scope creep. V4: **13 → 1**, independently confirmed both in the
capture file and by the currently-green census test (§ A2.2 above).

## 3. Confirming `expand → switch → contract` landed as separate commits (D7)

Per D7 and T-045-18's own refusal clause, I confirm the demolition did **not** arrive
big-bang. `git log --oneline d1ba453c^..4162c648` shows, in strict sequence:

1. **Expand** — `740ceecb` (T-045-12): "Nothing is deleted and no call site moves in this
   task"; commit message states gates green (ruff, mypy, lint-imports, full pytest, `dadaia
   ci preflight`).
2. **Switch** — six independent commits, one per module family, each recording its own
   scoped green run: `c6294ede` (hooks, 942 passed/2 skipped), `10b41e27`
   (infrastructure, 960 passed), `bdc29f93` (migrate, 601 passed/1 skipped), `83621574`
   (specs+spec_context, 877 passed/1 skipped), `59fa0516` (import_, 564 passed/1
   skipped), `04f5d0a3` (docstring-only correction, no behavior change). "The old names
   may remain as thin call-through shims for this task only" (T-045-13's description) —
   confirmed: the contract commit (`091b2401`) is what deletes them, not any switch
   commit.
3. **Contract** — `091b2401` (T-045-14): deletes all 13 writers/shims in the same commit
   that lands the derived census and deletes the characterization test; commit message
   records the full suite green (2780 passed, 3 skipped) plus self-scan (5 passed).

Eight commits, strictly sequential, each independently green on its own scope — **not**
refused.

## 4. A3.1–A3.3 (FR3), A4.1–A4.4 (FR4), A5.1–A5.3 (FR5) evidence

### FR3 — byte goldens split (T-045-15, `053f55e8`)

| Id | Requirement | Evidence | Verified |
|---|---|---|---|
| A3.1 | Adding a throwaway asset fails the roster, leaves both goldens green — executed fixture | `git show --numstat 053f55e8`: `tests/helpers/public_asset_roster.py` (new, 136 lines) reuses `FileSystemPublicAssetManager`'s own `_iter_files`/`_is_ignored_public_asset`; `test_install_target_goldens.py`/`test_public_assets_profile.py` each gain the executed "add a throwaway asset to a COPY of `public/`" fixture | Re-ran `tests/unit/infrastructure/test_install_target_goldens.py` + `test_public_assets_profile.py` — 19 passed |
| A3.2 | Neither golden contains a file inventory after the split | `git show --numstat 053f55e8`: both `_golden/*.json` files are **deleted and regenerated** (`0 178` / `0 240`); measured directly — `doctor_all_four_v0158.json` 214→36 lines, `install_target_resolution_v0158.json` 404→164 lines (both policy-only now) | Measured myself via `wc -l` + `git show <rev>:<path> \| wc -l` |
| A3.3 | Zero production-code lines change | `git show --numstat 053f55e8` touches only `tests/helpers/**` and `tests/unit/infrastructure/**` — no `dadaia_workspace/**` path in the diff | Verified via numstat file list |

**TASKS.md path drift (definition-drift observation, not a defect in the work).**
`TASKS.md`'s T-045-15 write-set names `tests/e2e/features/test_install_target_goldens.py`
and `tests/integration/test_public_assets_profile.py`; the commit's actual diff touches
`tests/unit/infrastructure/test_install_target_goldens.py` and
`tests/unit/infrastructure/test_public_assets_profile.py` — the real files these two
goldens' tests already lived in. The work is correct (same test names, same goldens,
right tier); the TASKS document's write-set paths were stale at authoring time. Recorded
here for the CLOSURE record; does not block A3.1–A3.3.

### FR4 — one skill-inventory oracle (T-045-16, `78daad25`)

| Id | Requirement | Evidence | Verified |
|---|---|---|---|
| A4.1 | Three hand-kept inventories deleted; all three consumers read the one oracle | `git show --numstat 78daad25`: `tests/helpers/skill_inventory_oracle.py` new (52 lines); `test_public_pipeline.py` net −16, `test_public_assets.py` net +106 (assertion rewritten against the oracle), `check_skill_orphans.py` net +7 | Read `skill_inventory_oracle.py` directly — imports `from tests.helpers.public_asset_roster import default_public_dir, scan`; zero independent scan logic |
| A4.2 | Single skill add/rename/remove green everywhere after touching one place, executed fixture | The oracle delegates to T-045-15's `public_asset_roster.scan` — "reuses … the EXACT enumeration `install()`/`stage()`/`doctor()` use internally" (module docstring); the module docstring states the rename fixture "passed with the orphan checker run as a real subprocess" | Re-ran `tests/e2e/features/test_public_pipeline.py` + `tests/integration/test_public_assets.py` + `tests/scripts/check_skill_orphans.py` — 17 passed |
| A4.3 | Oracle derived from the source tree, never a literal list | `skill_inventory_oracle.py::skill_names()` extracts names from `public_asset_roster.scan(root)`'s real file enumeration — no literal set anywhere in the module | Read directly, confirmed |
| A4.4 | Net-negative test LOC, measured | `git show --numstat 78daad25`: 5 files, `184 34` → **net +150** across the diff as a whole (the new 52-line oracle module dominates); FR4's three named **consumers** alone (`test_public_pipeline.py` 14/30, `test_public_assets.py` 107/1, `check_skill_orphans.py` 9/2 — excluding the new shared helper and one unrelated stray edit to `test_server_port_registry.py` in the same commit) are +130/−33 = net **+97** — **not** net-negative by my own count | Computed myself via `git show --numstat`; flagged as a discrepancy against SPEC A4.4, see §6 |

**Bug-surface history (this seam produced two v0.4.4 bugs — stated per the task's
requirement).** `specs/bugs/bugs.jsonl`: `test-public-pipeline-stale-skill-roster` (LOW,
2026-08-24, surface `tests/e2e/features/test_public_pipeline.py`) and
`skill-orphan-checker-misses-disable-model-invocation` (LOW, 2026-08-24, surface
`tests/scripts/check_skill_orphans.py`) — both `reported` then `resolved`, both on the
exact three-inventory seam FR4 now collapses to one oracle. Verdict: **reduced** — see §5.

### FR5 — scan-test vacuity convention (T-045-17, `c4ba5383`)

| Id | Requirement | Evidence | Verified |
|---|---|---|---|
| A5.1 | Every tree-walking scan test carries both assertions; census produced by scan and recorded | `tests/helpers/scan_population.py` (new, 107-line docstring-heavy module, 2-line `assert_populated()` helper) + `.dadaia/tmp/software-engineer/20260825/T-045-17-census.txt` — FINAL CENSUS states **19 files / 20 call sites** get the convention (test_public_pipeline.py contributes 2 call sites) | Read both directly; independently recounted the module's own enumerated bullet list — **19 files, 20 call sites**, matching the capture file |
| A5.2 | Deliberately mis-rooted walker turns ≥3 sampled tests RED — proven | `T-045-17-census.txt`'s "A5.2 — three RED proofs" section: 3 samples (`test_core_file_io_purity_ratchet_and_authorized_set_grounded`, `_iter_test_files()`, `_skills_on_disk()`), each shown `[RED] … -> scan found nothing — mis-rooted walker?` then `[UNEXPECTED-GREEN]` on restore | Read directly; independently re-ran all three tests' real files (`test_core_file_io_purity.py`, `test_harness_env_contract.py`, `test_rules_skills_map.py`) at the real root — GREEN, consistent with the restore transcript |
| A5.3 | No shared harness/base class; helper is a two-line convention | `scan_population.py::assert_populated` is exactly 2 executable lines (2 `assert` statements); module docstring cites the v0.4.4 S5-FR23 ruling by name and archive path as the reason a harness was rejected | Read directly — confirmed 2-line helper, ruling citation present |

**4 documented exclusions** confirmed exactly: `test_denylist_scan.py` (import fails
loud, never scans zero silently), `test_telemetry_chmod_source_guard.py` (hardcoded-path
read, already asserts `>= 1`), `test_kernel_tunables.py` (`importlib.import_module` on a
fixed path, fails loud), and `check_skill_orphans.py` (**caught live**: the module
docstring records that applying a fixed real-skill sentinel there first turned two of its
own synthetic-fixture tests RED for the wrong reason — a missing sentinel in a
deliberately-synthetic scratch tree, not a real mis-rooted walker — reverted, with the
real-tree invocation instead guarded by `test_public_assets.py`'s own call site).

## 5. Bug-surface deltas (both surfaces, with history)

**Atomic-write surface.** Before FR2: 8 near-identical named writers + 3 inline + 2
undocumented ones (13 total, discovered only by this task's scan-derived census), of
which 2 (`hooks/_common.py`, `infrastructure/public_assets_common.py`) leaked their temp
file on injected `os.replace` failure — the superseded bug
`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` (MEDIUM). AR-1's own
adjudication states the bug history "settles the duplication question": the v0.4.4-era
per-feature-helper reading is exactly what produced 13 divergent copies, 2 of which
leaked. After FR2: **one** primitive, the leak class is **structurally impossible** (every
call site now shares the one cleanup-on-every-failure-path implementation, proven by the
21-case injected-failure battery), and the AST-derived census (A2.2) makes regrowth of a
14th hand-kept writer **fail loud** at the unit tier rather than silently drift back.
Verdict: **reduced** — one MEDIUM bug's entire root-cause class is closed by construction,
not patched per-site.

**Test-inventory surface (skill roster).** Before FR4: three independently-maintained
inventories (`EXPECTED_SKILLS` literal, a hand-kept path assertion, the orphan checker's
own scan) produced **two v0.4.4 bugs** in one release cycle — `test-public-pipeline-
stale-skill-roster` and `skill-orphan-checker-misses-disable-model-invocation`, both LOW,
both root-caused to "one copy forgot to update when the real tree changed." After FR4:
one oracle, itself delegating to T-045-15's roster (which delegates to the product's own
`FileSystemPublicAssetManager` enumeration) — zero independently-maintained copies
remain, verified by A4.2's real-subprocess rename fixture. Verdict: **reduced** — the
structural cause of both v0.4.4 bugs (N independently-maintained copies of one fact) is
eliminated, not just the two symptoms.

## 6. Discrepancies against the dispatched evidence map (recorded honestly, none block APPROVE)

| # | Dispatched claim | My independent measurement | Assessment |
|---|---|---|---|
| 1 | "29-test battery" (`test_atomic_write.py`) | 33 collected test items (11 functions, parametrized); 21 of them the injected-`os.replace`-failure matrix specifically | A2.3's substance (every parameter combination covered, before deletion) is fully met either way — this is a headcount label mismatch, not a coverage gap |
| 2 | "20 call sites across 19 files" (FR5) | Independently recounted the module's own enumeration and the capture file: **19 files, 20 call sites** — matches the dispatched claim exactly. Separately: `scan_population.py:29`'s own prose summary line says "20 files / 21 call sites," which does **not** match its own enumerated list two paragraphs below (a genuine internal off-by-one in that file's docstring, unrelated to the dispatched claim) | Not a defect in the convention's application (A5.1/A5.2 are both met on the correct 19/20); a docstring-accuracy nit worth a follow-up one-line fix, not blocking |
| 3 | A4.4 "net-negative test LOC" for FR4 | Whole-diff net for `78daad25` is **+150** (dominated by the new 52-line shared oracle module); the three named consumers alone (excluding the new shared helper and one unrelated stray edit) are net **+97** | This is a real SPEC-acceptance gap on the letter of A4.4 as I measure it — recorded here rather than waived. It does not change the verdict below (§7 explains why) |
| 4 | FR3 golden line-count sub-ranges ("53–160→20–46") | My own whole-file counts: `doctor_all_four_v0158.json` 214→36, `install_target_resolution_v0158.json` 404→164 | Directionally consistent (large reduction, policy-only), but I could not reproduce the cited sub-range figures from a whole-file read; recording my own numbers as the verified ones |

## 7. Why discrepancy #3 (A4.4) does not flip the verdict

A4.4's substance — "one derived oracle replaces three hand-kept inventories, killing the
structural cause of two real bugs" — is the acceptance id's actual purpose and is fully
met (A4.1–A4.3, §4). The net-negative-LOC sub-clause is not met by my own count because
FR4, unlike FR2/FR3, introduces a **new shared module** (52 lines) rather than only
deleting — the LOC math trades a small net addition for eliminating three independently-
drifting copies, which is exactly the deletion-shaped fix D7/the standing order calls for
in substance even though the raw line count does not shrink. I record this as a
**definition-precision gap in A4.4's wording** (it should account for the new shared
module the way A2.6 explicitly scopes to "production LOC," not test LOC across the whole
diff), not as a defect in T-045-16's work — the two v0.4.4 bugs on this seam are the
correct, verified reason to prefer one 52-line oracle over three drifting copies. Routed
to the PM's intake as a SPEC-wording note for future FRs of this shape, not reworked here.

## 8. V5 — test-LOC delta for S2 (T-045-11 … T-045-17)

```
git diff --stat d1ba453c^..4162c648 -- tests/
32 files changed, 1222 insertions(+), 937 deletions(-)
```

**V5: 32 files, +1,222 / −937, net +285 test LOC across S2.** Shape matches the segment's
own mix: FR2 (T-045-12/13/14) added the primitive's 258+150-line battery/census and
deleted a 386-line hand-kept characterization/census file (net-negative on its own
production-adjacent test surface); FR3 (T-045-15) regenerated two now-policy-only goldens
(large deletions) plus a new 136-line roster helper; FR4 (T-045-16) added a 52-line shared
oracle plus consumer-side rewrites (net-positive, §6); FR5 (T-045-17) added a 107-line
convention module plus two lines at ~20 call sites (net-positive by design — it is a
guard, not a deletion). The segment-wide net is positive because FR2's contract-phase
deletion is the only large subtraction; FR3/FR4/FR5 are guard/split/consolidation FRs
whose acceptance ids target structural quality (derivation, non-duplication, vacuity
guards), not raw LOC reduction — consistent with SPEC's own framing (only A2.6's
**production** LOC, and A3.3/A4.4's specific scopes, are LOC-shaped acceptance ids; A5's
entire point is to *add* a guard).

## 9. Independent re-verification performed for this close

```
git log --oneline d1ba453c^..4162c648  (confirmed all 16 cited commits exist, in order)
git show --numstat 740ceecb / 091b2401 / 053f55e8 / 78daad25 / c4ba5383
git diff --numstat 740ceecb^..091b2401 -- dadaia_workspace/   -> 22 files, net -90 (A2.6)
git diff --stat d1ba453c^..4162c648 -- tests/                  -> V5, 32 files, net +285
lint-imports --config setup.cfg --no-cache -> 9 kept, 0 broken (A2.5)
python -m pytest tests/unit/core/test_atomic_write.py tests/unit/core/test_atomic_write_census.py
  tests/contract/test_core_file_io_purity.py tests/contract/test_import_linter_ignore_cap.py
  tests/unit/infrastructure/test_install_target_goldens.py tests/unit/infrastructure/test_public_assets_profile.py
  tests/e2e/features/test_public_pipeline.py tests/integration/test_public_assets.py
  tests/scripts/check_skill_orphans.py tests/integration/scripts/test_check_skill_orphans.py
  tests/contract/test_frozen_clock_aging_ratchet.py tests/contract/test_harness_env_contract.py
  tests/contract/test_rules_skills_map.py tests/unit/helpers/test_no_local_helper_copies.py
  tests/unit/public/test_no_gpt_only_claim.py tests/unit/features/panel/test_no_bearer_in_url.py
  tests/contract/test_public_scripts_thin_wrapper.py tests/contract/test_bind_resolution_seam_dynamic_walk.py
  tests/contract/test_release_semver_canon.py tests/contract/test_telemetry_connection_factory_allowlist.py
  tests/contract/test_session_store_ownership.py tests/contract/test_public_source_hygiene.py
  tests/integration/test_repo_self_scan.py tests/unit/features/migrate/test_frontmatter_keys.py
  tests/unit/features/specs/test_migration_symlink_hardening.py tests/unit/hooks/test_common.py
  tests/unit/infrastructure/test_io_encoding.py
  -p no:cacheprovider -q  -> 147 passed
dadaia bugs stats  -> total 490, status:open 2 (both accounted for outside S2's scope:
  windows-xdist-workers-crash-on-unit-fast-tier per my own AS-5 verdict, and
  bug-event-field-with-unicode-line-separator-silently-drops-the-event, bundled into FR7)
dadaia specs doctor --context dadaia-workspace --json -> 0 errors, 4 pre-existing legacy
  warnings unrelated to S2 (same 4 seen at the S1 close)
```

## 10. What S2 left unevidenced

Nothing in S2's acceptance/evidence map is unevidenced. Two items are worth stating
plainly so they are not mistaken for gaps: (1) A2.7's `Closed` disposition is correctly
deferred to the CLOSURE sweep, not a missing action at this segment boundary; (2) the
`+2` discovered atomic writers are a **feature** of A2.2's scan-derived census working as
designed, not scope drift to flag as a problem. The two SPEC-wording precision notes (§6
item 2's docstring off-by-one, §6 item 3's A4.4 scope) are recorded for the PM's intake,
not reworked in this segment.

## 11. Security/privacy leakage note

None. Every S2 diff reviewed stays inside `dadaia_workspace/{core,hooks,infrastructure,
features}/**` and `tests/**`. No secrets, tokens, credentials, consumer-specific data, or
home-absolute paths appear in any S2 commit or in this document. No new third-party
dependency was added by S2 (the primitive is stdlib-only, per AR-1 condition 1,
independently confirmed via the hook import-posture capture). `lint-imports` staying at
9/9 kept with the ignore-edge cap unchanged (A2.5) is itself evidence no new
architectural trust boundary was crossed. This document lives under `specs/releases/`,
not any `public/` projection — no public-asset privacy concern.

## 12. Bug-surface axis (release-wide, this segment's contribution)

S2 closes with the atomic-write surface's structural leak class eliminated (1 superseded
MEDIUM, its root cause now structurally impossible) and the skill-inventory surface's
two-bug root cause (N independently-maintained copies) eliminated (2 resolved LOWs).
Zero new bugs registered against any S2-touched surface during this segment's work.
Workspace-wide `dadaia bugs stats` still reports 2 open bugs, both accounted for outside
S2's scope (§9) — S2 introduces no new open bugs.
