# SPEC: v0.1.10 — Lock Correctness + Model Registry

**Status:** Em revisão
**Release ID:** v0.1.10
**Owner:** product-engineer
**Created:** 2026-06-10

---

## Objective

Fix five open bugs covering two failure domains:

1. **Lock-correctness domain** — three compounding defects that allow a live lease to be
   stolen by a non-owning session (CRITICAL bug `lease-stolen-by-additive-write-from-live-session`)
   and two related ergonomic defects (`context-bind-forces-mode-choice-on-operator`,
   `gate-fpath-not-canonicalized-before-classifier`).

2. **Model-registry domain** — two independent defects: the FPATH canonicalization gap in
   the bash gate (included in lock-correctness workstream) and the dual-table haiku
   desync + absent single registry (`model-catalog-modelmap-pricing-drift-no-registry`).

One additional bug (`opencode-parity-test-asserts-stale-bash-script-ref`) is verified
superseded by prior work and is closed here with that justification.

One infrastructure bug (`pre-push-gate-cannot-locate-workspace-venv`) rounds out the
release by making the pre-push CI gate actually executable in the self-hosting layout.

No new features, no new CLI commands. Every change is correctness or infrastructure
hardening.

---

## Bug inventory and resolution map

| Bug | Severity | Resolution |
|-----|----------|-----------|
| `lease-stolen-by-additive-write-from-live-session` | CRITICAL | Fixed by WS-1 (D1), WS-2 (D2), WS-3 (D3) |
| `model-catalog-modelmap-pricing-drift-no-registry` | MEDIUM | Fixed by WS-4 |
| `context-bind-forces-mode-choice-on-operator` | MEDIUM | Fixed by WS-3 |
| `gate-fpath-not-canonicalized-before-classifier` | MEDIUM | Fixed by WS-5 |
| `pre-push-gate-cannot-locate-workspace-venv` | MEDIUM | Fixed by WS-6 |
| `opencode-parity-test-asserts-stale-bash-script-ref` | MEDIUM | Superseded by v0.1.8 (T-018-19); see §Bug supersession |

### Bug-always-solved justification

Every picked bug is either fixed by a named workstream or explicitly superseded with
verifiable evidence. No bug is silently dropped.

---

## Bug supersession

### `opencode-parity-test-asserts-stale-bash-script-ref`

**Status in codebase at v0.1.10 definition time:** Already corrected.

Inspection of
`tests/e2e/features/test_opencode_parity_hardening.py::TestPluginProjection::test_sdd_gate_plugin_projected`
at HEAD shows line 129 reads:

```python
assert "sdd-spec-gate.sh" not in text
```

This is the correct post-ADR-7 assertion. The bug described a `not in` being written as
`in`. The fix was delivered as part of the v0.1.8 implementation work (T-018-19 scope
expansion or a follow-up edit). Task T-0110-VERIFY-01 verifies this is indeed the current
HEAD state and formally closes the bug as superseded-by-v0.1.8.

`superseded_by: v0.1.8`

---

## Workstreams

### WS-1 — Context-relative ADDITIVE classifier (D1 fix)

**Root cause:** `gate_policy.classify_path` checks workspace-root relative paths.
A bug file at `repos/dadaia-workspace/specs/bugs/<slug>.md` has workspace-relative path
`repos/dadaia-workspace/specs/bugs/<slug>.md`, which starts with `repos/` and matches
`MUTATING` before any ADDITIVE prefix is checked. The ADDITIVE prefixes (`specs/bugs/`,
`specs/backlog/`, etc.) are never reached for in-repo paths.

**Fix:** After the workspace-relative path is computed (and before the `case` classifier
runs), strip the `repos/<slug>/` prefix to get the context-relative path, then check
ADDITIVE against the context-relative path. This check is a **short-circuit only**: if
the context-relative path matches an ADDITIVE prefix, classify `ADDITIVE` immediately —
bypassing `lease.acquire` entirely. If the context-relative path does NOT match an
ADDITIVE prefix, fall through to the unchanged workspace-relative classifier. This
guarantees that all non-ADDITIVE in-repo paths (`repos/<ctx>/specs/releases/...`,
`repos/<ctx>/specs/memory/...`, etc.) continue to be classified by the workspace-relative
classifier as MUTATING, MEMORY, FROZEN, or PROTECTED — never as UNGATED.

