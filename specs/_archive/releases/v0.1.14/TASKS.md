# TASKS: v0.1.14 — Deterministic Lifecycle Kernel

**Status:** Aprovado
**Release ID:** v0.1.14
**Owner:** product-engineer
**Created:** 2026-06-12

> Clarity review: software-engineer APPROVED 2026-06-12 (handoff 2026-06-12T043506Z).

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

Group order = commit order (W4 → W2 → W3 → W1 → W5 → projection/verification,
per PLAN). Each group is commit-able and qa-gated on its own. Write sets are
disjoint across groups EXCEPT the declared sequential overlaps: TG-2/TG-3 on
`cli/commands/context.py`; TG-2/TG-5 on `hooks/sdd_post_gate.py`; TG-1/TG-4 on
`hooks/pre_gate.py` + `infrastructure/runtime_config.py`. Overlapping groups
never run in parallel. All code paths repo-relative to `repos/dadaia-workspace/`.
TDD law: every task's tests are written first (or accompany the same commit) —
a task without its declared tests is not completable.

---

## TG-1 — W4 substrate: tunables, merged entrypoint, multi-file patch, telemetry

Write set (group): `dadaia_workspace/hooks/pre_gate.py` (NEW),
`dadaia_workspace/hooks/_common.py`, `dadaia_workspace/hooks/sdd_gate.py`,
`dadaia_workspace/hooks/root_whitelist.py`,
`dadaia_workspace/core/kernel_tunables.py` (NEW),
`dadaia_workspace/infrastructure/runtime_config.py`, tests.

### [x] T-014-01 — Kernel tunables single home
- **Owner:** software-engineer
- **FR:** FR-W4-05 (DP-1)
- **Files:** `dadaia_workspace/core/kernel_tunables.py` (NEW),
  `dadaia_workspace/features/spec_context/{lease,gate_policy,doctor}.py`,
  `dadaia_workspace/hooks/ctx_inject.py` (constant import only), tests
- **Precondition:** none (group opener)
- **Tests (TDD):** single-home import/AST check scoped to the kernel modules
  (assert they import names from `kernel_tunables`; NOT a digit grep);
  behavioral test: monkeypatch a constant, assert lease TTL logic observes it;
  re-export test: `lease.LEASE_TTL_SECONDS` still importable (deprecation note).
- **Done:** all kernel tunables (lease TTL, sentinel GC TTL, session-record GC
  TTLs, CAS retries, reconciler throttle TTL) live in `core/kernel_tunables.py`
  (pure constants, zero I/O); import-linter contract added (hooks may import
  tunables; no reverse dependency); focused pytest green.

### [x] T-014-02 — apply_patch multi-file classification (bug fold)
- **Owner:** software-engineer
- **FR:** FR-W4-04 — closes `sdd-gate-apply-patch-multi-file-first-header-only`
- **Files:** `dadaia_workspace/hooks/_common.py` (`target_paths() -> list[str]`),
  callers in `hooks/sdd_gate.py` / `hooks/root_whitelist.py`, tests
- **Precondition:** none (disjoint from T-014-01)
- **Tests (TDD):** REGRESSION — the bug's repro fixture (multi-file
  `*** Add/Update/Delete File:` patch where a later header is FROZEN/PROTECTED)
  written FIRST and failing; most-restrictive-verdict matrix tests.
- **Done:** every apply_patch file header is classified; most restrictive
  verdict wins (one blocked file blocks the whole patch); bug repro passes.

### [x] T-014-03 — `pre_gate` merged PreToolUse entrypoint
- **Owner:** software-engineer
- **FR:** FR-W4-01
- **Files:** `dadaia_workspace/hooks/pre_gate.py` (NEW),
  `dadaia_workspace/hooks/sdd_gate.py` + `hooks/root_whitelist.py` (become thin
  policy modules; `main()` kept one release), tests
- **Precondition:** T-014-01, T-014-02 done (tunables + `target_paths` landed)
- **Tests (TDD):** existing sdd_gate + root_whitelist contract/property suites
  run UNCHANGED against `pre_gate` (parity proof, incl. NotebookEdit exclusion
  and fail-closed PROTECTED semantics); subprocess-free single-spawn contract
  test (monkeypatch `subprocess.Popen/run` + `os.exec*` to raise; drive
  `pre_gate.main()` with fixture stdin for Edit/Write/MultiEdit/apply_patch).
