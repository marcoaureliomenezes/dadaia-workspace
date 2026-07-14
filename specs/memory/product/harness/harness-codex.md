---
slug: harness-codex
title: Harness — Codex
category: product
tldr: 'Dual-layer harness: Layer-1 TUI (deterministic hooks) vs headless exec (chokepoints only); Layer-2 CODEX_EXEC worker; scaffold = .codex/ projection.'
summary: Capability and scaffold truth for the Codex harness at both agentic layers —
  interactive vs headless enforcement asymmetry, the CODEX_EXEC worker transport,
  content-delta changed-path attribution, bytecode-suppression environment preservation,
  model catalog, and what a Codex-only workspace installation contains.
tags:
- harness
- codex
- layer-1
- layer-2
- projection
token_estimate: 980
last_updated: '2026-07-14'
release_origin: v0.2.5
---

## Purpose

Codex is a **dual-layer** harness. Layer 1: the operator's `codex` TUI, governed by
`AGENTS.md` read natively up-tree plus the `.codex/` projection. Layer 2: the
`CODEX_EXEC` worker — `codex exec` driven headless by a dadaia-workflow, one-shot per
step, bounded by Ring-2 (git-diff `changed_paths`) + the git chokepoints. In a Codex
entry session, dadaia-workflows are the preferred execution path, defaulting the
Layer-2 harness to `codex` unless the operator overrides to `pi`. **Entry signal
(v0.1.64):** a present `CODEX_SESSION_ID` auto-defaults every `dadaia lifecycle` verb's
`--harness` to `codex` (a `DADAIA_ENTRY_HARNESS` pin beats it; an explicit flag always
wins; every real-worker auto-default prints the loud `[harness] auto-default:` echo —
a stale id inherited from a parent shell could auto-spend codex credits, mitigated by
the echo, the pin, and explicit `--harness fake`).

## Usage flow

1. Operator launches `codex` at the workspace root; `AGENTS.md` loads natively;
   `SessionStart` ctx-inject loads the bound context once per session.
2. Interactive sessions get the deterministic gate: PreToolUse `pre_gate` (matcher
   `^(apply_patch|Edit|Write|Bash)$`) + matcher-less PostToolUse heartbeat, registered
   in `.codex/hooks.json` via self-locating wrappers under `.dadaia/hooks/codex-*`.
3. **Headless asymmetry (honesty):** `codex exec` fires NO hooks (upstream codex-cli
   defect, live-verified) — headless enforcement is chokepoints-only. The live
   verification harness is `tests/integration/codex_live/` (opt-in
   `DADAIA_CODEX_LIVE=1`): it drives a real Codex binary against a throwaway trusted
   workspace under `.dadaia/tmp/` and re-proves these contract facts repeatably.
4. As a Layer-2 worker: the engine builds the exec argv (model `(id, effort)` discrete;
   no approval flag — exec never prompts), preserves the non-secret
   `PYTHONDONTWRITEBYTECODE` control in the subprocess environment allowlist, pipes the
   fragment+persona prompt, extracts the result via the shared strict-schema-first
   extraction, and returns Git-derived content-delta `changed_paths` rather than trusting
   model self-report.
5. **Trust + sandbox posture (v0.1.66, FR4/FR5).** `CodexExecAdapter._command` includes
   `--skip-git-repo-check` unconditionally alongside `--ignore-user-config`, so a
   governed worker never fails codex's own "Not inside a trusted directory" trust
   check when driven from an untrusted-by-codex working directory (the outer
   `dadaia lifecycle` gate — not codex's own trust flag — is the real access boundary,
   same reasoning as the `--ignore-user-config` precedent). `CodexExecConfig`'s
   `sandbox` value is resolvable via the `DADAIA_CODEX_SANDBOX` environment variable,
   read once at `__post_init__` (the single choke point every construction path
   passes through): an explicit caller-supplied `sandbox=` always wins over the env
   var; the resolved value — whether from the caller or the env — is always validated
   against `{read-only, workspace-write, danger-full-access}` (an unrecognized value
   raises at construction, never passed through blind to `codex exec`); the
   compiled-in default stays `read-only` when the env var is unset (no silent security
   posture downgrade for operators who never set it). The override exists because the
   `read-only` default's underlying sandbox mechanism (`bwrap`) can fail inside
   constrained containers ("loopback: Failed RTM_NEWADDR: Operation not permitted");
   `danger-full-access` is the confirmed bwrap-free unblock for that case.

## Typical trigger

Layer 1: operator preference for the Codex TUI. Layer 2: every dadaia-workflow step
whose governed harness resolves to `codex` (model catalog: `(gpt-5.5, high)`,
`(gpt-5.5, medium)`).

## Differentiator

Runs on the operator's Codex subscription. Command policy is expressed natively as
Starlark `.codex/rules/*.rules` (prefix rules, venv-form paths) — not in config keys.
The interactive/headless enforcement split is the key operational fact: never assume a
hook fired in an exec run.

## Runtime state touched

Scaffold projected by `dadaia public install --target codex`: `.codex/config.toml`
(header + per-agent config blocks only — no inert keys), `.codex/hooks.json`,
`.codex/agents/` (12 TOML personas — tier identity is Codex-native
`(model id × model_reasoning_effort)`, registry-derived via
`core/model_registry.codex_tier_views()`: deep→high, dispatch→medium reasoning
effort, and rendering fails loudly when two tiers collapse to one `(id, effort)`
pair; doctor lint D-CX-4 blocks Anthropic tier names (Opus/Sonnet/Haiku) and Claude
model/path/tool-name leaks in Codex-projected artifacts), `.codex/rules/`
(Starlark command policy), `.codex/skills/` (context adapters), `.codex/workflows/`
(reference-only). Wrappers in `.dadaia/hooks/codex-*`. `DADAIA_CODEX_SANDBOX`
(operator-set process env var, v0.1.66) overrides the Layer-2 `CODEX_EXEC` worker's
sandbox default — not a projected file, an env-var input read at adapter construction.
A Codex-only workspace = `--target codex` (+ shared `--target agents`). This isolation
is now **enforced mechanically at init** — `dadaia init --harness codex` scaffolds
only the `.codex/` surface + the `.dadaia/hooks/codex-*` wrappers and persists the
profile ([[workspace-init]]) — not merely documented.

## Dependencies

- [[tech-stack]] — roster + model catalog single source.
- [[lifecycle-foundation]] — the engine that drives the CODEX_EXEC worker.
- [[sdd-gate-v3]] — gate + chokepoint mechanism, incl. the headless asymmetry.
- [[public-asset-distribution]] — the `.codex/` projection pipeline.
