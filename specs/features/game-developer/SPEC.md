# Spec: Feature — Game Developer Agent

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/features/agents/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`

---

## Contexto

O `game-developer` é um **agente de domínio exclusivo** para código de jogo no workspace.
Nenhum outro agente está autorizado a escrever, modificar ou evoluir qualquer código de jogo.
Essa exclusividade é enforçada pela rule `dadaia-workspace/public/rules/game-developer-scope.md`.

O agente não faz parte do pipeline SDD core-4. Ele consome specs aprovadas (produzidas pelo
`product-engineer`) e as implementa exclusivamente dentro de `repos/redacted-slug/`.

---

## Workspace de Jogo Atual

| Projeto | Engine | Stack |
|---|---|---|
| `redacted-slug-trex` | Phaser.js 3.60 | HTML + JS puro, CDN, sem build step |
| `redacted-slug` | Three.js r165 | HTML + JS puro, estética N64, CDN |

Ambos os projetos vivem em `repos/redacted-slug/`. O agente não assume que este workspace
é imutável — novos projetos e engines podem ser adicionados sem alterar esta spec.

---

## Responsabilidades

| Área | Descrição |
|---|---|
| Implementação | Implementar backlog de jogos a partir de specs aprovadas pelo `product-engineer` |
| Game Review | Emitir gameplay reviews com avaliação técnica e de experiência de jogo |
| Plataformas | Browser (Phaser/Three.js), Godot, Unity, Unreal Engine 5 — nessa ordem de preferência |
| Distribuição | Empacotar e distribuir jogos para plataformas-alvo (itch.io, GitHub Pages, Steam) |

---

## Definição do Agente

**Arquivo canônico:** `dadaia_workspace/public/agents/game-developer.md`

| Campo | Valor |
|---|---|
| `name` | `game-developer` |
| `model` | `claude-sonnet-4-6` |
| `maxTurns` | 60 |
| `color` | `orange` |
| `tools` | Read, Write, Edit, Bash, Glob, Grep, WebFetch |
| `skills` | `game-physics-engine`, `game-map-architect`, `game-platform-browser`, `game-platform-godot`, `game-platform-unity`, `game-platform-unreal`, `game-packaging-distribution` |

**Permissões (write):** Exclusivamente `repos/redacted-slug/`

**Proibições:**
- Jamais modifica infraestrutura, Docker, CI/CD, pipelines de dados ou APIs de negócio
- Jamais modifica `specs/` (é consumidor de specs, nunca autor)
- Jamais toca em `.dadaia/`, `.claude/`, `.agents/`, `.codex/` ou `.opencode/`
- Jamais escreve fora de `repos/redacted-slug/`

---

## Regra de Escopo

A rule `dadaia_workspace/public/rules/game-developer-scope.md` é sempre ativa e:
- Declara `game-developer` como o único agente autorizado em `repos/redacted-slug/`
- Instrui `product-engineer`, `soft-engineer-agent`, `software-architect` e `devops-engineer`
  a rejeitar qualquer tarefa que envolva arquivos de jogo com mensagem `[SCOPE ERROR]`

---

## Requisitos Funcionais

- FR-001: O agente `game-developer` shall be defined in `dadaia_workspace/public/agents/game-developer.md` with complete YAML frontmatter.
- FR-002: O agente shall use the `game-physics-engine` skill for all physics, game loop, collision, and ballistics implementation.
- FR-003: O agente shall use the `game-map-architect` skill for all tilemap, camera, parallax, and HUD work.
- FR-004: O agente shall use the `game-platform-browser` skill when implementing for Phaser.js or Three.js targets.
- FR-005: O agente shall use the `game-platform-godot` skill when implementing for Godot Engine.
- FR-006: O agente shall use the `game-platform-unity` skill when implementing for Unity.
- FR-007: O agente shall use the `game-platform-unreal` skill when implementing for Unreal Engine 5.
- FR-008: O agente shall use the `game-packaging-distribution` skill before any game publishing action.
- FR-009: O agente shall only read specs from `specs/` — never write to them. Spec authoring is delegated to `product-engineer`.
- FR-010: O agente shall only write within `repos/redacted-slug/`.
- FR-011: The rule `game-developer-scope.md` shall be always active and enforced across all supported runtimes.
- FR-012: O agente shall be projected to all supported runtimes via `dadaia public install --target all`.

## Skills Requeridas

| Skill | Finalidade |
|---|---|
| `game-physics-engine` | Game loop, delta time, física, colisão, balística, partículas |
| `game-map-architect` | Tilemap, câmera, parallax, efeitos de câmera, HUD |
| `game-platform-browser` | Phaser.js v4, Three.js, Babylon.js, setup CDN |
| `game-platform-godot` | Godot v4.x, GDScript, física 2D, export |
| `game-platform-unity` | Unity 6, C#, Rigidbody, ScriptableObjects, Steam |
| `game-platform-unreal` | UE5, Blueprint vs C++, Nanite/Lumen, Shipping build |
| `game-packaging-distribution` | GitHub Pages, itch.io, Butler CLI, Steam, checklist de release |

---

## Requisitos Não-Funcionais

- NFR-001: [Exclusividade] Nenhum outro agente escreve código de jogo. A regra de escopo é a única barreira — o operador é responsável por não escalar tarefas de jogo para outros agentes.
- NFR-002: [Modelo adequado] `claude-sonnet-4-6` é escolhido para tarefas de game dev por velocidade e custo. Para análise arquitetural de jogos complexos, o operador pode solicitar ao `software-architect` um report antes de iniciar a implementação.
- NFR-003: [Plataforma-agnóstico] O agente domina 4 plataformas em ordem de preferência. Nunca usa Unreal sem justificativa documentada na spec.

---

## Fora de Escopo (v1.0)

- Criação de assets de arte (sprites, texturas, modelos 3D originais)
- Multiplayer networking e servidores de jogo
- Código fora de `repos/redacted-slug/`
- Specs e planos (responsabilidade do `product-engineer`)
- CI/CD de jogos (responsabilidade do `devops-engineer`)
