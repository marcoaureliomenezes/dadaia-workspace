# Closure: Release — v0.4.5 — hardening and consolidation

> **Status:** Aprovado
> **Release ID:** v0.4.5
> **Owner:** product-engineer
> **Closed:** 2026-08-27

**Note on one elided ledger id.** One bug id closed by this release begins with a token
that is also a foreign context slug. It is written throughout this document as
`…-md-canonical-table-omits-sanctioned-references` (the suffix is unique in the ledger).
The elision is this closure's own privacy rule, not a doubt about the id: the T-045-35
ruling establishes that such ids are legitimate, immutable identifiers and that the
push-gate's slug layer must stop matching them.

## Summary

v0.4.5 is the hardening-and-consolidation round that v0.4.4 earned. It opened with eight
bugs on the ledger and closed with one — the single item the SPEC declared, in advance,
might end the release still open (AS-5). Everything else it touched already existed, and
most of what it did was deletion: thirteen near-identical atomic writers collapsed into one
primitive, three hand-kept skill inventories into one derived oracle, two byte goldens split
so they pin policy instead of a file inventory, five over-ceiling persona bodies trimmed by
relocating justified content into skill siblings that already existed.

Three gate and seam lanes that the v0.4.4 reviews had classed as *recurrences* are now
structurally closed rather than patched: the operator denylist is consulted at the moment a
bug event is written and no longer only at push time; control and format characters are
sanitized once, at one seam, in an order that keeps the redaction pass working on normalized
text; and `specs init --specs-dir` refuses a symlinked target by reusing the hardened
resolver rather than by adding a second symlink check. The SDD gate now classifies the LAW
path class **by origin** instead of by filename, so a repository's own `AGENTS.md` is
writable by the agents the library's own scaffold tells to write it — one predicate, one
line shorter than before. The doctor learned `.dadaia/references/` as a sanctioned,
operator-owned subtree that no lifecycle verb may ever act on, and gained a registry-wide
repo-slug ownership check that reports a collision the two write seams can never see.

The token-economy program ran as one measured pass and **missed its targets honestly**. The
always-on load fell from ~21.5k to ~20.5k tokens against a ≤3.5k acceptance, negations from
299 to 257 against ≤60, the bound-session injection prefix from ~1,506 to ~878 tokens against
≤700, and five personas remain above the 220-line ceiling with the fleet 93 source lines
lighter. Every one of those numbers was measured, never estimated; every miss carries its
reason and the assumption (AS-1/AS-3) that authorized recording it instead of failing the
release on a number. The operator rules on them here.

Nothing is published. By operator law **O5**, ship means merge to `main`; `release.yml`'s
approval gate is left deliberately unapproved, no `v0.4.5` tag is minted, and PyPI's latest
published version stays `0.4.4`. That makes `0.4.5` the second locally-minted, unpublished
version after `0.4.3` — a repeated shape, now recorded as product truth in memory rather
than as a footnote.

## Tasks completed

Final shas are short shas on `feature/0.4.5`. Where a task landed as several commits, the
last substantive commit is given and the marker-flip commit follows in parentheses.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-045-01 | [git] Definition commit (SPEC/PLAN/TASKS + purge-on-pick + `superseded` event) | `135a768d` (marker; the definition commit itself precedes it, with the security fold at `e97084fb`) |
| T-045-02 | [git] Milestone (a): push + definition PR → `develop` | `135a768d` |
| T-045-03 | [operator] Wire the verdict-gate required check on both PR edges | **`[ ]` — operator-pending.** Never picked up by an agent by design (operator-only item B1). Due before any `rc-2` PR (D-7); no `rc-2` exists yet, so it is not yet overdue |
| T-045-04 | FR1: the LAW path class decides by origin, not by basename | `6dcf278f` (`17815b53`) |
| T-045-05 | [shell] Install the gate fix and probe it on the executed path (V3) | `66434b3a` (capture `.dadaia/tmp/software-engineer/20260825/V3-gate-probe.txt`) |
| T-045-06 | Bug: `dadaia-task-manager-stale-workspace-protocol-citation` | `db9d0c20` (`11193db5`) |
| T-045-07 | Bug: `certify-skip-detail-leaks-full-codex-output` (CWE-532) | `7681d4f3` + ruling `185f0940` (`484cac2c`) |
| T-045-08 | Bug: `codex-probe-unit-fixture-carries-real-session-uuid` | `5c9be8ed` (`484cac2c`) |
| T-045-09 | Bug (time-boxed): `windows-xdist-workers-crash-on-unit-fast-tier` | verdict `697d7da6`; separable finding fixed at `0d9d49bb` (`9461206f`) |
| T-045-10 | `S1` close (qa-engineer, committed on branch) | `d17a4414` (`664461d6`) |
| T-045-11 | AR-1: the atomic-write primitive's home, ruled | `d1ba453c` (`82f5b617`) |
| T-045-12 | FR2 (expand): the primitive + injected-failure battery | `740ceecb` (`a48533a7`) |
| T-045-13 | FR2 (switch): call sites move to the primitive | `c6294ede`, `10b41e27`, `bdc29f93`, `83621574`, `59fa0516`, `04f5d0a3` (`8e6bca03`) |
| T-045-14 | FR2 (contract): delete the writers, land the derived census | `091b2401` (`6867dc3a`) |
| T-045-15 | FR3: split the inventory out of the two byte goldens | `053f55e8` (`05d3a094`) |
| T-045-16 | FR4: one shared skill-inventory oracle | `78daad25` (`0df61155`) |
| T-045-17 | FR5: the scan-test vacuity convention | `c4ba5383` (`4162c648`) |
| T-045-18 | `S2` close (qa-engineer) | `20d9287f` (`c0737c0a`) |
| T-045-19 | FR6: the denylist reaches the write-time redaction seam | `eb03d01b` → firing `a2faaad2` → amendment `0cb08157` (`c84dae57`) |
| T-045-20 | FR7: one control/format-character sanitation pass | `2b9b30c1` (`61d258a7`) |
| T-045-21 | FR8: `specs init --specs-dir` refuses a symlinked target | `f3acf990` (`b3bf58da`) |
| T-045-22 | FR9: the slug-ownership healing lane, decided | ruling `4f890913` + `fa43364e` (`5a82dcbf`) |
| T-045-23 | FR10: the doctor learns `.dadaia/references/` | `9bdb960b`; in-flight bug fixes `43e020e9`, `92b8b3d6` (`94bd7f3d`) |
| T-045-24 | `S3` close (qa-engineer) | `f7012f68` (`21b275c3`) |
| T-045-25 | [shell] FR11 baseline: measure before any cut (V6/V7/V8/V9) | `bdb62406` (capture `.dadaia/tmp/ai-engineer/20260826/T-045-25-baseline.md`) |
| T-045-26 | FR12: the catalog digest curation policy | `5c4f30c9` → firing `04167386` → amendment `d85dfc19` (`b96d95ec`) |
| T-045-27 | FR11: the always-on diet pass | `ba17bbe9` (`974a045f`) |
| T-045-28 | FR13: trim the over-ceiling personas | `47074883` (`a119434c`) |
| T-045-29 | FR14: the AI-surface hygiene residuals | `af7bd369` + `a4754a28` (`4f3fca57`) |
| T-045-30 | FR15: rule the test-Intent vocabulary | `91d559f6` + `96637803` (`81b071af`) |
| T-045-31 | `S4` close (qa-engineer) | `1d7089ec` (`c29c53ed`) |
| T-045-32 | [shell] FR16: the invariants, measured (V10/V11) | `b207c20d` (capture `.dadaia/tmp/software-engineer/20260826/T-045-32-invariants.md`) |
| T-045-33 | Six-axis code review on the thawed tree | `e64a4922` → re-verdict `1bfd9209` (@`27c3374a`) → re-verdict `2a5cec96` (@`395bfb35`) |
| T-045-34 | Security review + the QA release verdict | `ae84021e` → `f837168a` (@`395bfb35`); security verdicts `8b1e4aa3` (REJECTED @`5a8810ac`), `2c23e717` (APPROVED @`395bfb35`), `6214fc35` (re-key) |
| T-045-35 | [git] `rc-1`: PR `feature/0.4.5` → `develop` | **`[-]` — pending push.** On-branch work complete: `e34f1209` (bug reported), `7de4783f` (architect ruling), `395bfb35` (fix), trio verdicts all APPROVE on `395bfb35`. **Remaining:** push `feature/0.4.5` through the chokepoint, open the PR, watch CI to green, merge |
| T-045-36 | Adjustment rounds on the merged scope | **`[ ]` — pending push.** Zero rounds so far, because `develop` cannot be exercised before the push. **Remaining:** exercise the merged `develop`; any finding on this scope opens `rc-2` on the branch |
| T-045-37 | Memory window (SPEC §5) | `e514e679` (reservation `7b80e646`) |
| T-045-38 | `CLOSURE.md` with every sweep | this document (reservation `bb96253a`) |
| T-045-39 | [git] Archive the release | **`[ ]` — pending.** **Remaining:** `git mv specs/releases/v0.4.5 specs/_archive/releases/v0.4.5`, `ACTIVE.md` → `phase: ARCHIVED`, riding one commit with T-045-37/38 |
| T-045-40 | [git] Final-`rc` merge: version bump and PR → `develop` | **`[ ]` — pending push.** **Remaining:** `pyproject.toml` `0.4.4` → `0.4.5`, `CHANGELOG.md` `[0.4.5]` stating the unpublished mint once, APPROVED verdict on the PR head sha, CI green, merge |
| T-045-41 | [git] Ship — merge to `main`, publish NOTHING | **`[ ]` — pending push.** **Remaining:** `develop` → `main` PR, CI green, merge; leave `release.yml`'s `approve` job unapproved; delete `feature/0.4.5` and cut `feature/0.4.6` from `main` in the same step; reconciliation merge into `develop`; capture **V12** and fill `## Ship-without-publish record`; repoint `ACTIVE.md` |

