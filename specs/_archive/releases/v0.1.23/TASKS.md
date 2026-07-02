# TASKS — Release: v0.1.23 — Multi-harness Layer-2 completion + two-layer fidelity

**Status:** Aprovado
**Release ID:** v0.1.23
**Owner:** product-engineer

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]` per owner unless a
parallel block declares disjoint write sets. Implementer = `software-engineer` unless noted.
`human` tasks are operator-owned and block CLOSURE/deploy.

---

## alpha-1 — Truth-up + coverage

### T-23-01 — RPC removal from constitution + README (WS-4)
- **Owner:** software-engineer
- **Write set:** `specs/constitution.md`, `README.md`
- **Preconditions:** none.
- **Description:** Remove RPC as a stated/supported Layer-2 transport. State the supported
  set as exactly two — CLI-headless and SDK — consistently. RPC may appear only as an
  explicitly-labelled possible future. (The `specs/memory/architecture.md` part is
  T-23-12, CLOSURE phase.)
- **Done when:** no doc states RPC as supported/current; transport set stated as two
  everywhere outside memory; `grep -ri "rpc" specs/constitution.md README.md` shows only
  future-labelled mentions (or none).
- `[x]`

### T-23-02 — Workflow happy-path e2e: IMPLEMENTATION → CLOSURE on FAKE (WS-5)
- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or new
  `tests/integration/cli/test_lifecycle_pipeline_full.py`)
- **Preconditions:** none.
- **Description:** Add an e2e that walks `IMPLEMENTATION → QA_REVIEW → SECURITY_REVIEW →
  CODE_REVIEW → CLOSURE` on `--harness fake`, feeding each gate a green handoff, asserting
  the run advances to `CLOSURE` (first e2e to reach it).
- **Done when:** test asserts terminal phase `CLOSURE` and passes in CI.
- `[x]`

### T-23-03 — Workflow backtrack e2e: review → IMPLEMENTATION (WS-5)
- **Owner:** software-engineer
- **Write set:** same module as T-23-02.
- **Preconditions:** T-23-02 (shares fixtures).
- **Description:** E2e covering `QA_REVIEW`/`SECURITY_REVIEW`/`CODE_REVIEW` → `IMPLEMENTATION`
  on a rejected handoff; assert the run routes back to `IMPLEMENTATION`.
- **Done when:** each backtrack transition asserted end-to-end; CI green.
- `[x]` (transition mechanism proven end-to-end; production rework-path gap filed as backlog `review-rejection-rework-path`)

### T-23-04 — OpenCode Layer-1 gate content-invariant parity test (WS-6)
- **Owner:** software-engineer
- **Write set:** `tests/e2e/features/test_opencode_parity_hardening.py` (extend) or sibling
- **Preconditions:** none.
- **Description:** Assert the OpenCode `sdd-gate.ts` plugin carries the same content
  invariants the PI extension test asserts: single-gate delegation, tool-name→`Write`/`Edit`
  mapping, fail-open default, venv resolution without bash, block-envelope check. Do NOT
  re-add the already-existing projection/delegation assertions.
- **Done when:** new content-invariant assertions present and CI green.
- `[x]`

### T-23-05 — Codex adapter Ring-2 `_GitDiffPort` parity (WS-3 unit half / GAP-B)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/codex_runtime.py`,
  `dadaia_workspace/container.py`, `tests/unit/infrastructure/test_codex_runtime.py`
- **Preconditions:** none.
- **Description:** Inject an optional `_GitDiffPort` into `CodexExecAdapter` so it carries a
  real Ring-2 `changed_paths` seam matching PI; wire it in `build_agent_runtime`. Unit-test
  with a fake git client. (If operator scopes out, abandon → backlog return.)
- **Done when:** Codex `changed_paths` sourced from git diff when a git client is injected;
  unit test green; `build_agent_runtime` signature unchanged for callers.
- `[x]`

---

## alpha-2 — Real adapters

### T-23-06 — Implement `OpenCodeAdapter.run` against `opencode run` headless (WS-1)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/opencode_runtime.py`,
  `dadaia_workspace/container.py` (if wiring needs the git seam)
- **Preconditions:** study the real `opencode run` JSON/stream contract first.
- **Description:** Replace the `NotImplementedError` stub with a real adapter mirroring
  `PiHeadlessAdapter`: injectable `Runner`, env allowlist, secret redaction, defensive
  never-crash parsing, real git-diff Ring-2 `changed_paths` (`_GitDiffPort`), wrong-runtime
  guard returning `FAILED`. Document the verified output contract in the docstring.
- **Done when:** adapter no longer raises on a valid request; `build_agent_runtime(
  OPENCODE_RUN)` returns it with no call-site change; the studied contract is documented.
- `[x]`

### T-23-07 — OpenCode adapter unit tests (WS-1)
- **Owner:** software-engineer
- **Write set:** `tests/unit/infrastructure/test_opencode_runtime.py`
- **Preconditions:** T-23-06.
- **Description:** Mocked-subprocess unit tests: success mapping, wrong-runtime guard,
  timeout, OSError-on-start, malformed-stream degrade, secret redaction, changed_paths from
  git.
- **Done when:** all branches covered; CI green.
- `[x]`