**Affected:** `features/spec_context/gate_policy.py` (classifier + evaluate), unit tests.

**Functional requirements:**

- FR-WS1-01: A Write to `repos/<slug>/specs/bugs/<any>.md` must classify ADDITIVE and
  return `Decision.ALLOW` without touching the lease.
- FR-WS1-02: A Write to `repos/<slug>/specs/backlog/<any>.md` must classify ADDITIVE.
- FR-WS1-03: A Write to `repos/<slug>/specs/audits/<any>/<any>.md` must classify ADDITIVE.
- FR-WS1-04: A Write to `repos/<slug>/specs/releases/<id>/SPEC.md` must still classify
  MUTATING (releases are not ADDITIVE even in-repo; the context-relative short-circuit
  does not match, falls through to the workspace-relative classifier which correctly
  returns MUTATING).
- FR-WS1-05: A Write to `repos/<slug>/specs/memory/<any>.md` must still classify MEMORY
  (same fall-through logic; workspace-relative classifier handles this).
- FR-WS1-06: The PROTECTED class (`repos/<slug>/...` that resolves to `.dadaia/sessions/`)
  must remain PROTECTED (workspace-relative classifier handles this).
- FR-WS1-07: Workspace-root ADDITIVE paths (`specs/bugs/`, `.dadaia/reports/`, etc.) must
  continue to classify ADDITIVE with no regression.

### WS-2 — Lease heartbeat from PostToolUse (D2 fix)

**Root cause:** The PostToolUse hook (`hooks/sdd_post_gate.py`) renews
`.dadaia/sessions/<id>.json:last_seen_at` keyed by `DADAIA_SESSION_ID`. The lease record
heartbeat in `.dadaia/states/ctx_locks/<ctx>.lock.json` is only renewed when
`lease.acquire` is called — which only happens on a gate-visible Write/Edit tool call.
Long-running Bash calls (pytest, git push) emit no Write/Edit tool calls, so the lease
heartbeat starves. After 120 s the lease appears stale and any concurrent write performs
an auto-TAKEOVER.

**Fix:** Extend `sdd_post_gate.py` to also call `lease.renew_heartbeat` for the active
context when `DADAIA_SESSION_ID` is the lease holder. This decouples lease liveness from
write frequency. The `renew_heartbeat` function already exists in `lease.py` and is
a pure heartbeat bump with no lock state change — it is safe to call on every PostToolUse.

**Critical implementation constraint:** The current `sdd_post_gate.py` returns early (at
approximately line 47–49) if no session file is found. The `renew_heartbeat` call MUST be
placed OUTSIDE this session-file guard — it must run whenever `DADAIA_SESSION_ID` is set
and non-empty, regardless of whether a session file exists. The incident session had no
session file; gating the renewal on file presence defeats the fix.

Implementation notes:
- PostToolUse runs after EVERY tool call (Read, Bash, Write, etc.), so the heartbeat fires
  on Bash tool calls during pytest runs.
- The context must be derived from the same PATH-first logic as the gate; fallback:
  read `DADAIA_CONTEXT` env var, then first-ALIVE registry entry. If context is
  unresolvable, fail-open (no renewal attempted, no error surfaced).
- `renew_heartbeat` is a no-op if the session does not hold the lease — safe for
  read-mode sessions.
- `DADAIA_SESSION_ID` env propagation to subprocess hooks: the harness passes env to
  hook subprocesses. No change needed to the env contract — the PostToolUse already uses
  this env var; extending it to also renew the lease record uses the same channel.