**Marker state at closure:** 34 `[x]`, 2 `[-]` (T-045-35 in flight and T-045-38, this
document), 5 `[ ]` — one operator-pending (T-045-03) and four blocked on the push
(T-045-36, 39, 40, 41). The push itself is an external action the agent fleet cannot take.

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Local CI preflight green (ruff format/check, mypy --strict, lint-imports, pytest) | `dadaia ci preflight` | exit 0 at `b207c20d` — `.dadaia/tmp/software-engineer/20260826/T-045-32-preflight.txt`; re-run by qa-engineer at `27c3374a` and `395bfb35`, unpiped, exit 0 (`reviews/RELEASE-VERDICT.md` §2, re-verdict) |
| Workspace invariants healthy | `dadaia doctor` | "All invariants OK" — `.dadaia/tmp/software-engineer/20260826/T-045-32-doctor.txt` |
| SDD structure clean | `dadaia specs doctor --json` | 0 errors, 4 pre-existing legacy warnings (2 archived-release naming, 2 archived-audit disposition) — `.dadaia/tmp/software-engineer/20260826/T-045-32-specs-doctor.txt` |
| Backlog structure clean | `dadaia backlog doctor` | clean — `.dadaia/tmp/software-engineer/20260826/T-045-32-backlog-doctor.txt` |
| Projections match source; no consumer data in `public/**` | `dadaia public doctor` | `[ok] public-privacy`, `[ok] entities-derivation`, no `[drift]`/`[missing]` — `.dadaia/tmp/software-engineer/20260826/T-045-32-public-doctor.txt` |
| Layer contracts hold, no new accepted edge (A16.2/A2.5) | `lint-imports --config setup.cfg --no-cache` | 9 contracts kept, 0 broken, ignore-edge cap unchanged — `.dadaia/tmp/software-engineer/20260826/T-045-32-lint-imports.txt` |
| FR1 on the executed path, both directions, on the **installed** venv (A1.1–A1.3, A1.7) | PreToolUse hook spawn + direct `classify_path` table | `.dadaia/tmp/software-engineer/20260825/V3-gate-probe.txt` — fresh-repo `AGENTS.md` write allowed; root `DADAIA.md` and `.claude/rules/DADAIA.md` blocked; `repos/<slug>/AGENTS.md` → MUTATING |
| FR2 census: every atomic write routes through one primitive (A2.2) | `pytest tests/unit/core/test_atomic_write_census.py` | AST-shape scan, 2 passed; 13 → 1 recorded in `.dadaia/tmp/software-engineer/20260825/T-045-14-V4-census.txt` |
| FR2 injected-`os.replace`-failure battery, every parameter combination, landed before any deletion (A2.3) | `pytest tests/unit/core/test_atomic_write.py -p no:cacheprovider` | 33 items collected, 21 of them the injected-failure matrix — re-run independently at the S2 close (`reviews/S2-qa-close.md` §2) |
| FR2 production LOC net-negative (A2.6) | `git diff --numstat 740ceecb^..091b2401 -- dadaia_workspace/` | 22 files, +172/−262 = **−90** — `.dadaia/tmp/software-engineer/20260825/T-045-14-fr2-loc-stat.txt`, reproduced by qa (`S2-qa-close.md` §2) |
| FR3 roster catches an added asset while both goldens stay green (A3.1) | `pytest tests/unit/infrastructure/test_install_target_goldens.py tests/unit/infrastructure/test_public_assets_profile.py` | 19 passed; goldens 214→36 and 404→164 lines, policy-only (`S2-qa-close.md` §4) |
| FR4 one skill add/rename/remove is green everywhere after touching one place (A4.2) | `pytest tests/e2e/features/test_public_pipeline.py tests/integration/test_public_assets.py tests/scripts/check_skill_orphans.py` | 17 passed, orphan checker run as a real subprocess (`S2-qa-close.md` §4) |
| FR5 census + mis-rooted-walker RED proofs (A5.1/A5.2) | scan census + three sampled RED/GREEN replays | 19 files / 20 call sites, 3 RED proofs — `.dadaia/tmp/software-engineer/20260825/T-045-17-census.txt` |
| FR6 write-time denylist masking, RED then GREEN, scrub set derived from the schema (A6.1/A6.5) | `pytest tests/unit/features/bugs/test_write_time_denylist_redaction.py` | green, incl. `test_bug_event_redact_scrubs_every_schema_string_field_derived_from_schema` (`S3-qa-close.md` §1) |
| FR7 U+2028 round-trip, ESC-free render, strip-before-mask ordering (A7.1–A7.3, A7.6) | `pytest tests/unit/features/bugs/test_control_format_char_sanitation.py` | green (`S3-qa-close.md` §1); after the F1 rework, 13 passed at `27c3374a` with TAB/LF/CR preserved and ESC/C1/NEL/LS stripped (`T-045-33-code-review.md` re-verdict, per-character probe) |
| FR7 every historical event still parses, none rewritten (A7.4) | `pytest tests/integration/infrastructure/test_live_bugs_ledger_still_parses.py` | green over the full live ledger (1,000+ rows) |
| FR8 symlinked `--specs-dir` refused, capability-probed (A8.1–A8.3) | `pytest tests/contract/cli/test_cli_specs_init_symlink_refused.py` | green; skip is a real `_can_symlink()` probe, not a platform guess (`S3-qa-close.md` §1) |
| FR9 INV-6 reports a pre-existing collision, `fixable=False` (A9.1–A9.3) | `pytest tests/unit/test_spec_context_doctor.py -k inv6` | 8 passed, no-regression pin green (`S3-qa-close.md` §1) |
| FR10 reference clone is doctor-clean and outside the context lifecycle (A10.1–A10.4) | `pytest tests/unit/features/spec_context/test_dadaia_references_lifecycle_sanction.py` | green (`S3-qa-close.md` §1) |
| FR12 `ctx_inject`'s digest logic byte-unchanged (A12.2) | `git diff --stat bdb62406..HEAD -- dadaia_workspace/hooks/ctx_inject.py` | empty, confirmed independently at the S4 close |
| FR11/FR13 always-on measurement, before and after, same script (A11.1/A13.1) | `.dadaia/tmp/ai-engineer/20260826/measure_v6_v7_v9.py` | baseline `T-045-25-baseline.md`; after `T-045-27-after.md`, `T-045-28-after.md`; qa re-run reproduced them exactly — `.dadaia/tmp/qa-engineer/20260826/S4-close-v6v7v9-raw.md` |
| FR12 bound-session prefix measured on a **real** session, before and after (A12.1) | `dadaia context bind` + `python -B -m dadaia_workspace.hooks.ctx_inject` | 1,505.6 → 877.8 tokens — `.dadaia/tmp/ai-engineer/20260826/v8-stdout.txt` / `v8-after-stdout.txt`; qa reproduced 7,393 chars / 660 words / 877.8 tokens (`.dadaia/tmp/qa-engineer/20260826/v8-stdout.txt`) |
| FR15 zero off-taxonomy Intent declarations (A15.2) | `grep -rn -E 'Intent: *(REGRESSION\|BUG)\b' tests/` | zero hits, exit 1 — `.dadaia/tmp/software-engineer/20260826/T-045-30-scan.txt` |
| V10/V11 release deltas measured, not estimated (A16.3/A16.4) | `git diff --numstat 68658783..<sha> -- dadaia_workspace/` | `.dadaia/tmp/software-engineer/20260826/T-045-32-v10.txt`, `T-045-32-v11.txt`, `T-045-32-v10-attribution.txt` |
| rc-1 push gate replayed on the very range that exposed the foreign-slug defect | `dadaia ci push-gate-check` (real refspec replay) | exit 1 → exit 0 with the 11 objects clean after `395bfb35`; a bare foreign slug still BLOCKS — `.dadaia/tmp/software-engineer/20260827/foreign-slug-gate-before-after.txt` |
| Trio APPROVE on one sha (final-rc precondition) | qa + code + security verdicts on `395bfb35` | `reviews/RELEASE-VERDICT.md` (re-verdict), `reviews/T-045-33-code-review.md` (re-verdict), `verdicts/395bfb352a4cdefa7cbbbf06d0c1908a1af38728.handoff.json` (commit `2c23e717`, re-keyed `6214fc35`) |
| Open-bug ledger at closure | `dadaia bugs status` | `[ok] 1 open bug(s)` — exactly `windows-xdist-workers-crash-on-unit-fast-tier` (AS-5) |
| Memory atoms clean after the memory window | `dadaia specs doctor` | 0 errors at `e514e679` (T-045-37 done criterion) |

