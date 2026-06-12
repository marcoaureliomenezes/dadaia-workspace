# PLAN: v0.1.14 — Deterministic Lifecycle Kernel

**Status:** Aprovado
**Release ID:** v0.1.14
**Owner:** product-engineer
**Created:** 2026-06-12
**Hard cap:** ≤300 lines (SPEC-DOC-005)

---

## Strategy overview

Implementation order: **W4 → W2 → W3 → W1 → W5**. Rationale: W4 (consolidated
PreToolUse entrypoint + tunables module) is the substrate the W3 venv guard and
the W1 reconciler plug into; W2 is independent and high-value (HIGH bug);
W1 chokepoints land once lease correctness (FR-W4-03) is fixed — the pre-commit
gate must not consult a lease store that `context release` corrupts; W5 law
updates land last against the implemented reality. TDD throughout: each FR gets
failing tests first; existing gate contract/property suites must pass unchanged
against the merged entrypoint.

All file paths below are repo-relative to `repos/dadaia-workspace/` and were
verified to exist (or are marked NEW).

## W4 — Hook consolidation + perf + lease correctness

**Design.**
- NEW `dadaia_workspace/hooks/pre_gate.py`: single PreToolUse entrypoint. Reads
  stdin once, then evaluates in order: root-whitelist policy → venv-guard policy
  (W3) → SDD gate policy. First block wins; allow requires all. The existing
  `sdd_gate.py` and `root_whitelist.py` become thin policy modules (their
  `main()` retained one release for back-compat wiring; deprecation note).
- NEW `dadaia_workspace/core/kernel_tunables.py` (ratified DP-1 — pure
  constants, zero I/O; hooks/features/cli all hold a legal core edge): single
  home for `LEASE_TTL_SECONDS`, sentinel GC TTL (`_SENTINEL_GC_TTL_SECONDS` in
  `hooks/ctx_inject.py:46`), session-record GC TTLs, CAS retry counts,
  reconciler throttle TTL. All importers (`features/spec_context/lease.py`,
  `gate_policy.py`, `doctor.py`, hooks) switch to it; `lease.LEASE_TTL_SECONDS`
  kept as a re-export for one release. Import-linter contract: hooks may
  import the tunables module; no reverse dependency.
- **FR-W4-02** `dadaia_workspace/hooks/sdd_post_gate.py::_iter_lease_contexts`
  (line 72) currently lists the whole `ctx_locks/` dir per tool call. Replace
  with `.dadaia/states/ctx_locks/by-session/<sid>.json`, written/removed
  **inside the same O_EXCL sentinel CAS** as the lock-record write in
  `lease.acquire`/`steal`/`release` (one atomic unit per transition — a lost
  index entry is indistinguishable from "holds nothing" and would starve
  renewal). No `renew_heartbeat` index updates needed. Fallback: full scan
  whenever the by-session DIR is absent (migration window). Zero behavior
  change for holders. (Session-record-based lookup is rejected: harness sids
  have no session record.)
- **FR-W4-03** `dadaia_workspace/cli/commands/context.py::release_cmd`
  (line 433): before unlinking the session record, call
  `lease.release(workspace, ctx, session_id)` (exists at
  `features/spec_context/lease.py:462`) per the SPEC's per-flow predicate
  (env-sid records in the eval flow; bound-context resolution + dead-pid or
  caller-ancestry check in the default flow — `ProcessAncestry` port reused).
  **No hook-side renewal guard** (ratified DP-3): renewal stays outside any
  session-record check; `renew_heartbeat` (lease.py:451–456) never re-creates
  an absent/foreign record, so release alone closes the bug.
- **FR-W4-04** `dadaia_workspace/hooks/_common.py::target_path` (line 76):
  return ALL apply_patch file headers (`target_paths() -> list[str]`); gate
  evaluates every path, most restrictive verdict wins. Callers updated
  (`hooks/sdd_gate.py` / new `pre_gate.py`, `hooks/root_whitelist.py`).
- **FR-W4-06** latency telemetry: wrap entrypoint `main()` with monotonic timer;
  append `{ts, hook, event, duration_ms}` to `.dadaia/logs/hook-latency.jsonl`
  (best-effort, fail-open, same pattern as `lock-events.jsonl`). Perf note:
  W3 adds Bash to the PreToolUse matcher — Bash calls go 0 → 1 interpreter
  spawn each (highest-frequency tool); the telemetry captures a Bash-event
  latency percentile so the trade is measured, not implicit.

