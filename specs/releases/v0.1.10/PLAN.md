# PLAN: v0.1.10 — Lock Correctness + Model Registry

**Status:** Em revisão
**Release ID:** v0.1.10
**Owner:** product-engineer
**Created:** 2026-06-10

---

## Strategy

Five bug fixes across two domains, executed in parallel tracks with one shared
dependency. The lock-correctness domain (WS-1/WS-2/WS-3) is the centerpiece — three
coordinated changes to `gate_policy`, `sdd_post_gate`, and the bind CLI. WS-4 (model
registry) is independent. WS-5 and WS-6 are shell script patches.

No migration of existing state is required. No schema changes. Backward compatibility:
additive changes only to existing modules; old lease records remain valid.

---

## Layers affected

| Workstream | Files | Layer |
|---|---|---|
| WS-1 | `features/spec_context/gate_policy.py` | features |
| WS-2 | `hooks/sdd_post_gate.py` | hooks |
| WS-3 | `hooks/sdd_gate.py`, `cli/context_cmd.py` (or bind entrypoint) | hooks + cli |
| WS-4 | `core/model_registry.py` (new), `infrastructure/runtime_transforms/model_mapping.py`, `features/telemetry/pricing.py`, `features/public/` doctor | core + infrastructure + features |
| WS-5 | `public/scripts/sdd-spec-gate.sh` | public (shell) |
| WS-6 | `public/scripts/pre-push-ci-gate.sh` | public (shell) |
| Tests | `tests/unit/features/spec_context/test_gate_policy.py`, `tests/unit/hooks/test_sdd_post_gate.py`, `tests/unit/hooks/test_sdd_gate.py`, `tests/integration/`, `tests/unit/features/public/test_model_registry_doctor.py` | test |

---

## Execution order and parallelism

```
T-0110-VERIFY-01 (verify opencode-parity supersession) — solo, fast; can run first

[PARALLEL TRACK A — lock correctness]
  T-0110-01 WS-1: classify_path context-relative ADDITIVE
  T-0110-02 WS-2: sdd_post_gate lease heartbeat (outside session-file guard)
  T-0110-03 WS-3A: dadaia context bind --mode optional
  T-0110-04 WS-3B: sdd_gate.py session-file READ-mode + DADAIA_MODE fast-path
    → WS-3B depends on WS-3A (same CLI area; coordinate to avoid conflicts)
    → WS-1 and WS-2 are file-disjoint; safe to run concurrently

[PARALLEL TRACK B — model registry]
  T-0110-VERIFY-02: confirm claude-fable-5 workaround applied (PRECONDITION SATISFIED)
  T-0110-05 WS-4A: core/model_registry.py + refactor MODEL_MAP + PRICING_TABLE
  T-0110-06 WS-4B: features/public/ doctor check for model resolution
    → T-0110-06 depends on T-0110-05 (registry must exist)

[PARALLEL TRACK C — shell gates]
  T-0110-07 WS-5: sdd-spec-gate.sh FPATH realpath + Python fallback
  T-0110-08 WS-6: pre-push-ci-gate.sh DADAIA_BIN + workspace venv probe

[FINAL]
  T-0110-09: full gate (pytest + ruff + mypy + dadaia public doctor + dadaia specs doctor)
```

Tracks A, B, C are file-disjoint and may run in parallel. T-0110-09 waits for all.

---

## Technical approach per workstream

### WS-1 — Context-relative ADDITIVE (gate_policy.py)

`classify_path` receives a workspace-relative POSIX path string. The change adds a
**short-circuit only** before the existing classifier: strip `repos/<slug>/` prefix to
get the context-relative path; if that context-relative path matches an ADDITIVE prefix,
return `PathClass.ADDITIVE` immediately. If it does NOT match, fall through to the
**unchanged** workspace-relative classifier. This guarantees non-ADDITIVE in-repo paths
(`repos/<ctx>/specs/releases/...`, `repos/<ctx>/specs/memory/...`) still resolve to
MUTATING, MEMORY, FROZEN, or PROTECTED via the workspace-relative classifier.

