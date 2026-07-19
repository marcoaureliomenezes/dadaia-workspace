# SPEC — Release v0.2.8 — Kimi Code as a Layer-1 Entry Harness

> **Status:** Aprovado

**Release ID:** v0.2.8
**Owner:** product-engineer
**Source:** operator demand (kimi-code Layer-1 support)
**Workflow:** release-definition / spec_create

## 1. Problem

dadaia-workspace supports three Layer-1 agentic entry harnesses — Claude Code, Codex, and
PI — each receiving a projected config tree (`.claude/`, `.codex/`, `.pi/`) that wires the
same deterministic actions: the merged PreToolUse gate (root-whitelist, venv-guard, SDD
gate), the PostToolUse presence heartbeat, and bind-driven context injection
(`ctx_inject`). The **Kimi Code CLI** (`kimi`) is a fourth agentic CLI in operator use,
but dadaia-workspace projects nothing for it: a kimi session in a dadaia workspace runs
without the gate, without presence, and without context injection. The kimi harness must
become a fully supported Layer-1 entry harness.

Kimi Code constraints established from the official documentation
(`https://www.kimi.com/code/docs/en/`, fetched 2026-07-19):

- Kimi has **no project-level config file mechanism**; `[[hooks]]` rules live only in the
  user-level `~/.kimi-code/config.toml` (`$KIMI_CODE_HOME/config.toml`) or in plugin
  manifests. Hook commands run with the session's project directory as cwd, receive a JSON
  payload on stdin (`hook_event_name`, `session_id`, `cwd`, tool fields), and decide via
  exit code (`0` allow, `2` block with stderr reason; anything else fail-open).
- Kimi hook events cover every dadaia need: `PreToolUse` (blockable), `PostToolUse`
  (observation), `UserPromptSubmit` (stdout is appended to context), `SessionStart`
  (`startup|resume`), and `PreCompact`/`PostCompact` (`manual|auto`, observation-only).
- Kimi has **no custom sub-agent definitions** (built-ins `coder`/`explore`/`plan` only),
  so — like PI — no sub-agent projection exists; Layer-2 keeps personas.
- Kimi natively scans project-level `.agents/skills/` and reads project `AGENTS.md`
  (plus `.kimi-code/AGENTS.md`), so the universal skills corpus and the scoped AGENTS.md
  rules already work unmodified.

## 2. Objective

Make `kimi-code` a first-class Layer-1 entry harness of dadaia-workspace — projection
target, deterministic hooks (gate, heartbeat, ctx-inject, post-compact re-inject), doctor
coverage, init scaffolding, and documentation — with Layer-2 workers unchanged
(`codex`/`pi` only).

## 3. Scope

### FR1 — Harness registry

`kimi-code` is added to `L1_ENTRY_HARNESSES` in `dadaia_workspace/core/harness_registry.py`
(deriving `PROJECTION_TARGETS`/`INSTALL_TARGETS`/`parse_harness_set`). It is **not** added
to `L2_WORKER_HARNESSES`, `_LAYER2_ENTRY_HARNESSES`, `AgentRuntimeKind`, or the L2 model
catalog.

Acceptance / verification:

- Registry contract tests assert the exact tuples including `kimi-code`.
- `dadaia public install --target kimi-code` is accepted; `--target all` includes it.

### FR2 — Projection source and installer

New staged source tree `dadaia_workspace/public/kimi-code/` (added to `_COPY_DIRS`)
containing the kimi-facing `AGENTS.md` orientation file. A new `_install_kimi_code()`
installer:

- copies the staged tree to the workspace `.kimi-code/` (verbatim, like `_install_pi`);
- writes/updates a **managed `[[hooks]]` block** in `~/.kimi-code/config.toml` between
  marker comments, containing exactly four rules: `PreToolUse` (matcher
  `^(Edit|Write|Bash)$`), `PostToolUse`, `UserPromptSubmit`, `PostCompact`
  (matcher `manual|auto`), each calling a generated shim;
- writes executable shim scripts under `~/.kimi-code/hooks/dadaia-kimi-*.sh`. Shims are
  workspace-agnostic: they resolve the nearest `.dadaia/.venv/bin/python` by walking up
  from the hook cwd, delegate to the existing Python hook modules, and exit 0 (fail-open)
  outside dadaia workspaces. Both sides honor `KIMI_CODE_HOME` when set.

Acceptance / verification:

- Unit tests pin the generated TOML block and shim contents; install is idempotent
  (hash-compare, `write_generated`) and preserves user config outside the markers.

### FR3 — Deterministic hook wiring (same actions as other harnesses)

The shims delegate to the existing modules with kimi protocol translation:

- `dadaia-kimi-pre-gate.sh` → `hooks.pre_gate`; stdout containing `"decision": "block"`
  is translated to exit `2` with the reason on stderr; anything else exits `0`.
