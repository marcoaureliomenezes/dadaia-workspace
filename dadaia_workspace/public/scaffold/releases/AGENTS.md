# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`.

- `RELEASE_PY` below is `python3 .agents/skills/dd-release-implementation/scripts/release.py` — this ledger's ONE writer.

- Exactly ONE live release directory, ever: a bare SemVer id, created only by `RELEASE_PY new <id>`,
  which writes `rc-1/SPEC.md` + `_RELEASE.json` (DEFINITION) in one transaction and refuses a second one.
- The release has OPEN scope: it grows by CANDIDATES, each born by `RELEASE_PY new` in its own `rc-<N>/` (ADR 0150).
- Canonical release state: `_RELEASE.json` — one mutable document (`phase`/milestones) plus an append-only `log`; a legacy `RELEASE.json` is renamed by `.dadaia/.venv/bin/dadaia doctor --fix` (SPEC-DOC-046, ADR 0007).
- No `_RELEASE.jsonl` event stream, no `CLOSURE.md`, no `reviews/` directory, no `segment`/`audited` fields.

## 1. Structure

- `<release-id>/` — the live release: only `_RELEASE.json` at its root, one `rc-<N>/` trio per candidate; the live candidate is the highest `rc-<N>/`, every lower one is history. A flat trio at the root is off-canon (TREE-8).
- `_archive/**` is history: read, never written, never rewritten, never ranked.

## 2. Authoring rules

- One `**Origin:**` line per SPEC, the first counting (ADR 0161): `operator-demand`, or `backlog:<ids>; bugs:<ids>; findings:<ids>`, each kind at most once, a finding id in full (`<audit-id>-F<nnn>`); `RELEASE_PY check` judges it and traces each id back. Weight: `operator-demand` is the heaviest — as-is review and grill first, full memory pass; a `backlog:` pick the default, full memory pass; `bugs:` alone composes bugs, memory pass surgical or none.
- SDD lifecycle order PER CANDIDATE: as-is review -> grill -> SPEC (Draft) -> operator approval -> PLAN -> TASKS -> implementation -> closure -> integration-branch merge -> promote-or-continue gate.
- Full arc, gate cadence, the step-by-step ladder: `dd-release-implementation`'s `RC-FLOW.md`.
- A candidate is closed: created, implemented, or cancelled into the next; never amended (shape 8 records approval only); a new AC goes to the next rc.
- A candidate is defined in its own `rc-<N>/`, authored in a `define` tree: rc N+1 is drafted there while rc N implements and enters by `RELEASE_PY new` at rc N's CLOSURE;
  its `## Bug window review` judges rc N's bug fixes; one rc implements at a time.
- Recommended size, never a gate (ADR 0152 (2)): SPEC.md within 24 KiB, each job file within 12 KiB.
- A `v`-prefixed id is minted nowhere — the bare axis (`^\d+\.\d+\.\d+$`) is the only current one.

## 3. Tasks — the auditable trace

- Read SPEC, PLAN and every job file before implementing; the approval precondition's home is `specs/AGENTS.md`. Historical `TASKS.md` files remain readable, but current candidates carry tasks only in `tasks/<job>.md` (`dd-release-definition` §5).
- The `W:` is exact: every file the task touches, with derived files it re-records; the commit body names each file and why. Current task ids are `J<n>.T<k>`; readers retain historical `J<n>.S<m>.T<k>` ids.
- A REBUILD keeps the fix's tests.
- The task's commit is `conventional-commit(task-id): description`.
- `phase` and the `defined`/`implemented` milestones move only by `RELEASE_PY phase`; `shipped` only by `RELEASE_PY ship`.

## 4. _RELEASE.json

- The active release's phase is its `phase` field — read directly, no reconciliation, no event-stream replay.
- Who sets which milestone, and the exact shape per field: `dd-release-implementation`'s `RELEASE-EVENTS.md`.

## 5. Promote

- Promote is merging the PR into the principal branch (the constitution's `gitflow:`); `RELEASE_PY ship --sha <sha>` records it: `shipped`, one `delivered` histo line, the whole release directory moved to `_archive/<id>/`, never deleted (ADR 0152 (1)).
- Version, CHANGELOG and tag belong to the project's own release pipeline; no verb and no agent mints a version.
