# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`.

- `RELEASE_PY` below is `python3 .agents/skills/dd-release-implementation/scripts/release.py` — this ledger's ONE writer.

- Exactly ONE live release directory, ever: a bare SemVer id, created only by `RELEASE_PY new <id>`,
  which writes `SPEC.md` + `_RELEASE.json` (DEFINITION) in one transaction and refuses a second one.
- The release has OPEN scope: it grows by stacked closed-scope CANDIDATES, each trio written at the release root.
- A closed candidate's trio is overwritten in place by the next candidate's `RELEASE_PY new`; that trio lives in git at its CLOSURE commit, which is the whole archive.
- Canonical release state: `_RELEASE.json` — one mutable document (`phase`/milestones) plus an append-only `log`; a legacy `RELEASE.json` is renamed by `.dadaia/.venv/bin/dadaia doctor --fix` (SPEC-DOC-046, ADR 0007).
- No `_RELEASE.jsonl` event stream, no `CLOSURE.md`, no `reviews/` directory, no `segment`/`audited` fields.

## 1. Structure

- `<release-id>/{SPEC.md, PLAN.md, TASKS.md, _RELEASE.json}` — the live release, its trio flat at the root.
- `_archive/**` and any candidate folder under a release are history: read, never written, never rewritten, never ranked.

## 2. Authoring rules

- Three flows, one `**Origin:**` per SPEC (`SPEC-DOC-048`): Flow 1 `backlog:<ids>` is the default weight, full memory pass; Flow 2 `bugs:<ids>` composes bugs, memory pass surgical or none; Flow 3 `operator-demand` is the heaviest — as-is review and grill first, full memory pass.
- SDD lifecycle order PER CANDIDATE: as-is review -> grill -> `SPEC.md` (Draft) -> operator approval -> `PLAN.md` -> `TASKS.md` -> implementation -> closure -> develop merge -> promote-or-continue gate.
- Candidate closure order: memory update -> closure narrative in `_RELEASE.json`'s `log` -> disposition sweep -> artifact GC -> merge -> gate (continue = the next candidate's `RELEASE_PY new`; promote = merging the release PR).
- Full arc, gate cadence, the step-by-step ladder: `dd-release-implementation`'s `RC-FLOW.md`.
- A candidate's SPEC.md fits 24 KB and TASKS.md 12 KB; measure with `wc -c` before the definition commit.
- A `v`-prefixed id is minted nowhere — the bare axis (`^\d+\.\d+\.\d+$`) is the only current one.

## 3. Tasks — the auditable trace

- Read SPEC, PLAN and TASKS before implementing; all three must carry `**Status:** Approved`.
- Reserve before writing: flip `[ ] -> [-]`; one `[-]` at a time unless TASKS declares disjoint write sets.
- Complete the work inside the task's declared write set; a completed task group is one commit.
- Flip `[-] -> [x]` and commit as `conventional-commit(task-id): description`.
- `phase` and the `defined`/`implemented` milestones move only by `RELEASE_PY phase`; `ARCHIVED` is written by no verb.

## 4. _RELEASE.json

- The active release's phase is its `phase` field — read directly, no reconciliation, no event-stream replay.
- Who sets which milestone, and the exact shape per field: `dd-release-implementation`'s `RELEASE-EVENTS.md`.

## 5. Promote

- Version, CHANGELOG and tag come from release-please over Conventional Commits, through one release PR on `main`.
- Promote is merging that PR; `RELEASE_PY phase CLOSURE --sha <sha> --pr <n>` records it in the candidate's note.
- The publish jobs run in the same workflow, gated on `release_created`; no verb and no agent mints a version.