- `dadaia-kimi-post-gate.sh` → `hooks.sdd_post_gate` (presence heartbeat); always exit `0`.
- `dadaia-kimi-ctx-inject.sh` → `hooks.ctx_inject`; stdout passes through (kimi appends it
  to context on `UserPromptSubmit`); always exit `0`.
- `dadaia-kimi-post-compact.sh` → `hooks.ctx_inject` with `DADAIA_HOOK_EVENT=PostCompact`
  (see FR4); always exit `0`.

Acceptance / verification:

- Shim tests simulate payloads (block and allow) and assert exit codes/stdout/stderr.
- venv-guard parity: shims only ever invoke `<workspace>/.dadaia/.venv/bin/python`.

### FR4 — Post-compaction context re-injection

`hooks/ctx_inject.py` learns a second epoch source: a per-session compact marker
(`.dadaia/tmp/ctx-compact-<session_id>`) written when `DADAIA_HOOK_EVENT=PostCompact`.
The fire condition becomes *bind-epoch newer than sentinel* **or** *compact marker newer
than sentinel*. The next `UserPromptSubmit` after a `/compact` therefore re-injects the
tech-stack digest + catalog tldr-digest — the deterministic compaction re-injection the
other harnesses do not have yet.

Acceptance / verification:

- New unit tests: PostCompact writes the marker and injects nothing; a subsequent
  UserPromptSubmit re-injects exactly once (sentinel discipline preserved).

### FR5 — Root law, init, capabilities

- `.kimi-code` joins the workspace-root whitelist (`hooks/root_whitelist.py`), the
  spec-context doctor allowed root dirs (`features/spec_context/doctor.py`), the
  `dadaia init` scaffold (`features/workspace/service.py`), and the root `AGENTS.md`
  template (`public/data/AGENTS.md` + repo `AGENTS.md`).
- `features/capabilities/service.py` lists `kimi-code` in `layer_1`.

Acceptance / verification:

- Root-whitelist and doctor tests cover `.kimi-code`; init tests assert the scaffold.

### FR6 — Doctor coverage

`dadaia public doctor` gains a kimi family: `.kimi-code/` tree compare (like the pi
block), managed config block presence + currency, shim presence + executable bit +
currency, and out-of-profile warning when `.kimi-code/` exists outside the harness
profile.

Acceptance / verification:

- Doctor unit/integration tests for the new checks; existing doctor goldens regenerated.

### FR7 — Tests and goldens

All harness-enumerating tests are updated: registry contract, install-target goldens
(regenerated via `UPDATE_INSTALL_GOLDENS=1`), profile/init tests, `harness_env` fixture +
contract test (new `kimi_hook_env()`), hook tests, e2e pipeline profile lists, plugin
projection target lists.

Acceptance / verification:

- The full pytest suite passes with the new harness in every enumeration.

### FR8 — Documentation and memory

README harness table, `pyproject.toml` description/keywords, root `AGENTS.md` template,
and product memory (`specs/memory/tech-stack.md`, `specs/memory/architecture.md`,
`specs/memory/product/harness/harness-kimi-code.md`, `catalog.json`, `index.md`) state
that kimi-code is a supported Layer-1 harness, including the no-project-config design
consequence (managed user-level hook block).

Acceptance / verification:

- `dadaia specs doctor` and `dadaia public doctor` are clean; memory files updated in the
  CLOSURE phase per the phase gate.

## 4. Out of scope

- Kimi as a Layer-2 worker (no `AgentRuntimeKind`, no runtime adapter, no model catalog
  entry) — Layer-2 stays `codex`/`pi` only.
- Telemetry/session-log readers and panel runtime switcher for kimi (session storage
  format not stabilized upstream); panel keeps claude/codex/pi.
- Kimi plugin-marketplace distribution of dadaia assets (the managed config block is the
  supported mechanism; a local plugin manifest is not shipped).
- Porting the post-compact re-injection (FR4) to claude/codex/pi (candidate future work).
- Custom kimi sub-agents (unsupported upstream by design).

## 5. Dependencies and risks

| Risk | Mitigation |
|---|---|
| Kimi has no project-level config; hooks must live in the user-global `~/.kimi-code/config.toml` — a new "write outside the workspace" pattern. | Managed marker-delimited block only; shims fail-open outside dadaia workspaces; doctor verifies block and shims; no credentials or workspace-absolute paths are written (shims resolve at runtime). |
| Hook protocol mismatch (dadaia envelope vs kimi exit codes). | Shim translates `"decision": "block"` → exit 2 + stderr; fail-open on any error, mirroring the PI extension contract. |
| Harness id contains a hyphen (`kimi-code`) and may break tokenization assumptions (labels, JS data attrs, paths). | Grep-driven audit during implementation; contract tests pin the exact id; doctor labels follow the existing `pi:`-style prefix pattern. |
| Upstream doc drift (hook events/payload fields). | Design uses only documented stable surface (events, stdin payload, exit codes); smoke validation replays real payloads. |
| `specs doctor` / goldens churn from the new target. | Goldens regenerated in the same release; profile scoping keeps non-kimi workspaces untouched. |
