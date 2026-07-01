# Codex Runtime Fidelity Review

- **Auditor:** ai-engineer (READ mode, ADDITIVE audit channel)
- **Date:** 2026-06-12T001813Z
- **Scope:** Everything `dadaia public install --target codex` projects into an instantiated workspace, judged against what Codex (OpenAI) discovers and honors natively by default.
- **Lenses:** `ai-harness-codex` skill (primary), academy course `07_codex/*` (secondary, itself audited).

## Executive verdict

**The Codex projection is substantially faithful — it targets real Codex primitives, not Claude shadows.** Skills (`.agents/skills` + `[skills] paths`), custom-agent TOMLs (correct required/optional fields, role-boundary sandbox modes, registry-mapped models, zero `claude-*` ids), Starlark `prefix_rule` command policy, and the hooks.json event wiring all match the documented Codex contract, and the D-CX-1..10 doctor suite actively defends that parity. The academy course is accurate and consistent with the harness skill.

**Three structural risks remain:**

1. **Enforcement is unproven on the current wiring (F-1, HIGH/UNVERIFIED).** The SDD gate's actual blocking on Codex depends on an anchored-regex matcher, a Claude-style `{"decision":"block"}` stdout envelope, and shell-executed env-prefixed commands — none verified against a live Codex binary since the v0.1.10 Python-hook rewrite, and all of it silently absent in an untrusted workspace (F-3).
2. **The markdown protocol corpus is Claude-only (F-2, HIGH).** Codex sessions never load `workspace-protocol`, `release-governance`, etc., yet root AGENTS.md and every agent TOML cite them by name — dangling references on the runtime that needs them most.
3. **A tail of inert/wrong artifacts:** untransformed `description` Claude-ism on project-manager (F-4), `dadaia` command rules that can never match the mandated venv invocation (F-5), likely-inert `approved_commands` (F-6), adapter skills claiming auto-fire semantics Codex doesn't have (F-7), inert `.codex/workflows/` (F-9), and a stale roster lint (F-10).

**Counts:** 2 HIGH (1 unverified), 5 MEDIUM, 5 LOW, 1 INFO. 3 product-bug candidates, 5 backlog candidates. First action: WS-CDX-VERIFY — one live trusted-Codex smoke run resolves every UNVERIFIED cell and decides whether F-1 is a non-issue or the most important bug in the projection.

## Codex native contract (checklist derived from skill + academy)

What Codex discovers and honors BY DEFAULT:

