# The bug loop

Register → RED → fix → resolve. A confirmed bug is fixed on the live feature branch,
in any phase, with no SPEC, PLAN or TASKS.

## 1. Register — ask first

<!-- derived-from: bug-ledger sha256:9534ded07707 -->

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
  --context demo --symptom "…" --repro "…" --expected "…"
```

`specs/bugs/BUGS.jsonl` holds one record per bug, appended once and keyed by `id`, git
history being that line's change log. `append` opens the record at `status: open` and
refuses a duplicate id and `--surface unknown`: `surface` is one of the six non-feature
layers (`cli core hooks infrastructure public-assets tests`) or a feature package, and
`component` is free-text `path#symbol`. Every written field except `id`, `ts` and
`reported_by` is redacted on write.

Not a bug: an agent's own mistake, wrong usage, an environment limit, a designed
validation, a law ambiguity, or a missing feature.

## 2. Lineage, then a RED test

<!-- derived-from: bug-ledger sha256:9534ded07707 -->

Resolution follows seven ordered phases — lineage, red loop, minimise, hypothesise,
instrument, seam test, cleanup and resolve. Lineage comes first: read at most the 20
most recent records sharing this bug's `surface` or `component` in the window since the
newest archived audit, and end with `caused_by: <id> | none`.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats
```

Then the red loop: a test that fails for the real cause, before production code moves.

## 3. Fix, and let the diff shrink

<!-- derived-from: bug-ledger sha256:9534ded07707 -->

Fix the root cause and watch the test go green. The resolution records the fix's
direction: `diff_direction` is derived from `--evidence-diff`'s `net-negative:`,
`net-positive:` or `net-neutral:` prefix. A fix whose diff grows the touched feature is
routed to the architecture lens before it lands.

## 4. Resolve with evidence and lineage

<!-- derived-from: bug-ledger sha256:9534ded07707 -->

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <bug-id> \
  --cause "…" --caused-by none --resolved-release 0.1.0 --solution "…" \
  --evidence-loop "…" --evidence-seam "…" --evidence-diff "net-negative:…"
```

- `resolve` refuses an incomplete call, naming every missing field, and accepts
  `--caused-by` only as a ledger id or `none`.
- `status` is `open | resolved | superseded | deferred | rejected`; a terminal status
  is reached only through its transition — `resolve`, `supersede --by`, `defer` or
  `reject` with `--reason` — and `closed_at` is set exactly when `status` is terminal,
  never earlier than `ts`.
- `update <id> --set field=value` writes a governance field and refuses `status`,
  `closed_at`, `caused_by`, an immutable core field and a differing second write to a
  write-once field. A reopen is a new record.
- Every write runs `check` over the new ledger bytes before replacing the file
  atomically, so a refused write leaves the file byte-identical.

One commit holds the code, the regression test and the `BUGS.jsonl` line.

`bugs.py archive` moves records whose `closed_at` is older than 90 days into
`specs/bugs/_archive/bugs_histo.jsonl`. `.dadaia/.venv/bin/dadaia doctor`'s `ledgers` section runs
`bugs.py check` (`LEDGER-BUGS-SCHEMA`), and `SPEC-DOC-041` warns on a terminal record
closed longer ago than the archive threshold.
