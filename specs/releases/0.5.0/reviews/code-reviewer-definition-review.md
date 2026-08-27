# code-reviewer — definition review of release 0.5.0 (cold-external-reader pass)

**Reviewer:** `code-reviewer` · 2026-08-26 · read-only (no commit, no push) · **CI:** n/a (no PR,
no branch, no code delta — this is a definition review).
**Subject:** `specs/releases/_ideas/0.5.0/{SPEC,PLAN,TASKS}.md` — 2 817 lines, read in that order.
**Authority:** grill handoff `2026-08-26T120000Z-…-adr-grill` (D1–D15, findings[0..2]); the six
`BACKLOG.md` entries at `:155`, `:342`, `:394`, `:454`, `:519`, `:564`.
**Tree:** branch `feature/0.4.5`, HEAD `49d9afa8` (4 files dirty from live v0.4.5 work).

---

## 1. Findings

### Axis 3 — fidelity to D1–D15 and to the entries

All fifteen rulings are honoured **in substance**: D1 §2.1:140 · D2 FR2/FR3/FR8 · D3 FR4:461-474 ·
D4 (no push on resolve) FR8 rule 4, `SPEC:638-640` · D5 FR13:835-841 · D6 (cadence) FR14:901 ·
D7 (window) FR14:903-906 · D8 FR7:566-580 + A7.5:619 · D9 FR9:672-688 · D10 FR8:626-642 ·
D11 (record model) FR2:319-331 + FR13:843-847 · D12 (operator-only acceptance) FR19:1068-1106 +
FR20:1123-1138 · D13 FR17:991-998 · D14 (full map) FR10:706-726 · D15 §1.4:117-120 + A22.6:1178.
The entries' concrete examples survive undiluted: BUGS record before/after (`SPEC:337, 344`),
`RELEASE.jsonl` milestones (`:470-473`), FINDINGS record (`:850-851`), ADR skeleton (`:1075-1096`),
`Measured by:` P-04 (`:1000-1009`), the `caused_by` evidence block (`:576-580`). Drift:

- **HIGH — the provenance marker has two names, and FR14 filters a field the schema lacks.** D-A
  (`SPEC:160`) and PLAN §0 (`PLAN:31`) say `commit_granularity`; FR2's field list (`SPEC:324-325`),
  the example record (`:337`), FR3 and FR7 (`:571`) say `registration_granularity` /
  `resolution_granularity`. FR14 pillar 1 then filters `commit_granularity == "exact"` (`:887`),
  which no record carries. *Fix:* one name, stated once in FR2, cited by D-A, PLAN §0, FR14, §8.
- **HIGH — `dadaia bugs archive` is declared consumed but never specified.** `specs-canon-v6`
  requires the idempotent verb (terminal records >90 d → `bugs_histo.jsonl`, doctor overdue-WARN,
  `BACKLOG.md:346`). The SPEC mentions it only in passing (`SPEC:416-417`): no FR, no task, no
  acceptance — while AS-8 (`:231`) forbids partial consumption.
- **MEDIUM — D14 cardinality inverted.** D14 goes RED when a `DADAIA.md` section has **no** owner;
  A10.1 (`SPEC:739-740`) demands **exactly one** owner row per section, forbidding two skills
  sharing §7 Quality — as the map's own rows already do (`:715, 720`).
- **MEDIUM — dropped entry requirements:** `RC-FLOW.md`'s `dd-architecture-survey` operative
  pointer (`BACKLOG.md:425`) is absent from FR12 (`SPEC:795-798`); FR1 retires `specs/assets/`
  (`:284`) but no task names it, `specs/backlog/remote-bugs/`, or the `../assets/` link fixes the
  entry requires (`BACKLOG.md:357`) — T-050-06's write set is `TASKS:278-282`. Both exist at HEAD.
- **LOW —** two spellings of the follow-up commit shape (`BACKLOG.md:468` vs `SPEC:224, 637`) while
  A8.1 demands each be stated exactly once; `superseded_by` is a new field undeclared in §8
  (`:1331-1334`); the entries' `P-12` and `F011` examples are dropped without note.

### Axis 2 — internal consistency (SPEC ↔ PLAN ↔ TASKS)

