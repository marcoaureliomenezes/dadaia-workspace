# Closure: Release - v0.2.8

> **Status:** Aprovado
> **Release ID:** v0.2.8
> **Owner:** product-engineer
> **Closed:** 2026-07-19

## Summary

v0.2.8 makes **Kimi Code** the fourth Layer-1 entry harness of dadaia-workspace,
alongside Claude Code, Codex, and PI. The release adds `kimi-code` to the typed
harness registry, a `public/kimi-code/` projection source, a `_install_kimi_code()`
installer, a `kimi:` doctor family, and root-law/init/capabilities coverage.

Because Kimi Code has **no project-level config file** (verified against the official
documentation), the deterministic hook wiring is delivered through a managed,
marker-delimited block of TOML hook rules upserted into the user-level
`$KIMI_CODE_HOME/config.toml`, plus four workspace-agnostic POSIX shims under
`$KIMI_CODE_HOME/hooks/`. The shims delegate to the same Python hook modules the other
harnesses use — merged PreToolUse gate (block ⇒ kimi-protocol exit 2 + stderr reason),
PostToolUse presence heartbeat, UserPromptSubmit ctx-inject — and fail open outside
dadaia workspaces. v0.2.8 also lands the **compact epoch**: the kimi `PostCompact` hook
stamps a per-session marker that makes the next prompt re-inject the bound context's
bootstrap exactly once — the first deterministic post-compaction re-injection in any
harness. Layer-2 workers remain `codex`/`pi` only, per the operator demand.

## Scope and task completion

| Task ID | Planned scope | Final state | Evidence |
|---|---|---|---|
| T1 | Harness registry: kimi-code as L1 entry harness | Implemented | `tests/unit/core/test_harness_registry.py` 22 passed |
| T2 | runtime_config: kimi managed hook block + shim generators | Implemented | `tests/unit/infrastructure/test_runtime_config_kimi.py` 17 passed |
| T3 | Projection source, installer, doctor family | Implemented | `tests/unit/infrastructure/test_public_assets_kimi.py` 8 passed |
| T4 | ctx_inject PostCompact marker + compact-epoch re-injection | Implemented | `tests/unit/hooks/` 166 passed |
| T5 | Root law, init scaffolding, capabilities | Implemented | root-whitelist/doctor/init/workspace suites 48 passed |
| T6 | Harness fixtures, contract tests, goldens, enumeration sweeps | Implemented | full suite green (see Validations) |
| T7 | Smoke validation: temp consumer workspace + shim replay | Implemented | `.dadaia/tmp/kimi/20260719/smoke.sh` → `SMOKE PASS` |
| T8 | Operator-facing docs: README, pyproject, AGENTS.md templates | Implemented | `dadaia public doctor` exit 0 incl. `[ok] public-privacy` |
| T9 | Product memory update (CLOSURE phase) | Implemented | `dadaia specs doctor` 0 errors |

## Validations

| Description | Command / Artifact | Evidence |
|---|---|---|
| Unit + contract suite | `python -m pytest -p no:cacheprovider tests/unit tests/contract -q` | `2530 passed, 4 skipped` (pre-existing opt-in skips) |
| Integration + e2e suite | `python -m pytest -p no:cacheprovider tests/integration tests/e2e -q` | `258 passed, 6 skipped` (pre-existing opt-in skips) |
| Public pipeline e2e (post-edit re-run) | `pytest tests/e2e/features/test_public_pipeline.py` | `12 passed` (incl. new kimi-code-only profile) |
| Shim replay smoke (allow/block/fail-open/inject/re-inject) | `.dadaia/tmp/kimi/20260719/smoke.sh` | `SMOKE PASS` |
| Projection doctor (real workspace, kimi wiring installed) | `dadaia public doctor` | exit 0; all `kimi-code:*` lines `[ok]`; `[ok] public-privacy` |
| SDD artifact integrity | `dadaia specs doctor` | 0 errors (warnings pre-existing: SPEC-DOC-027/036, token_estimate) |
| Kimi config TOML validity (real `~/.kimi-code/config.toml`) | `python -c tomllib.load` | valid; exactly 4 dadaia `[[hooks]]` rules |