| # | Surface | Native contract |
|---|---|---|
| C1 | AGENTS.md | Discovered globally (`~/.codex/AGENTS.md`) then project root → CWD; one file per dir (`AGENTS.override.md` preferred); later/closer wins; combined size capped by `project_doc_max_bytes`. Advisory text, not enforcement. |
| C2 | config.toml | User layer `~/.codex/config.toml` always; project `.codex/config.toml` only when project is TRUSTED. Sensitive keys (provider, base URLs, auth, telemetry, notify, profiles) are ignored/forbidden project-locally. |
| C3 | Hooks | `.codex/hooks.json` (project layer, trusted only). Events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, PostCompact, SubagentStart, SubagentStop, Stop. Only `command` handlers execute today. `UserPromptSubmit` and `Stop` ignore matchers. Multiple matching hooks may run in parallel. |
| C4 | Rules | Starlark `.rules` files under `rules/` next to an active config layer. Documented unit: `prefix_rule(pattern, decision, justification, match, not_match)`. Decisions: allow/prompt/forbidden; most restrictive wins. Command policy ONLY — Markdown in `.codex/rules/` is inert. |
| C5 | Skills | Folder with `SKILL.md`; frontmatter `name` + `description` is the trigger surface; body loaded on use. Repo discovery: `.agents/skills` from CWD up to repo root, plus configurable `[skills] paths`. Unknown frontmatter keys ignored. |
| C6 | Custom agents | TOML under `~/.codex/agents/` or `.codex/agents/`. Required: `name`, `description`, `developer_instructions`. Optional: `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, skills config. Makes a role SPAWNABLE; never auto-routes prompts. Subagents spawn only on explicit delegation request. |
| C7 | Workflows | NO native Codex concept of `*.workflow.md`. Any projected workflow markdown is reference text at best, and only if something actually loads it into context. |
| C8 | Model config | Model selection comes from user config / agent TOML `model` key; ids must be valid for the operator's Codex provider. |

## Per-surface gap table

| Surface | Codex native default | What dadaia projects | Verdict | Evidence |
|---|---|---|---|---|
| Root + repo `AGENTS.md` | Discovered natively, root→CWD chain at session start (C1) | `public/data/AGENTS.md` → workspace root + every `repos/<slug>/AGENTS.md` (`install_helpers.py:89-99,260-266`) | **WORKS** | Root file is generic, Codex-readable; CLAUDE.md bridge is Claude-only and harmless |
| Scoped `AGENTS.md` (`.dadaia/reports\|handoff\|tmp\|states/`, `specs/`) | Loaded only if session CWD is inside that dir; NOT loaded on file access mid-session (C1; academy 02 "discovery happens at run/session start") | Installed by `install_reports_agents_md` etc. (`install_helpers.py:102-146`) | **PARTIALLY WORKS** | On Codex these are discipline docs the agent must read on instruction from root AGENTS.md ("Scoped Rules" section); never auto-honored |
| Markdown rule corpus (`public/rules/*.md` → `.claude/rules/`) | No Codex equivalent; `.md` in `.codex/rules/` would be inert (C4) | Projected ONLY to `.claude/rules/`; nothing Codex-visible. Root AGENTS.md and agent TOMLs reference rules by name (`workspace-protocol` §4, `backlog-ownership`, `tmp-file-guardrail`, `harness-skill-scope`) | **INERT on Codex** (F-2) | `transform_for_codex` rewrites only the one literal path `.claude/rules/workspace-protocol.md` (`codex.py:38`); name-only references survive untransformed (e.g. `.codex/agents/ai-engineer.toml` body cites "workspace-protocol rule §4") |
| `config.toml` `[skills] paths` | Skill search path config (skill §6 table) | `paths = [".agents/skills", ".codex/skills"]` (`runtime_config.py:144-147`) | **WORKS** | Matches native `.agents/skills` discovery anyway — belt and braces |
| `config.toml` `[agents."<n>"] config_file` | Custom agents natively discovered as `.codex/agents/*.toml` (C6); the `config_file` indirection key is not attested in skill/academy | One block per agent (`codex_assets.py:245-275`); instance has 12 | **UNVERIFIED** (F-8) | If the key is unsupported it is harmless (dir discovery covers it); if dir discovery requires registration, it is load-bearing — needs live test |
| `config.toml` `approved_commands` | Not a documented current Codex config key in skill/academy/REFERENCES; command approval is owned by Rules (C4) | 10-entry list (`runtime_config.py:123-136`) | **INERT (likely)** (F-6) | Unknown keys are ignored; the list misleads readers into thinking approval policy lives here |
| `hooks.json` | Trusted-project command hooks; events per C3; PostToolUse match-all = omitted matcher; SessionStart matcher `startup\|resume`; only command handlers run | `runtime_config.py:150-237`: PreToolUse `^(apply_patch\|Edit\|Write)$` → sdd_gate + root_whitelist; PostToolUse no-matcher → sdd_post_gate; SessionStart + UserPromptSubmit → ctx_inject with `DADAIA_HOOK_OUTPUT=codex-json` env-prefix | **PARTIALLY WORKS / UNVERIFIED** (F-1, F-3) | Structure matches the skill's reference wiring; 3 contract points unverified (anchored regex matcher, `{"decision":"block"}` envelope, shell-exec of env-prefixed command strings); everything is dead in an untrusted workspace |
| `.codex/rules/dadaia-command-policy.rules` | Starlark `prefix_rule`, most-restrictive-wins, conservative shell splitting (C4) | Generated `prefix_rule(...)` set (`codex_assets.py:191-242`); doctor D-CX-8 guards shape | **PARTIALLY WORKS** (F-5) | Shape is documented-correct; but the two `dadaia` rules can never fire — the workspace convention invokes `.dadaia/.venv/bin/dadaia` (bare `dadaia` is off-PATH), and a prefix pattern `["dadaia", ...]` does not match an absolute-path argv0 |
| Skills (`.agents/skills/**`) | Native repo discovery CWD→root + metadata-first progressive disclosure (C5); unknown frontmatter keys ignored | `install_universal_skills` → `.agents/skills` (`install_helpers.py:149-170`); frontmatter is `name`+`description`(+`applyTo`, ignored by Codex) | **WORKS** | Sampled `dadaia-task-manager`, `harness-primitives`: Codex-compatible. `harness-skill-scope` restriction is discipline-only on Codex (same as Claude) |
| Codex adapter skills (`.codex/skills/{memory,design,frontend}-ctx`) | Skills load only when the model selects them; nothing "fires" automatically (C5) | `install_codex_runtime_adapters` (`install_helpers.py:420-441`); doctor D-CX-6 guards no-leak | **PARTIALLY WORKS** (F-7) | `memory-ctx` description claims "Fires before all role-specific adapters... Injects ... into every Codex session" — false per contract; actual injection is the SessionStart ctx_inject hook, making the adapter largely redundant |
| Agent personas (`.codex/agents/*.toml`) | TOML custom agents: required `name`/`description`/`developer_instructions`; optional `model`, `model_reasoning_effort`, `sandbox_mode`; spawnable only on explicit delegation (C6) | `install_codex_agents` + `_render_codex_agent_toml` (`install_helpers.py:355-417`, `codex_assets.py:145-188`): all required + valid optional fields; reviewers read-only sandbox; body via `transform_for_codex`; model via registry map | **WORKS** (with F-4) | 12 TOMLs present, parse clean, models `gpt-5.5`×9 / `gpt-5.3-codex`×3, no `claude-*` ids. The `description` field bypasses the transform → Claude-ism leak (F-4). No auto-routing — correct per contract, surfaced honestly by academy 05 |
| Workflows (`.codex/workflows/*.workflow.md`) | No native concept (C7) | Copied verbatim; doctor labels `[reference-only] codex:... (installed, no workflow executor)` (`codex_doctor.py:449-465`) | **INERT** (F-9) | Honest labeling; still dead weight nothing on Codex ever loads |
| Model mapping | Model ids must be valid for the operator's provider (C8) | `MODEL_MAP` derived from `core/model_registry.py`; `map_model` raises on unknown (`model_mapping.py:23-41`); doctor D-CX-4 forbids `claude-*` leftovers | **WORKS** | Registry-derived, fails loudly, verified clean on instance |
| Doctor coverage | n/a | D-CX-1..10 + D-CX-SKILLS + SINGLE-SRC-1 (`codex_doctor.py`) | **WORKS, with gaps** (F-4, F-10) | Strong parity suite; blind to `description`-field Claude-isms, carries a stale roster lint, never asserts Codex project trust |

## Findings

### F-1 — HIGH / UNVERIFIED — SDD-gate enforcement on Codex rests on three unverified contract points
The deterministic write gate works on Codex only if ALL of these hold: (a) Codex PreToolUse matchers accept the anchored regex `^(apply_patch|Edit|Write)$` (`runtime_config.py:154`; the skill's documented reference wiring is the bare `apply_patch|Edit|Write` form); (b) Codex honors the Claude-style stdout envelope `{"decision":"block","reason":...}` emitted by `_common.emit_block` (`hooks/_common.py:119-121`) — the gate exits 0, so if Codex keys denial on exit code 2 or a different JSON schema, every block becomes a silent allow; (c) Codex executes hook `command` strings through a shell, otherwise the env-prefixed `DADAIA_HOOK_OUTPUT=codex-json python -m ...` ctx_inject commands fail to exec at all. Historical live evidence (a gate block reproduced in a Codex session, v0.1.7 era) predates the v0.1.10 Python-hook rewiring, so it does not certify the current shape. Failure mode is the worst kind: silent no-op while the workspace believes "deterministic enforcement" exists.
**Fix:** live Codex verification harness (attempt a FROZEN `specs/_archive/` write via apply_patch in a trusted workspace; assert block + marker file from each hook) + align the matcher with the skill's documented form. **Class:** backlog (verification workstream) — not yet a reproducible break.

### F-2 — HIGH — The markdown rule corpus is invisible to Codex while referenced everywhere
`public/rules/*.md` (workspace-protocol, release-governance, tmp-file-guardrail, plugin-scope, harness-skill-scope, backlog-ownership, bug-registration-guardrail, dadaia-workspace-dev-guardrail) project only to `.claude/rules/`. Codex never loads them (C4: `.md` is not Codex Rules; no other Codex surface carries them; ctx_inject injects memory bootstrap only — `hooks/ctx_inject.py:1-10`). Yet root AGENTS.md says "See `workspace-protocol` rule for the full context-resolution procedure" and agent TOML bodies cite rules by name (e.g. ai-engineer.toml "workspace-protocol rule §4", project-manager "rule: `backlog-ownership`"). `transform_for_codex` rewrites only the single literal path string (`codex.py:38`). Mitigation today: root AGENTS.md inlines summaries of most law, and a Codex agent CAN read `.claude/rules/*.md` from disk if it thinks to; but nothing tells it where the named rules live.
**Fix direction:** either (i) transform name-references into explicit on-disk paths Codex agents are instructed to read, (ii) project the rule corpus to a Codex-visible docs dir referenced from root AGENTS.md, or (iii) fold load-bearing rule content into the AGENTS.md layer / a skill. **Class:** backlog (design gap), candidate flagship item.

### F-3 — MEDIUM — Codex trust gating is undetected and undocumented at the instance surface
Project-local config, hooks, and Rules load **only when the project is trusted** (C2/C3). In an untrusted Codex workspace the entire governance surface (SDD gate, heartbeat, ctx-inject, command policy) silently does not exist. No onboarding step, doctor check, or instance doc asserts/verifies Codex trust; `dadaia public doctor` reports `[ok] codex:hooks.json` for a file Codex may never load.
**Fix:** onboarding note + a doctor INFO line ("Codex governance requires project trust — verify in a live session"); a probe-hook (SessionStart writing a marker) would make trust observable. **Class:** backlog.

### F-4 — MEDIUM — Agent TOML `description` bypasses `transform_for_codex` → Claude-ism leaked to the spawn-trigger surface
`install_codex_agents` transforms the body but passes frontmatter `description` through raw (`install_helpers.py:393-401`). Result on instance: `project-manager.toml:2` description says "dispatches sub-agents via Agent tool" — a Claude Code tool name on the very field Codex uses to select a spawnable role. Doctor D-CX-4 is blind to it (checks only `claude-*` model ids and `.claude/rules/` paths, `codex_doctor.py:27-30,155`).
**Fix:** run descriptions through the same replacement table; extend D-CX-4 with an "Agent tool / `Agent`" pattern. **Class:** PRODUCT BUG (reproducible contract break of the no-Claude-isms invariant, AC3 spirit).

### F-5 — MEDIUM — The `dadaia` command-policy rules can never fire as written
`.codex/rules/dadaia-command-policy.rules` gates `["dadaia","public","install"]` and `["dadaia","context","dead"]` — but the workspace convention (root AGENTS.md, shell-hygiene memory) is to invoke `.dadaia/.venv/bin/dadaia` because bare `dadaia` is intentionally off-PATH. A prefix rule on argv0 `dadaia` does not match an absolute-path argv0, so the two highest-value prompts never trigger. Secondary nit: `git commit` appears in a `not_match` example but no rule governs it.
**Fix:** add patterns for the venv-path invocation form (or gate on a wrapper), and prove with `match=` examples using the real invocation. **Class:** PRODUCT BUG (policy demonstrably cannot match the documented invocation form).

### F-6 — MEDIUM / UNVERIFIED — `approved_commands` in generated config.toml is (likely) an inert, misleading key
`runtime_config.py:123-136` emits a 10-command `approved_commands` list. The key is absent from the skill's config-layer model, academy lesson 04, and the REFERENCES config pages' surveyed surface; command approval is owned by Rules. Codex ignores unknown keys, so this is probably dead weight that misleads operators about where approval policy lives (the exact confusion the naming-collision section warns about).
**Fix:** verify against the live config reference; remove or replace with Rules. **Class:** backlog (verify-then-remove).

### F-7 — MEDIUM — Codex adapter skills assert auto-fire semantics that do not exist
`.codex/skills/memory-ctx/SKILL.md` description: "Fires before all role-specific adapters... Injects tech-stack and feature catalog into every Codex session." Skills never fire automatically and have no ordering (C5); the actual once-per-session injection is the SessionStart ctx_inject hook — which makes the adapter redundant where the hook runs, and a false promise where it doesn't. design-ctx/frontend-ctx carry the same pattern.
**Fix:** reword as on-demand bootstrap procedures ("Use when the session lacks workspace context...") or retire in favor of the hook. **Class:** backlog.

### F-8 — LOW / UNVERIFIED — `[agents."<name>"] config_file` indirection unattested
Neither skill nor academy attests the `config_file` key. If unsupported, agents are still discovered via `.codex/agents/` (C6) and the blocks are harmless; if directory discovery alone is insufficient in some Codex versions, the key is load-bearing. **Fix:** live verify; document the outcome in the skill. **Class:** backlog (verification).

### F-9 — LOW — Workflows projected into `.codex/workflows/` are pure dead weight
No Codex surface reads `*.workflow.md` (C7). Doctor labels them `[reference-only]` honestly (`codex_doctor.py:463`), and they are also installed to `.agents/workflows/`. The `.codex/workflows/` copy duplicates an already-inert artifact. **Fix:** decide — keep for symmetry or stop projecting to `.codex/`. **Class:** backlog.

### F-10 — LOW — Stale T-35 lint inverts the current roster
`lint_legacy_software_engineer` (`codex_doctor.py:425-446`, regex `codex_assets.py:31-34`) flags `subagent_type: software-engineer` and tells authors to use `software-engineer-python|node` — names deleted in the 15→9 agent consolidation; `software-engineer` IS the canonical implementer. Currently dormant (no literal in `public/`), but the first public asset that legitimately writes `subagent_type: software-engineer` gets a wrong doctor error with a dead-name remedy. **Fix:** delete the lint (or invert it). **Class:** PRODUCT BUG (dormant, deterministic misfire).

### F-11 — LOW — Scoped AGENTS.md semantics differ on Codex (CWD-chain, not file-access)
`specs/AGENTS.md` and the `.dadaia/**/AGENTS.md` set load on Codex only when the session starts inside those dirs — unlike Claude Code path-scoped rules. Root AGENTS.md's "Scoped Rules — before editing, check for the nearest scoped rule file" instruction is the (adequate) discipline mitigation. **Fix:** none required; record the delta in `harness-primitives`/onboarding so authors stop assuming Claude semantics. **Class:** backlog (doc note).

### F-12 — LOW — Stale RULE-D docstring + ambient artifact
`codex_assets._parse_write_allowlist` docstring (`codex_assets.py:379-382`) still says agents.index.json feeds "the SDD gate's RULE D" — removed in 0.1.7 rc-3; the index is now consumed by `features/reports_next/service.py:23`. Doc-only drift. **Class:** backlog (cleanup).

### F-13 — INFO — Live instance drift (not a Codex defect)
`dadaia public doctor` currently exits 1: `[drift] stage:workflows/audit-fanout.workflow.md` (source edited, not restaged). All codex-family lines are `[ok]`/`[reference-only]`. This is the doctor contract working; repair is `dadaia public stage && dadaia public install --target all` (operator/devops).

## Bug candidates vs backlog candidates

**PRODUCT BUG candidates** (reproducible contract breaks — coordinator to file in `repos/dadaia-workspace/specs/bugs/`):

| Slug suggestion | Finding | Severity |
|---|---|---|
| `codex-agent-description-claude-ism-leak` | F-4 — description field bypasses transform; "Agent tool" in project-manager.toml; D-CX-4 blind | MEDIUM |
| `codex-rules-dadaia-prefix-never-matches-venv-invocation` | F-5 — prefix rules on bare `dadaia` vs mandated `.dadaia/.venv/bin/dadaia` invocation | MEDIUM |
| `stale-legacy-software-engineer-lint-inverts-roster` | F-10 — T-35 lint forbids the canonical implementer name, remedy names dead agents | LOW |

**Backlog candidates** (gaps / improvements):

| Slug suggestion | Findings |
|---|---|
| `codex-live-contract-verification-harness` | F-1, F-6, F-8 — one live trusted-Codex smoke run converting all UNVERIFIED cells to facts (matcher regex, block envelope, shell-exec env-prefix, config_file key, approved_commands) |
| `codex-visible-protocol-corpus` | F-2, F-11 — make the markdown rule law reachable from Codex sessions; fix dangling name-references |
| `codex-trust-model-surfacing` | F-3 — onboarding + doctor visibility for the trusted-project precondition |
| `codex-adapter-skills-rework` | F-7 — reword or retire memory/design/frontend-ctx adapters |
| `codex-projection-pruning` | F-9, F-12 — workflows-in-.codex decision, stale docstrings, approved_commands removal (post-verify) |

## Recommended release workstreams (ordered)

1. **WS-CDX-VERIFY** (small, highest leverage): live trusted-Codex smoke harness — probe hooks that write markers on each event + an attempted FROZEN write via `apply_patch` + config-key probes. Converts F-1/F-6/F-8 from UNVERIFIED to facts; everything downstream depends on these answers. Also align the PreToolUse matcher with the skill's documented bare form while at it.
2. **WS-CDX-BUGFIX** (small): F-4 description transform + D-CX-4 extension; F-5 rules patterns for the venv invocation; F-10 lint deletion. All mechanical, test-backed.
3. **WS-CDX-PROTOCOL** (medium): F-2/F-11 — design where the rule corpus lives for Codex (AGENTS.md fold-in vs readable path references vs skill), then retransform agent bodies. Touches `transform_for_codex`, `public/data/AGENTS.md`, possibly every persona — release-governed fleet change.
4. **WS-CDX-HYGIENE** (small): F-3 trust surfacing, F-7 adapter rework, F-9 workflows decision, F-12 doc cleanup, drop `approved_commands` if WS-1 confirms inert.

---

## Audit notes — academy course accuracy

The academy course `07_codex/01..05 + REFERENCES` was read in full and cross-checked
against the `ai-harness-codex` skill:

- Lessons 01–05 are **accurate and mutually consistent** with the skill on every
  load-bearing claim: explicit-spawn-only subagents, `prefix_rule` Starlark shape,
  most-restrictive-wins, trusted-project gating for project config/hooks/rules,
  `project_doc_max_bytes` truncation risk, AGENTS.override.md preference, hooks event
  surface (incl. PreCompact/PostCompact/SubagentStart/Stop), and "only command
  handlers run today".
- Lesson 04's projection invariants ("hooks.json points to workspace Python hooks",
  "`.codex/rules/*.rules` uses documented syntax", "no provider/auth/telemetry from
  public assets") are the correct audit criteria and are used below.
- No contradiction found between course and skill. The course correctly frames the
  central drift: declarative workflow files do not execute on Codex.
