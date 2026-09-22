---
slug: harness-claude-code
title: harness-claude-code
tldr: Entry harness with native sub-agent dispatch; reads the root AGENTS.md map natively and reaches skills and personas through per-entry symlinks into .agents/.
summary: How Claude Code loads the workspace law, attaches scoped law, dispatches the three dd- personas, and which hooks and gates it runs; the CLAUDE.md bridge and the DADAIA.md chain died at 0.4.7 candidate 6 (ADR 0017).
tags: [harness, claude-code, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Load path and gates

- Claude Code is the only harness with native sub-agent dispatch (the Agent tool); the three `dd-` personas run inside it as sub-agents.
- Claude Code 2.1.277+ reads the root `AGENTS.md` map natively at session start when no `CLAUDE.md` sits on or above the cwd; a scoped `AGENTS.md` attaches when a file in its directory is Read — probes ZEBRA/KOALA 2026-09-20 ([[agentic-entities]]).
- No `CLAUDE.md`, no `DADAIA.md`: the workspace ships none, and `dadaia init` recommends the user setting `instructionFiles: claude-md-and-agents-md` so a repo's own `CLAUDE.md` never hides the map; sessions launch at the workspace root.
- `.claude/skills/<name>` and `.claude/agents/<name>.md` are relative symlinks into `.agents/skills/` and `.agents/agents/` (hash-verified copies where `os.symlink` fails); `SYMLINK-TARGET-1` attests every entry ([[public-asset-distribution]]).
- `dadaia context bind <ctx>` arms ctx-inject (`UserPromptSubmit`), which injects the bound context's tech-stack digest and feature catalog once per session — never the law, which the map already loads.
- Claude Code exposes a native session id, so the bind record is this session's own at rung 2 and a concurrent session's bind never reaches it ([[context-management]]).
- `.claude/settings.json` registers `SessionStart` matchers `compact`, `clear`, `startup` and `resume` — the bootstrap re-emits after a compact or `/clear`, and a NEW session receives it at the event itself.
- Writes pass PreToolUse `pre_gate` (matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`), the throttled PostToolUse reaper, and the git chokepoints ([[sdd-gate-v3]]).
- The pre-gate emits a merged envelope — `hookSpecificOutput.permissionDecision: deny` with its reason is the operative contract, the top-level `decision: block`/`reason` pair riding along for the Codex hooks and the Kimi shim; an ALLOW carries no permission verdict.
- It never answers `permissionDecision: allow`, which would bypass the permission prompts.
- `dadaia harness add claude` (or `public install` with claude on the roster) writes `.claude/settings.json` and the symlink set; the personas themselves render once into `.agents/agents/` with resolved model/effort and `activity_class`-derived permissions ([[public-asset-distribution]]).

- Without a workspace, the standalone dd- skills reach Claude Code as the `dadaia-skills` marketplace (`/plugin marketplace add marcoaureliomenezes/dadaia-skills`, `/plugin install dadaia-skills@dadaia-skills`) or by `npx skills add` into `.claude/skills` ([[public-asset-distribution]]).

## Dependencies

[[ARCHITECTURE]], [[sdd-gate-v3]], [[public-asset-distribution]], [[agent-orchestration]], [[agentic-entities]].
