# RELEASE-EVENTS — `RELEASE.jsonl` append recipes per milestone

Disclosed reference reached from `SKILL.md` and `RC-FLOW.md` wherever the arc says
"append a RELEASE.jsonl record". `specs/releases/<release-id>/RELEASE.jsonl` is the
append-only event stream that is replacing `ACTIVE.md`'s phase field and `CLOSURE.md`'s
closure narrative (SPEC FR4, D3/D7/D11). Schema:
`dadaia_workspace/public/schemas/releases/release-event-v1.schema.json` — validate a
new line against it before appending; the fold that reads this file back is
`dadaia_workspace/core/release_events.py` (read-only, no write call — pure
parse-and-fold, never the writer).

## Envelope

Every line is one JSON object, no trailing comma, `{ts, event, agent, data}` — no
`session_id` (a harness session id is PROTECTED state; committing it would link a
governance milestone to a local session permanently, for no governance value).

## The seven kinds, who appends which, and the shape

| Kind | Appended by | `data` shape | Cardinality |
|---|---|---|---|
| `phase` | whoever drives the transition (`product-engineer` at DEFINITION/CLOSURE, the first implementer at IMPLEMENTATION) | `{"phase": "<DISCOVERY\|DEFINITION\|SPEC\|PLAN\|TASKS\|IMPLEMENTATION\|CLOSURE\|ARCHIVED>", "segment"?: "<alpha-N\|rc-N>"}` | many — the fold takes the **last** record |
| `defined` | `product-engineer`, at the definition promotion commit (`dd-release-definition`'s own recipe) | `{"sha": "<sha>", "pr": <n\|null>}` | once — a later record is a duplicate finding |
| `implemented` | `qa-engineer`, at the **final-`rc` QA close**, on that closed commit's sha — **not** the merge commit (D3; the two differ by the merge artifact) | `{"sha": "<sha>", "rc": <n>}` | once |
| `shipped` | `project-manager` (or whoever opens/merges the `develop`→`main` ship PR), at the merge | `{"sha": "<sha>", "pr": <n>, "tag": "<M.m.p>"}` | once |
| `audited` | `project-auditor`, the one place `resolved_commit`/`resolution_granularity`/`audited` are ever written together on a bug record, in a single atomic rewrite (FR14 pillar 1) | `{"sha": "<sha>", "audit": "audits/<window-id>"}` | once per audit window that reviewed this release |
| `rc` | `product-engineer`/implementer, opening and closing each `rc-N` round | `{"open\|close": true, "n": <rc-number>}` | many — one open + one close per round |
| `note` | any implementer, for governance text that doesn't warrant its own kind | `{"kind": "<free text>", "text": "<free text>"}` | many |

`defined`/`implemented`/`shipped` are the three **sha-bearing milestone facts** — each
appended **at most once meaningfully**; the fold (`core/release_events.py`) takes the
FIRST record of each kind and reports any later one as a duplicate — a doctor WARNING
(SPEC-DOC-043), never a block (D15).

## Worked example (from SPEC FR4)

```json
{"ts":"2026-08-28T14:02:11Z","event":"defined","agent":"product-engineer","data":{"sha":"4e5f6a7","pr":210}}
{"ts":"2026-09-03T18:40:05Z","event":"implemented","agent":"qa-engineer","data":{"sha":"b8c9d0e","rc":2}}
{"ts":"2026-09-04T10:15:00Z","event":"shipped","agent":"project-manager","data":{"sha":"f1a2b3c","pr":214,"tag":"0.5.0"}}
{"ts":"2026-10-20T09:00:00Z","event":"audited","agent":"project-auditor","data":{"sha":"c0ffee1","audit":"audits/20261020-five-release-window"}}
```

## `note` conventions for the retired `CLOSURE.md` narrative (T-050-21, A12.2)

`CLOSURE-TEMPLATE.md`/`CLOSURE.md` retire at T-050-21 (FR12) — everything they carried
gets a named surviving home; the narrative sections (Summary, Size accounting, Drifts,
Artifact GC sweep, Test dispositions) that used to live in `CLOSURE.md` prose now land
as `note` records, one per class, `data.kind` naming which:

| Old `CLOSURE.md` section | `note` `data.kind` | Surviving home if not a `note` |
|---|---|---|
| `## Summary` | `closure-summary` | — |
| `## Size accounting` | `closure-size-accounting` | — |
| `## Drifts` | `closure-drift` (one per drift) | — |
| `## Test dispositions` | `closure-test-dispositions` | `dadaia-test-stewardship`'s own demotion/quarantine record is the primary source; this note only summarizes |
| `## Artifact GC sweep` | `closure-artifact-gc` | — |
| `## Dispositions` | *(none needed)* | already native: `specs/backlog/_archive/backlog_histo.jsonl`'s `release` field and `BUGS.jsonl`'s `resolved_release` field carry this per-item, per record — the sweep is verified with `dadaia bugs stats` / `dadaia backlog doctor`, never re-tabulated |
| `## Record-only observations` | *(none needed)* | already native: the reviewer's own findings array/handoff — never re-homed (FR6/R4) |
| `## Intake candidates` | *(none needed)* | handed directly to `project-manager`'s intake-report workflow (`dd-backlog-definition` §5) instead of staging in a closure doc first |
| `## Archive decision` | *(none needed)* | implicit in the `git mv` + `phase: ARCHIVED` record — `MOVE` is the only path now |
| `## Tasks completed` | *(none needed)* | already native: `TASKS.md`'s `[x]` markers + each task's final commit sha |
| `## Validations` | *(none needed)* | already native: per-task `implementation-complete` handoffs + the trio's `APPROVE` verdicts |
| `## Memory updates` | *(none needed)* | already native: the memory atom diffs themselves, in git history |

**Transitional note (until T-050-25A).** `dadaia specs doctor`'s SPEC-DOC-006 still
requires an *archived* release directory to carry a `CLOSURE.md` with `## Summary`,
`## Validations`, `## Drifts`, `## Memory updates` headings and a validation triple —
that doctor-side parser retires at **T-050-25A** (FR15), not here. Until it lands,
write a minimal freeform `CLOSURE.md` carrying exactly those four headings (sourced
from the `note` records above — no template dependency, no `CLOSURE-TEMPLATE.md`); the
`RELEASE.jsonl` records are the canonical, forward-looking form regardless.

## Validation

```bash
python -c "import json; json.loads(open('specs/releases/<release-id>/RELEASE.jsonl').readlines()[-1])"
```

A malformed line never loses the well-formed records around it — the fold
(`core/release_events.py`) skips a bad line and reports it, not the whole file.
