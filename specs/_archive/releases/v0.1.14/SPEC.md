# SPEC: v0.1.14 — Deterministic Lifecycle Kernel

**Status:** Aprovado
**Release ID:** v0.1.14
**Owner:** product-engineer
**Created:** 2026-06-12
**Pick contract:** `specs/backlog/deterministic-lifecycle-kernel-v0114.md` (ADR-G1..G7, G6 as amended 2026-06-12)
**Grill:** satisfied — operator sessions `82c8408f` (2026-06-11) + governance grill `fc45dd8c` (2026-06-12); refinement report `.dadaia/reports/dadaia-workspace/project-manager/2026-06-12T023635Z-refine-specs.html`

---

## Objective

The historic lock freezes were architecture bugs, not an argument against
determinism. This release re-architects the lifecycle kernel around ONE
concurrency invariant, enforced without false blocks: per Spec Context, ADDITIVE
work (research / backlog / bugs / audits) is N-parallel; release-definition and
implementation+review are strictly 1-at-a-time. Around that invariant the
lifecycle gains named, narrow determinisms — and enforcement moves to
**chokepoints** (git pre-commit / pre-push) instead of unbounded Bash
interception.

Five workstreams: (W1) chokepoint enforcement closing the Bash hole at commit
and push; (W2) strict bind-driven context injection — `bind` becomes the sole
trigger for context-memory injection; (W3) a narrow venv-determinism guard for
`dadaia`/`pip`/`python -m dadaia_workspace` Bash invocations; (W4) hook
consolidation + performance (one interpreter spawn per write, session-indexed
heartbeat renewal, centralized tunables, latency telemetry); (W5) law updates
keeping constitution, rules, and enforcement matrix coherent in the same
release.

**Binding requirement (ADR-G1): zero false blocks.** Any mechanism shipped here
must never block the legitimate lease holder, across relaunch/incumbent
scenarios — the v0.1.9–v0.1.11 lease regression history is the test bed.

## Operator Input — grill decisions (binding ADRs)

| ADR | Decision |
|---|---|
| G1 | Law evolves: one well-architected concurrency invariant (N ADDITIVE / 1 MUTATING per context), zero-false-block requirement; determinism is wanted where the lifecycle needs it |
| G2 | Bash hole closed at **chokepoints**, not by shell parsing: git pre-commit lease check (a commit into a Spec Context repo from a session not holding the lease is blocked) + advisory PostToolUse working-tree reconciler (flags out-of-lease dirty MUTATING paths, never blocks) |
| G3 | OpenCode deferred: posture canonized "advisory + chokepoint-protected"; focus Claude Code + Codex; plugin shim is a later candidate |
| G4 | Venv determinism: narrow fixed-pattern Bash PreToolUse check on `dadaia` / `pip` / `python -m dadaia_workspace` not rooted in `.dadaia/.venv/bin/` → block with corrected command in message; doctor venv-health check. pytest/ruff/mypy NOT included |
| G6 (AMENDED 2026-06-12) | FORK-1 reopened at the push boundary: the pre-push hook verifies a **`security-reviewer` APPROVE** handoff verdict for the current push-cycle (rc-N = one push); commits stay review-unblocked (lease-only) — the TDD inner loop keeps zero friction. The alpha-N / trio-at-rc-push model is **abolished** (governance grill ADR-2/ADR-9, `specs/backlog/sdd-governance-v2-agents-lifecycle.md` §2). qa-per-task-group-commit and code-review-at-PR remain PM discipline in this release; v0.1.15 codifies the full gate ladder |
| G5 | **Strict bind-driven context injection**: unbound session gets generic preflight + alive-context list only; `bind` invalidates the session injection sentinel and is the SOLE trigger for context-memory injection; first-ALIVE fallback deleted from injection resolution; `workspace-protocol §2` rewritten (bind stays non-blocking for ADDITIVE work) |
| G7 | One release — v0.1.14 — after v0.1.13 ships; hook perf consolidation rides along (same files); fast-tier/efficiency item stays a separate P2 candidate |

(Table ordered as in the pick contract; G6 reproduced in its amended form only —
the original trio wording is void.)

