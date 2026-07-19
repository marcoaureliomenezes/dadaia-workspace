# PLAN — Release v0.2.8 — Kimi Code as a Layer-1 Entry Harness

> **Status:** Aprovado

**Release ID:** v0.2.8
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.2.8/SPEC.md`
**Workflow:** release-definition / plan_create

## 1. Planning problem

Add `kimi-code` as the fourth Layer-1 entry harness so a `kimi` CLI session inside a
dadaia workspace runs under the same deterministic guardrails as claude/codex/pi — the
merged PreToolUse gate, the PostToolUse presence heartbeat, bind-driven ctx-inject — plus
post-compact re-injection, which no harness has yet. The constraint that shapes the whole
plan: kimi has **no project-level config file**, so the hook *registration* must live in
the user-level `~/.kimi-code/config.toml`, while the hook *logic* must stay in the
workspace venv (venv-guard law) and remain shared with the other harnesses.

## 2. Architectural approach

Follow the established per-harness pattern (registry → stage → install → doctor), with the
kimi-specific split between workspace assets and user-global wiring:

- **Registry seam:** `core/harness_registry.py` (`L1_ENTRY_HARNESSES += "kimi-code"`).
  Everything downstream (targets, CLI choices, profile scoping) derives from it.
- **Projection source:** `public/kimi-code/AGENTS.md` — kimi-facing orientation (hook trust
  boundary, bind ritual, `/skill:` usage). Staged via `_COPY_DIRS`, copied verbatim to
  `.kimi-code/` by the installer (the `_install_pi` model).
- **User-global wiring (new seam):** `infrastructure/runtime_config.py` gains
  `kimi_hooks_block()` (the managed TOML block text) and `kimi_hook_shims()` (shim
  name → content). The installer upserts the marker-delimited block into
  `$KIMI_CODE_HOME/config.toml` (default `~/.kimi-code/config.toml`) and writes the shims
  to `$KIMI_CODE_HOME/hooks/`, chmod 755, through the same `write_generated` /
  hash-compare idempotence used for codex wrappers.
- **Shim contract (4 scripts):** each shim walks up from its cwd to the nearest
  `.dadaia/.venv/bin/python`; if none exists it exits 0 immediately (fail-open outside
  dadaia workspaces). Otherwise it pipes the stdin payload to the shared Python module and
  translates the result to the kimi protocol:
  - `dadaia-kimi-pre-gate.sh` → `hooks.pre_gate`; `"decision": "block"` in stdout ⇒
    extract `"reason"` to stderr, exit 2; else exit 0 silent.
  - `dadaia-kimi-post-gate.sh` → `hooks.sdd_post_gate`; discard output, exit 0.
  - `dadaia-kimi-ctx-inject.sh` → `hooks.ctx_inject`; forward stdout, exit 0.
  - `dadaia-kimi-post-compact.sh` → `hooks.ctx_inject` with `DADAIA_HOOK_EVENT=PostCompact`;
    discard output, exit 0.
- **Compact epoch (FR4):** `hooks/ctx_inject.py` — when the resolved event is
  `PostCompact`, write `.dadaia/tmp/ctx-compact-<session_id>` and emit nothing. The
  existing fire predicate gains a disjunct: compact marker mtime > sentinel mtime. The
  sentinel/24 h-GC mechanics are reused unchanged; no other harness is affected because
  only kimi wires a PostCompact hook.
- **Root law / init / capabilities:** one-line roster additions in
  `hooks/root_whitelist.py`, `features/spec_context/doctor.py`,
  `features/workspace/service.py`, `core/models/workspace.py` (optional `kimi_dir`),
  `features/capabilities/service.py`, plus the `public/data/AGENTS.md` template and the
  repo-root `AGENTS.md`.
- **Doctor:** a `kimi:`-labelled block in `infrastructure/public_assets.py` `doctor()`
  mirroring the pi block (tree compare + out-of-profile warn) plus generated-block
  verification for the config block and shims.

No new Python dependencies; shims are POSIX `sh` (mirroring the codex wrapper style).

## 3. Implementation contract bindings

### 3.1 Managed config block (exact shape)

```toml
# >>> dadaia-workspace kimi-code hooks (managed by dadaia public install — do not edit) >>>
[[hooks]]
event = "PreToolUse"
matcher = "^(Edit|Write|Bash)$"
command = "<KIMI_CODE_HOME>/hooks/dadaia-kimi-pre-gate.sh"
timeout = 10

[[hooks]]
event = "PostToolUse"
command = "<KIMI_CODE_HOME>/hooks/dadaia-kimi-post-gate.sh"
timeout = 10