**Acknowledged race — `renew_heartbeat` check-then-act (lease.py:379–394):**
`renew_heartbeat` reads the lock record, checks that `session_id` matches the holder, then
writes an updated heartbeat timestamp. A concurrent `lease.acquire` by a foreign session
can replace the lock record between the read and the write, causing the write to overwrite
with stale holder data. The `is_same_holder` guard at line 388 is the current boundary but
is NOT sufficient: the read-compare-write is unprotected by the sentinel CAS. This release
does not fix the race (doing so requires sentinel-guarded renew, which is a separate
change); it acknowledges it here and adds an acceptance criterion (AC-LOCK-04B) to verify
the guard still catches the most common scenario. A follow-on bug is recorded for the
unsupported case.

**Affected:** `hooks/sdd_post_gate.py`, unit tests.

**Functional requirements:**

- FR-WS2-01: PostToolUse must call `lease.renew_heartbeat(workspace, ctx, session_id)`
  whenever `DADAIA_SESSION_ID` is set and non-empty, outside any session-file guard.
- FR-WS2-02: If the holder runs a Bash call lasting > 120 s with no Write/Edit, the lease
  heartbeat must remain fresh (< 120 s old) via PostToolUse renewal.
- FR-WS2-03: A session that does not hold the lease must not acquire or modify it via
  PostToolUse (renew_heartbeat is a guarded no-op when session_id does not match holder).
- FR-WS2-04: PostToolUse failure (OSError, unresolvable workspace, unresolvable context)
  must never block any tool call; hook must always return 0.
- FR-WS2-05: PostToolUse must call `renew_heartbeat` even when the session file is absent
  (no early return that skips the call when `DADAIA_SESSION_ID` is present).

### WS-3 — Read-mode bind honoured by gate; bind --mode optional (D3 fix)

**Root cause (two parts):**

Part A: `dadaia context bind` requires `--mode` as a mandatory option, forcing the
operator to make a lifecycle decision at bind time. The mode is a lifecycle concern that
should be derived from the dispatched role and phase, not chosen by the human at bind.

Part B: The gate resolves mode as `os.environ.get("DADAIA_MODE", "IMPLEMENTATION")`.
Harness Bash calls run in fresh shells — exported env from a preceding
`eval $(dadaia context bind --mode read)` does not reach the hook subprocess. So
`--mode read` binds are theater for harness invocations: the gate always sees
`IMPLEMENTATION`.

**Fix:**

Part A: Make `--mode` optional in `dadaia context bind`. Default: `read` (observe-only
bind; no lease implications). Document that lease-escalating modes (`implementation`,
`review`) are taken by the dispatched role when it reaches the gate, not by the human.
The `workspace-protocol §2` statement "a bind is optional convenience, never a
precondition" is preserved; now the CLI contract matches the documented model.

Part B (WS-3B — mode resolution): The gate must resolve mode from the **session file as
the primary source**. OQ-1 is resolved: `context.py:319–330` already records the mode in
the session file when the session is created. The gate resolves `session_id` from the hook
payload, reads `.dadaia/sessions/<session_id>.json`, and extracts the `mode` field. If the
session file records `mode: READ` (or `BOUND_READ`), the gate blocks MUTATING writes for
that session. `DADAIA_MODE` env var is retained as a **fast-path override** only (checked
first; if present, used directly; if absent, session-file lookup is the authoritative
source). When DADAIA_MODE is absent from the hook env AND no session file exists (or the
session file has no `mode` field), the gate defaults to `IMPLEMENTATION` — preserving
today's behavior for sessions created before this release.

**Affected:** `cli/context_cmd.py` (or equivalent bind CLI), `hooks/sdd_gate.py`, tests.

**Functional requirements:**

- FR-WS3-01: `dadaia context bind <name>` with no `--mode` flag must succeed (not error).
  Default mode is `read`.
- FR-WS3-02: `dadaia context bind <name> --mode implementation` and `--mode read` must
  continue to work as before.
- FR-WS3-03: The gate resolves mode from the session file as the primary source:
  `session_id` from hook payload → read `.dadaia/sessions/<session_id>.json` → extract
  `mode`. If `DADAIA_MODE` env var is present, it is used as a fast-path override instead.
  When a session file records `mode: READ` or `BOUND_READ`, the gate BLOCKS MUTATING
  writes with a message explaining the session is read-bound.
