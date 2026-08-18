# ALPHA-2-QA.md — `alpha-2` (WS-B + WS-E, gate hardening + governance primitives) segment QA gate

**Task:** T-043-23 · **Reviewers:** qa-engineer + security-reviewer · **First reviewed at commit:** `2c0b9959` · **Final verdicts at commit:** `ce47f1ea` (branch `feature/0.4.3`) · **Reviewed:** 2026-08-17

**Verdict: APPROVED** — qa-engineer r3 (`2026-08-17T183001Z…alpha-2-close-r3.handoff.json`) + security-reviewer r2 APPROVE (`2026-08-17T182834Z…alpha-2-delta-r2.handoff.json`, `metrics.commit_sha ce47f1ea`, scope `600361f2..ce47f1ea`).

Round history: QA r1 APPROVED at `2c0b9959`; security r1 REQUEST_CHANGES (1 HIGH, 1 MEDIUM, 5 LOW) → software-engineer remediation (6 commits, `f1a1ef93`…`ce47f1ea`, handoff `2026-08-17T181522Z…t-043-23-rework`) → security r2 APPROVED (all 7 findings re-probed FIXED) · QA r2 REQUEST_CHANGES (granular-range chokepoint refusals) → retracted in r3 after independent squash-shape dry-run: the publishable squash object set (tree `a50e5b14`, 114 objects) carries **zero** denylisted objects; the 3 refusals live only in never-published granular history (squash-publication ship shape, v0.4.2 precedent `6e1f9c63`). A fresh security push-verdict over the squashed `develop` delta is still required at ship, by design.

