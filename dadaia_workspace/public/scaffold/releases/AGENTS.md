# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`. Replaces the retired `releases/README.md` (v6 canon, FR1).

- Exactly ONE live release directory, ever (release-candidates model, ADR 0005): a bare
  SemVer id = last published PyPI + 1 patch, created only by `dadaia release new <id>`.
- The release has OPEN scope: it grows by stacked closed-scope CANDIDATES. The live
  candidate's SPEC/PLAN/TASKS trio sits at the release root; each completed-but-not-shipped
  candidate's trio is archived to `rc-N/` by `dadaia release rc-archive` (ADR 0008).
- Canonical release state: `_RELEASE.json` — one mutable document (`phase`/`rc`/milestones)
  plus an append-only `log`; `rc` counts archived candidates. A legacy `RELEASE.json` is
  read-side accepted and renamed by `specs doctor --fix` (SPEC-DOC-046, ADR 0007).
- No `_RELEASE.jsonl` event stream, no `CLOSURE.md`, no `reviews/` directory, no scaffolded
  segment dirs (`alpha-N` retired, ADR 0006).

## 1. Structure

- `AGENTS.md` — this file.
- `<release-id>/{SPEC.md, PLAN.md, TASKS.md, _RELEASE.json, rc-N/, verdicts/}` — the live release; `rc-N/{SPEC,PLAN,TASKS}.md` are archived candidates.
- `verdicts/` — required-check evidence handoffs, deleted once consumed.
- `_ideas/<release-id>/` — pre-approval drafts; own scoped rule, `_ideas/AGENTS.md`.
- `_archive/<release-id>/` — the whole archived release directory, `git mv`'d at closure.
- `_archive/releases_histo.jsonl` — one summary record appended per archived release.

## 2. Authoring rules

- SDD lifecycle order PER CANDIDATE: grill -> `SPEC.md` (Draft) -> operator approval -> `PLAN.md` -> `TASKS.md` -> implementation -> closure -> develop merge -> promote-or-continue gate.
- Candidate closure order: memory update -> closure narrative in `_RELEASE.json`'s `log` -> disposition sweep -> artifact GC -> merge -> gate (continue = `rc-archive`; promote = ship, then archive the whole folder — final trio at root, ADR 0009).
- Full arc, gate cadence, the step-by-step ladder: `dd-release-implementation`'s `RC-FLOW.md`.
- A candidate's SPEC.md fits 24 KB and TASKS.md 12 KB (`DADAIA.md` §6.7); measure with `wc -c` before the definition commit.
- A `v`-prefixed id is minted nowhere — the bare axis (`^\d+\.\d+\.\d+$`) is the only current one.
- A legacy `v`-prefixed id still resolves inside `_archive/` (read-only lookup) — pre-canon-v6 history.

## 3. _RELEASE.json (D3/D7/D11)

- The active release's phase is its `phase` field — read directly, no fold, no event-stream replay.
- Who sets which milestone, and the exact shape per field: `dd-release-implementation`'s `RELEASE-EVENTS.md`.
- No dual-write, no mirror file (v0.5.0 FR4/T-050-21A, A4.1).
- The SDD gate resolves the active release directly: the ONE non-archived, non-`_ideas` directory with a `_RELEASE.json`.
- No such directory: no active release — honest absence, no placeholder file.

## 4. `_ideas/` and `_archive/`

- `_ideas/<release-id>/` holds a pre-approval Draft; stays MUTATING, never an evidence root, carries no `_RELEASE.json`.
- Archiving (at deploy) `git mv`'s the whole release directory (final trio at root, `rc-N/` folders, `_RELEASE.json`, verdicts) into `_archive/<release-id>/`.
- Every archived directory's `_RELEASE.json` carries `phase: ARCHIVED`.
- One `_archive/releases_histo.jsonl` summary record is appended per archived release, same commit as the `git mv`.
- History survives in git, the archived directory, and this histo record — never a second on-disk copy.