- **Done:** one entrypoint reads stdin once; order root-whitelist → venv-guard
  slot (wired in TG-4) → SDD gate; first block wins; parity suites green.

### [x] T-014-04 — Hook-latency telemetry
- **Owner:** software-engineer
- **FR:** FR-W4-06
- **Files:** `dadaia_workspace/hooks/pre_gate.py` (timer wrapper), tests
- **Precondition:** T-014-03 done
- **Tests (TDD):** entrypoint invocation appends one
  `{ts, hook, event, duration_ms>=0}` record to
  `.dadaia/logs/hook-latency.jsonl`; unwritable/absent logs dir → verdict and
  exit code unchanged (fail-open contract test).
- **Done:** best-effort JSONL telemetry live; no new dependency; Bash-event
  latency capturable as its own percentile (consumed as CLOSURE evidence).

### [x] T-014-05 — Runtime wiring switch to `pre_gate`
- **Owner:** software-engineer
- **FR:** FR-W4-01 (wiring) + seed-5 static proof
- **Files:** `dadaia_workspace/infrastructure/runtime_config.py` (Claude
  `settings.json` + Codex `hooks.json` templates),
  `dadaia_workspace/features/spec_context/gate_policy.py` (docstring/`__all__`),
  tests
- **Precondition:** T-014-03 done
- **Tests (TDD):** static seed-5 test — a SINGLE registered PreToolUse command
  per runtime config; projection-template tests updated.
- **Done:** both runtime templates point PreToolUse at
  `dadaia_workspace.hooks.pre_gate`; old dual wiring gone from templates.

---

## TG-2 — W4 lease correctness: ProcessAncestry, same-CAS index, release-drops-lease

Write set (group): `dadaia_workspace/cli/commands/context.py`,
`dadaia_workspace/features/spec_context/lease.py`,
`dadaia_workspace/hooks/sdd_post_gate.py`, `dadaia_workspace/core/` (port),
`dadaia_workspace/infrastructure/` (adapters), tests. Sequential after TG-1;
shares `context.py` with TG-3 and `sdd_post_gate.py` with TG-5 (never parallel).

### [x] T-014-06 — `ProcessAncestry` port + three adapters
- **Owner:** software-engineer
- **FR:** FR-W1-01 step 3 (DP-4) — created here, reused read-only by TG-5
- **Files:** `dadaia_workspace/core/` (protocol port),
  `dadaia_workspace/infrastructure/` (Linux `/proc` walk, macOS `ps -o ppid=`
  via ProcessRunner, Windows read-only Toolhelp32), composition root
  (`container.py` platform-seam selection), tests
- **Precondition:** none within group
- **Tests (TDD):** per-adapter units (synthetic `/proc` tree fixture;
  ProcessRunner fake for macOS; mocked Toolhelp32 for Windows); contract test:
  NEVER calls `os.kill`; indeterminate ancestry → explicit `None`/UNKNOWN result
  (the ALLOW+WARN decision lives in callers); selection respects
  `has_os_kill_liveness` platform seam.
- **Done:** port + 3 adapters wired in the composition root; mypy --strict
  clean; no destructive probe anywhere.

### [x] T-014-07 — By-session heartbeat index, same-CAS atomic
- **Owner:** software-engineer
- **FR:** FR-W4-02
- **Files:** `dadaia_workspace/features/spec_context/lease.py`
  (`acquire`/`steal`/`release` write/remove
  `ctx_locks/by-session/<sid>.json` inside the SAME O_EXCL sentinel CAS),
  `dadaia_workspace/hooks/sdd_post_gate.py::_iter_lease_contexts`, tests
- **Precondition:** T-014-01 done (tunables imports)
- **Tests (TDD):** crash-injection contract test via the existing
  `_before_write` seam — record-write and index-write cannot diverge;
  FS-op-counting fake — PostToolUse does NOT scan the lock dir when the session
  holds nothing; full-scan fallback when the by-session DIR is absent
  (migration window); lease regression canon green
  (`test_lease_activity_exemption.py`, `test_two_actor_lease.py` i–ii
  unchanged).
- **Done:** renewal is index-driven, structurally lossless; zero behavior
  change for holders.

