# The bug loop

Register → RED → fix → resolve. A confirmed bug is fixed in one `bug` worktree,
in any phase, with no SPEC, PLAN or TASKS.

## 1. Register — ask first

<!-- derived-from: bug-ledger sha256:156cfaca5544 -->

A bug is a tool breaking a contract it documents. Registration is ask-first: the agent
proposes the violated contract line, one reproducing command already run, why it is not
agent error, and a severity — CRITICAL a stall or data loss, HIGH a contract broken on
the default path, MEDIUM off the default path or with a workaround, LOW a message or
cosmetic defect. `append` runs only after the operator confirms; with no operator
present the proposal leaves the session as one handoff finding whose `message` starts
`bug-proposal:`.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append \
  --bug-id doctor-exits-zero-with-errors --reported-by dd-software-engineer \
  --title "doctor exits 0 while reporting error findings" \
  --severity HIGH --surface cli --component "cli/commands/doctor.py#run" \
  --context demo --symptom "…" --repro "…" --expected "…" --correlates none
```

`specs/bugs/BUGS.jsonl` holds one record per bug, appended once and keyed by `id`, git
history being that line's change log. `append` first prints the correlation candidates — open
records on the same surface and those resolved there in the last 30 days — then opens
the record at `status: open`, stamping `found_in` — the candidate holding the registration instant — and refusing a duplicate id, a `surface` that names no tracked
directory of the repo, and a missing or unknown `--correlates <ids>|none`; `component`
is free-text `path#symbol`. Every written field except `id`, `ts` and
`reported_by` is redacted on write.

Not a bug: an agent's own mistake, wrong usage, an environment limit, a designed
validation, a law ambiguity, or a missing feature.

## 2. Lineage, then a RED test

<!-- derived-from: bug-ledger sha256:156cfaca5544 -->

Resolution follows seven ordered phases — lineage, red loop, minimise, hypothesise,
instrument, seam test, cleanup and resolve. Lineage comes first: read at most the 20
most recent records sharing this bug's `surface` or `component` in the window since the
newest archived audit, and end with `caused_by: <id> | none`. Two or more prior fixes on
the unit the bug lands in make this fix a rebuild of that unit, never a third patch: the
commit body says `rebuild: <unit> — prior fixes <id>, <id>` (or `rebuild: none`), and
the `--solution` opens with `REBUILD <unit>:`.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats
```

Then the red loop: a new case that fails for the real cause, before production code moves; a fix never rewrites an old assert.

## 3. Fix, and let the diff shrink

<!-- derived-from: bug-ledger sha256:156cfaca5544 -->

Fix the root cause and watch the test go green. The fix's direction is derived, never
typed: `bugs.py fix <bug-id>` prints the fix commits, their numstat and `net-negative`,
`net-positive` or `net-neutral` on production paths, and `bugs.py stats` counts it as `direction:`. A fix whose diff grows the touched feature is
routed to the architecture lens before it lands.

## 4. Resolve with the red loop and lineage

<!-- derived-from: bug-ledger sha256:156cfaca5544 -->

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <bug-id> \
  --cause "…" --caused-by none --solution "…" --evidence-loop "…"
```

- Stage the fix first: `resolve` prints the blame candidates — the bugs whose fix and the
  tasks whose commit wrote a line the staged diff removes — and refuses a `--caused-by`
  outside them, or `none` while any exist, unless `--lineage-reason` says why.
- `resolve` refuses an incomplete call, naming every missing field; `caused_by: X` means
  the fix of X wrote the lines this fix corrects — a live or archived record, a task id,
  or `none`, never a loop; `resolved_release` is derived from the resolve instant.
- `status` is `open | resolved | superseded | deferred | rejected`; a terminal status
  is reached only through its transition — `resolve`, `supersede --by`, `defer` or
  `reject` with `--reason` — and `closed_at` is set exactly when `status` is terminal,
  never earlier than `ts`.
- `update <id> --set field=value` writes a governance field, `caused_by` included, and
  refuses `status`, `closed_at`, `resolved_release`, `superseded_by`, an immutable core field and a
  differing second write to a write-once field. A reopen is a new record.
- Every write runs `check` over the new ledger bytes before replacing the file
  atomically, so a refused write leaves the file byte-identical.

One commit holds the code, the regression test and the `BUGS.jsonl` line, its red loop
quoted in the body.

`bugs.py archive` moves records whose `closed_at` is older than 90 days into
`specs/bugs/_archive/bugs_histo.jsonl`. `.dadaia/.venv/bin/dadaia doctor`'s `ledgers` section runs
`bugs.py check` (`LEDGER-BUGS-SCHEMA`), and `SPEC-DOC-041` warns on a terminal record
closed longer ago than the archive threshold.
