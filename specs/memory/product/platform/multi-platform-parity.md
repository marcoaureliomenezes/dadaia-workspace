---
slug: multi-platform-parity
title: multi-platform-parity
category: product
tldr: "Claude Code, Codex, and PI get honest runtime-specific projections from one public source (9 core agents / 18 skills / 2 reference workflow docs)."
summary: Codex uses native config, shared and Codex-specific skills, interactive-only
  hook execution (codex exec never fires hooks — headless posture is chokepoints-only),
  native Starlark .rules command policy with venv-path prefix_rule patterns, workflow
  docs that do not auto-execute, read-only sandbox for evidence-only reviewers, and
  registry-derived Codex-native model tiering (model id × model_reasoning_effort). All
  harnesses are protected by the git chokepoints (pre-commit lease gate + pre-push
  security-verdict gate), which fire independently of harness hooks. The Layer-1
  entry-harness set is exactly {claude, codex, pi}. PI projects a minimal `.pi/`
  surface and is Layer-1-governed via AGENTS.md natively plus a post-trust Ring-1
  SDD-gate extension (.pi/extensions/dadaia-sdd-gate.ts → pre_gate). Public surface is
  9 core agents + 3 plugin stubs, 18 skills, 2 reference workflow docs.
tags:
- codex
- claude-code
- pi
- parity
- multi-platform
agent_tier: self-pull
token_estimate: 1600
last_updated: '2026-07-02'
release_origin: v0.1.48
---

## Purpose

Multi-platform parity means the same canonical public assets are projected to
Claude Code, Codex, and PI without pretending the runtimes are identical. Each
projection must be truthful about the runtime's native concepts, supported hooks,
config loading, workflow support, and skill discovery. The Layer-1 entry-harness set is
exactly `{claude, codex, pi}` (roster single-source: [[tech-stack]] §Agent runtimes).

### Two-layer scope: projection-parity vs worker-runtime parity