## Size accounting

**Mandatory** (FR21b/A21.4). Every figure below was produced by an agent with a shell and
captured under `.dadaia/tmp/<agent>/<date>/`; `product-engineer` measured nothing itself.

### V10 — production LOC (`dadaia_workspace/`, excluding `public/`), base `68658783`

| Capture point | Measured | Source |
|---|---|---|
| `b207c20d` (T-045-32, the release's own invariant capture) | **+464 / −426 = +38** | `.dadaia/tmp/software-engineer/20260826/T-045-32-v10.txt` |
| `27c3374a` (after the F1 rework) | +471 / −426 = **+45** | qa re-measurement, `reviews/RELEASE-VERDICT.md` §2 (the +7 is exactly F1's `+25/−18` in `core/models/bugs.py`) |
| `395bfb35` (after the foreign-slug fix) | not re-captured as a V10 total; the delta is `+30/−7` across two files, of which **`+2/−1` is logic** (one regex literal) and the rest docstring | `reviews/T-045-33-code-review.md` re-verdict @`395bfb35` |

**The net is positive, and it is justified per FR rather than waived** (SPEC §3, A16.3):

| FR | Commits | Net | Justification |
|---|---|---:|---|
| FR1 gate LAW predicate | `6dcf278f` | −1 | a branch deleted, nothing added |
| certify residual (bug) | `7681d4f3` | +17 | FR23 Firing 1 **SOUND** — the added lines *are* the missing parse-and-bound seam; the old half-seam was deleted, not wrapped |
| FR2 atomic write | `740ceecb` … `091b2401` | **−90** | the deletion engine: 13 writers → 1 primitive |
| FR6 denylist seam | `eb03d01b`, `0cb08157` | +14 | Firing 2 **SOUND-WITH-AMENDMENT** applied before the marker flip; DI through the composition root; hand-kept field list deleted |
| FR7 sanitation | `2b9b30c1` | +41 | one regex + one ordering line at the write seam plus the reader's `split("\n")` fix — verified by the code review as **39 prose, 2 logic** |
| FR8 symlink refusal | `f3acf990` | +5 | one call-site swap onto the existing hardened resolver |
| FR9 INV-6 | `fa43364e` | +26 | architect ruling: growth **is** the missing detector, not a branch on a verb |
| FR10 references | `9bdb960b`, `92b8b3d6` | +9 / 0 | one allowlist line; the reconcile fix collapsed two hand-kept lists into one canonical set (+54/−54) |
| FR12 catalog policy | `5c4f30c9`, `d85dfc19` | +16 | Firing 3 **SOUND-WITH-AMENDMENT** applied; the twin writer curates identically |
| FR14 residuals | `a4754a28` | +1 | wording only |

Three architect-ruled seams (+47), one ruled invariant (+26) and FR7 (+41) against a single
−90 deletion engine. **The operator's ruling is requested on this positive net** — the SPEC
required it to be justified per contributing FR or refused, and the justification is above;
no FR in the list is additive-by-preference.

**Three largest additions by file** (measured where captured; the release captured per-FR
attribution rather than a whole-release per-file ranking):

| File | LOC added |
|------|-----------|
| `dadaia_workspace/core/atomic_write.py` | `+75` (new primitive, the expand step) |
| `dadaia_workspace/core/models/bugs.py` | `+31` at FR7's landing, then `+25/−18` at the F1 rework — 24 of those 25 lines are the rewritten `#:` block |
| `dadaia_workspace/features/spec_context/doctor.py` | `+26` (INV-6) |

**Three largest deletions by file:**

| File | LOC deleted |
|------|-------------|
| `tests/unit/features/specs/test_migration_symlink_hardening.py` | `−386` (`+17`) — the 10-case hand-kept characterization table; 9 unrelated symlink-security tests retained |
| `dadaia_workspace/**` at the FR2 contract commit `091b2401` | `−132` across 19 production files (all 13 writers and shims) — per-file ranking inside that commit was not separately captured |
| `dadaia_workspace/hooks/_common.py` | `−11` (the writer deletion; the only hook file touched all release) |

### V11 — AI-surface LOC (`public/{agents,skills,data,entities}/**`)

**+213 / −251 = −38 (negative — A16.4 holds).** agents −93 · skills +53 (relocated persona
overflow, on-demand, never always-on) · data +2 · entities 0. Unchanged at `27c3374a` and at
`395bfb35` (neither touches `public/**`).

### V6–V9 — the token-economy program, measured before and after

| Metric | Baseline (T-045-25) | After S4 | Target | Verdict |
|---|---:|---:|---|---|
| **V6** always-on tokens (Claude Code) | 21,527.4 | **20,502.0** (−4.8%) | ≤3,500 | **MISSED** |
| **V7** negations (Claude Code) | 299 | **257** (−14.0%) | ≤60 | **MISSED, improved** |
| **V8** bound-session injection prefix | 1,505.6 | **877.8** (−41.7%) | ≤700 | **MISSED** |
| **V9** personas above the 220-line ceiling | 5 | **5** (fleet source 2,170 → 2,077 lines, −93) | 0 | **PARTIAL** |

**The reasons, stated rather than redefined.**

- **V6.** Persona bodies are 16,344 tokens — 76% of the always-on set — and `DADAIA.md`
  alone (2,559 words / 3,403.5 tokens per copy) already exceeds the whole 3.5k target before
  a single persona or skill description is counted. T-045-27's own scope excluded
  line-ceiling relocation (that lever is T-045-28's) and T-045-28 is bounded by **AS-1** to
  siblings that already exist. Governed by **AS-3**: the entry is consumed by executing and
  measuring the pass, not by reaching the number. **Honest miss — the operator rules.**
- **V7.** 226 of the 257 remaining negations (88%) sit in persona bodies, many inside
  protected hard-stop sentences that A13.3 forbids weakening. `DADAIA.md`'s own count halved
  (58 → 28). T-045-28's pointer idiom "referenced, not restated" added **+3 back** (254 →
  257) and was flagged in its own coverage table rather than hidden; rewording it positively
  is an intake candidate. **Honest miss — the operator rules.**
- **V8.** The remaining prefix is two floors: the tech-stack digest (~564 tokens,
  `_digest_tech_stack`) which A30.3 pins **outside** FR12's lever, and the catalog's own
  ~314-token floor from keeping `slug`/`title`/`path` on every entry (A12.3 — every atom must
  stay one self-pull step away). Closing the rest requires an FR that touches `ctx_inject`,
  explicitly out of scope (§4.6). **Honest miss — the operator rules.**
- **V9.** Five, not four (see the drift below). After the pass: `product-engineer` 279,
  `qa-engineer` 269, `ai-engineer` 252, `software-architect` 250, `software-engineer` 245
  (source 243). Each residual is named with its non-relocatable reason in
  `reviews/T-045-28-coverage-table.md`; **A13.4 is satisfied by naming them here, never by
  silently accepting them.** A13.1's real acceptance — a measured reduction with a coverage
  table — is met: −93 source lines, all 34 coverage rows opened and verified at their
  surviving home by qa-engineer (100%, against a ≥50% floor).

**No law was dropped.** Both coverage tables (`reviews/T-045-27-coverage-table.md`,
`reviews/T-045-28-coverage-table.md`) map every removed block to its surviving home, and
every row was independently opened at that home.

### Ceilings

| Ceiling | Before | After | Justification (only if decreased) |
|---------|--------|-------|------------------------------------|
| `C90` (`max-complexity`) | `63` | `63` | n/a — unchanged; `git diff 68658783..HEAD -- pyproject.toml` shows zero change, never raised |
| `PLR1702` (`max-nested-blocks`) | `6` | `6` | n/a — unchanged |

**Nesting-violation count:** `0` — `ruff check` is part of `dadaia ci preflight`, green at
every capture point with `PLR1702` pinned at 6. Observed maximum cyclomatic complexity is 61
against the pinned 63; ratcheting the ceiling down to 61 is a companion-release closure step,
deliberately not taken here (ceilings ratchet only downward, and this release refused to
raise or lower a ceiling it did not earn).

### Tests

`tests/` **+2,817 / −980 = +1,837** lines (re-measured by qa at `27c3374a`; `+2,749/−980 =
+1,769` at the T-045-32 capture point, the +68 being F1's three new cases). The growth is
AST-derived censuses, a call-site oracle delegating to the product's own enumeration, and a
21-case injected-failure matrix landed *before* any writer was deleted; what left is the
hand-kept-table class that had already produced four registered bugs. Both the code review
and the QA verdict judge the delta **higher-value per line** than what it replaced.

## Ship-without-publish record

**To be filled at T-045-41** — this section records A16.8's three verifications (capture
**V12**), which are only checkable after the `develop` → `main` merge fires `release.yml`.
The three verifications owed are:

1. `release.yml`'s `approve` job is **pending and unapproved** on the `release-gate` GitHub
   environment, so `publish` never ran.
2. `git tag --list 'v0.4.5'` is **empty** — no tag was minted.
3. PyPI's latest published version is still **`0.4.4`**.

**Already true at `395bfb35`, recorded here as the partial evidence that exists today**
(qa-engineer, `reviews/RELEASE-VERDICT.md` §5): `pyproject.toml` still reads
`version = "0.4.4"` (the bump is T-045-40's, deliberately deferred to the final `rc` per D6);
`git diff 68658783..27c3374a -- pyproject.toml .github/workflows/release.yml` is **empty** —
neither file was touched anywhere in the release; and `git tag -l v0.4.5` returns nothing.

## Drifts

### fr13-four-vs-five-personas-measured

**Description.** SPEC FR13 and TASKS T-045-28 both name **four** over-ceiling personas
(`product-engineer`, `qa-engineer`, `ai-engineer`, `software-architect`). The T-045-25
baseline measured **five** — `software-engineer` (245 source / 247 projected) was over the
ceiling and omitted from both documents. The number in the SPEC was inherited from v0.4.4's
own closure and was stale by the time this release measured it.

**Resolution.** The dispatching agent instructed T-045-28 to include `software-engineer` in
the pass, which was correct: the acceptance is a measured fleet reduction, and excluding a
persona that the measurement itself identified would have been dishonest accounting. TASKS
and SPEC were left untouched (amending an `Aprovado` document mid-implementation without an
operator ruling is a worse defect than the stale count). **V9 is therefore 5 → 5, not 4 → 4**,
and the fleet net is −93 source lines. `software-engineer` moved 245 → 243 at source (−2);
its projected count reads 245 → 245 because of harness overlay padding, explained in
`.dadaia/tmp/ai-engineer/20260826/T-045-28-after.md`. **The operator/PM reconcile the SPEC's
"four" wording**; this closure records the measured five.

**Memory updates:** `specs/memory/product/agents/agentic-entities.md` — carries the persona
ceiling state as measured (five above the ceiling, fleet mass and the reason it is the
dominant always-on contributor), never the stale four.

### fr12-curation-default-ratified-as-product-truth

**Description.** FR12's mechanism is `_TLDR_INJECTED_CATEGORIES = frozenset({"core"})` in
`dadaia_workspace/features/specs/catalog.py`: the persisted `catalog.json` drops `tldr` for
every atom whose `category` falls outside the tier set. No current atom carries
`category: core` — all 26 are `category: product` — so today's live behaviour is **drop all
persisted tldrs**, the theoretical floor of this lever. T-045-26, FR23 Firing 3 and the S4
close all deferred ratification of that default to `product-engineer` at closure.

**Resolution — ratified.** `product-engineer` ratifies `frozenset({"core"})` as the product's
curation policy, and this closure records it as product truth for three reasons: (a) A12.3
holds — every entry keeps `slug`/`title`/`path`, so every atom stays exactly one self-pull
step away and `index.md` renders the full, uncurated catalog; (b) the tier key is an existing
required frontmatter field, so the policy costs no schema change and `rank` (documented as
alphabetical order, **not** priority — F-77) was correctly rejected as a tier signal; (c) the
policy lives at the generator and is applied by **both** writers, pinned by the F-84 contract
on the written output (AM-1) — a curation applied by one writer only would have re-created
the divergent-renderer class the ledger already records. The residual ~178-token V8 gap this
default cannot close is recorded above as an honest miss.

**Memory updates:** `specs/memory/product/index.md` + `catalog.json` (regenerated under the
policy) and `specs/memory/product/platform/context-management.md` (the leaner bound-session
prefix).

### fr1-landed-without-the-manifest-arm

**Description.** SPEC FR1 describes an **additive manifest arm** over a static fail-closed
floor: the floor matches LAW unconditionally and a `.dadaia/agentic/manifest.json` lookup
only *extends* LAW. The landed fix has **no manifest arm at all** — `_is_law_path` lost a
parameter and the branch that shadowed the floor, and what remains is a pure string predicate
performing **zero I/O**.

**Resolution.** Simpler and safer than specified: A1.7 (CWE-284 — a manifest edit can never
demote a floored LAW path) now holds *by construction* rather than by a guard, and A1.3's
manifest-enumerating contract test still pins every manifest-tracked projection as LAW. Net
−1 line on the classifier, one decision path where there were two. Recorded, not refused.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the LAW class restated by
**origin**, with a repo's own domain-scoped `AGENTS.md` named explicitly as MUTATING.

### fr2-thirteen-writers-not-eleven

**Description.** SPEC FR2 and TASKS enumerate **eleven** writers (8 named + 3 inline). The
T-045-13 scan found **thirteen**: `features/migrate/state_v3.py::_atomic_write_json` (added
by a later feature, after the original census was written) and an inline
`tmp.write_text(...); tmp.replace(...)` in `features/migrate/bugs_single_file.py`.

**Resolution.** Migrated under the dispatcher's binding scope ruling — SPEC A2.2 requires the
census to be **derived by scan**, so a scan-derived total exceeding a hand-written enumeration
is the acceptance working as designed, never scope creep. 13 → 1, confirmed by the census test
and by `.dadaia/tmp/software-engineer/20260825/T-045-14-V4-census.txt`.

**Memory updates:** `specs/memory/architecture.md` — one atomic-write primitive and its core
file-I/O ratchet entry, citing AR-1.

### write-set drifts recorded in the QA closes

Four TASKS write sets named paths or owners that the correct work did not match. In every
case the work is right and the document was stale or under-scoped at authoring time; none was
a defect in execution, and none was silently absorbed.

| Task | What TASKS said | Where the work correctly landed | Recorded by |
|---|---|---|---|
| T-045-15 | `tests/e2e/features/…`, `tests/integration/…` | `tests/unit/infrastructure/test_install_target_goldens.py`, `…/test_public_assets_profile.py` — where the two goldens already lived | `S2-qa-close.md` §4 |
| T-045-19 | one file | plus `features/bugs/service.py` and `cli/commands/bugs.py` — **necessary**: `core` cannot import the loader, so a caller must hand the terms in, and putting enforcement in the CLI would leave `BugService` able to write raw terms | FR23 Firing 2 §2, `S3-qa-close.md` |
| T-045-21 | `features/specs/**` | `cli/commands/specs.py` — the hardened resolver seam A8.2 requires reusing is consumed at the CLI call site | `S3-qa-close.md` §3 |
| T-045-29 | `ai-engineer` as sole owner | the F-7/F-8/F-10 residuals are production Python **outside** `public/**`, so `software-engineer` swept them in a second commit under the same task id | `S4-qa-close.md` §6 |

**Memory updates:** none — these are document-accuracy drifts, not product behaviour.

### a4-4-net-negative-test-loc-not-met-as-written

**Description.** A4.4 demands "net-negative test LOC" for FR4. Measured by qa: the whole
commit is **+150** (dominated by the new 52-line shared oracle) and the three named consumers
alone are **+97**. Not net-negative by any count.

**Resolution.** A4.4's *substance* — one derived oracle replacing three hand-kept inventories,
killing the structural cause of two v0.4.4 bugs — is fully met (A4.1–A4.3). Unlike FR2/FR3,
FR4 introduces a new shared module rather than only deleting, so the raw line count trades a
small addition for eliminating three independently-drifting copies. Recorded as a
**definition-precision gap in A4.4's wording**, not as a defect in the work, and routed to
intake for future FRs of this shape. Not waived, not reworked.

**Memory updates:** `specs/memory/quality-assurance.md` — the derived roster and the shared
skill-inventory oracle as the current state.

### s3-is-production-loc-net-positive

**Description.** S1 is −1 and S2 is −90; **S3 is +96** across 10 files. The release-wide net
is therefore positive (+38 at the capture point).

**Resolution.** Expected and individually justified: S3's theme is closing gaps — write-time
enforcement, sanitation, a symlink refusal, a missing detector, a sanction — and FR6–FR10
carry no net-negative-LOC acceptance clause, unlike FR2/FR3/FR4. FR9's own architect ruling
states it plainly: *growth is the missing detector itself, not a branch on a verb.* The
release-wide accounting is reconciled in `## Size accounting` above, where the operator's
ruling on the positive net is requested.

**Memory updates:** none beyond the per-FR atoms already listed.

## Memory updates

Written in the CLOSURE phase at commit `e514e679` (T-045-37), the two mandatory rewrites
first, then the rest, one authoring pass per atom. `dadaia specs doctor` reports 0 errors.

- `specs/memory/product/sdd/sdd-gate-v3.md` — **mandatory rewrite.** The LAW path class is
  restated by **origin** (the workspace-root law family plus manifest-tracked projections),
  and a repo's own domain-scoped `AGENTS.md`/`CLAUDE.md` is named explicitly as MUTATING.
- `specs/memory/product/distribution/pypi-distribution.md` — **mandatory rewrite.** The
  published lineage stays `0.4.2 → 0.4.4` while `main` reads `0.4.5`; the one-axis law's
  wording now distinguishes the **published lineage** from **`HEAD`**, because the
  minted-unpublished shape is repeated rather than accidental.
- `specs/memory/architecture.md` — the one atomic-write primitive at `core/atomic_write.py`,
  its core file-I/O ratchet entry with the AR-1 rationale, and the persona size contract
  after FR13.
- `specs/memory/quality-assurance.md` — the derived roster and the shared skill-inventory
  oracle that replaced three hand-kept inventories; the scan-vacuity convention (a two-line
  convention, never a harness); the Intent vocabulary ruling.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — the bug-event write-time
  redaction seam (one loader, consumed twice) and the single control/format-character
  sanitation pass, with its strip-before-mask ordering.
- `specs/memory/product/platform/workspace-doctor.md` — `.dadaia/references/` as a sanctioned
  operator-owned subtree, **outside the context lifecycle**; the registry-wide `INV-6`
  slug-ownership check.
- `specs/memory/product/platform/context-management.md` — the slug-ownership healing-lane
  outcome (report-only, `fixable=False`) and the leaner bound-session injection prefix.
- `specs/memory/product/agents/agentic-entities.md` — the measured always-on budget
  (~20.5k tokens, 257 negations against ≤3.5k/≤60) and the persona ceiling state.
- `specs/memory/product/distribution/public-asset-distribution.md` — the policy-only byte
  goldens and the derived roster.
- `specs/memory/product/sdd/specs-doctor.md` — updated only to point at `INV-6`'s home in
  `[[workspace-doctor]]`; no `specs doctor` rule changed (FR9 lands in `dadaia doctor`, and
  FR8's refusal reuses the existing resolver posture rather than adding a doctor rule).
- `specs/memory/product/index.md` + `specs/memory/product/catalog.json` — regenerated under
  FR12's curation policy; catalog order and membership are unchanged.
- `specs/memory/tech-stack.md` — **no change:** the release added no third-party dependency
  and changed no approved technology. Confirmed independently at every segment close.

## Dispositions

### Backlog — 14 entries, `CONSUMED · v0.4.5` → `DELIVERED · v0.4.5`

`product-engineer` **does not edit `specs/backlog/BACKLOG.md`** — the PM executes the sweep.
The 14 lines below are `## LEDGER` lines 738–751 of that file; each must be **updated in
place** to `DELIVERED · v0.4.5`, never duplicated with a second line (BL-DUP). Purge-on-pick
already removed every one of these slugs from `## ACTIVE` in the definition commit.

| Record | Kind | Terminal disposition | Evidence |
|--------|------|-----------------------|----------|
| `atomic-write-primitive-consolidation` | backlog | `DELIVERED · v0.4.5` | FR2 · `091b2401` · `S2-qa-close.md` §2 |
| `byte-golden-test-inventory-roster-split` | backlog | `DELIVERED · v0.4.5` | FR3 · `053f55e8` · `S2-qa-close.md` §4 |
| `coupled-inventory-shared-oracle` | backlog | `DELIVERED · v0.4.5` | FR4 · `78daad25` · `S2-qa-close.md` §4 (A4.4 wording gap recorded under `## Drifts`) |
| `scan-test-vacuity-guard` | backlog | `DELIVERED · v0.4.5` | FR5 · `c4ba5383` · `S2-qa-close.md` §4 |
| `doctor-slug-ownership-uniqueness` | backlog | `DELIVERED · v0.4.5` | FR9 · ruling `4f890913` + `fa43364e` · AS-4's implement arm taken |
| `bug-append-write-time-denylist-redaction` | backlog | `DELIVERED · v0.4.5` | FR6 · `eb03d01b`+`0cb08157` · `S3-qa-close.md` §1 |
| `specs-init-symlinked-target-refusal` | backlog | `DELIVERED · v0.4.5` | FR8 · `f3acf990` · `S3-qa-close.md` §1 |
| `bug-event-control-character-sanitation` | backlog | `DELIVERED · v0.4.5` | FR7 · `2b9b30c1`, narrowed at `27c3374a` · bundles the MEDIUM unicode bug (D3) |
| `always-on-token-diet` | backlog | `DELIVERED · v0.4.5` | FR11 · `ba17bbe9` · consumed by executing and measuring the pass (**AS-3**); V6/V7 missed and recorded |
| `memory-catalog-digest-trimming` | backlog | `DELIVERED · v0.4.5` | FR12 · `5c4f30c9`+`d85dfc19` · V8 1,505.6 → 877.8, miss recorded |
| `persona-line-ceiling-trim` | backlog | `DELIVERED · v0.4.5` | FR13 · `47074883` · bounded by **AS-1**; fleet −93 source lines, five residuals named |
| `ai-surface-hygiene-residuals` | backlog | `DELIVERED · v0.4.5` | FR14 · `af7bd369`+`a4754a28` · `S4-qa-close.md` §3 |
| `intent-taxonomy-vocabulary-ruling` | backlog | `DELIVERED · v0.4.5` | FR15 · `91d559f6`+`96637803` · zero off-taxonomy declarations |
| `dadaia-references-doctor-sanction` | backlog | `DELIVERED · v0.4.5` | FR10 · `9bdb960b` · operator ruling O4 |

**A15.3, stated as the SPEC requires:** ruling the `REGRESSION`/`BUG` Intent tokens onto
`CONTRACT` inside `dadaia-test-stewardship`'s taxonomy section **does not pre-empt** the
ratified `nine-skill-study-execution` Update of that same skill (O3). The later release
**rebases on this text rather than reverting it** — the vocabulary decision is complete in
itself and the Update inherits it.

### Bugs — 12 `Closed`, 1 `Closed` + `superseded_by`, 1 left open

| Record | Kind | Terminal disposition | Evidence |
|--------|------|-----------------------|----------|
| `sdd-gate-blocks-fresh-repo-root-agents-md` (MEDIUM) | bug | `Closed` | `resolved` @ `6dcf278f` — one shared root cause with the row below (D2) |
| `repo-agents-md-law-gate-contradicts-template` (MEDIUM) | bug | `Closed` | `resolved` @ `6dcf278f` — same cause, same commit |
| `dadaia-task-manager-stale-workspace-protocol-citation` (LOW) | bug | `Closed` | `resolved` @ `db9d0c20` — fixed at source and re-projected |
| `certify-skip-detail-leaks-full-codex-output` (LOW, CWE-532) | bug | `Closed` | `resolved` @ `7681d4f3` — FR23 Firing 1 **SOUND** |
| `codex-probe-unit-fixture-carries-real-session-uuid` (LOW) | bug | `Closed` | `resolved` @ `5c9be8ed` — synthetic UUID |
| `bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM) | bug | `Closed` | `resolved` @ `2b9b30c1` — bundled into FR7 (D3) |
| `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` (LOW) | bug | `Closed` + `superseded_by: atomic-write-primitive-consolidation` | `superseded` appended at definition (D4); the leak class is structurally impossible after `091b2401`, and the characterization test that pinned the leaking behaviour was deleted in the same commit (A2.4) |
| `frozen-clock-ratchet-scans-tests-tmp-scratch-dir` (LOW) | bug | `Closed` | `resolved` @ `0d9d49bb` — found in flight during T-045-09's investigation |
| `…-md-canonical-table-omits-sanctioned-references` | bug | `Closed` | `resolved` @ `43e020e9` — found in flight, S3 |
| `dadaia-reconcile-quarantines-sanctioned-references-clone` | bug | `Closed` | `resolved` @ `92b8b3d6` — found within the hour of FR10 landing, because a **second** hand-kept allowlist existed; both lists collapsed into one canonical set, net 0 |
| `mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes` (LOW) | bug | `Closed` | `resolved` @ `aea57a34` — root-caused, **never quarantined** |
| `bug-event-sanitation-strips-tab-lf-cr-from-free-text` (HIGH) | bug | `Closed` | reported `2dbc2b41`, `resolved` @ `27c3374a` — the code review's F1; Arm B order correct, no history rewritten |
| `push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-substrings` (HIGH) | bug | `Closed` | reported `e34f1209`, ruled `7de4783f`, `resolved` @ `395bfb35` — the rc-1 push-gate false positive |
| `windows-xdist-workers-crash-on-unit-fast-tier` (LOW) | bug | **Open — unpicked** | `reviews/S1-AS5-xdist-verdict.md`. The bounded root-cause attempt was inconclusive; the failing unit is the xdist **worker OS process**, not a test, so a per-test quarantine would be a test-level workaround for a non-test-level defect. Per **AS-5** the bug stays open and is **never closed by a quarantine**; no quarantine was filed. Two CI-config mitigations are routed to intake |

**Ledger state at closure:** `dadaia bugs status` → `[ok] 1 open bug(s)`, exactly the AS-5
item. Open bugs across the release: **8 → 1**, with six more registered and closed in flight.

## Test dispositions

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| deletion | the 10-case hand-kept characterization table inside `tests/unit/features/specs/test_migration_symlink_hardening.py` (−369 net) — it pinned the *leaking* atomic-write behaviour as current | deleted in the same commit that made leaking impossible; the 21-case injected-failure matrix in `tests/unit/core/test_atomic_write.py` is the replacement coverage; 9 unrelated symlink-security tests retained | `091b2401` · ratified `RELEASE-VERDICT.md` §3 |
| deletion | three hand-kept skill inventories (`EXPECTED_SKILLS` literal, a path-assertion list, the orphan checker's own roster) — the root cause of two v0.4.4 bugs | one derived oracle, `tests/helpers/skill_inventory_oracle.py`, delegating to the product's own enumeration | `78daad25` · ratified `RELEASE-VERDICT.md` §3 |
| demotion | the two byte goldens' file-inventory blocks (214→36 and 404→164 lines) | goldens **kept as policy-only SENTINEL**; the inventory assertion moved to a roster derived by scanning `public/**` | `053f55e8` · ratified `RELEASE-VERDICT.md` §3 |
| KEEP-with-follow-up | `tests/unit/features/spec_context/test_dadaia_references_lifecycle_sanction.py` — imports a private module (code review F5) | **KEEP.** Justified inline (it is the real seam behind no-arg resolution); single instance, no recurrence in this release's bug history. Promote the seam to a public name in a later pass | `RELEASE-VERDICT.md` §3 |
| KEEP-with-demotion-decision | `tests/integration/infrastructure/test_live_bugs_ledger_still_parses.py` — bound to the live, growing ledger as its oracle (code review F6) | **KEEP, demotion deferred and now decided here: KEEP as-is for one more release.** A7.4 needed exactly one live proof; the test is read-only and vacuity-checked, and the same-shaped flake found in S4 was a *different* test, already root-cause fixed. Re-evaluate at the next closure that touches the ledger reader; if it flakes once, it demotes to a fixture-bound test with a synthetic multi-thousand-row ledger | `RELEASE-VERDICT.md` §3, this section |
| quarantine expiry | — | **none.** The quarantine lane is **empty**: zero quarantines existed at the start of this release, zero were added, zero expired. The one flake observed (`test_staging_step_copies_scoped_subset_without_touching_repo_git_tree`) was **root-cause fixed** at `aea57a34` with its bug registered, never quarantined; and AS-5's bug was explicitly refused a quarantine verdict | `S4-qa-close.md` §5, `S1-AS5-xdist-verdict.md` |
| SCAFFOLD expiry | — | **none.** Every new test file this release declares `Intent:` plus size in its module docstring at birth — zero SCAFFOLD, zero undeclared, across 10 new S1–S3 files plus 5 cases appended at `395bfb35` | `RELEASE-VERDICT.md` §3, re-verdict |
| taxonomy sweep | 11 off-taxonomy `Intent:` declarations (8 `REGRESSION`, 3 `BUG`) | **swept onto `CONTRACT`** and the vocabulary ruled once in `dadaia-test-stewardship`'s taxonomy section; scan confirms zero remaining off-taxonomy declarations | `91d559f6` (ruling), `96637803` (sweep) · `S4-qa-close.md` §3 |

**Zero new `tests/e2e/**` files** across the whole release, so SPEC §3's "no new e2e without a
named `qa-engineer` exception" holds trivially and the pre-existing LARGE-tier census is not
worsened.

## Record-only observations

INFO-grade or already-fixed-at-HEAD observations. Each was recorded in its reviewer's own
findings, carries no actionable fix surface, and **terminates here** — none enters the PM's
intake report.

| Source | Observation | Why record-only |
|---|---|---|
| `T-045-33-code-review.md` F4 (LOW) | The FR2 contract commit also switched 12 call sites no switch commit had touched, with no independently-green switch-only intermediate | Each is a mechanical call swap; that commit's full-suite run is green and no harm is evidenced. Recorded because D7's guarantee is per-site — already-fixed-at-HEAD in substance |
| `T-045-33-code-review.md` F10 (INFO) | 17 comment lines plus 10 docstring lines for 2 lines of logic in the sanitation block (a 20:1 ratio) | Awareness-only. The block was rewritten at the F1 rework; the prose is load-bearing and high quality, and no rule caps the ratio |
| `S2-qa-close.md` §6 item 1 | The dispatched evidence map said "29-test battery"; qa counted 33 collected items (21 of them the injected-failure matrix) | A headcount label mismatch, not a coverage gap — A2.3's substance is met either way |
| `S2-qa-close.md` §6 item 4 | FR3's cited golden line-count sub-ranges could not be reproduced from a whole-file read | qa recorded its own whole-file counts (214→36, 404→164) as the verified numbers; direction and outcome identical |
| `RELEASE-VERDICT.md` §2 (A16.6) | 14 picked entries were still `CONSUMED · v0.4.5` at the trio review | Correct sequencing — the flip to `DELIVERED` is a CLOSURE step, executed by the PM off this document |

## Intake candidates

Residuals for the PM's operator-facing intake report. **`product-engineer` creates no backlog
entry** — every item below is listed, never materialized (ADR #15).

### To be adjudicated

1. **A4.4's wording gap.** "Net-negative test LOC" should scope to *net LOC excluding a new
   shared module*, mirroring A2.6's "production LOC" framing, for any future FR of this
   consolidation shape. (`S2-qa-close.md` §6/§7.)
2. **`tests/helpers/scan_population.py`'s self-inconsistent docstring** — prose says
   "20 files / 21 call sites" against its own enumerated 19/20. One line, unfixed at HEAD.
   (`S2-qa-close.md` §6 item 2; code review F7.)
3. **The tech-stack digest floor (~564 tokens, `_digest_tech_stack`)** is the next V8 lever
   and is out of FR12's scope by A30.3 — closing it needs its own FR touching `ctx_inject`.
   (`S4-qa-close.md` §7.1.)
4. **`dadaia-step0-memory-bootstrap`'s "tldr/summary" wording** should read "summary" — the
   persisted catalog no longer carries `tldr` under the ratified default. (`S4-qa-close.md`
   §7.3; FR23 Firing 3.)
5. **The "referenced, not restated" pointer idiom trips the V7 negation regex** (+3). Reword
   positively (e.g. "canonical home:") in a future pass, without reopening line-count scope.
   (`S4-qa-close.md` §7.4.)
6. **No test enforces the Intent-token taxonomy itself.** A lightweight grep-based contract
   would catch regrowth of the `REGRESSION`/`BUG` drift class; out of T-045-30's dispatched
   scope. (`S4-qa-close.md` §7.5.)
7. **The stale-citation class has no structural close.** Three instances across two releases,
   each caught only after the fact by the same enforcer. Named anchors or citation derivation
   is the candidate direction. (Code review F3.)
8. **FR23 Firing 1's LOW residual** — `features/certification/service.py`'s marker-mismatch
   branch still embeds capped-but-unredacted output instead of routing through
   `_codex_capped_detail`. One line, when the file is next touched. (Code review F9.)
9. **Promote the private-symbol-importing seam** behind no-arg context resolution to a public
   name, so a contract test stops importing a leading-underscore module. (Code review F5.)
10. **The clone-URL sub-class of the whole-token slug trade** — `…/<slug>.git` and
    `…:<org>/<slug>.git` now go from BLOCK to MISS on the auto-derived slug layer, while the
    same URL without `.git` still blocks. Inside the ruled trade, but the highest-value
    instance of it and worth naming explicitly. (Code review F11 @`395bfb35`.)
11. **Two CI-config mitigations for the AS-5 bug**, both `.github/workflows/ci.yml` changes,
    both outside this release's picked FR set: (a) job-level retry/backoff on the
    windows-latest leg of `unit-fast-cross`; (b) a pinned, smaller `-n` worker count for that
    leg. (`S1-AS5-xdist-verdict.md`.)
12. **The five-persona ceiling residual.** Five personas remain above 220 lines after FR13's
    pass, bounded by AS-1 to siblings that already exist. Closing the ceiling needs the
    `nine-skill-study-execution` sibling mechanisms (ratified as provenance by O3, execution
    unpicked) or an explicit operator decision to raise or retire the 220 ceiling. Both the
    SPEC's stale "four" wording and the target itself need the operator's ruling.
13. **`public-assets-single-source-engines`.** Named while drafting the companion release's
    idea specs on this branch: the public-assets surface carries several parallel engines that
    should resolve to one source, with the deferred engines' bug ids attached. Listed here so
    it reaches an operator-facing intake report instead of living only inside a draft.
14. **FR9's accepted residual risk.** Between a registry migration and the next `dadaia
    doctor` run, a colliding registry can still be destroyed by `dead()` on one owner. The
    architect accepted this deliberately (guarding `dead()` was ruled out by the earlier
    Firing 5 precedent) and it is stated for visibility, not as a gap. (`S3-FR9-ruling.md`.)
15. **P3 as a class — "baseline patterns police review prose".** The T-045-35 ruling closes
    the slug-in-identifier sub-class permanently but states plainly that no option closes P3
    as a class: its structural fix is a policy decision about where review prose lives and
    what the scanner reads, which is not Arm B material.

### Pre-approved intake

None. Every residual above is new to this release and carries no prior operator ruling; the
operator-ratified deferrals taken *during* this release (AS-1 … AS-5) were consumed by the
release itself rather than deferred out of it.

### Operator-only action items (not backlog)

- **T-045-03 — wire the verdict-gate required check on both PR edges.** Scheduled as an
  `[operator]` task in W0, still `[ ]`. Due before any `rc-2` PR (D-7); no `rc-2` exists yet.

## The `rc` ledger

| `rc` | Scope | What was found on `develop` | By whom | Fix | Status |
|---|---|---|---|---|---|
| `rc-1` | **The whole scope** — S1 … S4, every FR1–FR16 | — | — | — | **PR pending the operator's push.** All three verdicts APPROVE `395bfb35`; the branch is gate-green and the push-gate defect that blocked the first attempt is fixed and replayed clean |
| `rc-2 … rc-N` | adjustment rounds | **Zero rounds so far** | — | — | Not opened — `develop` cannot be exercised before the push, and the push is an external action the agent fleet cannot take |

**How this release's lane collapses.** D8 defines `rc-1` as the first and only integration of
the whole scope, and the final `rc` as the one that carries memory → CLOSURE → archive and
ships. Because zero adjustment rounds have been possible, **the memory window (T-045-37), this
`CLOSURE.md` (T-045-38), the archive move (T-045-39) and the version bump (T-045-40) collapse
into `rc-1`, which is therefore the final `rc`** — exactly the case D8 anticipated ("if
nothing is found, the final `rc` **is** `rc-1`").

**What re-opens the lane.** Any finding on this release's scope discovered after the push
opens **`rc-2` on `feature/0.4.5`**: fixed on the branch, QA-closed, delta-reviewed and merged
by its own PR, with a row added to this table naming the finding, who found it, and its fix.
**No new backlog ever enters an `rc`** (A16.7/R-7) — a demand outside this scope is recorded
for the PM's intake, never worked in a round. Every `rc` must hold A16.1–A16.6.

**Pre-`rc-1` work already burned on the branch, for the record.** The definition PR
(milestone (a), T-045-02) advanced `develop` and burned **no** `rc`. The four segment closes
(`S1` … `S4`) were qa-gated commits on the branch, no merge and no `rc`. One security verdict
was **REJECTED** at `5a8810ac` before the push-gate defect was understood; it was superseded by
the APPROVED verdict at `395bfb35` after the architect ruling and fix — recorded because a
rejected verdict is part of the honest trail, not something the final APPROVE erases.

## Architecture rulings

### AR-1 — the atomic-write primitive's home (T-045-11, `d1ba453c`)

Reproduced **verbatim** from `reviews/S2-AR1-ruling.md`, per SPEC §5's closure obligation.

> ## Verdict
>
> **UPHOLD D5.** `core/atomic_write.py` is the correct and only legal home.
> **Hooks duplicate required: NO** — the D5 fallback is not taken.
>
> ---
>
> ## Adjudication 1 — the no-cross-feature rule vs. the core file-I/O ratchet
>
> **The consumer set spans three layers.** The eleven writers FR2 consolidates live in
> `features/` (`features/migrate/frontmatter_keys.py:125`, `features/specs/doctor_structural.py:481`,
> `features/spec_context/session_identity.py:112`, `features/spec_context/presence.py:95`,
> `features/migrate/state_v2.py`, two inline in `features/import_/service.py`), in
> `infrastructure/` (`infrastructure/public_assets_common.py:119`,
> `infrastructure/json_agent_model_policy_store.py:236,239`), and in `hooks/`
> (`hooks/_common.py:231`). The import-boundary contracts in `setup.cfg` rule out every
> non-`core` home:
>
> - `features-no-cross-feature` (`setup.cfg:174`, independence contract) — a feature-hosted
>   home would add forbidden sibling edges from every other consuming feature.
> - `features-no-infrastructure` (`setup.cfg:49`) — an infrastructure-hosted home would add
>   new `features → infrastructure` edges to a capped, ratchet-down ignore list
>   (`setup.cfg:22–29`; pinned in `tests/contract/test_import_linter_ignore_cap.py`).
> - `infrastructure-no-upper-layers` (`setup.cfg:137`) — a feature- or hook-hosted home is
>   unreachable from the two infrastructure consumers.
> - `core-no-upper-layers` (`setup.cfg:126`) — `core` is the bottom layer; every consumer
>   (`features`, `infrastructure`, `cli`, `hooks`) holds a legal downward edge to it.
>
> `core/` is the unique intersection. This is byte-for-byte the `core/specs_repair`
> precedent: its docstring (`dadaia_workspace/core/specs_repair.py:5–12`) states it exists
> so "BOTH repair surfaces … share one home without a forbidden sibling edge. Layering: a
> pure `core` leaf — stdlib only, no upward import." D5 quotes that precedent accurately —
> **architecture-fidelity gate: PASS.**
>
> **The ratchet is not re-opened — it is exercised as designed.** The ratchet
> (`tests/contract/test_core_file_io_purity.py`, architect ruling A9: *GUARD, not
> relocation*) exists to stop file I/O drifting into `core/` **by accident**; its own
> failure message (`test_core_file_io_purity.py:114–116`) prescribes the deliberate path:
> add the stem to `_AUTHORIZED_STEMS` **and** record the architecture rationale. The
> "shared-mutable-helper hole" the ratchet guards is stateful convenience helpers hiding
> coupling; `atomic_write` is a stateless, parameterized, stdlib-pure function with no
> module-level mutable state — no hidden coupling channel exists.
>
> **The bug history settles the duplication question.** The v0.4.4-era reading — "a shared
> helper lives inside each feature" — is precisely what produced eleven hand-kept copies
> that **diverged**: per the bug record (`specs/bugs/bugs.jsonl`, `reported`
> 2026-08-24T04:34:58Z), 6 of 8 named writers cleaned their temp file on injected
> `os.replace` failure and 2 (`hooks/_common.py:atomic_write_text`,
> `infrastructure/public_assets_common.py:_atomic_write_text`) leaked it forever. Divergent
> copies of a correctness-critical primitive are the structural cause; per-site patching of
> the two leakers would have been a symptom patch (refused in D4, correctly). FR2 is
> deletion-shaped (11 → 1, net-negative LOC per A2.6). **Root-cause gate: PASS.**
>
> ## Adjudication 2 — the hooks-never-import-container latency law
>
> **The law** (`specs/memory/architecture.md:80–86`): hooks are *sanctioned direct
> importers* of `core` — "no hook imports `container`", pinned by an attesting
> import-surface test; the 2.25s → 0.46s hook-load win came from cutting the
> composition-root graph, not from banning `core` edges.
>
> **Current posture of the call site.** `hooks/_common.py:27–28` already imports
> `dadaia_workspace.core.platform` and `dadaia_workspace.core.session_env`. Their
> transitive closure is pure stdlib (`platform.py`: `sys`, `tempfile`, `dataclasses`,
> `pathlib`; `session_env.py`: `os`, `re`), and `core/__init__.py` carries zero imports,
> so a `core` submodule import drags in nothing else. The hooks → core edge is already
> paid on every gated tool call.
>
> **Consequence.** Importing a stdlib-pure `core/atomic_write.py` adds one leaf module to
> an already-warm import path — zero container, zero features, zero infrastructure,
> guaranteed transitively by `core-no-upper-layers` (`setup.cfg:126`) under `lint-imports`.
> The latency posture is preserved by construction. **No sanctioned import-light duplicate
> in `hooks/_common` is required**; taking the fallback would recreate exactly the
> two-divergent-copies shape the superseded bug documents, inside the very file that
> carried one of the leakers.
>
> ## Conditions binding T-045-12 (and T-045-13/14)
>
> 1. **Stdlib-pure, zero package-internal imports.** `core/atomic_write.py` imports only
>    the stdlib (`os`, `uuid`/`tempfile`, `pathlib`, `typing`) — no `dadaia_workspace.*`
>    import, not even a `core` sibling. This is the fact Adjudication 2 rests on; a later
>    internal import invalidates this ruling and must return to AR review.
> 2. **Stateless.** No module-level mutable state, no config global, no caching.
> 3. **Ratchet declaration.** Add stem `atomic_write` to `_AUTHORIZED_STEMS` in
>    `tests/contract/test_core_file_io_purity.py` with an inline rationale citing this
>    ruling (A2.5: "exactly one entry, with its rationale on the entry"). The matching
>    `specs/memory/architecture.md` "Core file-I/O authorized set" update (line 259 set)
>    is MEMORY-class and lands via `product-engineer` at CLOSURE, citing AR-1.
> 4. **No new accepted edge.** `lint-imports --config setup.cfg --no-cache` green with the
>    ignore-edge cap unchanged (A2.5); all 11 consumer switches are plain downward
>    `→ core` edges needing zero `ignore_imports`.
> 5. **Temp cleanup on every failure path, every parameter combination** (A2.3), battery
>    re-pointed **before** any writer is deleted (D7 expand → switch → contract).
> 6. **No lingering aliases.** The contract step deletes all eight named writers including
>    `hooks/_common.atomic_write_text` — no re-export shim that lets the old names survive;
>    A2.2's scan-derived census is the proof.
>
> ## Bug-surface axis (FR24)
>
> **Reduced.** Eleven divergent implementations of one correctness contract collapse to
> one; the temp-leak class (`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`,
> superseded 2026-08-25T01:47:10Z) becomes structurally impossible rather than
> per-site-patched, and the A2.2 census blocks regrowth. Evidence: the 6-vs-2 behavioral
> divergence recorded in the bug's `symptom` field is exactly the failure mode a single
> primitive cannot exhibit.
>
> ## Gate record
>
> | Gate | Verdict |
> |---|---|
> | Root-cause gate | **PASS** — FR2 fixes the divergence class, not the two leak sites |
> | Architecture-fidelity gate | **PASS** — D5's layer claims match `setup.cfg` contracts and the `specs_repair` precedent verbatim |

**All six binding conditions were independently verified as met** — by qa-engineer at the S2
close (§1/§2) and again by the code reviewer on the code itself (§8): no `dadaia_workspace.*`
import, no module-level mutable state, the ratchet stem declared with an AR-1-citing
rationale, `lint-imports` 9/9 with the cap unchanged, the battery landed before any deletion,
and no surviving alias. **A2.1's fallback clause is therefore not exercised: no sanctioned
import-light duplicate exists, and none is required.**

### FR9 ruling — the registry slug-ownership healing lane (T-045-22, `4f890913`)

**(a) IMPLEMENT — report-only.** One check, `INV-6`, inside the existing `DoctorService.check()`
lane, reading the registry once and reporting every `repos/<slug>` owned by more than one
context, `fixable=False`. No `--fix` branch, no new doctor surface, no change to `dead()`,
`create`, `add_repo` or the migration. Healing was refused because it requires a disposition
policy — which of two owners loses the slug — and any automatic choice is the
"check on the destructive side of a broken invariant" shape a prior firing already rejected.
**A9.2 is satisfied explicitly: the F-1/F-12 class has no remaining undecided lane** — the two
write seams are guarded by construction and lane 3 (historical/migrated state) is now surfaced.
AS-4's alternative arm (a one-paragraph recorded rule-out) was **not** taken; the implement arm
was, and both were admissible.

### T-045-35 ruling — the foreign-slug layer matches whole tokens (`7de4783f`)

The push gate's registry-derived slug layer anchored each slug with `\b`, which treats `-` and
`.` as delimiters — so a hyphenated slug matched **inside** longer identifiers. At the rc-1
push it flagged the library's own tracked asset basename and one of its own append-only ledger
bug ids: neither a private name, both immutable identifiers. Option 1 was selected — replace
the `\b` anchor with a lookaround bounding the match to true token edges, one predicate, no
branch, no allowlist, no carve-out; both consumers inherit it by construction. The
false-negative trade (`<slug>-x`, `<slug>.ext`) is explicit and compensated: the operator
denylist layer is a case-insensitive **substring** match and is untouched, so a genuinely
private term still fires wherever it appears. **`--no-verify` was refused** — this gate *is*
the publication boundary, and a three-line fix on the live feature branch is not an emergency.

### The three FR23 firings

| # | Task | Verdict | Outcome |
|---|---|---|---|
| 1 | T-045-07 (+17) | **SOUND** | The added lines *are* the missing parse-and-bound seam the bug-history chain proves absent; the under-structured half-seam was deleted, not wrapped. Precedent recorded: a net-positive bug fix is sound when the addition is the missing structure, the superseded seam is deleted, and the floor below it is test-proven to leave the defect live |
| 2 | T-045-19 (+52) | **SOUND-WITH-AMENDMENT** | AM-1 deleted the CLI's duplicate redaction pass; AM-2 replaced an 11-field hand-kept kwarg list with iteration over the schema mirror. Both applied at `0cb08157` (net +14) **before** the marker flipped. Precedent: when a fix closes the class the bug names but leaves the older half-seam beside it, the ruling is amendment-by-deletion, never acceptance as-is |
| 3 | T-045-26 (+59) | **SOUND-WITH-AMENDMENT** | AM-1 curated the twin catalog writer and extended the F-84 contract to pin **both written** outputs; AM-2 cut 27 lines of prose. Both applied at `d85dfc19` (net +16) before the flip. Precedent: a curation policy applied to a persisted artifact must be applied by every writer of it and pinned by the contract that binds them |

**One firing that should have fired and did not** (code review F2, MEDIUM): T-045-20's
`resolved` event labelled a `+46/−5` commit `net-neutral`, and the label is what kept it out of
the firing queue — the one place F1 was most likely to have been caught before commit. The
append-only ledger was corrected **forward** at the F1 rework, with the new event naming the
prior mislabel explicitly; no history was rewritten.

## Standing-order verdict record

Every review verdict in this release stated the bug-surface direction of the feature it
touched, with ledger evidence, rather than "tests green".

- **12 of 13 touched surfaces reduced or held** their bug surface at the release review; the
  one surface that briefly *increased* (`core/models/bugs.py::redact_text`, opened by FR7's
  landing) is **reduced** again after the F1 rework — narrower than its pre-FR7 state on the
  classes it exists to close, without the whitespace-loss lane it had opened. The push-gate
  chokepoint surface moved from *unchanged-by-design* to **reduced** at `395bfb35`.
- **Five recurrence chains are now structurally unrepresentable** rather than patched per
  instance: privacy-leak-into-committed-material (the write-time seam now sees the push
  denylist), the hand-kept-field-list class (the scrub set is derived from the schema, so
  there is no list left to forget), the `.dadaia/` duplicate-allowlist class (two hand-kept
  lists collapsed into one canonical set, identity-asserted), atomic-writer divergence (13
  copies → 1, with an AST census that makes a 14th fail loud), and the slug-in-identifier
  push-gate false positive (one predicate, no allowlist).
- **The one place this release added surface** (F1) was found by review, registered as its own
  HIGH bug in an isolated ledger commit *before* the fix, and closed with a RED-then-GREEN
  narrowing that made the function smaller than the reviewer first found it.

## The restated git-identity standing question

**Restated for the operator, not decided here.** Should the git commit identity used in this
workspace be de-personalised going forward? Both v0.12.0 security reviews dispositioned the
existing identity as pre-existing published metadata — not a leak, an operator policy call.
v0.4.3 restated it in its own closure rather than deciding it; v0.4.4 did the same; v0.4.5
does the same. It remains open until the operator rules.

## Artifact GC sweep

**Mandatory** (FR25/A25.1). Run after the `## Validations` and `## Dispositions` evidence
pointers above were final. Lane guard (AG.1, verbatim): resolve the target, refuse any
resolved target outside `.dadaia/`, never follow a symlinked directory. Nothing referenced by
a surviving row above appears in the deleted column.

| Artifact class | Kept (still referenced) | Deleted/archived | Evidence |
|----------------|--------------------------|-------------------|----------|
| `.dadaia/handoff/dadaia-workspace/*.handoff.json` (this release) | `7` — the definition verdict, the SPEC security fold, the FR23 Firing 1 ruling, the rc-1 security verdict, the two qa release verdicts, and the approved rc-1 security verdict | `0` remaining to delete — this release's coordination handoffs were deleted **at consume** by ack-on-consume as they were read; this sweep found none left unreferenced | this document's `## Validations` and `## Dispositions` rows |
| `.dadaia/reports/dadaia-workspace/**` (this release) | `0` | `0` | The release ran handoff-only end to end; no HTML report was requested or authored |
| `.dadaia/tmp/<agent>/{20260825,20260826,20260827}/**` (this release's captures) | `48` — software-engineer 7 + 20 + 1, ai-engineer 16, qa-engineer 3, claude-code 1 | `0` | **Every capture is an evidence pointer** in `## Validations`, `## Size accounting`, a segment QA close or an architect ruling. The SPEC's measurement rule makes them the only proof that this release's numbers were measured rather than estimated, so they are retained with the archived release |
| `.dadaia/tmp/claude-code/20260826/**`, `.dadaia/tmp/software-engineer/20260827/T-050-03-*` | out of scope | out of scope | Companion-release definition artifacts produced on this branch; **another release's artifacts are never swept here** |
| In-repo artifacts (`specs/releases/v0.4.5/{reviews,verdicts}/**`) | `13` review documents + `4` verdict handoffs | `0` | Outside `.dadaia/`, therefore outside this sweep's lane by the guard above; they archive with the release directory |

**Nothing was deleted by this sweep.** The keep/delete rule says to keep anything a surviving
evidence pointer references and, when in doubt, keep — and this release's artifacts are, without
exception, referenced.

## Archive decision

**MOVE** — `specs/releases/v0.4.5/` moves to `specs/_archive/releases/v0.4.5/` via `git mv`
(T-045-39, dispatcher-executed), and `ACTIVE.md` advances to `phase: ARCHIVED` before being
repointed at the next release or `release: none`. Steps T-045-37 … 39 ride **one** commit, in
the order memory → CLOSURE → sweep → archive.

**Standing note (CLOSURE-CHECKS §2):** capture the `SPEC-DOC-031` count **after** that archive
move, never before. This closure's own archived `## Dispositions` rows add one WARN per
non-terminal `ACTIVE` slug they name; all 14 backlog rows are terminal once the PM's sweep
lands, so the expected delta is zero.