- FR-WS3-04: When mode resolves to READ, the gate must still ALLOW ADDITIVE, UNGATED, and
  PROTECTED writes per their respective policies (PROTECTED is the only fail-CLOSED path).
- FR-WS3-05: The BLOCK message for a READ-mode MUTATING attempt must NOT instruct the
  operator to rebind or relaunch.
- FR-WS3-06: When DADAIA_MODE is absent from hook env AND no session file is found (or
  session file has no mode field), gate defaults to IMPLEMENTATION (backward compatible).

### WS-4 — Single model registry (model-catalog fix)

**Context:** The operator workaround is already applied as of 2026-06-10: `MODEL_MAP` has
`"claude-fable-5": "gpt-5.5"`, `PRICING_TABLE` has
`ModelPricing(10.00, 50.00, 12.50, 1.00, date(2026,6,1))` (input $10.00/MTok, output
$50.00/MTok, cache-write-5m $12.50/MTok, cache-read $1.00/MTok), `test_model_mapping.py`
updated to 5 entries, all targets reprojected, doctor exit 0. Five agents (product-engineer,
software-engineer, qa-engineer, ai-engineer, project-auditor) run `claude-fable-5`. VERIFY-02
and AC-MODEL-04 preconditions are satisfied (evidence: workaround applied 2026-06-10, 27
catalog tests green).

**Root cause:** `MODEL_MAP` in `infrastructure/runtime_transforms/model_mapping.py` and
`PRICING_TABLE` in `features/telemetry/pricing.py` are independently maintained hardcoded
tables. Currently `MODEL_MAP` has `claude-haiku-4-5-20251001` but `PRICING_TABLE` has
`claude-haiku-3-5`. No automated check detects the desync. Every new model requires
editing both tables manually.

**Fix:** Create a single model-registry module (`dadaia_workspace/core/model_registry.py`)
that defines a unified `ModelEntry` with: `claude_id`, `codex_id`,
`pricing: list[ModelPricing]` (append-only dated rows — preserves `PRICING_TABLE`'s
point-in-time historical-cost semantics; a new pricing tier is appended, never replacing
an existing row), and `tier`. Both `model_mapping.MODEL_MAP` and `pricing.PRICING_TABLE`
become thin views over the registry. `PRICING_TABLE` is derived by taking the most-recent
`ModelPricing` row per model (ordered by `effective_from`); the full dated list is
available from the registry for historical cost computation.

**Doctor check:** A new check in the `features/public/` doctor module (the surface that
runs as part of `dadaia public doctor`) verifies:
1. Every `model:` value in `public/agents/*.md` frontmatter resolves in the registry.
2. `MODEL_MAP` and `PRICING_TABLE` key sets are identical.
Import-linter contracts must allow `features/public/ → core/model_registry` (verify this
dependency is permitted or add the exception before implementation).

Additionally: fix the `codex.py` body-text leak for unknown `claude-*` model ids (the
map_model fail-loud behavior is correct and intentional; the issue is whether the unknown
model id leaks into the Codex TOML body text verbatim when projection runs with an unset
id — verify whether this path exists and close it if it does).

**Affected:** `core/model_registry.py` (new), `infrastructure/runtime_transforms/model_mapping.py`,
`features/telemetry/pricing.py`, `dadaia_workspace/public/` codex projection code (if
leak confirmed), `features/public/` doctor check.

**Functional requirements:**

- FR-WS4-01: A single `core/model_registry.py` module defines `ModelEntry` with
  `claude_id`, `codex_id`, `pricing: list[ModelPricing]` (dated, append-only), and `tier`.
  `MODEL_MAP` and `PRICING_TABLE` are computed from it; `PRICING_TABLE` uses the
  most-recent row per model.
- FR-WS4-02: Every claude model id that appears in `public/agents/*.md` frontmatter
  `model:` field resolves in the registry. Doctor (in `features/public/` surface) emits
  an error if any frontmatter model id is absent.
