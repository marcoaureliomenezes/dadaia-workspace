# S1 FR23 firing — ruling on the net-positive production diff

**Release:** 0.5.0 · **Segment:** S1 (T-050-04 … T-050-13A; T-050-14 operator-pending; T-050-15 `[-]`)
**Author:** software-architect · **Date:** 2026-08-27
**Trigger:** operator standing order (permanent architecture review oriented by bug history) — a
net-positive diff routes to the architect before acceptance. Reported range
`02eef219..HEAD -- dadaia_workspace` ≈ +5,200 / −1,815 (net ≈ +3,385); tests +5,072 / −3,544.
**Method:** no shell in this session. Every statement is from `Read`/`Grep` over the tree at
HEAD, the S1 commit subjects in the reflog, `S1-AR1-ruling.md`, SPEC §1/FR1/FR2/FR4/A2.5/A13.4,
`bug-history-forensic-100.md`, `architecture-metrics-baseline.md`, and the live
`specs/bugs/BUGS.jsonl`. Line counts below are **raw lines at HEAD** (counted), not diff stats.
Complexity numbers are **hand-computed from the source** where stated, else quoted from the
dispatch. What could not be measured is listed in §8.

**Verdict: SOUND-WITH-AMENDMENT.** The four permanent seams are the right shapes and the
`specs doctor` lane did **not** grow `#doctor` (it shrank it). The growth is not sound as it
stands on three points: (1) the permanent service still reads the ledger through the
deletable adapter and the ledger has **six** line parsers at HEAD, not one — AR-1 §4's
conditional flips to INCREASED on that axis until amended; (2) the event fold and its
state machine that FR2 and AR-1 both declare "deleted" are alive in `core/`, dead on the
executed path; (3) a brand-new reader (`core/release_events.py`) re-introduces the exact
`str.splitlines()` root cause the ledger's memory carries, and is read through three
copy-pasted disk readers. Seven amendments in §7, each a deletion or a collapse.

---

## 0. Problem, constraints, prior art (architect-core-workflow)

**Core problem.** Rule whether S1's +3.4k production lines are structure (seams that
replace hand-kept or duplicated paths, deletable-by-design migration code, data) or
puxadinho (branches, second code paths, readers beside readers), per module, with the bug
history as the evidence.

**Constraints (from the tree).** `setup.cfg` contracts unchanged in kind; ignore-edge cap
pinned at **14** (`tests/contract/test_import_linter_ignore_cap.py:100` — was 15, the
`cli.commands.bugs → infrastructure.jsonl_bug_store` edge is gone, AR-1 (b)(v) honored).
`core/` is a zero-file-I/O ring (`test_core_file_io_purity.py`). D15: nothing added blocks.
V28: an undeclared/unrenewed SCAFFOLD turns RED. `#upgrade ≤ 26`, `#doctor ≤ 30`
(`tests/contract/test_specs_cli_complexity_ratchet.py:35-36`).

**Success criteria.** AR-1 §0: hand-kept parsers of the bug ledger **= 1** after T-050-08
(3 at AR-1 time). SPEC A2.5: "no v5 branch survives inside the bugs feature after the
contract step". SPEC §1.6: "FR1 does not grow either function". A13.4: a store instance only
where a writer exists. A2.7: a doctor WARN comparing each record's immutable core against
FR3's first-add derivation.

**Assumptions made explicit.** (1) The reported diff range ends at HEAD, which already carries
S2 commits (T-050-16/17/18/18A/19 per the reflog); the numbers in the dispatch therefore
include S2 growth (`BugService.resolved_commit`, the test-suite ratchets, hooks de-slop). This
ruling attributes S1 modules only and names the S2 overlap where it touches them. (2) The
live ledger is fully migrated: `specs/bugs/BUGS.jsonl` carries **0** lines with an `"event"`
key and 2 records with `status: "open"` (grep-counted). Every v5-tolerant read path is
therefore exercised by the git history walk only, never by the live file.

**Prior art.** Surveyed in AR-1 §0 (whole-document JSON stores, per-key stores, CAS-by-version,
SQLite) — not re-run; nothing in S1 introduces a problem class that survey did not cover.
The one new question — "where does a permanent classifier of an immutable v5 history live" —
is an ownership question, not a library question; ruled in §7 A2.

---

## 1. The growth, attributed per class

