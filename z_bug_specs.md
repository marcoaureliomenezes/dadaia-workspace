# z_bug_specs.md

Atualizado em: 2026-04-26
Escopo: pass de convergencia do template `.dadaia`, da politica `.dadaia/.venv`, da governanca SDD pre-implementacao, da politica de execucao de skills e do contrato de erros agent-friendly

## Gaps abertos

Esta rodada resolveu os contratos canonicos de CLI-first para skills, fallback controlado em `.dadaia/tmp/python/`, diagnostico de falhas orientado a agentes e o modelo incorreto de `.claude/` local ao repositório. Os assets versionados do produto vivem somente em `dadaia_workspace/public/` e a extração destino é `<workspace-root>/.claude/`.

### G3. A superficie de CLI ainda nao cobre operacoes granulares de assets de agente

O contrato atual cobre `dadaia init`, `dadaia context ...`, `dadaia repos list` e `dadaia public install`, mas nao cobre operacoes CLI dedicadas para assets da biblioteca como:

- listar assets publicos disponiveis;
- extrair ou instalar seletivamente rules, skills ou commands;
- scaffold inicial ou refresh mais granular de assets de agente.

Impacto:

- mesmo com a politica CLI-first agora congelada, ainda faltam comandos oficiais para varios casos fora do Spec Context e do install em lote.

## Uso deste arquivo

- Este e o registro vivo de gaps remanescentes antes da implementacao.
- Adicione entradas aqui somente quando um conflito, buraco ou ambiguidade permanecer sem resolucao ao fim de uma revisao.
- `report-specs-review.md` deve ser tratado apenas como contexto historico, nao como fonte canonica do estado atual.