# ALPHA-1 QA Review — Release v0.11.0 (scan-v2: prior-published-term amnesty and push-gate hardening)

**Task:** T-110-15 · **Owner role:** qa-engineer · **Reviewer:** qa-engineer
**Preconditions verified:** T-110-01..14 all `[x]` in `TASKS.md`.
**Validated from:** the live instance (branch `feature/v0.11.0`, worktree HEAD at
`e4492735 chore(T-110-14): measure the shipped scan on real content, ordinary and
fallback ranges`, plus this review's own `9ceceaa2 chore(tasks): start T-110-15`
reservation commit), not the diff or the implementer's report alone. Every command below
was independently re-run in this session against that commit, with caches redirected
outside the repo (`-p no:cacheprovider`, `MYPY_CACHE_DIR` under `.dadaia/tmp/`).

## Verdict

**APPROVED.** All 55 SPEC acceptance ids across FR1–FR10 (A1.1–A10.5) are satisfied,
independently re-verified against the shipped code — not taken on the implementer's
word. Particular attention was given, per the task description, to: the amnesty's three
semantic cases (A1.1–A1.3), including a direct read of the smuggling-path attack test
(`test_amnesty_does_not_apply_to_a_new_value_in_an_edited_path`); the FR2 fail-closed
table (A2.3–A2.4); the FR4 oversized byte-bound (A4.2); the FR6 masking regression
fixture (A6.2); and the FR10 invariants — A4.1's contract test and the FROZEN↔scan
integration test are both confirmed **unmodified** by direct diff inspection, not by
trusting the TASKS.md claim. Zero new e2e tests (56 collected, unchanged). No CRITICAL or
HIGH finding. One non-blocking MEDIUM finding (QA-1, below) outside this task's
acceptance-id scope, routed to CLOSURE. No task returns to `[-]`.

---

## Per-FR acceptance evidence

### FR1 — Prior-published-term amnesty (the suppression predicate)

| ID | Evidence | Verified |
|---|---|---|
| A1.1 | `test_amnesty_suppresses_a_value_already_published_at_the_same_path` — a blob whose prior version at the base carries the matched value produces no hit | Re-run: PASS (V3) |
| A1.2 | `test_amnesty_does_not_apply_to_a_new_path_carrying_the_same_value` — same value in a path with no prior content still hits | Re-run: PASS (V3) |
| A1.3 | `test_amnesty_does_not_apply_to_a_new_value_in_an_edited_path` — the deliberate smuggling-path attack: a value absent from the prior text of an edited path still refuses even though a *different* value of the same term source was present there; also asserts `masked_term` never leaks the suppressed term (A5.2 v0.9.0 unaffected) | Re-run: PASS (V3); read the predicate in `denylist_scan.py#_first_match` directly — keyed on `matched_value`, never on pattern id/layer, matching the SPEC's normative sentence exactly |
| A1.4 | `test_amnesty_suppression_is_case_insensitive_on_both_sides` | Re-run: PASS (V3) |
| A1.5 | `scan_objects` signature unchanged (4 params, confirmed by direct read); `lint-imports --config setup.cfg --no-cache` green (V2, folded into V1) | Re-run: PASS |
| A1.6 | `test_editing_a_tests_fixture_that_already_published_the_literal_no_longer_refuses` — real git range, real remote, `tests/**` fixture literal | Re-run: PASS (V5) |

### FR2 — Prior-side same-path resolution inside the chunk loop