### [x] T-014-08 — `context release` drops held lease(s) (bug fold)
- **Owner:** software-engineer
- **FR:** FR-W4-03 (DP-3: NO hook-side renewal guard) — closes
  `context-release-leaves-lease-heartbeat-renewing`
- **Files:** `dadaia_workspace/cli/commands/context.py::release_cmd`,
  `dadaia_workspace/features/spec_context/lease.py` (release predicate
  helpers only), tests
- **Precondition:** T-014-06 done (ancestry probe for the default flow),
  T-014-07 done (release also clears the by-session index)
- **Tests (TDD):** REGRESSION — bug repro for BOTH flows written first:
  (a) eval flow (env sid) — release drops every lock record naming the sid;
  (b) default flow (CLI sid ≠ harness sid) — bound-context resolution +
  dead-pid-or-caller-ancestry; a live foreign holder's lease is NEVER released
  by context name alone; after release, heartbeat does NOT renew and the lease
  is reclaimable; unbound holder with no session record → renewal continues
  (v0.1.10 FR-R2-01 invariant, preserved); `context dead <ctx>` proceeds after
  a successful release.
- **Done:** `lease.release()` called per-flow before the session record is
  unlinked; no absence-based renewal guard introduced anywhere.

---

## TG-3 — W2 bind-driven context injection

Write set (group): `dadaia_workspace/hooks/ctx_inject.py`,
`dadaia_workspace/cli/commands/context.py` (bind fn only), tests. Sequential
after TG-2 on `cli/commands/context.py`.

### [x] T-014-09 — `bind` writes the bind-epoch marker
- **Owner:** software-engineer
- **FR:** FR-W2-02 (DP-2, CLI half)
- **Files:** `dadaia_workspace/cli/commands/context.py` (bind fn), tests
- **Precondition:** TG-2 complete (shared file)
- **Tests (TDD):** bind writes `.dadaia/states/bind_epoch/<ctx>` (standalone
  marker, NOT a `.ptr` field); re-bind refreshes mtime; marker dir created on
  demand.
- **Done:** marker written on every successful bind; `.ptr` untouched by this
  task.

### [x] T-014-10 — `ctx_inject` resolution rewrite + re-injection state machine (bug fold)
- **Owner:** software-engineer
- **FR:** FR-W2-01 + FR-W2-02 — closes
  `ctx-inject-ignores-session-bind-first-alive-proxy`
- **Files:** `dadaia_workspace/hooks/ctx_inject.py`, tests
- **Precondition:** T-014-09 done
- **Tests (TDD):** REGRESSION — bug repro first (bound session X with ALIVE Y
  listed first → X injected, never Y); state-machine units: no sentinel →
  generic preflight + sentinel stamped; marker newer than EXISTING sentinel →
  re-inject + sentinel restamped with slug; re-bind to another context →
  re-inject; repeat prompt → silent; STALE-MARKER NEGATIVE (architect MEDIUM):
  fresh session + pre-existing marker, no sentinel → generic preflight, NO
  context memory; first-ALIVE absent from the injection chain (test asserts).
- **Done:** chain = env → self-keyed session record → newest qualifying
  bind-epoch marker → generic preflight (dispatcher preflight + ALIVE list,
  no memory); first-ALIVE loop deleted from this hook only.

### [x] T-014-11 — Seed-3 injection e2e across the real process boundary
- **Owner:** software-engineer
- **FR:** FR-W2 acceptance (seed 3)
- **Files:** `tests/e2e/` (new test module; reuse
  `tests/fixtures/harness_env.run_hook_subprocess`), tests only
- **Precondition:** T-014-10 done
- **Tests (TDD):** real `dadaia context bind` (subprocess/CliRunner, distinct
  sid) + real hook subprocess: unbound → no memory + ALIVE list; bind X → X
  memory; re-bind Y → Y memory; repeat prompt → silent.
- **Done:** e2e green crossing the genuine bind-CLI → hook sid boundary.

---

## TG-4 — W3 venv guard + doctor health check

Write set (group): `dadaia_workspace/hooks/venv_guard.py` (NEW),
`dadaia_workspace/hooks/pre_gate.py` (wiring), workspace doctor module,
`dadaia_workspace/infrastructure/runtime_config.py` (matcher gains Bash),
tests. Sequential after TG-1 on `pre_gate.py` + `runtime_config.py`.

