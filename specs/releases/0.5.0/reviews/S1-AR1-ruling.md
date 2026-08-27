# AR-1 Ruling — the record model and the v5 boundary adapter (S1)

**Release:** 0.5.0 · **Segment:** S1 · **Task:** T-050-04 (SPEC FR2/FR3 · A2.5 · A3.10 · A13.4 · AS-16)
**Author:** software-architect · **Date:** 2026-08-27
**Mandate:** confirm or overturn the three AR-1 answers against the tree as it stands at
`feature/0.5.0` HEAD, and rule AS-16 in the operator's absence. Standing order applied:
permanent architecture review, oriented by bug history. No shell in this session — every
statement below is from `Read`/`Grep` inspection of the named files and lines.

**Verdict summary:** (a) **CONFIRMED**, one precision on the deletion list. (b) **CONFIRMED**,
five binding precisions on the store. (c) **CONFIRMED** — the existing `GitObjectReader` does
**not** cover the need and is not widened; the new narrow port is implemented by the
**existing** `GitSubprocessClient`, so no sibling adapter is born. **AS-16 → recommend (i)**
`dadaia bugs update`, overturnable by the operator.

---

## 0. Problem and prior art (architect-core-workflow)

**Core problem.** One record per bug id, immutable core, mutable governance rewritten in
place, with commit provenance derived from git history — without a second reader or writer
of the ledger and without a new `features → infrastructure`/`subprocess` edge.

**Constraints (from the tree).** `setup.cfg` contracts: `features-no-infrastructure`,
`features-no-subprocess`, `core-no-os-primitives`, `core-no-upper-layers`,
`features-no-cross-feature` (independence, `features.bugs` and `features.migrate` both
listed), `cli-no-infrastructure` with the `cli.commands.bugs → infrastructure.jsonl_bug_store`
ignore at `setup.cfg:232`; ignore-edge cap pinned at **15**
(`tests/contract/test_import_linter_ignore_cap.py:93`). `core/atomic_write.py` is a zero-import
core leaf (v0.4.5 AR-1). `migrate_v5.py` is SCAFFOLD, expires 0.6.0 (V28). Operator rules: no
CLI verb by reflex; hooks and CLI never block a human.

**Success criteria.** A2.5, A2.9, A2.13, A3.10, A13.4 provable on the executed path; the
number of hand-kept parsers of the bug ledger is **1** after T-050-08 (it is **3** at HEAD —
see §4).

**Assumptions made explicit.** (1) `specs upgrade` is not automated for v5→v6 (SPEC A1.4,
§9 item 23) — therefore no `features/migrate` step will ever import the v5 adapter.
(2) The `GitHistoryReader` port supplies `touched_paths` for the **whole** commit, not the
pathspec-filtered subset (see (c) line 4).

**Prior art surveyed.** `json-storage-manager` (whole-document JSON behind an atomic
`os.replace` context manager), `jk-keyvaluestore` (one file per key, last-write-wins),
the `eventsourcing` library's optimistic-concurrency (version-number compare-and-swap),
SQLite. None clears Fit + Integration: the ledger must remain a git-diffable
one-record-per-line text file — FR3 derives provenance from **added lines**, and the push
scan reads it as a blob — so a database or per-key files are out, and whole-document rewrite
is exactly the atomic replace the repo already owns. The CAS-by-version idea is adopted in
spirit as **refuse-stale on the snapshot re-read immediately before the rewrite**, over
`core/atomic_write.py`. Build it (≈80 LOC), no dependency.

---

## 1. Answer (a) — the v5 adapter lives in `features/bugs/migrate_v5.py`