**Coverage is complete:** every FR1–FR22 has ≥1 task; every task cites its FR and acceptance ids
(`TASKS:90-134`); the segment maps agree across all three files (SPEC §3 / `PLAN:114-153` /
`TASKS:31-41`); ids are contiguous T-050-01…43; no numbering gaps.

- **HIGH — A3.2/A3.3 derive acceptances from the wrong unit.** §1.2 measures *79 commits that
  register exactly one bug* (`SPEC:71`) and *155 resolved **bugs** whose resolving commit is a
  release squash* (`:74`). A3.2 turns 79 into "**≥79** marked `exact`" (`:439`) — but `exact` also
  requires a non-`specs/` file (`:400-401`), so the true figure is ≤79 and the acceptance is
  probably unsatisfiable. A3.3 (`:441-442`) puts "≥155 marked `release-squash`" inside a list of
  *distinct commits* while 155 counts *bugs*, and defines the marker by line count where §1.2
  measured it by commit message. T-050-10 then tells the implementer that a low count "means the
  ref scope was wrong, not that the ground truth moved" (`TASKS:388-389`) — sending a correct
  migration back to chase a wrong target.
- **HIGH — D-B promises a file→FR ownership assignment that §3 does not contain.** `SPEC:172`
  claims "§3 assigns exactly one owning FR to every file". No such table exists, and the write sets
  contradict it for ≥5 files: `infrastructure/jsonl_bug_store.py` (T-050-07, 23),
  `features/bugs/service.py` (T-050-08, 09, 17), `features/spec_context/gate_policy.py` (T-050-06,
  11, 14), `hooks/sdd_gate.py` (T-050-11, 14), `tests/**` (everywhere). A11.1's proof "by
  inspection of §3" (`:778`) is not executable. The four *named* single-writer files
  (`DADAIA.md`, `constitution.md`, `behavior-map.json`, `dd-bug-resolution/SKILL.md`) do hold —
  verified against every write set.
- **MEDIUM —** V3 is defined (`SPEC:1266`) and assigned to no task, T-050-15 included; V1–V19 are
  otherwise all placed. · AS-9 says "295 of the 295 ledger commits are reachable only with the
  tags" (`:232`) while §1.2 puts 75 on `main` (`:68`) and T-050-14 says 220 (`TASKS:488`) —
  measured here: 295 ledger commits, 50 `archive/*` tags, so 220 is right. · The headline deletion
  count is stated three ways — "removes **one** of each" (`:120`), "**two** fewer hook blocks"
  (`:131`), "removes two" (`:1179`) — while FR9 removes three things. · FR2's "the record's shape
  never changes" (`:333-335`) is false in its own example (`:337` omits `root_cause`, `solution`,
  `superseded_by`, all required later at `:344, :365`): with `additionalProperties: false` there is
  a third category — *write-once, absent until set* — that A2.2 (`:361-363`) does not test.
- **LOW —** 132 of **471** resolutions (`:57`) vs **470** in §1.2/A3.3 (`:72, 441`); measured:
  `status:resolved 470`. · `PLAN:89` lists `catalog.py` (in no write set), omits `doctor_release.py`
  and `doctor_governance.py` (both in write sets), and has no `features/backlog/**` row at all.

### Axis 4 — the worked example of the loop (the operator's stated purpose)

- **HIGH — the end-to-end example exists but is fragmented and never assembled.** The pieces are
  present with consistent ids: the record carrying `caused_by` (`SPEC:337, 344`), the lineage
  declaration with `git show` evidence (`:576-580`), the pillar-1 finding naming both bugs and both
  shas (`:850`), its disposition (`:851`). Nothing walks a reader through *bug A's fix commit →
  bug B's record → pillar-1 finding → disposition* as one story, and the first hop appears only as
  a bare sha. Three defects compound it: the ids (`…-048`, `frozen-clock-guard-tz-boundary-031`,
  `4c1d2e3`, `9d8e7f6`) are **invented** — verified absent from `specs/bugs/bugs.jsonl` — while
  §1.1 uses real ids and nothing marks the difference; the disposition's `reason` cites `T-050-04`
  (`:851`), which in *this* release is the AR-1 architecture ruling, not a fix; and the second
  FINDINGS line is not valid JSON (`"…same immutable fields…":"…"`), so it cannot seed a fixture
  for a schema with `additionalProperties: false`. **This is the #1 gap**, exactly as anticipated:
  the release exists to make the loop visible and never shows it being seen once.