- FR-WS4-03: `MODEL_MAP` and `PRICING_TABLE` key sets are always identical (both derived
  from the same registry). Doctor emits an error if they desync.
- FR-WS4-04: `pytest` full suite passes. Import-linter passes (including the new
  `features/public/ → core/model_registry` dependency). No regressions in telemetry
  cost computation.
- FR-WS4-05: The haiku desync is corrected: both tables use `claude-haiku-4-5-20251001`
  (or whatever the registry declares as the canonical haiku entry).
- FR-WS4-06 (conditional): If the codex body-text leak for unknown model ids is confirmed,
  it is fixed. If not present, this FR is closed as N/A.

### WS-5 — FPATH canonicalization in gate (hardening)

**Root cause:** `sdd-spec-gate.sh` makes `FPATH` absolute but does not canonicalize it
(no `realpath`) before the `case` classifier. A symlink from an ungated location into
`specs/memory/` could be classified UNGATED instead of MEMORY.

Note: The Python gate (`hooks/sdd_gate.py`) already uses `fpath.resolve()` before
`relative_to`, so it does canonicalize. The shell gate (`public/scripts/sdd-spec-gate.sh`)
does not. This release adds `realpath` canonicalization to the shell gate.

Care: normalize `$WS` consistently (realpath both) so the `repos/$CONTEXT_SLUG/`
reclassification still matches. Verify the gate integration suite stays green (some CI
sandboxes symlink `/tmp`).

**Affected:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh`.

**Functional requirements:**

- FR-WS5-01: `FPATH` is canonicalized via `realpath --canonicalize-missing` (or
  equivalent) immediately after being made absolute, before the `case` classifier runs.
- FR-WS5-02: `$WS` is also canonicalized consistently so relative-to comparisons remain
  correct.
- FR-WS5-03: The gate integration test suite passes on Linux CI (including sandboxes that
  symlink `/tmp`).
- FR-WS5-04: A symlink from an ungated location targeting `specs/memory/` is classified
  MEMORY (or FROZEN/PROTECTED for other gated subtrees), not UNGATED.
- FR-WS5-05: The portability fallback order is: `realpath --canonicalize-missing` (GNU
  coreutils, Linux) → `readlink -f` (macOS/BSD) → `python3 -c "import os,sys;
  print(os.path.realpath(sys.argv[1]))" "$FPATH"` (universal fallback). The final
  fallback must be the Python one-liner — a silent `echo "$FPATH"` is not acceptable as
  a last resort because it would silently preserve unresolved symlinks.

### WS-6 — Pre-push gate workspace venv resolution

**Root cause:** `pre-push-ci-gate.sh` probes `command -v poetry` (PATH) and
`.venv/bin/dadaia` (repo-relative). In the self-hosting layout, the dadaia CLI lives at
`<ws>/.dadaia/.venv/bin/dadaia` (workspace-level venv), not inside the sub-repo. The gate
fails-closed with an error and the operator is forced to use `git push --no-verify`,
defeating the gate's purpose.

**Fix:** Walk up from the git repo root to find the workspace root (presence of `.dadaia/`
directory), then probe `<ws>/.dadaia/.venv/bin/dadaia`. Also accept a `DADAIA_BIN` env
var override.

**Priority order (highest to lowest):**
1. `DADAIA_BIN` env var override — if set and binary exists, use it directly.
2. Workspace-level venv — walk up from `$GIT_DIR` to find `.dadaia/.venv/bin/dadaia`.
3. `poetry` on PATH — existing probe, retained as fallback.
4. Repo-relative `.venv/bin/dadaia` — existing probe, retained as last resort.

**Note on `ci-preflight-raw-traceback-when-poetry-absent`:** This bug is already
`status: Closed` as of the workspace state at definition time. It is moot — WS-6 stands
alone on the `pre-push-gate-cannot-locate-workspace-venv` bug.

**Affected:** `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`.

**Functional requirements:**

- FR-WS6-01: `DADAIA_BIN` env var is checked first; if set and binary exists, use it
  directly (highest priority).