## Drifts

### Post-compact re-injection resolves from the sentinel slug

**Description:** the first T4 iteration re-resolved context only via the FR-W2-01
bind-epoch chain, which cannot fire post-compact (the marker is older than the
sentinel). The final design treats the sentinel's recorded `ctx=<slug>` as the compact
re-injection source — the session's bound truth.

**Resolution:** `hooks/ctx_inject.py` falls back to `recorded_slug` only when
`compacted` is true; covered by `test_bound_session_reinjects_once_after_compact`.

### `kimi_dir` workspace field dropped

**Description:** PLAN §4 listed an optional `kimi_dir` field on
`core/models/workspace.py`. It was not added: `codex`/`pi` carry no such fields either
(only `claude_dir` exists, for legacy reasons), so the field would be speculative
surface with no consumer.

### Panel/telemetry stay claude/codex/pi

**Description:** the panel runtime switcher and telemetry session-log readers do not
gain a kimi row in this release (SPEC §4 out of scope: session storage format not
stabilized upstream). Presence works via the shim-exported `DADAIA_RUNTIME=kimi-code`.

## Memory updates

- `specs/memory/product/harness/harness-kimi-code.md` — NEW atom (Layer-1 surface,
  user-level hook block, compact epoch, out-of-scope L2).
- `specs/memory/product/catalog.json` + `index.md` — regenerated via
  `dadaia memory catalog generate` (28 features; harness-kimi-code rank 10).
- `specs/memory/tech-stack.md` — runtimes roster gains Kimi Code as Layer-1-only.
- `specs/memory/architecture.md` — projection targets and Layer-1/Layer-2 split updated.

## Dispositions

No backlog items or bugs were part of this release scope; nothing to disposition.

## Backlog returns

Candidate future work (not registered as commitments): port the compact-epoch
re-injection to claude/codex/pi; kimi telemetry reader + panel runtime row; kimi
plugin-manifest distribution as an alternative to the managed config block.

## Archive decision

Archive `specs/releases/v0.2.8/` to `specs/_archive/releases/` after the operator
confirms the PyPI deploy of the validated candidate.

## Hermes certification (deploy gate, 2026-07-19)

The candidate wheel `dadaia_workspace-0.4.0` (commit `a649b91e`) passed the full
hermes-crawler gate at dd-chain-capture: **CERTIFIED_100** — matrix 26 PASS / 0 FAIL,
structural gates 5/5, deterministic certification 18/18, verdict JSON at
`/opt/data/.val/matrix-verdict/hermes-certification-0.4.0.json`.

Five certification rounds, each bug investigated to root cause (no workaround fixes):

| Round | Finding | Resolution |
|---|---|---|
| R1 | root-whitelist block message omitted `.kimi-code/` | message now DERIVES from `_WHITELIST` (bug `root-whitelist-message-drifts-from-policy`, resolved) |
| R1 | audit_report rejected by `audit-report-v1` | persona `project-auditor` instructed a competing output envelope vs the fragment; persona now defers to the fragment, fragment pins required finding keys (bug `audit-fragment-schema-envelope-mismatch`, resolved) |
| R2 | kimi-only init leaves `public doctor` red on `dadaia:scripts/*` | chokepoint scripts install for EVERY L1 harness target; e2e fixture workaround removed (bug `kimi-only-init-public-doctor-missing-managed-scripts`, resolved) |
| R2 | kimi PostCompact silent (unverifiable) | PostCompact stamps the marker AND re-emits the bootstrap on stdout without restamping the sentinel (bug `kimi-postcompact-discards-context-reinjection`, resolved) |
| R3 | PostCompact emitted generic preflight after bind-without-prompt | PostCompact resolves context through the full FR-W2-01 chain (session-record leg) with sentinel-slug fallback (bug `kimi-postcompact-omits-bound-context-bootstrap`, resolved) |
| R4 | live backlog intent ref `public list` called unresolvable | **refuted with evidence**: `cli public list` is a canonical Typer-derived anchor listed by `dadaia backlog subjects`; the gate accepted it correctly (bug closed `rejected`) |