- **HIGH — A16.2's reference set is not falsifiable.** A16.2 (`:969-972`) makes "names, with
  evidence, at least the four documented chains of §1.1" an acceptance, but §1.1 gives ids for one
  chain only, and that row is self-contradictory: labelled "**four** recurrences" over **eight**
  ids (`:52`), one literally named `…-fourth-recurrence`. The certify and frozen-clock chains carry
  no ids (`:53-54`); the ledger chain names one of its two (`:55`). A reviewer cannot decide
  whether the dry run passed.

### Axis 5 — write sets vs the tree at HEAD

All 54 production paths checked exist at HEAD. Drifts:

- **HIGH — BL-DUP is in the wrong module.** T-050-13 (`TASKS:456`) puts its deletion in
  `features/specs/doctor_governance.py`; BL-DUP lives at `features/backlog/doctor.py:98` (also
  `:11, :134, :223, :248`). No write set names `features/backlog/**`, though FR5 retires the
  in-file LEDGER that `features/backlog/{document,ledger}.py` parse.
- **HIGH — the FR4 write set misses most `ACTIVE.md`/`CLOSURE.md` consumers.** T-050-11
  (`TASKS:405-411`) names `doctor_release.py`, `gate_policy.py`, `sdd_gate.py`. At HEAD `ACTIVE.md`
  is also read or written by `cli/commands/specs.py:32,37,370,404` (the `dadaia specs release` /
  `specs segment` verbs), `features/specs/doctor_common.py:20,32-54`,
  `features/reports/next.py:4,108-118`, `core/exceptions.py:76`, plus `doctor.py`,
  `doctor_structural.py`, `scaffolder.py`; `CLOSURE.md` appears in seven modules
  (`doctor_closure_audit.py` ×9, `doctor_release.py` ×8, `doctor_governance.py` ×7,
  `doctor_structural.py` ×3, `doctor_common.py`, `catalog.py`, `memory_lint.py`). A4.1's "no
  fallback branch left behind" cannot be executed inside the declared write set.
- **MEDIUM — A1.5 pins the wrong file.** `SPEC:308-311` proves the MEMORY-phase repoint "by the
  diff on `features/spec_context/gate_policy.py`", which has zero `ACTIVE.md` references; the phase
  read is `hooks/sdd_gate.py:138-146,204` (TASKS gets this right). Related: `gate_policy.py:63-65`
  **already** carries the per-area `_archive/` FROZEN prefixes, so FR6/A6.3's "repoint" is really
  "delete `_FROZEN_PREFIX` at `:73`, add `specs/releases/_archive/`" — smaller than stated.
- **MEDIUM — T-050-12 scans half the archive.** `TASKS:436` says "for every release under
  `specs/_archive/releases/`" — 93 directories, four of them not versions
  (`ctx-inject-v2-drift-fix-v1`, `memory-markdown-source-v1`, `multiharness-engine-v0116`,
  `pi-fourth-harness-v1`). A second layout at `specs/_archive/<release-id>/` (30 entries, e.g.
  `v0.1.47`…`v0.2.3`) is not scanned. V7's "line count = archived-release count" (`SPEC:1270`) has
  no defined denominator.
- **LOW —** T-050-21 (`TASKS:665`) lists `specs/backlog/AGENTS.md` and `specs/releases/AGENTS.md`,
  neither of which exists at HEAD, without the `(new)` marker other tasks use.

### Axis 1 — clarity for a cold reader

`PLAN §0` (`PLAN:20-33`) is a genuine asset, but the read order is SPEC → PLAN, so every SPEC-first
use precedes its definition. Undefined or late-defined, with first SPEC use:

| Term | First use | Defined |
|---|---|---|
| `seam` `:55` · `FR23` `:53` · Arm B `:1210` | SPEC | `SPEC:586-587` (532 lines later) / only `PLAN:29` / only `PLAN:24` |
| `histo` `:196` · "live photo" `:508` · TREE-5 `:804` | SPEC | never |
| "one-axis law" and operator law "O5" `:229` · "thawed tree" (`PLAN:146`, `TASKS:993`) | SPEC/PLAN | never |
| presence `:672` · verdict gate `:488` · purge-on-pick `:641` | SPEC | late or never |