## Bug Inventory (pick + fold)

Open-bug census at definition time: 9 Open. Verified against current code —
`gate-cross-context-lock-contamination`, `gate-fpath-not-canonicalized-before-classifier`,
and `doctor-stale-lease-misdiagnosed-as-forgery` (named in the dispatch briefing)
are already **Closed** (fixed v0.1.10–v0.1.13); not re-picked.

### Picked (every picked bug is solved in this release)

| Bug | Sev | FR | Disposition |
|---|---|---|---|
| `ctx-inject-ignores-session-bind-first-alive-proxy` | HIGH | FR-W2 | Fixed — bind-driven injection replaces first-ALIVE proxy (code-verified still open: `hooks/ctx_inject.py::_resolve_context` resolves env → first-ALIVE; sentinel never invalidated by bind) |
| `context-release-leaves-lease-heartbeat-renewing` | HIGH | FR-W4-03 | Fixed — `context release` drops the session's held lease(s); heartbeat never resurrects a released session's lease (code-verified: `cli/commands/context.py::release_cmd` only unlinks the session record; `lease.release()` exists but is never called) |
| `sdd-gate-apply-patch-multi-file-first-header-only` | MED | FR-W4-04 | Fixed — all `apply_patch` file headers classified; most-restrictive verdict wins (code-verified: `hooks/_common.py::target_path` returns first header) |
| `codex-exec-hooks-do-not-fire-headless` | HIGH | FR-W1 + FR-W5 | Resolved per the bug's own "Expected" option (b) + chokepoints: the per-harness enforcement matrix stops claiming hook determinism on headless `codex exec`; W1 chokepoints (pre-commit lease, pre-push verdict) provide deterministic coverage that does NOT depend on harness hooks firing. Upstream codex-cli 0.139.0 defect referenced, not fixable here |
| `bug-guardrail-template-omits-required-session-id` | LOW | FR-W5-04 | Fixed — one-line template fix (`session_id: null`) in `public/rules/bug-registration-guardrail.md`; recurring push-blocker during implementation otherwise. v0.1.15 JSONL migration later rewrites the whole format |

### Sanitized / not picked (bug status canon stays {Open, Closed})

| Bug | Action | Reason |
|---|---|---|
| `agents-md-instructs-html-report-validation-unsupported` | Closed (duplicate) | Same defect as `reports-validate-rejects-html-despite-agents-md-contract`; surviving tracker noted in both files |
| `reports-validate-rejects-html-despite-agents-md-contract` | Open, not picked | Doc/CLI-UX drift, outside kernel scope |
| `context-dead-nonwritable-guard-rejects-standard-git-objects` | Open, not picked | `dead()` repo-removal guard, outside kernel scope |
| `memory-heading-allowlist-not-consumer-extensible` | Open, not picked | specs-doctor lint extensibility; natural fit for v0.1.15 (doctor invariants reworked there) |

### Backlog re-status (at CLOSURE)

- `lease-shell-write-coverage-gap.md` → SUPERSEDED — chokepoint architecture (this release).
- `harness-agentic-entities-and-determinism-parity.md` → narrowed note (OpenCode deferred per ADR-G3; enforcement-parity statement partially delivered by W5).
- `deterministic-lifecycle-kernel-v0114.md` → DELIVERED — v0.1.14.

## Functional Requirements

### FR-W1 — Chokepoint enforcement (ADR-G2 + G6 as amended)

- **FR-W1-01 — pre-commit lease gate.** A `git commit` into a Spec Context repo
  from a session that does not hold the context's MUTATING lease is blocked with
  an actionable message (who holds it, how to proceed). The holder's commits
  flow. Commits while NO lease exists flow (ADDITIVE work commits freely —
  zero-false-block; the invariant binds only when a live foreign lease exists).
  **Holder-identity probe order (ratified DP-4):** (1) no lease or stale-dead
  lease ⇒ allow; (2) `DADAIA_SESSION_ID` equals the holder sid ⇒ allow; (3) the
  holder's recorded pid is an ancestor of the invoking process, via a NEW
  `ProcessAncestry` protocol port with three adapters — Linux `/proc` walk,
  macOS `ps -o ppid=` through ProcessRunner, Windows **read-only** Toolhelp32
  snapshot; NEVER `os.kill` (destructive on Windows); adapter selected in the
  composition root by the platform seam, respecting `has_os_kill_liveness` ⇒
  allow; (4) ancestry unavailable or indeterminate ⇒ **ALLOW with a logged
  WARN** — zero-false-block dominates; the chokepoint degrades to advisory on
  that platform (documented honestly in constitution §8 — see FR-W5-01). Block
  ONLY on a live foreign lease with a positive non-match at steps 2–3.
  Fail-closed runner resolution reuses the `pre-push-ci-gate.sh` pattern;
  installed via the `dadaia ci install-hook` family.