### [x] T-014-12 — Venv-guard policy + Bash matcher wiring
- **Owner:** software-engineer
- **FR:** FR-W3-01 (ADR-G4)
- **Files:** `dadaia_workspace/hooks/venv_guard.py` (NEW),
  `dadaia_workspace/hooks/pre_gate.py` (Bash branch),
  `dadaia_workspace/infrastructure/runtime_config.py` (PreToolUse matcher
  gains Bash), tests
- **Precondition:** TG-1 complete (shared files)
- **Tests (TDD):** pattern-table block/allow matrix — block: bare `dadaia`,
  `pip`/`pip3`, `python -m dadaia_workspace`, `python3 -m dadaia_workspace`;
  allow: `.dadaia/.venv/bin/…`, workspace-absolute equivalent, `$DADAIA_BIN`,
  and EXPLICITLY pytest/ruff/mypy; first-command-token only (no shell parsing);
  block message contains the corrected command.
- **Done:** narrow fixed-pattern guard live inside `pre_gate`; matcher updated
  in both runtime templates; seed-4 acceptance cases green.

### [x] T-014-13 — Doctor venv-health check
- **Owner:** software-engineer
- **FR:** FR-W3-02
- **Files:** workspace doctor module under `dadaia_workspace/features/`
  (exact module resolved at implementation; doctor surface only), tests
- **Precondition:** none within group (disjoint from T-014-12)
- **Tests (TDD):** synthetic trees ONLY (mkdir/touch/chmod — NEVER a real venv
  build, quality-assurance memory law): missing `.dadaia/.venv` → finding;
  `bin/dadaia` absent or non-executable → finding; healthy synthetic tree → ok.
- **Done:** `dadaia doctor` reports venv health; negative + positive paths
  covered.

---

## TG-5 — W1 chokepoints: pre-commit lease gate, push verdict gate, reconciler

Write set (group): `dadaia_workspace/public/scripts/pre-commit-lease-gate.sh`
(NEW), `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`,
`dadaia_workspace/cli/commands/ci.py` (+ a `features/` service module),
`dadaia_workspace/hooks/sdd_post_gate.py` (reconciler fn), tests. Reuses
TG-2's `ProcessAncestry` read-only. Sequential after TG-2 on
`sdd_post_gate.py`.

### [x] T-014-14 — Pre-commit lease gate (script + CLI) + seed-1 e2e (bug fold)
- **Owner:** software-engineer
- **FR:** FR-W1-01 (DP-4) — harness-independence regression for
  `codex-exec-hooks-do-not-fire-headless`
- **Files:** `dadaia_workspace/public/scripts/pre-commit-lease-gate.sh` (NEW),
  `dadaia_workspace/cli/commands/ci.py` (`pre-commit-check`), new `features/`
  chokepoint service module, `dadaia ci install-hook` extension, tests
- **Precondition:** T-014-06 done (`ProcessAncestry`); T-014-08 done (lease
  store correct before the gate consults it)
- **Tests (TDD):** probe-chain units (no/stale-dead lease → allow; env-sid
  match → allow; ancestry ancestor → allow; indeterminate → ALLOW + logged
  WARN; positive non-match on live foreign lease → block with holder sid, age,
  "lease frees itself" message — never "rebind/steal"); two-actor e2e (seed 1,
  `lease_rendezvous` REAL-process pattern): holder's child commits → flows,
  foreign process → blocked; relaunch (new pid, same `.ptr`) → flows;
  v0.1.9–v0.1.11 regression scenarios parametrized; REGRESSION (headless): e2e
  runs with NO harness hook env beyond `DADAIA_SESSION_ID`/`DADAIA_BIN`;
  G6 case: holder commits with ZERO security handoffs on disk → commit flows.
- **Done:** zero false blocks across the regression matrix; fail-closed runner
  resolution mirrors `pre-push-ci-gate.sh`; context derived from repo path
  (never first-ALIVE).