### T-23-08 — OpenCode opt-in live contract test (WS-1)
- **Owner:** software-engineer
- **Write set:** `tests/integration/opencode_live/` (new dir, mirror `pi_live/`)
- **Preconditions:** T-23-06.
- **Description:** Live test driving the real `opencode` binary through `OpenCodeAdapter`,
  gated by `DADAIA_OPENCODE_LIVE=1` + binary-present + auth-present; auto-SKIP otherwise;
  NOT CI-gated; sandbox under `.dadaia/tmp/`.
- **Done when:** test collected + SKIPs cleanly with env unset; asserts a non-crashing typed
  result when run live.
- `[x]`

### T-23-09 — Complete `ClaudeSdkAdapter._default_query_fn` binding (WS-2)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/claude_sdk_runtime.py`
- **Preconditions:** none (lazy import keeps offline build intact).
- **Description:** Wire the real `claude-agent-sdk` `query()` and route `write_permission`
  into `can_use_tool` (deny out-of-scope writes pre-disk). Keep lazy import; keep the
  actionable `ImportError` when absent; map any SDK exception to `FAILED`.
- **Done when:** `_default_query_fn` no longer raises `NotImplementedError` when the package
  is present; module-load import discipline preserved.
- `[x]`

### T-23-10 — Claude SDK adapter unit tests for permission wiring (WS-2)
- **Owner:** software-engineer
- **Write set:** `tests/unit/infrastructure/test_claude_sdk_runtime.py`
- **Preconditions:** T-23-09.
- **Description:** Unit-test the `permission → can_use_tool` wiring with a fake SDK
  module/object (no network): in-scope write allowed, out-of-scope write denied, SDK
  exception → `FAILED`, absent package → actionable `ImportError`.
- **Done when:** all cases covered; CI green; no network.
- `[x]`

### T-23-11 — Claude opt-in live contract test (WS-2)
- **Owner:** software-engineer
- **Write set:** `tests/integration/claude_live/` (new dir, mirror `pi_live/`)
- **Preconditions:** T-23-09.
- **Description:** Live test gated by `DADAIA_CLAUDE_LIVE=1` + `claude-agent-sdk` installed +
  `ANTHROPIC_API_KEY`; auto-SKIP otherwise; NOT CI-gated; asserts a typed result and that an
  out-of-scope write is denied by the Ring-1 wiring.
- **Done when:** collected + SKIPs cleanly with env unset.
- `[x]`

### T-23-12 — Codex Layer-2 adapter opt-in live contract test (WS-3 live half)
- **Owner:** software-engineer
- **Write set:** `tests/integration/codex_live/test_codex_adapter_live_contract.py` (new
  file in the existing dir — distinct from the existing Layer-1 hook tests)
- **Preconditions:** T-23-05 (so the adapter under test carries the git seam).
- **Description:** Live test driving the real `codex exec` binary through `CodexExecAdapter`
  (Layer-2), asserting a typed non-crashing `AgentRunResult`. Gated by `DADAIA_CODEX_LIVE=1`
  + binary + `~/.codex/auth.json`; auto-SKIP; NOT CI-gated. Do not modify the existing
  Layer-1 hook tests.
- **Done when:** collected + SKIPs cleanly with env unset.
- `[x]`

---

## rc-1 — Validation, closure, ship

### T-23-13 — Operator live-validation acceptance gate (WS-7) [HARD GATE]
- **Owner:** human (operator)
- **Write set:** none (sign-off only; results captured in CLOSURE.md at close)
- **Preconditions:** T-23-06..T-23-12 complete and merged-to-feature.
- **Description:** Operator personally runs and confirms each:
  - `[ ]` PI headless live run produces a real typed result.
  - `[ ]` Codex `exec` adapter live run produces a real typed result.
  - `[ ]` Claude SDK live run produces a real typed result AND an out-of-scope write is
    denied by `can_use_tool`.
  - `[ ]` OpenCode live run produces a real typed result.
  - `[ ]` PI post-trust Layer-1 gate blocks a FROZEN write in a real trusted session.
  - `[ ]` Each Layer-1 entry gate (claude/codex/opencode) blocks a FROZEN write (spot-check).
- **Done when:** every sub-item confirmed by the operator. **Blocks CLOSURE and T-23-15.**
- `[ ]`

### T-23-14 — CLOSURE: write CLOSURE.md + update memory atoms (WS-4 memory half)
- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.1.23/CLOSURE.md`, `specs/memory/architecture.md`,
  `specs/memory/tech-stack.md`, affected `specs/memory/product/*.md`,
  `specs/releases/ACTIVE.md`
- **Preconditions:** T-23-13 confirmed; ACTIVE.md phase = CLOSURE.
- **Description:** Write CLOSURE.md (summary, tasks+SHAs, validations incl. WS-7 evidence,
  drifts, memory updates, disposition sweep, archive decision). Update memory: drop RPC from
  the transport set in `architecture.md`, mark OpenCode + Claude Layer-2 workers as real,
  record WS-7-verified `opencode`/`claude-agent-sdk`/`codex` versions in `tech-stack.md`.
- **Done when:** `dadaia specs doctor` green; CLOSURE evidence complete.
- `[ ]`

### T-23-15 — Version bump + deploy (WS-8) [LAST, gated by T-23-13]
- **Owner:** human (operator)
- **Write set:** `pyproject.toml`
- **Preconditions:** T-23-13 confirmed AND T-23-14 complete.
- **Description:** Bump version to `0.1.23`, tag, let `release.yml` publish. Must not run
  before WS-7 sign-off.
- **Done when:** tag pushed; `release.yml` publishes; operator confirms deploy.
- `[ ]`