**Wiring.** `dadaia_workspace/infrastructure/runtime_config.py` (lines ~70/165:
Claude `settings.json` + Codex `hooks.json` templates) switches PreToolUse to
`dadaia_workspace.hooks.pre_gate`. `features/spec_context/gate_policy.py`
docstring + `__all__` updated (it stays the single classifier/decision policy).

**Touched:** `hooks/pre_gate.py` (NEW), `hooks/sdd_gate.py`,
`hooks/root_whitelist.py`, `hooks/sdd_post_gate.py`, `hooks/_common.py`,
`core/kernel_tunables.py` (NEW), `features/spec_context/{lease,gate_policy,doctor}.py`,
`cli/commands/context.py`, `infrastructure/runtime_config.py`.

## W2 — Bind-driven injection

**Design.** `dadaia_workspace/hooks/ctx_inject.py`:
- `_resolve_context` (line 81): `DADAIA_CONTEXT` env → self-keyed session
  record (resolve sid via `_common.resolve_session_id`, read through
  `features/spec_context/session_identity.py`) → bind-epoch discovery (below)
  → `""`. The first-ALIVE loop is **deleted** from this hook only.
- Unbound path: emit `[no bound context]` + dispatcher preflight + ALIVE-context
  list (names from `.dadaia/states/spec_contexts.json`) — never memory.
- **Re-injection + discovery (ratified DP-2):** bind CLI sid ≠ harness sid, so
  `read_session(harness_sid)` is structurally None in the default flow.
  `dadaia context bind` writes a standalone marker
  `.dadaia/states/bind_epoch/<ctx>` (NOT a `.ptr` field — `.ptr` is
  lease-incumbency, rewritten by `acquire`). The hook scans the small marker
  dir; re-injects when (a) no sentinel for this sid exists, or (b) a marker is
  newer than the sentinel mtime — picking the newest qualifying marker as the
  context (the discovery half that makes FR-W2-02/seed-3 satisfiable).
  Sentinel content gains the injected slug so re-bind to another context also
  re-injects. Accepted semantic: bind binds the CONTEXT (may re-inject a
  concurrent parallel session on its next prompt — NF-2 canon).
- `cli/commands/context.py::bind` updated to write the epoch marker.

**Touched:** `hooks/ctx_inject.py`, `cli/commands/context.py`,
`public/rules/workspace-protocol.md` (§2 — with W5).

## W3 — Venv guard

**Design.** NEW policy module `dadaia_workspace/hooks/venv_guard.py`, invoked
from `pre_gate.py` when `tool_name == "Bash"` (Claude) / shell command events
(Codex). Fixed leading-token patterns only (after stripping env-var prefixes and
`cd … &&` segments is NOT attempted — first command token only, per ADR-G4
narrowness): `dadaia`, `pip`/`pip3`, `python -m dadaia_workspace`,
`python3 -m dadaia_workspace` not prefixed by `.dadaia/.venv/bin/` (or the
workspace-absolute equivalent / `$DADAIA_BIN`) → block; message prints the
corrected invocation. Allow everything else (incl. pytest/ruff/mypy).
**Doctor:** venv-health check in `features/workspace/doctor` surface (venv
exists, `<ws>/.dadaia/.venv/bin/dadaia` executable) — locate the existing
workspace-doctor module and add the invariant there (it lives under
`features/`; exact module resolved at task-writing).

**Touched:** `hooks/venv_guard.py` (NEW), `hooks/pre_gate.py`, workspace doctor
module, `infrastructure/runtime_config.py` (PreToolUse matcher gains Bash).

## W1 — Chokepoints

**Design.**
- NEW `dadaia_workspace/public/scripts/pre-commit-lease-gate.sh`: same
  fail-closed runner resolution as `public/scripts/pre-push-ci-gate.sh`
  (verified: `$DADAIA_BIN` → walk-up `<ws>/.dadaia/.venv/bin/dadaia` → poetry →
  repo venv); delegates to NEW CLI `dadaia ci pre-commit-check`.