- FR-WS6-02: If `DADAIA_BIN` is unset, walk up from `$GIT_DIR` to find a parent containing
  `.dadaia/.venv/bin/dadaia` and use it.
- FR-WS6-03: `poetry` on PATH is the third fallback; repo-relative `.venv/bin/dadaia` is
  the fourth.
- FR-WS6-04: In the self-hosting dadaia-workspace layout, `git push` from
  `repos/dadaia-workspace/` successfully runs the CI-equivalent suite via the workspace
  venv rather than erroring.
- FR-WS6-05: If no runner is found after all probe paths, the gate must still fail-closed
  with a clear error message (preserve the "never push red silently" contract).
- FR-WS6-06: `pytest` on the hook integration suite passes.

---

## Architecture deltas

- **`dadaia_workspace/core/model_registry.py`** (new): single source of truth for
  `claude_id → {codex_id, pricing: list[ModelPricing], tier}`. Zero I/O. Layer: `core/`
  (no OS calls, no subprocess). Consumed by `infrastructure/runtime_transforms/model_mapping.py`
  and `features/telemetry/pricing.py`.
- **`features/spec_context/gate_policy.py`**: `classify_path` gains a context-relative
  short-circuit for in-repo ADDITIVE paths (non-ADDITIVE falls through unchanged).
  `evaluate` gains READ-mode BLOCK logic driven by session-file mode lookup.
- **`hooks/sdd_post_gate.py`**: adds `lease.renew_heartbeat` call on every PostToolUse
  when session id is set, outside the session-file guard.
- **`hooks/sdd_gate.py`**: resolves mode from session file (primary); `DADAIA_MODE` env
  var as fast-path override; BLOCKS MUTATING paths when mode resolves to READ; defaults
  to IMPLEMENTATION when both sources absent.
- **`cli/context_cmd.py`** (or bind entrypoint): `--mode` becomes optional with default
  `read`.
- **`dadaia_workspace/public/scripts/sdd-spec-gate.sh`**: FPATH `realpath`
  canonicalization with Python one-liner as final fallback.
- **`dadaia_workspace/public/scripts/pre-push-ci-gate.sh`**: workspace venv probe with
  priority DADAIA_BIN > workspace venv > poetry > repo-local .venv.
- No new CLI commands.
- No new agent personas.
- No changes to the lease record schema.
- No changes to the `.ptr` file semantics.

---

## Tech-stack deltas

None. No new dependencies.

---

## Security/operations deltas

- WS-3 (session-file READ-mode gate block) closes a confused-deputy hole: a read-bound
  session could accidentally acquire a MUTATING lease. The fix is now effective for
  harness sessions (session-file lookup) as well as direct-shell use (DADAIA_MODE env).
  Severity: MEDIUM.
- WS-5 (FPATH canonicalization) closes a theoretical symlink traversal misclassification
  (CWE-59). No known exploit path; hardening only.
- WS-1 (context-relative ADDITIVE short-circuit) is primarily a correctness fix but also
  prevents the ADDITIVE bypass being used as a lease-steal vector.

---

## Memory files affected at closure

- `specs/memory/architecture.md` — lease model and gate-policy section updated (WS-1/WS-2/WS-3)
- `specs/memory/product/sdd/sdd-gate-v3.md` — ADDITIVE classifier contract, READ-mode
  gate behavior (session-file primary source)
- `specs/memory/tech-stack.md` — model-registry module noted; model assignments already
  current (workaround applied 2026-06-10)

---

## Acceptance criteria

### AC-LOCK-01 — In-repo ADDITIVE writes bypass lease (WS-1)
A Write to `repos/<any-ctx>/specs/bugs/<slug>.md` by a session that does not hold the
lease is classified ADDITIVE and returns `Decision.ALLOW` without modifying the lease
record. Verified by unit test in
`tests/unit/features/spec_context/test_gate_policy.py`.

