# PLAN: v0.1.3 - codex-runtime-readiness

**Status:** Draft
**Release ID:** v0.1.3
**Owner:** product-engineer
**Created:** 2026-06-02

---

## 1. Strategy

Fix the Codex readiness gaps in small, testable slices. The first slice defines the real
Codex activation contract; subsequent slices align docs/adapters/code to that contract.

Do not edit generated projections (`.codex/`, `.agents/`, `.claude/`, `.opencode/`)
directly. All changes go through canonical `dadaia_workspace/public/**`, Python
infrastructure, tests, and memory at CLOSURE.

---

## 2. Execution order

```text
T-CR-01 research/lock Codex activation contract
  -> T-CR-02 fix Markdown memory references
  -> T-CR-03 fix Codex skills/config projection
  -> T-CR-04 fix Codex persona transform for dispatch wording
  -> T-CR-05 ignore cache files in public asset staging/doctor
  -> T-CR-06 reconcile Codex workflow policy
  -> T-CR-09 add scoped AGENTS.md for .dadaia runtime subtrees
  -> T-CR-10 enforce Codex hook parity + Markdown-only memory gate
  -> T-CR-07 propagate and run gates
  -> T-CR-08 QA
  -> CLOSURE memory updates
```

---

## 3. Implementation notes

### Codex activation contract

Use local evidence first:

```bash
codex --version
codex doctor
codex debug prompt-input "probe"
```

`codex doctor` currently reports `~/.codex/config.toml` as the active config. If workspace
`.codex/config.toml` is not automatically consumed, implement a safe bridge instead of
pretending the projection is active. Candidate designs:

- `dadaia codex bootstrap` prints the exact user-level config snippet to include the
  workspace agent/skill setup.
- `dadaia codex exec -- <prompt>` launches Codex with `--config` overrides or a profile.
- `dadaia public install --target codex` writes workspace files only, while doctor reports
  `[warn] codex:user-config-not-bridged` until the user-level config references them.

Do not auto-edit `~/.codex/config.toml` in this release unless the SPEC is amended.

### Markdown memory references

Replace stale `.html` memory paths in:

- `dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md`
- `dadaia_workspace/public/skills/dadaia-workspace-spec-navigator/SKILL.md`
- `dadaia_workspace/public/data/AGENTS.md`
- `dadaia_workspace/public/templates/specs-AGENTS.md`
- agent bodies that still mention `specs/memory/*.html`

Keep the `dadaia-step0-memory-bootstrap` skill as the source pattern: read Markdown
verbatim, prefer `catalog.json`, self-pull 1-3 feature atoms.

### Codex skills/config

Decide whether generated config should be:

```toml
[skills]
paths = [".agents/skills", ".codex/skills"]
```

or whether `.codex/skills` is guaranteed by Codex default discovery. Add a test either
way so the decision is explicit.

### Persona transform

Update `runtime_transforms/codex.py` so PM/auditor dispatch language matches Codex:

- mention `tool_search` when multi-agent tools are deferred;
- avoid implying a literal `subagent` tool exists;
- preserve generic intent for environments where multi-agent tools are unavailable.

### Cache filtering

Update `_iter_files()` or the public staging traversal to exclude:

- `__pycache__/`
- `*.pyc`
- possibly `.DS_Store`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`

Add a regression test that creates a fake `public/scripts/__pycache__/x.pyc` and proves it
does not appear in stage manifest or doctor reports.

### Workflow policy

Pick one:

- Remove Codex workflow projection and keep `[not-applicable]`.
- Keep projection as reference docs and rename doctor status to a truthful non-error such
  as `[reference-only] codex:workflows/<name>`.

The second option is preferred because operators can still inspect canonical workflows in
Codex sessions, but no runtime executor is claimed.

### Scoped AGENTS.md for runtime subtrees

Add public data sources and projection/doctor checks for:

- `.dadaia/AGENTS.md` — runtime control plane rules.
- `.dadaia/tmp/AGENTS.md` — temporary artifact rules.
- `.dadaia/states/AGENTS.md` — machine-owned JSON state rules.
- `.dadaia/reports/AGENTS.md` — report and handoff sidecar rules.

Keep root `AGENTS.md` as a short router to scoped rules. Do not duplicate
report, state, or temporary-file details in the root file.

### Codex hook parity and Markdown-only memory gate

Make Codex hooks behaviorally match the Claude Code SDD hooks:

- Generate `PreToolUse`, `PostToolUse`, and `UserPromptSubmit` in `.codex/hooks.json`.
- Use broad matchers for Codex `PreToolUse` and `PostToolUse`; the shell scripts decide
  whether a tool call is relevant.
- Keep `sdd-spec-gate.sh` as the blocking authority and `sdd-post-gate.sh` as the
  heartbeat authority.
- Prefer `.dadaia/.venv/bin/python` inside hook scripts.
- Stop removing hook references in Codex persona transforms.
- Treat legacy memory `.html`, `.yaml`, and `.yml` files as read-only forever. CLOSURE
  authoring uses Markdown atoms.

---

## 4. Validation plan

Run:

```bash
.dadaia/.venv/bin/python -m pytest \
  tests/unit/infrastructure/test_public_assets.py \
  tests/unit/infrastructure/test_codex_runtime.py \
  tests/unit/test_public_assets.py \
  tests/integration/test_hooks.py \
  tests/unit/gate/test_path_scope.py \
  -q

.dadaia/.venv/bin/python -m ruff check dadaia_workspace tests
.dadaia/.venv/bin/python -m mypy dadaia_workspace
.dadaia/.venv/bin/dadaia specs doctor --specs-dir specs
.dadaia/.venv/bin/dadaia public stage
.dadaia/.venv/bin/dadaia public install --target all
.dadaia/.venv/bin/dadaia public doctor
```

`dadaia public doctor` must report `[ok]` for:

- `dadaia:AGENTS.md`
- `dadaia:tmp/AGENTS.md`
- `dadaia:states/AGENTS.md`
- `reports:AGENTS.md`

Also run a Codex projection smoke under `.dadaia/tmp/` and inspect:

```bash
codex doctor
tomllib.loads(open(".codex/config.toml", "rb").read().decode())
find .codex -maxdepth 3 -type f | sort
```
