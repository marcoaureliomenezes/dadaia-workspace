# S3 QA close — gate, doctor and seam hardening (T-045-19 … T-045-23)

**Author:** qa-engineer, 2026-08-26
**Governs:** TASKS.md T-045-24 ("`S3` close: `qa-engineer` review committed on the branch")
**Scope reviewed:** commits `eb03d01b` … `92b8b3d6` on `feature/0.4.5` (FR6–FR10 plus two
Arm-B bugs found in flight)
**Independent verification method:** `git show`/`git diff --numstat` on every cited commit,
direct reads of every cited artifact, and a fresh local re-run of every acceptance-relevant
test suite plus `dadaia ci preflight` / `dadaia specs doctor` / `dadaia public doctor` /
`dadaia doctor` / `dadaia bugs stats` — nothing below is taken on report alone.

## Verdict

**APPROVE.**

Every S3 acceptance id (A6.1–A6.5, A7.1–A7.6, A8.1–A8.3, A9.1–A9.3, A10.1–A10.4) is
evidenced by a named, currently-green test on the executed path. All three resolved
events (`bug-event-field-with-unicode-line-separator-silently-drops-the-event`,
`dadaia-agents-md-canonical-table-omits-sanctioned-references`,
`dadaia-reconcile-quarantines-sanctioned-references-clone`) carry the three FR23 fields,
each `evidence_diff` prefixed `net-…`. `dadaia bugs stats`: 1 open bug workspace-wide,
exactly `windows-xdist-workers-crash-on-unit-fast-tier` (AS-5-governed, not S3's). FR23
firing 2 (`eb03d01b` net +52 → SOUND-WITH-AMENDMENT → `0cb08157` net +14) is closed on the
branch, applied before commit. No REQUEST_CHANGES finding.

## 1. Acceptance evidence

| Id | Commit | Test/artifact | Verified |
|---|---|---|---|
| A6.1–A6.3, A6.5 | `eb03d01b`+`0cb08157` | `tests/unit/features/bugs/test_write_time_denylist_redaction.py` incl. `test_bug_event_redact_scrubs_every_schema_string_field_derived_from_schema` (A6.5, schema-derived, closes T-043-23→T-044-62) | Re-ran — green |
| A6.2 (single loader) | `0cb08157` | `cli/commands/bugs.py`'s `.redact()` double-pass deleted (AM-1); grep confirms one reader of `load_privacy_terms` | Read `git show` diff myself |
| A6.4 | live doctor | `dadaia public doctor` → `[ok] public-privacy` | Ran myself |
| A7.1–A7.3, A7.6 | `2b9b30c1` | `tests/unit/features/bugs/test_control_format_char_sanitation.py` (U+2028 round-trip, ESC-free render, strip-before-mask ordering) | Re-ran — green |
| A7.4 | `2b9b30c1` | `tests/integration/infrastructure/test_live_bugs_ledger_still_parses.py` — full live `specs/bugs/bugs.jsonl` (1000+ rows), byte-identical before/after | Re-ran — green |
| A7.5 | ledger | `bug-event-field-with-unicode-line-separator-silently-drops-the-event` `resolved`, three FR23 fields present | Parsed directly |
| A8.1–A8.3 | `f3acf990` | `tests/contract/cli/test_cli_specs_init_symlink_refused.py` — capability-probed (`_can_symlink()`, create-then-clean, not `sys.platform`), baseline fixture unchanged | Re-ran — green; read the probe function myself |
| A9.1–A9.3 | `4f890913`+`fa43364e` | `S3-FR9-ruling.md` (architect, report-only INV-6) + `tests/unit/test_spec_context_doctor.py` (`inv6` cases, no-regression pin) | Re-ran — 8 passed |
| A10.1–A10.4 | `9bdb960b` | `tests/unit/features/spec_context/test_dadaia_references_lifecycle_sanction.py` (ROOT-4 clean + shared-seam proof tests for resolve/bind-show/doctor-fix-GC) | Re-ran — green |

Full targeted sweep re-run independently: **60 passed** across all nine files above
(`-p no:cacheprovider`). `tests/contract/test_workspace_layout_single_authority.py` +
`tests/unit/features/migrate/test_legacy_dadaia_dirs.py` (the `92b8b3d6` bug fix): **9
passed**.

## 2. Gates at HEAD (`a0eb6932`)

```
dadaia ci preflight            -> [PASS] ruff format/check, mypy --strict, lint-imports, pytest — exit 0
dadaia specs doctor --json     -> errors 0, warnings 4 (same 4 pre-existing legacy items S1/S2 already recorded)
dadaia public doctor           -> [ok] public-privacy
dadaia doctor                  -> All invariants OK — workspace is healthy.
dadaia bugs stats              -> total 492, status:open 1 (windows-xdist-workers-crash-on-unit-fast-tier only)
```

## 3. Definition drift (T-045-21)

TASKS.md's write set for T-045-21 names `dadaia_workspace/features/specs/**`, `tests/**`.
The actual fix landed in `dadaia_workspace/cli/commands/specs.py` (+7/−2), because the
reusable seam it must reuse (A8.2, no second symlink check) —
`core.specs_resolver.resolve_specs_dir` via the already-imported `_resolve_specs_dir`
helper — is consumed at the CLI call site, not inside `features/specs/`. Correct fix,
wrong TASKS path; recorded for CLOSURE, not blocking.

## 4. FR23 firing 2 provenance

`eb03d01b` (net +52) routed to `software-architect` per FR6's positive-diff carve-out;
ruled **SOUND-WITH-AMENDMENT** (`FR23-firings.md` "Firing 2") — AM-1 deletes the CLI's
superseded double-redaction pass, AM-2 replaces `BugEvent.redact()`'s 11-field hand-kept
kwarg list with an iteration over the existing schema-mirror `_OPTIONAL_STR_FIELDS` tuple.
Engineer applied both as `0cb08157` (net +14, matching the ruling's predicted "≈+10
logic") **before** flipping `[x]` — order respected.

## 5. Bug-surface axis (operator's standing order)

**Privacy-leak-into-committed-material class** (`public-privacy-consumer-leak-in-public-repo`
→ T-043-23 → `reconciliation-merge-body-scan-unamendable-main-squash` → the two v0.4.4
committed leaks FR6 cites): **the write-time half is now closed at the seam.** Before,
the operator denylist was consulted only at push time — a leak had to be committed first
and refused later; FR6/T-045-19 wires the same `load_privacy_terms` loader into
`BugService.append_event`, proven RED-then-GREEN, push-scan behaviour unchanged (A6.3).
The **hand-kept-field-list sub-class** (T-043-23 widened the list by 2 fields → T-044-62
widened it by 3 more — same defect shape twice) **is now closed by construction**: AM-2
derives the scrub set from `_OPTIONAL_STR_FIELDS`, the same tuple `to_dict`/`from_dict`
already use, and `test_bug_event_redact_scrubs_every_schema_string_field_derived_from_schema`
pins it against the schema file itself — a future field addition can no longer be missed
by a hand-kept list, because there is no longer a hand-kept list.

**`.dadaia/` layout class** (`doctor-whitelist-legitimizes-slop-dirs`, 2026-07-15 → FR10
sanctions `references/` in the doctor's allowlist → `dadaia-reconcile-quarantines-
sanctioned-references-clone`, discovered and reported **within the hour** of the FR10
commit landing, because `migrate/legacy_dadaia_dirs.py` hand-copied its own second
allowlist that FR10 never touched): **closed by construction**, `92b8b3d6`. The fix
deletes both hand-kept lists and moves the one canonical set to
`core/workspace_layout.py::DADAIA_ALLOWED_SUBDIRS`; `doctor.py` derives its allowlist by
identity, `legacy_dadaia_dirs.py`'s quarantine set is now *computed* as candidates minus
the canonical set — a name sanctioned in one place cannot stay duplicated-as-legacy in
the other; the recurrence class is structurally unrepresentable now, not merely fixed for
today's values. `tests/contract/test_workspace_layout_single_authority.py` (identity
assertions) proves it. Diff is exactly balanced (+54/−54, net 0) — textbook
deduplication, not addition.

**Registry slug-ownership class** (F-1 `context-repo-add-accepts-foreign-context-slug` +
F-12 `context-create-accepts-slug-owned-by-another-context`, both HIGH, resolved with zero
recurrence): FR9/INV-6 closes the third lane the architect ruling names (historical/
migrated state) with a report-only detector, deliberately **not** a heal — healing would
require picking a disposition winner between two owners, which is the destructive-branch
shape Firing 5 already rejected for `dead()`. `dead()` stays untouched.

**Net effect on the bug ledger this segment:** 5 bugs terminally dispositioned (3 resolved
in-scope + 2 Arm-B bugs found and closed in flight), 0 new open bugs, workspace-wide open
count unchanged at 1 (the pre-existing AS-5 item). Three separate recurrence chains — the
privacy-leak class, the hand-kept-field-list class, and the `.dadaia/` layout class — are
each now structurally closed, not patched per instance.

## 6. Production LOC — measured, not estimated

Per task: `dadaia_workspace/` only, excluding non-S3 commits in range (`bd9d68f5`,
`a2faaad2`, `49d9afa8`, `c84dae57`, `8f6c63c1`, `61d258a7`, `4f890913`, `b3bf58da`,
`5a82dcbf`, `94bd7f3d`, `b1d424b8`, `057a400c`, `fd48a513`, `a0eb6932`, and the five
`chore(backlog)` commits — all docs/specs/tasks/backlog, zero `dadaia_workspace/` touch,
confirmed by numstat).

| Task | Range | Diff |
|---|---|---|
| T-045-19 (+ amendment) | `eb03d01b^..0cb08157` | 4 files, +71/−57, **net +14** |
| T-045-20 | `2b9b30c1^` | 2 files, +46/−5, **net +41** |
| T-045-21 | `f3acf990^` | 1 file, +7/−2, **net +5** |
| T-045-22 | `4f890913..fa43364e` | 1 file, +26/−0, **net +26** |
| T-045-23 | `9bdb960b^` | 1 file, +11/−2, **net +9** |
| bug `dadaia-agents-md-canonical-table-omits-sanctioned-references` | `43e020e9^` | 1 file (`public/data/…`), +4/−3, **net +1** |
| bug `dadaia-reconcile-quarantines-sanctioned-references-clone` | `92b8b3d6^` | 3 files, +54/−54, **net 0** |
| **Whole segment** | `c0737c0a..HEAD` (`dadaia_workspace/` only) | 10 files, **+206/−110, net +96** |

S3 is production-LOC **net-positive**, unlike S1 (net −1) and S2 (net −90). This is
expected and individually justified per-FR, not a defect: S3's theme is closing gaps
(write-time enforcement, sanitation, symlink refusal, a missing detector, a sanction),
not consolidation — FR6–FR10's acceptance ids carry no net-negative-LOC clause (unlike
FR2/A2.6, FR3/A3.3, FR4/A4.4), and FR9's own architect ruling states explicitly "growth
is the missing detector itself, not a branch on a verb." The two Arm-B bugs are net +1
and net 0 (the latter a textbook deduplication). The release-wide net-negative rule
(SPEC §3) is a release-wide accounting, reconciled at CLOSURE against S1+S2's larger
negatives — recorded here as an honest number for that reconciliation, not a finding
against S3.

## 7. Test stewardship

Every new test file declares `Intent: CONTRACT` + size in its module docstring (T-045-19,
-20, -21, -23). The two new cases added to the pre-existing
`test_workspace_layout_single_authority.py` (92b8b3d6) inherit that module's own
pre-declared contract framing (`pytestmark = pytest.mark.contract`, docstring states its
single-authority intent) — not undeclared SCAFFOLD. `test_legacy_dadaia_dirs.py` (new)
declares `Intent: CONTRACT` citing the bug id. The only new skip
(`test_cli_specs_init_symlink_refused.py`) is `_can_symlink()` — a real create-then-clean
capability probe at collection time, explicitly documented as rejecting a `sys.platform`
guess (Windows Developer Mode can create symlinks) — not a platform-name skip. No
quarantine added.

## 8. Intake candidates (not bugs, routed for the PM's intake)

- `S3-FR9-ruling.md`'s own stated residual risk: between a v2→v3 migration and the next
  `dadaia doctor` run, a colliding registry can still be destroyed by `dead()` on one
  owner — accepted by the architect (not a lane `dead()` should guard, per the Firing 5
  precedent), stated for visibility, not a gap in this segment's acceptance.
- FR23 Firing 1's own LOW residual (the `certify` marker-mismatch branch not yet routed
  through `_codex_capped_detail`) is an S1 item, re-noted only for completeness — not S3.

## 9. Security/privacy leakage note

None newly introduced. FR6/FR7 are themselves privacy/integrity hardening (write-time
denylist enforcement; CWE-117 control-character stripping) — both independently proven on
the executed path. `dadaia public doctor` stays `[ok] public-privacy` after the FR10
`public/data/dadaia-AGENTS.md` edit and its re-projection. No secrets, tokens,
credentials, consumer-specific data, or home-absolute paths appear in any S3 diff or in
this document. No new third-party dependency in any S3 commit. `dadaia bugs stats`
confirms no bug reopened and no unregistered pass-on-retry.

## 10. What S3 left unevidenced

Nothing in S3's acceptance/evidence map is unevidenced. FR9's "or a recorded rule-out" arm
was not taken — the architect implemented INV-6 instead, per §1 above; both are admissible
under A9.1 and the implementation path is the one fully evidenced here.
