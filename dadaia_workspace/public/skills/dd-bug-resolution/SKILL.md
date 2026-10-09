---
name: dd-bug-resolution
description: >
  Close out Arm B on a registered bug: the seven-phase diagnosing method (lineage,
  red loop, minimise, hypotheses, instrument, seam test, cleanup) plus the resolve
  record and commit. Use when a bug carries an open record in BUGS.jsonl; registering
  one is dd-bug-registration's job.
compatibility: Standalone Agent Skill. Inside a dadaia-workspace (pip install dadaia-workspace) it also drives the SDD lifecycle — specs, backlog, bugs, releases.
---

# dd-bug-resolution — Arm B

> `dd-software-engineer` runs this directly once a bug carries a record.

## 1. Lifecycle frame

1. Inside a dadaia workspace, open `specs/bugs/AGENTS.md` (the area's scoped law) and follow it — its redaction rule
   covers the whole arc: commands, outputs, captured artifacts.
2. Hotfix job or candidate scope: `specs/bugs/AGENTS.md` §2.

## 2. The method — seven phases, each gated

**Phase 0 — Lineage.** Read the bug ledger for prior fixes to the same
`surface`/`component` in the bounded window ([`LINEAGE.md`](LINEAGE.md)); inspect every named
`fix_sha` with `git show`; a `caused_by` other than `none`, or ≥ 2 prior fixes, makes this fix a REBUILD (`specs/bugs/AGENTS.md` §2);
carry the link to Phase 6 (`resolve --caused-by`; `update` repairs);
echo the `caused_by:`/`evidence:`/`prior diffs read:`/`rebuild:` block in the fix commit body.
*Done when prior diffs were actually read and the link and the rebuild decision (`rebuild` or `none`) are decided.*

**Phase 1 — Red loop.** This is the skill; everything after it is mechanical. Build a
**tight** pass/fail signal that goes red on THIS bug — construction menu, tightening
and non-deterministic bugs: [`RED-LOOP.md`](RED-LOOP.md).
*Done when you can name ONE command, already run at least once, that is red-capable
(asserts the exact symptom), deterministic, fast, and agent-runnable. Phase 2 starts
from that command, because a theory built by reading code first is the failure this
phase prevents.*

**Phase 2 — Minimise.** Shrink the repro one cut at a time, re-running the loop after
each cut.
*Done when every remaining element is load-bearing: removing any one makes the loop
go green.*

**Phase 3 — Hypothesise.** Write 3–5 ranked, falsifiable hypotheses before touching
code — each states its prediction ("if X is the cause, changing Y makes the bug
disappear"). A hypothesis with no prediction is a vibe: discard or sharpen it.
*Done when the ranked list exists with a killing observation per hypothesis.*

**Phase 4 — Instrument.** Probe the executed path to distinguish hypotheses: debugger
or REPL first, targeted logs second, one variable at a time. Tag every probe with a
unique prefix (e.g. `[DEBUG-a4f2]`) so cleanup is a single grep. For performance
regressions: measure a baseline, then bisect — logs mislead.
*Done when one hypothesis survives by observation, not by reading code.*

**Phase 5 — Seam test.** The regression test at the correct seam, BEFORE the fix, is
a new case in the owner file with a literal expected value, at the lowest level that detects it (the root map §1: fixes never rewrite old asserts), committed by the RED-test dispatch; watch it fail,
fix the cause, watch it pass, re-run the Phase 1 loop on the original scenario. A
correct seam exercises the real bug pattern at its call site; when none exists, that
is itself the finding — return the seam gap to the main thread as a finding
before fixing.
*Done when the test fails for the real reason and passes with the fix (or the seam
gap was returned first).*

**Phase 6 — Cleanup + resolve.** Grep the probe prefix to zero:

- Commit the GREEN source fix with shape 3 of `dd-gitflow-default` §3a, then resolve with its
  40-hex sha:

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <bug-id> --specs <specs-dir> \
  --cause "…" --caused-by <prior-bug-id>\|<task-id>\|none \
  --solution "…" --fix-sha <40-hex-sha>
```

- `caused_by` names a live or archived bug, a known release task, or `none`, never a loop;
  writes refuse anything else.
- Commit the resulting ledger-only `BUGS.jsonl` transition with shape 4 of
  `dd-gitflow-default` §3a.

## 3. Done when

- Phase 0 read the window; the link is declared at resolve and echoed in the fix commit body.
- The red loop was captured before any hypothesis; the repro is minimised to
  load-bearing.
- The surviving hypothesis was confirmed by instrumentation.
- The regression test sits at the correct seam, or the seam gap was returned first.
- `git grep -n '\[DEBUG-'` prints nothing; the resolve record carries `cause`, `solution`, `caused_by`, `fix_sha`
  and `closed_at`; the fix and ledger transition are isolated; worktree clean.
- `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py check --specs <specs-dir>` exits 0.

## 4. References

- `dd-bug-registration` — classify-first registration; the record this skill requires.
- `dd-gitflow-default` §3a — the exact commit shape.