- **FR-W1-02 — pre-push security verdict gate.** A `git push` is blocked unless
  a `security-reviewer` handoff JSON with `"verdict": "APPROVED"` covers the
  push-cycle. **Predicate (ratified DP-5):** keyed on the pre-push **stdin ref
  lines** (`<local-ref> <local-sha> <remote-ref> <remote-sha>`), never
  `git rev-parse HEAD` — for each non-zero `<local-sha>` being pushed, an
  APPROVED security-reviewer handoff whose `metrics.commit_sha` equals that sha
  must exist. `metrics.commit_sha` is the single canonical field — no `scope`
  fallback, no schema rev (handoff-v1.1 `metrics` accepts additive keys).
  Zero-sha refs (branch deletions) and tag-only pushes pass without a verdict.
  Stale approvals (older sha) do not pass. Commits are never review-blocked.
  Runs in addition to (not replacing) the existing CI preflight in the same
  pre-push hook; `pre-push-ci-gate.sh` forwards its stdin to
  `dadaia ci push-gate-check`.
- **FR-W1-03 — advisory working-tree reconciler.** A PostToolUse pass flags
  out-of-lease dirty MUTATING paths in the bound context's repo (report line /
  log event); it NEVER blocks and never exits non-zero.

**Acceptance (seeds 1–2):**
- Two-actor e2e: session B (no lease) commits into a leased context → blocked
  with actionable message; session A (holder) commits → flows; no false block
  across relaunch/incumbent scenarios (regression suite over the v0.1.9–v0.1.11
  lease-bug history).
- Explicit G6 case: lease holder commits with ZERO security handoffs on disk →
  commit flows; same state → push blocked. Proves the pre-commit gate consults
  the lease ONLY, never handoff verdicts — commits are never review-blocked.
- Push without a security-reviewer APPROVE matching a pushed stdin ref sha →
  blocked; with it → flows; stale-sha APPROVE → blocked; branch-deletion and
  tag-only pushes flow with no verdict.
- Harness independence (regression criterion for
  `codex-exec-hooks-do-not-fire-headless`): the chokepoint e2e runs with NO
  harness hook environment — no PreToolUse/PostToolUse payloads, no DADAIA hook
  env beyond `DADAIA_SESSION_ID`/`DADAIA_BIN`.

**Acceptance (FR-W1-03 reconciler — "NEVER blocks" is a zero-false-block
safety invariant under ADR-G1, contract-tested):**
- Dirty MUTATING path in the bound context's repo + no held lease →
  `RECONCILER_FLAG` event appended to `.dadaia/logs/lock-events.jsonl`.
- Held lease OR clean tree OR ADDITIVE-only dirt → no event.
- Hook exit code is 0 in ALL reconciler branches, including `git status`
  failure (never-blocks / fail-open contract test).
- Rate-limit honored: a second invocation inside the throttle window emits
  nothing.

### FR-W2 — Bind-driven context injection (ADR-G5)

- **FR-W2-01.** `ctx_inject` context resolution becomes: `DADAIA_CONTEXT` env →
  self-keyed session record (bound context) → **newest bind-epoch marker newer
  than this session's sentinel** (the epoch store carries the context slug and
  is the harness-real discovery path: the bind CLI mints its own sid, so
  `read_session(harness_sid)` is structurally None in the default flow) →
  **generic preflight only** (dispatcher preflight + list of ALIVE contexts; NO
  context memory). The first-ALIVE fallback is deleted from injection. (It
  remains valid only inside the SDD gate's lease-context resolution — a
  different job.)
