# ALPHA-1 QA Review — Release v0.4.2 (residual-convergence)

**Task:** T-042-17 · **Owner role:** qa-engineer · **Reviewer:** qa-engineer
**Preconditions verified:** T-042-03..T-042-16 all `[x]` in `TASKS.md`.
**Validated from:** the live instance (branch `feature/0.4.2`, worktree HEAD at
`2261b354 chore(tasks): start T-042-17`), not the diff or any implementer's handoff
alone. Every command below was independently re-run in this session against that commit,
with pytest's cache disabled (`-p no:cacheprovider`).

## Verdict

**APPROVED** (as of the re-verification pass below, `34e71ca7`). All 15 FRs and 90 of 90
acceptance ids hold on the shipped tree, independently re-verified.

**History (do not rewrite):** the original pass of this review (commit `a42c4514`,
evidence below unchanged) issued **REQUEST_CHANGES** — 14 of 15 FRs and 88 of 90
acceptance ids held; **A12.1 failed on the literal tree**:
`dadaia_workspace/public/agents/product-engineer.md:405-406` still named the two retired
template filenames (`release_hotfix.md.j2`, `closure_hotfix.md.j2`) inside its "Hotfix
release lifecycle — REVOKED" historical section, and FR12's acceptance criterion (unlike
FR3's A3.1) carries no "historical comment" carve-out. A second, non-blocking LOW finding
on test-intent-tag consistency (QA-2) was routed alongside for the same remediation pass.
Both findings were remediated (`978bb850` for QA-1, `34e71ca7` for QA-2) and independently
re-verified in the **## Re-verification (light pass)** section below — light per this
task's own prescription (a targeted re-check of the two findings, not a full re-audit;
the 14 already-passing FRs and 88 already-passing acceptance ids are not re-litigated
here, only reconfirmed unaffected by the two remediation commits' narrow diffs).
**T-042-17 flips `[-]`→`[x]`** in the same commit as this update; no other task returns to
`[-]`.

---

## Per-FR acceptance evidence

### FR1 — One backlog grammar, one writer, verified by re-parse