```python
_REPO_PREFIX = "repos/"

def _context_relative_path(ws_rel: str) -> str | None:
    """Strip 'repos/<slug>/' prefix; return None if path is not under repos/."""
    if ws_rel.startswith(_REPO_PREFIX):
        rest = ws_rel[len(_REPO_PREFIX):]
        slash = rest.find("/")
        if slash >= 0:
            return rest[slash + 1:]  # path relative to the repo root
    return None
```

In `classify_path`, before the existing checks, call `_context_relative_path`. If the
result is non-None AND matches an ADDITIVE prefix → return `PathClass.ADDITIVE`. Otherwise
fall through. The unit tests must cover the full matrix in FR-WS1-01..07.

### WS-2 — PostToolUse lease heartbeat (sdd_post_gate.py)

The `renew_heartbeat` call must be placed OUTSIDE the session-file existence guard.
Current structure (approximate):

```python
sess_file = workspace / "sessions" / f"{sess_id}.json"
if not sess_file.exists():
    return 0          # renew_heartbeat must NOT be inside this guard
# ... update session file ...
```

Correct structure:

```python
# Renew lease heartbeat unconditionally when session id is present
if sess_id:
    ctx = _resolve_context(workspace)
    if ctx:
        try:
            from dadaia_workspace.features.spec_context.lease import renew_heartbeat
            renew_heartbeat(workspace, ctx, sess_id)
        except Exception:
            pass  # fail-open

# Session file update (may return early if file absent)
sess_file = workspace / "sessions" / f"{sess_id}.json"
if not sess_file.exists():
    return 0
# ... update session file ...
```

`_resolve_context` uses: (1) `DADAIA_CONTEXT` env var, (2) first-ALIVE registry. Wrap
in broad exception handler (fail-open).

### WS-3 — Bind --mode optional + session-file READ-mode gate (two-part)

Part A (CLI): Change `--mode` from `Option(...)` (required) to `Option(None)` (optional)
with default `"read"`. Update the printed export line and `--help` output.

Part B (gate): Mode resolution order in `sdd_gate.py`:
1. Check `DADAIA_MODE` env var. If present → use it (fast-path override).
2. Resolve `session_id` from hook payload → read
   `.dadaia/sessions/<session_id>.json` → extract `mode` field. If `mode` is `READ` or
   `BOUND_READ` → treat as READ.
3. If both absent → default to `IMPLEMENTATION` (backward compatible).

When mode resolves to READ and `cls == gate_policy.PathClass.MUTATING`:

```python
_common.emit_block(
    "[GATE] This session is bound in read-only mode. "
    "MUTATING writes are not permitted. "
    "No manual action is needed — wait for the active lease holder to finish."
)
return 0
```

This must be evaluated AFTER the PROTECTED short-circuit and AFTER context slug resolution,
but BEFORE calling `gate_policy.evaluate` for MUTATING paths.

### WS-4 — Single model registry (core/model_registry.py)

New module at `dadaia_workspace/core/model_registry.py`:

```python
@dataclass(frozen=True)
class ModelEntry:
    claude_id: str
    codex_id: str
    pricing: list[ModelPricing]  # append-only dated rows; empty = no pricing data
    tier: str  # "opus" | "sonnet" | "haiku" | etc.
```

`ModelPricing` (currently in `features/telemetry/pricing.py`) is moved to `core/` (it
has no I/O, is a pure dataclass, belongs in core models). `pricing.py` imports from
`core`. Import-linter allows `features → core`. Verify `features/public/ → core` is also
permitted before implementing the doctor check; add the exception if needed.

`_REGISTRY: list[ModelEntry]` is the single source. Derived views:
- `MODEL_MAP = {e.claude_id: e.codex_id for e in _REGISTRY}`
- `PRICING_TABLE = {e.claude_id: max(e.pricing, key=lambda p: p.effective_from) for e in _REGISTRY if e.pricing}`