- **FR-W2-02 — bind-epoch mechanism (ratified DP-2).** `dadaia context bind`
  invalidates the session injection sentinel and is the SOLE trigger for
  context-memory injection. Mechanism: `bind` writes a standalone marker file
  `.dadaia/states/bind_epoch/<ctx>` — **NOT** a field in the incumbent `.ptr`
  (the `.ptr` is lease-incumbency, rewritten by `acquire` on first MUTATING
  write; overloading it would couple injection to the lease kernel and risk
  spurious re-injection/clobber). The marker doubles as the injection hook's
  context-discovery source. The hook re-injects when (a) no sentinel for this
  sid exists, or (b) a bind-epoch marker is newer than the sentinel mtime — it
  scans the small marker dir, picks the newest qualifying marker, injects that
  context, and stamps the sentinel content with the injected slug (so a
  re-bind to a different context also re-injects). A bind-epoch marker
  qualifies only by being newer than an EXISTING sentinel; when no sentinel
  exists, the chain yields generic preflight (which stamps the sentinel) —
  pre-existing markers never bind a fresh session. Accepted semantic: bind
  binds the CONTEXT — a bind can re-inject into a concurrent parallel session
  on its next prompt, consistent with the NF-2 incumbent-mode canon.
- **FR-W2-03.** `workspace-protocol §2` rewritten for the new model: bind
  drives injection; bind remains non-blocking for ADDITIVE work (never halt the
  flow to demand a bind).
- Closes `ctx-inject-ignores-session-bind-first-alive-proxy`.

**Acceptance (seed 3):** fresh unbound session → injection contains NO context
memory; after `dadaia context bind X` → next prompt injects X's memory; re-bind
Y → Y injected. The e2e crosses the REAL bind-CLI → hook process boundary
(distinct sids), exercising the CLI-side epoch write end-to-end.

### FR-W3 — Venv guard (ADR-G4)

- **FR-W3-01.** New narrow Bash PreToolUse hook: fixed-pattern check on Bash
  commands invoking `dadaia`, `pip`, or `python -m dadaia_workspace` not rooted
  in `.dadaia/.venv/bin/` → block, message contains the corrected command.
  pytest/ruff/mypy are explicitly NOT covered. No general shell parsing — fixed
  leading-token patterns only.
- **FR-W3-02.** Doctor venv-health check (venv exists, `dadaia` entrypoint
  executable, interpreter matches workspace venv).

**Acceptance (seed 4):** `pip install foo` / bare `dadaia` via Bash → blocked
with corrected command; `.dadaia/.venv/bin/dadaia …` → flows. FR-W3-02
negative tests: missing `.dadaia/.venv` → doctor emits the venv-health
finding; venv present but `bin/dadaia` absent or non-executable → finding;
healthy venv tree → ok. All fixtures are synthetic trees (mkdir/touch/chmod)
— NEVER a real venv build (quality-assurance memory law).

### FR-W4 — Hook consolidation + perf + lease correctness

- **FR-W4-01.** Merge `sdd_gate` + `root_whitelist` (+ the W3 venv guard) into
  ONE PreToolUse entrypoint: one interpreter spawn per tool call; both policies
  preserved byte-for-byte in behavior (contract tests).
- **FR-W4-02.** PostToolUse heartbeat renewal indexed by session id — no full
  lock-dir scan when the session holds nothing. The by-session index entry
  (`ctx_locks/by-session/<sid>.json`) is written/removed **inside the SAME
  O_EXCL sentinel CAS as the lock-record write** in `acquire`/`steal`/`release`
  — one atomic unit per transition; a lost index entry must be structurally
  impossible (a silent miss starves renewal and reopens the lease-theft
  class). Fallback: full scan whenever the by-session DIR is absent
  (migration window). Contract test asserts record-write and index-write
  cannot diverge (crash-injection via the existing `_before_write` seam).