| Class | Module (raw lines at HEAD) | Kind | Verdict |
|---|---|---|---|
| **(a) deletable-by-design** | `features/bugs/migrate_v5.py` **725** — `read_ledger` 95-143, `parse_ledger_lines` 146-184 (a second copy of the same tolerant loop), `_fold_v5_events`, `classify_ledger_line` 229-271, `LEGACY_SURFACE_MAP` 290-516 (≈225 lines, one row per legacy string), `run_migration`, `mine_cause`/`mine_caused_by`/`build_migrated_record` | expires 0.6.0 (V28, tests `Intent: SCAFFOLD — T-050-09 — expires: 0.6.0` in `tests/unit/features/bugs/test_migrate_v5_provenance_scaffold.py`) | **Mostly sound, two defects:** (i) the permanent service imports it for every read (§3 F1); (ii) `classify_ledger_line` is **not** deletable — git history is v5-shaped for 295 commits forever and FR8's permanent resolver calls it (`service.py:279`). `run_migration` has **no production caller** (grep: only its own module and tests) — dead in the package by construction; acceptable only because V28 schedules its death. |
| **(b) new permanent seams** | `infrastructure/jsonl_record_store.py` **148** · `core/protocols/record_store.py` **74** · `core/bug_provenance.py` **208** · `core/protocols/git_history_reader.py` **86** · `infrastructure/git_subprocess.py` +≈130 (`_run_bytes`, `_decode_lines_strict`, `_added_lines_for_commit`, `_touched_paths_for_commit`, `log_added_lines`) · `core/release_events.py` **161** · `container.py` +≈120 (four `build_*_store` seams 237-330, `build_git_history_reader` 215-234, `resolve_release_phase` 627-652) · `core/models/backlog.py` **374** (histo + consumed-histo models) · `features/backlog/ledger.py` **59** (rewritten onto the store) | replace: the event-sourced `jsonl_bug_store.py` + `core/protocols/bug_store.py` (both **gone** — verified by glob), the hourly-rotation reader and its two doctor mirror constants, the `ACTIVE.md` regex read (kept for the expand window), the in-file `## LEDGER` parser, the 18 `consumed_backlog.json` sidecar glob | **Sound in shape.** Record store: file `Path` not directory (b)(i) ✓, `"\n"` split (b)(ii) ✓, refuse-stale by re-read bytes (b)(iii) ✓ `jsonl_record_store.py:102-104`, no model import (b)(iv) ✓, cap 15→14 (b)(v) ✓. `bug_provenance` pure, classifier injected ✓. `GitHistoryReader`: bytes + strict UTF-8 per line, unrestricted `touched_paths` via `diff-tree` ✓ (AR-1 (c)3/(c)4 honored). **Defects:** `release_events.py:113` uses `str.splitlines()` (§3 F3); `RecordStore.path` exists only so callers can read the file behind the store's back (`record_store.py:49-55` says so) — the leak that enables F1; `BugService.archive` rewrites the file outside the store (§3 F4). |
| **(c) new doctor checks** | `doctor_structural.py` TREE-8 (+≈50) · `cli/commands/specs.py` `_render_recipe_steps`/`_print_recipe` (+≈22) · `doctor_governance.py` SPEC-DOC-040 458-495, SPEC-DOC-041 497-528, `_iter_native_bug_records` 131-154 · `doctor_release.py` SPEC-DOC-042 593-633, SPEC-DOC-043 635-668, `_fold_release_jsonl_phase` 86-103 · `hooks/sdd_gate.py` `_release_jsonl_phase` 158-182 + call 240-241 | all `Severity.WARNING`, `fixable=False`; none changes an exit code | **Measuring instruments, none a gate** ✓. But: **SPEC-DOC-040 never fires in production** — `bug_first_add_baselines` is passed by nobody (`cli/commands/specs.py:202-206` builds `SpecsDoctor` without it; `doctor_governance.py:469` returns `[]` on the empty default). A2.7 is unmet on the executed path (§3 F5). **SPEC-DOC-042** is an expand-window instrument that dies at T-050-21A — correct, provided it is actually deleted then. Doctor code count: 47 → **51** at S1 (+TREE-8, +040, +041, +042, +043, −BL-DUP which lives in the backlog doctor). The SPEC's §8 projection ("47 → ≤ 47") counted only +TREE-8; FR15 (S3) must now delete ≥ 4 to land at the SPEC's own ceiling. Recorded as a measured fact, not a failure. |
| **(d) schema / data** | `public/schemas/bugs/bug-record-v1.schema.json` (new; `bug-event-v1` deleted ✓), `public/schemas/releases/release-event-v1.schema.json`, `core/models/bugs.py` **804** (`BugRecord` 553-736 ≈ 185 lines + derived field tuples), `specs/bugs/BUGS.jsonl` (496 records), `RELEASE.jsonl`, `releases_histo.jsonl`, `backlog_histo.jsonl`, `consumed_backlog_histo.jsonl` | data + the one runtime mirror | **Sound with one carry-over:** `_OPTIONAL_STR_FIELDS` deleted ✓, field sets derived from `dataclasses.field(metadata=...)` ✓ (A2.10). **Not deleted:** `BugEvent` 375-494, `advance_coherence` 98-156, `BugCoherenceRecord`/`BugCoherenceViolation`/`diagnose_bug_coherence_history` 159-239 ≈ **260 lines** in `core/`, whose only consumers are the v5 fold in the deletable adapter and the v5 branch of the doctor lane — both dead against a ledger with zero v5 lines (§3 F2). |

**Where the +3.4k actually sits.** Roughly: (a) ≈ 725 (21 %); (b) ≈ 1,300 (38 %); (c) ≈ 300
(9 %); (d) ≈ 500 in `core/models/bugs.py` growth + schemas (15 %); the remainder is S2 spill
(`BugService.resolved_commit`, test ratchets, hook scripts) and docstrings — S1's modules
carry unusually long module docstrings (`migrate_v5.py` 53 lines before the first import;
`release_events.py` 25) which inflate raw counts without adding surface. Of the ≈ 3.4k,
the lines that are **retained-but-dead on the executed path** are ≈ 260 (core event
machinery) + ≈ 40 (`parse_ledger_lines` duplicate loop) + ≈ 40 (SPEC-DOC-040 never firing)
+ ≈ 25 (`_release_jsonl_phase` called and discarded in the hook) ≈ **365 lines** — the part
this ruling orders removed or wired.