### AC-LOCK-02 — Full-pipeline regression: in-repo ADDITIVE does not steal live lease (WS-1)
Full-pipeline regression test of the incident scenario: session A acquires the lease on
context `dadaia-workspace`; clock is injected to advance 130 s with no Write/Edit from
session A; session B calls `gate_policy.evaluate` end-to-end on
`repos/dadaia-workspace/specs/bugs/<slug>.md`; assert Write is ALLOWED AND
`lease.read_record()` still shows session A as holder (lease was not stolen). A unit test
of `classify_path` alone is insufficient — the full `evaluate` pipeline must be exercised
in the dual-session fixture.

### AC-LOCK-03 — PostToolUse renews lease heartbeat on non-write tools (WS-2)
After a simulated `Bash` tool call (non-write) with `DADAIA_SESSION_ID` set to the lease
holder's id, `lease.read_record().heartbeat` is fresher than it was before the call.
Unit test in `tests/unit/hooks/test_sdd_post_gate.py`. A no-session-file variant must
also pass: the renewal occurs even when the session file is absent (no early return that
skips the renewal when `DADAIA_SESSION_ID` is set).

### AC-LOCK-04 — Lease survives a 120 s+ gap; renewal works for live holder past TTL (WS-2)
Two-clock scenario:
1. Acquire lease at T=0 (clock injected).
2. Call `renew_heartbeat` with clock at T+130. Must return True (renewal succeeds for the
   live holder, even though the lease would appear stale to an external observer). Note:
   the current `renew_heartbeat` is_stale-gate would no-op if is_stale is True — the spec
   requires this guard be relaxed for the confirmed holder (same session_id): a live holder
   must be able to renew past TTL to prevent self-steal.
3. After renewal, `is_stale(record)` at T+130 is False (heartbeat was updated).
4. Separately: a foreign `lease.acquire` at T+130 (before renewal) raises `LockHeldError`
   (the holder's heartbeat was refreshed by PostToolUse, so the lease is not stale to the
   foreign session).
Unit test with injected clock.

### AC-LOCK-05 — `dadaia context bind` without --mode succeeds (WS-3)
`dadaia context bind dadaia-workspace` (no `--mode`) exits 0. The exported shell env
contains `DADAIA_MODE=read` (or equivalent default). Verified by CLI integration test.

### AC-LOCK-06 — READ-mode session cannot acquire MUTATING lease; default path unchanged (WS-3)
When mode resolves to READ (via session-file lookup or DADAIA_MODE=READ env), a Write to
a MUTATING path is BLOCKed by the gate with a clear message. No lease record is written.
When DADAIA_MODE is absent from hook env AND no session file exists (or session file has
no mode field), gate defaults to IMPLEMENTATION and a holder session's MUTATING writes
proceed as today. Both paths verified by unit test.

### AC-LOCK-07 — READ-mode session can write ADDITIVE paths (WS-3)
With mode resolved to READ, a Write to `specs/bugs/<slug>.md` returns `Decision.ALLOW`.
Unit test.

### AC-MODEL-01 — Single registry is the source of both tables (WS-4)
`core/model_registry.py` exists. `MODEL_MAP` and `PRICING_TABLE` key sets are identical.
`ModelEntry.pricing` is `list[ModelPricing]` with at least one dated row per model.
`pytest` passes. Import-linter passes (including `features/public/ → core/model_registry`).

### AC-MODEL-02 — Haiku desync corrected (WS-4)
`PRICING_TABLE` contains key `claude-haiku-4-5-20251001` (not `claude-haiku-3-5`).
`MODEL_MAP` and `PRICING_TABLE` both map the same haiku claude id. Doctor emits no error.

### AC-MODEL-03 — Doctor validates agent frontmatter model resolution (WS-4)
`dadaia public doctor` (surface: `features/public/` doctor module) emits an error for any
`model:` value in `public/agents/*.md` that is absent from the registry. When all
frontmatter models resolve, doctor exits 0 for the model-consistency check.

### AC-MODEL-04 — Workaround validation: claude-fable-5 pre-registered (WS-4)
**Precondition: SATISFIED** (evidence: workaround applied 2026-06-10, 27 catalog tests
green). The doctor check finds `claude-fable-5` resolves for all 5 retiered agent
frontmatter files. No error emitted.

