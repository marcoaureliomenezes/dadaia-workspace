# TASKS — v0.2.2 Full Codex Compatibility

**Status:** Aprovado
**Release:** v0.2.2

---

- [-] T-CX-1 — Fix Codex semantic transformer and model mapping
  - Owner: software-engineer
  - Write set:
    - `dadaia_workspace/infrastructure/runtime_transforms/**`
    - `tests/**`
  - Acceptance:
    - `ai-harness-claude-code` is preserved as a skill name.
    - Model identifiers map only in model contexts.

- [ ] T-CX-2 — Generate Codex-native command `.rules`
  - Owner: software-engineer
  - Write set:
    - `dadaia_workspace/infrastructure/public_assets.py`
    - `dadaia_workspace/public/runtime/codex/**`
    - `tests/**`
  - Acceptance:
    - `.codex/rules/*.rules` is generated.
    - Markdown protocol docs do not masquerade as executable Codex Rules.

- [ ] T-CX-3 — Add Codex custom-agent config boundaries
  - Owner: software-engineer
  - Write set:
    - `dadaia_workspace/infrastructure/public_assets.py`
    - `dadaia_workspace/public/agents/**`
    - `tests/**`
  - Acceptance:
    - Generated TOML includes supported role-boundary config.
    - Provider/auth/telemetry remain absent.

- [ ] T-CX-4 — Update Codex AI-surface wording
  - Owner: ai-engineer
  - Write set:
    - `dadaia_workspace/public/agents/**`
    - `dadaia_workspace/public/skills/**`
    - `dadaia_workspace/public/rules/**`
    - `dadaia_workspace/public/workflows/**`
    - `dadaia_workspace/public/data/**`
  - Acceptance:
    - Codex subagent/custom-agent wording is current.
    - `.claude/rules/...` is not emitted into Codex agents.

- [ ] T-CX-5 — Expand public doctor semantic checks
  - Owner: software-engineer
  - Write set:
    - `dadaia_workspace/infrastructure/public_assets.py`
    - `tests/**`
  - Acceptance:
    - Doctor fails on non-existent Codex skill references, stale Claude path leaks, missing TOML files, bad rules/config/hooks.

- [ ] T-CX-6 — Stage/install and eliminate runtime projection drift
  - Owner: software-engineer
  - Write set:
    - `.dadaia/agentic/**`
    - `.codex/**`
    - `.claude/**`
    - `.opencode/**`
    - `.agents/**`
    - `AGENTS.md`
    - `CLAUDE.md`
  - Acceptance:
    - `dadaia public stage && dadaia public install --target all && dadaia public doctor` passes.
    - Instantiated workspace projection matches library source.

- [ ] T-CX-7 — Memory update, closure, archive, PR
  - Owner: product-engineer
  - Write set:
    - `specs/memory/**`
    - `specs/releases/**`
    - `specs/_archive/releases/**`
  - Acceptance:
    - Memory records the Codex compatibility invariant.
    - `CLOSURE.md` includes evidence triples.
    - Release archived and `ACTIVE.md` reset.
    - Branch pushed and PR opened; not merged.
