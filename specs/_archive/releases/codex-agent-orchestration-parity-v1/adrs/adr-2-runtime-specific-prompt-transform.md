# ADR-2 — Runtime-Specific Prompt Transform

> **Status:** Aprovado
> **Release:** codex-agent-orchestration-parity-v1
> **Decided:** 2026-05-20 (grill-me session)
> **Decider:** product-engineer (derivado de NG4 + SPEC §2 item 4)
> **Supersedes:** —

---

## Contexto

O texto canônico de `project-manager` e `project-auditor` referencia o **Agent tool**
do Claude Code (`Agent({...})`). O Codex não tem Agent tool nativo — usa subagents e
recipes. Se o texto canônico for copiado verbatim para `developer_instructions`, o
agente Codex receberá instruções que referenciam uma tool que não existe no seu runtime.

O non-goal NG4 proíbe reescrever o texto canônico no repositório. A solução é uma
função de transformação determinística aplicada no momento da geração do TOML.

---

## Decisão

Uma função de transformação **determinística** recebe o markdown canônico de um agente
e produz o `developer_instructions` para o TOML Codex, sem modificar o arquivo fonte.

### Localização

```
dadaia_workspace/infrastructure/runtime_transforms/codex.py
```

### Contrato da função

```python
def transform_for_codex(canonical_body: str, agent_id: str) -> str:
    """
    Dado o body canônico de um agente (frontmatter removido),
    retorna o developer_instructions adequado para Codex.

    Transformações obrigatórias:
    - Substituir referências ao Agent tool por equivalente Codex (subagent/recipe)
    - Remover menções a hooks Claude-específicos (UserPromptSubmit, etc.)
    - Preservar todo o restante verbatim

    Retorna string não-vazia após strip().
    """
```

### Transformações obrigatórias (v1)

| Padrão no canônico | Substituição no Codex |
|---|---|
| `Agent({...})` / `Agent tool` | `subagent` / `codex subagent dispatch` |
| `UserPromptSubmit hook` | removido (capability gap — ver ADR-3) |
| Todo o restante | preservado verbatim |

### Golden tests

Suite de testes com fixtures por agente (`tests/unit/infrastructure/runtime_transforms/`):
- `test_transform_project_manager.py` — valida substituição de Agent tool
- `test_transform_project_auditor.py` — valida substituição de Agent tool
- `test_transform_generic_agent.py` — valida que agentes sem Agent tool são preservados verbatim
- `test_transform_output_nonempty.py` — para todos os 20 agentes, output não é vazio após strip

---

## Consequências

- O texto canônico em `dadaia_workspace/public/agents/*.md` nunca é editado por esta
  release (NG4 respeitado).
- Qualquer mudança futura na sintaxe do Agent tool requer apenas atualizar a tabela de
  transformações — não o texto de 20 agentes.
- A função é testada independentemente da geração de TOML.
