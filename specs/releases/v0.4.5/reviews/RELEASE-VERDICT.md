# RELEASE VERDICT — v0.4.5 (T-045-34, QA half)

**Author:** qa-engineer, 2026-08-26
**Governs:** TASKS.md T-045-34 ("security-reviewer APPROVED + qa-engineer release verdict")
**Commit reviewed:** `27c3374a9770783c7d9716c9594064fe9d429b3f` (full sha; docs-only commits
`1bfd9209`, `4252c43b` follow it, zero production/test diff)
**Base:** `68658783` (shipped v0.4.4)
**Independent verification:** re-ran `dadaia ci preflight` (unpiped, exit captured
directly), `dadaia doctor`, `dadaia specs doctor --json`, `dadaia backlog doctor`,
`dadaia public doctor`, `dadaia bugs stats`, `lint-imports` myself at HEAD; re-measured
V10/V11/test-LOC-delta myself via `git diff --numstat` against both `68658783` and the
prior `T-045-32` capture point (`b207c20d`) to isolate the F1-rework contribution; cross-
read all four segment QA closes, both passes of the code review, `FR23-firings.md`, and
`T-045-32`'s own capture. Nothing below is taken on report alone.

## Verdict

**APPROVED** for `27c3374a`.

Every FR1–FR15 acceptance is evidenced by a named test or artifact on the executed path,
with three PARTIALs recorded as honest, AS-governed misses — never a silently redefined
target. FR16's invariants hold at HEAD, re-verified independently. The one HIGH finding
(code review F1) is closed at `27c3374a` with a RED-then-GREEN test and a narrowing (not
additive) fix. O5 holds: no version bump, no workflow diff, no `v0.4.5` tag. Every bug
touched by this release is terminal except the one AS-5-governed item, which is correctly
still open. Zero SCAFFOLD/undeclared tests, zero new `tests/e2e/**`.

---

## 1. Scope-complete — FR1–FR16 acceptance evidence

