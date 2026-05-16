# Constitution: dadaia-workspace

> Este documento define as leis imutáveis que governam todo o desenvolvimento do dadaia-workspace.
> Todo agente de IA trabalhando neste projeto DEVE seguir estas regras em toda tarefa.
> Atualizado apenas pelo arquiteto após revisão da equipe.

---

## Propósito do Projeto

dadaia-workspace é uma biblioteca Python e uma CLI que transforma um diretório em um **workspace AI-native multi-runtime** para desenvolvimento multi-repositório orientado por SDD. O produto organiza repositórios, contextos de trabalho, estado durável em JSON e artefatos de agente para Claude Code, OpenCode e Codex em um único fluxo previsível e seguro.

---

## Stack Tecnológica (Obrigatória)

| Componente | Tecnologia | Versão mínima |
|---|---|---|
| Linguagem | Python | 3.12+ |
| Package manager | Poetry | latest stable |
| CLI framework | Typer | latest stable |
| Ambiente Python isolado | `venv` (stdlib) | — |
| Estado persistido | JSON via `json` + `os.replace()` (stdlib) | — |
| Catálogo de repositórios | openpyxl | latest stable |
| Operações git | subprocess (stdlib) | — |
| Testes | pytest | latest stable |
| Formatação e lint | ruff | latest stable |
| Type checking | mypy | latest stable |

**Nenhuma tecnologia fora desta lista pode ser adicionada sem revisão e atualização desta constituição.**

**SQLite não faz parte da stack.** O estado do workspace é gerenciado inteiramente por arquivos JSON.

---

## Segurança (Não-Negociáveis)

- **NUNCA** exponha credenciais, tokens ou secrets em código-fonte, specs ou logs.
- **NUNCA** armazene tokens git em `.dadaia/`, `.agents/`, `.claude/`, `.codex/`, `.opencode/` ou em qualquer arquivo do projeto.
- Todas as operações git usam **exclusivamente** as credenciais do sistema operacional (`~/.gitconfig`, SSH keys, credential manager do OS).
- **NUNCA** faça log de URLs com tokens embutidos.
- **SEMPRE** valide entradas do usuário na camada CLI antes de chamar serviços.
- **NUNCA** apague diretórios de repositório em `repos/` sem que o ciclo de vida de deactivate tenha sido concluído com sucesso (commit + push verificados).

---

## Princípios de Arquitetura

### Arquitetura Oficial
O produto adota uma arquitetura em quatro camadas com uma composition root explícita:

```
CLI  →  Features  →  Core  ←  Infrastructure
           \                  /
            \                /
             └─ container ──┘
```

- `cli/` orquestra input e output.
- `features/` contém regras de negócio e depende apenas de `core/`.
- `core/` contém modelos, exceções e Protocols; não depende de nenhuma outra camada do projeto.
- `infrastructure/` implementa os Protocols de `core/`.
- `dadaia_workspace/container.py` é a **composition root**. Ele pode conhecer `features/` e `infrastructure/`, mas **não faz parte do core**.

### Regras de Dependência
- A camada **CLI** nunca acessa diretamente filesystem, git ou estado JSON de forma não mediada.
- Nenhuma feature importa outra feature.
- Nenhum módulo dentro de `core/` importa `features/`, `cli/` ou `infrastructure/`.
- Toda dependência externa usada por `features/` deve passar por um `Protocol` definido em `core/`.

### Estados do Spec Context Project
Os únicos estados válidos são:
- `inativo`
- `ativo`

A flag `is_primary` (`bool`) distingue, dentro de `ativo`, qual contexto é o primário do workspace. Somente um contexto pode ter `is_primary=True` ao mesmo tempo. **Não existe estado `standby`.**

### Ciclo de Vida de Repositórios
- Um contexto `inativo` não tem repo clonado em disco.
- Um contexto `ativo` tem repo clonado em `repos/<slug>/`.
- **`activate`**: se o repo não está em disco, clona automaticamente via `git clone`.
- **`deactivate`**: executa git commit (se houver mudanças) + git push (se houver remote) antes de remover o repo do disco. Se o git sync falhar, a operação é abortada para evitar perda de dados.

### JSON como Fonte da Verdade
- O estado de todos os contextos vive em `.dadaia/states/spec_contexts.json`.
- O ponteiro do contexto primário vive em `.dadaia/states/primary_context.json`.
- Toda escrita nesses arquivos é atômica: write para `.tmp` → `os.replace()`.
- O estado pode ser diagnosticado e reparado por `dadaia doctor [--fix]`.

### Workspace Runtime Externo ao Repositório
- O **dadaia workspace runtime** vive no diretório de trabalho do usuário, fora do repositório da biblioteca `dadaia-workspace/`.
- A pasta raiz de estado do workspace é `<workspace-root>/.dadaia/`.
- A estrutura canônica de `.dadaia/` é definida **somente** em `specs/memory/architecture.md`.

### Ambiente Python do Workspace
- O ambiente Python isolado do workspace vive em `<workspace-root>/.dadaia/.venv/`.
- Após o bootstrap do workspace, agentes e automações devem usar esse ambiente para comandos Python e pip.
- O uso de Python global só é aceitável antes da criação de `.dadaia/.venv` ou para criar a própria venv.

### Artefatos Efêmeros
- Scripts Python efêmeros pertencem somente a `<workspace-root>/.dadaia/tmp/python/`.
- JSONs e dados transitórios efêmeros pertencem somente a `<workspace-root>/.dadaia/tmp/json/`.
- Artefatos efêmeros não devem ser criados em `dadaia-workspace/`, em `specs/`, em `tests/` ou na raiz do repositório.