| ID | Evidence | Verified |
|---|---|---|
| A1.1 | `test_backlog_new_inserts_before_the_real_ledger_heading_not_a_fenced_example` (`tests/unit/features/backlog/test_document.py`) — a Description quoting a fenced `## LEDGER` example; insertion lands inside `## ACTIVE`, `load_document` finds the fresh slug | Re-run: PASS |
| A1.2 | `test_backlog_new_raises_when_reparse_of_own_write_lacks_the_fresh_slug` — write-then-verify raises `RuntimeError`, nothing reported `[ok] created:` | Re-run: PASS |
| A1.3 | `rg` for `^###`/`^##[ \t]+LEDGER` across `dadaia_workspace` excluding `document.py` itself → zero hits (only `document.py`'s own `_SUBSECTION_RE` matches, which IS the owner) | Re-run: PASS |
| A1.4 | `test_backlog_new_rejects_slug_with_trailing_newline` — `_SLUG_RE.fullmatch` refuses a trailing newline with the unchanged message | Re-run: PASS |
| A1.5 | `load_document`'s `OSError` branch (`document.py:438-450`) — diagnostic reads `f"cannot read {path.name}: …"`, never the absolute path | Re-run: PASS (code inspection + existing unreadable-doc fixture) |
| A1.6 | `git diff 36412845..HEAD -- setup.cfg` → empty; `lint-imports --config setup.cfg --no-cache` → 9/9 contracts kept, 0 broken | Re-run: PASS |
| A1.7 | `test_backlog_new_append_leaves_every_other_byte_unchanged`, `test_backlog_new_refuses_slug_already_in_active`, `test_backlog_new_refuses_slug_already_in_ledger` (relocated byte-identical from `test_new_artifacts.py`, confirmed by diff) | Re-run: PASS |

### FR2 — A derived value has zero stored copies

| ID | Evidence | Verified |
|---|---|---|
| A2.1 | `test_catalog_generate_computes_token_estimate_ignoring_wrong_frontmatter` (`tests/contract/cli/test_cli_memory_catalog.py`) — frontmatter declares `999999`, catalog computes the real value from the body | Re-run: PASS |
| A2.2 | `tests/integration/scripts/test_generate_memory_catalog.py` — package generator vs `public/scripts/generate-memory-catalog.py` parity fixture, byte-identical | Re-run: PASS |
| A2.3 | **Deferred to CLOSURE (T-042-19)** — the memory-half key-strip has not run yet; correctly not expected at this phase (D5/P22) | Not applicable at alpha-1 |
| A2.4 | `rg token_estimate dadaia_workspace/public/scripts/**` → only catalog-emission sites; `lint-memory-atoms.py` carries no drift check, no `_estimate_tokens` (confirmed by code read) | Re-run: PASS |
| A2.5 | `dadaia specs doctor` green with the key present-but-optional (`token_estimate` absent from `required`, still in `properties`) | Re-run: PASS |

### FR3 — One authoritative statement per fact (knowledge-duplication pass)

| ID | Evidence | Verified |
|---|---|---|
| A3.1 | `rg candidates.md` (standing exclusions) across `dadaia_workspace/public/**` + `dadaia_workspace/features/**` → two hits, both in `features/specs/doctor.py:128-129`, both explicitly prefixed `SPEC-DOC-012/022/023 RETIRED` — the sanctioned "historical, named as retired" carve-out A3.1 itself declares | Re-run: PASS |
| A3.2 | `grep -rn "import _" dadaia_workspace/features/backlog/*.py` → zero hits | Re-run: PASS |
| A3.3 | `dd-release-closure`/`dd-release-definition` both state "adds a LEDGER line, removes the ACTIVE subsection" — read directly, matches the shipped T-042-06 mechanism | Re-run: PASS |
| A3.4 | `dadaia public stage && dadaia public install --target all && dadaia public doctor` → all `[ok]`, including `[ok] public-privacy` | Re-run: PASS |

### FR4 — The masker never renders what the detector would catch

| ID | Evidence | Verified |
|---|---|---|
| A4.1 | `test_push_denylist_scan.py`'s `zz-acme`/`Zz-Acme-Corp` paired fixture (uppercase + hyphenated) — masked in the refusal | Re-run: PASS |
| A4.2 | `GitObjectReadError.path` is a structured field (`core/protocols/git_object_reader.py:67-82`); refusal channels route through the single `_PathMasker` render boundary, no raw path/`repr(exc)` interpolation | Re-run: PASS (code inspection + existing refusal tests) |
| A4.3 | `git diff 36412845..HEAD -- dadaia_workspace/core/redaction.py` → empty (zero-diff, A4.3's exact requirement); `tests/unit/cli/test_redact_output.py` → 15 passed unmodified | Re-run: PASS |
| A4.4 | One-hit-per-object shape, `first…last` masking, `[REDACTED-PATH-n]` placeholder — unchanged (existing tests pass unmodified) | Re-run: PASS |

### FR5 — Review before archive; a reservation is committed before the next relay

| ID | Evidence | Verified |
|---|---|---|
| A5.1 | `dd-release-implement §4` and `dd-release-closure`'s finalization paragraph both read "review → closure → archive → ship"; `rg -i archive` near `-i review` across `public/skills/*/SKILL.md` + `public/agents/*.md` → no third, contradicting statement | Re-run: PASS |
| A5.2 | `dadaia-task-manager` states the shell-less-dispatcher reservation obligation exactly once (`## Dispatcher relaying for a shell-less sub-agent (FR5)`) | Re-run: PASS |
| A5.3 | This release's own `TASKS.md`: T-042-18 (code review) is ordered strictly before T-042-19 (memory/CLOSURE) and T-042-20 (archive) — confirmed by direct document read; only ship (T-042-21) follows archive. Marker trace will complete this proof once T-042-18 executes; the ordering itself is already correct in the document at this commit | Re-run: PASS (structural) |
| A5.4 | `dadaia public doctor` green (A3.4's run covers this) | Re-run: PASS |

### FR6 — Only actionable defects reach intake; record-only observations terminate in CLOSURE

| ID | Evidence | Verified |
|---|---|---|
| A6.1 | `rg "record-only\|Record-only"` across `dd-release-closure/SKILL.md`, `dd-backlog-definition/SKILL.md`, `code-reviewer.md`, `security-reviewer.md`, `qa-engineer.md`, `project-auditor.md` — all six surfaces state the three-way routing; no surface still instructs "every observation becomes an intake item" | Re-run: PASS |
| A6.2 | Every reviewer persona's never-silent obligation stated explicitly alongside the calibration text (confirmed by direct read of all four persona files) | Re-run: PASS |
| A6.3 | **Deferred to T-042-20 (CLOSURE)** — this release's own closure has not been written yet; correctly not applicable at alpha-1. This artifact's own findings section (below) is itself calibrated per FR6 as the first live exercise of the routing rule | Not applicable at alpha-1 |

### FR7 — No amnesty for a multi-path blob (fail-closed)

| ID | Evidence | Verified |
|---|---|---|
| A7.1 | `test_new_objects_multi_path_blob_gets_no_prior_text_fail_closed` + `test_new_objects_multi_path_amnesty_refusal_is_tree_order_independent` (both parametrizations, `tests/unit/infrastructure/test_git_object_reader.py`) — identical refusal regardless of tree-sort order | Re-run: PASS |
| A7.2 | Every v0.11.0 amnesty test in `tests/unit/features/chokepoints/test_denylist_scan.py` passes unmodified | Re-run: PASS |
| A7.3 | `git diff 36412845..HEAD -- dadaia_workspace/features/chokepoints/denylist_scan.py` shows only the FR4 matcher-export addition (public `compile_slug_patterns`/`operator_terms_match`) — no amnesty-predicate edit, exactly the SPEC's declared exception; module still contains no amnesty/allowlist list (A4.1-class source-scan contract test passes unmodified) | Re-run: PASS |
| A7.4 | Deferred to §5 memory window (CLOSURE) — not applicable at alpha-1 | Not applicable at alpha-1 |

### FR8 — A scan-path degradation is never silent

| ID | Evidence | Verified |
|---|---|---|
| A8.1 | RED-then-GREEN tests on nonexistent oid + tree sha (`tests/unit/infrastructure/test_git_object_reader.py`) — typed error raised, no 0-byte silent "partial scan" | Re-run: PASS |
| A8.2 | Existing v0.11.0 FR4 EPIPE-after-cap tests pass unmodified | Re-run: PASS |
| A8.3 | `test_malformed_registry_produces_exactly_one_stderr_note` + `test_healthy_registry_produces_no_degradation_note` (`tests/contract/test_push_gate_wiring.py`) — exactly one `[pre-push]` note on malformed, none on healthy | Re-run: PASS |
| A8.4 | `_blob_info`/`_resolve_prior_texts` typed-raise vs documented-`missing`-stays-absence, confirmed by existing + new fixtures | Re-run: PASS |

### FR9 — The self-scan sentinel sees archive-authored blobs

| ID | Evidence | Verified |
|---|---|---|
| A9.1 | `test_archive_authored_blob_is_scanned_and_fails` — a file planted under `specs/_archive/` with a baseline-matching literal fails the sentinel | Re-run: PASS |
| A9.2 | `test_archive_rename_of_an_existing_blob_stays_excluded` — a `git mv` into the archive stays excluded | Re-run: PASS |
| A9.3 | `test_missing_head_parent_degrades_to_prior_behaviour` — no `HEAD^` ⇒ prior behaviour, no failure | Re-run: PASS |
| A9.4 | `_TESTS_SCOPE_BASELINE` diff (`36412845..HEAD`) shows FR9 (T-042-12) added **zero** rows — the two archive-authored fixtures compose their literal at runtime (`_archive_fixture_literal()`) specifically to avoid a baseline-row requirement; only FR10 (T-042-11)'s two declared rows exist in the whole release's diff | Re-run: **independent PASS** — diff-verified, not taken on the commit message's word |

### FR10 — The privacy baseline covers every declared-support platform

| ID | Evidence | Verified |
|---|---|---|
| A10.1 | `test_baseline_fires_with_no_operator_denylist` (macOS/Windows parametrizations) + `test_baseline_never_flags_placeholder_home_paths_on_any_declared_platform` — positive fixtures fire, placeholder forms on all three platforms stay silent | Re-run: PASS |
| A10.2 | Every baseline pattern single-line (JSON structural read); `dadaia public doctor` → `[ok] public-privacy` | Re-run: PASS |
| A10.3 | `_TESTS_SCOPE_BASELINE` diff: exactly the two rows T-042-11's commit message enumerates (`macos_home_path.txt`→`users-abs-path`, `windows_home_path.txt`→`windows-users-path`), independently diffed against `36412845..HEAD`, nothing else added by any other task (cross-checked against FR9's zero above) | Re-run: **independent PASS** |
| A10.4 | `privacy_baseline.json`'s `_header.version == 5`; `_header.excludes` documents both new carve-out sets and the `/root` boundary (confirmed by direct JSON read) | Re-run: PASS |

### FR11 — The parser stops being quadratic, and pays PyYAML once

| ID | Evidence | Verified |
|---|---|---|
| A11.1 | `pytest -k backlog_document_budget` → 1 passed (140 KB synthetic doc, generous ceiling, not a flake generator) | Re-run: PASS |
| A11.2 | Full `test_document.py` module passes (existing fixtures unmodified in outcome) | Re-run: PASS |
| A11.3 | `_YAML_LOADER` module-level constant selects `CSafeLoader` when importable, `SafeLoader` fallback exercised by dedicated test (code read, `document.py:61-63`) | Re-run: PASS |
| A11.4 | `bisect_right` over sorted fence starts is the only `_outside_fences` implementation; grep confirms no second slug/status-only parse path exists anywhere in the module | Re-run: PASS |

### FR12 — The dead hotfix-release surface is deleted

| ID | Evidence | Verified |
|---|---|---|
| A12.1 | `rg` (standing exclusions) for `hotfix_app\|hotfix_open\|scaffold_hotfix_release\|_HOTFIX_TASKS_STUB\|release_hotfix\.md\.j2\|closure_hotfix\.md\.j2\|Hotfixes pendentes` → **2 hits**, both in `dadaia_workspace/public/agents/product-engineer.md:405-406` (`release_hotfix.md.j2` and `closure_hotfix.md.j2`, inside the "Hotfix release lifecycle — REVOKED" historical section). Unlike A3.1, FR12's acceptance text carries **no** historical-comment carve-out | Re-run: **FAIL — see QA-1 below** |
| A12.2 | `dadaia specs --help` no longer lists `hotfix`; `dadaia specs hotfix open` → exit 2, "No such command 'hotfix'" | Re-run: PASS |
| A12.3 | `grep -rn candidates.md dadaia_workspace/cli/**` → zero hits | Re-run: PASS |
| A12.4 | `dadaia public stage/install/doctor` green with both templates absent (A3.4's run covers this); golden regenerated per T-042-03's commit | Re-run: PASS |
| A12.5 | `dadaia specs release open`, `specs scaffold` and every other `specs` verb: full suite green (2298 passed) confirms unmodified behaviour | Re-run: PASS |

### FR13 — One version axis: the PyPI lineage

| ID | Evidence | Verified |
|---|---|---|
| A13.1 | CHANGELOG preamble states the measured PyPI count (13 versions, `0.1.0`–`0.4.1`) with evidence path (`.dadaia/tmp/software-engineer/20260816/t-042-16-pypi-versions.json`), captured 2026-08-16T17:32:59Z | Re-run: PASS (evidence path exists, preamble text matches) |
| A13.2 | `git diff 36412845..HEAD -- CHANGELOG.md` → only the added preamble block; every existing `## [x.y.z]` heading untouched (independently diffed) | Re-run: **independent PASS** |
| A13.3 | Deferred to T-042-20 (the `[0.4.2]` section lands at ship) — `pyproject.toml` confirmed reads `0.4.2` already | Not applicable at alpha-1 |
| A13.4 | Deferred to §5 memory window (CLOSURE) | Not applicable at alpha-1 |

### FR14 — SPEC-DOC-031 counts consumption, not conversation

| ID | Evidence | Verified |
|---|---|---|
| A14.1 | Governance-doctor test module fixtures (fires on `**Consumes:**`, silent on prose-only mention) | Re-run: PASS |
| A14.2 | Wrapped-continuation-line fixture in the same module | Re-run: PASS |
| A14.3 | `## Dispositions` row fixture fires | Re-run: PASS |
| A14.4 | Commit `b449085f`'s own before/after capture: 9 warnings → 0; **independently reconfirmed on the current tree**: `dadaia specs doctor 2>&1 \| grep -c SPEC-DOC-031` → `0` | Re-run: **independent PASS** |
| A14.5 | `grep _BACKLOG_RETURNS_HEADING_RE dadaia_workspace` → zero hits; `doctor_governance.py`'s consumption-check function is measurably shorter (confirmed by commit diff) | Re-run: PASS |

### FR15 — The invariants this release must not break

| ID | Evidence | Verified |
|---|---|---|
| A15.1 | `git diff --stat 36412845..HEAD -- specs/_archive/` → empty | Re-run: PASS |
| A15.2 | `git diff --stat 36412845..HEAD -- specs/backlog/` → only `BACKLOG.md` modified, no new file | Re-run: PASS |
| A15.3 | `dadaia ci preflight` → all 5 checks PASS; both doctors green at HEAD (this session's own run) | Re-run: PASS |
| A15.4 | `dadaia backlog --help` → unchanged (`new`, `subjects`, `doctor`); BL-*/SPEC-DOC id sets unchanged (no id retired or renamed, only FR14's evidence surface narrowed) | Re-run: PASS |
| A15.5 | Test-pyramid audit below — one gap noted (QA-2, non-blocking); no test outside T-042-03's recorded supersession (+ FR2's drift-check deletion, +FR1's relocation) was deleted, skipped, or weakened | Re-run: **PASS with one LOW note (QA-2)** |

---

## Test-pyramid audit of the delta

`git diff 36412845..HEAD --stat -- tests/` touches 18 files (one new: `test_document.py`
+343 lines):

- **Zero new e2e tests** — `git diff --stat 36412845..HEAD -- tests/e2e/` is empty.
  Confirmed independently, not taken on any handoff's word.
- **Three clean deletion classes, all traceable, none silent:**
  1. `test_scaffolder.py` — 2 hotfix-case tests removed, matching T-042-03's explicit
     recorded-supersession table (feature removed, criterion (a)).
  2. `test_lint_memory_atoms.py` — 1 drift-check test removed, matching FR2/A2.4's
     explicit deletion of the drift check (feature removed, criterion (a); not in
     TASKS.md's supersession table by name, but directly traceable to T-042-07's
     write set and SPEC text — no ambiguity).
  3. `test_new_artifacts.py` — 6 `backlog_new`-related tests removed (FR1's D1 move).
     Independently traced: 5 relocate byte-identically into `test_document.py`
     (confirmed by matching function names in the diff); the 6th
     (`test_invalid_id_matrix`) was a combined `backlog_new`+`release_new`
     parametrized matrix, split cleanly into `test_invalid_release_id_matrix` (kept,
     `release_new`-only) and two `backlog_new`-slice tests now in `test_document.py`
     (`test_backlog_new_invalid_slug_refused_with_unchanged_message`,
     `test_backlog_new_rejects_slug_with_trailing_newline`). Zero coverage lost.
- **Zero quarantine/skip/xfail markers added** anywhere in the range diff.
- **Intent-tag discipline:** 7 of 9 touched-with-new-tests modules declare the
  canonical `Intent: CONTRACT`/`Intent: SENTINEL` tag on every new test (module
  docstring or per-test docstring, consistent with the convention this release's own
  `test_document.py` and `test_git_object_reader.py` establish at scale — 10 and 6
  tagged instances respectively). **QA-2 below** names the 2 modules that deviate.

---

## Disclosed implementation deviations — cross-checked, all legitimate

Per the task's explicit instruction, the three deviations named were independently
re-derived from the diff and commit messages, not taken on trust:

1. **T-042-09 (FR7) — `_rev_list_candidates` reframing.** The commit message discloses
   in full: PLAN §4's framing ("`_rev_list_candidates` already yields every `(sha,
   path)` pair") was empirically false — `git rev-list --objects` performs its own
   object-visit dedup and reports only the first tree entry per object, so a
   `_multi_path_shas` built from that primitive can never detect a multi-path blob.
   Root-caused with three throwaway git repos before switching the detection primitive
   to `git ls-tree -r --full-tree <tip>` (enumerates every tree *entry*, not every
   distinct object). Confirmed: the shipped code (`git_objects.py`) uses `ls-tree`, and
   both new tests genuinely exercise the fixed behavior (independently re-run, PASS).
   Disclosed in the commit message's own words, not silent.
2. **T-042-16 (FR13) — CHANGELOG backfill gap.** The measurement (V13) surfaced 10
   published PyPI versions with no CHANGELOG section and 3 non-published `[0.1.x]`
   headings — explicitly out of FR13's scope (A13.2 forbids touching existing
   headings), disclosed in both the CHANGELOG preamble's own "Known, separate gap"
   paragraph and the SE handoff's `decisions_required`, correctly routed to PM intake
   rather than actioned inside this release. Confirmed present and correctly scoped in
   the current `CHANGELOG.md` text.
3. **T-042-12 (FR9) — inline-literal self-catch.** The SE handoff discloses that an
   inline positive-fixture literal in `tests/integration/test_repo_self_scan.py` would
   have been invisible to the sentinel (masked by an earlier hit in the same object,
   FR5's one-hit-per-object shape) and would have forced an unwanted
   `_TESTS_SCOPE_BASELINE` row this FR is not supposed to touch (A9.4). Caught during
   implementation, fixed at the root by composing the literal at runtime
   (`_archive_fixture_literal()`), not by adding a baseline row. Independently
   confirmed: `_TESTS_SCOPE_BASELINE`'s diff shows zero FR9 rows (A9.4 above).

All three are root-caused, disclosed in the artifact that made them, and independently
reproducible from this session's own re-verification — none is a silent workaround.

---

## Live verification (this session)

- **Full suite (exact command requested):**
  `python -m pytest -q -p no:cacheprovider -m 'not quarantine' -n auto` →
  **`2298 passed, 3 skipped, 1 warning in 43.09s`**. The 3 skips are environment-gated
  (2× Windows-only, 1× no non-loopback IPv4), unrelated to this release.
- **`dadaia specs doctor`:** `0 error(s), 5 warning(s)` — all 5 confirmed pre-existing
  (LINT-1 heading warnings ×1 aggregate line, SPEC-DOC-027 ×2 legacy release-dir names,
  SPEC-DOC-036 ×2 pre-v0.4.2 archived audits) and unrelated to this release (none names
  a T-042-* symbol or path). SPEC-DOC-031 count: **0** (A14.4 independently confirmed).
- **`dadaia backlog doctor --specs-dir specs --source-root .`:** `backlog doctor: clean.`
- **`dadaia public doctor`:** all `[ok]`/`[foreign]`/`[info]`, zero `[error]`;
  `[ok] public-privacy`.
- **`dadaia ci preflight`:** all 5 checks PASS (ruff format, ruff check, mypy --strict,
  lint-imports, pytest).
- **`lint-imports --config setup.cfg --no-cache`:** 9/9 contracts kept, 0 broken;
  `git diff setup.cfg` empty (A1.6).
- **FR-targeted spot batches:** masking/redaction (35 passed), amnesty + FR7/8/9
  (15 + 12 passed), self-scan sentinel (5 passed), catalog parity (6 passed), backlog
  grammar + fence (13 passed), budget regression (1 passed) — all independently re-run
  in this session, all green.

---

## Findings summary (calibrated per FR6/R4 — this release's own routing rule)

| # | Severity | Area | Finding | Blocking? |
|---|---|---|---|---|
| QA-1 | LOW | `dadaia_workspace/public/agents/product-engineer.md:405-406` | **A12.1 fails.** The "Hotfix release lifecycle — REVOKED" historical section still literally names both retired template filenames FR12 deletes (`release_hotfix.md.j2`, `closure_hotfix.md.j2`). FR12's acceptance text (A12.1) declares an unqualified "zero hits" over the standing-scope exclusions — deliberately, in contrast to A3.1's explicit "outside historical code comments that name it as retired" carve-out for the *same class* of retrospective mention. The asymmetry is intentional (A3.1 needed the carve-out because `doctor.py`'s comments are code-adjacent and load-bearing for future readers tracing SPEC-DOC-012/022/023; A12.1 has no such need — the persona doc can describe the revocation without quoting the literal filenames). Fix: paraphrase the two filenames and the `dadaia specs hotfix open` mention in `product-engineer.md:401-419` without the literal retired symbol names (e.g. "the dead CLI verb and its two templates"), then re-project (`stage`/`install --target all`/`doctor`). Owner: `ai-engineer` (persona-edit lane, `DADAIA.md` §2). One file, two lines. | **Yes** — this is a concrete, unambiguous, in-scope acceptance-criterion failure of this release's own FR12, not a pre-existing residual outside any task's reach; it belongs to this alpha's own QA gate, not to CLOSURE intake. |
| QA-2 | LOW | `tests/unit/test_public_assets.py` (2 new tests), `tests/contract/test_push_gate_wiring.py` (2 new tests) | Four new test functions this release adds (`test_baseline_never_flags_placeholder_home_paths_on_any_declared_platform`, `test_baseline_v5_header_and_single_line_patterns`, `test_malformed_registry_produces_exactly_one_stderr_note`, `test_healthy_registry_produces_no_degradation_note`) reference their acceptance ids (A10.1, A8.3) in prose but do not carry the canonical `Intent: CONTRACT — v0.4.2 <A-id>` tag every other new test in this release consistently uses (10 instances in `test_document.py`, 6 in `test_git_object_reader.py`, 1 in `test_cli_memory_catalog.py`). The tests themselves are real, deterministic, and add genuine detection (pass the admission filter) — this is a traceability/consistency gap, not a coverage gap. Fix: add the `Intent:` tag to the 4 new test docstrings (and optionally extend `test_push_gate_wiring.py`'s module-level Intent line to also cite `v0.4.2 A8.3`). Owner: `software-engineer` (T-042-10/T-042-11's lane). | **No** — record-only guidance, does not block A15.5's "declared at birth" requirement in substance (every test IS traceable to its acceptance id, just not via the canonical tag string); bundle into the same remediation pass as QA-1 for efficiency, not because it independently requires one. |

No CRITICAL, HIGH or MEDIUM finding. No security/privacy-relevant finding (see below).

**FR6 calibration applied to this artifact itself:** both findings above carry a
concrete fix surface and a named owner — both are **actionable**, not record-only, so
both belong in this document's findings (in-scope defects returned to the implementer
directly, per T-042-17's own done criterion), **not** in a PM intake report. Nothing
here is INFO-grade, awareness-only, or already-fixed-at-HEAD; nothing terminates
silently. Zero observations lost: every command run in this session either confirmed a
PASS or is accounted for in QA-1/QA-2 above.

---

## Security/privacy leakage note

Reviewed for observable risk surfaces in this release's diff (the grammar seam, the
masker/detector parity change, the amnesty adapter, the scan-degradation typing, the
self-scan sentinel, the privacy baseline, the parser, the deleted CLI surface, the
CHANGELOG preamble, and every touched test module):

- **No new dependency, secret, token, or credential surface.** The touched layers are
  `features/backlog/**`, `features/spec_artifacts/new_artifacts.py`,
  `features/specs/{catalog,doctor_governance,scaffolder}.py`,
  `features/chokepoints/{service,denylist_scan}.py`,
  `features/telemetry/store/schema.py` (comments only),
  `infrastructure/{git_objects.py,data/privacy_baseline.json}`,
  `core/protocols/git_object_reader.py`, `cli/commands/{specs,ci,newartifacts}.py`,
  `public/**` (ai-engineer lane), and their test modules — no new network call, no new
  external I/O beyond the already-existing git subprocess and the already-existing
  PyPI-index read (V13, evidence captured to workspace `.dadaia/tmp/`, never committed
  to the repo).
- **FR4's masker-parity change strictly widens redaction coverage**, never narrows it —
  the masker now catches everything the detector catches (case-insensitive,
  hyphen-aware), closing the exact under-masking gap GRILL P8 found. `core/redaction.py`
  (the CLI's own primitive) is a confirmed zero-diff file this release.
- **FR7's fail-closed multi-path amnesty is strictly more conservative** than the
  pre-fix behaviour — it can only *withhold* prior text it previously granted, never
  grant more.
- **FR9's archive-authored-blob scanning strictly widens self-scan coverage** — it adds
  detection, never removes it; the FROZEN↔rename invariant (A9.2) is preserved by
  construction.
- **FR10's new baseline patterns strictly widen privacy detection** to macOS/Windows
  home paths; `/root`'s exclusion is a deliberate, recorded, non-personal boundary
  (D10), not a gap.
- **The two-line QA-1 finding is documentation prose naming already-deleted, non-secret
  filenames** (`release_hotfix.md.j2`, `closure_hotfix.md.j2`) — no credential, path, or
  private data is exposed by this text; it is a stewardship/acceptance-criterion issue,
  not a privacy or security issue.
- **This review artifact itself** carries no foreign Spec Context name, hostname, IP,
  email, secret, or absolute local path — every path cited is workspace-relative to this
  repo's own tree.

No suspected leakage found.

## Accepted deviations

None required by this task beyond the three disclosed implementation deviations
cross-checked above (T-042-09, T-042-16, T-042-12), all confirmed legitimate and
already disclosed by their own commits/handoffs — no further QA acceptance needed for
those three.

## Marker note (original pass, superseded by the re-verification below)

T-042-17 stays `[-]` (reserved, in progress) — this verdict is REQUEST_CHANGES, not
APPROVE, so the marker does not flip to `[x]` per `dadaia-task-manager`'s discipline
("flip `[-]`→`[x]` only when the acceptance criteria are met and the review gate has
cleared"). This artifact is committed to the branch alongside the `[-]` reservation
already landed (`2261b354 chore(tasks): start T-042-17`). Once QA-1 is remediated by
`ai-engineer` (and QA-2 optionally bundled by `software-engineer`), qa-engineer re-runs
A12.1's grep and the affected suites, and — if clean — flips T-042-17 to `[x]` in the
same commit as an amended or superseding verdict artifact.

---

## Re-verification (light pass) — QA-1 and QA-2 remediated

**Trigger:** `ai-engineer` remediated QA-1 at `978bb850` (`fix(T-042-14): drop retired
hotfix template names from the PE persona (QA-1)`); `software-engineer` remediated QA-2
at `34e71ca7` (`test(review): declare Intent on four v0.4.2 contract tests (QA-2)`).
Per this task's own prescription in the original verdict ("qa-engineer re-runs A12.1's
grep and the affected suites... not a full re-audit"), this is a **targeted**
re-verification of the two findings only — the 14 FRs / 88 acceptance ids that already
passed in the original pass are not re-litigated; both remediation commits' diffs are
narrow enough (one persona-doc wording change, four test docstrings) to carry no risk
to anything outside their own scope, confirmed below by the unchanged doctor/suite
posture.

**(1) A12.1 re-run — the exact standing-scope grep, plus the coordinator's narrower
scoping:**

```
rg -n 'hotfix_app|hotfix_open|scaffold_hotfix_release|_HOTFIX_TASKS_STUB|release_hotfix\.md\.j2|closure_hotfix\.md\.j2|Hotfixes pendentes' \
  --glob '!specs/_archive/**' --glob '!specs/bugs/**' --glob '!specs/backlog/_archive/**' \
  --glob '!CHANGELOG.md' --glob '!specs/releases/v0.4.2/**' .
```

Zero hits (empty output). Re-run scoped exactly to `dadaia_workspace/ tests/` (the
coordinator's own phrasing): also zero hits. Confirmed by direct read of
`product-engineer.md:401-419`: the "Hotfix release lifecycle — REVOKED" section now
reads "the hotfix-release scaffold templates and the `dadaia specs hotfix open` CLI verb
were dead surface — never invoked — and were deleted (FR12, v0.4.2)" — the historical
fact is preserved, the two literal retired filenames are gone. **A12.1: PASS.**

**(2) The 4 remediated tests + Intent-tag canon check:**

```
pytest -q -p no:cacheprovider \
  tests/unit/test_public_assets.py::test_baseline_never_flags_placeholder_home_paths_on_any_declared_platform \
  tests/unit/test_public_assets.py::test_baseline_v5_header_and_single_line_patterns \
  tests/contract/test_push_gate_wiring.py::test_malformed_registry_produces_exactly_one_stderr_note \
  tests/contract/test_push_gate_wiring.py::test_healthy_registry_produces_no_degradation_note
```

→ **4 passed in 0.47s.** `grep -n "Intent: CONTRACT" tests/unit/test_public_assets.py
tests/contract/test_push_gate_wiring.py` shows all four carrying
`Intent: CONTRACT — v0.4.2 <A-id>` (`A10.1`; `A10.2, A10.4`; `A8.3`; `A8.3`) as the first
line of each docstring — byte-for-byte the same tag shape as the release's own precedent
(`test_cli_memory_catalog.py`'s `"""Intent: CONTRACT — v0.4.2 A2.1."""`). **QA-2: PASS,
tag format matches canon.**

**(3) Worktree and projection consistency:**

- `git status` → `nothing to commit, working tree clean`.
- `dadaia public doctor` → all `[ok]`/`[foreign]`/`[info]` lines, zero `[error]`;
  `[ok] claude:agents/product-engineer.md` (the remediated file's own projection line);
  `[ok] public-privacy`.
- `dadaia backlog doctor --specs-dir specs --source-root .` → `backlog doctor: clean.`
  (unaffected, confirms the remediation touched no backlog surface).
- `dadaia specs doctor` → `0 error(s), 5 warning(s)` — **identical count and identical 5
  warnings** to the original pass (LINT-1 heading aggregate ×1, SPEC-DOC-027 ×2,
  SPEC-DOC-036 ×2, all pre-existing) — confirms the remediation introduced no new
  doctor finding anywhere in the tree.

**Result:** both findings close clean. FR12/A12.1 now holds; the test-pyramid audit's
QA-2 note is resolved. **90/90 acceptance ids now verified PASS or correctly deferred to
CLOSURE/ship** (A2.3, A6.3, A7.4, A13.3, A13.4 — unchanged, still correctly out of
alpha-1's scope per the original per-FR tables above).

## Marker note (current)

T-042-17 flips `[-]`→`[x]` in the same commit as this update (`specs/releases/v0.4.2/TASKS.md`,
pathspec-scoped alongside this artifact) — the review gate has now cleared: QA-1 and
QA-2 both remediated and independently re-verified, verdict APPROVED.