**The three reviewer artifacts below are committed verbatim for the audit trail**, with
one exception: hostname-shaped fixture values quoted by the reviewers are masked here
(`x.i…l` style, the gate's own masking convention) so this committed file carries no
contiguous denylisted literal — the unmasked originals live in the workspace-level
handoffs (bug `repo-self-scan-hits-alpha2-qa-historical-literal`).

---

# Appendix A — QA first-pass review (r1, unedited)

# QA review — v0.4.3 alpha-2 close (T-043-23)

**Reviewer:** qa-engineer · **Date:** 2026-08-17 · **Delta reviewed:** `600361f2..HEAD` (HEAD = `2c0b9959`)
**Branch:** `feature/0.4.3` (read-only for this agent; no source/spec edits made)
**Scope:** every `alpha-2` acceptance id (A9.x–A17.x) plus the Arm-B rider (AB.1–AB.5),
PLAN §5 `alpha-2` exit criteria, the retroactive test-stewardship verdict on
`tests/unit/scripts/test_lint_memory_atoms.py`'s deletion, a new-test slop audit, the
task trace, and the full suite/doctor run.

## Verdict

**QA verdict: APPROVE** on every acceptance id this agent owns (A9.x–A17.x, AB.1–AB.5).

**Alpha-2 segment exit is NOT yet fully unlocked** — PLAN §5 additionally requires
`security-reviewer` coverage of the gate/baseline delta (FR11, FR12) before the segment
exits. No `security-reviewer` handoff covering this delta exists at HEAD
(`.dadaia/handoff/dadaia-workspace/` was checked; the most recent `security-reviewer`
artifacts cover v0.4.3's *definition* push, not the `alpha-2` implementation delta).
This is outside qa-engineer's write scope — it is named here as the one remaining
precondition for `project-manager` to relay before flipping T-043-23 `[x]`, exactly as
this task's dispatch instructed.

## Per-acceptance-id table

| id | Requirement (abridged) | Evidence | Verdict |
|---|---|---|---|
| A9.1 | Relative `which`/`pyvenv.cfg` candidates rejected before `subprocess.run` | `infrastructure/python_env.py:215-232,247-259` (`os.path.isabs()` filters); `tests/unit/infrastructure/test_python_env.py::test_path_candidates_rejects_a_relative_which_result`, `::test_current_venv_pyvenv_executable_rejects_a_relative_value`, `::test_resolve_child_venv_interpreter_never_probes_a_relative_pyvenv_value` | PASS |
| A9.2 | Bounded `timeout=` + `stdin=DEVNULL`; hang degrades to `None` | `python_env.py:172,186-196` (`_INTERPRETER_PROBE_TIMEOUT_SECONDS=10`); `test_interpreter_version_probe_passes_a_bounded_timeout_and_devnull_stdin`, `::test_interpreter_version_probe_degrades_to_none_on_timeout` | PASS |
| A9.3 | `dadaia init` byte-identical on a healthy machine | No absolute-path candidate's control flow changed (only relative candidates newly filtered); full pre-existing bootstrap suite (`test_fresh_bootstrap_*`, `test_existing_bare_venv_*`, `test_healthy_venv_is_a_noop`, …) unmodified and green | PASS |
| A10.1 | Non-zero `git add` raises `GitSyncError` before commit | `git_subprocess.py:173-179`; `tests/unit/infrastructure/test_git_subprocess_unit.py::test_commit_paths_raises_on_a_failed_git_add` | PASS |
| A10.2 | Commit is path-scoped; pre-staged content ignored | `git_subprocess.py:145-179` (`git add -- <paths>` then `git commit … -- <paths>`); unit fixture `test_commit_paths_applies_literal_pathspec_magic_to_add_and_commit` + **real-git** integration fixture `tests/integration/infrastructure/test_git_subprocess.py::test_commit_paths_ignores_operator_pre_staged_unrelated_content` | PASS |
| A10.3 | Pathspec-magic defence applied or declined with reason | `git_subprocess.py:173` — `:(literal)` prefix applied to every path (not declined) | PASS |
| A11.1 | Range with a denylisted term only in a commit message is refused, masked, reword/amend healing | `tests/unit/features/chokepoints/test_push_denylist_scan.py::test_push_with_denylisted_term_only_in_a_commit_message_body_is_refused` — confirms `service.py` needed **zero** changes (`scan_objects` already generic over `ScannedObject.kind`) | PASS |
| A11.2 | Reconciliation shape (two commits, zero blobs) is an acceptance fixture | `tests/unit/infrastructure/test_git_object_reader.py::test_reconciliation_shape_two_commits_zero_blobs_still_yields_commit_bodies` | PASS |
| A11.3 | Annotated tag body scanned for a tag-ref push; lightweight tag yields nothing | `git_objects.py:_is_annotated_tag`; `::test_annotated_tag_push_yields_the_tag_bodys_own_object`, `::test_lightweight_tag_push_yields_no_tag_body_object` | PASS |
| A11.4 | Typed-error/degradation parity with the blob path — no silent skip | `_read_object_bodies` raises `GitObjectReadError` on batch failure, mirroring blob path; `::test_commit_body_batch_failure_raises_the_typed_error` | PASS |
| A11.5 | `sdd-gate-v3` atom's blob-only non-goal retired | **Deferred to T-043-51** (rc-1 CLOSURE memory window) per this task's own done-criterion — MEMORY-class write, correctly out of `alpha-2`'s write set | DEFERRED (as designed, not a gap) |
| A11.6 | Header/body boundary: only body/tag-body scanned, author/committer headers out of scope | `_split_object_body` splits on first `\n\n`; `::test_commit_body_object_never_carries_the_author_or_committer_identity` | PASS |
| A11.7 | Path-less objects never amnestied — fail-closed | `_read_object_bodies` never sets `prior_text`; `::test_commit_body_repeating_a_previously_published_commit_message_is_never_amnestied` | PASS |
| A12.1 | Carve-out with no rationale flagged by doctor/CI | `privacy_check.py:_check_baseline_exclude_rationale`, wired into `check_public_privacy` | PASS |
| A12.2 | `noreply@anthropic.com` local-part carved out; genuine same-domain address still fires | Already shipped by the Arm-B rider bug `privacy-baseline-noreply-local-part-not-carved-out`; **verified** at HEAD in `privacy_baseline.json`'s `email-address` pattern + counter-fixture in `test_public_assets.py` | PASS (verified, correctly not re-implemented) |
| A12.3 | Windows trailing-period escape no longer defeats the carve-out | `privacy_baseline.json` `windows-users-path.exclude_regex` gains `\.?`; fixture section "A12.3 — CR-6" in `test_public_assets.py` | PASS |
| A12.4 | Dotted-chain class gets a structural rule, narrowness preserved by counter-fixture | `internal-hostname.exclude_regex` → `(?:^|\.)[A-Z][A-Za-z0-9_]*`; fixture section "A12.4" with all-lowercase counter-fixture still firing | PASS |
| A12.5 | Every pattern stays single-line; version bump with extended `_header` rationale | `privacy_baseline.json` version 6→7, `_header.description` extended | PASS |
| A12.6 | `dadaia public doctor` reports `[ok] public-privacy`; self-scan sentinel green | Live run this session: `[ok] public-privacy` | PASS |
| A13.1 | Memory-dotfile classification encoded in code **and** stated as a rule | `gate_policy.py` module docstring + `_MEMORY_PREFIX` comment (bare-prefix, no carve-out, no SPEC override) | PASS |
| A13.2 | Fixture pins decided behaviour per phase | `tests/unit/features/spec_context/test_gate_policy.py::test_memory_dotfile_classifies_as_memory`, `::test_memory_dotfile_evaluate_allows_in_definition_and_closure`, `::test_memory_dotfile_evaluate_blocks_rule_a_outside_definition_and_closure`, `::test_memory_dotfile_evaluate_matches_a_non_dot_sibling_atom_across_every_phase` | PASS |
| A13.3 | 12 LINT-1 warnings enumerated, then eliminated at CLOSURE | V3 capture: `.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-17-fr13-v3-lint1-heading-capture.md` — 20 headings across 12 WARN-only atoms, named individually with proposed disposition, correctly handed to T-043-51 (MEMORY-class edit) | PASS (measured + handed off, elimination correctly deferred) |
| A14.1 | `--event picked` records reservation; `bugs status` surfaces picked-by | `core/models/bugs.py` (`BugEventKind.PICKED`), `cli/commands/bugs.py`, `features/bugs/service.py`; `tests/integration/cli/test_bugs_picked_event.py`, `tests/unit/features/bugs/test_service_picked_fold.py` | PASS |
| A14.2 | Repeated pick on open stream accepted and visible | `advance_coherence` PICKED branch never mutates `seen_reported`/`terminated`; NO-LOCKS fixtures in `test_bugs_picked_event.py` (both core and CLI) | PASS |
| A14.3 | Pick after terminal refused as incoherent | `advance_coherence`: `if bug_id in terminated: return <violation>` | PASS |
| A14.4 | Schema + fold + CLI in one change; older ledgers still fold | `bug-event-v1.schema.json` + fold + CLI all in commit `b001acdd`; `test_bug_event_schema.py::_picked` case | PASS |
| A15.1 | One appended event; 2026-07-01 line byte-unchanged | `specs/bugs/bugs.jsonl:897` appended (event=`archived`); line 202 (the 2026-07-01 `deferred` line) untouched — confirmed by diff of commit `b85302ac` (append-only, 1 line added) | PASS |
| A15.2 | Corrected disposition named with existing token + reason | Event reason states "'deferred' is ruled TERMINAL for this bug" — uses the existing `deferred`/`archived` vocabulary, no new token | PASS |
| A15.3 | No new disposition token anywhere | `BugEventKind` still has exactly 7 members (6 pre-existing + `picked` from FR14); no 8th token added by FR15 | PASS |
| A16.1 | LINT-1 imports shared implementation; no subprocess to a projected script | `doctor_memory.py` imports `features.specs.memory_lint` directly; `test_import_linter_ignore_cap.py` cap lowered 16→14 (features-no-infrastructure 7→6, features-no-subprocess 4→3) — the exact two edges LINT-1's subprocess call used to hold | PASS |
| A16.2 | Every `public/scripts/` script is a thin wrapper, structurally asserted | `tests/contract/test_public_scripts_thin_wrapper.py` — data-driven registry; `lint-memory-atoms.py` reduced from 598 to a near-zero-LOC shim | PASS |
| A16.3 | RO-5 duplication removed or CLOSURE states precisely why not | `estimate_tokens` duplication removed from `generate-memory-catalog.py`, imports the package canonical; remaining local logic (CLI surface, `generate_catalog`/`generate_index_md`) justified inline against `test_memory_catalog_render_contract.py`'s pinned signatures | PASS |
| A16.4 | "architectural exception it HOLDS" docstring note deleted with the exception | Confirmed via diff of `b12791cd` (module docstring's subprocess-import-edge note removed) and a live grep for "architectural exception" — zero hits | PASS |
| A17.1 | Symlinked destination refused at every write site, one fixture per site | `features/spec_context/service.py:400`'s `alive()` template copy (traced correctly past TASKS.md's stale write-set label — see note below); `tests/unit/features/spec_context/test_repo_agents_scaffold_symlink.py` — 4 sites: symlinked containing dir, non-dangling destination symlink, dangling destination symlink, repeated-call idempotency | PASS |
| A17.2 | Memory atom's existing claim becomes true | `public-asset-distribution` atom's "destination-file symlink refusal" claim now covers the repo-`AGENTS.md` site too | PASS |
| AB.1 | Missing segment dir produces explicit ERROR, never silent pass | `doctor_release.py:162-186` (`SPEC-DOC-004`), `doctor_structural.py:339-366` (`TREE-6`); `tests/unit/features/specs/test_doctor.py::test_missing_segment_directory_is_an_explicit_error_not_a_silent_skip` | PASS |
| AB.2 | Healthy segmented path unaffected | `::test_healthy_segmented_release_is_unaffected_by_the_missing_segment_check` | PASS |
| AB.3 | Flat release unaffected | `::test_flat_release_is_unaffected_by_the_missing_segment_check` | PASS |
| AB.4 | Stale "already reported by check 9" comment corrected | Both call sites' comments replaced with an accurate description of what SPEC-DOC-009 actually validates | PASS |
| AB.5 | Bug closed with `resolved` event carrying reproducing test + fix + suite result | `specs/bugs/bugs.jsonl:898` — `resolved` event names the RED test, the fix, and "full `tests/unit/features/specs/` suite (143 tests) passes" | PASS |

**Note on A17.1's write-set correction.** `T-043-21`'s commit message documents that the
actual write site is `features/spec_context/service.py:400`, not
`infrastructure/public_assets.py` as TASKS.md's write-set label named — traced to the
SPEC's own prose ("the repo-AGENTS.md destination write") and confirmed as the only
site in the package writing that template. This is an honestly-disclosed correction, not
a scope violation; no action required.

## RED-then-GREEN evidence (FR11, FR12, Arm-B rider)

- FR11 (T-043-15): the reader-seam extension and its 6+ new fixtures (header/body
  boundary, amnesty fail-closed, reconciliation shape) are new assertions against new
  code paths — no pre-existing green test exercised commit-body scanning before this
  commit, satisfying "RED first" by construction (the capability did not exist to make
  green).
- FR12 (T-043-16): the rationale-check function and its wiring are new; the "A12.3 —
  CR-6" and "A12.4" fixture sections in `test_public_assets.py` are titled as such and
  include explicit counter-fixtures proving the narrower/wider behavior split — the
  standard RED-first shape for a structural-rule change.
- Arm-B rider (T-043-22): the bug's `resolved` event evidence field explicitly names
  the RED test (`test_missing_segment_directory_is_an_explicit_error_not_a_silent_skip`)
  and states it "failed pre-fix (doc004==[] / tree6==[])" before the GREEN run.

## Retroactive test-stewardship verdict — deletion of `tests/unit/scripts/test_lint_memory_atoms.py`

**Verdict: RATIFIED.** The deletion in `2c0b9959` is coverage-preserving; no restoration
required.

**Scenario → surviving-counterpart map** (independently verified by this agent, not
taken on the implementer's word):

| Deleted test (pre-2c0b9959) | Surviving counterpart in `tests/unit/features/specs/test_memory_lint.py` |
|---|---|
| `test_agent_tier_property_absent_from_schema` | `test_agent_tier_property_absent_from_schema` (verbatim port) |
| `test_valid_atom_passes_and_exit_codes` | `test_valid_atom_with_allowlisted_heading_has_no_errors_or_warnings` + `test_main_end_to_end_exit_codes` (parametrized) |
| `test_structural_error_table` (parametrized) | Split into `test_forbidden_heading_is_an_error`, `test_unknown_heading_is_a_warning_not_an_error`, `test_duplicate_heading_is_an_error`, `test_missing_required_frontmatter_field_is_an_error`, `test_slug_mismatch_is_an_error` |
| `test_forbidden_heading_errors` | `test_forbidden_heading_is_an_error` |
| `test_wikilinks_broken_valid_and_product_subdir` | `test_wikilink_resolution_valid_and_broken` |
| `test_duplicate_errors_and_unknown_warns` | `test_duplicate_heading_is_an_error` + `test_unknown_heading_is_a_warning_not_an_error` |
| `test_lint_directory_scans_product_subdir_and_empty_is_noop` | `test_lint_directory_scans_toplevel_and_product_subdir_excludes_index` + `test_lint_directory_empty_is_a_noop` |
| `test_workspace_allowlist_load_and_merge` | `test_workspace_allowlist_extends_the_curated_set` + `test_workspace_allowlist_absent_file_is_empty` |
| `test_scaffold_atom_headings_are_allowlisted` | `test_scaffold_atom_headings_are_allowlisted` (verbatim port, added by `2c0b9959` — one of the 4 non-duplicate checks) |
| `test_memory_feature_template_headings_are_allowlisted` | `test_memory_feature_template_headings_are_allowlisted` (verbatim port, ditto) |
| `test_allowlist_content_pins` (parametrized) | `test_allowlist_content_pins` (verbatim port, ditto) |

Every one of the 11 deleted test functions (including 2 parametrized groups) has a
surviving counterpart. The reasoning matches the commit message's claim exactly: the
behavioral scenarios were already 1:1-ported in `b12791cd` (software-engineer's package
half); `2c0b9959` (ai-engineer's `public/` half) additionally deleted the now-pointless
script-level file and ported the four checks that validate real on-disk public assets
(frontmatter schema, scaffold headings, memory-feature template headings, allowlist
content) — those are the four this agent independently located at lines 236, 249, 269
and 347 of the surviving file. The deletion is a correct structural consequence of
moving the tested surface (the lint logic) out of the standalone script and into the
package: the deleted file loaded the script via `importlib.util.spec_from_file_location`
and asserted symbols the script no longer defines post-thinning — testing a surface that
no longer exists would itself be slop (a tombstone test).

## New-test quality audit (~2,100 test LOC added this segment)

**Net change:** 2,410 insertions / 721 deletions across 19 test files (per
`git diff --stat 600361f2..HEAD -- tests/`); 721 of those deletions are the retired
`test_lint_memory_atoms.py` (already dispositioned above) plus the `test_doctor_lint.py`
subprocess-fake removal (see below) — net growth is proportionate to the ~40 acceptance
ids this segment adds, not padding.

**Findings:**

- **No magic-mock inflation.** Zero `unittest.mock`/`MagicMock` usages introduced in any
  new test line (grepped across the full diff). The codebase's existing style —
  `monkeypatch` + small hand-written fakes/fixtures — is followed throughout.
- **No tautological assertions.** Zero `assert True` or equivalent no-op assertions in
  the diff.
- **Genuine mock-reduction, not addition.** `test_doctor_lint.py`'s rewrite (T-043-20)
  *deletes* `_FakeProcessRunner`/`_TimeoutProcessRunner` subprocess-mocking classes and
  replaces them with real on-disk fixture atoms exercised through the real
  `memory_lint` implementation — the opposite of slop, and exactly what the stewardship
  doctrine wants (testing real behavior, not a mocked stand-in).
- **Parametrization over copy-paste.** Every family with more than one similar case uses
  `@pytest.mark.parametrize` (e.g. `test_memory_dotfile_classifies_as_memory` over 2
  path forms, `test_allowlist_content_pins` over N allowlist files, `test_bugs_picked_event`'s
  terminal-field-omission matrix) rather than near-duplicate function bodies.
- **Intent/size declared at each addition point.** Every new test *section* (not every
  individual function, consistent with this repo's own convention of module- or
  section-level `Intent:`/`Size:` headers, RO-9) carries an explicit acceptance-id
  anchor and, in the majority of files, an explicit `Intent: CONTRACT`/`Intent: BUG`/
  `Intent: SENTINEL` + `Size: SMALL` declaration. One partial exception noted below.
- **Census-freeze (D12) held.** `git diff --stat 600361f2..HEAD -- tests/e2e/` is empty —
  zero e2e tests added or touched this segment.
- **Tests pin contract, not implementation trivia.** Spot-checked FR11's and FR14's test
  files: assertions target observable outcomes (decision.allowed, refusal message
  content, exit codes, `bugs status` surfaced state) rather than private internals.

**One LOW finding (non-blocking):**
`tests/integration/infrastructure/test_git_subprocess.py::test_commit_paths_ignores_operator_pre_staged_unrelated_content`
(A10.2's real-git integration fixture) carries a section-header comment naming the
acceptance id but no explicit `Intent:`/`Size:` token pair, unlike most other new
sections this segment. It is unambiguous by directory placement (`tests/integration/`)
and its acceptance-id anchor, so it is not SCAFFOLD-slop, but it falls slightly short of
this segment's own otherwise-consistent declaration style.
**Fix recommendation:** add a one-line `Intent: CONTRACT — v0.4.3 A10.2. Size: INTEGRATION
(real git repo).` header alongside the existing section comment; no behavioral change,
no verdict impact — carry as a trivial polish item in `alpha-3` or `rc-1`, not a blocker.

## Full suite and doctor run (this session, live)

- `pytest -p no:cacheprovider -m 'not quarantine' -n auto`: **2407 passed, 3 skipped**
  (skips are platform-gated: Windows icacls, Windows telemetry lock, no non-loopback
  IPv4 — none are alpha-2-relevant), 0 failed, 43.71s wall.
- `dadaia doctor`: **"All invariants OK — workspace is healthy."**
- `dadaia specs doctor --context dadaia-workspace`: **0 errors, 5 warnings** — all 5 are
  pre-existing and out of `alpha-2`'s scope: 12 `LINT-1` heading-atom warnings (correctly
  measured at T-043-17/A13.3 and handed to T-043-51 for elimination, per SPEC/PLAN) plus
  3 legacy `SPEC-DOC-027`/`SPEC-DOC-036` archive-naming warnings unrelated to this
  segment's FRs.
- `dadaia public doctor`: **all `[ok]`** — `public-privacy`, `entities-derivation` (9
  Personas ↔ 9 core sub-agents), `model-resolution`; every projected asset `[ok]`;
  `[foreign]` lines are correctly-excluded operator/consumer-repo files, not findings.

## Task trace verification

- `T-043-13` … `T-043-22` all `[x]` in `specs/releases/v0.4.3/TASKS.md`; `T-043-23`
  correctly `[ ]` (this review, per dispatch instruction, does not flip it).
- Every task's `chore(tasks): start T-043-NN` reservation commit is present in
  `git log 600361f2..HEAD` immediately preceding that task's implementation commit —
  the full ordered sequence (`9c77e921`→`69214f14`, `3057f806`→`24a349f5`,
  `a2969910`→`5479b827`, `4cf12127`→`d4658ae5`, `ca8f4bd1`→`9dac383d`,
  `c172ee6a`→`b001acdd`/`6fb8674d`, `77aa7bd8`→`b85302ac`, `e31f6857`→`b12791cd`,
  `8bff0a90`→`bb2a5959`, `eafbc2c9`→`29d0f9d0`, then `2c0b9959` as ai-engineer's public/
  half with no separate reservation commit — consistent with T-043-20 being a single
  task split across two owners under one reservation) — confirmed at HEAD.
- Bug `specs-doctor-segment-router-silent-skip`: `reported` event at
  `specs/bugs/bugs.jsonl:892` (2026-08-17T14:14:50Z, product-engineer) and `resolved`
  event at `:898` (2026-08-17T17:02:00Z, software-engineer) with full resolution
  evidence (reproducing test name, fix description, suite result) — confirmed.

## Decisions required (routed to project-manager)

1. **Security-reviewer coverage of the gate/baseline delta (FR11, FR12) is outstanding.**
   PLAN §5's `alpha-2` exit criteria requires it explicitly; no covering handoff exists
   at HEAD. This is the one remaining precondition before T-043-23 can flip `[x]`, per
   this task's own dispatch instructions.
2. The LOW documentation-polish finding above (missing `Intent:`/`Size:` header on one
   integration fixture) may be actioned at `alpha-3` or `rc-1`; it does not block this
   segment's QA verdict.

No CRITICAL/HIGH findings. No test-deletion or demotion beyond the one ratified above.
No secrets, tokens, or credential material observed in any reviewed diff, test fixture,
or bug-ledger entry.


---

# Appendix B — QA r2 addendum (REQUEST_CHANGES, superseded by r3)

# QA re-check addendum — v0.4.3 alpha-2 close (T-043-23), round 2

**Reviewer:** qa-engineer (this session) · **Date:** 2026-08-17
**Prior round:** APPROVED at tip `2c0b9959` (artifact
`v0.4.3-alpha-2-qa-review.md`, handoff
`2026-08-17T172854Z-qa-engineer-T-043-23-alpha-2-close.handoff.json`) — QA verdict on
every acceptance id held; segment exit was left gated on outstanding
`security-reviewer` coverage of the FR11/FR12 delta.
**Trigger for this round:** `security-reviewer` returned `REJECTED` at
`2026-08-17T173112Z-security-reviewer-v0.4.3-alpha-2-delta.handoff.json` (2 blocking
findings: HIGH — push refused by the pushed-range denylist scan itself; MEDIUM — FR12
carve-out over-permissive), plus 6 LOW findings and 3 INFO notes. `software-engineer`
landed 6 remediation commits, new tip `ce47f1ea`, delta `2c0b9959..ce47f1ea`
(+619/−55, 12 files: 6 production, 6 test).
**Scope of this addendum:** does not re-derive the full alpha-2 acceptance table —
appends to it. Verifies (1) no A9.x–A17.x id regressed at `ce47f1ea`; (2)
test-stewardship audit of the ~438 new test LOC; (3) full suite + doctors, live; (4)
adjudicates the carried-forward LOW (missing `Intent:`/`Size:` header); (5) independently
re-executes the real push-gate chokepoint the security review's HIGH finding was based
on, against the new tip.

## Verdict

**QA verdict: REQUEST_CHANGES.**

Every A9.x–A17.x acceptance id this agent owns still holds functionally at `ce47f1ea`
(spot-check table below) and the new-test stewardship audit finds no slop. But this
round's independent re-execution of the real pre-push chokepoint proves the
security-reviewer's HIGH blocking finding is **not resolved at `ce47f1ea`** — and the
object count it blocks on has grown from 2 to 3. This is a hard blocker under
`DADAIA.md` §5/§6 (a `qa-engineer` QA-only `APPROVE` never substitutes for the
`security-reviewer` coverage PLAN §5's alpha-2 exit criteria requires, and a delta that
cannot pass its own pre-push gate cannot be pushed regardless of any reviewer's
verdict). Routed to `project-manager` to relay back to `software-engineer` for a second
rework pass, then a fresh `security-reviewer` re-review of the new tip.

## HIGH — the pushed range is still refused by its own pre-push denylist scan at `ce47f1ea` (worsened: 2 → 3 objects)

**Independently re-executed, read-only, no push**, the exact real chokepoint the
`2026-08-17T173112Z-security-reviewer-v0.4.3-alpha-2-delta` handoff's HIGH finding was
based on, now pointed at the new tip:

```
echo "refs/heads/develop <ce47f1ea-full-sha> refs/heads/develop <df3b1a93-full-sha>" \
  | dadaia ci push-gate-check
```

```
[pre-push] BLOCKED: the pushed range publishes 3 object(s) carrying a denylisted term
  dadaia_workspace/infrastructure/data/privacy_baseline.json:18 (blob b904d2f74386) — masked term 'S…l' (baseline pattern 'internal-hostname')
  tests/unit/test_public_assets.py:758 (blob a285204caee1) — masked term 'S…l' (baseline pattern 'internal-hostname')
  tests/unit/core/models/test_bugs_picked_event.py:253 (blob 0c4dea315737) — masked term '1…3' (baseline pattern 'ipv4-literal')
```

**Root cause — the same class of mistake the security review already named, now
repeated a second time.** `software-engineer`'s remediation commit `f1a1ef93`
correctly narrowed the `internal-hostname` `exclude_regex` at HEAD (`^workspace\.local$
|(?:^|\.)[A-Z][A-Za-z0-9_]*\.home$`, requiring the `.home` suffix — verified against
the security review's MEDIUM finding below) and correctly re-authored the module's own
test fixtures to compose hostname literals at runtime (`_hostname_literal()`) so no
literal is contiguous in the **current** tracked blob. That is a real, correct fix of
the MEDIUM finding's *content*. But git history was never rewritten: commit `d4658ae5`
(pre-existing, from before this rework round, `alpha-2`'s original FR12 commit) still
carries the file's PRE-narrowing text verbatim — the exclude-rationale prose in
`privacy_baseline.json`'s own `_header.excludes` array, and the un-composed
`"SomeClass.i…l()"` literal in `test_public_assets.py`'s A12.4 counter-fixture —
and that commit is still reachable inside the pushed range `600361f2..ce47f1ea`
(confirmed: `git cat-file -t d4658ae5` → `commit`; `git rev-list --objects
600361f2..ce47f1ea | grep 0c4dea315737` → found).

Because the push-gate scanner evaluates every object in the range against the
**currently loaded** baseline regex (not whatever regex existed when that object was
authored), narrowing the exclude regex at HEAD makes MORE historical content newly
non-excluded, not less: `d4658ae5`'s old `"SomeClass.i…l()"` text does not end in
`.home`, so under the new narrower rule it now fails the carve-out and fires — a
**brand-new** blocking object (`privacy_baseline.json:18`, blob `b904d2f74386`) that
was not blocking before this remediation round, joining `test_public_assets.py`'s own
equivalent pre-fix blob (`a285204caee1`, same root cause, same commit) and the
already-known `test_bugs_picked_event.py` IPv4-literal blob (`0c4dea315737`, from
`b001acdd`) that the original security review named and whose companion fix
(`6fb8674d`) was likewise never squashed into it.

**The security review's own fix_recommendation (a) — "rewrite history so the pre-fix
blob is never published: `git rebase -i 600361f2` and squash/fixup `6fb8674d` into
`b001acdd`... Then re-run `dadaia ci push-gate-check` over the new tip and request a
fresh security verdict" — was not executed.** None of the 6 remediation commits touch
history; `git log --oneline 600361f2..ce47f1ea` still shows `b001acdd` and `6fb8674d`
as two separate commits, unchanged, in their original order. No evidence in the
6 commit messages or diffs indicates `dadaia ci push-gate-check` was re-run before this
round was considered complete — had it been, this exact block would have been visible.

**Fix recommendation.** `software-engineer` must, in order: (1) `git rebase -i
600361f2` on `feature/0.4.3` and squash/fixup `6fb8674d` into `b001acdd` so the
pre-fix IPv4-literal blob is never published; (2) squash/fixup the FR12-narrowing
content change into `d4658ae5` itself (or otherwise rewrite `d4658ae5` so its tree
never carries the un-narrowed exclude-rationale prose or the un-composed
`"SomeClass.i…l()"` literal) so neither `privacy_baseline.json:18` nor
`test_public_assets.py:758`'s pre-fix blob survives in history; (3) re-run `dadaia ci
push-gate-check` locally against the rewritten tip and confirm zero blocked objects
before declaring the rework complete; (4) request a fresh `security-reviewer` handoff
against the new tip sha, per the original review's own closing instruction. This is
the single blocking item for this round.

## MEDIUM finding — content-level fix verified correct (independent re-derivation)

Independently re-derived (not taken on the commit message's word) against the shipped
`internal-hostname` pattern at `ce47f1ea`:

| value | old `exclude_regex` (unanchored, any uppercase-initial chain) | new `exclude_regex` (`.home`-anchored) |
|---|---|---|
| `Path.home` / `pathlib.Path.home` | excluded | still excluded (PASS — regression guard) |
| `SomeClass.home` (brand-new `.home` chain) | excluded | still excluded (PASS — widening within class holds) |
| `SomeClass.i…l` (brand-new, non-`.home`) | excluded (the bug) | **fires** (PASS — MEDIUM fixed at content level) |
| `Marcos-MacBook-Pro.l…l`, `DESKTOP-AB12CD.l…l`, `vpn.Acme.i…l`, `MYNAS.l…n` (the security review's 4 verified bypass values) | excluded (the bug) | **fires** (PASS — all 4 confirmed via the new parametrized test, see stewardship notes) |
| `db1.i…l`, `fileserver.c…p`, `build-agent.l…n` (pre-existing narrowness counter-fixtures) | fires | still fires (PASS — no regression) |

The regex-level fix is correct and complete. The finding is only outstanding because of
the HIGH history-rewrite gap above — the corrected regex cannot help the pushed
range while the pre-narrowing blob is still in it.

## Spot-check table — alpha-2 acceptance ids touched by the remediation delta

Every id below re-verified against the executed tree at `ce47f1ea`, independent of the
prior round's evidence (re-run, not re-cited).

| id | Prior round | This round — regression check | Evidence at `ce47f1ea` |
|---|---|---|---|
| A9.1 | PASS | **HOLDS** — `os.path.isabs` filters at the two source functions are unchanged; the probe-boundary filter is now the stricter `_is_fully_qualified` (superset of the old check, POSIX path untouched) | `python_env.py:268-289` (`_is_fully_qualified`), `:497` (call site); `tests/unit/infrastructure/test_python_env.py::test_is_fully_qualified_rejects_a_windows_drive_relative_path`, `::test_is_fully_qualified_accepts_a_windows_drive_qualified_path`, `::test_is_fully_qualified_accepts_a_posix_absolute_path`, `::test_is_fully_qualified_rejects_a_posix_relative_path`, `::test_resolve_child_venv_interpreter_never_probes_a_windows_drive_relative_pyvenv_value` — 5 new tests, all pass |
| A9.2 | PASS | **HOLDS** — timeout/DEVNULL wiring untouched by this delta | `test_interpreter_version_probe_passes_a_bounded_timeout_and_devnull_stdin` still green |
| A9.3 | PASS | **HOLDS** — `_is_fully_qualified` is a strict superset filter (rejects the same relative paths PLUS the new Windows drive-relative case); no absolute-path candidate's control flow changed | full bootstrap suite unmodified and green |
| A10.1 | PASS | **HOLDS** — `commit_paths`'s own A10.1 exit-check untouched; this delta additionally extends the SAME defence to `_stage_files_safe`'s sibling seam (previously uncovered) | `git_subprocess.py:44-49,90-95` (new exit checks); `test_stage_files_safe_raises_on_a_failed_git_add_dash_u`, `::test_stage_files_safe_raises_on_a_failed_git_add_for_untracked_paths` |
| A10.2 | PASS | **HOLDS** — `_commit`'s pathspec-scoped commit logic untouched; a new CWE-367 docstring note documents (not redesigns) the theoretical TOCTOU, per the security review's own accepted alternative | `git_subprocess.py:108-124` docstring addition only, no behavior change; pre-existing `test_commit_paths_applies_literal_pathspec_magic_to_add_and_commit` + integration fixture still green |
| A10.3 | PASS | **HOLDS** — `:(literal)` wrapping on `commit_paths` untouched; the same wrapping is newly extended to `_stage_files_safe`'s untracked-path `git add` (previously unwrapped) | `git_subprocess.py:90` (`literal_safe = [f":(literal){p}" ...]`); `test_stage_files_safe_applies_literal_pathspec_magic_to_untracked_paths` |
| A11.1–A11.4, A11.6, A11.7 | PASS | **HOLDS** — `_split_object_body`, `_read_object_bodies`'s typed-error path, and the fail-closed amnesty logic are all untouched; the only change is the new `_mergetag_bodies`/`_unfold_mergetag_blocks` addition, which appends to `body` rather than replacing it | full `test_git_object_reader.py` suite green, including all pre-existing A11.x fixtures |
| A11.5 | DEFERRED (as designed) | **UNCHANGED** — still correctly deferred to T-043-51 (MEMORY-class, out of `alpha-2`'s write set) | no change |
| A11.new — mergetag body scan (FR11 LOW remediation, not a pre-existing alpha-2 id but tracks its rework) | n/a | **NEW, PASS** — the previously-documented header-region non-goal now covers the specific mergetag sub-case: a merge-of-a-signed-tag's own message body reaches the matcher; a real, isolated `tmp_path` fixture (not the tracked repo) proves both the positive case and a negative twin | `git_objects.py:192-244` (`_MERGETAG_PREFIX`, `_unfold_mergetag_blocks`, `_mergetag_bodies`); `test_mergetag_embedded_tag_body_reaches_the_matcher`, `::test_mergetag_absent_is_unaffected` |
| A12.1, A12.2, A12.3, A12.6 | PASS | **HOLDS** — untouched by this delta | not re-diffed this round (no lines touched) |
| A12.4 | PASS | **NARROWED, content-verified PASS** — see the MEDIUM section above; still correctly excludes `Path.home()`/`pathlib.Path.home()`, still correctly fires on the pre-existing all-lowercase counter-fixtures, and now ALSO correctly fires on the 4 previously-bypassed uppercase-initial real-hostname shapes | `privacy_baseline.json` v7→v8; `test_internal_hostname_dotted_chain_structural_rule_still_excludes_path_home` (updated), `::test_internal_hostname_dotted_chain_structural_rule_excludes_a_brand_new_home_chain` (renamed/narrowed), `::test_internal_hostname_uppercase_chain_no_longer_excluded_outside_the_home_class` (new), `::test_internal_hostname_dotted_chain_structural_rule_preserves_narrowness[…]` (unchanged, 3 cases), `::test_internal_hostname_uppercase_initial_real_hostname_still_fires[…]` (new, 4 cases — the exact 4 bypass values named in the security handoff), `::test_internal_hostname_dotted_chain_counter_fixture_fires_through_the_doctor` (updated), `::test_internal_hostname_uppercase_initial_real_hostname_fires_through_the_doctor` (new) — 16 test functions total, all pass |
| A12.5 | PASS | **HOLDS, version re-bumped** — baseline version 7→8 this round (was 6→7 for A12.5 itself); `test_baseline_v7_header_and_single_line_patterns` updated to assert `version == 8` and still asserts the `_header.excludes` rationale content | `privacy_baseline.json` `_header.version: 8`; test updated in place, passes |
| A13.x, A15.x, A16.x | PASS | **UNCHANGED** — zero lines touched by this delta | not re-diffed this round (no lines touched) |
| A14.1–A14.4 | PASS | **HOLDS, widened** — the `picked` event's schema/fold/CLI wiring is untouched; `BugEvent.redact()` now additionally scrubs `release`/`reason` (a genuine widening of I9's redaction coverage, not a regression) | `bugs.py:280-311`; `test_i9_redaction_scrubs_release_and_reason_fields` (new); pre-existing `test_i9_picked_event_redaction_scrubs_free_text_leaves_structured_fields_alone` still green |
| A14 gap noted this round (not blocking) | n/a | The security review's FR14 fix_recommendation had TWO parts: (a) add a `pattern` to the `release` schema property + CLI enforcement, (b) widen `redact()`. Only (b) landed — `dadaia_workspace/public/schemas/bugs/bug-event-v1.schema.json` is untouched by this delta (confirmed: empty diff), `release` still carries no `pattern` constraint | Non-blocking LOW-level gap; carry forward, not this round's blocker |
| A17.1 | PASS | **HOLDS, hardened** — the two-tier symlink-refusal check-then-copy is replaced with a single atomic `os.open(O_CREAT\|O_EXCL\|O_NOFOLLOW)` per the security review's own recommendation; all 4 pre-existing fixture scenarios (symlinked containing dir, non-dangling dest symlink, dangling dest symlink, idempotency) still pass unmodified, plus one new fixture asserting the atomic-open call shape | `service.py:409-424`; `tests/unit/features/spec_context/test_repo_agents_scaffold_symlink.py` — all pre-existing tests green + `test_repo_agents_write_uses_a_single_atomic_open_call` (new, `os.open` spy, asserts `O_CREAT\|O_EXCL\|O_NOFOLLOW` all set) |
| A17.2 | PASS | **HOLDS** — memory atom claim unaffected by this delta | no change |
| AB.1–AB.5 | PASS | **HOLDS** — zero lines touched by this delta | not re-diffed this round (no lines touched) |

**No acceptance id regressed.** Every id this agent owns still holds functionally at
`ce47f1ea`. The blocking issue is orthogonal to acceptance-id correctness — it is the
mechanical pre-push gate on the range as a whole.

## Test-stewardship audit — ~438 new test LOC (6 files, `git diff --numstat 2c0b9959..ce47f1ea -- tests/`)

| File | +/− | New test functions |
|---|---|---|
| `tests/unit/core/models/test_bugs_picked_event.py` | +25/−0 | 1 |
| `tests/unit/features/spec_context/test_repo_agents_scaffold_symlink.py` | +42/−0 | 1 |
| `tests/unit/infrastructure/test_git_object_reader.py` | +90/−0 | 2 |
| `tests/unit/infrastructure/test_git_subprocess_unit.py` | +84/−0 | 3 |
| `tests/unit/infrastructure/test_python_env.py` | +69/−0 | 5 |
| `tests/unit/test_public_assets.py` | +128/−29 | 4 (+1 helper `_hostname_literal`, +1 renamed/narrowed, others updated in place) |
| **Total** | **+438/−29** | **16 new test functions** |

**Findings:**

- **No magic-mock inflation.** Zero `unittest.mock`/`MagicMock` in the new lines
  (grepped across the full delta). Fixtures use `monkeypatch`, small hand-written fakes
  (`fake_run`), and — for the mergetag and TOCTOU tests — REAL git objects in an
  isolated `tmp_path` repo or a real `os.open` spy that passes through to the real
  syscall. This is the stronger end of the spectrum, not the weaker.
- **No tautological assertions, no e2e-census violation** (`git diff --stat
  2c0b9959..ce47f1ea -- tests/e2e/` is empty).
- **Every new section carries Intent/Size + acceptance-id/CWE anchoring** consistent
  with alpha-2's own established convention — e.g. `test_python_env.py`'s new section
  header states `Size: SMALL` / `Intent: CONTRACT`, `test_git_subprocess_unit.py`'s
  states `Size: SMALL` / `Intent: CONTRACT`, and every new function's docstring
  explicitly cites the CWE and the originating security handoff by filename/timestamp
  — traceable review provenance, not decorative.
- **Parametrization used correctly, not copy-paste.** The 4 verified-bypass hostname
  values (`Marcos-MacBook-Pro.l…l`, `DESKTOP-AB12CD.l…l`, `vpn.Acme.i…l`,
  `MYNAS.l…n`) are one `@pytest.mark.parametrize`d function, not 4 near-duplicate
  bodies — this is the exact "four hostname bypass RED tests" named in this round's
  dispatch, confirmed as a single parametrized function
  (`test_internal_hostname_uppercase_initial_real_hostname_still_fires`), each case
  independently verified matching and correctly non-excluded.
- **The mergetag fixture is genuine RED-then-GREEN, not a mock.** It builds a REAL
  git commit object (`git hash-object -t commit -w --stdin`) in an isolated `tmp_path`
  repo, splicing a real tag's header shape onto a real commit's tree/parent lines —
  no GPG key needed, no mocking of the object reader itself. The negative twin
  (`test_mergetag_absent_is_unaffected`) proves the extraction is a no-op on the
  ordinary path, correctly bounding the new code's blast radius.
- **The `os.open` spy test is a genuine wiring proof, not a magic mock.** It patches
  `os.open` at the shared module level but the spy PASSES THROUGH to the real syscall
  (`return real_open(...)`) and only RECORDS calls targeting the exact destination
  path — every other caller (including pytest's own teardown) is unaffected. This is
  the correct pattern for asserting a specific flag combination on a specific call
  without disabling the real filesystem operation.
- **No test deletion or demotion this round.** All 16 additions are net-new or narrow
  in-place edits to existing test bodies (renamed to match the narrowed contract);
  nothing was removed except the 29 deleted lines, all of which are the OLD (pre-narrow)
  literal forms in `test_public_assets.py` being replaced by their `_hostname_literal`-
  composed equivalents — a like-for-like content update, not a coverage reduction
  (confirmed: test COUNT in that file only grew, from the diff's `+def test_` count).
- **No secrets in the new test content itself.** Every hostname/IP-shaped literal in
  the new fixtures is either an RFC-reserved documentation form (`t@example.com`) or is
  now composed at runtime via `_hostname_literal()`/f-strings specifically so it is
  never a contiguous literal in the tracked blob — this is architecturally sound
  practice. It is precisely the *historical, pre-this-practice* blobs (§HIGH above)
  that remain the open problem, not anything newly authored this round.

**No CRITICAL/HIGH/MEDIUM/LOW test-quality findings this round.** The new-test
stewardship verdict is clean; the round's blocker is a git-history/push-range issue,
not a test-authorship issue.

## LOW finding adjudication — carried forward, unchanged, still non-blocking

`tests/integration/infrastructure/test_git_subprocess.py`'s
`test_commit_paths_ignores_operator_pre_staged_unrelated_content` (A10.2's real-git
integration fixture) still has no explicit `Intent:`/`Size:` header pair. **This file
is untouched by the remediation delta** (confirmed: absent from `git diff --numstat
2c0b9959..ce47f1ea -- tests/`, and the function body at line 181 is byte-identical to
the prior round). The finding is neither fixed nor worsened this round — it remains a
trivial, non-blocking documentation-polish item, exactly as adjudicated last round:
does not block alpha-2's close, safe to carry into `alpha-3`/`rc-1`.

## Secondary observation (not this round's blocker, worth noting for the rework pass)

The security review's LOW FR10 finding also asked, as a secondary item, to "log (not
suppress) the `GitSyncError`" at `service.py`'s `commit_paths` call site
(`contextlib.suppress(Exception)` around line 457). This is still present, unaddressed,
in the same form as the original review found it. Non-blocking on its own (it was a
secondary note inside a LOW finding whose primary ask — hardening
`_stage_files_safe` — was correctly implemented), but worth folding into the same
rework pass since the file is already being touched.

## Full suite and doctor run (this session, live, at `ce47f1ea`)

- Targeted spot-check (`test_python_env.py`, `test_git_subprocess_unit.py`,
  `test_git_object_reader.py`, `test_public_assets.py`, `test_bugs_picked_event.py`,
  `test_repo_agents_scaffold_symlink.py`): **169 passed**, 0 failed.
- `pytest -p no:cacheprovider -m 'not quarantine' -n auto` (full suite): **2425 passed,
  3 skipped**, 0 failed, 70.02s wall. (Prior round: 2407 passed / 3 skipped — the +18
  is the 16 new functions above plus 2 net-new from the `test_public_assets.py`
  in-place edits; same 3 platform-gated skips as last round — Windows icacls, Windows
  telemetry lock, no non-loopback IPv4 — none alpha-2-relevant.)
- `dadaia doctor`: **"All invariants OK — workspace is healthy."**
- `dadaia specs doctor --context dadaia-workspace`: **0 errors, 5 warnings** — same 5
  as last round (12 `LINT-1` heading warnings collapsed into one block, correctly
  deferred to T-043-51, plus 3 legacy `SPEC-DOC-027`/`SPEC-DOC-036` archive-naming
  warnings unrelated to this segment).
- `dadaia public doctor`: **`[ok] public-privacy`**, `[ok] entities-derivation` (9
  Personas ↔ 9 core sub-agents), `[ok] model-resolution`; **zero `[drift]` lines** —
  the security review's INFO finding ("3 public assets are staged-drifted") is
  resolved; the projected surface now matches source.
- **`dadaia ci push-gate-check` against the real range `df3b1a93..ce47f1ea`
  (read-only, no push): BLOCKED, 3 objects.** See §HIGH above — this is the round's
  actual gating result, independent of the internal test/doctor suite all being green.

## Decisions required (routed to project-manager)

1. **Blocking.** The security-reviewer HIGH finding (pushed-range denylist refusal) is
   not resolved at `ce47f1ea` and has grown from 2 to 3 blocking objects. Dispatch
   `software-engineer` for a second rework pass: rebase/squash the two pre-fix blobs
   out of history (`b001acdd`+`6fb8674d`, `d4658ae5`'s FR12 content), verify locally
   with `dadaia ci push-gate-check` before declaring done, then request a fresh
   `security-reviewer` re-review against the new tip sha — exactly the closing
   instruction the original security handoff already gave.
2. Non-blocking, fold into the same rework pass: (a) `bug-event-v1.schema.json`'s
   `release` property still has no grammar `pattern` (FR14 fix_recommendation part
   (a), not landed); (b) `service.py:457`'s `contextlib.suppress(Exception)` around
   `commit_paths` still swallows the diagnostic (FR10 secondary observation, not
   landed).
3. Non-blocking, carry to `alpha-3`/`rc-1` at will: the LOW `Intent:`/`Size:` header
   gap on `test_commit_paths_ignores_operator_pre_staged_unrelated_content`,
   unchanged from last round.

No new secrets, tokens, or credential material observed in any reviewed diff, test
fixture, or bug-ledger entry this round. No test-deletion or demotion this round.


---

# Appendix C — QA r3 addendum (final: APPROVED)

# QA re-check addendum — v0.4.3 alpha-2 close (T-043-23), round 3

**Reviewer:** qa-engineer (this session) · **Date:** 2026-08-17
**Trigger:** dispatcher relay presenting new empirical evidence against this agent's
own round-2 single blocking (HIGH) finding — that the granular `feature/0.4.3` push
range is refused by the real pre-push denylist chokepoint. The relay's claim: history
rewrite is not the sanctioned remediation in this workspace; the operator-accepted ship
shape is squash-publication at the `feature/{M.m.p}` → `develop` merge, so the granular
range this agent scanned in round 2 is never the range that is actually pushed.

**This addendum does not take the relay's claim on say-so.** Every factual assertion in
it was independently re-derived against the real repository and the real chokepoint
before this round's verdict changed, consistent with this agent's own standing
practice ("independently verified by this agent, not taken on the implementer's word",
round 1).

## What was independently verified this round

**1. The squash-publication precedent is real, not asserted.** `git log -1 6e1f9c63`
shows a single-parent commit (`git cat-file -p 6e1f9c63 | grep '^parent' | wc -l` → 1)
whose own subject line reads `feat: v0.4.2 — residual-convergence (squash ship of
feature/0.4.2)`. A 40-commit sample of `develop`'s own history
(`git log --pretty=format:'%h %p' -40 develop`) is single-parent throughout —
consistent with every prior `feature/{M.m.p}` → `develop` merge in this repo's actual
history having been executed as a squash, never a history-preserving merge. `6e1f9c63`
also appears in the live push-gate-check's own "APPROVE shas on disk" list, confirming
it as a real, already-pushed, already-approved commit — not a hypothetical.
`dadaia-gitflow`'s own "Reconciliation merge" section independently documents the same
v0.4.2 squash-ship episode by name.

**2. The dry-run's tree claim is correct.** Reproduced independently:
`git commit-tree ce47f1ea^{tree} -p df3b1a93 -m x` → a synthetic commit whose tree
(`git rev-parse <synthetic>^{tree}`) is byte-identical to `git rev-parse
ce47f1ea^{tree}` (`a50e5b14019194e16f114fd9a8f685b5aa1f88ff` both sides) — i.e. a
squash of `feature/0.4.3` onto `develop`'s current tip would publish exactly `ce47f1ea`'s
final file state, nothing more and nothing less. (This agent's own synthetic commit sha
differs from the dispatcher's — expected, since `commit-tree` embeds the committer
timestamp; the TREE match is the load-bearing fact, and it matches.)

**3. The synthetic squash range is clean under the real denylist scanner —
independently re-run, not re-cited.** `git rev-list --objects
df3b1a93..<synthetic-sha> | wc -l` → 114 objects newly reachable; grepped for both
offending blob shas (`0c4dea315737`, the FR14 `test_bugs_picked_event.py` IPv4 literal,
and `b904d2f74386`/`a285204caee1`, `privacy_baseline.json`/`test_public_assets.py`'s
pre-narrowing text) — **neither appears**. Feeding that same synthetic range to the
real `dadaia ci push-gate-check` chokepoint (read-only, no push) produces **zero**
denylist-block lines; the only refusal is the structurally inherent "no
security-reviewer APPROVE covers this delta" — which cannot exist for a commit that was
only just synthesized locally, and is the same precondition round 1 and round 2 already
named as the one outstanding item outside this agent's scope.

**Conclusion: the round-2 HIGH finding is retracted.** It was a real, technically
accurate observation about the GRANULAR `feature/0.4.3` commit range — but that range is
not, and under this workspace's actual gitflow practice never will be, the range that is
pushed to `develop`. The publishable artifact (the eventual squash commit at ship,
milestone (b)) is proven clean by direct reproduction, not by removing round 2's
evidence — round 2's evidence about the granular range was correct; it was simply the
wrong range to gate this segment's QA verdict on.

**Secondary correction, independent of the relay.** Re-reading `dd-release-implement`'s
own Review/QA gate cadence table (already loaded in this agent's context both rounds):
"End of each `alpha-N` | `qa-engineer` only ... | a qa-gated commit on the branch — **no
push/PR/merge/CLOSURE**." The pre-push chokepoint does not even apply at an `alpha-N`
close — it is a ship-time (`rc-N`, milestone (b)) mechanism. Round 2 evaluated the wrong
lifecycle event for this task's actual scope on top of evaluating the wrong git range;
both errors point the same direction and are now corrected together.

## What is unaffected by this correction

- Every A9.x–A17.x acceptance-id spot-check from round 2 — unaffected, still PASS.
- The test-stewardship audit of the ~438 new test LOC — unaffected, still clean.
- The MEDIUM finding's content-level fix (the `.home`-anchored `exclude_regex`) —
  unaffected, still independently verified correct.
- The two non-blocking LOW gaps (FR14 schema `pattern` not landed; FR10
  `contextlib.suppress` not converted to logging) — unaffected, still open, still
  non-blocking, still worth folding into a future pass at the implementer's discretion.
- The carried-forward LOW header finding on
  `test_commit_paths_ignores_operator_pre_staged_unrelated_content` — unaffected, still
  unchanged, still non-blocking.
- The full suite (2425 passed / 3 skipped / 0 failed) and all three doctors
  (`dadaia doctor` healthy, `specs doctor` 0 errors/5 pre-existing warnings, `public
  doctor` all `[ok]`/zero drift) — unaffected, all still green from round 2's live run.

## Verdict

**QA verdict: APPROVE** on every acceptance id this agent owns (A9.x–A17.x, AB.1–AB.5),
matching round 1's original posture. Alpha-2 segment exit is still gated on one item
outside this agent's write scope — a fresh `security-reviewer` re-review of the
`ce47f1ea` content delta (the prior `security-reviewer` handoff `REJECTED` the OLD tip
`2c0b9959`; no verdict yet covers the new tip's actual code changes) — but that gate is
now understood correctly as "awaiting a fresh review", not "blocked by an unresolved
defect in the publishable artifact". This is the same shape round 1 already described
before round 2's (now-retracted) HIGH finding intervened.

## Decisions required (routed to project-manager)

1. Dispatch `security-reviewer` for a fresh diff-based review of `ce47f1ea`'s content
   delta (the 6 remediation commits) — content-level, not history-level; no rebase or
   history rewrite is required or expected. The MEDIUM (FR12 carve-out) and the 6 LOW
   findings from the `2026-08-17T173112Z` review are each independently confirmed fixed
   or explicitly adjudicated non-blocking in this and the prior round's addenda.
2. Non-blocking, at the implementer's discretion for a future pass: FR14 schema
   `pattern` on `release` (part (a) of that finding, not landed); FR10's
   `contextlib.suppress(Exception)` around `commit_paths` in `service.py:457` (secondary
   observation, not landed).
3. Non-blocking, carry to `alpha-3`/`rc-1` at will: the LOW `Intent:`/`Size:` header gap
   on `test_commit_paths_ignores_operator_pre_staged_unrelated_content`.

No CRITICAL/HIGH findings remain. No secrets, tokens, or credential material observed in
any reviewed diff, test fixture, or bug-ledger entry across all three rounds.
