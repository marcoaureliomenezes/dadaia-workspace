# software-architect — definition review of release 0.5.0 (Draft trio)

**Reviewed:** `specs/releases/_ideas/0.5.0/{SPEC,PLAN,TASKS}.md` (read in full) against the
2026-08-26 grill handoff (D1–D15), the six named backlog entries, the operator's standing
order, and the live code the FRs touch. **Mode:** REVIEW. **Verdict:** **REWORK (targeted)** —
one CRITICAL root-cause-gate failure and two HIGH structural gaps; everything else is sound
and the rework is textual to the trio, not a re-scoping.

## 0. Core-workflow trail

- **Core problem** (operator's words, SPEC §1 states it correctly): the agent, fixing one
  bug, creates others; the loop is invisible because no record carries cause, lineage or a
  diffable commit, and no audit reads history.
- **Constraints:** D15 (no new blocking CLI/hook), layer contracts in `setup.cfg` (nine
  import-linter contracts, `features` never imports `infrastructure`/`subprocess`, hooks
  never import the container), `main` squash-only (history is coarse), `product-engineer`
  has no shell.
- **Success criteria:** FR16's dry run rediscovers the four documented chains (A16.2); zero
  new blockers (A22.6); every FR's bug-surface direction measured (A22.3).
- **Prior art surveyed (by inspection, no web needed):** Nygard/MADR ADRs (D12 adopts them);
  expand→switch→contract for schema retirement (D-F); "JSONL as a document keyed by id" with
  atomic replace — the standard practice the SPEC omits (finding F2); first-add-wins
  chronological derivation over `git log --all` — sound and O(history), better than pickaxe.

## 1. Axis verdicts

| Axis | Verdict | Evidence |
|---|---|---|
| 1 Purpose fidelity | **PASS** | SPEC §1 opens with the operator's sentence; §1.4 pillars; every FR carries "Bug-surface direction" + "Bug-history evidence"; §7 maps FR7/FR14/FR16 to the standing order. Wording defect only: §1.1 says "four recurrences" while listing eight ids (ledger holds nine, the ninth `v0.4.4-reviews-dir-untrackable-gitignore-recurrence`) — F5. |
| 2 Root-cause gate | **FAIL** | FR2 claims the record model closes the U+2028 family, but the seam is live and unfixed (F1). FR1 (gitignore class → TREE-8), FR9 (hooks), FR7 (certify/frozen-clock) name the structure correctly. No puxadinho found in FR9/FR12/FR15/FR21; one latent in AS-1 (§3 below). |
| 3 Architecture fidelity | **GAP** | Layering respected on paper (PLAN §2 "no new accepted edge"). Gaps: FR4 consumer set understated (F3); shared record store must be model-agnostic (F6); ADDITIVE class vs mutable record unaddressed (F2). |
| 4 Bug-surface accounting | **PASS with corrections** | Per-FR directions credible; FR2's "net-negative" is only true after F1; deletion list can be larger (§4). |
| 5 Ruling fidelity | **PASS** | No sentence contradicts D1–D15. Two drifts of degree: D3's `implemented` = "final rc QA close" sha vs T-050-42 writing it at the final-rc PR merge (pick one, state it); D-A names the marker `commit_granularity` while FR2's record uses `registration_granularity`/`resolution_granularity` (F8). |
| 6 Unsettled decisions | see §3 | AS-1 **RE-DECIDE**; D-A, D-G, AS-3, AS-5, AS-11 **SOUND**. |
| 7 Simplification | see §4 | Five concrete cuts. |

## 2. Findings

### [CRITICAL] FR2/FR3 layer a new record model on the live U+2028 seam — the release's own first build-on-stale-layer
Location: `dadaia_workspace/infrastructure/jsonl_bug_store.py:75` (`text.splitlines()`);
`specs/bugs/bugs.jsonl` line 984 (`bug-event-field-with-unicode-line-separator-silently-drops-the-event`, `reported`, **no terminal event** — SPEC AS-4 says the only open bug is `windows-xdist-…`, which is false on this tree).
Issue: `str.splitlines()` splits on U+2028/U+2029/U+0085; a record whose `symptom` carries one is read as two malformed lines and skipped with a log WARN. FR2's argument ("one line per bug means a corrupt line loses one bug, loudly") is not true — the same reader loses the whole bug, and `bugs status` renders no count of skipped lines. A3.7 tests "no silent drop" on the migrated corpus, which contains no such character, so it passes without proving anything.
Why it matters: this is exactly the loop the release exists to end — a structural defect paved over by a bigger structure. The migration would even carry the character through, so the first future audit reads a record that the CLI cannot.
Trade-off if fixed: ~6 lines (reader splits on `"\n"` only; writer serialises with `ensure_ascii=True` or escapes U+2028/2029; the reader surfaces `skipped: N` in `bugs status`); one fixture with U+2028 in a field.
Recommendation: close the bug as Arm B **before or inside T-050-07** with that fix; add **A2.6** "a record containing U+2028/U+2029 in any field round-trips byte-identically and `bugs status` reports skipped-line counts"; correct AS-4 to list this bug.

### [HIGH] The ADDITIVE class assumed append-only writes; a mutable-field record breaks that assumption and the SPEC does not say how
Location: `dadaia_workspace/features/spec_context/gate_policy.py:49-53` (`specs/bugs/` ADDITIVE, always writable, any mode, no phase); SPEC FR2 "a governance update rewrites that record's line in place"; `DADAIA.md` §3 row "Always writable — register bugs freely".
Issue: (a) the immutable core is enforced only at the service seam (A2.2); any agent's `Edit` tool rewrites any field and the gate cannot tell — it reads no content. The SPEC implies enforcement it cannot have. (b) In-place rewrite is read-modify-write; two sessions (the sanctioned NO-LOCKS race) can lose each other's line. `O_APPEND` made the event stream race-benign; nothing in FR2 replaces that property. (c) The `DADAIA.md` §3 wording becomes stale.
Why it matters: silent lost updates on the one file the whole release depends on; a "measured truth" ledger whose immutability is a sentence.
Trade-off if fixed: zero gate change (D15 honoured); ~15 lines in the store; one pillar-1 measure.
Recommendation: state plainly in FR2 that immutability is **discipline measured by audit, never gate-enforced**; add to pillar 1 (FR14) the measure "a hunk in `git log -p -- specs/bugs/BUGS.jsonl` that changes a core field of an existing id = HIGH finding"; require the update seam to write through temp file + `os.replace` and to re-read immediately before rewriting (A2.2 amendment); FR11 rewrites the §3 ADDITIVE row to "always writable; the record contract is audited, not gated". No new path class, no second classifier.

### [HIGH] FR4's `ACTIVE.md` retirement understates its consumer set and its layer placement
Location: TASKS T-050-11 write set (three code files); `dadaia_workspace/hooks/sdd_gate.py:137-155` (`_active_field`); 28 files reference `ACTIVE.md` in `dadaia_workspace/` — `container.py`, `features/specs/{doctor,doctor_common,doctor_release,doctor_structural,scaffolder}.py`, `features/reports/next.py`, `cli/commands/specs.py`, `core/exceptions.py`, six personas, five skills, `scaffold/AGENTS.md`, `templates/specs-AGENTS.md`, `DADAIA.md`.
Issue: the contract step (delete `ACTIVE.md`, "no fallback branch") lands in `S1` while the personas/skills/law that cite it are owned by FR11/FR12 in `S2` — an expand→contract violation by the SPEC's own D-F: for a whole segment the always-on law names a file that does not exist. The fold that replaces `_active_field` is not placed; hooks must not import the container (standing law), so it must be a pure `core` function.
Trade-off if fixed: none in code; task ordering only.
Recommendation: T-050-11 enumerates every consumer above; the `RELEASE.jsonl` fold is `core/release_events.py` (stdlib json, tri-state like `_active_field`) called from `hooks/sdd_gate.py`, `container.py` and the doctor; the **contract step moves to `S2` after T-050-21** (or the persona/skill citations move into T-050-11 with `ai-engineer` as co-owner). A4.5 then reads "at least one commit" honestly across the segment boundary.

### [MEDIUM] Release id `0.5.0` collides with the archived spec-lineage release `v0.5.0`
Location: `setup.cfg:256` ("v0.5.0 FR1"), `core/models/bugs.py:151` ("v0.5.0 FR2"), `hooks/sdd_gate.py:193` ("v0.5.0 code review") — 46 citations in 28 files; `specs/_archive/releases/v0.5.0/` (shipped 2026-08-12, before the version-axis collapse).
Issue: pillar 2, FR16 and every external reader will read "v0.5.0 FR2" as this release's FR2 (a different subject). Nothing in SPEC §7 "Version lineage" mentions it.
Recommendation: one paragraph in §7: `v0.5.0` (2026-08-12) belongs to the retired spec-lineage axis; `0.5.0` is the PyPI axis; in-code citations `v0.5.0 FRn` refer to the archived release and are **not** renamed. Pillar 2's window recipe excludes the `v`-prefixed archived id from this release's history.

### [MEDIUM] The shared record-update seam is a cross-cutting helper unless it is model-agnostic
Location: PLAN §2 (`infrastructure/jsonl_bug_store.py` "serving bugs, findings and the backlog histo"); TASKS T-050-04 (b), T-050-23.
Issue: a module named and typed for `BugEvent` that also folds findings and backlog records is the hidden coupling the standing order forbids; three features would share one file that knows all three shapes.
Recommendation (this is the AR-1 answer to T-050-04 (b), given now): the seam is admissible **only** as `infrastructure/jsonl_record_store.py` — a generic `JsonlRecordStore` keyed by `id`, parse/serialise injected through a `core.protocols` record protocol; each feature owns its model (`core/models/{bugs,findings,backlog}.py`) and gets its own store instance from the container. The legacy hourly-file reader (`_BUG_LOG_RE`, `_sorted_files`, `ROWS_PER_FILE`, v3→4 consolidation) is deleted in the same task — it is dead under canon v6.

### [MEDIUM] AR-1 (a) and (c), answered now so T-050-04 becomes a confirmation
(a) The v5 adapter lives in the migration module (`features/bugs/migrate_v5.py`), imported by nothing else; A2.5 stands. (c) The FR3 derivation is a **pure core function** over an iterator of `(sha, parents, date, touched_paths, added_lines)`; git access is a `core.protocols.GitHistoryReader` implemented in `infrastructure/git_subprocess.py` (`GitSubprocessClient` gains `log_added_lines(pathspec)`), injected via the container — no `subprocess` in `features`, no new accepted edge. Unit tests run the pure function on an in-memory history (T-050-09's synthetic repo becomes unnecessary; a fixture list suffices).

### [MEDIUM] `picked` as a status drops `picked_by`, the only NO-LOCKS race evidence the fold keeps
Location: `features/bugs/service.py:42-50`; SPEC FR2 status vocabulary.
Recommendation: drop `picked` from `status` entirely — the pick is already recorded by the bundled definition commit (FR8 shape 5) and readable by pillar 2. Smaller enum, one fewer transition, nothing lost. D11 lists `status` as mutable but fixes no vocabulary, so this is admissible without re-litigation.

### [LOW] Marker field naming (F8) and §1.1 counting (F5)
Unify on `registration_granularity` / `resolution_granularity` everywhere (D-A, FR14 "filters `commit_granularity == "exact"`"). Rewrite §1.1 row 1 as "one class, nine registered instances, three patched instance-by-instance, the last self-labelled *fourth recurrence*".

## 3. Unsettled decisions (SPEC §8)

- **AS-1 — RE-DECIDE → option (ii).** "Derive-on-read is the authority **plus** a follow-up ledger-only cache commit" is two writers of one value kept equal by a contract test — the definition of a second path. The handoff's option (ii) already names the cleaner shape: `resolved_commit` stays `null` at resolve time and is filled by **pillar 1** in the same in-place rewrite that sets `audited`. One writer (the audit), one resolver, zero extra commits per bug, FR8 shape 3b deleted, A8.2's test reduces to "audit-filled equals derived". The follow-up-commit variant also fails D10's "fix contained in the resolving commit" spirit by adding a second ledger commit per bug that pillar 2 must then recognise.
- **D-A markers — SOUND** (closed enumerations on a record; the alternative is heuristic sniffing). Fix the naming (F8).
- **D-G `releases_histo.jsonl` — SOUND**; symmetric with the two existing histo files. Read the archive before FR6 (already gated).
- **AS-5 `feature/0.5.0` — SOUND**, with F4's lineage note.
- **AS-3 frozen legacy archive — SOUND**; converting prose to structured truth would fabricate evidence.
- **AS-11 lineage as `dd-diagnose` phase 0 — SOUND**; one procedure, one statement.

## 4. Simplification opportunities

| # | Cut | Effect |
|---|---|---|
| S1 | AS-1 → option (ii) (above) | −1 commit shape, −1 skill paragraph ×3, −1 CLI-adjacent seam; the resolver keeps one signature |
| S2 | Drop `picked` status (F7) | −1 enum value, −1 fold branch, −`picked_by` |
| S3 | FR4 event kinds: keep `phase`, `defined`, `implemented`, `shipped`, `audited`, `rc` (open/close as `data`), `note`; drop `created`, `spec_status` (the SPEC header is the source), `review`, `push`, `pr`, `ship` (duplicate of `shipped`), `archive` (= `phase: ARCHIVED`) | 15 → 7 kinds; smaller schema, smaller fold, nothing D3 requires lost |
| S4 | FR1 `--recipe`: do not add a flag; `specs upgrade` prints what it did and what it cannot do (its existing output channel) | zero new CLI surface; same information |
| S5 | Delete with FR2, explicitly: `BugEventKind`, `TERMINAL_EVENTS`, `advance_coherence`, `diagnose_bug_coherence_history`, `BugCoherenceRecord/Violation`, `_OPTIONAL_STR_FIELDS`-driven `to_dict` event shape, the legacy hourly reader (F6), SPEC-DOC-033's fold; with FR4: `_active_field` and its regex, `doctor_closure_audit.py` CLOSURE regexes, `AUDIT_DIR_NAME_RE` (single new home for the `<YYYYMMDD>-<slug>` shape, also the comment at `gate_policy.py:41-42`) | names the deletion so V19 measures it |
| S6 | T-050-04 becomes a five-line confirmation of §2 F6/AR-1 above | −1 segment gate |
| S7 | FR14 pillar 1 adds one cheap measure: registration→resolution interval; the ledger shows `certify-cannot-install-installed-provider` reported 18:41:56Z and resolved 18:41:57Z (bulk registration of an already-"fixed" bug) — the no-red-loop signature the certify chain exemplifies | detects the certify class mechanically |

## 5. Verdict

**REWORK (targeted).** The purpose, the rulings and the segment architecture are right; the
trio must not be approved while FR2 stands on an open, unfixed defect of the exact seam it
claims to close. Gate record: **Root-cause gate: FAIL** (F1). **Architecture-fidelity gate:
FAIL** (F2, F3, F6 — abstractions are right, placement and consumer set are not).

**Five changes for `product-engineer`, in priority order:**
1. F1 — fix the line-splitting seam as Arm B before/inside T-050-07; add A2.6; correct AS-4.
2. F2 — FR2 states immutability is audited not gated; atomic replace + re-read at the update seam; pillar-1 "core field changed" measure; FR11 rewrites the §3 ADDITIVE row.
3. AS-1 → option (ii); delete FR8 shape 3b; A8.2 becomes "audit-filled equals derived".
4. F3 — T-050-11 lists every `ACTIVE.md` consumer; fold in `core/release_events.py`; contract step after T-050-21.
5. F6/AR-1 pre-answered: generic `jsonl_record_store.py`, migration-owned v5 adapter, pure derivation over a `GitHistoryReader` protocol; T-050-04 becomes a confirmation. Plus F4's lineage note and the S2–S4 cuts.

**Bug-surface statement.** As defined, the release **reduces** the bug surface of hooks
(FR9: `precommit-backlog-doctor-blocks-unrelated-commits` + `backlog-doctor-blocks-consumed-item-refactor-commit` are the registered causes; two blockers deleted, none added), of the
specs doctor's prose parsing (FR15; the SPEC-DOC-0xx false-positive class), of the backlog
ledger (FR5; BL-DUP structurally impossible), of the AI surface (FR12/FR21; the stale-citation
class, `dadaia-task-manager-stale-workspace-protocol-citation`), and of the bugs feature's
state machine (FR2 deletes the fold that produced `bugs-append-accepts-second-terminal-event`
/ `…-without-reported` and the pick-after-terminal branches). It **increases** the surface of
release state (FR4: a new schema, fold and histo — justified by D3/D7, shrinkable by S3) and
of the specs doctor (FR1: TREE-8, `--recipe` — S4 removes half of that). For the bugs store
specifically the direction is **negative only if F1 and F2 land**: without them the record
model is a second floor over the live `splitlines()` defect and a new lost-update race — the
frozen-clock shape (`no-ratchet-against-frozen-clock-…` → `frozen-clock-ratchet-scans-tests-tmp-scratch-dir`, ledger lines 933→1004: a guard that bred its own bug) repeated on the
ledger itself. With the five changes applied, the release is net-negative on every touched
feature except release state, and that addition is the operator's ruling.
