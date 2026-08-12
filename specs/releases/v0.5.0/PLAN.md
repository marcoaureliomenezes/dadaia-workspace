# PLAN — Release v0.5.0 — One context-resolution authority, a healable ledger, hardening at chokepoints

> **Status:** Aprovado

**Release ID:** v0.5.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.5.0/SPEC.md`
**Branch:** `feature/v0.5.0`

## 1. Planning problem

v0.3.0 and v0.4.0 were **demolitions**: a subsystem was cut out and the tree closed over the
hole. FR1 is not that. It is a **transplant on a load-bearing organ** — every hook, every
verb, the gate, the memory injector and the certification entrypoint resolve a context on
every invocation. Five ladders must become one *without a moment where the tree resolves
nothing*, and the failure mode is silent: a wrong context does not crash, it writes the
right bytes into the wrong repo, or injects another project's memory.

Three consequences shape the plan.

**The new authority lands before anything is deleted.** Stage 1 adds the single function and
re-points all five consumers to it while the old rungs are still physically present but
unreachable. The suite is green at that boundary with zero behavioral regression; only then
does Stage 2 delete. A deletion-first order would leave the tree unresolvable mid-lane.

**The gate's semantics are the trap.** `sdd_gate._context_slug` is path-FIRST; the law is
env-first. Unifying naively inverts attribution for every write into `repos/<slug>/` from a
shell carrying a stale `DADAIA_CONTEXT` — and the gate would keep passing its own tests
while misattributing presence. The `target_path` rung-0 parameter is the design answer, and
Stage 1 proves it with a test that writes into `repos/x/` with `DADAIA_CONTEXT=y` and asserts
`x`.

**The live instance is the acceptance surface, not the fixture.** This workspace is a real
instantiated consumer of its own library. FR1 must be exercised from a Claude session (rung
2), a plain shell (rung 1) and a bare `repos/<slug>/` cwd (rung 3) on this instance before
the release is closeable. A green internal gate that diverges from real behavior is itself a
bug (§6).

FR2, FR3 and FR4 are independent of that risk. FR2 and FR3 are small, self-contained lanes
that can run in parallel with FR1 by different agents — their write sets are disjoint from
FR1's. FR4 runs **last** and depends on FR2: re-terminalizing a deferred bug legally means
appending compensating events, and until FR2's healing rule ships, a compensating append
against an already-flagged stream cannot be verified green by `specs doctor`.

## 2. Execution lanes

### Lane A — FR1 stage 1: the authority and its consumers (additive only)

**Owner:** software-engineer.

1. Add `resolve_context(explicit=None, *, target_path=None)` to `core/specs_resolver.py`
   implementing the SPEC's four-rung contract, plus the registry inverse
   `context_name_for_repo_slug(workspace_root, slug)` next to the existing
   `repo_slug_for_context` (`:93-125`). Both are pure additions at this stage.
2. Re-point the five consumers, one commit each so each is independently revertible:
   - `cli/_specs_resolution.resolve_context_for_cli` delegates (its `--context`/explicit
     value enters rung 0);
   - `hooks/sdd_gate._context_slug` delegates with `target_path=fpath` (path-first
     preserved through rung 0);
   - `hooks/sdd_post_gate.py` presence attribution (the read side) delegates;
   - `container` exposes the one factory the hooks and verbs use.

   **ctx_inject is deliberately NOT re-pointed here.** In `_newest_qualifying_marker`
   (`ctx_inject.py:145-180`) name resolution and the **injection trigger**
   (marker-newer-than-sentinel) are fused in one function; a "name-only" delegation at this
   stage would either double-inject on every prompt for marker-bound sessions or keep the
   marker call anyway. Both halves move together, in step 3.
3. Move ctx-inject wholesale: delegate its **name** resolution to the authority *and* switch
   its **injection trigger** from marker mtime to the session record's bind timestamp vs the
   sentinel (`ctx_inject.py:145-198`), in one commit. Its sentinel / `recorded_slug`
   compaction logic is untouched — a separate mechanism.

   **One behavior change, intended and declared:** today a **same-context re-bind does not
   re-inject** (the `recorded_slug == context` guard, `ctx_inject.py:531`); under a
   `bound_at`-newer-than-sentinel trigger it will. That is a *desired* correction — a re-bind
   is how a mode or release change reaches a live session, and today that change is invisible
   to the injected context. It is not a one-for-one swap and the PLAN does not claim it is.
   FR-W2-02 (a pre-existing bind never injects into a fresh session) must be **re-proven**
   under the new trigger, not assumed.

**Verification gate:** full suite green; `dadaia doctor`/`specs doctor`/`public doctor`/
`certify --json` green; the four new law tests (env rung, record rung, cwd-repo rung,
rung-0 `target_path`) and the gate-inversion test green; FR-W2-02 re-proven; **no file
deleted yet**.

### Lane B — FR1 stage 2: the deletions

**Owner:** software-engineer. **Precondition:** Lane A complete and green.

4. Delete the ladder bodies: `specs_resolver._persisted_bind_context`, `_marker_chain`, the
   `DADAIA_SESSION_ID` resolution channel in `_session_context`, and the old
   `resolve_bound_context_name` entrypoint (callers already moved in Lane A).
5. Delete the marker subsystem: `session_identity.{write_bind_epoch,iter_bind_epochs,
   read_bind_epoch_pids,read_bind_epoch_sid}` **and the now-false marker narrative at
   `session_identity.py:115-123`**, `container.resolve_persisted_bind_context`,
   `ctx_inject._newest_qualifying_marker`, `cli/_specs_resolution.current_ancestry_pids`,
   `.dadaia/states/bind_epoch/` writes, and the ancestry-chain plumbing that existed only to
   feed them. **`hooks/sdd_post_gate._adopt_attributed_bind` (`:108-176`) and its call site
   (`:296-305`) are deleted by name in the same commit** — it is the sole caller of
   `resolve_persisted_bind_context` and `read_bind_epoch_sid`, so deleting the callee without
   it leaves either an import error or a silently dead path. Its replacement for kimi-code is
   `DADAIA_CONTEXT` at harness launch (SPEC FR1 coupling 2), plus the `bind` warning in
   step 6.
6. Delete the workarounds and dead surface: the pop/restore block
   (`_specs_resolution.py:141-148`), `_SELF_HOSTING_SLUG` + `_is_self_hosting_checkout`
   (`:71`, `:96-103`, `:151-152`), the `cwd/specs` fallback plus its workspace-root refusal
   patch (`specs_resolver.py:351-363`), the `DADAIA_AGENT_RUNTIME` alias (`sdd_gate.py:200`,
   `cli/commands/context.py:519`), and the stale "first-ALIVE" docstring
   (`_specs_resolution.py:22-23`).
7. Collapse the four session-id micro-ladders in `cli/commands/context.py` (`:276`, `:516`,
   `:599`, `:630`) into one helper, and add the **bind warning**: when `bind` can neither key
   a harness-native record nor see `DADAIA_CONTEXT`, it prints loudly that the binding is
   reachable only by exporting `DADAIA_CONTEXT=<ctx>`. This is the one addition in an
   otherwise subtractive lane, and its §12.4 justification is explicit: the deleted adoption
   path used to make that binding work invisibly, so removing it without a warning would
   convert a working flow into a silent no-op.
8. Test surface: delete the tests that pin a deleted rung (with their rung, in the same
   commit — a pin that outlives its subject leaves the suite red across a task boundary);
   re-point the tests that pin a law rung. **No `skip`/`xfail` placeholders.**

**Verification gate:** full suite green; every FR1 grep assertion returns 0;
`core/specs_resolver.py` ≤ 200 lines; goldens byte-identical (none is expected to move in
this lane — any that does is a finding, not a regen).

### Lane C — FR1 stage 3: law, contract, docs

**Owner:** ai-engineer (assets and law), software-engineer (`setup.cfg`).

9. Rewrite the `setup.cfg` import-linter contract
   `bind-resolution-seam-is-a-single-home` (`:241-275`) to police the **new** seam, keeping
   `allow_indirect_imports = True` and **zero** `ignore_imports`.
10. Amend `public/data/DADAIA.md` §3 (`:103-106`) for precision (live session record keyed by
    the harness session id; the non-harness-shell `DADAIA_CONTEXT` guidance), then
    `dadaia public stage` → `install --target all` → `public doctor`. The projected copies
    are never hand-edited.
11. Update the skills that teach binding: `dadaia-workspace-manager`,
    `dadaia-workspace-spec-navigator`, `dadaia-cli`, plus
    `public/data/CONSUMER_VALIDATION_RECIPE.md:115-120` and `public/data/dadaia-AGENTS.md`.
    Three things must be taught by name: the **kimi-code launch-env binding**
    (`DADAIA_CONTEXT` exported by the harness), `context heartbeat` (whose marker-sid path
    dies with the subsystem — a plain-shell bind without `eval` no longer resolves through a
    marker), and the `bind` warning from step 7.

**Verification gate:** `lint-imports` green; four projected `DADAIA.md` copies byte-identical
to source and mode `0444`; `public doctor` `[ok] public-privacy`; suite green.

### Lane D — FR2: the healable ledger (independent, parallel to A–C)

**Owner:** software-engineer.

12. RED first: a test asserting that a violation row followed by a LATER `reported` for the
    same `bug_id` is **not** reported, and that an uncompensated one still is.
13. Add the whole-history diagnosis function to `core/models/bugs.py` beside
    `advance_coherence` (unchanged); make `doctor_governance._fold_bug_coherence`
    (`:432-460`) a thin caller.
14. Append the two compensating events for `closure-catalog-references-missing-memory-atom`
    via `dadaia bugs append` (never by editing the file): `reported` documenting the
    historical repair, then `resolved` citing `specs/bugs/bugs.jsonl:719` / release `0.4.2`.

**Verification gate:** `dadaia specs doctor` and `--json` exit 0 with 0 errors; the service's
append-refusal tests still green (enforcement untouched); `git diff specs/bugs/bugs.jsonl`
shows **appended lines only**.

### Lane E — FR3: four chokepoints (independent, parallel to A–C)

**Owner:** software-engineer. Each item is RED-first and one commit.

15. `LedgerEntry` relpath validation (`core/models/install_ledger.py`) — one authority, both
    consumers (`public_assets.py:773-788` and `:1365-1385`) covered without touching either.
16. `DoctorLine.render()` control-character escaping (`core/models/doctor_report.py:75-77`).
    Goldens: only lines whose text legitimately changes under escaping may move, and each is
    explained in the commit message.
17. `codex_doctor.check_entities_derivation` shape normalization at the parse seam
    (`:654-664`) emitting a typed `ENT-DERIVE-1` error line.
18. Kimi reader lexical containment (`features/telemetry/reader/kimi.py:103-109`) + the
    reader's **first** test file, using the existing `DADAIA_KIMI_SESSION_INDEX` override.

**Verification gate:** suite, ruff, mypy `--strict` green after each item; goldens explained.

### Lane F — FR4: triage and dispositions (last)

**Owner:** product-engineer (dispositions), software-engineer (verification runs).
**Precondition:** Lane D shipped.

19. Verify each of the 12 deferred bugs against current `main`; record the verdict and its
    evidence per bug.
20. Append the compensating ceremony for the obsolete ones (`reported` reopen-note, then
    `superseded`/`resolved` with evidence). Still-real bugs stay `deferred`, untouched.
21. Backlog terminal dispositions written into CLOSURE, including the ~3.5k-vs-≤3k token
    count recorded as an **accepted deviation**, not a silent pass.

**Verification gate:** `dadaia bugs status` reflects the new counts; `specs doctor` still 0;
append-only proven by diff.

### Lane G — QA, review, ship

**Owner:** qa-engineer, then code-reviewer + security-reviewer.

22. `alpha-1` close: qa-engineer validates FR1 on the **live instance** across the
    four-profile rung matrix (Claude, **kimi-code**, plain shell, `repos/<slug>/` cwd) plus
    the gate-attribution case, and runs the SPEC §6 list end to end.
23. `rc-1`: code-review six-axis; security-reviewer re-verifies FR3 items 1-4 fixed and item
    5 re-scoped, and emits the APPROVED handoff whose `metrics.commit_sha` equals the pushed
    ref sha.
24. Push → PR → watch CI to green on every job → merge → CLOSURE.

## 3. Sequencing

```
Lane A (FR1 authority + consumers)  ──▶ Lane B (FR1 deletions) ──▶ Lane C (law/contract/docs)
Lane D (FR2 healing)                ──────────────────────────────────────────┐
Lane E (FR3 chokepoints)            ──────────────────────────────────────────┤
                                                                              ▼
                                                        Lane F (FR4 triage) ──▶ Lane G (QA/review/ship)
