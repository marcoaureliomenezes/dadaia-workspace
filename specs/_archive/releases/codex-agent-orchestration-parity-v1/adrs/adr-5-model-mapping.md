# ADR-5 — Model Mapping (Claude → Codex)

> **Status:** Aprovado
> **Release:** codex-agent-orchestration-parity-v1
> **Decided:** 2026-05-20 (grill-me session)
> **Decider:** operador
> **Supersedes:** —

---

## Contexto

Os 20 agentes canônicos têm `model:` definido em frontmatter como identificadores Claude
(`claude-sonnet-4-6`, `claude-haiku-4-5-20251001`). Os arquivos `.codex/agents/<name>.toml`
não podem conter identificadores `claude-*` (AC3 — zero leak). É necessária uma tabela
de mapping explícita para a geração do TOML.

**Estado atual dos modelos (inspecionado em 2026-05-20):**
- 19 agentes: `claude-sonnet-4-6`
- 1 agente (`researcher`): `claude-haiku-4-5-20251001`
- 0 agentes: `claude-opus-4-7` (ADR-X4 moveu todos para Sonnet-default)

`claude-opus-4-7` é incluído no mapping para suportar `DADAIA_MODEL_OVERRIDE=opus` e
possíveis usos futuros.

**Fonte dos identifiers Codex:** `07_codex/02_codex_models.md` (consultado 2026-05-09).

---

## Decisão

### Tabela de mapping

| Claude identifier | Codex identifier | Posicionamento |
|---|---|---|
| `claude-opus-4-7` | `gpt-5.5` | Modelo topo Codex; especializado, alta qualidade |
| `claude-sonnet-4-6` | `gpt-5.3-codex` | Especializado em software engineering; default dos 19 agentes |
| `claude-haiku-4-5-20251001` | `gpt-5.4-mini` | Rápido/leve; researcher e subagents |

### Localização da implementação

```
dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py
```

```python
MODEL_MAP: dict[str, str] = {
    "claude-opus-4-7": "gpt-5.5",
    "claude-sonnet-4-6": "gpt-5.3-codex",
    "claude-haiku-4-5-20251001": "gpt-5.4-mini",
}

def map_model(claude_id: str) -> str:
    """Raises ValueError se o identifier Claude não tem mapping Codex."""
    if claude_id not in MODEL_MAP:
        raise ValueError(f"No Codex mapping for model: {claude_id!r}")
    return MODEL_MAP[claude_id]
```

### Acceptance

- AC3: `grep -rE '(^|[^a-zA-Z0-9_-])claude-' .codex/` retorna zero linhas após install.
- Teste unitário: `pytest tests/unit/infrastructure/runtime_transforms/test_model_mapping.py`
  — cobre os 3 mappings e o caso de identifier desconhecido.

---

## Consequências

- `_install_codex_agents` chama `map_model()` para cada agente antes de escrever o TOML.
- Identifier desconhecido levanta `ValueError` — install falha explicitamente, nunca
  silenciosamente.
- Se um novo modelo Claude for adicionado à frontmatter de algum agente, o install
  falha até esta tabela ser atualizada (comportamento desejado — evita falsa paridade).
