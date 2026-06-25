# PLAN: Release — pi-fourth-harness-v1

> **Status:** Aprovado
> **Release ID:** pi-fourth-harness-v1
> **Owner:** product-engineer
> **SPEC:** `specs/releases/pi-fourth-harness-v1/SPEC.md` (Aprovado)

## Strategy

PI is a **clean adapter addition** behind the existing `AgentRuntimePort`. The whole
release is "mirror `CodexExecAdapter`, swap the binary and the parser." The engine spine is
untouched. Build the hard spine in dependency order so each step is shippable and tested
before the next:

```
enum  →  adapter(min parser)  →  factory  →  CLI  →  result-extraction(WS-PI-2)
      →  changed_paths(git diff, Ring-2)  →  full-gate-green  →  CLOSURE
```

TDD-first throughout: a failing test precedes every production change. Conventional commits.
Max one `[-]` per owner at a time. Implementation owner: `software-engineer`. CLOSURE owner:
`product-engineer`.

## Layers affected

| Layer | File | Change |
|---|---|---|
| core | `core/models/lifecycle.py:45-49` | add `PI_HEADLESS = "pi_headless"` enum member (no model change) |
| infrastructure | `infrastructure/pi_runtime.py` (NEW) | `PiHeadlessAdapter` + `PiHeadlessConfig` |
| infrastructure | `infrastructure/git_subprocess.py` | add a `diff_name_only(path)` helper |
| container | `container.py:303-340` | `PI_HEADLESS` factory branch (lazy import) |
| cli | `cli/commands/lifecycle.py:27-32` | `"pi": AgentRuntimeKind.PI_HEADLESS` in `_HARNESS_KINDS` |

**Untouched (must stay untouched):** `core/scope_match.py`,
`features/lifecycle/agent_runner.py`, `phase_workflow.py`, `pipeline.py`. The Ring-2
classifier and the per-step sequencing are reused, not modified.

## Execution order (the hard spine)

1. **Enum** — add `PI_HEADLESS`; cover the round-trip in `test_agent_runtime_kind.py`.
   `AgentRunRequest.to_dict/from_dict` already round-trips via `AgentRuntimeKind(str(...))`,
   so the only change is the new member + its test coverage.
2. **Adapter (minimal parser)** — `PiHeadlessAdapter` + `PiHeadlessConfig` mirroring
   `CodexExecAdapter`. `runtime_kind() → PI_HEADLESS`; `run()` validates the runtime
   (mismatch → FAILED), builds `pi --mode json --tools <csv> -p -`, runs via the injected
   runner with the same timeout/OSError/non-zero handling, and ships with a minimal
   "last `message_end` → summary" parser. Secret redaction covers `ANTHROPIC_API_KEY`.
3. **Factory** — `build_agent_runtime` gains the `PI_HEADLESS` branch (lazy import; mirror
   the `CODEX_EXEC` branch). Factory stays total (`ValueError` path intact).
4. **CLI** — add `"pi"` to `_HARNESS_KINDS`. `_resolve_harness` then makes `--harness pi` /
   `--step-harness x=pi` work across all verbs with zero workflow/pipeline change.
5. **Result extraction (WS-PI-2)** — harden `_result_from_output(stdout, proc)`: parse JSONL,
   take the **last** `message_end` event, extract assistant text from `message.content`
   (string AND content-block shapes), degraded fallback on no/unparseable `message_end`,
   fenced-JSON-block → `structured_output` when it matches `request.expected_schema`. Map
   `verdict` / `commit_sha` / `summary` / `artifact_refs`.
6. **changed_paths via git diff (Ring-2 root-cause)** — add `GitSubprocessClient.diff_name_only`;
   in `run()`, snapshot the git baseline before spawning `pi`, compute `git diff --name-only`
   after, write the comma-separated list into `result.structured_output["changed_paths"]`.
   Prove the Ring-2 block end-to-end through `LifecycleAgentRunner` with a faked runner.
7. **Full gate green** — `dadaia ci preflight` green + `lint-imports` 6 kept / 0 broken;
   document the `tests/integration/pi_live/` opt-in seam.
8. **CLOSURE** (held for ship) — CLOSURE.md + memory atoms + archive.

## Implementation approach (key design decisions)

