# TASKS: Release — pi-fourth-harness-v1

> **Status:** Aprovado
> **Release ID:** pi-fourth-harness-v1
> **Owner:** product-engineer (authoring) → software-engineer (implementation)
> **SPEC:** Aprovado · **PLAN:** Aprovado

## Protocol

- TDD-first: write the failing test before the production change.
- Conventional commits; `chore(tasks): start <id>` reservation commit on each flip to `[-]`.
- Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. **Max one `[-]` per owner at a time.**
- Hard spine (dependency order): T-PI-01 → T-PI-02 → T-PI-03 → T-PI-04 → T-PI-05 → T-PI-06
  → T-PI-07 → T-PI-08 → T-PI-09 (CLOSURE).
- Owner of T-PI-01..08: `software-engineer`. Owner of T-PI-09: `product-engineer`.
- `changed_paths` MUST come from `git diff`, never a model self-report (root-cause gate).

---

### [x] T-PI-01 — Enum: add `PI_HEADLESS` member

- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/core/models/lifecycle.py` (lines 45-49, `AgentRuntimeKind`)
  - `tests/unit/core/test_agent_runtime_kind.py`
- **Preconditions:** none (spine root).
- **Steps (TDD):** add a failing test asserting `AgentRuntimeKind("pi_headless") is
  AgentRuntimeKind.PI_HEADLESS` and that an `AgentRunRequest` with `runtime=PI_HEADLESS`
  round-trips through `to_dict`/`from_dict`. Then add `PI_HEADLESS = "pi_headless"` to the enum.
- **Done criterion:** new test passes; `AgentRunRequest.to_dict/from_dict` round-trips the
  member with **no** change to `to_dict`/`from_dict` bodies (covered by the existing
  `AgentRuntimeKind(str(...))`).
- **Parallelism:** none — spine root.

### [x] T-PI-02 — Adapter (minimal parser): `PiHeadlessAdapter` + `PiHeadlessConfig`

- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/pi_runtime.py` (NEW)
  - `tests/unit/infrastructure/test_pi_runtime.py` (NEW)
- **Preconditions:** T-PI-01 `[x]`.
- **Steps (TDD):** write `test_pi_runtime.py` (mirror `test_codex_runtime.py`) with an injected
  fake `Runner` returning a canned JSONL stream; assert: `runtime_kind() == PI_HEADLESS`;
  successful run → `AgentRunResult` mapping; runtime-kind mismatch → FAILED; timeout
  (`subprocess.TimeoutExpired`) → FAILED; OSError → FAILED; non-zero exit → FAILED; secret
  redaction incl. `ANTHROPIC_API_KEY`. Then implement `pi_runtime.py` mirroring
  `CodexExecAdapter` (`codex_runtime.py:49-216`): frozen `PiHeadlessConfig(cwd, pi_bin="pi",
  model=None, timeout_seconds=900, env_allowlist=(...incl ANTHROPIC_API_KEY...),
  tools=("read","write","edit","bash"))`; `run()` validates `request.runtime is PI_HEADLESS`,
  builds `pi --mode json --tools <csv> -p -` (prompt on stdin via the same JSON `_prompt`
  shape), runs via injected runner with the same timeout/OSError/non-zero handling; ship a
  **minimal** "last `message_end` → summary" parser (full hardening is T-PI-05).
- **Done criterion:** all listed unit cases pass; **no PI client import at module load**
  (subprocess only); `ANTHROPIC_API_KEY` redacted from output.
- **Parallelism:** none.

### [x] T-PI-03 — Factory branch in `build_agent_runtime`

- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/container.py` (lines 303-340)
  - `tests/unit/test_build_agent_runtime.py`
- **Preconditions:** T-PI-02 `[x]`.
- **Steps (TDD):** add a failing test asserting `build_agent_runtime(AgentRuntimeKind.PI_HEADLESS)`
  returns a `PiHeadlessAdapter` AND that an unknown kind still raises `ValueError`. Then add the
  `PI_HEADLESS` branch (lazy-import `PiHeadlessAdapter` + `PiHeadlessConfig`, mirror the
  `CODEX_EXEC` branch at 325-331).
- **Done criterion:** test passes; factory stays total over the enum (`ValueError` path intact).
- **Parallelism:** none.

### [x] T-PI-04 — CLI harness map: `--harness pi` / `--step-harness x=pi`

- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/cli/commands/lifecycle.py` (lines 27-32, `_HARNESS_KINDS`)
  - the CLI lifecycle harness-resolution test (the test covering `_resolve_harness` /
    `_HARNESS_KINDS`)
- **Preconditions:** T-PI-03 `[x]`.
- **Steps (TDD):** add a failing test asserting `"pi"` resolves to `AgentRuntimeKind.PI_HEADLESS`
  via the harness map and that `--step-harness x=pi` resolves. Then add
  `"pi": AgentRuntimeKind.PI_HEADLESS` to `_HARNESS_KINDS`.
- **Done criterion:** `--harness pi` and `--step-harness x=pi` resolve; **no change** to
  `phase_workflow.py` / `pipeline.py`.
- **Parallelism:** none.

### [x] T-PI-05 — Result extraction (WS-PI-2): harden `_result_from_output`

- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/pi_runtime.py`
  - `tests/unit/infrastructure/test_pi_runtime.py`
- **Preconditions:** T-PI-04 `[x]`.
- **Steps (TDD):** add failing tests for: last-`message_end` wins over earlier events;
  `message.content` extraction handling BOTH a plain string AND a content-block array;
  no/unparseable `message_end` → degraded summary (SUCCEEDED, no crash); a fenced JSON block
  matching `request.expected_schema` → populated `structured_output`; `verdict` / `commit_sha`
  / `summary` / `artifact_refs` mapped as the runner reads them (`agent_runner.py:127-160`).
  Then harden `_result_from_output(stdout, proc)` accordingly.
- **Done criterion:** all extraction cases pass; degraded fallback never crashes; the
  append-system-prompt sentinel is used ONLY as the in-band verdict channel, not primary transport.
- **Parallelism:** none.

### [x] T-PI-06 — `changed_paths` via git diff (Ring-2 root-cause) + end-to-end block test

- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/git_subprocess.py` (add `diff_name_only(path)`)
  - `dadaia_workspace/infrastructure/pi_runtime.py`
  - `tests/unit/infrastructure/test_pi_runtime.py`
  - `tests/unit/infrastructure/test_git_subprocess.py` (the git client unit test) — cover
    `diff_name_only`
  - the lifecycle agent-runner end-to-end test module (faked-runner Ring-2 test)
- **Preconditions:** T-PI-05 `[x]`.
- **Steps (TDD):** add a failing test for `GitSubprocessClient.diff_name_only` (returns the
  `git diff --name-only` list). Add a failing `pi_runtime` test proving `run()` snapshots a git
  baseline before spawning `pi`, computes the post-run diff, and writes the comma-separated list
  into `result.structured_output["changed_paths"]` from a **FAKED git diff** (not a model claim).
  Add a failing end-to-end test through `LifecycleAgentRunner` proving an **out-of-scope**
  `changed_paths` triggers the Ring-2 block (`agent_runner.py:114-123`) and an in-scope set
  passes. Then implement `diff_name_only` and the baseline-snapshot/post-diff in `run()` via
  `GitSubprocessClient` (OS-call boundary stays in infrastructure).
- **Done criterion:** all tests pass; `changed_paths` is sourced from git diff, never a model
  self-report; Ring-2 demonstrably blocks an out-of-scope PI write.
- **Parallelism:** none — closes the WS-PI-2 root-cause gate.

### [x] T-PI-07 — Live-`pi` integration seam (opt-in, NOT CI-gated)

