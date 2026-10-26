---
slug: harness-codex
title: harness-codex
tldr: "Entry harness on the Codex CLI: native AGENTS.md chain and .agents/skills; .codex/ carries config, hooks, the command policy and persona TOML."
summary: Codex reads the root map, the root->cwd AGENTS.md chain and .agents/skills natively; .codex/ holds config.toml, hooks.json, the command-policy rules and the five dd- persona TOMLs transcoded from .agents/agents/.
tags: [harness, codex, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/codex_doctor.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_config.py
  - dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Surface

- Codex is an entry harness — the `codex` TUI and headless `codex exec` — reading the root `AGENTS.md` map, the root->cwd `AGENTS.md` chain and `.agents/skills/` natively; scoped law outside that chain reaches it by skill procedure ([[agentic-entities]]).
- `dadaia harness add codex` projects `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/dadaia-command-policy.rules` and `.codex/agents/dd-*.toml` — each persona transcoded from `.agents/agents/` with `sandbox_mode = "workspace-write"` always (a persona's `read_only` is validated and fail-closed on a bad value, never rendered as a sandbox; the reviewer's read-only holds through its write set and `verdict.py`); every file is compared byte-wise against its renderer, stale persona files pruned.
- Command policy is the Starlark `.rules` file — prefix rules over venv-form paths, the one rule dialect Codex executes. Ordinary `public install` and work-branch pushes receive no product-defined decision; pushes follow the root `AGENTS.md` Gitflow and its shipped pre-push chokepoint. `public install --force`, context deletion and destructive commands receive product-defined prompts.

## Hooks

- The hook behaviours ([[agentic-entities]]) are registered in `.codex/hooks.json` through wrappers under `.dadaia/hooks/codex-*`: `PreToolUse` the pre-gate (matcher `^(apply_patch|Edit|Write)$`), a matcher-less `PostToolUse` post-gate, `SessionStart` (`startup|resume`) ctx-inject plus the reaper, and `UserPromptSubmit` ctx-inject.
- Codex reads the gate's `decision: block`/`reason` envelope directly; the wrappers translate nothing.
- Its hooks run with no session id in their env: each takes the payload's `session_id`, which equals the `CODEX_SESSION_ID` a command of the session and of its subagents sees, so the heartbeat leaves the live record under that id ([[context-management]]).
- Its registry row names the payload's `agent_type` as its subagent key, so Codex is judged by its session record: `verdict.py`, `worktree merge` and `context bind` refuse a call whose env carries a Codex session id with no live record under the workspace root, with the refused bind's fix ([[context-management]]). Codex runs a project hook only for a trusted project whose hook hashes it trusts, so a session launched outside the root, or in a project Codex does not trust, writes no record and is refused; the library sets no Codex trust itself. The pre-gate's matcher holds no shell tool, so the verdict-writer act itself is not judged: inside a governed session an ad-hoc subagent can still write a verdict, which the eval's forged-verdict check measures ([[sdd-gate-v3]], [[agent-evals]]).
- Whether hooks fire is `dadaia certify`'s `codex-live-probe` (a real `codex exec`), never the doctor's.

## Models and doctor

- Codex tier identity is native `(model id × model_reasoning_effort)`: `TIER_CODEX` maps the template's tier alias to the Codex id, an alias outside it failing closed, and the effort comes from one resolver: the D-3 clamp of the template effort, else `medium`.
- `dadaia public doctor` keeps the structural checks byte comparison cannot express: `D-CX-7` (every `dd-` token a persona cites resolves to a skill or persona) and `D-CX-8` (a Markdown file in `.codex/rules/` is flagged; the `.rules` file itself is a byte-compared rule).

## Dependencies

[[agentic-entities]], [[agent-orchestration]], [[sdd-gate-v3]], [[public-asset-distribution]].
