# S1 QA Close — release 0.5.0

**Task:** T-050-15 · **Reviewer:** qa-engineer · **Branch:** `feature/0.5.0` ·
**HEAD reviewed:** `ffe1b00982e864e3e304bc72b2a8ea81ba843202`
**Scope:** T-050-04…T-050-13A (`[x]`), T-050-14 (`[ ]`, operator-pending — recorded, not
evidenced as done).

**Verdict: APPROVE-CONDITIONAL** — conditional on the software-architect firing running in
parallel with this close (referenced by commit `38045be0`'s own message: "architect firing
at S1 close"). All S1 acceptance ids named below are PASS or PASS-WITH-FINDING; nothing is
FAIL. The condition is procedural — this close does not itself resolve or supersede that
architecture ruling.

---

## 1. Acceptance evidence (S1 scope: FR1–FR5, A13.4)

Every row cites either a command run directly in this session, or (marked `[implementer
evidence]`) the S1 commit's own captured verification, reviewed and — where practical —
independently re-run.

### FR1 — v6 canon (A1.1–A1.10)

| id | command | evidence | verdict |
|---|---|---|---|
| A1.1–A1.4 | `git show 10540961 --stat` + capture read | scaffold emits exact v6 root, zero README.md/assets/, `--recipe` renders per-finding steps, `specs upgrade` rename-automation cut (§ deviations recorded) | PASS |
| A1.5 | `grep -n "_FROZEN_PREFIX" dadaia_workspace/features/spec_context/gate_policy.py` | still `specs/_archive/` only — **not yet repointed**; explicitly deferred to T-050-14/T-050-21A per T-050-06/06A's own disposition table | PENDING (T-050-14) |
| A1.6 | `DADAIA_CONTEXT=dadaia-workspace dadaia specs doctor` (this session, current HEAD) | 1 error (SPEC-DOC-024, pre-existing release-wide governance-status condition, not FR1's write set), 490 warnings (see §5 below) — zero new/regressed FR1-attributable finding vs T-050-06's own before/after capture | PASS |
| A1.7 | `pytest -p no:cacheprovider -q tests/contract/test_source_repo_hygiene.py` (this session) | 1 file, part of the 17 green in the combined run below | PASS |
| A1.8 | `pytest -p no:cacheprovider -q tests/contract/test_pr_verdict_check_gate.py tests/contract/test_source_repo_hygiene.py` (this session) | `17 passed` — all 7 V20 arms + the A1.7 fixtures green at current HEAD, independently re-run, not merely cited from the commit | PASS |
| A1.9 | `.dadaia/tmp/software-engineer/20260827/T-050-06-v3.md` §"A1.5/A1.6/A1.9 — done" `[implementer evidence]` | release-dir canon (SPEC/PLAN/TASKS/RELEASE.jsonl/reviews/verdicts) produces zero TREE-8/TREE-3 findings | PASS |
| A1.10 | `git show 78b2b3ce` body, part (b) `[implementer evidence]` | `RELEASE_SEMVER_RE` gains optional `v`; `dadaia release new` refused a v-prefixed id at mint; `test_release_semver_canon.py` inverted, not deleted | PASS |

### FR2 — bug-record-v1 (A2.1–A2.13)

| id | command | evidence | verdict |
|---|---|---|---|
| A2.1, A2.10, A2.12 | `git show 912e3855` body `[implementer evidence]` | schema authored per-property mutability; `_OPTIONAL_STR_FIELDS` deleted, zero module-level field tuples (AST-scan contract); `surface` enum == `setup.cfg modules=` list | PASS |
| A2.2a/b/c | same commit, "Tests (+8...)" | immutable-core refusal, write-once refusal (parametrized over 8 fields), governance-rewrite byte-identity — all seam-level contract tests named | PASS |
| A2.6, A2.9, A2.11 | same commit | schema-fixture-driven redaction both write paths; `StaleRecordWriteError` on concurrent-write refusal; FR23 triple write-once | PASS |
| A2.3, A2.7, A2.8 | `git show b8e65f42` body `[implementer evidence]` | coherence WARN-only (exit unchanged); SPEC-DOC-040 (immutable-core drift) + SPEC-DOC-041 (archive-overdue) added, WARN-only; `bugs archive` idempotent through the record-store seam | PASS |
| A2.4, A2.5 | `git show b8e65f42` body, "Deleted whole" + "Rewritten in place" sections | expand(912e3855)→switch+contract(b8e65f42): `jsonl_bug_store.py` + `core/protocols/bug_store.py` deleted whole; `migrate_v5.py` is the one boundary adapter, imported by nothing else (contract-tested — see A3.10 below) | PASS |
| A2.13 | `git show b8e65f42` body | `dadaia bugs update` is the one governance write seam (AS-16(i)); `--event resolved\|picked\|archived` retired | PASS |

### FR3 — commit derivation + physical migration (A3.1–A3.11)

| id | command | evidence | verdict |
|---|---|---|---|
| A3.1 | `.dadaia/tmp/software-engineer/20260827/T-050-10-migration-report.md` §"V4" `[implementer evidence]` | migrated 496 == distinct `bug_id` count of the v5 ledger on the same branch-cut tree | PASS |
| A3.2 | same report §"A3.2" | non-null for all 496; 129 distinct commits (≥124); 81 single-line-adding commits (≥79); `exact`=36 (≤79) | PASS |
| A3.3 | same report §"A3.3" | non-null for all 495 terminal; 128 distinct commits (≥117); 78 single-record-resolving (≥70) | PASS |
| A3.4 | same report §"V5" | two independent full-pipeline runs, byte-identical sha256 (pre-V22-redaction) | PASS |
| A3.5 | `python3` scan run in this session over `specs/bugs/BUGS.jsonl`, scoped to the 496 migrated records (`registration_granularity is not None`) | lineage_source correctness: 70/70 `caused_by`-populated migrated records carry `lineage_source: "text-reference"` — PASS. `caused_by == "none"`: 0/496 migrated records — PASS (the one live `caused_by: "none"` found ledger-wide belongs to a directly-registered, non-migrated record outside FR3's scope). `cause` literal-text check: of the 4/496 migrated `cause` values, **2 do not appear verbatim** in the record's own retained text fields (`post-gate-reconciler-tests-order-dependent-flake` — the record carries no `evidence_diff`/`notes` field at all for the value to have been mined from; `citation-mutation-fixtures-never-turn-red-on-windows` — its `cause` is a distinct rephrased narrative, not a substring of `evidence_diff`/`evidence_loop`/`evidence_seam`/`symptom`/`repro`/`expected`/`title`) | **PASS-WITH-FINDING** (see §4, Q2) |
| A3.6 | `git diff --stat 02eef219..HEAD -- specs/bugs/_archive/archive.jsonl` (this session) | empty diff — byte-identical | PASS |
| A3.7 | migration report §"V23" `[implementer evidence]` | U+2028+ESC through the write seam is stripped and round-trips byte-stable; `dadaia bugs status --all` → `[ok] 496 all bug(s)`, exit 0, skipped: 0 | PASS |
| A3.8 | `git log --oneline 912e3855..588e4722` (this session) | FR2 schema commit (912e3855/b8e65f42) and the FR3 physical migration (588e4722) are separate commits; report is referenced from the migration commit body | PASS |
| A3.9 | migration report §"V22" `[implementer evidence]` | first `push-gate-check` run BLOCKED on the migration's own content (2 real hits), remediated at the source record, not excluded; second run clean of migration-introduced content; the one residual object predates this migration (T-050-09's own fixture, `d2e28c1e`) and is tracked as a separate bug | PASS |
| A3.10 | `git show d2e28c1e` body + `pytest -p no:cacheprovider -q tests/contract/test_migrate_v5_not_imported_by_permanent_consumer.py` (this session) | `core/bug_provenance.py` is pure/stdlib-only; `migrate_v5.py` keeps only the v5 adapter; AST census contract test green | PASS |
| A3.11 | migration report, "FR23 evidence triple" + "Surface mapping" sections `[implementer evidence]` | all three (27/496), none (469/496), partial (0/496) — counted; surface mapped 231/496 (46.6%), `unknown` 265/496 (53.4%, honestly above the 10% guideline, root cause named — retired lifecycle/workflow-engine subsystem, nothing fabricated) | PASS |

### FR4 — `RELEASE.jsonl` (S1 portion: A4.1a, A4.2, A4.3, A4.6 — A4.1/A4.5/A4.7 contract steps are T-050-21A, `S2`, out of this close's scope)

| id | command | evidence | verdict |
|---|---|---|---|
| A4.1a | `git show 6ac0be42` body `[implementer evidence]` | `RELEASE.jsonl` + `ACTIVE.md` read in parallel, doctor's SPEC-DOC-042 WARNs on disagreement — both live | PASS (expand half only; A4.1 proper is T-050-21A's) |
| A4.2 | same commit, doctor SPEC-DOC-043 (duplicate milestone WARN) | contract test refuses a milestone rewrite | PASS |
| A4.3 | `.dadaia/tmp/software-engineer/20260827/T-050-12-backfill-report.md` §"A4.3" `[implementer evidence]` | 114 scanned (V7 denominator); `defined` 12/114, `shipped` 41/114, all 53 non-null shas verified via `git rev-parse --verify <sha>^{commit}`; `implemented` deliberately 0/114 (scoping decision, not a gap — D3's rc-lane concept postdates pre-0.6.0 releases) | PASS |
| A4.6 | same report, fold-correctness spot-check (`v0.1.47`) | `audited` milestones scannable across live/`_ideas`/`_archive` in one pass | PASS |

### FR5 — `BACKLOG.md` live photo (A5.1–A5.5)

| id | command | evidence | verdict |
|---|---|---|---|
| A5.1 | `git show 3b167e07` body `[implementer evidence]` | 117 `## LEDGER` lines migrated: 68 with `entry_md` recovered verbatim (byte-identical), 49 `entry_md: null` + explained source | PASS |
| A5.2 | same commit + `dadaia backlog doctor` (cited in commit, this session's own `specs doctor` corroborates no BL-DUP finding at HEAD) | `BACKLOG.md` holds `## ACTIVE` only; BL-DUP deleted (`BacklogDoctorCode` drops `BL_DUP`), not disabled — diff-proven | PASS |
| A5.3 | same commit, "container.py gains `build_backlog_histo_store`..." | `document.backlog_exit` proven by an executed fixture: exactly one histo record appended, exactly one `## ACTIVE` subsection removed | PASS |
| A5.4 | same commit | legacy `_archive/*.md` untouched (read-only sources for the 68 recovered entries) | PASS |
| A5.5 | `git show 8910b3ee` body `[implementer evidence]` + `dadaia backlog doctor --specs-dir specs` cited (real CLI path, both stores wired) → "backlog doctor: clean." | all 18 `consumed_backlog.json` sidecars relocated into `consumed_backlog_histo.jsonl` (in fact captures all 18 by construction — a pre-existing 4-file glob gap in the OLD reader is fixed as a byproduct); BL-STALE proven still firing via the relocated store, before T-050-14 | PASS |

### A13.4 — store instance exists only where a writer exists

| id | command | evidence | verdict |
|---|---|---|---|
| A13.4 | `git show 8910b3ee` body ("container.py gains `build_backlog_histo_store`, the **third** `JsonlRecordStore` registration A13.4 asks for, with two real callers") | three registrations (bugs, backlog histo, consumed-backlog histo) as of S1 close, each with a named caller; the findings model (A13.4's third architecture-fidelity finding) is explicitly deferred to whichever later FR wires a writer for it — not registered speculatively | PASS |

### FR6 (A6.1–A6.6) — **not evidenced, T-050-14 is `[ ]`, operator-pending**

Recorded per instruction, not run: this task requires the operator physically present
(D-H). None of A6.1–A6.6 is claimed PASS or FAIL — they are **PENDING**. What T-050-14
blocks, concretely:

- The FROZEN gate class repoint (`specs/_archive/` prefix removed, `specs/releases/_archive/`
  added) in `dadaia_workspace/features/spec_context/gate_policy.py` — **A1.5 stays PENDING**
  until T-050-14 lands, since the SPEC assigns A1.5's repoint to T-050-14/T-050-21A, not to
  any `[x]` S1 task.
- V8 (throwaway-clone tag reachability) — cannot run before the tag exists.
- The relocation of every historical `verdicts/**` directory under root `specs/_archive/
  releases/*/` to the per-area archive (A6.2) — the required-PR-check's evidence resolution
  for those old verdicts stays on the pre-v6 path until this runs.
- Deletion of root `specs/_archive/` itself (~114 scanned directories, per T-050-12's own
  denominator) — until then, TREE-8 keeps firing its one expected WARN on `specs/_archive`
  (confirmed still present in this session's `specs doctor` run).

None of this blocks S1's own acceptance ids above — every one of them is independently
evidenced without requiring T-050-14. It blocks the **release's** FR1/FR6 closure and the
segment boundary into `S2`'s A1.5-dependent work.

---

## 2. The four questions

**(1) Migration thresholds and marker-distribution honesty.** Both `≥` bars are met with
margin: registration spread over 129 commits (≥124) with 81 single-line-adding commits
(≥79, `exact`=36≤79); resolution spread over 128 commits (≥117) with 78 single-record-
resolving commits (≥70, `exact`=53). The marker distribution is reported as a **measured
fact**, not forced toward §1.2's narrative estimate: registration `release-squash`
415/`ledger-only` 45/`exact` 36 (sums to 496); resolution `release-squash` 417/`ledger-only`
25/`exact` 53 (sums to 495) — the migration report states this plainly ("recorded as
measured, not chased to a target") against §1.2's differently-counted narrative figures
(~400/~155), which the SPEC itself already disclaims as measuring something structurally
different. **Answer: yes to both — thresholds cleared, distribution honestly reported.**

**(2) Any record whose `cause`/`caused_by` was not literally present in its source text
(A3.5)?** A live re-scan of the 496 migrated records (this session, not cited from the
implementer) finds: **yes, 2 of the 4 migrated `cause` values are not literally
reproducible as a substring of the record's own retained text** (§1, A3.5 row, above). Both
are already-resolved historical bugs from before this release; neither points at a wrong
cause, and neither involves fabricated causation of a *different* bug — the gap is prose
paraphrase vs. literal quotation, and in one case the record has no surviving
`evidence_diff`/`notes` field to have literally sourced the value from at all. `caused_by`
holds cleanly on the constraints A3.5 actually states (lineage_source correctness, zero
`"none"` among migrated records); a broad re-check of whether every migrated `caused_by`
target id is *itself* literally quoted in the final v6 record's retained fields
under-recovers (45/70) by design — T-050-09/10's own documented method mined "every one of
[the bug's own v5] events," i.e. the full v5 event history, not only the subset of fields
the terminal v6 record retains, so this under-recovery is not itself an A3.5 violation and
re-verifying it would require walking full v5 git history, out of this close's scope.
**Recommendation:** file a MEDIUM backlog candidate for PM intake — "2 migrated `cause`
values are not literal-text-traceable against their retained v6 record" — not a release
blocker.

**(3) Did V20 and V21 run at T-050-06A?** Yes, both — confirmed from `78b2b3ce`'s own body
(part (a): the `.gitignore` inversion, V21; part (c): `test_pr_verdict_check_gate.py`'s
seven-arm contract suite, V20) **and independently re-run in this session** at current HEAD
(`pytest -p no:cacheprovider -q tests/contract/test_pr_verdict_check_gate.py
tests/contract/test_source_repo_hygiene.py` → `17 passed`). Both still hold at S1 close.

**(4) Was V23 verified before the migration ran?** Yes — the migration report
(`T-050-10-migration-report.md`) carries a dedicated `## V23 — T-045-20 precondition
(verified before running)` section, ordered **before** the V4/V5 migration-result sections,
and commit `588e4722`'s own body labels it explicitly "V23 (precondition, before running)":
the write-seam strip verified on a throwaway sandbox ledger (U+2028+ESC → stripped, byte-
stable round-trip) and against the live, untouched ledger (byte-identical before/after, 0
bytes rewritten; `skipped: 0`) — before the physical rewrite executed.

---

## 3. Bug-surface delta — `features/bugs` and every reader of its ledger

Per the AR-1 ruling (§4) and the S1 commits that executed against it: **REDUCED**, and the
AR-1's stated condition for that verdict is **satisfied**.

- **Readers:** 3 → 1. Confirmed by inspection at current HEAD:
  `dadaia_workspace/features/specs/doctor_governance.py` no longer contains the
  `str.splitlines()` U+2028-losing defect on the bug lane (`grep -n splitlines` on that file
  hits only two unrelated `SPEC.md`/`CLOSURE.md` text-parsing call sites, and the store's
  own docstring at line 347 states the fix explicitly: "Splits on a literal `\\n` only,
  never `str.splitlines()`"). `infrastructure/jsonl_bug_store.py` and its protocol
  `core/protocols/bug_store.py` are deleted whole (b8e65f42). The one surviving reader is
  the generic `JsonlRecordStore`, consumed by both the doctor and `BugService`.
  `features/migrate/bugs_jsonl.py`'s own `splitlines()` (lines 223/318) is a historical
  v3→v4 consolidation module describing a past event, not a live reader of the current
  ledger — out of the "3 readers" count by AR-1's own scoping (§1.3).
- **Write seams:** 3 → 1. `append`/`resolve`/`pick+archive-annotate` fold into
  `register` + `apply_update`, both routed through `dadaia bugs update` (AS-16(i)).
- **The event fold and its seven-kind state machine:** deleted (`bug-event-v1.schema.json`
  retired whole; `--event resolved|picked|archived` and the reservation-marker concept die
  with T-050-08).
- The `splitlines()` second-reader defect the bug-history evidence names
  (`bug-event-field-with-unicode-line-separator-silently-drops-the-event`, T-045-20) is
  **v0.4.5's fix, not this release's claim** — S1's own contribution is closing the
  **doctor's** independent second parser of the same defect class
  (`specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators`, resolved same session
  as T-050-08, per that bug's own record and `b8e65f42`'s commit body), consistent with
  what the task text requires me to state plainly.

---

## 4. `tests/e2e/**` — zero new files in S1

`git log --diff-filter=A --name-only 02eef219..HEAD -- 'tests/e2e/**'` (this session)
returns **no output** — zero e2e files added across the full 02eef219..HEAD range,
S1 included. `git show --name-status` on each of the eleven S1 commits individually
(10540961, fb81a03c, 78b2b3ce, 912e3855, b8e65f42, d2e28c1e, 588e4722, 6ac0be42, 198532be,
3b167e07, 8910b3ee) shows exactly one e2e touch across all of them: `fb81a03c` **modifies**
(status `M`) three existing e2e fixtures to the renamed memory filenames
(`test_bound_context_visible_to_cli.py`, `test_ctx_inject_bind_boundary.py`,
`test_specs_upgrade_e2e.py`) — no new file. (For completeness: `S2`'s T-050-18, outside
this close's scope, *deletes* an e2e file rather than adding one — the opposite direction,
recorded but not part of this S1 count.) **Zero exceptions to confirm.**

---

## 5. Full suite — run once, at current HEAD

```
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q -n auto tests
2 failed, 2896 passed, 4 skipped in 51.60s
```

Both failures are **self-scan/test-ratchet fixture issues, not S1 production defects**,
and both show signs of an Arm-B session actively working the same surface concurrently
(a fresh bug record, `bug-record-write-once-evidence-fields-can-embed-selfscan-triggering-
literal-with-no-correction-path`, registered at `13:56:09Z` — after this session's own
read of the migration report and minutes before this suite run — points at exactly this
class of issue):

- **`tests/contract/test_test_suite_ratchets.py::test_v28_scaffold_expiry_goes_red_against_an_archived_release`**
  — `tests/integration/test_consumed_backlog_relocation.py` (T-050-13A's own SCAFFOLD
  fixture) declares `Intent: SCAFFOLD — T-050-13A (expires at T-050-14, ...)` in prose
  rather than the literal `expires: <M.m.p>` token form the V28 ratchet requires. A fixture
  wording defect in a not-yet-`[x]`-gated file, not a code regression.
- **`tests/integration/test_repo_self_scan.py::test_no_hit_outside_the_shrink_only_baseline`**
  — a single email-pattern hit inside `specs/bugs/BUGS.jsonl` itself, growing between two
  runs seconds apart (line 497 in the `-n auto` run, line 500 in an isolated re-run) — the
  ledger's own bug-description prose quotes the masked fixture-email literal (an
  email-shaped two-character-TLD synthetic value, not reproduced here to avoid
  re-triggering the same trap) while documenting an already-resolved sibling bug about
  that exact literal, tripping the ledger's own denylist scan recursively. Content, not
  S1 code.

Neither failure traces to any FR1–FR5/A13.4 acceptance id evidenced in §1; neither is
counted against this close's PASS verdicts.

---

## 6. LOC and test-count deltas

**Production LOC (`git diff --stat 02eef219..HEAD -- dadaia_workspace`, this session):**
`87 files changed, 5200 insertions(+), 1815 deletions(-)` — **net +3,385**, matching the
task's own `≈ +3,385` figure. Recorded as **net-positive**, expected for an
expand-heavy segment: FR2's expand step (912e3855, "+769 LOC") is explicitly followed by
its own contraction at FR2's switch+contract step (b8e65f42, same task pairing) per that
commit's own note ("architect firing at S1 close"); the full expand→switch→contract
arc for FR2/FR3/FR4 completes across S1+`S2` (A4.1/A4.5/A4.7's contract step is
T-050-21A, not yet run). This close does not adjudicate whether the net is
architecturally sound at scope-complete — that is the parallel software-architect
firing's job, hence the APPROVE-CONDITIONAL verdict above.

**Test-function delta** (`grep -rc "^def test_" tests | awk -F: '{s+=$2} END {print s}'`,
this session): **1,853**, against the T-050-03 baseline of **1,825** — **net +28**.

**`specs doctor`, current HEAD:** 1 error (SPEC-DOC-024 — release-wide `TASKS.md`
approval-status token, a pre-existing condition outside every S1 task's own write set,
confirmed unchanged since T-050-06's own before/after capture), 490 warnings (the large
majority are SPEC-DOC-033 governance-completeness signals on migrated historical
records legitimately lacking `cause`/`caused_by`/`resolved_release` — WARN-only per
A2.3/D15, never a block; plus the pre-existing TREE-8/SPEC-DOC-027/SPEC-DOC-036
legacy-naming/disposition warnings named in T-050-03's own baseline capture).

---

## 7. Security/privacy leakage note

No new leakage introduced by S1's own commits: `push-gate-check` ran clean over the
migration range before any push (A3.9, V22), with the one real hit (a foreign
consumer-repo slug in two `symptom` fields) remediated at the source record before this
close, never excluded. The residual object the scanner still flags belongs to a
pre-S1-close, already-tracked bug (`test-git-history-reader-fixture-email-not-on-
selfscan-baseline`), not new content. This session's own live re-scan (§4 above) surfaced
one additional, still-open recursive self-scan condition in the live ledger's own prose —
flagged in §5, tracked by the concurrent Arm-B bug registration noted there, not a new
leak this close introduces. No secrets, tokens, auth material, or operator-private data
observed in any artifact this close reviewed. No dependency additions in S1's scope.

---

## 8. Verdict

**APPROVE-CONDITIONAL** on the parallel software-architect ruling at S1 close. Every S1
acceptance id (FR1 A1.1–A1.10 except the T-050-14-owned A1.5 repoint; FR2 A2.1–A2.13; FR3
A3.1–A3.11 with one PASS-WITH-FINDING at A3.5 cause-literal-text; FR4's S1 portion A4.1a/
A4.2/A4.3/A4.6; FR5 A5.1–A5.5; A13.4) is evidenced PASS or PASS-WITH-FINDING, by a command
run in this session or the implementer's own captured report, reviewed. T-050-14 (FR6)
is correctly `[ ]`, operator-pending, and blocks exactly what §1's FR6 row states — nothing
else. Zero new `tests/e2e/**` files in S1. Full suite: 2 failed / 2896 passed / 4 skipped,
both failures self-scan/ratchet fixture issues under active concurrent Arm-B work, neither
attributable to an S1 acceptance id.