- **FR-W4-03.** `dadaia context release` releases the lease(s) the session
  holds (`lease.release()` per lock record naming the sid) in addition to
  removing the session record. There is **NO hook-side renewal guard**
  (ratified DP-3): lease renewal keeps running outside any session-record
  check — the deliberate v0.1.10 FR-R2-01 invariant (unbound harness sessions
  never have a session record; an absence-based guard would starve every
  unbound holder and re-open the v0.1.9–v0.1.11 lease-theft class). The
  primary fix alone is sufficient: `lease.renew_heartbeat` never re-creates
  an absent or foreign-sid record, so once `release` deletes the record,
  resurrection is structurally impossible. Release predicate per flow
  (CLI-sid/harness-sid split): (a) **eval flow** (`--print-env`,
  `DADAIA_SESSION_ID` exported) — release every lock record naming the env
  sid; hooks key on the same sid, so this is exact. (b) **default flow**
  (CLI-minted sid ≠ harness sid) — `release` resolves the bound context from
  the CLI session record and releases that context's lease only when its
  holder pid is dead OR matches the caller's process ancestry (via the FR-W1
  `ProcessAncestry` port); never release a live foreign holder's lease by
  context name alone. The closed bug
  (`context-release-leaves-lease-heartbeat-renewing`) covers both flows under
  these predicates; after a successful `release`, `context dead <ctx>` from
  the same session proceeds.
- **FR-W4-04.** `apply_patch` multi-file classification: every
  `*** Add/Update/Delete File:` header is classified; the most restrictive
  verdict wins (one FROZEN/PROTECTED/blocked-MUTATING file blocks the whole
  patch). Closes `sdd-gate-apply-patch-multi-file-first-header-only`.