- NEW CLI logic in `cli/commands/ci.py` (+ a `features/` service module):
  - `pre-commit-check`: resolve context from repo path (`repos/<slug>` ↔ lock
    name — NOT first-ALIVE; reuse the gate's context-from-path derivation in
    `gate_policy.py`); read `.dadaia/states/ctx_locks/<ctx>.lock.json`. Probe
    order per SPEC FR-W1-01 (ratified DP-4): no/stale-dead lease → allow;
    `DADAIA_SESSION_ID` == holder sid → allow; holder pid is an ancestor of
    the invoking process via NEW `ProcessAncestry` protocol port (port in
    `core/`, three adapters in `infrastructure/`: Linux `/proc` walk, macOS
    `ps -o ppid=` via ProcessRunner, Windows read-only Toolhelp32 — NEVER
    `os.kill`; composition-root selection by the platform seam) → allow;
    indeterminate → ALLOW + logged WARN. Block only on positive non-match.
    Block message: holder sid, age, "the lease frees itself when the holder
    finishes" guidance (never "rebind/steal" — forbidden law).
  - `push-gate-check`: reads the pre-push **stdin ref lines** forwarded by the
    hook (`<local-ref> <local-sha> <remote-ref> <remote-sha>`; never
    `rev-parse HEAD`). For each non-zero `<local-sha>`: scan
    `.dadaia/handoff/<ctx>/*.handoff.json` for `agent == "security-reviewer"`,
    `verdict == "APPROVED"`, `metrics.commit_sha == <local-sha>` (single
    canonical field — no `scope` fallback; schema-additive, no rev).
    Zero-sha (deletion) and tag-only pushes pass. Mismatch/absent → block
    listing what was found. Sha-in-verdict convention documented in W5
    (workspace-protocol §4 note + reviewer persona line).
- `pre-push-ci-gate.sh` extended: run `ci preflight` AND `ci push-gate-check`
  (both must pass), forwarding its stdin to the latter. `dadaia ci
  install-hook` installs both hooks (`.git/hooks/pre-commit`, `pre-push`;
  `--force` semantics preserved).
- **FR-W1-03 reconciler:** post-tool advisory pass inside `sdd_post_gate.py`
  (already fires on every tool call): when the session holds no lease but the
  bound context's repo has dirty MUTATING paths (`git status --porcelain`
  filtered through `gate_policy.classify_path`), append a `RECONCILER_FLAG`
  event to `.dadaia/logs/lock-events.jsonl`. **Layering (declared):** hooks
  are entrypoint/composition modules — a direct, timeout-bounded
  `subprocess.run(["git","status","--porcelain"])` is acceptable here as a
  documented exemption; do NOT route hooks through features service imports
  for this. **Throttle:** per-sid mtime marker
  `.dadaia/tmp/reconciler-last-<sid>`, TTL from `kernel_tunables`, checked
  BEFORE spawning git (no git child per tool call). Never blocks, exit 0 in
  all branches including git failure.

**Touched:** `public/scripts/pre-commit-lease-gate.sh` (NEW),
`public/scripts/pre-push-ci-gate.sh`, `cli/commands/ci.py`,
`core/` ProcessAncestry port + `infrastructure/` adapters (created in TG-2,
reused read-only here), `features/spec_context/{lease,gate_policy,
session_identity}.py` (read-only reuse), `hooks/sdd_post_gate.py`.

## W5 — Law updates

**Touched:** `specs/constitution.md` (§8 enforcement scope → chokepoint
envelope + per-harness matrix + OpenCode posture; §11 push gate mechanical;
operator confirmation required for constitution edits — PM surfaces diff),
`public/rules/workspace-protocol.md` (§1, §2, §4 sha-in-verdict note),
`public/agents/security-reviewer.md` (persona duty: emit `metrics.commit_sha` on push-cycle APPROVE handoffs — the W1 sha-in-verdict line),
`public/rules/release-governance.md` (push gate = security APPROVE; remove
trio-at-rc wording at the push boundary; full ladder deferred to v0.1.15),
`public/rules/bug-registration-guardrail.md` (`session_id: null`),
`public/data/AGENTS.md` (SDD Gate section: merged entrypoint, chokepoints),
backlog re-status edits (`specs/backlog/lease-shell-write-coverage-gap.md`,
`harness-agentic-entities-and-determinism-parity.md`). Affected skills:
`public/skills/dadaia-workspace-manager/SKILL.md`, `harness-primitives`,
`ai-harness-codex` (headless honesty) — wording-only sweep. CLOSURE memory
curation fixes pre-existing `specs/memory/architecture.md` drift: add the
`hooks --> features` edge (scoped: spec_context policy modules — real since
v0.1.10) and the new `hooks --> core/kernel_tunables` edge to the dependency
mermaid; mirror the import-linter contract in the Enforcement subsection.