```

A → B → C is strictly ordered. D and E are disjoint from A–C in write set and may run in
parallel; F needs D; G needs everything.

**One carve-out from the disjointness claim: golden fixtures.** Lane E's escaping change
(step 16) and Lane C's asset re-projection (steps 10-11) can both legitimately touch golden
files. They are ordered rather than parallel: **Lane C's projections land before Lane E's
escaping commit**, so any golden movement has exactly one candidate cause at any time. If
schedule forces the reverse, the merge risk is accepted explicitly in the task's commit
message and both goldens are re-derived from scratch, never merged by hand.

## 4. Risk points

**Silent misattribution (FR1's real risk).** The tree does not crash on a wrong context — it
writes correctly-formed bytes into the wrong place. Mitigations: Lane A's re-point is
behavior-preserving and gated on a green suite *before* any deletion; the gate-inversion test
is written before the gate consumer is re-pointed; and the live-instance rung matrix is an
explicit QA gate, not a smoke test.

**The marker was load-bearing for a whole harness, not only for resolution.** For kimi-code
— which exposes no native session-id env var — `_adopt_attributed_bind`
(`sdd_post_gate.py:108-176`) was the **writer** that made the session record exist at all.
Deleting the markers without disposing of it converts kimi's in-session bind into a silent
no-op: no injection, no gate mode, no heartbeat context, no error. Mitigations: the SPEC
names the disposition (launch-env `DADAIA_CONTEXT`), Lane B deletes the adoption path **by
name** in the same commit as its callee, step 7 adds the loud `bind` warning so the failure
can never be silent, and kimi-code is a **mandatory** profile in the live rung matrix — QA
without it cannot detect this regression.

**The marker was load-bearing for injection, not only for resolution.** ctx-inject used
marker mtime as the *epoch* signal. The session record's bind timestamp replaces it
one-for-one; the compaction `recorded_slug` fallbacks (`ctx_inject.py:444`, `:469`,
`:501-506`) are a different mechanism and stay. Post-compact behavior is re-verified against
`CONSUMER_VALIDATION_RECIPE.md:376`.

**Certification is env-scrubbed by design.** `service.py:82-89` deliberately removes every
context env var, then `:195-213` supplies `CODEX_THREAD_ID` — the surviving rung 2. If a
certify check regresses, the sanctioned remedy is exporting `DADAIA_CONTEXT` for its scratch
workspace (rung 1). **Re-adding a resolution rung to make certify pass is forbidden**; that
would recreate the defect this release removes.

**A contract that outlives its seam.** `setup.cfg:241-275` names 23 modules and takes zero
ignores. It must be rewritten in Lane C, in the same release — a stale contract passing green
is worse than no contract, because it certifies a seam that no longer exists.

**Golden churn as camouflage.** FR3 item 2 changes a rendering authority every doctor golden
passes through. Only lines whose text legitimately changes under escaping may move; a
broader diff means a producer was emitting control characters, which is a finding to report,
not a regen to accept.

**Append-only is a hard invariant.** FR2 and FR4 both write to `specs/bugs/bugs.jsonl`
exclusively through `dadaia bugs append`. Any diff hunk that is not a pure append fails the
lane.

## 5. Validation strategy

- **Per task:** package imports, suite collects, `pytest -p no:cacheprovider -q` green.
- **Per lane boundary:** the lane's verification gate above, plus `ruff format --check`,
  `ruff check`, `mypy --strict`, `lint-imports --no-cache`.
- **Goldens:** byte-identical everywhere except the FR3 item-2 escaping lines and any
  projection whose source asset Lane C edited. Every moved line is explained in its commit
  message.
- **Live instance (non-negotiable):** the four-profile FR1 rung matrix (Claude, **kimi-code**,
  plain shell, `repos/<slug>/` cwd), `dadaia context bind` →
  `context show --json` → a MUTATING write, post-compact injection, and
  `doctor`/`specs doctor`/`public doctor`/`certify --json` all run on this workspace, not
  only in fixtures.
- **Ship gates:** SPEC §6 in full → qa `alpha-1` → code-review + security-reviewer APPROVED
  handoff → push → CI green on every job → merge → CLOSURE + memory update + archive.
