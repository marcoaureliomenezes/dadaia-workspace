# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`. Replaces the retired `releases/README.md` (v6 canon, FR1).

- Each live release directory: a bare SemVer id (e.g. `0.6.0`), created only by `dadaia release new <id>`.
- Canonical release state: `RELEASE.json` — one mutable document (`phase`/`rc`/milestones) plus an append-only `log`.
- No `RELEASE.jsonl` event stream, no `CLOSURE.md`, no `reviews/` directory.
- Only one release may be in IMPLEMENTATION phase at a time.

## 1. Structure

- `AGENTS.md` — this file.
- `<release-id>/{SPEC.md, PLAN.md, TASKS.md, RELEASE.json, verdicts/}` — the live release.
- `verdicts/` — required-check evidence handoffs, deleted once consumed.
- `_ideas/<release-id>/` — pre-approval drafts; own scoped rule, `_ideas/AGENTS.md`.
- `_archive/<release-id>/` — the whole archived release directory, `git mv`'d at closure.
- `_archive/releases_histo.jsonl` — one summary record appended per archived release.

## 2. Authoring rules

- SDD lifecycle order: `SPEC.md` (Draft) -> operator approval -> `PLAN.md` -> `TASKS.md` -> implementation -> closure.
- Closure order: memory update -> closure narrative in `RELEASE.json`'s `log` -> disposition sweep -> artifact GC -> archive.
- Full arc, gate cadence, the step-by-step ladder: `dd-release-implement`'s `RC-FLOW.md`.
- A `v`-prefixed id is minted nowhere — the bare axis (`^\d+\.\d+\.\d+$`) is the only current one.
- A legacy `v`-prefixed id still resolves inside `_archive/` (read-only lookup) — pre-canon-v6 history.

## 3. RELEASE.json (D3/D7/D11)

- The active release's phase is its `phase` field — read directly, no fold, no event-stream replay.
- Who sets which milestone, and the exact shape per field: `dd-release-implement`'s `RELEASE-EVENTS.md`.
- No dual-write, no mirror file (v0.5.0 FR4/T-050-21A, A4.1).
- The SDD gate resolves the active release directly: the ONE non-archived, non-`_ideas` directory with a `RELEASE.json`.
- No such directory: no active release — honest absence, no placeholder file.

## 4. `_ideas/` and `_archive/`

- `_ideas/<release-id>/` holds a pre-approval Draft; stays MUTATING, never an evidence root, carries no `RELEASE.json`.
- Archiving `git mv`'s the whole release directory (SPEC/PLAN/TASKS/RELEASE.json/verdicts) into `_archive/<release-id>/`.
- Every archived directory's `RELEASE.json` carries `phase: ARCHIVED`.
- One `_archive/releases_histo.jsonl` summary record is appended per archived release, same commit as the `git mv`.
- History survives in git, the archived directory, and this histo record — never a second on-disk copy.