| FR | Evidence | Verdict |
|---|---|---|
| FR1 (gate LAW predicate) | `S1-qa-close.md` §1 (A1.1–A1.7); code review §2 confirms net-negative on every axis, zero I/O on the floor arm | **PASS** |
| FR2 (atomic-write primitive) | `S2-qa-close.md` §2 (A2.1–A2.7); AR-1 UPHOLD D5; code review §3 confirms `expand→switch→contract` (F4 LOW deviation, non-blocking) | **PASS** |
| FR3 (byte-golden split) | `S2-qa-close.md` §4 (A3.1–A3.3), zero production LOC | **PASS** |
| FR4 (shared skill oracle) | `S2-qa-close.md` §4 (A4.1–A4.3 met); A4.4 "net-negative test LOC" measured **net +97** on the three named consumers by QA's own count — recorded honestly (§6 discrepancy #3), does not block since the acceptance's substance (one oracle, killed root cause of two bugs) is fully met | **PARTIAL** (A4.4 wording gap, routed to intake) |
| FR5 (scan vacuity guard) | `S2-qa-close.md` §4 (A5.1–A5.3), 19 files/20 call sites, 3 RED proofs | **PASS** |
| FR6 (write-time denylist seam) | `S3-qa-close.md` §1 (A6.1–A6.5); FR23 Firing 2 SOUND-WITH-AMENDMENT applied before `[x]` | **PASS** |
| FR7 (control/format sanitation) | `S3-qa-close.md` §1 (A7.1–A7.6) as originally written — **but** code review F1 found the landed regex deleted TAB/LF/CR (word-joining every multi-line field, 8.2% historical base rate), zero test coverage for that hazard. Closed at `27c3374a`: narrowed in place, 3 new cases, re-verified by me (`test_control_format_char_sanitation.py` + `test_live_bugs_ledger_still_parses.py` green) | **PASS** (post-rework; was the release's one HIGH gap) |
| FR8 (symlink refusal) | `S3-qa-close.md` §1 (A8.1–A8.3), capability-probed, no `sys.platform` guess | **PASS** |
| FR9 (slug-ownership lane) | `S3-qa-close.md` §1 (A9.1–A9.3), architect ruling INV-6, report-only per AS-4's admissible-either-outcome | **PASS** |
| FR10 (`.dadaia/references/` sanction) | `S3-qa-close.md` §1 (A10.1–A10.4) | **PASS** |
| FR11 (always-on diet) | `S4-qa-close.md` §2/§3 — A11.1–A11.4 met (measured, coverage table, honest-miss statement); **V6/V7 targets themselves missed** (20502 vs ≤3.5k tokens; 257 vs ≤60 negations) | **PARTIAL** (AS-3-governed honest miss) |
| FR12 (catalog digest trim) | `S4-qa-close.md` §2/§3 — A12.1–A12.4 met; FR23 Firing 3 SOUND-WITH-AMENDMENT applied; **V8 target missed** (877.8 vs ≤700 tokens) | **PARTIAL** (AS-3-governed honest miss) |
| FR13 (persona ceiling trim) | `S4-qa-close.md` §2/§3 — A13.1–A13.4 met (fleet net −93 source lines); **V9 target missed**, 5 personas still over 220 (not the 4 SPEC named — `software-engineer` omitted from SPEC/TASKS, correctly included in execution) | **PARTIAL** (AS-1-bounded honest miss + a definition-drift, §7) |
| FR14 (AI-surface hygiene) | `S4-qa-close.md` §3 (A14.1–A14.3); code review F3 notes this is a third instance of the stale-citation class with no structural close — accepted as this FR's correct scope (the instance, not the class) | **PASS** |
| FR15 (Intent vocabulary ruling) | `S4-qa-close.md` §3 (A15.1–A15.2, zero off-taxonomy hits); A15.3 correctly deferred to this release's `CLOSURE.md` | **PASS** |
| FR16 | see §2 below | **PASS** |

Three PARTIALs (FR4, FR11, FR12, FR13) are every one an **honest, SPEC-governed miss**
(AS-1/AS-3, A4.4's wording gap) — none redefines a target, none is silently accepted;
each is named in its own segment close and carried to `CLOSURE.md` for the operator's
ruling, per SPEC §2.3/§5. None blocks this verdict.

## 2. FR16 invariants — re-run myself at HEAD `27c3374a`

| Id | Check | Result |
|---|---|---|
| A16.1 | `dadaia ci preflight` (unpiped) | exit 0 — ruff format/check, mypy --strict, lint-imports, pytest all PASS |
| A16.1 | `dadaia doctor` | "All invariants OK" |
| A16.1 | `dadaia specs doctor --json` | 0 errors, 4 pre-existing legacy warnings (2 archived-release naming, 2 archived-audit disposition — none touch this release) |
| A16.1 | `dadaia backlog doctor` | clean |
| A16.1 | `dadaia public doctor` | `[ok] public-privacy`, `[ok] entities-derivation`, no `[drift]`/`[missing]` |
| A16.2 | `lint-imports` (via preflight) | 9/9 contracts kept, 0 broken, no new accepted edge since base |
| A16.3 | V10 production LOC net, re-measured at `27c3374a` vs `68658783` (`dadaia_workspace/` excl. `public/`) | **+471/−426 = +45** (was +38 at the T-045-32 capture point `b207c20d`; the +7 delta is exactly the F1 rework, `+25/−18` in `core/models/bugs.py`). Positive net remains fully explained per-FR (T-045-32's table: FR2 deletion engine −90 against three architect-ruled net-positive seams, one ruled invariant, and FR7); F1's own +7 is a bug-fix narrowing, not new capability. Carried to `CLOSURE.md` for the operator's ruling, as SPEC requires for any positive net |
| A16.4 | V11 AI-surface LOC net, re-measured (`public/{agents,skills,data,entities}`) | **+213/−251 = −38**, unchanged from T-045-32 (F1 touches no `public/**` path) |
| A16.5 | Complexity ceilings | `git diff 68658783..27c3374a -- pyproject.toml` shows zero change to `max-complexity`/`PLR1702` config; still `max-complexity = 63`, never raised |
| A16.6 | Residual budget | Every picked bug terminal or explicitly open per AS-5 (§4); 14 picked backlog entries still `CONSUMED · v0.4.5` (disposition-to-`DELIVERED` is a `CLOSURE` step, not yet run — correct, T-045-34 precedes T-045-38); no agent has materialized a backlog entry |
| — | Tests LOC delta, re-measured (`tests/`) | **+2,817/−980 = +1,837** (was +1,769 at T-045-32's capture; the +68 delta is the F1 rework's 3 new cases in `test_control_format_char_sanitation.py`) |

## 3. Test-suite verdict at closure — the demotion step

**New tests this release:** 10 new test files (S1–S3), all declaring `Intent: CONTRACT`
plus size in the module docstring at birth — **zero SCAFFOLD/undeclared**. **Zero new
`tests/e2e/**` files** — confirmed by `git diff --name-status` — so SPEC §3's
"zero new e2e without a named exception" holds trivially and the LARGE-tier census
(~84 vs the declared cap of 30, a pre-existing companion-release remediation target) is
**not worsened** by this release.

**Demotions/deletions already executed in-segment (LARGE/hand-kept → derived/smaller),
ratified here:**

| # | Item | Criterion | Executed at | Verdict |
|---|---|---|---|---|
| 1 | 10-case hand-kept characterization test inside `test_migration_symlink_hardening.py` (−369 net) — pinned the *leaking* atomic-write behaviour as current | (a) feature removed / (d) self-destructing on its own subject | `091b2401` | **DELETE — ratified** |
| 2 | 3 hand-kept skill inventories (`EXPECTED_SKILLS` literal, a path-assertion list, the orphan checker's own roster) — root cause of 2 v0.4.4 bugs | (b) duplicate coverage, now one derived oracle | `78daad25` | **DELETE — ratified** |
| 3 | 2 byte-golden file-inventory blocks | policy vs inventory split, roster derived by scan | `053f55e8` | **DEMOTE — ratified** (goldens kept as policy-only SENTINEL, inventory assertion moved to a derived roster) |

**New KEEP-with-follow-up verdicts issued at this close (not executed here — routed to
the PM's intake, per the separation of powers: qa-engineer verdicts, software-engineer
executes):**

| # | Test | Concern (code review id) | Verdict | Reason |
|---|---|---|---|---|
| 4 | `tests/unit/features/spec_context/test_dadaia_references_lifecycle_sanction.py:35` | F5 — imports the private module `dadaia_workspace.cli._specs_resolution` | **KEEP**, follow-up recorded | Justified inline (the real seam behind `context bind`/`show` no-arg resolution); single instance, no recurrence in this release's bug history — promote the seam to a public name in a later pass, not urgent enough to block or rework now |
| 5 | `tests/integration/infrastructure/test_live_bugs_ledger_still_parses.py` | F6 — bound to the live, growing 1012-row `bugs.jsonl` as its oracle | **KEEP**, demotion decision deferred to `CLOSURE.md` | Read-only, vacuity-checked, needed exactly one live proof for A7.4 ("every historical event still parses"); nothing is broken today and it has not (yet) flaked — the class is the same shape as the S4 flake (`aea57a34`, a *different* test, already root-cause fixed), so it is worth a demotion decision at closure, not an emergency rework now |

**Flake handling.** One test observed pass+fail on the same code during the S4 close
(`test_staging_step_copies_scoped_subset_without_touching_repo_git_tree`) was
**root-cause fixed** (`aea57a34` — excludes ADDITIVE-path lines from the porcelain
comparison, per the NO-LOCKS DOCTRINE) rather than quarantined; its bug
(`mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes`, LOW) is
`resolved`. No quarantine was needed or used this release.

**Count:** 3 DELETE/DEMOTE verdicts ratified (already executed, correctly, in-segment),
2 KEEP-with-follow-up verdicts issued now, 0 SCAFFOLD expiries, 0 quarantines.

**Value judgment (concurring with the code review's §7).** The +1,837 test-line delta is
net-positive but higher-value per line than what it replaced: additions are AST-derived
censuses, a call-site oracle delegating to the product's own enumeration, and a
21-case injected-failure matrix landed *before* any writer was deleted; deletions are
hand-kept tables and literal inventories that had already produced four registered bugs.
The one real gap (F1: the sanitation suite tested the characters SPEC named and none of
the characters the regex actually ate) is closed by the F1 rework, independently
re-verified by me at `27c3374a`.

## 4. Bugs — every one terminal or explicitly open (AS-5)

| Bug | Severity | Origin | Disposition | Verified |
|---|---|---|---|---|
| `sdd-gate-blocks-fresh-repo-root-agents-md` | MEDIUM | picked | `resolved`, S1 | `bugs.jsonl` |
| `repo-agents-md-law-gate-contradicts-template` | MEDIUM | picked | `resolved`, S1 (same cause) | `bugs.jsonl` |
| `dadaia-task-manager-stale-workspace-protocol-citation` | LOW | picked | `resolved`, S1 | `bugs.jsonl` |
| `certify-skip-detail-leaks-full-codex-output` | LOW | picked | `resolved`, S1 (FR23 Firing 1, SOUND) | `bugs.jsonl` + `FR23-firings.md` |
| `codex-probe-unit-fixture-carries-real-session-uuid` | LOW | picked | `resolved`, S1 | `bugs.jsonl` |
| `bug-event-field-with-unicode-line-separator-silently-drops-the-event` | MEDIUM | picked | `resolved`, S3 (bundled into FR7, D3) | `bugs.jsonl` |
| `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` | LOW | picked | `superseded` by `atomic-write-primitive-consolidation`; `Closed` deferred to CLOSURE (correct, not a gap) | `bugs.jsonl` |
| `windows-xdist-workers-crash-on-unit-fast-tier` | LOW | picked | **OPEN** — bounded root-cause attempt inconclusive, AS-5 verdict issued (`S1-AS5-xdist-verdict.md`), never closed by a quarantine | `bugs.jsonl` (only `reported`), `dadaia bugs stats` |
| `frozen-clock-ratchet-scans-tests-tmp-scratch-dir` | LOW | found in flight, S1 | `resolved` | `bugs.jsonl` |
| `dadaia-agents-md-canonical-table-omits-sanctioned-references` | — | found in flight, S3 | `resolved` | `bugs.jsonl` |
| `dadaia-reconcile-quarantines-sanctioned-references-clone` | — | found in flight, S3 (within the hour of the FR10 commit) | `resolved`, net 0 | `bugs.jsonl` |
| `mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes` | LOW | found in flight, S4 | `resolved` (root-caused, not quarantined) | `bugs.jsonl` |
| `bug-event-sanitation-strips-tab-lf-cr-from-free-text` | HIGH | found in flight, T-045-33 code review (F1) | `resolved` at `27c3374a`, isolated `reported` commit (`2dbc2b41`) precedes the fix — Arm B order correct, no history rewrite | `bugs.jsonl`, re-verified by me |

**13 bugs touched, 12 terminal, 1 correctly open.** `dadaia bugs stats` (re-run by me):
workspace-wide `status:open 1` — exactly `windows-xdist-workers-crash-on-unit-fast-tier`.
Zero unregistered pass-on-retry across the release.

## 5. O5 — nothing published

- `pyproject.toml` still reads `version = "0.4.4"` at HEAD — the bump to `0.4.5` is
  correctly deferred to the final `rc` (D6), not yet run.
- `git diff 68658783..27c3374a -- pyproject.toml .github/workflows/release.yml` — **empty**,
  zero touch to either file across the whole release so far.
- `git tag -l v0.4.5` — **no such tag exists**.

All three of A16.8's verifications hold at this point in the release; the full A16.8
statement (approve-job pending-unapproved, PyPI latest still `0.4.4`) is a `CLOSURE.md`
recording obligation once the final `rc` actually ships, not yet applicable at T-045-34.

## 6. Intake candidates (consolidated from S1–S4 + the code review; list only, never
materialized here)

1. A4.4's wording gap — "net-negative test LOC" should scope to *net LOC excluding a new
   shared module*, mirroring A2.6's "production LOC" framing, for any future FR of this
   consolidation shape (S2 close §6/§7).
2. `scan_population.py`'s own docstring prose says "20 files/21 call sites" against its own
   enumerated "19 files/20 call sites" — a one-line self-inconsistency, unfixed at HEAD
   (S2 close §6 item 2; code review F7).
3. Tech-stack digest floor (~564 tokens, `_digest_tech_stack`) is the next V8 lever, out of
   FR12's scope (A30.3-pinned) — needs its own FR touching `ctx_inject` (S4 close §7.1).
4. `_TLDR_INJECTED_CATEGORIES = frozenset({"core"})` (today: drop-all) needs
   `product-engineer` ratification of the default, or an explicit disposition of the
   residual V8 gap as an honest miss (S4 close §7.2).
5. `dadaia-step0-memory-bootstrap`'s "tldr/summary" wording should read "summary" — the
   persisted file no longer carries `tldr` under the live default (S4 close §7.3).
6. T-045-28's "referenced, not restated" pointer idiom trips the V7 negation regex
   (+3) — reword positively in a future pass (S4 close §7.4).
7. No test enforces the Intent-token taxonomy itself (a lightweight grep-based contract
   would catch regrowth of the `REGRESSION`/`BUG` drift class) — not implemented, out of
   T-045-30's dispatched scope (S4 close §7.5).
8. The stale-citation class (three instances across two releases, each caught only after
   the fact by the same enforcer) has no structural close yet — named anchors or citation
   derivation is the candidate direction (code review F3).
9. FR23 Firing 1's own LOW residual — the `certify` marker-mismatch branch still embeds
   `stdout[:200]!r` unrouted through `_codex_capped_detail` (code review F9).
10. F5/F6 (§3 above) — promote the private-symbol-importing seam; record the demotion
    decision for the live-ledger-bound test at `CLOSURE.md`.

## 7. Definition drifts (consolidated, for the release's `CLOSURE.md`)

- **SPEC FR13 / TASKS T-045-28 both say "four" over-ceiling personas; five were measured**
  (`software-engineer` at 245/243 lines, omitted from both documents). The dispatching
  agent correctly included it in execution; SPEC's wording needs operator/PM
  reconciliation (S4 close §6; code review F8).
- **T-045-15's TASKS write set** names `tests/e2e/...`/`tests/integration/...` paths that
  do not match where the two golden tests actually live
  (`tests/unit/infrastructure/...`) — the work is correct, the TASKS document was stale
  at authoring time (S2 close §4 FR3 note).
- **T-045-19's TASKS write set undercounted** — the architect's Firing 2 ruling required
  touching `features/bugs/service.py` and `cli/commands/bugs.py` beyond the originally
  named file; necessary per the three import-linter contracts, not an SE fault (FR23
  Firing 2 §2).
- **T-045-21's TASKS write set** names `features/specs/**`; the real, correctly-reused
  seam is consumed at `cli/commands/specs.py` (S3 close §3).
- **T-045-29's TASKS names `ai-engineer` as sole owner**; F-7/F-8/F-10 are production
  Python outside `public/**` (out of `ai-engineer`'s write scope), so `software-engineer`
  correctly swept them in a second commit under the same task id (S4 close §6).

## 8. Security/privacy leakage note

None newly introduced by this verdict document or by the release since the last
segment close. FR6/FR7 are themselves privacy/integrity hardening, both independently
re-proven on the executed path at `27c3374a`. No secrets, tokens, credentials,
consumer-specific data, or home-absolute paths appear in this document or in any diff
reviewed. No new third-party dependency across the release. `dadaia public doctor`
reports `[ok] public-privacy` at HEAD. The one HIGH finding this verdict closes (F1) was
itself a data-fidelity/silent-loss defect, not a disclosure — its fix is independently
re-verified (per-character probe on the installed venv, 13 tests green). This document
lives under `specs/releases/`, not any `public/` projection.

## 9. Bug-surface axis (release-wide, FR24)

Concurring with the code review's §6/updated row: **12 of 13 touched surfaces reduced or
held their bug surface**; the one surface that briefly increased
(`core/models/bugs.py::redact_text`, opened by the FR7 landing) is now **reduced** again
after the F1 rework — narrower than its pre-FR7 state on the classes it exists to close
(privacy-leak, hand-kept-field-list) while no longer opening the whitespace-loss lane.
Three multi-bug recurrence chains (privacy-leak-into-committed-material,
hand-kept-field-list, `.dadaia/` duplicate allowlists) are each now structurally
unrepresentable, per the standing order, not merely patched per instance.

---

## Re-verdict @395bfb35

**Author:** qa-engineer, 2026-08-27
**Governs:** T-045-35 (`rc-1`) — all three verdicts (QA, code, security) on one sha,
required before the `feature/0.4.5` → `develop` PR merges.
**Delta since the prior APPROVED sha (`27c3374a`):** `e34f1209` registers
`push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-substrings` (HIGH) — the
rc-1 push-gate false positive; `7de4783f` is `software-architect`'s ruling
(`T-045-35-foreign-slug-ruling.md`, option 1 selected); `395bfb35` carries the fix.

### Verdict

**APPROVED** for `395bfb352a4cdefa7cbbbf06d0c1908a1af38728`.

### What the delta actually is

`compile_slug_patterns` anchored a registry-derived slug with `\b`. Python's `\b` treats
`-`/`.` as non-word delimiters, so a hyphenated slug (every `repos/<slug>` in this
workspace is hyphenated) matched **inside** a longer hyphen/dot-glued identifier —
`<slug>-anything`, `<slug>.ext` — not just as a whole token. The rc-1 push hit two false
positives from this: the library's own tracked asset basename
(`public/data/dadaia-AGENTS.md`-shaped path) and a ledger bug id beginning with a
consumer slug substring, neither a real private-name publication. The fix replaces the
`\b` anchor with a lookaround (`(?<![\w-])(?<!\w\.)…(?![\w-])(?!\.\w)`) that bounds the
match to true token edges; `IGNORECASE` is kept. **One predicate, no branch, no
allowlist, no new code path** — both consumers (`_slug_suppressed` and
`_PathMasker._segment_is_offending`) inherit the change unmodified, by construction, not
by a second edit kept in sync by convention.

### Independent re-verification performed for this re-verdict

```
python -m pytest tests/unit/features/chokepoints/ -p no:cacheprovider -q
  -> 108 passed
dadaia ci preflight   (unpiped, exit captured directly)
  -> [PASS] ruff format --check / ruff check / mypy --strict / lint-imports / pytest
  -> exit 0
dadaia bugs status
  -> windows-xdist-workers-crash-on-unit-fast-tier  open  LOW
  -> [ok] 1 open bug(s)                      (the AS-5 item only, unchanged)
```

`git show 395bfb35` read directly for both production files
(`denylist_scan.py` +2/−1 logic + docstring, `service.py` docstring-word-swap only) and
the test file — confirmed a whole-token regex swap, zero new branch/function/call site,
zero allowlist.

### Stewardship check on the 5 new tests (`test_denylist_scan.py`)

| Check | Result |
|---|---|
| Intent + size declared at birth | All 5 declare `Intent: CONTRACT — T-045-35 …` in the docstring; appended to an existing declared-CONTRACT module, not a new undeclared file |
| Synthetic names only | `_SYNTHETIC_FOREIGN_SLUG = "zz-fake-context-name"` — a fabricated slug, not a real foreign Spec Context or consumer repo name; no private name transcribed |
| Structure-sensitive (P1 class) | None — no private-symbol import, no exact-string assertion on a message body (asserts on `outcome.hits` tuple contents and `source_layer` field, not on rendered text), no hand-kept inventory |
| Duplicate coverage | No — one RED-then-GREEN pair (`test_foreign_slug_inside_hyphenated_basename_and_bug_id_does_not_match`, `test_foreign_slug_after_dotted_prefix_does_not_match`) plus three no-regression controls (bare-prose match, sentence-end-period match, `repos/<slug>/` path match) — each control asserts a distinct boundary condition, none redundant with another |
| Tier | `tests/unit/` — SMALL, correctly the cheapest tier that detects a regex-boundary regression |

**Verdict: 5 KEEP (admitted as-is).** Zero SCAFFOLD/undeclared, zero quarantine, zero new
`tests/e2e/**`. No demotion/deletion action needed for this delta.

### FR23 evidence triple (`push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-substrings`, `resolved`)

`evidence_loop` (RED-then-GREEN: 2 cases failed at `7de4783f`, green after the fix, plus
a real chokepoint refspec replay going exit 1 → 0), `evidence_seam` (the 5 named test ids
above), `evidence_diff` (`net-neutral: +2/−1 code, docstring updates only — no allowlist,
no branch, no new code path`) — all three present, consistent with the diff I
independently read.

### Security verdict cross-check

`security-reviewer` independently APPROVED this same sha
(`specs/releases/v0.4.5/verdicts/395bfb352a4cdefa7cbbbf06d0c1908a1af38728.handoff.json`,
commit `2c23e717`) — noted for T-045-35's "all three verdicts on one sha" precondition,
not relied on in place of my own re-verification above.

### Bug ledger, re-checked

13 bugs from the original verdict remain terminal/AS-5-open as recorded; **+1** this
delta (`push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-substrings`, HIGH,
`resolved` at `395bfb35`, FR23 triple present). `dadaia bugs status` confirms exactly one
bug open workspace-wide (`windows-xdist-workers-crash-on-unit-fast-tier`, unchanged).

### Security/privacy leakage note

None. The fix narrows a false-positive detector — it does not weaken the push-gate's
true-positive behavior (the three no-regression controls above prove bare-slug,
sentence-end and `repos/<slug>/`-path occurrences still match). No secrets, tokens,
home-absolute paths or real consumer/context names appear in the diff, the architect
ruling, or this section — the test fixture's slug is fabricated. No new dependency.

### Standing

Everything else in the original verdict (§1–§9 above) is unchanged by this delta — this
section supersedes only the "sha reviewed" fact for T-045-35's gate; it does not
re-litigate FR1–FR16 or the earlier bug/test-suite findings, which still hold as recorded
at `27c3374a`.
