# ADR-1 — Codex Agent Projection Format

> **Status:** Aprovado
> **Release:** codex-agent-orchestration-parity-v1
> **Decided:** 2026-05-20 (grill-me session)
> **Decider:** operador + product-engineer
> **Supersedes:** —

---

## Contexto

Esta release precisa gerar `.codex/agents/<name>.toml` para cada um dos 20 agentes
canônicos. O formato exato do TOML e os campos permitidos precisam ser decididos antes
de qualquer implementação, pois erros de formato bloqueiam a parseabilidade (AC2) e
campos Codex-only sem ADR são explicitamente proibidos (NG2).

Três sub-decisões foram consolidadas nesta ADR:
1. Formato do TOML por agente
2. Critério de classificação de rules (comportamental vs executável)
3. Localização de armazenamento das ADRs desta release

---

## Decisões

### D1 — Formato do arquivo `.codex/agents/<name>.toml`

Cada arquivo deve ser parseável por `tomllib.load()` e conter os seguintes campos
obrigatórios:

```toml
name = "<agent-id>"
model = "<codex-mapped-identifier>"
developer_instructions = """
<corpo da persona canônica, transformado pelo ADR-2 transform>
"""
```

Campos adicionais (`tools`, `paths.write_allowlist`) **só são incluídos** se:
- O campo for nativamente suportado pelo runtime Codex; E
- Uma ADR aprovar o campo antes do PLAN.

Campos Codex-only que não têm equivalente na frontmatter canônica são proibidos sem
nova ADR (NG2).

### D2 — Critério de classificação de rules (comportamental vs executável)

**Critério mecânico** (não depende de agente classificador):

| Categoria | Definição | Destino |
|---|---|---|
| **Comportamental** | Prose normativa — instruções, protocolos, decision matrices | Inline no body do agente Codex ou `AGENTS.md` raiz |
| **Executável** | Contém diretivas executáveis: bash inline, regex gate, script paths, hook commands | Projetada como arquivo `.rules` |

**Classificação das 4 rules canônicas atuais** (inspecionadas em 2026-05-20):

| Rule | Classificação | Justificativa |
|---|---|---|
| `game-agents-coordination.md` | Comportamental | Prose normativa, decision matrix, protocolo |
| `game-developer-scope.md` | Comportamental | Prose normativa, tabela de escopo |
| `plugin-scope.md` | Comportamental | Prose normativa, error message template |
| `workspace-protocol.md` | Comportamental | Protocolo SDD, gate instructions |

Nenhuma rule atual é executável — `.codex/rules/` fica vazio nesta release.

### D3 — Localização das ADRs desta release

ADRs vivem em `specs/releases/codex-agent-orchestration-parity-v1/adrs/` (release-local),
arquivadas no CLOSURE com a release. Não são projetadas para consumer repos.

**Rationale:** ADRs globais (X1..X7) vivem na `constitution.md` — são law-of-the-land.
As ADRs desta release são decisões de implementação específicas com vida útil limitada ao
ciclo desta release. Release-local preserva atomicidade e simplicidade.

---

## Consequências

- `_install_codex_agents` em `public_assets.py` gera TOML seguindo este formato.
- Cada TOML gerado é parseado em teste (AC2) usando `tomllib.load()`.
- `.codex/rules/` permanece vazio nesta release; regras comportamentais são embutidas no
  body dos agentes via ADR-2 transform.
- Se uma rule futura contiver diretivas executáveis, este critério a classifica
  automaticamente como executável sem nova ADR.
