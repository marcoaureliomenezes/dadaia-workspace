---
slug: multi-platform-parity
title: multi-platform-parity
category: product
tldr: "Claude Code, Codex, and PI get honest runtime-specific projections from one public source (9 agents / 18 skills / 7 dadaia-workflows)."
summary: Codex uses native config, shared and Codex-specific skills, interactive-only
  hook execution (codex exec never fires hooks — headless posture is chokepoints-only,
  per the §8 enforcement matrix), native Starlark .rules command policy with venv-path
  prefix_rule patterns, workflow docs that do not auto-execute, read-only sandbox for
  evidence-only reviewers, and registry-derived Codex-native model tiering (model id ×
  model_reasoning_effort). All harnesses are protected by the git chokepoints
  (pre-commit lease gate + pre-push security-verdict gate), which fire independently
  of harness hooks. The Layer-1 entry-harness set is exactly {claude, codex, pi} —
  OpenCode was removed entirely in v0.1.24 (both layers; no opencode target/.opencode
  projection/OPENCODE_RUN worker). PI (post-v0.1.18) projects a minimal `.pi/` surface
  and is Layer-1-governed via AGENTS.md natively plus a post-trust Ring-1 SDD-gate
  extension (.pi/extensions/dadaia-sdd-gate.ts → pre_gate, WS-PI-4). Public surface is
  9 core agents, 18 skills, and the 7 dadaia-workflows (see [[lifecycle-foundation]]).
  Plugin stubs (frontend-engineer,
  design-specialist, devops-engineer) project as thin stubs with no behavior until the
  plugin is installed.
tags:
- codex
- claude-code
- pi
- parity
- multi-platform
agent_tier: self-pull
token_estimate: 1550
last_updated: '2026-06-26'
release_origin: v0.1.24
---

## Propósito

Multi-platform parity means the same canonical public assets are projected to
Claude Code, Codex, and PI without pretending the runtimes are identical. Each
projection must be truthful about the runtime's native concepts, supported hooks,
config loading, workflow support, and skill discovery. The Layer-1 entry-harness set is
exactly `{claude, codex, pi}` — **OpenCode was removed entirely in v0.1.24** (both
layers).

### Two-layer scope: projection-parity vs worker-runtime parity