---

## 2. Bug-surface direction per class, with the ledger as evidence

Surfaces named by the dispatch: public-assets 18/18, specs-doctor 13/12, bugs ledger
9 bugs, reader/writer drift class. Record ids cited are in `specs/bugs/BUGS.jsonl` at HEAD.

### 2.1 Bugs ledger (the 9 + 1) — class (a)+(b)+(d)

Evidence read from the migrated records: `bugs-jsonl-migration-wrote-hollow-events`,
`specs-bugs-jsonl-store-gitignored` (both `release-squash`), `bugs-store-fragments-into-hourly-files`
(HIGH), `bug-evidence-field-bypasses-redaction`, `bugs-append-ledger-ignores-context-flag`,
`a2-bugs-append-context-resolution-ignores-repo-slug`, `bugs-append-accepts-second-terminal-event`
(`registration_granularity: exact`), `bugs-append-allows-terminal-event-without-reported`,
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` (`resolution_granularity:
exact`, `diff_direction: net-neutral`), `bug-event-sanitation-strips-tab-lf-cr-from-free-text`
(HIGH, `net-negative`, its `evidence_diff` states the prior fix "mislabeled its +46/-5 diff
net-neutral … the label that let this HIGH gap skip FR23's architect-routing check"), plus
the one AR-1 filed: `specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators`
(resolved `b8e65f42`, T-050-08, `net-negative`, `exact`).

**Structural cause (AR-1 §4, still the right diagnosis):** N hand-kept parsers and writers of
one file. The two `bugs-append-*` bugs are "diagnostic gate ≠ enforced gate" — a coherence
rule asserted in the doctor and absent from the writer; the U+2028 pair is one reader fixed,
the sibling reader not.

**What S1 did to it — measured at HEAD.**

| Axis | AR-1 baseline | HEAD | Direction |
|---|---|---|---|
| Write seams to the live ledger | 3 | **3** — `JsonlRecordStore.append`, `JsonlRecordStore.update` (refuse-stale ✓), `BugService.archive` raw rewrite via `atomic_write` (`service.py:220-240`, **no refuse-stale re-read**) | **neutral** (should be 1) |
| Line parsers of the live ledger | 3 | **6** — `JsonlRecordStore.iter_records` (:119), `migrate_v5.read_ledger` (:118), `migrate_v5.parse_ledger_lines` (:162), `doctor_governance.check_bugs_jsonl_invariant` (:362), `doctor_governance._iter_native_bug_records` (:140), `BugService.archive` (:227 + `_line_record_id`) | **INCREASED** |
| Parsers using `str.splitlines()` on the ledger | 2 live | **0** — every one splits on `"\n"` | reduced (the U+2028 *class* is closed on this file) |
| Shape decoders | `BugEvent.from_dict` + 2 hand-rolled field checks | `BugRecord.from_dict` (1) + `BugEvent.from_dict` (dead-on-live) + `classify_ledger_line` (raw-dict, permanent by necessity) | reduced by one hand-rolled check |
| Event fold / state machine | live, enforced + diagnosed | **retained** (`advance_coherence`, `diagnose_bug_coherence_history`) as a WARN over a v5 portion that no longer exists | not deleted (SPEC FR2 and AR-1 §4 both say "deleted") |
| Diagnostic gate = enforced gate | no | **yes** for governance completeness: `governance_completeness_gaps` is one core function rendered by both `bugs status` and the doctor (`core/models/bugs.py:753`) | reduced — the shape of the two `bugs-append-*` bugs cannot recur |
| Hand-kept field lists | 1 (`_OPTIONAL_STR_FIELDS`, 16) | 0 in the models ✓; **1 new** in the adapter (`_CAUSED_BY_TEXT_FIELDS`, `migrate_v5.py:622`, 10 `BugEvent` field names) | reduced in permanent code; the adapter's list dies with it |
| Redaction on both write paths | append only | `register` and `apply_update` both `.redact()` ✓; `archive` copies bytes verbatim (no new text, acceptable) | reduced |

**Direction for the bugs feature: REDUCED on the writer/coherence/redaction axes,
INCREASED on the reader axis.** Under AR-1 §4's own conditional ("if either survives, the
release adds a fourth reader and this verdict flips to INCREASED") the honest statement is:
the doctor's *old* parser was rewritten (bug closed, `net-negative` diff) but the *count* of
readers doubled because the service never switched to `record_store.iter_records()` and the
doctor grew a second helper beside its rewritten lane. Amendments A1/A3 return the axis to
REDUCED with a net deletion.

### 2.2 specs-doctor (13 bugs / 12 re-bugged) — class (c)

Chain 1 engine: `cli/commands/specs.py#upgrade` (CC 26) and `#doctor` (CC 30). Ruling on the
"FR1 does not grow #doctor" claim is in §4: **not violated; `#doctor` shrank to ≈10.**

