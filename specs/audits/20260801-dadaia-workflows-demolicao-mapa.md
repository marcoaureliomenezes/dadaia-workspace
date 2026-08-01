# Demolição dos dadaia-workflows — mapa de destino de fragments e personas

**Data:** 2026-08-01 · **Candidata na origem:** `bf1ad82f`

Este documento é a prestação de contas da revisão exigida antes da demolição: **nenhum
fragment ou persona foi apagado sem antes provar onde a sua parte essencial vive.**

Guardrail respeitado: só foram tocadas estruturas **universais** (`public/rules/`,
`public/skills/`) e do **Claude** (`public/agents/`). Nada específico de Codex ou Kimi CLI
foi alterado.

## Por que os workflows existiram

O ciclo SDD tinha falhas comportamentais reais e recorrentes: agentes faziam by-pass às
Specs, não seguiam SDD, ignoravam backlog existente ao definir mais backlog, e produziam
reviews mal feitas. Os workflows tentaram resolver isso tornando as etapas
(backlog-definition, release-definition, implementation+reviews, audit) **determinísticas**,
com contexto focado por etapa.

O diagnóstico da auditoria arquitetural: a necessidade era legítima, mas o determinismo foi
colocado **em volta do agente** (um motor que conduz, retoma e passa payloads) em vez de **em
volta dos artefactos** (validadores puros sobre ficheiros). O motor cresceu para 9.125 linhas
para entregar 1.045 linhas de prompt, e passou a responder por 51% de todos os bugs do
projeto.

## Personas (8) — destino: DELETE, zero migração

Todas as 8 declaram `source_agent: agents/<role>.md` e **derivam 1:1 de um sub-agent Claude
que existe**. Verificação de conteúdo substantivo:

| Persona | Regras substantivas | Cobertas no sub-agent? |
|---|---|---|
| `qa-engineer` | pirâmide 70/20/10, magic-mock, volume padding, always-pass, Given/When/Then | **sim** (G/W/T está no template do sub-agent) |
| `code-reviewer` | 6 eixos, severidade, `file:line`, veredicto | **sim** (o sub-agent usa `APPROVE`/`REQUEST_CHANGES`; o `REJECTED` da persona foi divergência imposta pelo gate Python) |
| `project-auditor` | CONFIRMED/DRIFTED/UNVERIFIABLE, score 1–10 | **sim** |
| `ai-engineer` | behavior-change-per-token, write-allowlist, scope drift | **sim** |
| `product-engineer`, `software-architect`, `software-engineer`, `security-reviewer` | — | **sim** |

Conteúdo exclusivo das personas = **acoplamento ao motor**, que morre com ele. Exemplos:
«This is a reserve role: it binds to no fixed dadaia-workflow step»; «the step's fragment
owns the JSON contract, never this persona... when they conflict, the fragment wins».

Único consumidor no código: `features/lifecycle/personas/loader.py` — parte do motor.

## Fragments (13) — destino por ficheiro

| Fragment | Destino | Justificação |
|---|---|---|
| `shared/anti-slop` | **→ nova rule `grounded-work`** | vivia só em 3 sub-agents, mas o motor injetava-o em **todos** os steps. Instinto certo, camada errada. Agora é regra universal, lida por todos os harnesses via corpus. |
| `shared/write-scope` | **delete** | coberto por `workspace-protocol` §6 (write-allowlist) e pelo skill `dadaia-task-manager` (marcadores `[ ]`/`[-]`/`[x]`). |
| `shared/memory-selection` | **delete** | coberto pelo skill `dadaia-step0-memory-bootstrap` (catálogo + atoms, não inventar atom ausente). |
| `shared/grill-questionnaire` | **→ `dadaia-grill-me`** | a checklist já existia no skill; faltava a **postura headless**, agora portada (Phase 1). |
| `backlog_definition/backlog_authoring` | **→ sub-agent `project-manager`** | NEW xor EDIT, intents ligados, `surface: new` — agora na secção «Authoring one backlog item» do dono do backlog. |
| `backlog_definition/intake_grill` | **delete** | o método (resolver por evidência, normalizar bug, nomear subjects, listar open questions) está no `dadaia-grill-me` + na nova secção do PM. |
| `release_definition/definition_draft` | **→ `dadaia-release-definition`** | portadas 3 regras que não existiam em lado nenhum: **caminho de verificação por critério**, **contract bindings decididos no PLAN e copiados verbatim**, **validation dependency table** (sem dependência para a frente; pipe em code span). |
| `release_definition/definition_review` | **delete** | o veredicto e os eixos vivem nos sub-agents revisores. |
| `implementation/implement-tdd` | **→ sub-agent `software-engineer`** | portado «ver o teste falhar e ler a falha» e «sem abstração especulativa». O resto já lá estava. |
| `implementation/self-verify` | **→ rule `grounded-work`** | portadas «nunca re-correr até ficar verde / não aparar o check», «verificar, não corrigir aqui», «registar comando e resultado». |
| `implementation/combined-review` | **delete** | os três ângulos são os três sub-agents revisores; a fusão num só passo era otimização de custo do motor. |
| `implementation/close-release` | **→ verificar contra `dadaia-release-closure`** | skill dedicado já existe. |
| `audit/audit-report` | **→ verificar contra `project-auditor` + `drift-detection`** | sub-agent e skill já existem. |

## O que a demolição NÃO pode levar

A mecânica **`Consumes` → `consumed_backlog.json` → remoção no closure** vive em
`features/backlog/` (`ledger.py`, `removal.py`, `removal_lifecycle.py`) — **não no motor**.
O motor apenas a chamava. Sobrevive; precisa apenas de um chamador.

Os **doctors** (`features/specs/`, `features/backlog/`) são validação pura e sobrevivem
inteiros. Foram eles que provaram, na ronda 25, apanhar violações reais.