1. **Verdict: CONFIRMED.** `features/bugs/migrate_v5.py` holds only the v5 line adapter, the
   legacy-`surface` mapping table and the one-shot runner; imported by no permanent module
   (A3.10's contract test), deleted with the migration.
2. **Tree evidence.** `features/migrate/registry.py:47-76` is the ordered, gap-refusing
   registry of specs migrations (`plan()` raises on a gap); FR1/A1.4 cuts the v5→v6
   automation, so no registry step will consume the adapter — placing it in `features/bugs`
   creates no cross-feature edge. **A `features.migrate → features.bugs.migrate_v5` import is
   forbidden by this ruling**: it would be a new `features-no-cross-feature` ignore edge
   (cap 15 → 16) for a deletable module.
3. **Bug history.** `bugs-jsonl-migration-wrote-hollow-events` (v0.1.47) and
   `bugs-store-fragments-into-hourly-files` (v0.1.73) are the two prior ledger migrations —
   both still live in `features/migrate/bugs_jsonl.py` (which still **writes** the retired
   hourly `<hour>Z-<n>.jsonl` shape at lines 296-322) and `bugs_single_file.py`. In this
   codebase "deletable" has meant "kept". The A3.10 zero-hit-grep contract test plus the V28
   SCAFFOLD expiry are the first mechanisms that make deletable enforceable — keep both.
4. **Precision on the A2.5 deletion list ("the v3→v4 consolidation").** What T-050-08 deletes
   is the **store-side dual-regime read** — `infrastructure/jsonl_bug_store.py` whole
   (`_BUG_LOG_RE`, `_sorted_files`, `_sort_key`, `ROWS_PER_FILE`, `CANONICAL_FILENAME`), its
   protocol `core/protocols/bug_store.py`, **and** the doctor's mirrors of the same constants
   (`features/specs/doctor_governance.py:40` `_BUGS_JSONL_ROW_CEILING`, `:43`
   `_BUGS_JSONL_NAME_RE`). The **registered step** `bugs-single-file` (3→4) in
   `features/migrate/bugs_single_file.py` is **not** deleted this release: `plan()` refuses a
   gap and a consumer below v4 must still reach v6. Collapsing the registry to a v6 floor
   needs registry-wide proof of no sub-v4 consumer — PM intake, not T-050-08.
5. **Trade-off.** Keeping the two old steps leaves ≈420 LOC of legacy-shape code alive in
   `features/migrate/`; the alternative — a no-op placeholder step — is a puxadinho and is
   refused. Cost accepted; the collapse is routed to intake with its proof requirement.

---

## 2. Answer (b) — a generic `infrastructure/jsonl_record_store.py`

1. **Verdict: CONFIRMED.** A generic `JsonlRecordStore` keyed by `id`, parse/serialise
   injected through a record protocol in `core/protocols/` (its own file, sibling of
   `git_object_reader.py`; name is the engineer's), one instance per feature model from the
   container; `jsonl_bug_store.py` and `core/protocols/bug_store.py` retire in T-050-08
   (expand → switch → contract, D-F).
2. **Tree evidence.** No generic store exists — `infrastructure/json_*_store.py` are
   per-model JSON documents and `jsonl_log_rotation.py` is an append-only log helper;
   `core/atomic_write.py` is the zero-import leaf the store may use. Three writers will exist
   (bugs FR2, findings FR13, backlog histo FR5), so A13.4's "one instance per writer that
   exists" holds with no speculative instance.
3. **Bug history — the reader class.**
   `bug-event-field-with-unicode-line-separator-silently-drops-the-event` (root cause
   `splitlines()` in the store reader, fixed T-045-20, ledger line 1006) was followed within
   a day by `bug-event-sanitation-strips-tab-lf-cr-from-free-text` (over-broad strip, 8.2 % of
   events word-joined, line 1014) — two fixes on one seam because the ledger has **three**
   hand-kept readers at HEAD: the store, `features/specs/doctor_governance.py:318`
   (`.read_text(...).splitlines()` — the **same defect, still live**), and
   `features/migrate/bugs_jsonl.py:223` (`splitlines()`). The record store is the one reader;
   the doctor lane (already in T-050-08's write set) **consumes it and deletes its parser**,
   or the record model does not reduce the surface (§4).
4. **Binding precisions on the store.** (i) It takes a file `Path`, never a directory plus a
   filename constant — the `BUGS.jsonl` name lives in the feature/container, so the store
   knows no ledger. (ii) Reads split on `"\n"` only (the T-045-20 root cause, carried, A3.7).
   (iii) `update(id, mutate)` re-reads immediately before `atomic_write` and refuses-stale by
   comparing the **re-read bytes (or their digest)** to the snapshot — never mtime
   (sub-second granularity, Windows) — raising a typed stale error the caller retries (A2.9,
   one race semantics). (iv) Zero knowledge of redaction or coherence: `BugRecord.redact`
   stays in `core/models/bugs.py` and `features/bugs/service.py` calls it on **both** write
   paths (A2.6); the store never imports a model. (v) The CLI obtains the service from a
   container seam (`container.build_bug_service(...)`) so the `setup.cfg:232` ignore is
   **deleted** and the cap moves 15 → 14 in the same commit; a direct
   `cli.commands.bugs → infrastructure.jsonl_record_store` import would re-create the edge
   and is refused.
5. **Trade-off.** One injected codec is one more indirection than a typed `JsonlBugStore`; it
   buys one parser for three ledgers and blocks the "one module knows three shapes" coupling
   (A13.4). Accepted.

---

## 3. Answer (c) — pure core derivation over a `GitHistoryReader`

1. **Verdict: CONFIRMED.** `core/bug_provenance.py` is pure and stdlib-only over an iterator
   of `(sha, parents, date, touched_paths, added_lines)`; git sits behind a **new narrow
   port** `core/protocols/git_history_reader.py` (`GitHistoryReader`, with the commit tuple
   shape and a typed read error), implemented by the **existing** `GitSubprocessClient` in
   `infrastructure/git_subprocess.py` (gains `log_added_lines(repo, pathspec)`), exposed by a
   container seam typed to the narrow port (`build_git_history_reader()`, mirroring
   `build_git_object_reader()` at `container.py:191`).
2. **Existing-reader check (the dispatcher's question).**
   `GitObjectReader.new_objects(repo, local_sha, remote_sha)` (`core/protocols/git_object_reader.py:99`,
   adapter `infrastructure/git_objects.py`, ≈930 LOC) answers "which objects does one pushed
   range publish": whole blob contents, deduplicated by object sha, no commit order, no
   parents or dates, no per-commit added lines, one exclusion formula scarred by
   `new-branch-push-loses-prior-published-denylist-amnesty`. FR3 needs a chronological
   all-refs history walk with per-commit added lines — a different contract. Widening that
   port would put two contracts on the push gate's seam: **REJECTED**. Widening the 13-method
   `GitClient` Protocol (`core/protocols/git_client.py`) is also refused (ISP:
   `tests/fakes.py:47 FakeGitClient` and every structural consumer would grow for one
   migration caller). One adapter class, one new narrow port — no sibling adapter module.
3. **Bug history.** `specs-bugs-jsonl-store-gitignored` (v0.1.47) is why the walk is `--all`
   including the 50 `archive/*` tags (AS-9, V6). The Windows-CI-only red family (memory:
   POSIX-only test, `as_posix()` file:line) applies here: `git_subprocess._run` (`:13-19`)
   uses `text=True` **without** `encoding=` (locale decode → cp1252 on `windows-latest`).
   `log_added_lines` must capture **bytes** and decode UTF-8 **strictly per line**, counting
   undecodable lines in the migration report rather than replacing characters — a
   replacement character would silently alter a ledger value. `_run` itself is not touched
   in T-050-09.
4. **Contract precision that changes the adapter's shape.** `touched_paths` must be the
   commit's **full** changed-path set — the `exact` marker requires "touches a file outside
   `specs/`" — but `git log -p -- specs/bugs/` restricts both `-p` and `--name-only` output
   to the pathspec. The adapter therefore pairs the pathspec-restricted added lines with an
   **unrestricted** per-commit path list (`git diff-tree -r --no-commit-id --name-only
   <sha>`, ≈295 calls once — acceptable for a one-shot — or one unrestricted `--name-only`
   log filtered client-side). The `tests/contract/` synthetic-repo test must contain a commit
   that adds one bug line **and** a non-`specs/` file (asserting `exact`) and a ledger-only
   commit (asserting `ledger-only`); otherwise the marker distribution is untested at the
   seam that produces it.
5. **Trade-off.** One new protocol file (+1 module) instead of overloading `GitClient`; the
   permanent consumers (FR8 resolver, FR14 pillar 1) import `core` only; `lint-imports` gains
   no edge (checked against every contract in `setup.cfg`: core → stdlib, infrastructure →
   core, features → core protocol, container composes). Accepted.

---

## 4. Bug-surface statement (standing order / FR24)

**Touched feature:** `features/bugs` and every reader of its ledger. **Ledger evidence
(`specs/bugs/bugs.jsonl`):** nine bugs on this surface since v0.1.46 —
`bugs-jsonl-migration-wrote-hollow-events`, `specs-bugs-jsonl-store-gitignored`,
`bugs-store-fragments-into-hourly-files`, `bug-evidence-field-bypasses-redaction`,
`bugs-append-ledger-ignores-context-flag`, `a2-bugs-append-context-resolution-ignores-repo-slug`,
`bugs-append-accepts-second-terminal-event`, `bugs-append-allows-terminal-event-without-reported`,
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` →
`bug-event-sanitation-strips-tab-lf-cr-from-free-text`.

**Repetition:** reader/writer shape drift, four times — hourly rotation (fixed by a
consolidation step kept forever) → `splitlines()` in the store (fixed) → `splitlines()` in
the doctor and the migration (**still live**) → write-time strip (over-broad, re-fixed).
**Structural cause:** N hand-kept parsers and writers of one file, each fixed
instance-by-instance.

**Direction of the three answers: REDUCED** — readers 3 → 1, write seams 3 → 1, the event
fold and its seven-kind state machine deleted, two protocols and one adapter retired, cap
15 → 14 — **conditional** on T-050-08 deleting the doctor's parser
(`doctor_governance.py:311-378` plus `:40-43`) and the migration's `_existing_bug_ids`
`splitlines()`, not merely "switching" beside them. If either survives, the release adds a
fourth reader and this verdict flips to **INCREASED**.

**Gates (§0.1).** Root-cause gate — **PASS**: the three answers address the structural cause
(parser/writer multiplicity; deletable code with permanent consumers), no workaround.
Architecture-fidelity gate — **PASS with corrections recorded** ((a)4 deletion-list
precision; (c)4 `touched_paths` contract; §5 finding 1, the doctor's second reader).

---

## 5. AS-16 — recommendation (the operator may overturn)

**Recommend (i): `dadaia bugs update <id> --set <field>=<value>`** — governance fields only,
schema-validated, exit codes unchanged (A8.3), refuse-stale reported as a non-zero exit with
"re-read and retry" (a validation the tool is designed to emit, never a block on a human),
CLI leaf count **71** after T-050-21A's two deletions.

**Why not (ii).** A "skill-invoked Python entry point" is a CLI with worse ergonomics: a
`python -m …` invocation differs from every other verb, has no `--help` or typer validation,
and — decisive — is **not exercised by `tests/integration/cli/**`**, the tier where every
writer bug on this ledger was proven fixed (`bugs-append-accepts-second-terminal-event`,
`bugs-append-allows-terminal-event-without-reported`, `bug-evidence-field-bypasses-redaction`,
the U+2028 and TAB/LF/CR pair — all fixed at `BugService` **because the CLI routes through
it**). Under (ii) two of the three writer roles stay one `python -c` away from a file tool,
which is the shape A2.13 exists to end.

**Standing order honored.** `append --event resolved|picked|archived` and their branches
(`cli/commands/bugs.py:194-224`, `:273-278`) die with the event kinds; `update` replaces
them — a vocabulary swap, leaves ±0, nothing blocks. **Conditions:** no coherence blocking in
`update` (WARN only, D15); a core-field `--set` is refused at the seam (A2.2a); the A2.13
fixture drives all three writer roles through the verb.

---

## 6. Findings for the dispatcher

### [HIGH] The doctor's bug lane is a second hand-kept reader carrying the fixed U+2028 root cause
Location: `dadaia_workspace/features/specs/doctor_governance.py:318` (`.read_text(...).splitlines()`), `:40-43` (`_BUGS_JSONL_ROW_CEILING`, `_BUGS_JSONL_NAME_RE`)
Issue: T-045-20 fixed `splitlines()` only in `jsonl_bug_store.iter_events`; the doctor re-parses the same file with `splitlines()`, so a historical record carrying U+0085/U+2028/U+2029 (the pre-`eb03d01b` history is unscrubbed) fragments into two "not valid JSON" SPEC-DOC-033 ERRORs while `bugs status` reads it whole.
Why it matters: diagnostic gate ≠ enforced gate — the v0.1.72-law violation that produced both `bugs-append-*` bugs — and it is the reader the record store must retire.
Trade-off if fixed: ≈70 lines of parser deleted in T-050-08; the doctor keeps its schema check and WARN rendering through the record reader.
Recommendation: T-050-08 reads through the record store and deletes the parser and both constants. PM registers the defect now (this session has no shell): `dadaia bugs append --bug-id specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators --event reported --reported-by software-architect --title "specs doctor bug lane still splits the ledger with splitlines()" --severity MEDIUM --surface "dadaia specs doctor" --component "features/specs/doctor_governance.py#check_bugs_jsonl_invariant" --context dadaia-workspace --tag ledger --symptom "doctor_governance.py:318 reads bugs.jsonl with str.splitlines(); a record carrying U+2028/U+2029/U+0085 is split into two fragments that each fail json.loads and emit SPEC-DOC-033 ERROR, while JsonlBugStore.iter_events (split on newline only since T-045-20) reads the same record whole" --repro "append a record whose free text carries U+2028 to a fixture ledger bypassing the write-seam strip (historical shape); run specs doctor; two SPEC-DOC-033 not-valid-JSON errors; bugs status lists the record" --expected "one reader of the ledger: the doctor consumes the record store; diagnostic gate equals enforced gate"`.

### [MEDIUM] `features/migrate/bugs_jsonl.py` still writes the retired hourly-file shape
Location: `dadaia_workspace/features/migrate/bugs_jsonl.py:296-322`, `:37` (`_ROWS_PER_FILE`), `:223` (`splitlines()`)
Issue: registry step 1→2 emits `<hour>Z-<n>.jsonl` files that only step 3→4 consolidates; under canon v6 both remain the only path for a pre-v4 consumer.
Why it matters: build-on-stale-layers — a v0–v3 consumer walking to v6 passes through two retired shapes and a third `splitlines()` reader.
Trade-off if fixed: collapsing the registry to a v6 floor deletes ≈420 LOC but requires registry-wide proof that no consumer sits below v4.
Recommendation: PM intake candidate `migration-registry-v6-floor`; not 0.5.0 scope (AS-8 full-consumption is unaffected — the v6 migration clause is T-050-10).

### [MEDIUM] `git_subprocess._run` decodes subprocess output with the locale
Location: `dadaia_workspace/infrastructure/git_subprocess.py:13-19`
Issue: `text=True` without `encoding="utf-8"`.
Why it matters: `log_added_lines` will read UTF-8 JSON ledger lines; on `windows-latest` a locale decode corrupts or raises — the CI-only red class already in the ledger's memory.
Trade-off if fixed: none for FR3 — `log_added_lines` reads bytes through its own call; the 13 existing methods keep their behavior this release.
Recommendation: T-050-09 implements `log_added_lines` on raw bytes with strict per-line UTF-8; `_run` is out of scope.

---

## 7. Disposition

Three answers confirmed with the precisions above; T-050-07/08/09 proceed against them.
AS-16 recommendation (i) recorded for the dispatcher to implement unless the operator
overturns it. Two intake candidates named (registry v6 floor; nothing else). One bug for PM
registration. No production code, tests, specs or TASKS touched by this session.