Five new WARN codes, zero new ERRORs, zero exit-code changes — consistent with forensic P6
("gate/doctor growth per bug: 22 additive fixes") being the class to stop: none of the five
is a per-bug guard; each names an invariant (canon root, first-add immutability, archive
age, expand-window agreement, milestone immutability). **But** two of the five carry the P6
shape in a milder form: SPEC-DOC-040 is a guard with no data behind it (the FR13 "documented
convention with no data" shape this very release condemns at T-050-13A), and SPEC-DOC-042 is
a check whose only purpose is to watch two authorities of one truth agree during a window —
P2 in the forensic. It is admissible **only** because T-050-21A deletes it; if 21A lands
without deleting `check_release_jsonl_agreement`, `_fold_release_jsonl_phase`, and the hook's
`_release_jsonl_phase`, the release will have added a P2 pair permanently.

**Direction: NEUTRAL now** (instruments, no blocks, `#doctor` down) → **REDUCED** if A5/A6
land; **INCREASED** if 21A forgets the expand-window code.

### 2.3 public-assets (18/18) — not touched by S1 production code

S1 ran projection cycles (scaffold v6 tree, `AGENTS.md` per area, `README.md` retirements)
and touched `public/scaffold/**` + two schemas. No `infrastructure/public_assets.py` or
`install_helpers.py` change in S1 modules. **Direction: neutral, and the SPEC says so
(§1.6, AS-17 deferral).** No ruling to make here beyond confirming the segment did not
add a roster, golden or hash literal — except one: `test_specs_cli_complexity_ratchet.py:40`
pins `features/migrate/upgrade.py` by a **hand-kept SHA-256 literal**. That is the
`shipped-hashes.json` shape (forensic P1, `upgrade-never-refreshes-uncustomised-scoped-law-projection`
— "a new hand-kept list was the fix"). It is a legitimate A1.4 zero-diff proof for **this
release only**; it must not outlive it (A7).

### 2.4 Reader/writer drift class — across (b) and (c)

`core/release_events.py` is a new append-only ledger reader whose file carries free text
(`note.data.text`, two long notes already in `specs/releases/0.5.0/RELEASE.jsonl`) and
whose parser splits with `text.splitlines()` (`release_events.py:113`). That is byte-for-byte
the root cause of `bug-event-field-with-unicode-line-separator-silently-drops-the-event`
(its `symptom` field: "iter_events reads with text.splitlines(), which splits on
U+2028/U+2029/U+0085/U+000B/U+000C") — re-introduced 3 days after that bug closed, in the
same release that made the fix a rule at every other reader (`git_subprocess.py:43-45`,
`jsonl_record_store.py:116`, `migrate_v5.py:109`, `doctor_governance.py:347` all cite it).
No writer-side strip exists for `RELEASE.jsonl` — agents append it with file tools by
design (A4.6, read-only fold) — so the reader is the only defence, and it is the wrong one.
**Direction: INCREASED on the drift class** until A4.

Second instance of the same class: the tri-state disk read of `RELEASE.jsonl` is
implemented three times — `hooks/sdd_gate.py:174-182`, `container.py:644-652`,
`features/specs/doctor_release.py:96-103` — identical bodies. The module docstring
(`release_events.py:12-17`) defends this by precedent (`_active_field` vs `read_active_md`,
"two independent readers of the same file"). The precedent is the defect: it is the
`ACTIVE.md` shape FR4 exists to retire, and the "N readers of one file" cause named in
AR-1 §4. The core file-I/O purity ratchet is the stated reason; it is not a reason to
copy the reader three times — it is a reason for **one** reader outside `core/` (A4).

---

## 3. Findings

### [HIGH] The permanent bug service reads the ledger through the deletable adapter, not the injected store
Location: `dadaia_workspace/features/bugs/service.py:57`, `:162`, `:286`, `:292`, `:303` (`migrate_v5.read_ledger(self._record_store.path)`); `dadaia_workspace/core/protocols/record_store.py:49-55` (`path` property, whose docstring names this bypass as its purpose); `tests/contract/test_migrate_v5_not_imported_by_permanent_consumer.py:44-46` (whitelists `service.py` as "retired by T-050-10 per migrate_v5.py's own module docstring" — T-050-10 landed and the import did not retire)
Issue: `BugService` holds a `RecordStore[BugRecord]` and never calls `iter_records()`; every read goes to `read_ledger`, which re-implements the store's loop with a v5 fold on top. The live ledger has 0 v5 lines. The module the SPEC calls "imported by nothing else and deletable with it" (A2.5) has a permanent importer on five lines, and the contract test that should catch it pins the exception.
Why it matters: build-on-stale-layer, the exact AR-1 §4 failure condition. At 0.6.0 the "git rm" the SPEC promises breaks `status`, `stats`, `register`'s duplicate check and `coherence_violations`. Until then the feature carries two readers of one file — the cause behind the U+2028 pair.
Trade-off if fixed: −5 import sites, −49 lines (`read_ledger`), the `path` property leaves the protocol; `register`'s duplicate check becomes `any(r.id == bug_id for r in self._record_store.iter_records())`. Risk: a foreign v5 write to the live file is no longer folded — correct: the doctor reports it (SPEC-DOC-033 ERROR), the reader does not silently adapt.
Recommendation: Amendment A1 — switch all five reads to `self._record_store.iter_records()`; delete `read_ledger`; delete `RecordStore.path` (the archive rewrite moves into the store, F4); flip `_KNOWN_MIGRATE_V5_IMPORTERS` to the empty set **after** A2 relocates the classifier.

### [HIGH] The v5 event fold and its state machine were declared deleted and are alive in `core/`
Location: `dadaia_workspace/core/models/bugs.py:98-156` (`advance_coherence`), `:159-239` (`BugCoherenceRecord`, `BugCoherenceViolation`, `diagnose_bug_coherence_history`), `:375-494` (`BugEvent`, `_BUG_EVENT_OPTIONAL_STR_FIELDS`); consumers `dadaia_workspace/features/specs/doctor_governance.py:384-403`, `:436-456` (`_fold_bug_coherence`), `dadaia_workspace/features/bugs/migrate_v5.py:187-226` (`_fold_v5_events`)
Issue: SPEC FR2 ("`BugEvent` + fold logic deleted") and AR-1 §4 ("the event fold and its seven-kind state machine deleted") are not met. ≈260 lines of v5 machinery remain in the permanent bottom layer, consumed only by (i) the deletable adapter's fold and (ii) the doctor's v5 branch — and the live ledger contains zero v5 lines, so both consumers are dead on the executed path. `BugEvent.redact`/`to_dict` are write-side methods of a shape that has no writer.
Why it matters: stale code in `core/` is read by every developer as current truth (`core/models/bugs.py` opens with "`BugEvent`, the retired-but-still-read v5 event shape"). Architecture-fidelity: the SPEC misrepresents the layer's contents. The forensic's `memory-token-estimate-normalizer-dead-code` → `memory-catalog-regenerator-orphaned-factory` chain is exactly "deletion exposes the next dead function".
Trade-off if fixed: −≈260 lines in `core/`, −≈70 in the doctor (the `"event" in obj` branch becomes an ERROR: "v5 line in a v6 ledger — run the migration"), −≈40 in the adapter. Historical coherence over v5 history is FR14 pillar 1's job, reading git, not the doctor's job reading a file that no longer holds events. Cost: the adapter's `mine_*` functions read `BugEvent` fields — they die at 0.6.0 anyway; until then they can consume raw dicts (they already receive `events_for_id` from `parse_ledger_lines`, which can return dicts).
Recommendation: Amendment A3 — delete `BugEvent`, `advance_coherence`, the two coherence dataclasses and `diagnose_bug_coherence_history` from `core/models/bugs.py`; keep `BugEventKind`/`TERMINAL_EVENTS` (the classifier's vocabulary); the doctor's v5 branch becomes a single ERROR line; the adapter parses raw dicts. SPEC FR2 text then matches the tree.

### [HIGH] `core/release_events.py` re-introduces `str.splitlines()` on a free-text JSONL ledger
Location: `dadaia_workspace/core/release_events.py:113` (`for lineno, raw_line in enumerate(text.splitlines(), start=1)`)
Issue: `RELEASE.jsonl` carries free text in `note.data.text`; the file is appended by file tools with no write-time strip (by design, A4.6). A U+2028/U+2029/U+0085 in a note fragments the record into two lines that each fail `json.loads`, are recorded as parse errors and **dropped** — with `_errors` discarded by all three callers (`sdd_gate.py:181`, `container.py:651`, `doctor_release.py:102`, `:651`). A `phase` record after such a note is unaffected, but a milestone record on the same physical line is lost silently.
Why it matters: same defect, same release, different file — the loop the SPEC §1 exists to make visible. The ledger's own `bug-event-field-with-unicode-line-separator-silently-drops-the-event` record names the mechanism verbatim.
Trade-off if fixed: one-token change (`text.split("\n")`); zero behaviour change for well-formed files. Surfacing `_errors` is a separate, optional improvement (the doctor could render them under SPEC-DOC-043's sibling); not required for this ruling.
Recommendation: Amendment A4 — `split("\n")`; add the one-line RED test the T-045-20 fix used (a note carrying U+2028 folds to one event, not zero). Register the bug (ADDITIVE): surface `specs`, component `core/release_events.py#parse_release_events`, `caused_by: bug-event-field-with-unicode-line-separator-silently-drops-the-event`, `lineage_source: declared` — the release's first record with a declared lineage, which is the point of FR2.

### [MEDIUM] `BugService.archive` is a second write path to the ledger, outside the store, without refuse-stale
Location: `dadaia_workspace/features/bugs/service.py:211-241`, `:322-333` (`_line_record_id`)
Issue: the archive reads the raw text, drops eligible lines, and `atomic_write`s the remainder. It never re-reads before the rewrite (A2.9's race semantics live only in `JsonlRecordStore.update`), and it owns its own line loop and id extractor. A2.13's "every governance-field write goes through the record store" is true for `update` and false for `archive`.
Why it matters: two write seams with different race semantics on one file — the P2 shape ("two writers / two authorities of one truth", 14 bugs). A concurrent `bugs update` between the archive's read and its write is clobbered.
Trade-off if fixed: the store gains `remove(record_ids) -> list[T]` (≈20 lines: same read-snapshot / filter / re-read-compare / `atomic_write` as `update`); the service loses ≈35 lines and the `path` dependency. Net negative, one race semantics.
Recommendation: Amendment A1 (second half) — `RecordStore.remove`; `archive` = `eligible → store.remove(ids) → archive_store.append(each)`.

### [MEDIUM] SPEC-DOC-040 is a check that cannot fire in production
Location: `dadaia_workspace/features/specs/doctor_governance.py:175`, `:186`, `:469-470`; `dadaia_workspace/features/specs/doctor.py:74`, `:114`; `dadaia_workspace/cli/commands/specs.py:202-206` (no `bug_first_add_baselines` argument)
Issue: A2.7 promises "a `specs doctor` WARN comparing each record's immutable core against FR3's first-add derivation". The check exists; its input is an empty dict everywhere; the docstring says "a genuine production no-op until FR3/T-050-09 threads a real git-derived mapping" — T-050-09 is `[x]` and threaded nothing. The derivation it needs (`derive_commit_provenance` + the classifier over `GitHistoryReader`) is a ≈2N+1 subprocess walk (`git_subprocess.py:424`), which the doctor must not run on every invocation.
Why it matters: the FR13 shape ("documented convention with no data behind it") inside the doctor, plus an unused constructor parameter threaded through two classes. A future reader trusts A2.7 and finds a WARN that has never once been emitted.
Trade-off if fixed: two honest options. (i) Delete the check and its plumbing (−≈60 lines) and move A2.7 to FR14 pillar 1, which already owns the git walk and the `audited` rewrite — the audit is where a first-add snapshot is cheap. (ii) Wire it: the doctor accepts an optional `--provenance` flag that runs the walk once. (ii) adds CLI surface (D15 refuses) and ≈300 subprocess calls per doctor run.
Recommendation: Amendment A5 — option (i). The SPEC amends A2.7 to name pillar 1 as the detector. Zero doctor CC is added; one code (040) leaves; the count returns toward the §8 projection.

### [MEDIUM] Three copy-pasted tri-state readers of `RELEASE.jsonl`, and a hook read whose result is discarded
Location: `dadaia_workspace/hooks/sdd_gate.py:158-182`, `:240-241` (`if release_raw: _release_jsonl_phase(specs_dir, release_raw)` — return value unused); `dadaia_workspace/container.py:627-652`; `dadaia_workspace/features/specs/doctor_release.py:86-103`
Issue: identical 10-line bodies in three layers, justified by the `core/` I/O ratchet. The hook additionally performs a file read on **every gated write** for a value it throws away ("intentionally unused here"). `resolve_release_phase` in the container has, at HEAD, no caller (grep: definition only).
Why it matters: N readers of one file (AR-1 §4's structural cause) reproduced on the new file on day one; an unused seam is dead code behind a docstring (A13.4's own principle); a no-op read on the hot path is a side effect with no consumer.
Trade-off if fixed: one reader function in a non-core home the hook may import without the container — `features/spec_context/gate_policy.py` is already the hook's sanctioned feature import (4 edges), or a new tiny leaf `features/specs/release_state.py`; the doctor and the container call the same function. The hook's discarded call is deleted now and re-added at T-050-21A as the **decision** read (its only legitimate form). −≈35 lines now.
Recommendation: Amendment A6 — one `read_release_phase(specs_dir, release_id)` outside `core/`; delete the hook's discarded call and the container's uncalled seam until 21A needs them.

### [MEDIUM] `consumed_backlog_histo.jsonl` is a second authority for a fact `backlog_histo.jsonl` already records
Location: `dadaia_workspace/core/models/backlog.py:339-374` (`ConsumedBacklogHistoRecord`, `consumed: list[dict[str, object]]` — untyped entries), `dadaia_workspace/features/backlog/ledger.py:49-58` (`.get("slug")`, `.get("shipped_anchors")` over raw dicts), `dadaia_workspace/container.py:307-330`
Issue: `BacklogHistoRecord` carries `disposition` and `release` per slug (`backlog.py:279-281`) — "consumed by release X" is derivable from it. T-050-13A relocated the 18 sidecars into a fourth store and a schema-less record rather than folding them into the histo the same task created one commit earlier. Two files now say which slug left the backlog for which release.
Why it matters: P2, the forensic's second-largest class. The relocation was correct in intent (do not let BL-STALE go quiet); the shape is a puxadinho: one more model, one more registration, one more file, no type.
Trade-off if fixed: BL-STALE's `shipped_anchors` per slug is the one field `BacklogHistoRecord` lacks; adding it (optional, `list[str]`) and back-filling the 18 releases into `backlog_histo.jsonl` deletes `ConsumedBacklogHistoRecord`, `read_consumed`'s dict walking, one container seam and one file (−≈120 lines). Cost: a one-shot back-fill of 18 records and the T-050-13A fixture rewritten against the histo.
Recommendation: Not an S1 blocker — route to intake as `backlog-histo-single-authority` with the deletion list above; T-050-14 may proceed (it depends only on the data being somewhere tracked).

### [LOW] `parse_ledger_lines` duplicates `read_ledger`'s loop inside the deletable module
Location: `dadaia_workspace/features/bugs/migrate_v5.py:95-143` vs `:146-184`
Issue: two copies of the same tolerant JSON/shape loop, 40 lines apart, differing only in whether the file is read; `read_ledger` could be `_fold_v5_events(*parse_ledger_lines(path.read_text()))`.
Why it matters: the module's own docstring promises "without a second, independently-maintained parse of this module's own tolerant JSON/shape decoding" — and then keeps two. Dies at 0.6.0; folds into A1 (`read_ledger` deleted) at zero extra cost.
Recommendation: covered by A1.

### [LOW] Stale references and a hand-kept field list in the adapter
Location: `dadaia_workspace/infrastructure/jsonl_record_store.py:115` (cites deleted `jsonl_bug_store.JsonlBugStore.iter_events`); `dadaia_workspace/core/protocols/record_store.py:11` (cites deleted `core/protocols/bug_store.py` as a live sibling); `dadaia_workspace/features/bugs/migrate_v5.py:622-633` (`_CAUSED_BY_TEXT_FIELDS`, ten `BugEvent` field names — the A2.10 shape)
Recommendation: fix the two docstrings when touching the files (A1 touches both); the tuple dies with the module (V28) — no action.

### [LOW] The A1.4 zero-diff proof is a hand-kept hash literal with no expiry
Location: `tests/contract/test_specs_cli_complexity_ratchet.py:40`, `:63-71`
Issue: `_UPGRADE_MODULE_SHA256` pins `features/migrate/upgrade.py` forever; the assertion's stated scope is "under T-050-05". It is P1's `shipped-hashes.json` shape in the test tier (forensic P4, "guard breeds guard").
Recommendation: Amendment A7 — mark that test `Intent: SCAFFOLD — T-050-05 — expires: 0.6.0` (V28 then retires it), or delete it at T-050-34 once V19 measures the diff. The CC ratchet in the same file is permanent and correct.

---

## 4. Ruling on "FR1 does not grow `#doctor`"

**Not violated — reversed.** `cli/commands/specs.py#doctor` at HEAD (`:138-222`) is a
dispatcher: option parsing, `SpecsDoctor(...)`, `check()`, then four extracted helpers
(`_print_migration_hints`, `_apply_doctor_fix`, `_print_json_result`/`_print_human_result`,
`_print_recipe`). Hand-computed cyclomatic complexity from the source: base 1 + `if … and …`
(2) + `if context` (1) + `if public_dir` (1) + `if fix` (1) + `if recipe` (1) + `elif
json_output` (1) + the `any(...)` generator (1) + the `1 if has_errors else 0` ternary (1)
= **10**, matching the "30 → 10" the dispatch reports for T-050-05. `--recipe` is rendered
in `_render_recipe_steps` (`:115-125`, CC 2) — its own function, A1.3 ✓ — and renders the
same `SpecsDoctorIssue` objects `--json` emits (no second table) ✓. T-050-08's two checks
and T-050-11's two checks live in the validator classes (`doctor_governance.py`,
`doctor_release.py`), each ≈ CC 4-6, and are wired by one `issues.extend(...)` line each in
`SpecsDoctor.check` (`doctor.py:184-190`) — `#doctor` in the CLI is untouched by them.
`#upgrade` (`:244+`) was not read line-by-line; the ratchet pins it ≤ 26 and
`features/migrate/upgrade.py` is byte-pinned — A1.4 holds by test.

**One amendment follows from the measurement:** the ratchet ceiling
`_DOCTOR_CEILING = 30` (`test_specs_cli_complexity_ratchet.py:36`) is now 20 points above
reality. A ratchet that does not ratchet lets `#doctor` regrow to 30 silently — the chain-1
engine re-armed. **Amendment A8:** pin `_DOCTOR_CEILING` at the `radon` value measured in
the same commit (10 by this reading; the engineer records the tool's number), per the
file's own rule "lowering is welcome".

Doctor-check code count at S1: **51** (47 − BL-DUP + TREE-8 + 040 + 041 + 042 + 043).
Expected after A5 and T-050-21A: 49; the SPEC's ≤ 47 then rests on FR15 deleting ≥ 2.

---

## 5. Architecture-fidelity gate (§0.1 gate 2)

**PASS with corrections recorded** — the SPEC must be amended in the S1 close fold on four
points, each a misrepresentation of the tree:

1. **A2.5** "imported by nothing else and deletable with it": `classify_ledger_line` is
   permanent (immutable v5 git history; FR8's resolver at `service.py:279` and FR14 pillar 1
   need it forever). Correction: "the v5 **fold** adapter (`read_ledger`, `_fold_v5_events`,
   the surface map, the runner and the miners) is deletable; the **line classifier** is
   permanent and lives in `core/bug_provenance.py` as the default `LineClassifier`, importing
   only `core.models.bugs.BugEventKind`/`TERMINAL_EVENTS`" (Amendment A2 — this is a
   `core → core` edge; the A3.10 purity test still passes since it forbids `features` imports
   only).
2. **FR2 / AR-1 §4** "`BugEvent` + fold logic deleted": not at HEAD (F2). Correction lands
   with A3.
3. **A2.7** names the doctor as the detector: the doctor has no data (F5). Correction lands
   with A5 (pillar 1 is the detector).
4. **FR4** "one reader, one fold, three callers": one fold, **three readers** (F6).
   Correction lands with A6.

**Root-cause gate (§0.1 gate 1) — PASS.** The one bug S1 closed in production code
(`specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators`, `b8e65f42`) is a
root-cause rewrite (`net-negative`, two hand-kept constants deleted), not a patch. No other
bug fix is in the S1 range's production diff. The two bug-registration commits in the range
(`chore(bugs): …`, `fix(bugs): ruff-format …`) touched tests/ledger only.

---

## 6. Bug-surface verdict (FR24 / `dd-bug-registration` §5), one line per feature

| Feature | Direction at HEAD | After amendments | Evidence |
|---|---|---|---|
| `features/bugs` | **mixed** — writer/redaction/coherence reduced; readers 3 → 6 | **REDUCED** (readers → 1 store + 1 doctor loop; writers → 1 store) | 10 ledger records §2.1; AR-1 §4 conditional |
| `core/models/bugs.py` | **increased** (+≈260 dead lines) | reduced (−≈260) | F2 |
| `features/specs` doctor lane | **neutral** (5 WARNs, `#doctor` 30 → 10) | reduced (040 out, 042 out at 21A, ceiling pinned) | §4, F5 |
| `core/release_events.py` + callers | **increased** (`splitlines`, ×3 readers, discarded hot-path read) | reduced | F3, F6 |
| `features/backlog` | reduced (`## LEDGER` parser and BL-DUP gone, BL-STALE data kept) with one P2 residue | — (intake) | F7 |
| `infrastructure` (store, git reader) | reduced (event store + hourly reader gone; cap 15 → 14) | — | (b) row, `test_import_linter_ignore_cap.py:100` |
| public-assets | neutral, as the SPEC states | — | §2.3 |

---

## 7. Verdict and amendments

**SOUND-WITH-AMENDMENT.** S1 may close only with the following landed on the branch, each a
net-negative or net-zero production diff, before T-050-15's QA close is committed:

| # | Amendment | Deletes | Adds | Owner |
|---|---|---|---|---|
| **A1** | `BugService` reads via `self._record_store.iter_records()`; `RecordStore.remove(ids)` replaces the archive's raw rewrite; `RecordStore.path` and `migrate_v5.read_ledger` deleted; `_KNOWN_MIGRATE_V5_IMPORTERS = frozenset()` | ≈ 90 lines | ≈ 20 (`remove`, mirrors `update`) | software-engineer |
| **A2** | `classify_ledger_line` moves to `core/bug_provenance.py` (permanent); `service.py:279` and `migrate_v5.run_migration` import it from there; SPEC A2.5 corrected as §5.1 | 0 | 0 (move) | software-engineer + product-engineer (SPEC text) |
| **A3** | Delete `BugEvent`, `advance_coherence`, `BugCoherenceRecord`, `BugCoherenceViolation`, `diagnose_bug_coherence_history` from `core/models/bugs.py`; the doctor's `"event" in obj` branch becomes one SPEC-DOC-033 ERROR ("v5 line in a v6 ledger — migrate"); `_fold_bug_coherence` deleted; the adapter's miners take raw dicts | ≈ 330 lines | ≈ 8 | software-engineer |
| **A4** | `release_events.py:113` → `split("\n")`; RED test (U+2028 note folds to one event); bug registered with `caused_by` declared (F3) | 0 | 1 line + 1 test | software-engineer (register: any agent) |
| **A5** | Delete SPEC-DOC-040 and the `bug_first_add_baselines` plumbing (`doctor.py`, `doctor_governance.py`); SPEC A2.7 names FR14 pillar 1 as the detector | ≈ 60 lines | 0 | software-engineer + product-engineer |
| **A6** | One `read_release_phase()` outside `core/` used by the doctor (and by the container/hook at 21A); delete `sdd_gate._release_jsonl_phase` + its discarded call and `container.resolve_release_phase` until 21A | ≈ 45 lines | ≈ 12 | software-engineer |
| **A7** | `test_specs_cli_complexity_ratchet.py::test_migrate_upgrade_module_is_untouched_by_fr1` marked `Intent: SCAFFOLD — T-050-05 — expires: 0.6.0` | 0 | 1 docstring line | software-engineer (qa-engineer verdict recorded) |
| **A8** | `_DOCTOR_CEILING` pinned at the measured `radon` value (≈10) | 0 | 0 | software-engineer |

Expected effect on the reported range: production ≈ −520 lines net; readers of the bug
ledger 6 → 2 (store + doctor loop over `BugRecord.from_dict`); write seams 3 → 1;
`core/` loses its v5 write-side shape; the drift class has zero `splitlines()` readers of
any governance JSONL.

**Not blocking S1, routed to PM intake:** `backlog-histo-single-authority` (F7);
`migration-registry-v6-floor` (AR-1 §6, unchanged); the doctor-code ceiling arithmetic
(47 → 51 → FR15's obligation) for T-050-34's measurement.

**Standing-order statement.** Every amendment above removes a branch, a second code path or
a duplicate reader; none adds a flag, a CLI verb, a hook block or a cross-feature edge. A1
and A3 are the two that decide whether this release's bugs feature is smaller than v0.4.5's
or merely differently shaped.

---

## 8. What this session could not measure

- `git diff --stat` per file and the per-commit `+769` of T-050-07: taken from the dispatch;
  raw-line counts at HEAD substituted (§1).
- `radon cc` for `#doctor`/`#upgrade`: `#doctor` hand-computed (§4); `#upgrade` not read
  line-by-line — relies on the ratchet test being green at HEAD.
- Whether `lint-imports` and the full suite are green at HEAD: relied on T-050-13A's done
  marker and the pinned cap test; not re-run.
- S1's QA close (`S1-qa-close.md`) does not exist yet (T-050-15 is `[-]`); this ruling
  precedes it by design (TASKS: "the `software-architect` AR-1 confirmation" + this firing
  gate S1).

**Disposition.** Ruling written; no production code, tests, specs or TASKS touched by this
session. Handoff to the dispatcher: land A1–A8 (one task-group commit per amendment or as
the dispatcher batches them), re-run the two contract tests named in §3 F1/§4, then commit
T-050-15.