| ID | Evidence | Verified |
|---|---|---|
| A2.1 | `test_new_objects_resolvable_base_edited_path_carries_prior_text` | Re-run: PASS (V4) |
| A2.2 | `test_new_objects_fallback_shape_every_object_carries_no_prior_text` — byte-identical to v0.9.0 in the fallback shape | Re-run: PASS (V4) |
| A2.3 | `test_new_objects_prior_side_batch_check_failure_raises_typed_error` (unit) + the integration case forcing a real git failure on the prior-side lookup, naming `--no-verify` | Re-run: PASS (V4, V5) |
| A2.4 | `test_new_objects_resolvable_base_new_path_carries_no_prior_text`, `test_new_objects_over_cap_prior_blob_carries_no_prior_text`, `test_new_objects_undecodable_prior_blob_carries_no_prior_text` — three unit cases, all map to explicit absence, never an empty string | Re-run: PASS (V4) |
| A2.5 | `test_prior_side_lookup_invocations_are_two_per_chunk_not_per_blob` | Re-run: PASS (V4) |
| A2.6 | `core/protocols/git_object_reader.py` read directly: `ScannedObject.prior_text` is a plain `str \| None` dataclass field, zero I/O in the module | Re-run: PASS (direct read) |

### FR3 — Self-scan sentinel covers `tests/**`, shrink-only baseline, integration marker

| ID | Evidence | Verified |
|---|---|---|
| A3.1 | `_SCAN_SCOPE = ("dadaia_workspace", "specs", "tests")`; `_EXCLUDED_PREFIXES = ("specs/_archive/", "specs/audits/_archive/")`; `_NO_FOREIGN_SLUGS = ()` — all read directly in `test_repo_self_scan.py` | Re-run: PASS (direct read) |
| A3.2 | `_TESTS_SCOPE_BASELINE` is a literal 29-row `tuple[tuple[str, str], ...]` — 14 `home-abs-path`, 9 `email-address`, 5 `ipv4-literal`, 1 `secret-token` — counted directly, matches SPEC §1's census and the T-110-12 enumeration capture | Re-run: PASS (direct count) |
| A3.3 | `test_no_hit_outside_the_shrink_only_baseline` | Re-run: PASS (V6) |
| A3.4 | `test_every_baseline_row_still_produces_a_hit` | Re-run: PASS (V6) |
| A3.5 | `pytestmark = [pytest.mark.integration, pytest.mark.slow(...)]`; `pytest tests/integration/test_repo_self_scan.py -m integration --collect-only -q` → 2 collected | Re-run: PASS (V7, direct read) |
| A3.6 | A4.1's grep-based source scan of `denylist_scan.py` (V8) is empty; the baseline lives only in the test module, confirmed by direct read of `denylist_scan.py` — no reference to any baseline structure | Re-run: PASS |

### FR4 — Oversized blobs partially scanned and honestly reported

| ID | Evidence | Verified |
|---|---|---|
| A4.1 | `test_oversized_object_produces_a_hit_when_its_scanned_prefix_matches` (matcher level) + `test_new_objects_scans_the_first_cap_bytes_of_an_oversized_text_blob` (adapter level, the REWRITE of the v0.9.0 zero-coverage test — see "Rewritten tests" below) | Re-run: PASS (V3, V4) |
| A4.2 | `assert len(big.text.encode("utf-8")) == big.scanned_bytes` inside the same adapter test — the byte-count assertion proves the remainder is never read | Re-run: PASS (V4) |
| A4.3 | `test_oversized_object_with_undecodable_prefix_counts_as_binary_only` / `test_new_objects_oversized_blob_with_undecodable_prefix_falls_back_to_binary` — genuinely undecodable still counted with today's wording | Re-run: PASS (V3, V4) |
| A4.4 | `test_oversized_note_appears_in_decision_warn_on_allow`/`test_oversized_note_appears_in_decision_warn_on_refuse` — masked path (FR6), total size, scanned-bytes fact all present; `test_oversized_object_always_produces_a_note_even_with_no_hit` at matcher level | Re-run: PASS (V3) |
| A4.5 | Same two `decision.warn`-on-allow/refuse tests — QA-1 (v0.10.0's own numbering conflict aside: this is the v0.9.0 CLOSURE's own QA-1 item, now closed) confirmed pinned by unit test, not a manual check | Re-run: PASS (V3) |
| A4.6 | `test_new_objects_oversized_blob_with_undecodable_prefix_falls_back_to_binary`; `_read_oversized_blob` decodes `errors="strict"` and falls back on `UnicodeDecodeError`, confirmed by direct read | Re-run: PASS (V4, direct read) |