### Artefatos de Agente
- Neste repositório, `dadaia_workspace/public/` é a única localização versionada para rules, skills, commands, scripts, agents e templates universais do produto.
- `dadaia-workspace/.agents/`, `dadaia-workspace/.claude/`, `dadaia-workspace/.codex/` e `dadaia-workspace/.opencode/` não fazem parte da arquitetura de authoring do produto e não devem ser usados como fonte canônica.
- `<workspace-root>/.dadaia/agentic/` é uma área local gerada pela CLI a partir do pacote instalado. Ela contém manifest com versão do pacote, hashes, timestamp de geração e versão de schema.
- `<workspace-root>/.agents/skills/` é o destino universal para skills reutilizáveis entre runtimes que suportam o padrão de Agent Skills.
- O comando `dadaia public stage` materializa os artefatos versionados de `dadaia_workspace/public/` em `.dadaia/agentic/`.
- O comando `dadaia public install --target all|claude|codex|opencode|agents` projeta os artefatos staged para os runtimes suportados, gerando `.dadaia/agentic/` antes se necessário.
- Claude Code recebe projeções em `.claude/agents/`, `.claude/commands/`, `.claude/skills/` e `.claude/settings.json`.
- OpenCode recebe projeções em `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/` e `opencode.json`, usando comandos, permissões e instruções nativas em vez de hooks inexistentes.
- Codex recebe projeções em `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/` e skills compartilhadas em `.agents/skills/`.
- `AGENTS.md` é o documento universal de regras e personas para runtimes que leem instruções no workspace root.
- Os 4 agentes especializados (`architect-agent`, `product-auditor-agent`, `product-engineer-agent`, `soft-engineer-agent`) são distribuídos em `dadaia_workspace/public/agents/` e projetados para cada runtime conforme suas capacidades nativas.
- A skill `dadaia-grill-me` é distribuída em `dadaia_workspace/public/skills/dadaia-grill-me/` e instalada em `.agents/skills/`, além das projeções runtime-specific quando suportadas.
- A rule `dadaia-workspace-dev-guardrail` é sempre ativa e proíbe edição direta de qualquer asset lib-originated em `.agents/`, `.claude/`, `.codex/` ou `.opencode/`. Assets lib-originated são identificados por comparação com o manifest staged em `.dadaia/agentic/`.
- `dadaia public doctor` diagnostica drift entre pacote, staging e projeções runtime, reportando `ok`, `missing`, `drift` e `unsupported`.

### Integração CLI-First para Agentes
- A CLI oficial `dadaia` é a interface primária do produto para consumo por humanos e agentes.
- Toda capacidade oficialmente suportada para automação deve ser exposta por comando CLI com help no comando raiz, no grupo e no subcomando correspondente.
- Skills, workflows e automações devem usar a CLI oficial sempre que a capacidade desejada existir nela.
- Se a CLI ainda não cobrir uma necessidade operacional, o único fallback permitido para automação é criar script Python efêmero em `<workspace-root>/.dadaia/tmp/python/` e gravar saída estruturada em `<workspace-root>/.dadaia/tmp/json/`.

---

## Qualidade de Código

- Cobertura mínima: **80%** para código novo na camada `features/`.
- `core/models/` e `core/exceptions.py` devem ter cobertura completa.
- Toda função pública deve ter type hints completos.
- Nenhum `print()` fora da CLI.
- O código deve passar em `ruff format`, `ruff check` e `mypy --strict`.
- Falhas devem preservar a cadeia de causa entre infraestrutura, feature e CLI.
- Mensagens de exceção e de erro de CLI devem informar a capacidade ou comando que falhou, o contexto ou recurso relevante e a próxima ação segura de recuperação quando ela existir.

---

## Workflow de Desenvolvimento (SDD)

- **NUNCA** implemente uma feature sem `SPEC.md` aprovado.
- **NUNCA** avance de fase (`SPEC.md` → `PLAN.md` → `TASKS.md` → implementação) sem aprovação humana explícita.
- Toda alteração em `specs/` deve passar por uma revisão de consistência antes de ser considerada pronta.
- Se restarem conflitos, ambiguidades ou buracos após a revisão, eles devem ser registrados em `z_bug_specs.md`.
- Se a implementação divergir da spec, atualize a spec primeiro. Nunca ajuste a spec para justificar o código já escrito.
- **Versão atômica**: specs ativas em `specs/releases/<v-id>/` representam apenas o estado atual; specs encerradas vão para `specs/_archive/releases/<v-id>/`. Hotfix releases (PATCH≥1) seguem o mesmo caminho. Não há rascunhos órfãos fora dessas trilhas.

---

## Mapa de Responsabilidade das Specs

- `specs/memory/architecture.md` é a fonte única da estrutura do workspace runtime e da árvore `.dadaia/`.
- `specs/memory/product.md` é a fonte única da definição do produto, dos usuários e do modelo conceitual.
- `specs/memory/tech-stack.md` é a fonte única da política de toolchain, `.dadaia/.venv` e execução Python.
- `specs/foundation/SPEC.md` é a fonte única da arquitetura de implementação e dos guardrails anti-drift.
- `specs/SPEC.md` é a fonte única do comportamento do produto e da superfície top-level da CLI.
- `specs/features/*/SPEC.md` possuem apenas contratos específicos de feature.
- `specs/PLAN.md` e `specs/TASKS.md` são documentos derivados e não podem redefinir contratos dos documentos acima.

---

## Workspace Runtime

- O template canônico do workspace runtime é definido em `specs/memory/architecture.md`.
- O bootstrap deve reconciliar a estrutura mínima do workspace sem destruir conteúdo já existente.
