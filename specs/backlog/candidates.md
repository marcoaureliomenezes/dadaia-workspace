# Backlog index — PM-curated

> **Consolidated 2026-07-10** (5 entries, PR #147). **Release-defined 2026-07-10**
> (operator goal: inspect entry-by-entry → research architecture/code → define
> well-scoped releases; lock focus under the ratified NO-LOCKS DOCTRINE). Every claim
> re-verified at HEAD; research evidence: full blocking-path map (gate/lease/
> chokepoints/locking), per-intent CONFIRMED sizing of all 5 lifecycle intents,
> bind-seam call-site census (15 hardcoded `--context` defaults; partial seam consumed
> by 5 command modules).

## The 5 consolidated entries

| # | Entry | Priority | Release | One-liner |
|---|---|---|---|---|
| 1 | `20260710-lock-lease-session-identity-kernel` | **P0** | **v0.1.76** | REMOVE all concurrency blocking; advisory presence replaces the lease (no-locks doctrine) |
| 2 | `20260709-central-bind-resolution-seam` | **P0** | **v0.1.77** | ONE bind-resolution seam for every resolver-driven verb + dynamic contract test |
| 3 | `20260710-lifecycle-pipeline-correctness-and-diagnosability` | **P1** | **v0.1.78** | lifecycle engine tells the truth; every block carries evidence + exact next command |
| 4 | `20260708-panel-tab-reorg-agentic-layers` | **P2** | **v0.1.79** | 7→6 primary tabs naming the two agentic layers |
| 5 | `20260710-deprecation-strips-and-doctor-cleanup` | **P3** | **v0.1.80** | `tier:` strip (**ship ≥ 2026-08-01**) + doctor partial-archive invariant |

## NO-LOCKS DOCTRINE (operator-ratified 2026-07-10 — 4 binding decisions)

Locks are the worst thing that can happen to a user; races are accepted and
*surfaced*, never prevented by blocking. (1) **Advisory presence** replaces the
blocking lease — warning/panel/doctor keep the signal, the block dies. (2)
**Pre-commit is WARN-only** — detection kept, ALLOW always. (3) **Millisecond
micro-locks stay** (registry-JSON/clone serialization = file integrity, invisible).
(4) **READ mode survives strictly self-scoped** — foreign bind can never change your
mode. After v0.1.76, NO path in dadaia-workspace can block an agent or operator
because of another session.

---

## Release definitions (2026-07-10)

### v0.1.76 — Lock liberation (advisory presence) — P0

**Scope (entry #1, full doctrine):**
- FR1 — gate: MUTATING writes upsert a presence record (never fails, never blocks);
  concurrent live presence ⇒ ALLOW + one-line advisory naming the other session.
  `LockHeldError` block path deleted (`gate_policy.py:294-316`).
- FR2 — delete blocking machinery: `acquire()` six-rung tree, O_EXCL sentinel CAS,
  `adopt_if_own_lineage`, by-session index, incumbent-pointer authority, `lock steal`
  verb. Replace with `.dadaia/states/presence/<ctx>/<session>.json` (harness-native
  id, runtime, long-lived pid, heartbeat; PostToolUse renews; TTL expiry; doctor GC).
- FR3 — pre-commit WARN-only (`chokepoints/service.py:161-282` BLOCK rung deleted);
  pre-push security gate + CI preflight untouched.
- FR4 — mode strictly self-scoped: env → own session record → IMPLEMENTATION; the
  context-incumbent fallback deleted (kills audit P1-1).
- FR5 — PI L1 presence parity: stable unique session id + long-lived pid on both
  hooks (fixes P1-4 + the anon-session facet).
- FR6 — micro-locks stay; `PLATFORM.has_fcntl` seam replaces the 3 in-body
  `sys.platform` checks (absorbed platform-seam entry).
- FR7 — repoint lease-reading surfaces (panel, doctor, `context show`, lock-events
  log) to presence.
**Acceptance:** executed-path probes on all 3 L1 harnesses: bind → write → rebind →
write → commit NEVER blocks; concurrent two-session write ALLOWS both + warns once;
READ self-scope holds; no `anon-session` presence; frozen no-steal descendant rows
retired via explicit QA-gate-adjudicated re-baseline (new invariants: presence upsert
never raises, pre-commit always allows). Dispositions: CRITICAL bug resolved-by-removal
with evidence; every audit finding mapped (see entry); audit archives with the release.
**Size:** L (deletion-heavy: ~lease.py 1,056 lines shrink drastically; gate/chokepoint/
hooks/panel/doctor edits; large frozen-suite re-baseline). **Risk:** test blast radius —
mitigated by the v0.1.75 rearchitected suite + explicit successor-baseline law.

### v0.1.77 — Central bind-resolution seam — P0

**Scope (entry #2, grill-corrected content carried):** ONE canonical resolution path
(`cli/_specs_resolution.py#resolve_specs_dir_for_cli` generalized) consumed by EVERY
resolver-driven verb; fold in `context show`'s private incumbent-pointer algorithm
(context.py:202-260 — NOTE: v0.1.76 deletes incumbent-pointer authority, so `show`
re-keys to presence/bound-session state — sequencing dependency, 76 first); retire the
15 hardcoded `--context "dadaia-workspace"` Typer defaults in lifecycle verbs
(unset-resolves-bound; user-visible CLI change, SPEC declares it); canonical order:
explicit → env → own session record → ancestry marker (self-scoped, consistent with
v0.1.76 FR4).
**Acceptance:** dynamic Typer-walk contract test (~25-30 resolver-driven subcommands,
per-verb probe — a static list cannot catch a future verb) + import-boundary lint
(nothing outside the seam imports resolution internals); after bare `context bind
<ctx>` every verb targets `<ctx>`; removing the seam from any verb fails the test.
**Size:** M. **Risk:** consumer-workspace behavior change on lifecycle `--context`
defaults — release notes + preflight message must say what changed.

### v0.1.78 — Lifecycle correctness & diagnosability — P1

**Scope (entry #3; all 5 intents CONFIRMED at HEAD, researched sizing S+M+M+M+M = L):**
- T-A (S): explicit step kind — thread `is_review=False` for `implement`/`close`
  (model exists: `PipelineStep.is_review`, pipeline.py:102); flip
  `test_lifecycle_command_skeletons.py:49` which asserts the bug as contract.
- T-B (M): full-pipeline atomic terminal state — `save(replace(run,
  status=COMPLETED))` before return (pipeline.py:234-304, mirroring :418-419) + wire
  `handoff_resolver` for per-step payloads in `run()`.
- T-C (M): ONE cleanup contract — hygiene clean delegates to (or aliases)
  RetentionSweep so remediation can reclaim what doctor flags; the 7 preflight block
  sites gain exact `operator_command` (test matrix asserts non-null for every reason).
- T-D (M): worker-noncompliance diagnostic — persist one redacted run-scoped record
  (runtime, model, requested/actual reasoning, exit, parser class, output tail,
  session ref) referenced from `BlockedState.detail` (pi_runtime.py:202-249 +
  agent_runner.py:200-215); wire `reasoning_effort` → PI `--thinking` and verify
  requested==actual.
- T-E (M): write-scope — `_extract_globs` rejects absolute/`..`/`~`/`$` tokens;
  `implement-review` gains `write_scope_from_tasks` + `--write-scope` parity.
**Acceptance:** per-bug executed-path tests (each of the 4 HIGH bugs resolved with
`--resolution-evidence`); no test ratifies old broken behavior.
**Size:** L (5 bounded tasks, 7 modules). **Risk:** low — all point fixes with
research-confirmed anchors.

### v0.1.79 — Panel agentic-layers reorg — P2

**Scope (entry #4, ratified, unchanged):** 7→6 primary tabs — Projects | 1º Agentic
Layer (Sub-agents control plane + merged Sessions dashboard) | 2º Agentic Layer |
Reports | Academy | Servers; CSP inline-script sha256 recompute
(`_CSP_SCRIPT_HASH_*`); `/api/sessions` + agent-policy + workflow-catalog API surfaces
UNCHANGED; DOM-contract tests single-source the tab list (v0.1.75 fixture
`PANEL_PRIMARY_TABS` makes this a one-list change); Playwright specs on the hermetic
harness (port 5065). NOTE: panel's lock/session surfaces will already be
presence-based (v0.1.76 FR7) — the Sessions dashboard merge must not resurrect lease
labels.
**Acceptance:** exactly 6 tabs in order; no `tab-sessions` remnants; CSP hashes equal
served scripts; v0.1.59 grep gates pass. **Size:** M. **Risk:** low.

### v0.1.80 — Deprecation strips & doctor cleanup — P3

**Scope (entry #5):** strip `tier:` fallback (reader.py:173) + `_ALLOWED_FIELDS` key +
`MissingTierError` alias + re-export; flip AC-6 test to unknown-key truth. Add
specs-doctor WARNING invariant for artifact-empty `_archive/releases/<id>/` dirs
(SPEC-DOC-027 allowlist honored, segmented layouts tolerated, wip-abandoned relocation
suggested).
**Constraint: ship on/after 2026-08-01** (consumer re-projection window).
**Acceptance:** legacy `tier:` gets the standard unknown-field warning, band defaults
to 3; invariant fires on the v0.1.41-class fixture, never on allowlisted/segmented
trees. **Size:** S. **Risk:** none.

---

Per `release-governance`: each release still runs its mandatory grill before SPEC —
these definitions fix scope, sequence, and acceptance skeletons, not the SPEC texts.
Open work outranks backlog if new bugs land. Ledger at definition time: **5 open bugs**
(absorbed into v0.1.76 + v0.1.78), **1 open audit** (dispositioned by v0.1.76).

## Triage record (2026-07-10 consolidation — retained)

- **Eliminated (stale):** `test-suite-remediation-waves` — consumed by v0.1.75.
- **Merged by feature:** platform-seam → P0 lock entry; preflight-reasons +
  implement-review-parity + traversal-hardening → P1 lifecycle entry; dispatch-band
  strip + doctor invariant → P3 cleanup entry.
- **Kept separate:** the two P0s (resolves-which-context ≠ holds-the-lease... now
  ≠ *signals-presence*); lock release ships FIRST (77 re-keys `context show` off the
  incumbent pointer that 76 deletes).
- Superseded originals in `_archive/` with pointers; bugs stay OPEN in `bugs.jsonl`
  until disposing releases resolve them with evidence.

## Archive

`_archive/` holds consumed/superseded/rejected entries; each carries its terminal
pointer in frontmatter.