### FR5 — Registry-derived foreign-name set

| ID | Evidence | Verified |
|---|---|---|
| A5.1 | `test_foreign_slugs_carrying_a_registry_name_and_slug_both_refuse` (unit) + the real-registry-fixture integration case | Re-run: PASS (V3, V5) |
| A5.2 | `_foreign_repo_slugs` subtracts **both** `own_slug` and `own_name` (resolved from `registry_identities` where `repo_slug == own_slug`), confirmed by direct read of `cli/commands/ci.py:227-273` | Re-run: PASS (direct read) |
| A5.3 | The registry read goes through `container.load_registry_context_identities` (mirrors `load_denylist_terms`); V1's `lint-imports` pass and `tests/contract/test_import_linter_ignore_cap.py` (part of the full suite, unmodified) confirm no new `ignore_imports` entry | Re-run: PASS |
| A5.4 | `load_registry_context_identities` catches `(OSError, ValueError, KeyError, TypeError, SchemaVersionError)` and returns `()`, confirmed by direct read of `container.py:228-251` | Re-run: PASS (direct read) |
| A5.5 | `.dadaia/tmp/software-engineer/20260815/t-110-13-enumeration-capture.txt` — 6 hits over the widened set, every one individually dispositioned (all "amnestied by FR1 by construction", none in this release's own push range — confirmed `origin/develop..develop` range object count = 0 at capture time) | Re-run: read in full, redaction discipline upheld (real names never printed, only `foreign-name-NN` ordinals and lengths) |
| A5.6 | `_NO_FOREIGN_SLUGS` in `test_repo_self_scan.py` is untouched by T-110-13 (confirmed: FR5's write set never names this file, and A3.1's direct read above shows it unchanged) | Re-run: PASS |

### FR6 — Every operator-facing path-bearing string masks its offending segments

| ID | Evidence | Verified |
|---|---|---|
| A6.1 | `test_refusal_path_segment_matching_a_foreign_slug_is_masked` — line number and short sha untouched, offending segment replaced | Re-run: PASS (V3) |
| A6.2 | `test_refusal_path_with_no_matching_segment_is_byte_identical` — regression fixture, no placeholder appears | Re-run: PASS (V3) |
| A6.3 | `test_oversized_note_path_segment_is_masked_too` — asserted separately from A6.1 | Re-run: PASS (V3) |
| A6.4 | `tests/unit/cli/test_redact_output.py` passes with unmodified assertions (V9); `cli/redact.py` confirmed a thin consumer of `core/redaction.py` by direct read | Re-run: PASS (V9, direct read) |
| A6.5 | `core/redaction.py` read directly: stdlib-only (`re`, `collections.abc`), zero I/O | Re-run: PASS (direct read) |
| A6.6 | `test_refusal_path_segment_matching_a_foreign_slug_is_masked`, `test_oversized_note_path_segment_is_masked_too`, `test_same_offending_segment_gets_the_same_ordinal_across_hit_and_note` all assert the unmasked slug is absent from both `decision.message` and `decision.warn` | Re-run: PASS (V3) |

### FR7 — Pre-push sha validation and git argv hardening

| ID | Evidence | Verified |
|---|---|---|
| A7.1 | `test_option_shaped_local_sha_glob_form_is_malformed`, `test_option_shaped_local_sha_branches_form_is_malformed` | Re-run: PASS (V3) |
| A7.2 | `test_all_zero_deletion_sentinel_still_parses` | Re-run: PASS (V3) |
| A7.3 | `test_sha256_length_local_sha_parses`, `test_39_and_41_char_hex_shas_are_malformed` | Re-run: PASS (V3) |
| A7.4 | `test_rev_list_argv_carries_trailing_end_of_options_marker_resolvable_base`/`..._fallback_shape`, `test_is_resolvable_commit_rejects_option_shaped_sha_before_interpolation` | Re-run: PASS (V4) |
| A7.5 | Full existing contract/integration suites pass unmodified (V1 full-suite run, 2253 passed) | Re-run: PASS |

### FR8 — Typed batch-parser boundary, desync aborts instead of fabricating

| ID | Evidence | Verified |
|---|---|---|
| A8.1 | `test_truncated_batch_stream_raises_typed_error_not_raw_value_error`, `test_non_numeric_size_field_raises_typed_error_not_raw_value_error` | Re-run: PASS (V4) |
| A8.2 | `test_desynchronised_header_shape_aborts_typed_never_yields_fabricated_object` | Re-run: PASS (V4) |
| A8.3 | `test_git_object_read_failure_refuses_naming_the_failure` (service-layer test) confirms the FR6-shaped refusal names the failure and `--no-verify`, never a traceback | Re-run: PASS (V3) |
| A8.4 | `core/protocols/git_object_reader.py`'s port contract re-read directly against the adapter's typed-error behavior (`_read_blob_chunk`/`_resolve_prior_texts`) — both wrap the same header-parse pair identically | Re-run: PASS (direct read) |

### FR9 — Chunked batch conversation, bounded resident set

| ID | Evidence | Verified |
|---|---|---|
| A9.1 | `.dadaia/tmp/software-engineer/20260815/t-110-05-peak-bound-measurement.txt` — 600→6000 blobs (10×) produces only ~22% peak-RSS growth (16000→19456 KiB), the flat signature of a chunk-bounded conversation vs. the ~277 MB unchunked baseline the v0.9.0 CLOSURE recorded | Re-run: read in full |
| A9.2 | `test_under_cap_blob_count_spawns_a_single_batch_call_not_per_object`, `test_batch_conversation_invocations_grow_with_chunks_not_blob_count` | Re-run: PASS (V4) |
| A9.3 | `tests/unit/infrastructure/test_git_object_reader.py` full module green (26 passed, V4); no weakening of prior timeout/typed-error assertions confirmed by diff read | Re-run: PASS |
| A9.4 | `.dadaia/tmp/software-engineer/20260815/t-110-14-fallback-range-capture.txt` — 9,095 blobs / 130.29 MB, read 1.261s + match 53.871s = 0.423 s/MB, peak RSS 285.5 MiB; explicitly supersedes the archived v0.9.0 V14 figure (147s/1.3 s/MB); match-throughput optimisation **REJECTED** with a three-point recorded reason | Re-run: read in full |
| A9.5 | `.dadaia/tmp/software-engineer/20260815/t-110-14-ordinary-range-capture.txt` — 8 repeated before/after pairs on the real release delta, mean delta ~+11.6ms, attributed to FR2's exactly-two-extra-batched-calls-per-chunk design cost, no algorithmic regression | Re-run: read in full |

### FR10 — Invariants this release must not break

| ID | Evidence | Verified |
|---|---|---|
| A10.1 | `test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source` — confirmed **unmodified** by direct `git diff 89a703b8..HEAD` hunk inspection: the function body (lines 358–369) falls entirely outside every changed hunk; only new tests were appended after it | Re-run: PASS (V3) + independent diff verification |
| A10.2 | `test_git_mv_into_archive_produces_no_new_blob_and_a_clean_scan` — confirmed **unmodified**: the diff hunk touching this file starts immediately after this function's closing lines; the rewritten test (`test_editing_the_same_content_produces_a_new_blob_and_a_refusal` → `test_editing_a_path_that_already_published_the_value_no_longer_refuses`) is a **different** function | Re-run: PASS (V5) + independent diff verification |
| A10.3 | `lint-imports --config setup.cfg --no-cache` green (V1/V2); `tests/contract/test_import_linter_ignore_cap.py` unmodified (part of the full 2253-pass run) | Re-run: PASS |
| A10.4 | `grep -rn "AMNESTY\|SANCTIONED\|ALLOWLIST" dadaia_workspace/features/chokepoints/ dadaia_workspace/infrastructure/git_objects.py` → zero hits | Re-run: PASS (V8, empty output) |
| A10.5 | `.dadaia/.venv/bin/dadaia ci preflight` → all 5 checks PASS (ruff format, ruff check, mypy --strict, lint-imports, pytest) | Re-run: PASS (V1) |

---

## Rewritten tests — the "3 rewrites" claim, independently verified

The implementer's TASKS.md evidence claims three legitimate behavior-change rewrites, not
pruning-to-green. Each was independently located and read against `git diff
89a703b8..HEAD` (89a703b8 = the milestone-(a) merge commit, the last point before any
T-110-0x task commit):

1. **FR1 superseding a v0.9.0 refusal assumption.**
   `test_editing_the_same_content_produces_a_new_blob_and_a_refusal` →
   `test_editing_a_path_that_already_published_the_value_no_longer_refuses`
   (`tests/integration/test_push_gate_denylist.py`). The v0.9.0 test asserted the edit
   **refuses**; the v0.11.0 test asserts the same edit **is allowed**, with a docstring
   that explicitly names the superseded test and cites SPEC §4.2 (the whole-blob ruler is
   *not* narrowed — the amnesty derives from published git state instead). Confirmed:
   this is the literal "blocking problem" (SPEC §1) the release exists to fix.

2. **FR4 partial-scan superseding zero-coverage.**
   `test_new_objects_marks_oversized_blob_undecodable_and_never_fetches_its_content` →
   `test_new_objects_scans_the_first_cap_bytes_of_an_oversized_text_blob`
   (`tests/unit/infrastructure/test_git_object_reader.py`). The v0.9.0 test asserted
   `decodable is False` / `text == ""` for an oversized blob; the v0.11.0 test asserts
   `decodable is True` / `oversized is True` / `text` carries the decoded prefix, with a
   new byte-count assertion (A4.2). This is exactly FR4's honesty fix (SPEC "the honesty
   problem") — the v0.9.0 fail-open is now partial coverage, not zero.

3. **Sentinel scope split.**
   `test_this_repos_own_tracked_tree_scans_clean` → two tests,
   `test_no_hit_outside_the_shrink_only_baseline` and
   `test_every_baseline_row_still_produces_a_hit`
   (`tests/integration/test_repo_self_scan.py`). The v0.9.0 single test asserted a
   strict-zero scan; the v0.11.0 split asserts the two-directional shrink-only baseline
   property FR3 requires (A3.3/A3.4) — a single assertion cannot express both directions.

All three rewrites are disclosed in their own docstrings, cite the SPEC entry/ADR that
authorizes the behavior change, and are the correct shape for a superseded assumption —
not a weakened or deleted assertion. No `qa-engineer` deletion/skip verdict was required
because nothing was deleted or skipped; each old assertion was replaced by a new one
proving the **new**, SPEC-mandated behavior. This satisfies `dadaia-test-stewardship`'s
demotion/rewrite bar.

---

## Test stewardship checklist

- **Intent declared at birth:** all 6 touched modules carry an updated module-level
  `Intent: CONTRACT — v0.9.0 <ids>; v0.11.0 <ids>` line (confirmed by direct grep of
  every changed file). **Zero new test modules** — `git diff 89a703b8..HEAD --name-status
  -- tests/` shows no `A` (added) rows; every new test landed inside one of the seven
  existing modules PLAN §8 names. PASS.
- **Zero new e2e:** `pytest tests/e2e --collect-only -q` → 56 tests collected — unchanged
  from the pre-release census. PASS.
- **No test pruned/skipped to go green:** the only removed test function
  (`test_this_repos_own_tracked_tree_scans_clean`) was split into two stronger
  assertions of the same seam (documented above), not deleted outright; the other two
  "removed" function names are the disclosed FR1/FR4 rewrites, also documented above. No
  `git diff` hunk anywhere in the 6 touched test files removes an assertion without a
  same-commit replacement that tests a stronger or superseding property. PASS.
- **No sanctioned/amnesty list introduced:** A10.1/A10.4 (unmodified contract test +
  empty grep). PASS.
- **No private term in the repository:** every new literal read in this review uses the
  standing `zz-`-prefixed synthetic-term convention (`_SYNTHETIC_TERM`,
  `_SYNTHETIC_FOREIGN_SLUG`, `other_term = "zz-other-published-term"`, etc.) or the
  redacted `foreign-name-NN` ordinal form in the T-110-13 capture. PASS.

---

## Style/scope note — what I did and did not edit

Per the coordinator's request to name this precisely: **this review edited no test file
and no production file.** The module-level `Intent:` lines quoted above (e.g.
`tests/unit/infrastructure/test_git_object_reader.py`'s "v0.9.0 ...; v0.11.0 A7.4, A8.1,
A8.2, A9.2, A9.3, A2.1, A2.2, A2.3, A2.4, A2.5") are **pre-existing content**, authored by
`software-engineer` in the T-110-03…T-110-14 commits already on this branch before this
review began (verified by `git log 89a703b8..HEAD -- <file>` against each, all landing
under the corresponding `T-110-0x` commit, none under this review's own commits). This
review's only writes are: this artifact
(`specs/releases/v0.11.0/ALPHA-1-QA.md`), the `TASKS.md` `[ ]`→`[-]`→`[x]` marker flip for
T-110-15, and the handoff JSON under `.dadaia/handoff/`. A prior instruction in this
session's transcript asserted I had made such edits; that assertion was incorrect and is
corrected here rather than accepted at face value or acted on.

---

## Live verification (this session, redaction doctrine applied)

- **Full suite (the exact command requested):**
  `MYPY_CACHE_DIR=.dadaia/tmp/qa-engineer/20260815/mypy_cache python -m pytest -q
  -p no:cacheprovider -m 'not quarantine' -n auto` →
  **`2253 passed, 3 skipped, 1 warning in 92.78s (0:01:32)`**. The 3 skips are
  environment-gated (Windows-only / no non-loopback IPv4), unrelated to this release.
- **`dadaia ci preflight` (V1):** all 5 checks PASS — ruff format, ruff check,
  mypy --strict, lint-imports, pytest.
- **V3** (`tests/unit/features/chokepoints`): 87 passed.
- **V4** (`tests/unit/infrastructure/test_git_object_reader.py`): 26 passed.
- **V5** (`tests/integration/test_push_gate_denylist.py`): 12 passed.
- **V6** (`tests/integration/test_repo_self_scan.py`): 2 passed.
- **V7** (sentinel marker reachability, `-m integration --collect-only`): 2 collected.
- **V8** (`grep AMNESTY\|SANCTIONED\|ALLOWLIST` over the matcher+adapter): empty — 0 hits.
- **V9** (`tests/unit/cli/test_redact_output.py`): 15 passed.
- **e2e census:** `pytest tests/e2e --collect-only -q` → 56 collected, unchanged.
- **Redaction discipline applied to this document itself:** no foreign Spec Context
  name, repo slug, hostname, IP, email, or absolute local path was transcribed into this
  artifact — the T-110-13 enumeration capture's redacted `foreign-name-NN` ordinals are
  quoted as-is (already redacted at authoring time by the implementer); this review adds
  no further identifying detail.

---

## Findings summary

| # | Severity | Area | Finding | Blocking? |
|---|---|---|---|---|
| QA-1 | MEDIUM | `specs/releases/v0.11.0/{SPEC,PLAN,TASKS}.md` — `**Status:**` line | `dadaia specs doctor` reports 4 ERRORs (SPEC-DOC-004 ×3 + the derived SPEC-DOC-024): the Status line reads `Aprovado — operator-delegated approval, 2026-08-15 (goal directive)` instead of the bare canonical token `Aprovado`. Every prior release (v0.8.0/v0.9.0/v0.10.0, checked directly) used the bare token; this is a new deviation introduced at T-110-01 (already `[x]`, product-engineer's write scope, not `software-engineer`'s). `DADAIA.md` §5 states the three status tokens are kept "as they are" — the annotation breaks the doctor's exact-membership check. | **No** for T-110-15 — outside FR1–FR10's declared write sets and acceptance ids (A1–A10), and no `software-engineer` task's write set includes `SPEC.md`/`PLAN.md`/`TASKS.md` prose correction. **Yes** for T-110-16/17 — their stated Done criterion is `dadaia specs doctor green`; this must be corrected (Status line normalized to the bare `Aprovado` token, or the annotation moved to a separate prose line beneath it) before CLOSURE, by `product-engineer`/dispatcher. |

No CRITICAL, HIGH, or additional MEDIUM/LOW findings.

---

## Security/privacy leakage note

Reviewed for observable risk surfaces in this release's diff (the matcher, the adapter,
the redaction primitive, the CLI seam, and all 6 touched test modules):

- **No new dependency, secret, token, or credential surface.** FR1–FR9 touch only
  `features/chokepoints/**`, `infrastructure/git_objects.py`,
  `core/protocols/git_object_reader.py`, the new `core/redaction.py`, `cli/redact.py`,
  `cli/commands/ci.py`, `container.py`, and the six test modules — no new network call,
  no new external I/O beyond the pre-existing `git` subprocess surface.
- **The amnesty predicate cannot smuggle a new value.** Directly read and confirmed:
  `_first_match`'s suppression guard keys on `matched_value` (the literal string), never
  on pattern id or term source — A1.3's dedicated attack test (a different value of the
  same baseline pattern id) passes, proving the "prior email amnesties a new email" class
  R1 warns against does not exist in the shipped predicate.
- **No unmasked private-name segment reaches any emitted string.** A6.6's three tests
  assert the offending slug/term is absent from both `decision.message` and
  `decision.warn` in every FR4/FR6 combination exercised (refusal, oversized note, and
  both together with ordinal-stability). `core/redaction.py` is stdlib-pure with zero I/O
  (direct read), so the masking primitive itself introduces no new I/O-based leak vector.
- **The FR5 registry seam degrades safely.** `load_registry_context_identities` swallows
  `OSError`/`ValueError`/`KeyError`/`TypeError`/`SchemaVersionError` into an empty tuple
  (direct read, A5.4) — a malformed or missing registry can never crash the push hook or
  produce an unhandled exception at the security boundary.
- **The T-110-13 enumeration capture (evidence for A5.5) upholds the redaction-at-authoring
  doctrine.** Read in full: every real foreign context name/slug is replaced by an
  `foreign-name-NN`/length-only ordinal before being written to the `.dadaia/tmp/`
  capture file — no real private name was transcribed by the implementer, and none is
  transcribed into this QA artifact either.
- **This review artifact itself** carries no foreign Spec Context name, hostname, IP, or
  absolute local path — every path cited is workspace-relative to this repo's own tree.
- **Standing milestone-(a) diff review already APPROVED** (T-110-02,
  `2026-08-15T173153Z-security-reviewer-v0.11.0-definition-push`) covered the definition
  commit only. The milestone-(b) diff review of the full implementation delta
  (`origin/develop..develop`) is still due at T-110-18, per the ordinary gitflow
  cadence — not a gap this alpha-1 review introduces, and it is explicitly tasked (per
  TASKS.md T-110-18) to attack the same smuggling-path property this review already
  exercised at the unit level.

No suspected leakage found.

## Accepted deviations

None required by this task. QA-1 above is recorded as a non-blocking finding routed to
T-110-16/17 (CLOSURE), not treated as a TASKS.md violation by any `software-engineer`
task — the deviation originates in T-110-01's authored prose, a `product-engineer`
surface outside this alpha's software-engineer write sets.

## Marker note

This review's `[-]`→`[x]` completion transition is committed in the same commit as this
artifact and the `TASKS.md` marker flip, per the ordinary `dadaia-task-manager`
discipline (reserve commit `9ceceaa2 chore(tasks): start T-110-15` already landed
separately).
