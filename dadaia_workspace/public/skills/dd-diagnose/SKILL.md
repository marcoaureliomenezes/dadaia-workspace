---
name: dd-diagnose
description: "The diagnosing method for Arm B, called by dd-bug-resolution (`dd-bug-fix` until T-050-21's rename): seven phases from lineage through cleanup, each ending on a checkable Done when. Phase 0 reads the bug ledger's lineage before any hypothesis is formed."
applyTo: "specs/bugs/**"
disable-model-invocation: true
---

# dd-diagnose — The Diagnosing Method (Arm B)

> Not a hook-enforced mechanism. No engine advances a phase or reads bug state; the
> fixer runs this protocol directly. `disable-model-invocation: true` — this skill is
> not yet in any persona's `skills:` allowlist; it is read on reference from
> `dd-bug-resolution`, the same way `dd-audit-project` was read before `project-auditor`
> gained it (lifted once a later task wires the reference in).

## 1. When to invoke

Called by `dd-bug-resolution` (bug lifecycle, commit, branch, concurrency — kept there,
not restated here) the moment a bug carries a `reported` event and Arm B begins. This
skill owns only the **method** — the seven phases that turn a report into a proven fix.
It never registers, brands, or closes a bug on its own.

## 2. Phase 0 — Lineage

Before any hypothesis is written, read the bug ledger for prior fixes to the same
`surface`/`component`, in a bounded window, and declare this bug's own causal link (or
lack of one). Full window computation, the 20-record cap, the exact-vs-coarse diff rule,
and the `dadaia bugs update` mechanics are stated **once**, in `LINEAGE.md` (sibling) —
read it there, not restated here (A7.2: FR14's audit pillar 1 cites that same text
rather than restating it).

*Done when:* this bug's own record carries `caused_by: <bug_id> | none` and
`lineage_source: declared` (via `dadaia bugs update <id> --set caused_by=… --set
lineage_source=declared`), and the eventual fix commit body echoes the same
`caused_by:` / `evidence:` / `prior diffs read:` block `LINEAGE.md` shows.

## 3. Phases 1–6 — the six-phase method

1. **Red loop before any hypothesis.** Reproduce the failure exactly as it occurred —
   real command, real environment, real path. *Done when:* the command and its red
   output are captured.
2. **Minimise until load-bearing.** Shrink the reproduction until every remaining
   element is necessary. *Done when:* removing any element makes it stop failing.
3. **3–5 falsifiable hypotheses.** Write them before touching code, each paired with
   the observation that would kill it. *Done when:* every hypothesis is killed by an
   observation or is the last one standing.
4. **Instrument, never read code for a theory.** Add probes/logs/asserts on the
   executed path that discriminate between the surviving hypotheses. *Done when:* the
   surviving hypothesis is confirmed by an observation, not by inference.
5. **Regression test at the correct seam.** Intent/size declared at birth:
   `dadaia-test-stewardship` §A. **No correct seam exists → register an architecture
   finding and dispatch `software-architect` before fixing** — the absence of a seam is
   itself the finding. *Done when:* the test fails at HEAD, passes after the fix.
6. **Cleanup.** Remove every probe from phase 4; the diff must leave the touched
   feature smaller or equal, never bigger (`DADAIA.md` §7 (Quality) "Root cause,
   always"). *Done when:* instrumentation is gone, worktree clean and GREEN.

## 4. The `caused_by` clause — the architecture-review trigger

A `caused_by` that names a prior bug is the trigger of the standing "permanent
architecture review, oriented by bug history" order: the fixer shows the structural
cause and produces a diff that does not grow the feature. A net-positive diff routes to
`software-architect` **before** the commit (`DADAIA.md` §7 (Quality), unchanged —
referenced, not restated).

## 5. Handback to `dd-bug-resolution`

This skill ends at phase 6, GREEN. Appending the `resolved` event, the FR23 evidence
triple (`evidence_loop`/`evidence_seam`/`evidence_diff`), the commit shape, and the
no-separate-release-ceremony rule are `dd-bug-resolution`'s own bug-lifecycle territory —
consult it, do not restate it here.

## 6. Checklist

- [ ] Phase 0: window read, `caused_by`/`lineage_source` declared on this bug's record,
      the same block echoed in the fix commit body.
- [ ] Red loop captured before any hypothesis; repro minimised to load-bearing.
- [ ] 3–5 falsifiable hypotheses written before touching code.
- [ ] Surviving hypothesis confirmed by instrumentation, not by reading code.
- [ ] Test lands at the correct seam, or an architecture finding is registered and
      `software-architect` dispatched first.
- [ ] Cleanup done (probes gone, diff smaller or equal); GREEN.
- [ ] A `caused_by` naming a prior bug routed a net-positive diff to
      `software-architect` before the commit.