### [x] T-014-15 — Push-gate verdict check + pre-push extension + seed-2 e2e
- **Owner:** software-engineer
- **FR:** FR-W1-02 (DP-5)
- **Files:** `dadaia_workspace/cli/commands/ci.py` (`push-gate-check`),
  `dadaia_workspace/public/scripts/pre-push-ci-gate.sh` (forwards stdin; runs
  preflight AND push-gate-check), `dadaia ci install-hook` (installs both
  hooks, `--force` preserved), tests
- **Precondition:** T-014-14 done (shared `ci.py` + service module)
- **Tests (TDD):** stdin-ref fixtures — APPROVED@pushed-sha → pass;
  APPROVED@stale-sha → block; REJECTED/absent → block listing what was found;
  branch-deletion zero-sha → pass; tag-only → pass; predicate keyed on stdin
  ref lines (test asserts `rev-parse HEAD` is never consulted);
  `metrics.commit_sha` single canonical field (no `scope` fallback); G6 case:
  same zero-handoff state that committed freely → push blocked.
- **Done:** push deterministically gated on a security-reviewer APPROVE
  covering every pushed sha; commits never review-blocked.

### [x] T-014-16 — Advisory working-tree reconciler
- **Owner:** software-engineer
- **FR:** FR-W1-03
- **Files:** `dadaia_workspace/hooks/sdd_post_gate.py` (reconciler fn;
  documented direct `subprocess.run(["git","status","--porcelain"])`
  exemption), throttle marker `.dadaia/tmp/reconciler-last-<sid>`, tests
- **Precondition:** T-014-07 done (shared `sdd_post_gate.py`)
- **Tests (TDD — never-blocks contract):** dirty MUTATING + no lease →
  `RECONCILER_FLAG` appended to `.dadaia/logs/lock-events.jsonl`; held lease /
  clean tree / ADDITIVE-only dirt → no event; exit 0 in ALL branches including
  `git status` failure (fail-open); throttle: second invocation inside the
  window emits nothing AND spawns no git child (checked BEFORE spawning).
- **Done:** advisory-only reconciler live; throttle TTL from
  `kernel_tunables`.

---

## TG-6 — W5 law, docs, personas, backlog re-status

Write set (group): `specs/constitution.md`, `dadaia_workspace/public/rules/*`,
`dadaia_workspace/public/agents/security-reviewer.md`,
`dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/skills/*`,
`specs/backlog/*`, contract tests. Disjoint from all code groups.

### [x] T-014-17 — Constitution §8 + §11
> Operator gate: constitution diff approved 2026-06-12 (PM-surfaced).
- **Owner:** product-engineer (operator confirmation REQUIRED — PM surfaces
  the diff before the edit lands)
- **FR:** FR-W5-01 + FR-W5-02
- **Files:** `specs/constitution.md`
- **Precondition:** TG-5 complete (law describes shipped reality)
- **Tests:** seed-6 doc sweep (no shell-parsing enforcement, no first-ALIVE
  injection, no trio-at-rc-push language at the push boundary) — grep-based
  assertions in the verification task T-014-22.