`puxadinho` (`:115`), `rc-N` (`:212`), TREE-8 (`:286`) and `[-]` (`TASKS:25`) **are** defined at
first use. **MEDIUM — §1 is not a checkable statement:** it is descriptive; the falsifiable form
appears only at A16.2 (`:969`). Hoist a one-paragraph success statement into §1.

### Axis 6 — dead weight, and things that are not what they claim

- **MEDIUM — AS-5/6/7/9 are not assumptions.** AS-5 (`:228`) decides a branch name; AS-6 (`:229`)
  restates existing operator law; AS-7 (`:230`) grants this Draft an exemption; AS-9 (`:232`)
  states a measured fact (295 commits / 50 tags — both verified). Labelling rulings, facts and
  exemptions as assumptions hides which of the eleven a reviewer must actually challenge.
  AS-1/2/3/10/11 *are* real assumptions and are well argued.
- **LOW —** §2.1 abridges rulings that §7, §8 and every FR header already cite (the mapping column
  earns its place; the prose does not). · T-050-38 (`TASKS:1050-1064`) is a lane marker, not a task
  — "may close with zero rounds", no write set, no fixed acceptance; say so.
- **INFO — retired-parser dead code is named but not scoped.** A4.4 (`:501`) defers CLOSURE.md's
  validators to FR15, but FR15 (`:935`) covers only SPEC-DOC-036/038 (`doctor.py:164,167`;
  `doctor_closure_audit.py:43,237,256,284,301`). The remaining CLOSURE.md checks in
  `doctor_closure_audit.py` (312 l), `doctor_release.py` (570) and `doctor_governance.py` (446),
  plus `RELEASE_ARTIFACTS` at `doctor_common.py:20`, have no retiring FR and survive as dead code
  behind a file that no longer exists.

### Axis 7 — six-axis pass on what the SPEC implies for code

**Architecture, patterns, tests, security: sound.** One boundary adapter owned by the migration
(A2.5, `:369-370`), gated by AR-1 (`TASKS:218-239`), which explicitly asks whether the shared JSONL
record-update seam becomes a cross-cutting helper; layer contracts held (`PLAN:105-108`). FR10
extends the existing enforcer rather than adding a second map (`:729-731`); FR13 reuses the FR2
seam (`:867-869`); FR14 absorbs the six-dimension method into pillar 3 instead of keeping it beside
(`:914-915`). Tests: five mutation fixtures (A10.2), fixture-repo derivation tests (T-050-09),
executed-path hook fixtures (A9.1), idempotence by double execution (A3.4) — the one hole is A2.2's
missing write-once coverage. Security: the trio contains zero home-absolute paths, e-mail literals
or IPs (scanned); FR16's artifact is committed inside `specs/` forever and the redaction duty is
stated three times (`:264-265`, `TASKS:83-85, 794`); FR13 widens `project-auditor`'s allowlist by
exactly one glob with a refusal fixture (A13.2); FR9 leaves the pre-push denylist scan and the PR
verdict gate untouched (`:681`), so the publication boundary holds. **One risk:** FR3 must shell
out to `git` while `features/**` may import neither `infrastructure` nor `subprocess`, yet
T-050-09 defaults the module to `features/bugs/` (`TASKS:351-352`) — the placement AR-1 is most
likely to reject; state it as "to be ruled", not a path.
**Performance — no concern, measured here:** `git log --all --no-merges --reverse --date-order --
specs/bugs/` returns 295 commits in 0.016 s; the full `-p` pass emits 42 946 lines in 0.46 s over
2 306 reachable commits. D-C's one-pass replacement of the per-bug pickaxe (`:177-181`) is the
right call and is cheap; the 1.1 MB ledger is a non-issue. **Dead code:** see Axis 6.

### Cross-cutting — what the trio does not see