- **FR-W4-05.** Centralize kernel tunables (lease TTL, GC TTLs, retries,
  sentinel TTL) in `core/kernel_tunables.py` (ratified DP-1: pure constants,
  zero I/O — fits core's law; hooks/features/cli all hold a legal core edge);
  all hooks and lease code import from it. `lease.LEASE_TTL_SECONDS` stays as
  a re-export for one release (deprecation note).
- **FR-W4-06.** Basic hook-latency telemetry: per-event duration appended to
  `.dadaia/logs/hook-latency.jsonl`; no new external dependency. Acceptance:
  (a) invoking the entrypoint appends one JSONL record
  `{ts, hook, event, duration_ms>=0}`; (b) unwritable/absent logs dir → hook
  verdict and exit code unchanged (fail-open contract test). Because the
  PreToolUse matcher gains Bash (W3), Bash-event latency is captured as its
  own percentile in the telemetry evidence — the 0→1 spawn cost on Bash
  calls is measured deliberately, not discovered.

**Acceptance (seed 5):** one interpreter spawn per file-write PreToolUse,
proven two ways: (a) static — a single registered PreToolUse command per
runtime config; (b) dynamic — a subprocess-free contract test on `pre_gate`
(monkeypatch `subprocess.Popen/run` + `os.exec*` to raise; drive `main()`
with fixture stdin for Edit/Write/MultiEdit/apply_patch payloads); plus the
hook-latency JSONL from the live instance as measured CLOSURE evidence (one
line per write event = one spawn, with `duration_ms`). PostToolUse does not
scan the lock dir when the session holds nothing (FS-op-counting fake). Both
folded bugs' repro scenarios pass as regression tests. Lease regression canon
stays green: the existing no-steal + activity-exemption suites
(`tests/unit/features/spec_context/test_lease_activity_exemption.py`,
`tests/e2e/test_two_actor_lease.py` scenarios i–ii) pass unchanged; new
parametrized cases: holder busy past TTL with live pid → never reclaimed;
released session (record gone via `context release`) → heartbeat does NOT
renew and the lease is reclaimable; unbound holder with no session record →
renewal continues (the v0.1.10 invariant, preserved by DP-3).

### FR-W5 — Law updates (ADR-G3 + G6 as amended)

- **FR-W5-01.** Constitution §8: chokepoint envelope added to the enforcement
  scope (honesty clause updated — Bash writes remain outside the file-tool
  envelope but commits/pushes are deterministically gated); OpenCode posture
  canonized "advisory + chokepoint-protected" (ADR-G3); per-harness enforcement
  matrix (Claude / Codex interactive / Codex headless / OpenCode) — headless
  Codex documented honestly per `codex-exec-hooks-do-not-fire-headless`. The
  §8 matrix also documents the pre-commit chokepoint's **advisory
  degradation** per platform: when the FR-W1-01 ancestry probe is unavailable
  or indeterminate the gate allows with a logged WARN (zero-false-block
  dominates), mirroring the 3-tier resilience contract.
- **FR-W5-02.** Constitution §11: push-boundary verdict enforcement — the
  pre-push security gate becomes a **mechanical gate** (not a checkpoint);
  wording aligned with G6-as-amended (no alpha-N/trio language introduced or
  retained for the push boundary); full gate-ladder codification stays v0.1.15.
- **FR-W5-03.** `workspace-protocol` rule §2 rewritten (with FR-W2-03); §1
  updated for the merged PreToolUse entrypoint and chokepoints.
- **FR-W5-04.** `bug-registration-guardrail` rule template gains
  `session_id: null` (closes `bug-guardrail-template-omits-required-session-id`).
  Regression criterion: a contract test asserts the template block in
  `public/rules/bug-registration-guardrail.md` contains `session_id:`,
  asserted post-stage so the projection carries it too.
- **FR-W5-05.** Re-status superseded/narrowed backlog entries (see Backlog
  re-status table). All law docs updated in this same release — no doc-drift
  window.

**Acceptance (seed 6):** `dadaia specs doctor` + `dadaia public doctor` exit 0;
no law doc still describes shell-parsing enforcement, first-ALIVE injection, or
the abolished trio-at-rc-push model at the push boundary.

## Out of Scope

- OpenCode enforcement depth / plugin shim (ADR-G3 — later candidate).
- Full gate-ladder law (qa→commit, code-review→PR) — v0.1.15
  (`sdd-governance-v2-agents-lifecycle`); this release ships only the
  security→push mechanical half.
- Bugs-as-JSONL, specs taxonomy `_archive` classes, roster changes — v0.1.15.
- Venv enforcement for pytest/ruff/mypy (ADR-G4 exclusion).
- Fixing codex-cli headless hook execution (upstream defect).
- Fast-tier/model-efficiency work (separate P2 candidate).
- The three not-picked Open bugs (table above).

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| Pre-commit lease gate false-blocks the legitimate holder (the v0.1.9–v0.1.11 failure class) | Zero-false-block acceptance is binding; holder identity resolved via the ratified DP-4 chain (env-sid match → `ProcessAncestry` ancestor probe → indeterminate ⇒ ALLOW + logged WARN); the holder's own commits arrive as Bash descendants of the harness pid carrying no env sid, so ancestry IS the harness-real allow path; two-actor e2e + relaunch/incumbent regression matrix required before Aprovado of implementation; no-lease ⇒ commit flows |
| Pre-push verdict predicate accepts a stale APPROVE, or false-blocks deletions/tag pushes | Predicate keyed on the pre-push stdin ref shas (never `rev-parse HEAD`) via `metrics.commit_sha`; zero-sha and tag-only pushes pass; tested with stale-sha, deletion, and tag fixtures |
| Hook merge changes gate behavior | Existing sdd_gate + root_whitelist contract/property tests run unchanged against the merged entrypoint (incl. NotebookEdit exclusion and fail-closed PROTECTED semantics) |
| Bind-epoch/sentinel race across harness sids (bind CLI sid ≠ harness sid) | Mechanism specified in SPEC FR-W2-02 (standalone `bind_epoch/<ctx>` marker doubling as context discovery); seed-3 e2e crosses the real bind-CLI → hook process boundary |
| By-session heartbeat index entry lost/diverged → renewal silently starves (lease-theft class) | FR-W4-02 mandates the index write inside the same O_EXCL CAS as the lock-record write; full-scan fallback when the index dir is absent; crash-injection contract test via `_before_write` |
| Git hooks bypassable (`--no-verify`) | Documented honestly as the chokepoint envelope's escape hatch (constitution §8 wording); doctor coherence remains the backstop |

Dependencies: v0.1.13 shipped (archived — satisfied); projection chain
(`dadaia public stage/install/doctor`) for hook wiring, rules, and scripts.