## Test strategy (TDD)

- **Unit/contract:** existing sdd_gate + root_whitelist suites run unchanged
  against `pre_gate` (parity proof, incl. NotebookEdit exclusion); new suites:
  venv-guard pattern table (block/allow matrix incl. pytest/ruff/mypy allow),
  apply_patch multi-file most-restrictive (bug repro fixture), tunables
  single-home (AST/import check scoped to the kernel modules —
  `features/spec_context/lease.py`, `gate_policy.py`, `doctor.py`, `hooks/*`
  — assert they import the names from `kernel_tunables`; NOT a digit grep;
  plus one behavioral test: monkeypatch the constant, assert lease TTL logic
  observes it), heartbeat no-scan (FS-op counting fake), index/record same-CAS
  atomicity (crash-injection via `_before_write`), `release` drops lease (bug
  repro, both flows), bind-epoch re-injection state machine.
- **Reconciler (FR-W1-03, never-blocks contract):** dirty MUTATING + no lease
  → `RECONCILER_FLAG` appended; held lease / clean tree / ADDITIVE-only dirt
  → no event; exit 0 in ALL branches including `git status` failure;
  throttle: second invocation inside the window emits nothing.
- **Telemetry (FR-W4-06):** entrypoint invocation appends one
  `{ts, hook, event, duration_ms>=0}` JSONL record; unwritable/absent logs
  dir → verdict and exit code unchanged (fail-open contract test).
- **Two-actor e2e (seed 1):** reuses the `lease_rendezvous` REAL-process
  pattern (tests/e2e/test_two_actor_lease.py lineage) for the ancestry-probe
  case: holder child process commits via git subprocess from inside the
  holder's process tree → flows; foreign process → blocked. Env-sid-match
  branch allowed as cheaper integration test. Plus: relaunch (new pid, same
  `.ptr`) → flows; stale-dead lease → flows; v0.1.9–v0.1.11 regression
  scenarios as parametrized cases. Runs with NO harness hook env beyond
  `DADAIA_SESSION_ID`/`DADAIA_BIN` (headless regression criterion).
- **Push-gate e2e (seed 2):** stdin-ref fixtures (APPROVED@pushed-sha,
  APPROVED@stale-sha, REJECTED, absent, branch-deletion zero-sha, tag-only)
  → exactly the right ones pass. Explicit G6 case: holder commits with zero
  handoffs → flows; same state pushes → blocked.
- **Injection e2e (seed 3):** crosses the REAL process boundary: real
  `dadaia context bind` (CliRunner/subprocess, distinct sid) + real hook
  subprocess (reuse `tests/fixtures/harness_env.run_hook_subprocess`):
  unbound → no memory + ALIVE list; bind X → X memory; re-bind Y → Y memory;
  repeat prompt → silent.
- **Doctor venv-health (FR-W3-02):** negative tests on synthetic trees
  (mkdir/touch/chmod, NEVER a real venv build — conftest backstop law):
  missing venv → finding; `bin/dadaia` absent/non-executable → finding;
  healthy synthetic tree → ok.
- **Perf (seed 5):** static — single registered PreToolUse command per
  runtime config; dynamic — subprocess-free contract test (monkeypatch
  `subprocess.Popen/run` + `os.exec*` to raise; drive `pre_gate.main()` with
  fixture stdin for Edit/Write/MultiEdit/apply_patch); live hook-latency
  JSONL as measured CLOSURE evidence (incl. Bash-event percentile);
  sdd_post_gate FS-op count with no held lease == index probe only. No
  timing-flaky assertions in CI.
