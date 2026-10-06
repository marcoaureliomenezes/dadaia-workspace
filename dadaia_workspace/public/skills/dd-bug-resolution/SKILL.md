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
> Git chokepoints (`.dadaia/AGENTS.md`) are the only mechanical backstop.

## 1. Lifecycle frame

1. Inside a dadaia workspace, open `specs/bugs/AGENTS.md` (the area's scoped law) and follow it — its redaction rule
   covers the whole arc: commands, outputs, captured artifacts.
2. Fix now only a block-list bug (`specs/bugs/AGENTS.md` §2), as a hotfix job in its own worktree; any other in the rc's bug batch, before its Reconciliation job.

## 2. The method — seven phases, each gated

**Phase 0 — Lineage.** Read the bug ledger for prior fixes to the same
`surface`/`component` in the bounded window ([`LINEAGE.md`](LINEAGE.md)); ≥ 2 prior fixes on the unit
make this fix a REBUILD of it (LINEAGE.md); carry the link to Phase 6 (`resolve --caused-by`; `update` repairs);
echo the `caused_by:`/`evidence:`/`prior diffs read:`/`rebuild:` block in the fix commit body.
*Done when prior diffs were actually read and the link and the rebuild decision (`rebuild` or `none`) are decided.*

**Phase 1 — Red loop.** This is the skill; everything after it is mechanical. Build a
**tight** pass/fail signal that goes red on THIS bug — construction menu, tightening
and non-deterministic bugs: [`RED-LOOP.md`](RED-LOOP.md).
*Done when you can name ONE command, already run at least once, that is red-capable
(asserts the exact symptom), deterministic, fast, and agent-runnable. No red-capable
command, no Phase 2 — reading code to build a theory first is the exact failure this
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
a new case — a parametrize row in the owner file, a literal expected value — at the lowest level that detects it (the root map §1: fixes never rewrite old asserts); watch it fail,
fix the cause, watch it pass, re-run the Phase 1 loop on the original scenario. A
correct seam exercises the real bug pattern at its call site (`dd-codebase-design`
owns the seam vocabulary and the deletion test the fix must pass); when none exists, that
is itself the finding — register an architecture finding and dispatch
the architecture lens before fixing.
*Done when the test fails for the real reason and passes with the fix (or the seam
gap is registered first).*

**Phase 6 — Cleanup + resolve.** Grep the probe prefix to zero; rewriting an old assert is its own commit, with a reason:

- Stage the code and its test first: `resolve` blames the lines the staged diff removes.

```
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <bug-id> --cause … --caused-by …
  --solution … --evidence-loop … --evidence-seam …
```

- `caused_by` names a live or archived record, or `none`, never a loop; writes refuse else.
- Stage code + regression test + the `BUGS.jsonl` line together, the red loop in the body, a hotfix's
  naming `block: <item>` — ONE commit, shape 3 of `dd-gitflow-default` §3a.

## 3. Done when

- Phase 0 read the window; the link is declared at resolve and echoed in the fix commit body.
- The red loop was captured before any hypothesis; the repro is minimised to
  load-bearing.
- The surviving hypothesis was confirmed by instrumentation.
- The regression test sits at the correct seam, or the seam gap was registered first.
- Probes are gone; the resolve record carries `evidence_loop`, `caused_by`,
  `resolved_release` and `closed_at`; one isolated commit; worktree clean.

## 4. References

- `dd-bug-registration` — classify-first registration; the record this skill requires.
- `dd-gitflow-default` §3a — the exact commit shape.