- **CRITICAL — FR6 silently deletes the BL-STALE data feed.** `features/backlog/ledger.py:1-10`
  reads `specs/_archive/<release-id>/consumed_backlog.json` and documents that an absent ledger
  degrades to `{}` — "BL-STALE is a no-op, never a false ERROR". **18** such files exist under root
  `specs/_archive/`. FR6 (`:536-552`) deletes the tree; D-G (`:196-202`) relocates only milestone
  shas; the sidecar is named nowhere in SPEC, PLAN or TASKS. A backlog-doctor rule goes quiet
  without failing — the exact "documented convention with no data behind it" shape FR13 condemns
  (`:857-859`). A6.2 (`:545-546`) frames the archive as something only the *back-fills* read, which
  is what hid this. *Fix:* relocate the 18 sidecars beside `releases_histo.jsonl`, or retire
  BL-STALE in an FR with its own acceptance.
- **HIGH — an open bug sits on the exact file this release rewrites, unpicked and
  undispositioned.** `SPEC:20-22` says the single open bug is
  `windows-xdist-workers-crash-on-unit-fast-tier`. `dadaia bugs status` reports **two**: the other
  is `bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM, component
  `infrastructure/jsonl_bug_store.py`, one `reported` event, never resolved). The SPEC cites it
  **four times as historical evidence** (`:55, :351-354, :453`; `TASKS:509`) as though closed,
  while FR2/FR13 rewrite its component (T-050-07, T-050-23). AS-4 covers only the Windows bug, and
  `DADAIA.md` §6 puts open bugs ahead of fresh backlog at pick time.
- **HIGH — `S4` writes memory during IMPLEMENTATION and the mitigation is to spoof the phase.**
  MEMORY is writable only in DEFINITION/CLOSURE (`DADAIA.md` §3). T-050-28's precondition
  (`TASKS:828-829`) reads "the dispatcher sets it before relaying, and flips it back afterwards";
  T-050-29 (`:856`) and T-050-31 (`:907`) write the memory trio with no phase note. A release
  installing "no fabricated evidence" as a standing rule (`SPEC:260-261`) cannot open with a
  phase-toggling ritual buried in a task precondition.
- **MEDIUM —** the release's primary evidence lives in a 3-day-GC directory: the FR3 migration and
  FR4 back-fill reports (sole evidence for A3.1–A3.3, A4.3, V4, V5, V7) go under
  `.dadaia/tmp/<agent>/<YYYYMMDD>/` (`TASKS:380, 433`), `features/tmp_gc/service.py:68` sets
  `_MAX_AGE_DAYS = 3`, and T-050-40 lists "the artifact GC sweep" as a closure obligation
  (`TASKS:1112`) while citing those reports by path (`:1108-1109`).
- **MEDIUM —** TREE-8 will WARN on the release's own artifacts: FR1 fixes the release-directory
  canon as `RELEASE.jsonl` + SPEC + PLAN + TASKS (`:282-283`, `BACKLOG.md:350`), yet seven tasks
  write `specs/releases/0.5.0/reviews/*.md` and the live and archived releases already carry
  `reviews/` and `verdicts/` at HEAD.

---

## 2. Bug-surface delta (FR24)

Ledger evidence: `dadaia bugs stats` → 490 records / 470 resolved / **2 open** (1 MEDIUM, 1 LOW);
1 005 events in `specs/bugs/bugs.jsonl`; 295 ledger commits across all refs; 50 `archive/*` tags.

**Reduces** — `features/bugs` and the hook surface. FR2 deletes the event fold and its
terminal/non-terminal state machine, the structural cause of the open U+2028 bug (silent loss is
reachable only because one bug's truth spans lines that must be re-folded); one line per bug turns
a silent half-fold into a loud single-record loss. FR9 deletes two blocking mechanisms whose
registered cost is `precommit-backlog-doctor-blocks-unrelated-commits`. FR1's TREE-8 names the
gitignore *class* behind eight ledger entries patched instance by instance. FR15 deletes
regex-over-prose. FR10's hash tuples answer the stale-citation class
(`dadaia-task-manager-stale-workspace-protocol-citation` plus the v0.4.5 recurrence) structurally.

**Increases** — `features/specs`, `features/backlog`, the audit lane: three schemas, a migration
module, a map plus enforcer, four skill siblings, an ADR canon. The SPEC is honest about this
(`:253-256`, A22.3) and measures it per FR, which is the right posture.

**Net: the definition as written increases the bug surface** — not because it adds code (declared
and justified) but because it leaves four new seams that will each produce a registered bug: the
dual granularity field name, the orphaned BL-STALE feed, the `ACTIVE.md` consumers outside the FR4
write set, and an open bug on the file being rewritten. Amend those four and the delta turns
net-reducing. Nothing is built yet: all four are cheap here and expensive at `rc-3`.

---

## 3. Summary and recommendation

| CRITICAL | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|
| 1 | 8 | 12 | 5 | 1 |

Structurally this is the best-argued definition in the repository: complete FR→task coverage,
agreeing segment maps, every ruling honoured, every number carrying a capture path, a real
glossary, `Done when` throughout. The list below is corrections, not a redesign.

**Recommendation: REWORK** (not APPROVE-FOR-FOLD). Blocking: 1 CRITICAL + 8 HIGH. None requires
re-litigating a ruling. Ordered amendments for `product-engineer`:

1. **Add §1.5 — the loop end to end, in one place:** bug A's fix commit → bug B's record with
   `caused_by: A` and evidence → the pillar-1 finding → its disposition; mark synthetic ids as
   synthetic; point A16.2 at it.
2. **Pin each of §1.1's four chains to an explicit bug-id list** and fix the gitignore row ("four
   recurrences" over eight ids, `:52`); have A16.2/V16 cite the pinned lists.
3. **Resolve FR6 vs `consumed_backlog.json`** — relocate the 18 sidecars or retire BL-STALE in an
   FR; re-word A6.2, which assumes only the back-fills read the archive.
4. **Disposition `bug-event-field-with-unicode-line-separator-silently-drops-the-event`** (pick it
   under FR2 or supersede it explicitly); correct "the single open bug" (`:20`) and the four
   citations that treat it as history.
5. **One name for the granularity marker** across D-A, PLAN §0, FR2, FR3, FR7, FR14, §8.
6. **Re-derive A3.2/A3.3 from the marker definitions**, not from §1.2's differently-counted
   metrics; drop T-050-10's "a low count means the ref scope was wrong".
7. **Fix the FR4 write set** (every `ACTIVE.md`/`CLOSURE.md` consumer in Axis 5) and give the
   surviving CLOSURE.md parsers a retiring FR — A4.4 defers to an FR15 that does not cover them.
8. **Resolve the `S4` memory-phase conflict** by an operator ruling recorded as an assumption, not
   a dispatcher phase toggle in a task precondition.
9. **Move FR5's write set to `features/backlog/**`** (BL-DUP at `features/backlog/doctor.py:98`)
   and add a `features/backlog` row to PLAN §2.
10. **Scope `dadaia bugs archive` (FR2/FR3, with an acceptance) or relax AS-8** and record the
    deferral.
11. **Commit the FR3/FR4 reports somewhere durable** — `.dadaia/tmp/` is GC'd at 3 days while the
    closure record cites them by path.
12. **Name `reviews/` and `verdicts/` in FR1's release-directory canon**, or state and accept the
    permanent TREE-8 self-WARN.
13. **Define at first use in the SPEC:** `seam`, `FR23`, Arm A/B, `histo`, "live photo", TREE-5,
    "thawed tree", "one-axis law", "operator law O5"; add a falsifiable success statement to §1.
14. **Fix T-050-12's archive scan** to cover both `_archive/` layouts and define V7's denominator.
15. **Housekeeping:** A10.1 cardinality (≥1 owner per section); FR2's "shape never changes" vs its
    own examples, plus a write-once test in A2.2; one accounting for how many blockers are removed
    (`:120`/`:131`/`:1179`); AS-9's "295 of the 295" → 220; 471 → 470; A1.5's `gate_policy.py` →
    `hooks/sdd_gate.py`; the two spellings of the `resolved_commit` follow-up commit; re-label
    AS-5/6/7/9 as rulings and facts; restore `RC-FLOW.md`'s `dd-architecture-survey` pointer; give
    `specs/assets/` and `specs/backlog/remote-bugs/` a named task; make the FINDINGS example valid
    JSON and drop its `T-050-04` back-reference.

Re-review required after rework, before this trio may be marked `Aprovado` or promoted.
