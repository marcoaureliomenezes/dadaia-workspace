# ALPHA-1 QA Review — Release v0.9.0 (Push-range denylist scan)

**Task:** T-090-10 · **Owner role:** qa-engineer · **Reviewer:** qa-engineer
**Preconditions verified:** T-090-01..09 all `[x]` in `TASKS.md`.
**Validated from:** the live instance (branch `feature/v0.9.0`, worktree HEAD at
`42b59cd8 fix(v0.9.0): scan-clean fixtures + RFC-2606 reserved-TLD email carve-out`,
plus this review's own `0491613a`/`ac805c67` housekeeping commits), not the diff alone.

## Verdict

**APPROVED.** All 36 SPEC acceptance ids (A1.1–A9.4, FR1–FR9) are satisfied with
verified evidence, independently re-run where cheap. Two non-blocking findings are
recorded below (a coverage gap on one A6.2 sub-clause, and an unrelated pre-existing
test-suite flake discovered and registered as a bug during this review). No CRITICAL,
HIGH, or MEDIUM finding. No task returns to `[-]`.

**Note on the dispatch brief's acceptance-id count.** The dispatch brief for this task
said "41 acceptance ids"; a direct count of `SPEC.md`'s `A<n>.<m>` markers gives **36**
(A1: 5, A2: 4, A3: 5, A4: 3, A5: 4, A6: 3, A7: 3, A8: 5, A9: 4). All 36 are enumerated
below; the discrepancy is recorded for traceability, not treated as a missing item.

---

## Per-FR acceptance evidence

### FR1 — Range-scoped denylist scan on pushed branch refs

| ID | Evidence | Verified |
|---|---|---|
| A1.1 | `tests/unit/features/chokepoints/test_push_denylist_scan.py::test_branch_push_with_denylisted_blob_in_range_is_refused` | Re-run: PASS |
| A1.2 | `test_term_outside_the_range_does_not_refuse` (fake object source never surfaces the out-of-range object) | Re-run: PASS |
| A1.3 | `test_deletion_ref_is_never_scanned` (asserts `source.calls == []`) | Re-run: PASS |
| A1.4 | `test_shared_blob_across_two_refs_is_deduped` (same blob sha reachable from two tag refs, one Hit) | Re-run: PASS |
| A1.5 | Module docstring: `Intent: CONTRACT — v0.9.0 A1.1, A1.2, A1.3, A1.4, A2.1, A2.2, A2.3, A2.4, A5.1, A5.2, A5.3, A5.4, A6.1` | Confirmed present |

Object-source range computation (both range forms of FR1's table, the git-object port
itself) is separately covered at `tests/unit/infrastructure/test_git_object_reader.py`
(`Intent: CONTRACT — v0.9.0 A1.1, A1.2, A1.3, A1.4, A6.1, A6.2`) — real `tmp_path` git
repos, both `--not <remote_sha>` and `--not --remotes` forms, a binary blob, a deletion
sha, and a simulated git failure. Re-run: PASS.

### FR2 — Tag pushes are scan-covered (and stay review-exempt)

| ID | Evidence | Verified |
|---|---|---|
| A2.1 | `test_tainted_tag_push_is_refused` | Re-run: PASS |
| A2.2 | `test_clean_tag_push_is_allowed_with_no_verdict_required` (asserts allow with no handoff file present anywhere) | Re-run: PASS |
| A2.3 | `test_deletion_ref_is_never_scanned` (shared with A1.3 — a deletion is unscanned and unverdict-checked) | Re-run: PASS |
| A2.4 | `test_branch_policy_refusal_precedes_the_scan` (a `_FailingObjectSource` would raise if the scan were ever reached; branch-name refusal fires first) | Re-run: PASS |

### FR3 — Term sources, fail-closed, and self-slug exclusion

| ID | Evidence | Verified |
|---|---|---|
| A3.1 | `tests/unit/features/chokepoints/test_denylist_scan.py::test_baseline_ipv4_literal_refused_with_no_operator_terms`, `test_baseline_home_path_refused_with_no_operator_terms` (no operator terms passed, baseline layer alone refuses) | Re-run: PASS |
| A3.2 | `test_own_slug_excluded_from_slugs_never_matches` (own slug never in the `slugs` tuple, never matches even though it appears in every blob) | Re-run: PASS |
| A3.3 | `test_foreign_slug_matches_as_whole_word` / `test_foreign_slug_embedded_in_longer_word_does_not_match` | Re-run: PASS |
| A3.4 | `test_baseline_excludes_loopback_and_documentation_values` + `test_baseline_excludes_rfc2606_reserved_tld_emails` (the remediation addition) | Re-run: PASS |
| A3.5 | `tests/contract/test_push_gate_wiring.py::test_mode_line_distinguishes_operator_denylist_from_baseline_only` | Re-run: PASS. Live-checked separately: `push-gate-check` over this repo's real range printed `[pre-push] denylist scan mode: operator denylist + baseline` on stderr (§"Live verification" below) |

### FR4 — No amnesty list; the FROZEN↔scan invariant is documented

| ID | Evidence | Verified |
|---|---|---|
| A4.1 | `test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source` (greps `denylist_scan.py`'s own source for an `ALLOWLIST/SANCTIONED/AMNESTY/EXEMPT` constant/dict/set assignment) | Re-run: PASS. Independently re-ran the same class of grep across `dadaia_workspace/features/chokepoints/**` — no match |
| A4.2 | `tests/integration/test_push_gate_denylist.py::test_git_mv_into_archive_produces_no_new_blob_and_a_clean_scan` (real git repo, `git mv` into `specs/_archive/`, clean scan) contrasted with `test_editing_the_same_content_produces_a_new_blob_and_a_refusal` (edit of same content, refused) | Re-run: PASS (both) |
| A4.3 | Deferred to T-090-11 (CLOSURE-phase memory write) — `specs/memory/` is writable only in DEFINITION/CLOSURE phase; the invariant paragraph exists verbatim in `SPEC.md` §3/FR4 now, ready to be quoted at closure | Not yet due — T-090-10 precondition is T-090-09, not T-090-11 |

### FR5 — The refusal is a satisfiable diagnostic

| ID | Evidence | Verified |
|---|---|---|
| A5.1 | `test_refusal_message_shape_and_ten_item_cap` — asserts ref, `path:line`, masked term, source layer all present | Re-run: PASS |
| A5.2 | Same test + `test_unmasked_operator_term_absent_from_every_hit_field` (pure matcher) + the e2e journey (`test_push_denylist_journey.py`) all assert the unmasked term is absent from every output surface | Re-run: PASS |
| A5.3 | Same test: asserts `"--amend" in message or "rebase" in message` and `"already-published history never needs a rewrite" in message` | Re-run: PASS |
| A5.4 | Same test: 12 synthetic hits, 10 shown + `"2 more"` remainder line | Re-run: PASS |

### FR6 — Fail-closed and fail-open boundaries are explicit

| ID | Evidence | Verified |
|---|---|---|
| A6.1 | `test_git_object_read_failure_refuses_naming_the_failure` (unit, fake) + `test_push_gate_denylist.py::test_real_git_failure_refuses_naming_the_failure` (integration, real non-repo dir) — both assert `--no-verify` named | Re-run: PASS (both) |
| A6.2 | `test_undecodable_object_is_skipped_and_counted` (pure matcher: `skipped_binary_count == 1`, hit list empty) + adapter-level `test_new_objects_marks_binary_blob_undecodable` (real binary blob, `decodable=False`, never raised) | Re-run: PASS. **Finding QA-1 (LOW, non-blocking)** — see below: no test exercises the skip-count note at the `push_gate_decision`/CLI-output layer end-to-end; manually verified live (see Finding QA-1) that the wiring is correct |
| A6.3 | `tests/contract/test_push_gate_wiring.py::test_push_gate_check_always_wires_a_real_object_source` (spy object source, asserts it was actually called) | Re-run: PASS |

### FR7 — Architectural purity and performance budget

| ID | Evidence | Verified |
|---|---|---|
| A7.1 | `lint-imports` (import-linter) | Re-run independently: **9 contracts kept, 0 broken**, including `features must not import infrastructure directly` and `features must not import subprocess directly` |
| A7.2 | `push_gate_decision(..., object_source: GitObjectReader, ...)` is a required keyword parameter (no default) — mypy `--strict` enforces every call site wires one; unit tests (`test_push_denylist_scan.py`, `test_push_gate_decision.py`) inject `_FakeObjectSource`/`_FailingObjectSource`, no real git, no filesystem | Re-run: PASS. `mypy --strict dadaia_workspace/` — clean, 265 files (matches SE-reported count) |
| A7.3 | SE handoff (`2026-08-14T19:09:16Z-software-engineer-T-090-09-push-denylist-journey.handoff.json`): measured `0.760s` over this release's own `origin/develop..HEAD` range (15 commits), well under the 2s budget; capture at `.dadaia/tmp/software-engineer/20260814/T-090-09-timing-A7.3.txt`. Recording it into `CLOSURE.md` is T-090-12's job (SPEC §5), not yet due | Underlying measurement verified present and < 2s; transcription pending at closure — not a T-090-10 defect |

### FR8 — Redaction of foreign context names at authoring time

| ID | Evidence | Verified |
|---|---|---|
| A8.1 | `tests/unit/cli/test_redact_output.py` (5 CLI-level tests: doctor, context list table/json, context show explicit-foreign/own-context) | Re-run: PASS (16/16 unit + 5/5 contract). **Live-checked** (see below): `dadaia context list --redact` against the real multi-context workspace registry emitted `[REDACTED-CONTEXT-1]` … `[REDACTED-CONTEXT-11]` for every context other than `dadaia-workspace` (this session's own resolved context); `dadaia doctor --redact` reported "All invariants OK" (no foreign name present to redact at this moment — healthy path) |
| A8.2 | `tests/contract/test_cli_output_stability.py` — 5 tests pinning the full captured default-output string byte-for-byte, doctor/context-list/context-show × table/json | Re-run: PASS |
| A8.3 | `test_redactor_ordinal_by_first_appearance_and_caller_exclusion` (pure) + the multi-foreign-context CLI scenarios | Re-run: PASS |
| A8.4 | `test_redactor_json_value_preserves_key_set_and_non_string_leaves` (`json.dumps`/`json.loads` round-trip) + `test_context_list_redact_json_same_key_set_and_masks_foreign` | Re-run: PASS |
| A8.5 | `dadaia public doctor` — `[ok] public-privacy`. Doctrine line confirmed present in `dadaia_workspace/public/agents/qa-engineer.md` under `## Approval contract` (`"Diagnostic output transcribed into any authored document — QA evidence, SPEC, CLOSURE, report, handoff — is captured with --redact or masked by hand; a foreign Spec Context name is never pasted verbatim."`) — the exact line this review's own §"Live verification" and §"Redaction doctrine applied to this artifact" sections follow | Confirmed present in the projected persona I am reading right now (this agent's own frontmatter body) |

### FR9 — Evidence of a clean gate

| ID | Evidence | Verified |
|---|---|---|
| A9.1 | `tests/e2e/test_push_denylist_journey.py::test_planted_term_refused_then_clean_push_after_amend` — real `.git/hooks/pre-push` boundary, planted synthetic term refused, term removed + amended, clean push after a matching security-reviewer APPROVE | Re-run (full suite): PASS |
| A9.2 | `dadaia ci preflight` — first run this session hit an unrelated flake (see Finding QA-2 below) in pytest only; ruff format, ruff check, mypy --strict, lint-imports all PASSED on that same run. Full-suite pytest re-run twice (once directly, once matching preflight's exact `-n auto -m "not quarantine"` invocation) both green: **2185 passed, 3 skipped** | Re-run: PASS (reproducible) |
| A9.3 | Every new test module in this release's diff (`test_git_object_reader.py`, `test_denylist_scan.py`, `test_push_denylist_scan.py`, `test_push_gate_wiring.py`, `test_push_gate_denylist.py`, `test_redact_output.py`, `test_cli_output_stability.py`, `test_push_denylist_journey.py`) declares `Intent: CONTRACT — v0.9.0 <A-id list>` in its module docstring, confirmed by direct grep of each file's first 20 lines. The three pre-existing files touched (`test_push_branch_policy.py`, `test_push_gate_decision.py`, `test_push_gate_check.py`) received fixture repairs only — `git diff` shows **zero** added/removed `def test_` lines in those three files, so no new undeclared test entered under A9.3's rule | Confirmed |
| A9.4 | Deferred to T-090-12 (CLOSURE) — not yet due | N/A for this task |

---

## Live verification (this session, redaction doctrine applied)

- **Full suite, twice**: `pytest -p no:cacheprovider -q` → `2185 passed, 3 skipped in 105.16s`; re-run as `pytest -q -p no:cacheprovider -m "not quarantine" -n auto` (the exact mode `ci preflight` uses) → `2185 passed, 3 skipped, 1 warning in 75.76s`. Both match the SE-reported baseline exactly.
- **`lint-imports`**: `Contracts: 9 kept, 0 broken.`
- **`dadaia ci preflight`**: ruff format / ruff check / mypy --strict / lint-imports all `[PASS]`; the pytest step failed once with 13 failures in pre-existing context-resolution tests unrelated to this release's diff (`tests/unit/core/test_specs_resolver_resolve_context.py`, `tests/unit/cli/test_specs_resolution.py`, `tests/unit/test_container.py`, two `tests/integration/cli/` files) — not reproduced on an isolated re-run of the same files (`57 passed`) nor on a full-suite re-run (`2185 passed, 3 skipped`). Registered as bug `specs-resolver-context-tests-flaky-under-xdist-full-suite` (Finding QA-2).
- **Push-range denylist scan, over the real `origin/develop..HEAD` range**: `printf 'refs/heads/develop <HEAD> refs/heads/develop <origin/develop>\n' | dadaia ci push-gate-check` printed `[pre-push] denylist scan mode: operator denylist + baseline` and then refused **only** on the expected missing-security-verdict ground (`no security-reviewer APPROVE covers the origin/develop..develop delta being pushed`) — the denylist scan itself produced **no** refusal, i.e. the range is scan-clean. This independently confirms the SE remediation handoff's claim (RFC-2606 baseline carve-out + fixture hygiene + positive-fixture concatenation left the pushed range clean of matchable terms).
- **`--redact` A8.1**: `dadaia context list --redact` against the real registry (11 other Spec Context Projects present on this box) rendered every foreign name/slug as `[REDACTED-CONTEXT-<n>]`, ordinal by first appearance, none unmasked. `dadaia context show --json --redact` for this session's own bound context (`dadaia-workspace`) returned the caller's own name unredacted (correct — only *foreign* names are masked) with no other context present in that particular output to mask. `dadaia doctor --redact` reported a clean bill of health at the moment of this check (no outstanding foreign-context diagnostic line to redact) — A8.1's masking behavior itself is separately pinned by the 5 CLI-level automated tests above, which construct the foreign-name-present case deterministically.
- **Redaction discipline applied to this document itself**: every foreign context name transcribed above (`[REDACTED-CONTEXT-1]` … `[REDACTED-CONTEXT-11]`) is the tool's own placeholder output, captured verbatim from the `--redact` run — no real foreign Spec Context name was read, typed, or pasted into this artifact at any point in this review.

---

## Findings summary

| # | Severity | Area | Finding | Blocking? |
|---|---|---|---|---|
| QA-1 | LOW | A6.2 test coverage | No automated test exercises the binary-skip-count note at the `push_gate_decision` → CLI-output layer end-to-end (only the pure-matcher `ScanOutcome.skipped_binary_count` and the real-adapter `decodable=False` marking are unit-tested separately). Manually verified live in this session that the wiring is correct: `_annotate_skip` (`service.py:329`) attaches the note to `Decision.warn`, and `ci.py:140-141`/`:298-299` echoes `decision.warn` to stderr on both the refuse and allow paths. Recommend a follow-up unit test asserting `decision.warn` contains the skip-count note for at least one allow-path and one refuse-path case | No — behavior verified correct; the gap is in test coverage of an already-correct code path, not a functional defect |
| QA-2 | LOW | Test-suite flake (not in this release's scope) | `dadaia ci preflight`'s pytest step failed once with 13 failures across pre-existing context/session-resolution tests, none touched by this release's diff; not reproduced on an isolated re-run or a full-suite re-run immediately after. Same flake CLASS as the already-resolved `panel-e2e-readiness-flaky-under-xdist-load` / `panel-command-readiness-flaky-under-xdist-load` bugs (full-suite `-n auto` load sensitivity), different site. Registered as `specs-resolver-context-tests-flaky-under-xdist-full-suite` | No — outside v0.9.0's scope (`features/chokepoints/**`); the release's own full-suite run is green and reproducible |
| QA-3 | INFO | Write-set deviations | T-090-06 touched `container.py` (not in its declared write set) and `tests/e2e/test_push_gate_check.py` (a pre-existing e2e file, fixture repair) — both flagged by the implementer's own T-090-03..06 handoff as deliberate, necessary deviations (purity constraint compliance + regression fix for the new `rev-list` call requiring a resolvable sha). Reviewed: both changes are minimal, correctly scoped, and covered by the green suite | No — justified and verified |
| QA-4 | INFO | Remediation root-cause check | The RFC-2606 baseline carve-out (`privacy_baseline.json` v1→v2) is a legitimate structural fix (RFC-2606 reserved TLDs are synthetic by definition, same carve-out philosophy as the pre-existing `example.com`/RFC-5737 exclusions), backed by a RED-first regression test (`test_baseline_excludes_rfc2606_reserved_tld_emails`) confirmed to fail before the JSON change and pass after. The fixture concatenation (`"198.18" + ".0.5"`, `"/hom" + "e/alice"`) still exercises the real compiled baseline regex at runtime — verified by reading the assertions, which check the assembled positive fixture actually produces exactly 1 hit | No — root-cause, not a symptom patch; not a stewardship violation |

No CRITICAL, HIGH, or MEDIUM findings.

---

## Test stewardship checklist (per TASKS.md T-090-10 description)

- **Intent declared at birth (A9.3):** confirmed for all 8 new test modules; zero new `def test_` entries in the 3 pre-existing files touched. PASS.
- **No test pruned/skipped to go green:** `git diff origin/develop..HEAD -- tests/` contains zero `pytest.mark.skip`/`xfail`/`quarantine` additions. PASS.
- **LARGE (e2e) census:** `pytest --collect-only -q -m e2e` → **56** e2e-tier tests currently collected (this release added exactly 1: `test_planted_term_refused_then_clean_push_after_amend`). `tests/AGENTS.md`'s declared cap for this repo is 30, tracked as a pre-existing WARN (companion release's remediation target, not a hard failure this release) — this release's contribution (+1) does not silently grow past its declared handling; the new file correctly names its owner (`Owner: software-engineer (LARGE-tier e2e; ...)`). PASS.
- **No amnesty/sanctioned-terms list introduced (FR4/A4.1):** confirmed above. PASS.

---

## Security/privacy leakage note

Reviewed for observable risk surfaces in this release's diff (`features/chokepoints/**`,
`infrastructure/git_objects.py`, `infrastructure/privacy_check.py`, `cli/commands/{ci,doctor,context}.py`,
`cli/redact.py`, `dadaia_workspace/public/agents/qa-engineer.md`, `privacy_baseline.json`,
`container.py` composition-root additions):

- **No new dependency, secret, token, or credential surface.** The scan is stdlib +
  `git` subprocess only, consistent with the rest of the chokepoints subsystem.
- **The refusal message never echoes the matched line or the unmasked term** — pinned
  by `A5.2`/`test_unmasked_operator_term_absent_from_every_hit_field` and independently
  re-confirmed by reading `_compose_denylist_refusal` (`service.py:341-367`), which
  only ever interpolates `hit.masked_term`, never `hit.path`'s raw line content or any
  raw matched substring.
- **The operator denylist file itself stays operator-private** — `load_denylist_terms()`
  (`container.py`) reads from `$DADAIA_PRIVACY_DENYLIST` / `.dadaia/states/privacy_denylist.json`,
  neither tracked in the repository; no new tracked file carries a real private term
  (confirmed: only synthetic `zz-`-prefixed terms and generic RFC-2544/RFC-2606 example
  values appear in the new test fixtures, per the TASKS standing rule and my own read of
  every new test file above).
- **`--redact`'s masking happens only at the render boundary** (per the T-090-07 SE
  handoff and confirmed by reading `doctor.py`/`context.py`'s `_build_redactor` call
  sites) — the underlying services keep returning true names; no service-layer data
  loss, only a display-time transform. `A8.4`'s JSON round-trip test confirms the
  `--redact --json` output stays valid JSON with the same key set, so no downstream
  machine consumer's parsing contract silently breaks.
- **This review artifact itself** carries no foreign Spec Context name pasted verbatim —
  every context name shown above (`[REDACTED-CONTEXT-1]` … `[REDACTED-CONTEXT-11]`) is
  the tool's own `--redact` placeholder output, captured directly from the CLI run in
  this session; no diagnostic output naming a real foreign context or repo slug was
  read into this document unmasked, per the FR8b doctrine line now present in this
  agent's own canonical persona (`qa-engineer.md`, confirmed under §FR8/A8.5 above).

No suspected leakage found. Nothing beyond the standing T-090-02/T-090-13 diff-based
`security-reviewer` reviews already scheduled at the gitflow milestones is surfaced by
this review.

## Accepted deviations

None required for T-090-10 itself. The two implementer-side write-set deviations
(QA-3) are reviewed and accepted as justified, not treated as a TASKS.md violation.

## Marker note

This review's `[-]`→`[x]` completion transition is committed in the same commit as this
artifact and the `TASKS.md` marker flip, per the ordinary `dadaia-task-manager`
discipline (reserve commit `0491613a chore(tasks): start T-090-10` already landed
separately).