### AC-GATE-01 — Shell gate canonicalizes FPATH; automated integration test required (WS-5)
An automated integration test (pytest fixture) creates a symlink in `tmp_path` pointing
into a path that would classify as MEMORY, invokes the shell gate via subprocess, and
asserts the gate returns a MEMORY (blocked) classification — not UNGATED. Manual smoke
alone is insufficient. Additionally, a bash-vs-python gate parity check verifies that
for in-repo ADDITIVE paths (e.g. `repos/<ctx>/specs/bugs/<slug>.md`), the bash gate does
NOT acquire a lease (returns ALLOW without lease modification), matching Python gate
behavior.

### AC-PRE-PUSH-01 — Pre-push gate finds workspace venv; unit test required (WS-6)
A unit test using a fake filesystem tree fixture verifies: DADAIA_BIN env var override
is honored (highest priority); workspace-walk probe finds `.dadaia/.venv/bin/dadaia` when
DADAIA_BIN is unset; error is raised when no runner is found. Manual smoke (git push from
self-hosting layout) provides additional CLOSURE evidence but is not the primary
verification.

### AC-OPENCODE-01 — Stale parity test verified closed (opencode-parity supersession)
`tests/e2e/features/test_opencode_parity_hardening.py::TestPluginProjection::test_sdd_gate_plugin_projected`
passes at HEAD without any modification. The assertion reads
`assert "sdd-spec-gate.sh" not in text`. Bug is formally closed as superseded-by-v0.1.8.

---

## Out of scope

- Full harness env propagation of `DADAIA_MODE` to hook subprocesses via harness config
  changes (WS-3B uses session-file lookup as the primary fix; no harness config changes
  are needed or in scope for this release).
- PID-based or process-liveness-based lease renewal (current TTL-only model is retained;
  WS-2 extends the heartbeat source without adding process probes).
- Sentinel-CAS protection for `renew_heartbeat` (the check-then-act race in
  `lease.py:379–394` is acknowledged; the guard at line 388 is the boundary but is not
  sentinel-protected — a follow-on bug is registered, fix is deferred to v0.1.11).
- Any new feature, CLI command, or agent persona.
- Bulk model-catalog updates beyond haiku desync and claude-fable-5 workaround validation.
- `sdd-spec-gate.sh` → Python full replacement (retained per architecture.md; only
  FPATH canonicalization added in this release).

---

## Dependencies and risks

- **Risk (WS-2):** PostToolUse fires on every tool call — adding `lease.renew_heartbeat`
  increases PostToolUse latency. `renew_heartbeat` is a JSON read + atomic write; measured
  overhead should be < 5 ms. Accept if under 10 ms; otherwise gate the call behind a
  sampling flag.
- **Risk (WS-2, acknowledged race):** `renew_heartbeat` has a check-then-act race
  (read holder → concurrent foreign acquire replaces record → write overwrites with stale
  data). The line-388 same-holder guard is the current boundary and is not sufficient.
  Registered as follow-on bug; this release does not fix it.
- **Risk (WS-4):** Making `PRICING_TABLE` a computed view over the registry changes the
  module structure that is imported by telemetry. Verify mypy --strict passes after
  refactor. Run full pytest suite before merge.
- **Risk (WS-4):** `ModelEntry.pricing: list[ModelPricing]` changes the type relative to
  the current single-`ModelPricing` field. All call sites that access pricing must be
  updated to use the most-recent row (or the full list for historical computation).
- **Risk (WS-1):** The context-relative ADDITIVE check introduces a path-parsing step in
  the classifier hot path. Profile on pathological paths (very long paths, no-repo writes).
- **Risk (WS-5):** `realpath --canonicalize-missing` availability varies across POSIX
  systems. The Python one-liner final fallback ensures the canonicalization is universal.
- **Dependency (WS-4):** `claude-fable-5` workaround already applied (see §WS-4 Context).
  AC-MODEL-04 precondition is satisfied.
- **Dependency (WS-4):** Import-linter contracts must allow `features/public/ → core/`.
  Verify before implementing the doctor check.