- **Done:** §8 carries the chokepoint envelope, per-harness matrix (Claude /
  Codex interactive / Codex headless / OpenCode "advisory +
  chokepoint-protected"), the pre-commit advisory-degradation honesty clause,
  and the `--no-verify` escape-hatch honesty; §11 makes the pre-push security
  gate a mechanical gate; full gate ladder explicitly deferred to v0.1.15.

### [x] T-014-18 — Rules, personas, AGENTS.md, skills sweep
- **Owner:** ai-engineer
- **FR:** FR-W2-03 + FR-W5-03 + W1 sha-in-verdict convention
- **Files:** `dadaia_workspace/public/rules/workspace-protocol.md` (§1 merged
  entrypoint + chokepoints; §2 bind-driven, non-blocking for ADDITIVE; §4
  sha-in-verdict note), `public/rules/release-governance.md` (push gate =
  security APPROVE; trio-at-rc wording removed at the push boundary),
  `public/agents/security-reviewer.md` (duty: emit `metrics.commit_sha` on
  push-cycle APPROVE handoffs), `public/data/AGENTS.md` (SDD Gate section),
  `public/skills/{dadaia-workspace-manager,harness-primitives,ai-harness-codex}`
  (wording-only; headless honesty)
- **Precondition:** TG-1..TG-5 complete
- **Tests:** seed-6 grep sweep (T-014-22) covers these files post-projection.
- **Done:** no law doc describes shell-parsing enforcement, first-ALIVE
  injection, or the abolished trio model at the push boundary.

### [x] T-014-19 — Bug-guardrail template `session_id` (bug fold)
- **Owner:** ai-engineer (template line); software-engineer (contract test —
  disjoint write set)
- **FR:** FR-W5-04 — closes
  `bug-guardrail-template-omits-required-session-id`
- **Files:** `dadaia_workspace/public/rules/bug-registration-guardrail.md`,
  `tests/` (contract test)
- **Precondition:** none within group
- **Tests (TDD):** REGRESSION — contract test asserts the template block in
  `public/rules/bug-registration-guardrail.md` contains `session_id:`,
  asserted POST-STAGE so the projection carries it too.
- **Done:** template carries `session_id: null`; contract test green.

### [x] T-014-20 — Backlog re-status + bug dispositions (CLOSURE input)
- **Owner:** product-engineer (disposition sweep; ADDITIVE/backlog paths)
- **FR:** FR-W5-05 + SPEC "Backlog re-status" table
- **Files:** `specs/backlog/lease-shell-write-coverage-gap.md` (SUPERSEDED —
  chokepoint architecture),
  `specs/backlog/harness-agentic-entities-and-determinism-parity.md`
  (narrowed note, ADR-G3),
  `specs/backlog/deterministic-lifecycle-kernel-v0114.md` (DELIVERED at
  CLOSURE); the 5 picked bugs flipped to `Closed` (incl.
  `codex-exec-hooks-do-not-fire-headless` per its option (b)) in the CLOSURE
  Dispositions table
- **Precondition:** TG-1..TG-6 code/doc tasks done
- **Tests:** `dadaia specs doctor` SPEC-DOC-031/032 clean (verified in
  T-014-22).
- **Done:** every picked bug/backlog item carries a terminal status with
  evidence; never-delete law respected.

---

## TG-7 — Projection + final verification

Write set (group): generated projections via `dadaia public stage/install`
(never hand-edited), `.git/hooks/` via `dadaia ci install-hook`, evidence
artifacts under `.dadaia/reports|handoff/`. Disjoint from all source groups.

### [x] T-014-21 — Projection chain + hook installation
- **Owner:** software-engineer (devops-engineer is a plugin, not distributed)
- **FR:** PLAN "Migration / projection steps" 1–5
- **Files:** projections via `dadaia public stage` →
  `dadaia public install --target all` → `dadaia public doctor`;
  `dadaia ci install-hook --force` on the library repo
- **Precondition:** TG-1..TG-6 complete
- **Tests:** `dadaia public doctor` exit 0 incl. `[ok] public-privacy`; old
  `sdd_gate`/`root_whitelist` PreToolUse wiring absent from projected configs
  (manifest-tracked overwrite verified); both git hooks installed
  (`.git/hooks/pre-commit`, `pre-push`).
- **Done:** live instance runs the merged entrypoint + chokepoints; consumer
  re-install step documented in the rule text.

### [x] T-014-22 — Final verification: e2e seeds 1–6, doctors, regression canon
- **Owner:** qa-engineer (evidence run); software-engineer fixes any red
- **FR:** all acceptance seeds 1–6 + SPEC zero-false-block binding requirement
- **Files:** evidence only (reports/handoff paths); NO production writes
- **Precondition:** T-014-21 done
- **Tests:** two-actor e2e (seed 1) green incl. relaunch/incumbent regression
  matrix and the headless no-hook-env criterion; push-gate e2e (seed 2) green
  incl. G6 commit-flows/push-blocks pair; injection e2e (seed 3) green;
  venv-guard matrix (seed 4) green; perf proofs (seed 5): static single
  PreToolUse command per runtime + subprocess-free dynamic test + live
  hook-latency JSONL (incl. Bash percentile) captured as CLOSURE evidence +
  sdd_post_gate FS-op count == index probe only; doc sweep (seed 6):
  `dadaia specs doctor` + `dadaia public doctor` + `dadaia doctor` exit 0,
  grep sweep over law docs; full lease regression canon green; focused pytest
  for every TG green (`-p no:cacheprovider`).
- **Done:** all seeds evidenced; release ready for security-reviewer push
  verdict and CLOSURE.