- **Mirror `CodexExecAdapter` structurally.** Same `__init__(config, *, runner, environ)`
  shape, same `_env()` allowlist filter, same `_redact` over secret-named env values, same
  timeout/OSError/non-zero-exit handling. This keeps the new surface minimal and the review
  trivial (diff against `codex_runtime.py`). Difference: command is
  `pi --mode json --tools <csv> -p -`; result parsing is JSONL (last `message_end`) instead
  of an `--output-last-message` file.
- **Injectable runner for offline testing.** `run()` calls an injected `Runner =
  Callable[..., subprocess.CompletedProcess[str]]`; tests pass a fake returning a canned JSONL
  stream. No PI client is imported at module load — subprocess only, offline-first preserved.
- **Defensive content parsing.** `message.content` may be a plain string or an array of
  content blocks (`{"type":"text","text":...}`). The parser handles both. Unknown shapes and
  unparseable lines degrade to "raw stdout as summary (SUCCEEDED)" rather than crashing —
  robustness over strictness, exactly as `codex_runtime.py:182-186`.
- **`changed_paths` from git diff, never the model.** A worker cannot be trusted to honestly
  report what it wrote. The adapter snapshots a baseline (`git diff --name-only` before, or an
  empty/clean baseline) and computes the post-run diff through `GitSubprocessClient`
  (`diff_name_only`), keeping the OS-call boundary in infrastructure. This is what gives PI a
  REAL Ring-2 boundary — without it Ring-2 has nothing to classify.
- **Append-system-prompt sentinel is fallback-only.** It survives strictly as the in-band
  channel for review verdicts inside the final message, NOT as the primary result transport.
  `--mode json` is the deterministic primary.

## Test strategy

- `tests/unit/core/test_agent_runtime_kind.py` — new member round-trips via `to_dict/from_dict`.
- `tests/unit/infrastructure/test_pi_runtime.py` (NEW, mirror `test_codex_runtime.py`) — an
  injected fake runner returns canned JSONL; assert: `AgentRunResult` mapping; runtime-kind
  mismatch → FAILED; timeout → FAILED; OSError → FAILED; non-zero exit → FAILED; secret
  redaction (incl. `ANTHROPIC_API_KEY`); **last** `message_end` wins over earlier ones;
  unparseable line → degraded summary (no crash); fenced-JSON verdict block → populated
  `structured_output`; `changed_paths` reflects a **faked git-diff** (not a model claim).
- `tests/unit/test_build_agent_runtime.py` — `PI_HEADLESS` → `PiHeadlessAdapter`; factory
  stays total (unknown kind → `ValueError`).
- **End-to-end Ring-2 test** through `LifecycleAgentRunner` with a faked runner: an out-of-scope
  `changed_paths` (sourced from the faked git diff) triggers the Ring-2 block
  (`agent_runner.py:114-123`), and an in-scope `changed_paths` passes.
- `tests/integration/pi_live/` (NEW, opt-in via `DADAIA_PI_LIVE=1`, skipped by default,
  mirroring `tests/integration/codex_live/`) — the live-`pi`-binary verification seam. NOT
  CI-gated. Documented as where the upstream `pi --mode json` event schema / `AgentMessage.content`
  shape is verified against the pinned `pi` build.

## Layering / lint-imports

The new adapter lives in `infrastructure/` and may import only `core/` (and the existing
`GitSubprocessClient`, also infrastructure). `features/` must not import it (DI via the port,
through the factory). After implementation, `lint-imports` must report **6 kept / 0 broken**
(the 6 contracts in `setup.cfg`) — run manually, since `dadaia ci preflight` does not run it.

## Technical risks

- **Upstream schema (the one unverified seam).** `AgentMessage.content` shape is upstream-owned
  and live-verified only via the opt-in seam. Mitigated by defensive parsing + degraded fallback
  + version pin recorded at CLOSURE. Everything else is real and faked-tested offline.
- **Git baseline correctness.** The diff helper must compute the worker's net changes reliably;
  faked in unit tests, validated live via the opt-in seam.

## Validation plan

| Validation | Command |
|---|---|
| Unit + type + lint | `dadaia ci preflight` (ruff format/check, mypy --strict, pytest) |
| Layering | `lint-imports` (expect 6 kept / 0 broken) — run manually |
| Live seam (opt-in, not CI) | `DADAIA_PI_LIVE=1 pytest tests/integration/pi_live/` |
