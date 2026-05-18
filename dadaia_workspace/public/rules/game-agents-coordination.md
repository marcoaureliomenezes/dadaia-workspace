# game-agents-coordination

Esta rule é sempre ativa em contextos de jogo neste workspace.

## Agentes de Jogo

Três agentes têm autoridade exclusiva sobre `repos/tauan-games/`, cada um com
sub-domínio distinto:

| Agente | Sub-domínio | Escreve |
|---|---|---|
| `game-developer` | Lógica | C++, Blueprints (gameplay), fixtures de teste |
| `game-designer` | Design | Scripts Python/CLI, configs, specs de assets, HDA |
| `game-tester` | Testes | Scripts de teste, reports HTML com evidências |

## Decision Authority Matrix

| Domínio | Autoridade Primária | Podem Objetar (com evidência) | Tie-breaker |
|---|---|---|---|
| Mecânicas, física, IA, balística | **game-developer** | game-designer, game-tester | product-engineer |
| Design visual, mapas, áudio, arte | **game-designer** | game-developer, game-tester | product-engineer |
| Critérios de qualidade, test strategy | **game-tester** | game-developer, game-designer | product-engineer |
| Arquitetura geral, code patterns | **software-architect** | game-developer (idiomas UE5) | game-developer vence em decisões UE5-específicas |
| CI/CD, build, deploy | **devops-engineer** | game-developer, game-designer | devops-engineer |
| Escopo, prioridades, dispatch | **project-manager** | todos | operador (palavra final) |
| Autoria de SPEC/PLAN/TASKS, memory atomicity | **product-engineer** | project-manager | product-engineer (memory é gate-locked) |
| Audit de drift + dead code | **project-auditor** | todos | operador (escalation) |

## Protocolo Anti-Deadlock

Quando dois agentes divergem:

1. Cada agente documenta sua posição e trade-offs no próprio report
2. `product-engineer` sintetiza e propõe resolução no synthesis report
3. Se ainda sem consenso → **invocar `dadaia-grill-me` com o operador** (decisão humana estruturada)

**Regra absoluta:** nenhum agente bloqueia o domínio do outro.
Uma objeção sem evidência é automaticamente ignorada.

## Protocolo de Pesquisa

Cada agente usa `WebSearch` apenas dentro de sua whitelist de fontes confiáveis.
A whitelist está embedded na skill especializada de cada agente.
Nunca usar fontes fora da whitelist sem aprovação explícita do operador.

## Conflito de Sub-domínio

Quando um bug ou feature span dois sub-domínios (ex: performance de mapa afeta física
de voo), o `game-tester` classifica e emite dois sub-reports direcionados
independentemente para `game-designer` e `game-developer`.
