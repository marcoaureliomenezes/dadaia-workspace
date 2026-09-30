# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`.

- `RELEASE_PY` below is `python3 .agents/skills/dd-release-implementation/scripts/release.py` — this ledger's ONE writer.

- Exactly ONE live release directory, ever: a bare SemVer id, created only by `RELEASE_PY new <id>`,
  which writes `rc-1/SPEC.md` + `_RELEASE.json` (DEFINITION) in one transaction and refuses a second one.
- The release has OPEN scope: it grows by closed-scope CANDIDATES, each born by `RELEASE_PY new` in its own `rc-<N>/` and never rewritten after its closure (ADR 0150).
- Canonical release state: `_RELEASE.json` — one mutable document (`phase`/milestones) plus an append-only `log`; a legacy `RELEASE.json` is renamed by `.dadaia/.venv/bin/dadaia doctor --fix` (SPEC-DOC-046, ADR 0007).
- No `_RELEASE.jsonl` event stream, no `CLOSURE.md`, no `reviews/` directory, no `segment`/`audited` fields.

## 1. Structure

- `<release-id>/` — the live release: only `_RELEASE.json` at its root, one `rc-<N>/` trio per candidate; the live candidate is the highest `rc-<N>/`, every lower one is history. A flat trio at the root is off-canon (TREE-8).
- `_archive/**` is history: read, never written, never rewritten, never ranked.

## 2. Authoring rules

- Three flows, one `**Origin:**` per SPEC (`SPEC-DOC-048`): Flow 1 `backlog:<ids>` is the default weight, full memory pass; Flow 2 `bugs:<ids>` composes bugs, memory pass surgical or none; Flow 3 `operator-demand` is the heaviest — as-is review and grill first, full memory pass.
- SDD lifecycle order PER CANDIDATE: as-is review -> grill -> SPEC (Draft) -> operator approval -> PLAN -> TASKS -> implementation -> closure -> integration-branch merge -> promote-or-continue gate.
- Candidate closure order: memory update -> closure narrative in `_RELEASE.json`'s `log` -> disposition sweep -> artifact GC -> merge -> gate (continue = the next candidate's `RELEASE_PY new`; promote = merging the release PR).
- Full arc, gate cadence, the step-by-step ladder: `dd-release-implementation`'s `RC-FLOW.md`.
- Recommended size, never a gate (ADR 0152 (2)): a candidate's SPEC.md within 24 KiB and TASKS.md within 12 KiB; past it, the next work opens `rc-<N+1>/`.
- A `v`-prefixed id is minted nowhere — the bare axis (`^\d+\.\d+\.\d+$`) is the only current one.

## 3. Tasks — the auditable trace

- Read SPEC, PLAN and TASKS before implementing; all three must carry `**Status:** Approved`.
- Reserve before writing: flip `[ ] -> [-]`; one `[-]` at a time unless TASKS declares disjoint write sets.
- Complete the work inside the task's declared write set; a completed task group is one commit.
- Flip `[-] -> [x]` and commit as `conventional-commit(task-id): description`.
- `phase` and the `defined`/`implemented` milestones move only by `RELEASE_PY phase`; `shipped` only by `RELEASE_PY ship`.

## 4. _RELEASE.json

- The active release's phase is its `phase` field — read directly, no reconciliation, no event-stream replay.
- Who sets which milestone, and the exact shape per field: `dd-release-implementation`'s `RELEASE-EVENTS.md`.

## 5. Promote

- Promote is merging the PR into the principal branch (the constitution's `gitflow:`); `RELEASE_PY ship --sha <sha> --pr <n>` records it: `shipped`, one `delivered` histo line, the whole release directory moved to `_archive/<id>/`, never deleted (ADR 0152 (1)).
- Version, CHANGELOG and tag belong to the project's own release pipeline; no verb and no agent mints a version.
