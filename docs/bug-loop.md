# The bug loop

Register → RED → fix → resolve. A bug is fixed on the spot, on the live feature
branch, in any phase — no SPEC, no PLAN, no TASKS, no pick line, no release directory
and no version mint.

## 1. Register — ask first

<!-- derived-from: sdd-bug-backlog-governance sha256:828ff63c54dd -->

Registration is ask-first. The agent proposes: the contract line violated, one command
that reproduces it, why it is not agent error, and a severity from the one rubric —
CRITICAL a stall or data loss, HIGH a contract broken on the default path, MEDIUM off
the default path or with a documented workaround, LOW a message or cosmetic defect.
The record is written only after the operator confirms; with no operator present the
proposal leaves the session as a handoff finding, never as a record.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append \
  --bug-id doctor-exits-zero-with-errors --reported-by dd-software-engineer \
  --title "doctor exits 0 while reporting error findings" \
  --severity HIGH --surface cli --component "cli/commands/doctor.py#run" \
  --context demo --symptom "…" --repro "…" --expected "…"
```

`specs/bugs/BUGS.jsonl` is the one bug record store: one record per bug, appended
once, keyed by its id, with git history as that line's change log. `--surface unknown`
is refused, naming the real surfaces; `component` is free-text `path#symbol`.

Not a bug: an agent's own mistake, wrong usage, an environment limit, a designed
validation, a law ambiguity, or a missing feature — the last two go to a grill and to
backlog intake.

## 2. Lineage, then a RED test

<!-- derived-from: sdd-bug-backlog-governance sha256:828ff63c54dd -->

Diagnosis is ordered, and its first phase is lineage: read the 20 most recent records
sharing this bug's `surface` or `component` before proposing anything.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats
```

Repetition in that window is evidence: the same surface failing again means the prior
fixes patched symptoms. Then build the regression test at the seam the bug really
lives at, watch it fail for the real reason, and only then touch production code.

## 3. Fix, and let the diff shrink

<!-- derived-from: sdd-bug-backlog-governance sha256:828ff63c54dd -->

Fix the cause, watch the test go green, re-run the original reproduction. A resolved
record requires a regression seam — no seam, no `resolved`.

A correct fix usually removes a branch, collapses two paths into one, or moves logic
back inside the feature that owns it. A fix that adds a flag, a wrapper or a second
code path is how the next bug in the family is born.

## 4. Resolve with evidence and lineage

<!-- derived-from: sdd-bug-backlog-governance sha256:828ff63c54dd -->

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <bug-id> \
  --cause "…" --caused-by none --resolved-release 0.1.0 --solution "…" \
  --evidence-loop "…" --evidence-seam "…" --evidence-diff "net-negative:…"
```

- `resolve` is the one lineage writer: `--caused-by` takes a known bug id or the
  literal `none`, and an unknown id is refused.
- `diff_direction` is derived from `--evidence-diff`'s `net-*:` prefix — there is no
  flag for it.
- `status` is `open | resolved | superseded | deferred | rejected`; `closed_at` is
  stamped once, is never earlier than the record's `ts`, and is never rewritten.
- A terminal status is reachable only through a transition carrying its evidence: a
  bare `status` or `closed_at` write is refused, as is `update` on `status`,
  `closed_at` or `caused_by`.
- A reopen is a new record declaring `caused_by`; a sweep closure is `superseded_by`.

Stage the code, the regression test and the `BUGS.jsonl` line together, in one commit.

Long-closed records leave the ledger on their own: `bugs.py archive` moves every
record closed more than 90 days ago into the bugs histo, and the candidate's closure
sweep runs it as its own step. `dadaia doctor`'s `ledgers` section validates every committed line, so a
malformed record is a finding, not a surprise.