- **Doctor/projection (seed 6):** `dadaia specs doctor`, `dadaia public doctor`
  exit 0 on the live instance after install; contract test:
  `bug-registration-guardrail.md` template block contains `session_id:`
  (post-stage, so projection carries it).
- Hygiene: pytest `-p no:cacheprovider`; tmp fixtures under `.dadaia/tmp/` or
  `tmp_path`; never against the repo root.

## Migration / projection steps

1. Library edits in `dadaia_workspace/` (source of truth).
2. `dadaia public stage && dadaia public install --target all` — projects
   hooks wiring (`runtime_config`), rules, scripts, AGENTS.md to the live
   instance; plain install propagates on hash change.
3. `dadaia public doctor` exit 0 (incl. `[ok] public-privacy`).
4. Re-run `dadaia ci install-hook --force` on the library repo to pick up the
   pre-commit hook + extended pre-push (and document the step for consumer
   repos in the rule text).
5. Old `sdd_gate`/`root_whitelist` PreToolUse wiring removed by install
   (manifest-tracked overwrite); `configure`d consumer workspaces get the new
   wiring via their next `dadaia public install`.
6. `dadaia doctor` + `dadaia specs doctor` exit 0; commit per task-group.

## Task-group boundaries (for TASKS.md after review)

| Group | Scope | Write set (disjoint) |
|---|---|---|
| TG-1 | W4 substrate: tunables module, pre_gate merge, multi-file apply_patch, telemetry | `hooks/pre_gate.py`, `hooks/_common.py`, `hooks/sdd_gate.py`, `hooks/root_whitelist.py`, `core/kernel_tunables.py`, `infrastructure/runtime_config.py`, tests |
| TG-2 | W4 lease correctness: release-drops-lease (per-flow predicate), same-CAS heartbeat index, `ProcessAncestry` port + adapters | `cli/commands/context.py`, `features/spec_context/lease.py`, `hooks/sdd_post_gate.py`, `core/` (port), `infrastructure/` (adapters), tests |
| TG-3 | W2 bind-driven injection (hook + bind-epoch marker) | `hooks/ctx_inject.py`, `cli/commands/context.py` (bind fn), tests |
| TG-4 | W3 venv guard + doctor check | `hooks/venv_guard.py`, workspace doctor module, tests |
| TG-5 | W1 chokepoints: pre-commit script+CLI, push-gate check, reconciler (reuses TG-2's `ProcessAncestry`) | `public/scripts/*`, `cli/commands/ci.py`, `hooks/sdd_post_gate.py` (reconciler fn), tests |
| TG-6 | W5 law + docs + backlog re-status + projection + e2e seeds 1–6 evidence | `specs/constitution.md`, `public/rules/*`, `public/agents/security-reviewer.md`, `public/data/AGENTS.md`, `public/skills/*`, `specs/backlog/*` |

Overlaps are SEQUENTIAL, never parallel: TG-2/TG-3 on `cli/commands/context.py`;
TG-2/TG-5 on `hooks/sdd_post_gate.py` (TG-1's write set deliberately excludes
it); TG-1/TG-4 on `hooks/pre_gate.py` + `infrastructure/runtime_config.py`.
Review flow per the new model: architect + qa review this SPEC/PLAN before
TASKS.md is written; TASKS only after their APPROVE.

## Design points — RESOLVED (architect DP-1..5, PM-ratified 2026-06-12)

1. Tunables home: `core/kernel_tunables.py` (zero-I/O constants);
   `lease.LEASE_TTL_SECONDS` re-exported one release.
2. Bind-epoch store: standalone `.dadaia/states/bind_epoch/<ctx>` marker —
   NOT a `.ptr` field; doubles as injection context discovery.
3. Heartbeat renewal guard: NONE — absence-based clause deleted;
   `lease.release()` in `release_cmd` is sufficient (`renew_heartbeat` never
   re-creates an absent record).
4. Pre-commit holder probe: env-sid match → `ProcessAncestry` port (Linux
   /proc, macOS ps via ProcessRunner, Windows read-only Toolhelp32 — never
   `os.kill`) → indeterminate ⇒ ALLOW + logged WARN.
5. Push-cycle sha: `metrics.commit_sha`, single canonical field, no `scope`
   fallback, no schema rev; predicate keyed to pre-push stdin ref shas.
