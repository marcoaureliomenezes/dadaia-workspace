# ALPHA-5-QA.md — `alpha-5` (WS-G, event-driven artifact GC) segment QA gate

**Task:** T-043-45 · **Reviewer:** qa-engineer · **Segment range:** `e2e13216` (alpha-4
close) `..` `ebc3b292` (T-043-44, last alpha-5 commit) · **Reviewed at:** `f68a4205`
(reservation commit, `feature/0.4.3`) · **Reviewed:** 2026-08-18

**Verdict: APPROVED** — every `alpha-5` acceptance id in scope (A23.1–A23.3, A24.1–A24.4,
A25.1/A25.3, A26.1–A26.3, A27.1–A27.3, A28.1–A28.3, A29.1–A29.4) verified against the live
tree, AG.1 is proven per deletion lane (FR23, FR24, FR25, FR26, FR29) with one lane-guard
fixture each run live by this review, the fail-open posture of every hook-riding capability
is cited with a live fixture, V10 is recorded and coherent, PLAN §5's `alpha-5` exit
criteria are met, and the segment's one Arm-B rider carries a complete
`reported`→`resolved` bug-ledger pair with zero open bugs at review time. One decision is
routed to the operator/PM in §6.1: T-043-39's `gc_consumed_push_verdicts` is correctly
implemented and tested as a pure action function, but is not yet wired to any live push
path — this does not block A24.x (worded and fixture-tested at the function level) or
`alpha-5`'s exit criteria, but it does mean FR24's preamble claim ("the pre-push chokepoint
deletes…") is not yet true in production.

---

## 1. Scope and method

Task delta: T-043-38 (`47255c21`), T-043-39 (`b3335d97`), T-043-40 (`7c7edae6`), T-043-41
(`ef2f824e`), T-043-42 (`ee712147`), T-043-43 (`86701967`), T-043-44 (`ebc3b292`), plus the
in-segment Arm-B rider `self-scan-baseline-drift-t04343-evidence-prose`
(register `e6563504`, fix `5ff19df2`). 16 commits total in `e2e13216..ebc3b292` (7
implementation commits, 7 `chore(tasks): start` reservation commits, 1 rider register + 1
rider fix).

Every prior evidence artifact under `.dadaia/tmp/software-engineer/20260817/` (V10) is
read directly by this review. Every load-bearing claim — acceptance-id evidence, AG.1
lane-guard fixtures, fail-open fixtures, doctor/suite numbers, the bug ledger — is
independently re-run or re-derived against the live tree at HEAD by this review rather
than trusted from the implementer's prior-session prose. Where a claim is re-confirmed
live (pytest node id, grep, diff, `dadaia` CLI output), the exact command and its live
output are cited.

Memory bootstrap (step 0) self-pulled `specs/memory/product/catalog.json`,
`specs/memory/product/agents/agent-comms.md` (FR23's handoff-retention home) and
`specs/memory/product/agents/agent-monitoring.md` (FR25/FR26/FR27's future memory home) —
both atoms still describe the pre-`alpha-5` product (memory update is `rc-1`/T-043-51
territory, MEMORY-class and phase-gated to DEFINITION/CLOSURE; current phase is
IMPLEMENTATION), so nothing in either atom is stale *relative to this segment's own scope*.

---

## 2. Per-acceptance-id table

| id | Requirement (abridged) | Evidence | Verdict |
|---|---|---|---|
| A23.1 | The ack-on-consume rule is stated once; no skill restates it | `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md` `## Consuming a handoff (ack-on-consume — FR23)` section (`47255c21`). Live re-verification: `grep -rniE "delete.*(consumed\|handoff)\|handoff.*retention\|ack-on-consume" public/skills/ public/agents/` → zero hits outside `dadaia-handoff-emitter/SKILL.md` and `dd-release-closure/SKILL.md` (T-043-40's pointer, which references rather than restates — confirmed by reading its text: "a pointer to `dadaia-handoff-emitter`'s ack-on-consume rule … rather than restating it"). Both `.claude/skills/dadaia-handoff-emitter/SKILL.md` and `.agents/skills/dadaia-handoff-emitter/SKILL.md` are byte-identical to the source (`diff -q`, this review) | PASS |
| A23.2 | A consumed coordination handoff is deleted; an artifact-bearing handoff is untouched | Stated explicitly in the skill text: "A handoff carrying `artifact.path` is **exempt** — it is artifact-bearing, not purely coordination, and its retention instead follows its referenced report's retention." FR23 is a doc-only lane (no code shipped in T-043-38's write set — the rule governs every consumer skill's own future behavior, not a new deletion function); this acceptance id is a documentation-correctness claim, verified by reading the text, not a runnable fixture (D-note: FR23 is a skills-surface rule, per the task's own framing) | PASS |
| A23.3 | Deleting a handoff never breaks `dadaia reports validate` on a surviving one | Stated explicitly: "**Never break a surviving handoff.** Deleting a consumed coordination handoff must never break `dadaia reports validate` on any other handoff still on disk — deletion is scoped to exactly the one consumed file, never a directory sweep." Documentation-correctness claim (FR23 doc-only lane), consistent with A23.2 | PASS |
| A24.1 | A successful push deletes exactly the covering verdict(s); unrelated verdict survives | `tests/unit/features/chokepoints/test_push_verdict_gc.py::test_matching_verdict_deleted_and_ledgered_unrelated_survives` + `test_multiple_pushed_shas_each_covering_verdict_deleted` + `test_non_qualifying_handoff_untouched`. Live re-run by this review (§5): 3/3 pass | PASS (at the function-contract level — see §6.1 for the live-wiring disposition) |
| A24.2 | A failed or refused push deletes nothing | `test_no_confirmed_shas_deletes_nothing` (empty `pushed_shas` set → no-op). Live re-run: pass | PASS |
| A24.3 | Deletion is best-effort: an I/O error never changes the push verdict | `test_unlink_failure_is_best_effort_and_does_not_abort_sweep`. Live re-run: pass | PASS |
| A24.4 | Append-before-delete audit ledger line; a failed append leaves the handoff in place | `test_failed_ledger_append_leaves_handoff_in_place` (directory-collision at the ledger path). Live re-run: pass. Ledger `.dadaia/logs/push-verdict-gc-ledger.jsonl` — same appender family FR27 (T-043-42) rotates, confirmed by T-043-42's own "Ledger decision" note and this review's log-rotation citation in §4 | PASS |
| A25.1 | `dd-release-closure`'s template carries the sweep step with an explicit keep/delete rule | `dadaia_workspace/public/skills/dd-release-closure/SKILL.md` `## Artifact GC sweep` (CLOSURE.md template subsection) + `## Artifact GC sweep (FR25, mandatory)` (protocol section), both live-verified present at HEAD; both `.claude/`/`.agents/` projections byte-identical to source (`diff -q`, this review) | PASS |
| A25.3 | Nothing referenced by a surviving CLOSURE evidence pointer is deleted | Stated as the explicit keep/delete rule: "KEEP anything a surviving `## Validations`/`## Dispositions` evidence pointer references, no exception; DELETE the rest once unreferenced." Documentation-correctness claim (FR25 doc-only lane, mirrors FR23's framing) — **A25.2 (this release's own CLOSURE *executing* the sweep) is out of `alpha-5`'s scope by TASKS.md's own evidence map ("T-043-52 executes it (A25.2)") and is correctly deferred to `rc-1`/T-043-52, not re-verified here** | PASS (scope-correct deferral of A25.2 noted, not a gap) |
| A26.1 | A stale record and its markers are deleted; a live session's records are never touched | `tests/unit/hooks/test_post_gate_reap.py` — `test_stale_session_reaped_with_paired_markers`, `test_fresh_heartbeat_foreign_session_untouched`, `test_self_session_untouched_even_when_ancient` (17 tests total in the file). Live re-run (§5): all pass. V10's real-workspace capture independently confirms the live-session-untouched claim three ways (bound_at unchanged, presence record identical, both markers survive) — see §5 | PASS |
| A26.2 | Zombie run records are reaped; the count before/after is captured | V10: 121 → 54 lifecycle records (29 `running` + 38 `completed` reaped, `blocked` survives) — matches the SPEC's own measured evidence (29 running / 38 completed) exactly, and matches the live `RECONCILER_REAP` event logged at `2026-08-17T22:48:39Z` (`lifecycle_runs_reaped: 67` = 29+38) | PASS |
| A26.3 | Reaping is best-effort/fail-open, matching the reconciler it extends | `test_reap_never_raises_and_never_changes_exit_code` — live re-run by this review (§4): pass. Each lane wrapped in its own `contextlib.suppress(Exception)` plus the caller's outer try/except (verified by reading `hooks/sdd_post_gate.py`'s `_reap_stale_records`) | PASS |
| A27.1 | A log crossing the cap rotates; exactly one rotated file is retained | `tests/unit/infrastructure/test_jsonl_log_rotation.py` (9 unit tests) + the four writer-level wiring tests (`test_latency_log_rotates_at_the_shared_cap` in `test_pre_gate.py`, `test_reconciler_flag_rotates_the_shared_events_log`/`test_reap_event_rotates_the_shared_events_log` in the reap suite, `test_ledger_rotates_at_the_shared_cap` in the push-verdict-gc suite). Live re-run by this review (§5): all pass | PASS |
| A27.2 | A rotation error never changes a gate verdict | `test_unwritable_parent_dir_is_fail_open`, `test_append_target_already_a_directory_is_fail_open`, `test_readonly_target_file_is_fail_open`, `test_readonly_logs_dir_blocks_rotation_but_append_still_lands` — live re-run by this review (§4): pass | PASS |
| A27.3 | Concurrent writers do not corrupt the rotation (fixture with two writers) | `tests/integration/infrastructure/test_jsonl_log_rotation_concurrency.py` — two real `multiprocessing.get_context("spawn")` processes synchronized on a `Barrier(2)`. Live re-run by this review (§5): pass | PASS |
| A28.1 | A cache-enabling invocation is blocked with the corrected command in the message | `tests/unit/hooks/test_venv_guard.py::test_blocks_cache_enabling_invocation` (11 parametrized rows). Live re-run (§5, bundled in the 81-test file run): pass | PASS |
| A28.2 | A compliant invocation passes untouched; no false block on an unrelated command | Two matrices in the same file: 19-row ALLOW matrix + 12-row no-false-block matrix (`test_no_false_block_cache_guard`) + `test_fail_open_and_codex_shape` (malformed/non-Bash payloads never block). Live re-run by this review (§4 + §5): all pass | PASS |
| A28.3 | The guard stays token-matched on fixed leading tokens — no shell parsing | Verified by reading `hooks/venv_guard.py`'s `_cache_tool_name`/`_cache_guard_reason`: flag-presence scanning on `shlex.split` args, no general shell parsing; `mypy --cache-dir` is presence-only per the task's own documented letter-of-the-law reading (cannot resolve/judge the destination path without a shell parser) | PASS |
| A29.1 | The verb is idempotent — a second run reports nothing and changes nothing | `tests/unit/features/tmp_gc/test_tmp_gc_service.py` idempotent-second-real-run fixture (bundled in the 17-test file). Live re-run (§5): pass. Live idempotency also demonstrated by this review's own `--dry-run` invocation (§5) reporting only genuinely-still-present cache dirs, none from a prior run | PASS |
| A29.2 | Never deletes a live session's markers or a non-dated path | `test_lane_guard_never_matches_a_symlinked_cache_directory` + the non-dated-path-protection fixture + the fresh-orphan SessionStart-safety fixture (mtime floor). Live re-run (§5): pass | PASS |
| A29.3 | A dry-run mode reports what it would remove | Live re-run by this review, own invocation (§5): `dadaia tmp gc --dry-run` → "would reclaim 10 item(s)", all in the `cache directories` lane, zero in `dated scratch`/`orphaned session markers` — matches T-043-44's own recorded evidence shape (self-inclusion of this session's own mypy-cache dirs is expected, not a bug) | PASS |
| A29.4 | Documented as the backstop, with every other capability named as event-driven | `tests/unit/cli/commands/test_tmp_gc_cmd.py::test_help_text_names_it_as_the_calendar_backstop` (the A29.4 help-text doctrine check, bundled in the 5-test file). Live re-run (§5): pass. Live re-verification: `dadaia tmp gc --help` text names it the calendar-based backstop | PASS |

All acceptance ids in scope for `alpha-5` (A23.1–A23.3, A24.1–A24.4, A25.1, A25.3,
A26.1–A26.3, A27.1–A27.3, A28.1–A28.3, A29.1–A29.4 — 23 ids) verify PASS with live-tree
evidence independently re-confirmed by this review. A24.1–A24.4's PASS carries the explicit
function-level qualifier resolved in §6.1.

---

## 3. AG.1 — per-deletion-lane verification (segment-wide acceptance)

**AG.1 text (SPEC §segment `alpha-5`):** "Every GC deletion path **resolves** its target
before removing it, **refuses** any resolved target outside `.dadaia/`, and **never
follows a symlinked directory** — inheriting FR17's symlink doctrine by reference (A17.1),
not restating it — with a fixture per deletion lane (FR23, FR24, FR25, FR26, FR29)."

FR23 and FR25 are skills-surface (doc) lanes — no code ships in either task's write set,
so AG.1 for those two lanes is verified as **text present in the skill**, not a runnable
fixture (matching the task's own framing). FR24, FR26, FR29 are code lanes — AG.1 is
verified by **running the actual fixture** myself, not accepted by inspection, per the
task's explicit instruction.

| Lane | FR | AG.1 evidence | Method |
|---|---|---|---|
| Ack-on-consume | FR23 | `dadaia-handoff-emitter/SKILL.md` `## Consuming a handoff` — "**The deletion lane guard (AG.1 …)**: 1. Resolve the handoff's real target path. 2. Refuse the deletion if the resolved target falls outside `.dadaia/`. 3. Never follow a symlinked directory while resolving or walking to the target." | Text read live at HEAD (doc lane, no fixture exists) |
| Push-verdict GC | FR24 | `tests/unit/features/chokepoints/test_push_verdict_gc.py::test_lane_guard_never_follows_a_symlinked_directory` + `::test_lane_guard_refuses_a_target_resolving_outside_dadaia` | **Run live by this review** — both PASS (§below) |
| Release-closure sweep | FR25 | `dd-release-closure/SKILL.md` `## Artifact GC sweep (FR25, mandatory)` — "**Lane guard (AG.1, stated verbatim — inherited by every deletion lane in this release):** resolve the target, refuse any resolved target outside `.dadaia/`, never follow a symlinked directory." | Text read live at HEAD (doc lane, no fixture exists) |
| Reconciler reap | FR26 | `tests/unit/hooks/test_post_gate_reap.py::test_lane_guard_never_follows_a_symlinked_directory` + `::test_lane_guard_refuses_a_target_resolving_outside_dadaia` | **Run live by this review** — both PASS (§below) |
| `dadaia tmp gc` | FR29 | `tests/unit/features/tmp_gc/test_tmp_gc_service.py::test_lane_guard_never_follows_a_symlinked_agent_directory` + `::test_lane_guard_refuses_an_orphan_marker_resolving_outside_dadaia` + `::test_lane_guard_never_matches_a_symlinked_cache_directory` (a THIRD fixture — the cache lane's own symlink exclusion, on top of the marker-lane pair) | **Run live by this review** — all 3 PASS (§below) |

**Live run, this review** (exact node ids, one command):

```
pytest -p no:cacheprovider -q \
  "tests/unit/features/chokepoints/test_push_verdict_gc.py::test_lane_guard_never_follows_a_symlinked_directory" \
  "tests/unit/features/chokepoints/test_push_verdict_gc.py::test_lane_guard_refuses_a_target_resolving_outside_dadaia" \
  "tests/unit/hooks/test_post_gate_reap.py::test_lane_guard_never_follows_a_symlinked_directory" \
  "tests/unit/hooks/test_post_gate_reap.py::test_lane_guard_refuses_a_target_resolving_outside_dadaia" \
  "tests/unit/features/tmp_gc/test_tmp_gc_service.py::test_lane_guard_never_follows_a_symlinked_agent_directory" \
  "tests/unit/features/tmp_gc/test_tmp_gc_service.py::test_lane_guard_refuses_an_orphan_marker_resolving_outside_dadaia" \
  "tests/unit/features/tmp_gc/test_tmp_gc_service.py::test_lane_guard_never_matches_a_symlinked_cache_directory"
```

Result: **7 passed in 0.16s.** AG.1 holds for all five code/text-bearing lanes, verified
per-lane rather than accepted by inspection.

---

## 4. Fail-open posture — every capability riding a hook

SPEC's `alpha-5` preamble: "Every capability below is fail-open where it rides a hook — a
GC error never changes a gate verdict." Four capabilities ride a hook this segment; each
is cited with a fixture **run live by this review**, not re-quoted from the implementer's
session.

| Capability | Hook it rides | Fail-open fixture | Live result |
|---|---|---|---|
| Reconciler reap (FR26) | `PostToolUse` (`hooks/sdd_post_gate.py`) | `tests/unit/hooks/test_post_gate_reap.py::test_reap_never_raises_and_never_changes_exit_code` | PASS |
| Log rotation (FR27) | Every `.dadaia/logs/*.jsonl` writer, invoked from `PreToolUse`/`PostToolUse` | `tests/unit/infrastructure/test_jsonl_log_rotation.py::test_readonly_logs_dir_blocks_rotation_but_append_still_lands` (BOTH the lock and the rotate fail; the append still lands) | PASS |
| Cache guard (FR28) | `PreToolUse` (`hooks/venv_guard.py`, Bash) | `tests/unit/hooks/test_venv_guard.py::test_fail_open_and_codex_shape` (malformed/empty/non-Bash payloads never block — ALLOW is the fail-open default) | PASS (5/5 parametrized rows) |
| `pre_gate` latency telemetry | `PreToolUse` (`hooks/pre_gate.py`) | `tests/unit/hooks/test_pre_gate.py::test_telemetry_failure_does_not_change_verdict` (an unwritable logs dir — fault-injected `Path.mkdir` — never alters the gate verdict or exit code) | PASS |

**Live run, this review:**

```
pytest -p no:cacheprovider -q \
  "tests/unit/hooks/test_post_gate_reap.py::test_reap_never_raises_and_never_changes_exit_code" \
  "tests/unit/infrastructure/test_jsonl_log_rotation.py::test_readonly_logs_dir_blocks_rotation_but_append_still_lands" \
  "tests/unit/hooks/test_pre_gate.py::test_telemetry_failure_does_not_change_verdict"
```
→ **3 passed.**

```
pytest -p no:cacheprovider -q "tests/unit/hooks/test_venv_guard.py::test_fail_open_and_codex_shape"
```
→ **5 passed** (all 5 parametrized rows, including the malformed-Bash-payload and
non-Bash-tool rows that prove the guard degrades to ALLOW, never to an uncaught
exception).

`dadaia tmp gc` (FR29) does **not** ride a hook — it is an explicit, operator/CLI-invoked
verb (its own "SessionStart-safe" property is about safety-when-invoked-unattended, not
fail-open-under-hook-failure — there is no hook to fail open from), so it is correctly out
of scope for this table; its safety is instead covered by A29.1–A29.4 and its AG.1 fixture
above.

---

## 5. Suite, doctor, certification and GC-command run (live, this session)

All commands run against `feature/0.4.3` at tip `ebc3b292`; this review's own reservation
commit `f68a4205` touches only `TASKS.md`, no source:

| Check | Command | Result |
|---|---|---|
| Full suite | `pytest -p no:cacheprovider -m 'not quarantine' -n auto` | **2576 passed, 3 skipped, 0 failed** (62.61s) — identical to T-043-44's recorded baseline (no source change since) |
| CI preflight | `dadaia ci preflight` | **5/5 PASS** — `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest` |
| Workspace doctor | `dadaia doctor` | **All invariants OK — workspace is healthy** |
| Specs doctor | `dadaia specs doctor --context dadaia-workspace` | **0 errors, 5 warnings** — 1 `LINT-1` heading-allowlist family + 2 `SPEC-DOC-027` legacy release-dir names + 2 `SPEC-DOC-036` un-disposed archived-audit warnings — identical pre-existing set to `ALPHA-4-QA.md`'s record, none newly introduced by `alpha-5` |
| Public doctor | `dadaia public doctor` | 0 `[error]` lines; **`[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution`**; one `[info] codex:trust-boundary` line (unchanged, pre-existing) |
| `dadaia tmp gc --dry-run` (never destructive) | `dadaia tmp gc --dry-run` | **"would reclaim 10 item(s)"** — all 10 in the `cache directories` lane (this session's and prior same-day sessions' `mypy-cache*` dirs under `tmp/**`); **zero** in `dated scratch` or `orphaned session markers` — matches T-043-44's own recorded evidence shape exactly, confirming the 3-day age floor protects live CLOSURE-evidence captures |
| AG.1 lane-guard fixtures (targeted, §3) | 7 named node ids | **7 passed** |
| Fail-open fixtures (targeted, §4) | 8 named node ids across two commands | **3 passed** + **5 passed** = 8 passed |
| Full alpha-5 code-lane suite (targeted) | `pytest -p no:cacheprovider -q tests/unit/features/chokepoints/test_push_verdict_gc.py tests/unit/hooks/test_post_gate_reap.py tests/unit/features/tmp_gc/test_tmp_gc_service.py tests/unit/cli/commands/test_tmp_gc_cmd.py tests/unit/infrastructure/test_jsonl_log_rotation.py tests/integration/infrastructure/test_jsonl_log_rotation_concurrency.py tests/unit/hooks/test_venv_guard.py tests/integration/test_repo_self_scan.py` | **147 passed** (0 failed), including `test_repo_self_scan.py` 5/5 |
| Bug ledger | `dadaia bugs status` | **`[ok] 0 open bug(s)`** |

---

## 6. Disposition — items this review must judge explicitly

### 6.1 T-043-39's `gc_consumed_push_verdicts` is a pure action function with no live chokepoint wiring

**Verdict: A24.1–A24.4 hold at the function-contract level; `alpha-5`'s PLAN §5 exit
criteria are not blocked; the live-wiring gap is a genuine, correctly-scoped decision
routed below — not silently passed as "delivered".**

**The facts, re-verified live by this review** (not re-quoted): `push_gate_decision`
(the pre-push chokepoint) runs entirely **before** git transfers any object, so "the push
succeeded" is categorically unknowable from inside it — a remote rejection can still fail
the push after the hook already returned ALLOW. `gc_consumed_push_verdicts`
(`features/chokepoints/service.py`) is therefore, by design, a **separate pure action
function** — its own module docstring documents that it requires an out-of-band,
already-confirmed-successful `pushed_shas` set from a **future caller** (a
`reference-transaction` git hook or a `git push`-wrapping CLI verb), and that caller is
**explicitly out of scope** for T-043-39 (not in its declared write set: no hook script,
no CLI wiring added). Live grep confirms this review's own re-check: no call site in
`hooks/`, `cli/`, or any `.dadaia/` git-hook script invokes `gc_consumed_push_verdicts` —
the only callers are its own test suite.

**Judged against SPEC wording (§2 rationale):** A24.1–A24.4's literal text describes
scenario-level function behavior ("a successful push deletes…", "a failed or refused push
deletes nothing…", "deletion is best-effort…", "the append precedes the delete…") — every
one of these is fully testable, and fully tested, by constructing a `pushed_shas` set that
*models* "a successful push" and asserting the function's contract, which is exactly what
the 10 fixtures in `test_push_verdict_gc.py` do (re-run live by this review, §2). None of
A24.1–A24.4's literal wording requires the *caller* to exist yet. `alpha-5`'s PLAN §5 exit
criteria ("FR23–FR29 `[x]`; V10 captured; every GC capability fail-open-proven;
`qa-engineer` review committed") likewise does not require live end-to-end wiring — it
requires the task marked `[x]` (true) and the capability's fail-open posture proven
(true, though moot for FR24 specifically since nothing calls it yet — there is no live
failure mode to prove fail-open for an uncalled function). **On these grounds, A24.1–A24.4
PASS and this does not block `alpha-5`'s close.**

**But the gap is real and must be named, not absorbed.** FR24's own SPEC preamble states,
as present-tense product behavior: *"After a successful push, the pre-push chokepoint
deletes the APPROVED `security-reviewer` verdict handoff(s)…"* — this sentence is **not
yet true of the live system**: no push, successful or otherwise, currently triggers this
function. If `rc-1`'s memory window (T-043-51) or CLOSURE (T-043-52) were to record FR24
as fully delivered without qualification, that would encode a false claim into product
memory — the same failure mode `ALPHA-4-QA.md` §4.3 named for the stale `harness-codex.md`
claim, just inverted (there, memory lagged a true implementation fact; here, an
implementation fact would lag what memory could claim).

**Routing (the three options named in the dispatch, decided here):**

1. *In-release task* (add a small wiring task before `rc-1` ship) — **not recommended as
   a blocking requirement for this segment's close**: it would require designing the
   `reference-transaction`-hook or `git push`-wrapping-CLI caller, a nontrivial design
   decision (which mechanism, what failure modes) that the task's own docstring
   deliberately deferred rather than rushed. Forcing it into `alpha-5` or a late `alpha-6`
   slot risks exactly the kind of un-designed, rushed wiring the segment's "pure action
   function first" scoping was trying to avoid.
2. **`rc-1` CLOSURE memory window (recommended primary routing):** T-043-51 must record
   FR24 honestly — "the deletion/ledger/fail-open contract is implemented and tested; the
   live push-path caller is not yet wired; a push today never invokes this function" —
   rather than an unqualified "delivered" claim. This mirrors the precedent
   `ALPHA-3-QA.md`/`ALPHA-4-QA.md` already set for CLOSURE-deferred, UNVERIFIED-by-design
   memory items (A21.5/A21.6, harness-codex.md).
3. **Operator/PM intake (secondary routing):** the actual wiring work (a
   `reference-transaction` hook or a `git push`-wrapping CLI verb) is named here as a
   concrete, well-scoped follow-up candidate for `project-manager`'s intake report to
   route to the backlog — it is real, scoped, low-priority (the ledger already preserves
   the audit trail even with zero deletions actually happening, so nothing is silently
   lost by deferring it), and not this review's to materialize as backlog demand itself.

This review's disposition: **routing (2) + (3) together — not (1).** Recorded as a
`decisions_required` item in this review's handoff for `project-manager`.

### 6.2 The segment's one Arm-B rider

**Bug:** `self-scan-baseline-drift-t04343-evidence-prose` — the only bug event timestamped
inside the `alpha-5` window (`e2e13216..ebc3b292`, confirmed by direct read of
`specs/bugs/bugs.jsonl`, filtering every bug id touched in that range: the segment's
`alpha-3`/`alpha-4`-window bugs — `specs-doctor-segment-router-silent-skip`,
`skill-orphans-unwired-agent-frontmatter`, `repo-self-scan-hits-alpha2-qa-historical-literal`,
`t043-33-absolute-path-leaked-into-tasks-md` — all pre-date `e2e13216` and are already
accounted for in `ALPHA-3-QA.md`/`ALPHA-4-QA.md`).

| Rider commits | Bug id | `reported` | `resolved` |
|---|---|---|---|
| register `e6563504`, fix `5ff19df2` | `self-scan-baseline-drift-t04343-evidence-prose` | 2026-08-18T00:21:24Z | 2026-08-18T00:23:49Z |

T-043-43's own evidence prose quoted a literal `/home/<user>/…` fixture path, tripping the
shrink-only `home-abs-path` baseline pattern; the fix redacted it to `<redacted>` in the
same file. Confirmed pre-existing (not this review's session) via the git log timestamps
above, both inside T-043-44's own commit window (per T-043-44's evidence: "registered as
bug…, root-cause fixed…, and the bug closed…, full Arm B, off this task's own write set").
Live `dadaia bugs status` at review time (§5): **`[ok] 0 open bug(s)`.**

### 6.3 The GC surface `alpha-6`'s consumer round must exercise (feeds A30.6)

SPEC A30.6: "The round's scope explicitly includes the `alpha-5` GC surface — the artifact
names which GC capabilities the journey exercised." This review names the concrete,
independently exercisable touchpoints the `alpha-6` consumer journey should hit, so its
own artifact can honestly report "exercised" vs. "not exercised, because…" per A30.4:

1. **Ack-on-consume (FR23)** — during the consumer round's own agent-to-agent handoff
   traffic, confirm at least one consumer skill invocation (e.g. a dispatcher relaying a
   sub-agent's coordination handoff) deletes the consumed handoff file and leaves any
   artifact-bearing handoff untouched.
2. **Push-verdict GC (FR24)** — **cannot be exercised as a live end-to-end push
   behavior** (per §6.1: nothing calls it yet); the round should instead exercise it, if
   at all, as a **direct function-level smoke check** against the throwaway workspace's
   own `.dadaia/` (construct a fake APPROVED verdict handoff + a `pushed_shas` set,
   confirm deletion + ledger line), or explicitly record it as "not exercised — the
   capability has no live caller yet, see `ALPHA-5-QA.md` §6.1" — never silently reported
   as exercised via a real push.
3. **Release-closure sweep (FR25)** — not directly exercisable in a throwaway workspace
   that never reaches its own release closure within the round's budget; record as
   "not exercised — closure lifecycle out of the round's scope" per A30.4, unless the
   round's own scripted journey happens to run a closure.
4. **Reconciler reap (FR26)** — trivially exercisable: the throwaway workspace's own
   installed `PostToolUse` hook fires this automatically (as V10 demonstrated for THIS
   workspace); the round should stage at least one artificially-staled session/marker
   record and observe the next reconciler pass reap it (or confirm via
   `.dadaia/logs/reconciler-events.jsonl`'s `RECONCILER_REAP` event that a pass ran even
   if it found nothing to reap).
5. **Log rotation (FR27)** — exercisable by driving enough hook-writer traffic (or
   directly lowering `LOG_ROTATION_MAX_BYTES` for the probe, as this review's own
   fixtures do) to observe a `.1` rotated file appear under `.dadaia/logs/`.
6. **Cache guard (FR28)** — trivially exercisable: attempt one deliberately
   cache-enabling Bash tool call (`pytest` with no `-p no:cacheprovider`) inside the
   throwaway workspace and confirm the `PreToolUse` hook blocks it with a corrected
   command in the message.
7. **`dadaia tmp gc` (FR29)** — exercise **both** modes explicitly, per this review's own
   demonstrated pattern: `dadaia tmp gc --dry-run` first (report-only, always safe), then
   the destructive form **only inside the throwaway workspace's own disposable `.dadaia/`
   tree**, never against the real workspace — mirroring this review's own restraint
   (dry-run only, real workspace, per the task's explicit instruction).

Touchpoint 2 is the one the round's artifact must record honestly as limited, per §6.1's
disposition — everything else is a genuine, currently-live capability.

---

## 7. Findings

No CRITICAL, HIGH, or MEDIUM findings. No LOW findings requiring intake beyond the one
named decision.

**Decision required (routed to `project-manager`, not silently absorbed):**
- §6.1 — `gc_consumed_push_verdicts` (FR24) has no live caller; A24.1–A24.4 hold at the
  function-contract level, but FR24's SPEC-preamble claim of live behavior is not yet
  true. Recommended routing: honest CLOSURE memory recording (T-043-51) + operator/PM
  backlog intake for the actual wiring (`reference-transaction` hook or `git
  push`-wrapping CLI verb) as a future, well-scoped, low-priority item — not an in-release
  blocking task.

**INFO (record-only, already covered by design, not repeated in intake):**
- §6.2 — the segment's single Arm-B rider is fully closed with a complete bug-ledger pair;
  `dadaia bugs status` shows zero open bugs at review time.
- §6.3 — the concrete GC-surface touchpoint list for `alpha-6`'s consumer round (feeds
  A30.6) is named above; touchpoint 2 (FR24) is explicitly flagged as
  not-live-exercisable, so the round's own A30.4 honesty requirement is pre-warned rather
  than discovered mid-round.

---

## 8. Verdict

**APPROVED.** All 23 in-scope `alpha-5` acceptance ids (A23.1–A23.3, A24.1–A24.4, A25.1,
A25.3, A26.1–A26.3, A27.1–A27.3, A28.1–A28.3, A29.1–A29.4) PASS with live-tree evidence,
independently re-run or re-derived by this review rather than re-quoted from the
implementer's own session. AG.1 is proven per deletion lane (FR23, FR24, FR25, FR26,
FR29) — the two doc-only lanes (FR23, FR25) by reading the stated text, the three code
lanes (FR24, FR26, FR29) by **running all 7 lane-guard fixtures live**, none accepted by
inspection. The fail-open posture of every capability riding a hook (reconciler reap, log
rotation, cache guard, `pre_gate` latency telemetry) is cited with a fixture **run live by
this review**, 8/8 passing. V10 (the reconciler-reap before/after capture) is confirmed
present on disk and internally coherent — its deltas match the logged
`RECONCILER_REAP` event exactly, and its live-session-untouched claim is proven three
independent ways. PLAN §5's `alpha-5` exit criteria are fully met: FR23–FR29 all `[x]`,
V10 captured, every GC capability's fail-open posture proven, this `qa-engineer` review
committed. The segment's one Arm-B rider closes with a complete bug-ledger pair;
`dadaia bugs status` shows zero open bugs at review time. The T-043-39 live-wiring gap
(§6.1) does not block A24.x or this segment's close — it is judged, not silently passed,
and routed to `rc-1`'s CLOSURE memory window plus operator/PM backlog intake, never left
implicit. The GC surface `alpha-6`'s consumer round must exercise (feeding A30.6) is named
concretely in §6.3, with the one non-live-exercisable touchpoint (FR24) flagged in
advance. The full gating suite (2576 passed, 3 skipped, 0 failed), `dadaia ci preflight`
(5/5), `dadaia doctor`, `dadaia specs doctor` (0 errors, 5 pre-existing warnings, unchanged
set), `dadaia public doctor` (0 errors), and a live `dadaia tmp gc --dry-run` (10 items,
all cache-lane, zero scratch/marker items — matching T-043-44's own recorded evidence
shape) are all green. `alpha-5` is cleared to close.
