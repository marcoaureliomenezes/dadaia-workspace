# TASKS — codex-runtime-agent-hotfix-v1

**Status:** Aprovado

- [ ] T-CX-HOTFIX-01 — Corrigir runtime Codex agents/skills projection.
  - Write set:
    - `dadaia_workspace/public/skills/*/SKILL.md`
    - `dadaia_workspace/public/runtime/codex/*/SKILL.md`
    - `dadaia_workspace/infrastructure/public_assets.py`
    - `tests/unit/test_public_assets.py`
    - `tests/unit/infrastructure/test_public_assets.py`
  - Aceite:
    - Skills carregáveis pelo Codex têm YAML frontmatter.
    - Runtime adapters Codex entram no staging.
    - Agent TOMLs Codex emitidos têm `description`.
    - Testes unitários relevantes passam.