This atom is about **Layer-1 projection parity** — how one canonical source projects
into the entry harnesses the operator launches. It must not be read as the full harness
set. dadaia-workspace runs harnesses at two layers (see [[architecture]] "Two-layer
agentic model"):

- **Layer 1 (this atom) — entry-harness projection parity.** Source
  (`dadaia_workspace/public/`) → `.claude/`, `.codex/`, `.pi/` asset trees via
  `dadaia public install` (targets `{agents, claude, codex, pi}`). Each tree is
  truthful about its runtime. PI's `.pi/` projection (target `pi`) is **minimal** —
  `.pi/SYSTEM.md` POINTS AT `AGENTS.md` (no law restatement); the `.pi/` surface
  inventory is owned by [[public-asset-distribution]].
- **Layer 2 — worker-runtime parity (NOT projection parity).** The lifecycle engine's
  per-step worker harnesses behind `AgentRuntimePort` (the four-member
  `AgentRuntimeKind` roster is single-sourced in [[tech-stack]] §Agent runtimes). These
  have **no projection tree** — they are subprocess/SDK adapters selected per step,
  governed by `--harness`, not by `.X/` asset projection. **LAW 1:** the selectable
  Layer-2 **workflow** harnesses are exactly `{pi, codex, fake}`; `CLAUDE_SDK` is
  kept/tested but `claude` is rejected as a workflow `--harness` (Layer-1 use only).
  [[lifecycle-foundation]] is the normative source for Layer 2.

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
| Skills | 18 | shared literacy + role-restricted skills |
| Reference workflow docs | 2 | release-ship, audit-fanout — Layer-1 documentation only; the 7 executable dadaia-workflows live in the engine's governed catalog ([[dadaia-workflows]]) |
| Rules | 8 | workspace-protocol, tmp-file-guardrail, plugin-scope, dadaia-workspace-dev-guardrail, harness-skill-scope, bug-registration-guardrail, backlog-ownership, release-governance |
| Personas | 8 | Layer-2 role mandates (one per non-PM core role) |

Plugin stubs (`frontend-engineer`, `design-specialist`, `devops-engineer`) project as
empty stubs — no behavior until the corresponding plugin is installed.

## Usage flow

Codex receives:

- `AGENTS.md` as the automatically loaded workspace rule surface.
- `.codex/config.toml` containing `[agents."<name>"] config_file = "agents/<name>.toml"`
  entries for all projected agents — `config_file` is a real, live-verified config
  key. The file carries **no inert keys**: the former `approved_commands` array and
  `[skills] paths` table (both live-verified INVALID in codex-cli 0.139.0) are no
  longer emitted; Codex discovers skills natively from `.codex/skills`/`.agents/skills`.
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
- `.codex/hooks.json` hook registration via the `.dadaia/hooks/codex-*` wrappers —
  wrapper and matcher registration mechanics are owned by [[public-asset-distribution]].
  **Honesty boundary (live-verified, codex-cli 0.139.0):** Codex executes command
  hooks ONLY in interactive (TUI) sessions — `codex exec` (headless) never fires
  them, so hook enforcement on Codex is interactive-only and the headless
  automation path is **chokepoints only**: the git pre-commit lease gate and the
  pre-push CI/security-verdict gate fire regardless of harness hooks. Live contract
  harness: `tests/integration/codex_live/` (opt-in `DADAIA_CODEX_LIVE=1`).
- workflows installed as reference docs; workflow Markdown does not auto-execute.
- dispatch wording based on Codex custom agents, never fake tool names or stale
  tool-discovery promises.

Hook scripts prefer `.dadaia/.venv/bin/python` and fall back only when the
workspace venv is absent.

Claude Code receives the canonical agent bodies, Claude-native frontmatter, skills,
rules, workflows, and hook registration in `.claude/settings.json`. Claude remains the
strongest hook/runtime reference, but shared docs must not assume Claude-only
mechanisms exist in Codex or PI. The only shell assets in the product are the two git
chokepoints (`pre-commit-lease-gate.sh`, `pre-push-ci-gate.sh`).

PI receives the `.pi/` projection via `dadaia public install --target pi` (surface
inventory: [[public-asset-distribution]]).
PI reads `AGENTS.md`/`CLAUDE.md` natively up the tree, so workspace
law rides for free; the `.pi/extensions/dadaia-sdd-gate.ts`
extension adds a real Layer-1 **Ring-1** pre-disk gate — its `tool_call` handler maps
write→Write/edit→Edit and delegates to the same Python `pre_gate` the other harnesses use,
returning `{block:true}` on an SDD block, fail-open otherwise. The extension carries **no
policy restatement** (policy lives only in Python) and no secrets/operator-local paths.
`.pi/**` is post-trust executable TypeScript when PI loads it — a deliberate operator
privilege grant, never hand-edited — so the Ring-1 block is active once the operator
trusts `.pi/` (the upstream trust seam; live efficacy verified on a trusted interactive
run, the same class as the `pi --mode json` live test).

## Runtime state touched

`dadaia public doctor` is the source of truth for projection state. It reports:
- `.claude/agents/`: 12 agent files (9 core + 3 plugin stubs); no orphan files from
  deleted personas.
- `.codex/agents/`: TOML agent files with no fake model-derived skill names.
- `.codex/rules/`: native `.rules` command policy and no Markdown protocol masquerading
  as executable rules.
- `.claude/skills/`, `.agents/skills/`: 18 skill directories.
- Codex workflows as reference-only, not missing runtime behavior.
- All staged SHA256 hashes match projected files (`[ok]` for every asset; `[drift]` on mismatch).

`dadaia public install --target all` propagates source → all runtimes (`{agents, claude,
codex, pi}`; an unknown target errors). Hash-compare overwrite and `--force` semantics
are owned by [[public-asset-distribution]].