[[hooks]]
event = "UserPromptSubmit"
command = "<KIMI_CODE_HOME>/hooks/dadaia-kimi-ctx-inject.sh"
timeout = 10

[[hooks]]
event = "PostCompact"
matcher = "manual|auto"
command = "<KIMI_CODE_HOME>/hooks/dadaia-kimi-post-compact.sh"
timeout = 10
# <<< dadaia-workspace kimi-code hooks (managed) <<<
```

- Upsert rule: replace text between the markers if present, else append the block at end
  of file (TOML allows extending the `hooks` array-of-tables from a later position).
  Content outside the markers is never touched; a missing file is created.
- The installer resolves `<KIMI_CODE_HOME>` from the `KIMI_CODE_HOME` env var, default
  `~/.kimi-code`; the written `command` paths are absolute at install time.

### 3.2 Shim resolution contract

- Resolution order for the workspace root: walk up from `$PWD` (kimi runs hooks with the
  session project dir as cwd) until a directory containing `.dadaia/.venv/bin/python` is
  found; none found ⇒ exit 0.
- The python invocation is always `<root>/.dadaia/.venv/bin/python -B -m dadaia_workspace.hooks.<mod>`
  (venv-guard parity); stdin payload is forwarded verbatim; any shim or python error ⇒
  exit 0 (kimi fail-open philosophy, matching the PI extension).

### 3.3 ctx_inject compact-epoch contract

- `DADAIA_HOOK_EVENT=PostCompact` ⇒ resolve session id, write/touch
  `.dadaia/tmp/ctx-compact-<session_id>`, exit 0 with no stdout.
- Fire predicate: fire iff (bind-epoch marker newer than sentinel) OR (compact marker
  newer than sentinel); on fire, write the sentinel as today. Existing tests must keep
  passing unchanged (no compact marker ⇒ old behavior).

### 3.4 Hyphen-id audit contract

Before close, grep for tokenization-sensitive consumers of harness ids (doctor labels,
JS `data-runtime`, CSS tokens, path joins) and confirm `kimi-code` needs no escaping;
panel/telemetry consumers are out of scope (SPEC §4) and must keep ignoring unknown ids.

## 4. File-touch map

- `dadaia_workspace/core/harness_registry.py`
- `dadaia_workspace/public/kimi-code/AGENTS.md` (new)
- `dadaia_workspace/infrastructure/public_assets_common.py` (`_COPY_DIRS`, `_KIMI_DIRS`)
- `dadaia_workspace/infrastructure/public_assets.py` (`_install_kimi_code`, doctor block,
  plugin-projection branches stay claude/codex-only)
- `dadaia_workspace/infrastructure/runtime_config.py` (`kimi_hooks_block`,
  `kimi_hook_shims`, home-dir resolution helper)
- `dadaia_workspace/infrastructure/install_helpers.py` (legacy-dirs list)
- `dadaia_workspace/hooks/ctx_inject.py` (PostCompact event + compact marker)
- `dadaia_workspace/hooks/root_whitelist.py`
- `dadaia_workspace/features/spec_context/doctor.py`
- `dadaia_workspace/features/workspace/service.py`, `core/models/workspace.py`
- `dadaia_workspace/features/capabilities/service.py`
- `dadaia_workspace/cli/commands/init.py`, `cli/commands/public.py` (help strings)
- `dadaia_workspace/public/data/AGENTS.md`, repo `AGENTS.md`, `README.md`,
  `pyproject.toml`
- Tests: `tests/unit/core/test_harness_registry.py`,
  `tests/unit/infrastructure/test_runtime_config_kimi.py` (new),
  `tests/unit/infrastructure/test_install_target_goldens.py` (+ regenerated goldens),
  `tests/unit/hooks/test_ctx_inject_compact.py` (new), `tests/fixtures/harness_env.py`,
  `tests/contract/test_harness_env_contract.py`, root-whitelist/init/doctor/profile
  suites, e2e profile lists.
- Memory (CLOSURE phase): `specs/memory/tech-stack.md`, `specs/memory/architecture.md`,
  `specs/memory/product/harness/harness-kimi-code.md` (new), `catalog.json`, `index.md`.

## 5. Validation strategy

- Per-task pytest runs (TDD order: tests first inside each task).
- Full suite: `python -m pytest -p no:cacheprovider tests/` (unit + contract + integration).
- Smoke: temp consumer workspace under `.dadaia/tmp/`, `dadaia public stage &&
  dadaia public install --target all`, then replay synthetic kimi hook payloads through
  the installed shims asserting exit codes and injected context; `dadaia public doctor`
  and `dadaia specs doctor` clean.
