# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`.

- `RELEASE_PY` below is `python3 .agents/skills/dd-release-implementation/scripts/release.py` — this ledger's ONE writer.
- `phase` moves only by `RELEASE_PY new` (DEFINITION) and `RELEASE_PY phase`, the `defined`/`implemented` milestones only by `RELEASE_PY phase`; `shipped` only by `RELEASE_PY ship`.

- Exactly ONE live release directory, ever: a bare SemVer id, created only by `RELEASE_PY new <id>`,
  which writes the next `rc-<N>/SPEC.md` + `_RELEASE.json` (DEFINITION) in one transaction and refuses a second one.
- The release has OPEN scope: it grows by CANDIDATES, each born by `RELEASE_PY new` in its own `rc-<N>/`.
- Canonical release state: `_RELEASE.json` — one mutable document (`phase`/milestones) plus an append-only `log`.

## 1. Structure

- `<release-id>/` — the live release: only `_RELEASE.json` at its root, one `rc-<N>/` trio per candidate; the live candidate is the highest `rc-<N>/`, every lower one is history. A flat trio at the root is off-canon (TREE-8).
- `_archive/**` is history: read-only history.

## 2. Authoring rules

- One `**Origin:**` line per SPEC, the first counting: `operator-demand`, or `backlog:<ids>; bugs:<ids>; findings:<ids>`, each kind at most once, a finding id in full (`<audit-id>-F<nnn>`); `RELEASE_PY check` judges it and traces each id back.
- SDD lifecycle order PER CANDIDATE: as-is review -> grill -> SPEC (Draft) -> PLAN -> job files -> operator approval of SPEC and PLAN -> implementation -> closure -> integration-branch merge -> promote-or-continue gate.
- Full arc, gate cadence, the step-by-step ladder: `dd-release-implementation`'s `RC-FLOW.md`.
- A candidate is closed: created, implemented, or cancelled into the next; never amended (shape 8 records approval only); a new AC goes to the next rc.
- A candidate is defined in its own `rc-<N>/`, authored in a `define` tree: rc N+1 is drafted there while rc N implements and enters by `RELEASE_PY new` at rc N's CLOSURE;
  its `## Bug window review` judges rc N's bug fixes; one rc implements at a time.
- Recommended size, never a gate: SPEC.md within 24 KiB, each job file within 12 KiB.
- Release ids are bare SemVer (`^\d+\.\d+\.\d+$`).

## 3. Tasks — the auditable trace

- Read SPEC, PLAN and every job file before implementing; the approval precondition's home is `specs/AGENTS.md`. Tasks live in `tasks/job<n>.md` (`dd-release-definition` §5); a closed rc keeps its `TASKS.md`.
- The `W:` is exact: every file the task touches, with derived files it re-records; the commit body names each file and why. Current task ids are `J<n>.T<k>`.

## 4. _RELEASE.json

- The active release's phase is its `phase` field — read directly, no reconciliation, no event-stream replay.
- Who sets which milestone, and the exact shape per field: `dd-release-implementation`'s `RELEASE-EVENTS.md`.

## 5. Promote

- Promote is merging the PR into the principal branch (the constitution's `gitflow:`); `RELEASE_PY ship --sha <sha>` records it: `shipped`, one `delivered` histo line, the whole release directory moved to `_archive/<id>/`, never deleted.
- Version, CHANGELOG and tag belong to the project's own release pipeline; no verb and no agent mints a version.
