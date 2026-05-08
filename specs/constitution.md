# Constitution: dadaia-workspace

> Este documento define as leis imutáveis que governam todo o desenvolvimento do dadaia-workspace.
> Todo agente de IA trabalhando neste projeto DEVE seguir estas regras em toda tarefa.
> Atualizado apenas pelo arquiteto após revisão da equipe.

---

## Propósito do Projeto

dadaia-workspace é uma biblioteca Python e uma CLI que transforma um diretório em um **workspace AI-native** para desenvolvimento multi-repositório orientado por SDD. O produto organiza contexto, repos materializados, artefatos de agente e regras de trabalho em um único fluxo previsível e seguro.

---

## Stack Tecnológica (Obrigatória)

| Componente | Tecnologia | Versão mínima |
|---|---|---|
| Linguagem | Python | 3.12+ |
| Package manager | Poetry | latest stable |
| CLI framework | Typer | latest stable |
| Ambiente Python isolado | `venv` (stdlib) | — |
| Persistência de estado | SQLite (stdlib `sqlite3`) | — |
| Catálogo de repositórios | openpyxl | latest stable |
| Operações git | subprocess (stdlib) | — |
| Testes | pytest | latest stable |
| Formatação e lint | ruff | latest stable |
| Type checking | mypy | latest stable |

**Nenhuma tecnologia fora desta lista pode ser adicionada sem revisão e atualização desta constituição.**

---

## Segurança (Não-Negociáveis)

- **NUNCA** exponha credenciais, tokens ou secrets em código-fonte, specs ou logs.
- **NUNCA** armazene tokens git no banco de dados SQLite, em `.dadaia/`, em `.claude/` ou em qualquer arquivo do projeto.
- Todas as operações git usam **exclusivamente** as credenciais do sistema operacional (`~/.gitconfig`, SSH keys, credential manager do OS).
- **NUNCA** faça log de URLs com tokens embutidos.
- **SEMPRE** valide entradas do usuário na camada CLI antes de chamar serviços.
- **NUNCA** apague diretórios de repositório fora da área gerenciada de materialização do contexto.

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
- A camada **CLI** nunca acessa diretamente SQLite, git ou filesystem.
- Nenhuma feature importa outra feature.
- Nenhum módulo dentro de `core/` importa `features/`, `cli/` ou `infrastructure/`.
- Toda dependência externa usada por `features/` deve passar por um `Protocol` definido em `core/`.

### Estados Oficiais do Spec Context Project
Os únicos estados válidos são:
- `inativo`
- `standby`
- `ativo`

Nenhum outro estado faz parte do v1.0.

### Materialização Gerenciada
- Um contexto `inativo` existe apenas como metadata persistida.
- Um contexto `standby` ou `ativo` possui materialização gerenciada em `.dadaia/contexts/<context-name>/`.
- Toda remoção de arquivos em disco se limita à materialização gerenciada dentro de `.dadaia/contexts/`.

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
- Neste repositório, `dadaia_workspace/public/` é a única localização versionada para rules, skills e workflows do produto.
- `dadaia-workspace/.claude/` não faz parte da arquitetura do produto e não deve existir.
- O comando `dadaia public install` extrai os artefatos versionados para o `.claude/` do workspace do usuário.

### Integração CLI-First para Agentes
- A CLI oficial `dadaia` é a interface primária do produto para consumo por humanos e agentes.
- Toda capacidade oficialmente suportada para automação deve ser exposta por comando CLI com help no comando raiz, no grupo e no subcomando correspondente.
- Skills, workflows e automações devem usar a CLI oficial sempre que a capacidade desejada existir nela; não devem contornar comandos existentes por leitura direta de SQLite, arquivos gerenciados ou módulos internos do pacote.
- Se a CLI ainda não cobrir uma necessidade operacional, o único fallback permitido para automação é criar script Python efêmero em `<workspace-root>/.dadaia/tmp/python/` e gravar saída estruturada em `<workspace-root>/.dadaia/tmp/json/`, de forma descartável e não versionada.

---

## Qualidade de Código

- Cobertura mínima: **80%** para código novo na camada `features/`.
- `core/models/` e `core/exceptions.py` devem ter cobertura completa.
- Toda função pública deve ter docstring curta e type hints completos.
- Nenhum `print()` fora da CLI.
- O código deve passar em `ruff format`, `ruff check` e `mypy --strict`.
- Classes, métodos e exceções públicas devem ter nomes que explicitem a capacidade de negócio que representam.
- Falhas devem preservar a cadeia de causa entre infraestrutura, feature e CLI; não é permitido perder a exceção original ou substituí-la por mensagens genéricas.
- Mensagens de exceção e de erro de CLI devem informar a capacidade ou comando que falhou, o contexto ou recurso relevante e a próxima ação segura de recuperação quando ela existir.

---

## Workflow de Desenvolvimento (SDD)

- **NUNCA** implemente uma feature sem `SPEC.md` aprovado.
- **NUNCA** avance de fase (`SPEC.md` → `PLAN.md` → `TASKS.md` → implementação) sem aprovação humana explícita.
- Toda alteração em `specs/` deve passar por uma revisão de consistência de spec antes de ser considerada pronta.
- Se restarem conflitos, ambiguidades ou buracos após a revisão, eles devem ser registrados em `z_bug_specs.md` antes de qualquer implementação.
- Se a implementação divergir da spec, atualize a spec primeiro. Nunca ajuste a spec para justificar o código já escrito.

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