- **Owner:** software-engineer
- **Write set:**
  - `tests/integration/pi_live/__init__.py` (NEW)
  - `tests/integration/pi_live/test_pi_live_contract.py` (NEW)
  - (optional) `tests/integration/pi_live/run_pi_contract_probes.sh` mirroring the codex seam
- **Preconditions:** T-PI-06 `[x]`.
- **Steps:** mirror `tests/integration/codex_live/`. Gate every live test behind
  `DADAIA_PI_LIVE=1` (skipped by default). Document that this is where the upstream
  `pi --mode json` event schema and `AgentMessage.content` shape are verified against a live
  `pi` binary with `ANTHROPIC_API_KEY` + Node present.
- **Done criterion:** with `DADAIA_PI_LIVE` unset, the module is collected and skipped (no live
  call); CI is NOT gated on it; the file documents the live-verification contract.
- **Parallelism:** disjoint write set from T-PI-08 (different files) — may run in parallel with
  T-PI-08 if a second owner is assigned; otherwise serial.

### [x] T-PI-08 — Full local gate green

- **Owner:** software-engineer
- **Write set:** none (verification only; fix-ups land in the relevant prior task's files).
- **Preconditions:** T-PI-06 `[x]` (T-PI-07 ideally `[x]`).
- **Steps:** run `dadaia ci preflight` (ruff format/check, mypy --strict, pytest) → green; run
  `lint-imports` manually → 6 kept / 0 broken. Resolve any failure in the owning task's files.
- **Done criterion:** `dadaia ci preflight` exits 0 AND `lint-imports` reports 6 kept / 0 broken.
  Record the exact commands + evidence (SHA / stdout snippet) for CLOSURE.
- **Parallelism:** none — final implementation gate before CLOSURE.

### [ ] T-PI-09 — CLOSURE (held for ship)

- **Owner:** product-engineer
- **Write set:**
  - `specs/releases/pi-fourth-harness-v1/CLOSURE.md` (NEW)
  - `specs/memory/tech-stack.md`
  - `specs/memory/architecture.md`
  - `specs/memory/product/<harness-or-lifecycle-feature-slug>.md` (exact slug confirmed at CLOSURE)
  - `specs/releases/ACTIVE.md`
- **Preconditions:** T-PI-01..08 all `[x]`; release reviewed and approved for ship; `ACTIVE.md`
  phase set to `CLOSURE` before any memory write.
- **Steps:** invoke `dadaia-release-closure`. Write CLOSURE.md (summary, tasks+SHAs, validations
  incl. preflight + lint-imports evidence, drifts, memory updates, disposition sweep for the EPIC,
  archive decision). Update memory atoms — **including the verified `pi` version pin in
  tech-stack.md** (recorded only after live verification of `pi --mode json` /
  `AgentMessage.content` via the T-PI-07 seam). Run `dadaia specs doctor` green. Then archive
  (`git mv` request to devops/operator) and repoint `ACTIVE.md`.
- **Done criterion:** CLOSURE.md `**Status:** Aprovado`; memory atoms updated; `specs doctor`
  green; disposition sweep complete; release archived.
- **Parallelism:** none — terminal task.

---

## Unverified-seam ledger (record at CLOSURE)

- **The single unverified binding:** the live `pi --mode json` event schema — specifically the
  `AgentMessage.content` shape (string vs content-block array) — is upstream-owned and must be
  live-verified on first networked install with `ANTHROPIC_API_KEY` + Node `pi` present
  (T-PI-07 / `tests/integration/pi_live/`). ALL engine integration + mapping logic is real and
  faked-tested offline. The verified `pi` version is pinned/recorded in `tech-stack.md` at CLOSURE.
- **Deferred (NOT in this release):** WS-PI-3 (`.pi/` projection), WS-PI-4 (Ring-1 extension),
  WS-PI-5 (retire pi-workspace), WS-PI-6 (telemetry), `--mode rpc` + TS SDK transports.
