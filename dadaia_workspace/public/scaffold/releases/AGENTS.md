# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`.

- `RELEASE_PY` below is `python3 .agents/skills/dd-release-implementation/scripts/release.py` — this ledger's ONE writer.

- Exactly ONE live release directory, ever (release-candidates model, ADR 0005): a bare
  SemVer id = last published PyPI + 1 patch, created only by `RELEASE_PY new <id>` — which
  writes `SPEC.md` + `_RELEASE.json` (DEFINITION) in one transaction and refuses a second live release.
- The release has OPEN scope: it grows by stacked closed-scope CANDIDATES. The live candidate's trio sits at the release root; a completed candidate's trio is archived to `rc-N/` by `RELEASE_PY rc-archive` (ADR 0008).
- Canonical release state: `_RELEASE.json` — one mutable document (`phase`/`rc`/milestones) plus an append-only `log`; a legacy `RELEASE.json` is renamed by `dadaia doctor --fix` (SPEC-DOC-046, ADR 0007).
- No `_RELEASE.jsonl` event stream, no `CLOSURE.md`, no `reviews/` directory, no `segment`/`audited` fields (ADR 0006).

## 1. Structure

- `<release-id>/{SPEC.md, PLAN.md, TASKS.md, _RELEASE.json, rc-N/}` — the live release; `rc-N/{SPEC,PLAN,TASKS}.md` are archived candidates.
- `_archive/<release-id>/` — the whole archived release directory, moved there by `RELEASE_PY archive`.
- `_archive/` holds published versions only (ADR 0014): a candidate closed between two publications is `rc-N/` of the version that published it; `RELEASE_PY fold <id> --into <published> [--final]` repairs a wrongly archived one (`RELEASE-TREE-ARCHIVE-ID`/`-UNSHIPPED` refuse the shape).
- `_archive/releases_histo.jsonl` — one summary record appended per archived release.

## 2. Authoring rules

- Three flows, one `**Origin:**` per SPEC (`SPEC-DOC-048`): Flow 1 `backlog:<ids>` is the default weight, full memory pass; Flow 2 `bugs:<ids>` composes open bugs, memory pass surgical or none; Flow 3 `operator-demand` is the heaviest — grill first, full memory pass.
- SDD lifecycle order PER CANDIDATE: grill -> `SPEC.md` (Draft) -> operator approval -> `PLAN.md` -> `TASKS.md` -> implementation -> closure -> develop merge -> promote-or-continue gate.
- Candidate closure order: memory update -> closure narrative in `_RELEASE.json`'s `log` -> disposition sweep -> artifact GC -> merge -> gate (continue = `rc-archive`; promote = ship, then `RELEASE_PY archive <id> --shipped <sha> --pr <n> --next <M.m.p>` — final trio at root, ADR 0009).
- Full arc, gate cadence, the step-by-step ladder: `dd-release-implementation`'s `RC-FLOW.md`.
- A candidate's SPEC.md fits 24 KB and TASKS.md 12 KB; measure with `wc -c` before the definition commit.
- A `v`-prefixed id is minted nowhere — the bare axis (`^\d+\.\d+\.\d+$`) is the only current one.

## 3. Tasks — the auditable trace

- Read SPEC, PLAN and TASKS before implementing; all three must carry `**Status:** Approved`.
- Reserve before writing: flip `[ ] -> [-]`; one `[-]` at a time unless TASKS declares disjoint write sets.
- Complete the work inside the task's declared write set; a completed task group is one commit.
- Flip `[-] -> [x]` and commit as `conventional-commit(task-id): description`.
- `phase` and the `defined`/`implemented` milestones move only by `RELEASE_PY phase`; `shipped` only by `RELEASE_PY archive`.

## 4. _RELEASE.json (D3/D7/D11)

- The active release's phase is its `phase` field — read directly, no fold, no event-stream replay.
- Who sets which milestone, and the exact shape per field: `dd-release-implementation`'s `RELEASE-EVENTS.md`.

## 5. `_archive/`

- Archiving (at deploy) is `RELEASE_PY archive`: it validates, sets `shipped` + ARCHIVED, moves the whole directory into `_archive/<release-id>/`, appends the histo record, births the next release and runs `bugs archive` — all-or-nothing.
- Every archived directory's `_RELEASE.json` carries `phase: ARCHIVED`.
- One `_archive/releases_histo.jsonl` record (`histo-record-v1`, `disposition: delivered`) is appended per archived release; the verb prints the git `next:` lines and never runs git.