This atom is about **Layer-1 projection parity** — how one canonical source projects
into the entry harnesses the operator launches. It must not be read as the full harness
set. dadaia-workspace runs harnesses at two layers (see [[architecture]] "Two-layer
agentic model"):

- **Layer 1 (this atom) — entry-harness projection parity.** Source
  (`dadaia_workspace/public/`) → `.claude/`, `.codex/`, `.pi/` asset trees via
  `dadaia public install` (targets `{agents, claude, codex, pi}`; **no `opencode` target
  / no `.opencode/` projection** post-v0.1.24). Each tree is truthful about its runtime.
  PI's `.pi/` projection (target `pi`) is **minimal**: `.pi/SYSTEM.md` POINTS AT
  `AGENTS.md` (no law restatement) + a generic `.pi/settings.json` + an optional
  `.pi/prompts/` affordance.
- **Layer 2 — worker-runtime parity (NOT projection parity).** The lifecycle engine's
  per-step worker harnesses behind `AgentRuntimePort` (`FAKE`, `CODEX_EXEC`,
  `CLAUDE_SDK`, `PI_HEADLESS` — `OPENCODE_RUN` removed in v0.1.24). These have **no
  projection tree** — they are subprocess/SDK adapters selected per step, governed by
  `--harness`, not by `.X/` asset projection. **LAW 1 (v0.1.24):** the selectable Layer-2
  **workflow** harnesses are exactly `{pi, codex, fake}`; `CLAUDE_SDK` is kept/tested but
  `claude` is rejected as a workflow `--harness` (Layer-1 use only). PI shipped here first
  (`pi --mode json`). [[lifecycle-foundation]] is the normative source for Layer 2.

**`.pi/` trust surface.** `.pi/**` is a post-trust, unsandboxed, executable-capable
surface (a real privilege grant — the operator who runs `pi` after seeing `.pi/`
extensions grants execution). The `.pi/SYSTEM.md` carries an inline trust-boundary note;
no secrets or operator-local values appear in `public/pi/**` and `[ok] public-privacy`
must stay green.

## Public surface counts (v0.2.0)

| Asset type | Count | Notes |
|-----------|-------|-------|
| Core agents | 9 | project-manager, project-auditor, product-engineer, software-engineer, qa-engineer, security-reviewer, code-reviewer, ai-engineer, software-architect |
| Plugin stubs | 3 | frontend-engineer, design-specialist (plugin: frontend-design); devops-engineer (plugin: devops) |
| Skills | 18 | Reduced from 22 in v0.1.9 (5 frontend/design skills → plugin) |
| dadaia-workflows | 7 | release_definition, backlog_definition, audit, research, bug_report, implementation pipeline, closure (see [[lifecycle-foundation]]) |
| Rules | 8 | workspace-protocol, tmp-file-guardrail, plugin-scope, dadaia-workspace-dev-guardrail, harness-skill-scope, bug-registration-guardrail, backlog-ownership, release-governance |

Agent personas for the following names do not exist in `dadaia_workspace/public/agents/`:
`software-engineer-python`, `software-engineer-node`, `backend-engineer`, `researcher`.
These were consolidated into `software-engineer` or removed from the public roster in v0.1.8.

Plugin stubs (`frontend-engineer`, `design-specialist`, `devops-engineer`) project as
empty stubs — no behavior until the corresponding plugin is installed.

## Fluxo de uso

Codex receives:

- `AGENTS.md` as the automatically loaded workspace rule surface.
- `.codex/config.toml` containing `[agents."<name>"] config_file = "agents/<name>.toml"`
  entries for all projected agents — `config_file` is a real, live-verified config
  key. The file still emits `approved_commands` and `[skills] paths`, but both are
  live-verified INVALID config keys in codex-cli 0.139.0 (inert — no runtime
  behavior; skill discovery does not flow through `[skills] paths`). Their removal
  is deferred backlog (`codex-runtime-fidelity` WS-CDX-HYGIENE).
- `.codex/agents/*.toml` containing native custom-agent definitions, registry-derived
  Codex models, `sandbox_mode`, `model_reasoning_effort`, and developer instructions.
  The `description` field runs through the same Claude-ism replacement table as the
  body. Evidence-only reviewers (`code-reviewer`, `security-reviewer`,
  `project-auditor`) project as `sandbox_mode = "read-only"`. Model guidance is
  rendered per-runtime from `core/model_registry.codex_tier_views()` — tier identity
  is (model id × `model_reasoning_effort`), deep→high / dispatch→medium, with a loud
  failure when a mapping collapses two tiers into one id. No Opus/Sonnet/Haiku prose
  survives in Codex-projected persona bodies (doctor D-CX-4 lints Anthropic tier
  names and Claude tool names like `Agent tool`/`Task tool`).
- `.codex/rules/dadaia-command-policy.rules` as the executable Starlark command-policy
  rule using documented `prefix_rule(...)` declarations whose patterns match the
  mandated venv-path invocation form (`.dadaia/.venv/bin/dadaia ...`), proven by
  real-form `match=` examples. Markdown files under `public/rules/*.md` remain
  behavioral protocols and are not projected as executable Codex Rules.
- `.codex/hooks.json` with a SINGLE `PreToolUse` command (anchored matcher
  `^(apply_patch|Edit|Write|Bash)$` → `dadaia_workspace.hooks.pre_gate`),
  `PostToolUse` (match-all), and `UserPromptSubmit`/`SessionStart` entries.
  **Honesty boundary (live-verified, codex-cli 0.139.0):** Codex executes command
  hooks ONLY in interactive (TUI) sessions — `codex exec` (headless) never fires
  them, so hook enforcement on Codex is interactive-only and the headless
  automation path is **chokepoints only**: the git pre-commit lease gate and the
  pre-push CI/security-verdict gate fire regardless of harness hooks (constitution
  §8 enforcement matrix). Live contract harness: `tests/integration/codex_live/`
  (opt-in `DADAIA_CODEX_LIVE=1`).
- workflows installed as reference docs; workflow Markdown does not auto-execute.
- dispatch wording based on Codex custom agents, never fake tool names or stale
  tool-discovery promises.

Hook scripts prefer `.dadaia/.venv/bin/python` and fall back only when the
workspace venv is absent.

Claude Code receives the canonical agent bodies, Claude-native frontmatter,
skills, commands, hooks, and rules. Claude remains the strongest hook/runtime
reference, but shared docs must not assume Claude-only mechanisms exist in
Codex or PI.

(OpenCode was removed entirely in v0.1.24 — no `.opencode/` projection, no
`public/plugins/sdd-gate.ts`, no `opencode` install target. The only remaining shell
asset in the product is the `pre-push-ci-gate.sh` git chokepoint.)

PI receives a `.pi/` projection (`SYSTEM.md`, `settings.json`,
`prompts/dadaia-context.md`, and `extensions/dadaia-sdd-gate.ts`) via `dadaia public
install --target pi`. PI reads `AGENTS.md`/`CLAUDE.md` natively up the tree, so workspace
law rides for free; post-v0.1.21 (WS-PI-4) the `.pi/extensions/dadaia-sdd-gate.ts`
extension adds a real Layer-1 **Ring-1** pre-disk gate — its `tool_call` handler maps
write→Write/edit→Edit and delegates to the same Python `pre_gate` the other harnesses use,
returning `{block:true}` on an SDD block, fail-open otherwise. The extension carries **no
policy restatement** (policy lives only in Python) and no secrets/operator-local paths.
`.pi/**` is post-trust executable TypeScript when PI loads it — a deliberate operator
privilege grant, never hand-edited — so the Ring-1 block is active once the operator
trusts `.pi/` (the upstream trust seam; live efficacy verified on a trusted interactive
run, the same class as the `pi --mode json` live test).

## Estado runtime tocado

`dadaia public doctor` is the source of truth for projection state. It reports:
- `.claude/agents/`: exactly 9 agent files; no orphan files from deleted personas.
- `.codex/agents/`: TOML agent files with no fake model-derived skill names.
- `.codex/rules/`: native `.rules` command policy and no Markdown protocol masquerading
  as executable rules.
- `.claude/skills/`, `.agents/skills/`: 18 skill directories.
- Codex workflows as reference-only, not missing runtime behavior.
- No `.opencode/` projection and no opencode manifest entry (OpenCode removed in v0.1.24).
- All staged SHA256 hashes match projected files (`[ok]` for every asset; `[drift]` on mismatch).

`dadaia public install --target all` propagates source → all runtimes (`{agents, claude,
codex, pi}`; `--target opencode` errors with an unknown-target message); no `--force`
needed for ordinary source edits (plain install overwrites on hash mismatch). `--force`
is only for clobbering a locally-diverged projection.