`claude-fable-5` is already in both tables via the operator workaround (precondition
satisfied). The registry entry for `claude-fable-5` carries a single `ModelPricing` row:
`effective_from=date(2026,6,1)`, input=$10.00/MTok, output=$50.00/MTok,
cache-write-5m=$12.50/MTok, cache-read=$1.00/MTok.

**Doctor check** — new check in `features/public/` doctor module (`dadaia public doctor`
surface):
1. Parse frontmatter `model:` values from all `public/agents/*.md` files.
2. Check each value against `MODEL_MAP` keys.
3. Emit error for any unknown model id.
4. Assert `MODEL_MAP.keys() == set(PRICING_TABLE.keys())` — emit error on mismatch.

### WS-5 — Shell gate FPATH realpath

In `sdd-spec-gate.sh`, after the existing `FPATH` absolute-path normalization, apply
canonicalization with the following portability order (highest to lowest):

```bash
# Canonicalize to resolve symlinks (CWE-59 hardening, v0.1.10)
_canonicalize() {
    local path="$1"
    realpath --canonicalize-missing "$path" 2>/dev/null \
        || readlink -f "$path" 2>/dev/null \
        || python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$path"
}
FPATH="$(_canonicalize "$FPATH")"
WS="$(_canonicalize "$WS")"
```

The Python one-liner is the universal final fallback — it resolves symlinks on any system
with Python 3, and is never a silent no-op.

### WS-6 — Pre-push gate workspace venv

Priority order: DADAIA_BIN env var → workspace-level venv walk → poetry on PATH →
repo-relative .venv. In `pre-push-ci-gate.sh`:

```bash
RUNNER=""

# 1. DADAIA_BIN env override (highest priority)
if [ -n "$DADAIA_BIN" ] && [ -x "$DADAIA_BIN" ]; then
    RUNNER="$DADAIA_BIN"
fi

# 2. Walk up to workspace root (presence of .dadaia/)
if [ -z "$RUNNER" ]; then
    DIR="$(pwd)"
    while [ "$DIR" != "/" ]; do
        if [ -x "$DIR/.dadaia/.venv/bin/dadaia" ]; then
            RUNNER="$DIR/.dadaia/.venv/bin/dadaia"
            break
        fi
        DIR="$(dirname "$DIR")"
    done
fi

# 3. poetry (fallback)
if [ -z "$RUNNER" ] && command -v poetry >/dev/null 2>&1; then
    RUNNER="poetry run dadaia"
fi

# 4. Repo-relative .venv (last resort)
if [ -z "$RUNNER" ] && [ -x ".venv/bin/dadaia" ]; then
    RUNNER=".venv/bin/dadaia"
fi

if [ -z "$RUNNER" ]; then
    echo "[pre-push] ERROR: cannot locate dadaia runner. Set DADAIA_BIN or install."
    exit 1
fi
```

---

## Validation plan

1. `pytest` full suite, 0 failures (all tracks).
2. `ruff format --check && ruff check` clean.
3. `mypy --strict` clean (model_registry refactor touches import graph).
4. `dadaia public doctor` exit 0 (WS-4 registry check added in features/public/).
5. `dadaia specs doctor` exit 0.
6. `import-linter` passes (no new forbidden-import violations; features/public/ → core/ verified).
7. Manual smoke: `git push` from self-hosting layout without `--no-verify` → gate runs.
8. Manual smoke: `dadaia context bind dadaia-workspace` (no --mode) → exits 0.

---

## Technical risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| `ModelPricing` move breaks mypy | MEDIUM | Verify import chain with mypy before merging |
| `list[ModelPricing]` call-site updates | MEDIUM | Audit all pricing.py consumers before refactor |
| PostToolUse latency increase | LOW | Benchmark renew_heartbeat (expected < 5 ms) |
| `renew_heartbeat` check-then-act race | LOW (known, not fixed) | Acknowledged; follow-on bug registered |
| `realpath` absent on edge systems | LOW | Python one-liner fallback is universal |
| WS-1 context-relative logic misclassifies edge cases | LOW | Unit tests for all 7 FRs; fuzz paths |
| features/public/ → core/ import-linter violation | MEDIUM | Verify linter rules before implementing doctor check |
