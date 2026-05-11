# Architecture: dadaia-workspace

## Escopos Distintos

- `dadaia-workspace/` é o **repositório da biblioteca**: authoring de código, specs e assets de agente.
- `<workspace-root>/` é o **runtime workspace do usuário**: local onde a biblioteca cria `.dadaia/`, `.agents/`, `.claude/`, `.codex/` e `.opencode/`.
- O template canônico do runtime workspace é definido neste arquivo. Outros documentos devem referenciar este contrato, não reescrevê-lo.

---

## Visão Geral do Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        dadaia-workspace                             │
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────┐              │
│  │ CLI Layer   │──▶│ Features    │──▶│ Core         │              │
│  │ (Typer)     │   │ (Business)  │   │ (Models +    │              │
│  └─────────────┘   └─────────────┘   │ Protocols)   │              │
│          │                ▲          └──────────────┘              │
│          ▼                │                 ▲                      │
│   container.py ───────────┘                 │                      │
│          │                                  │                      │
│          ▼                                  │                      │
│   Infrastructure (JSON, XLSX, git, public)                         │
└─────────────────────────────────────────────────────────────────────┘
```

`dadaia_workspace/container.py` é a composition root e monta serviços a partir de implementações concretas da infraestrutura.

---

## Estrutura do Workspace em Disco

```
<workspace-root>/
  repos/
    <repo-slug>/          ← clonado automaticamente por dadaia context activate
      specs/              ← fonte canônica de specs do projeto
  AGENTS.md               ← instruções universais para runtimes AI
  opencode.json           ← configuração OpenCode gerada/projetada
  .agents/
    skills/               ← skills universais compartilhadas entre runtimes
      dadaia-grill-me/
  .claude/
    rules/
    skills/
    commands/
    agents/               ← sub-agentes Claude Code (architect, auditor, engineer, soft)
    settings.json         ← hooks Claude Code suportados
  .codex/
    config.toml           ← configuração Codex projetada
    hooks.json            ← hooks Codex suportados
    rules/
  .opencode/
    agents/
    commands/
    skills/
  .dadaia/
    .venv/                ← Python env isolado do workspace
    academy/              ← cursos criados pelo operador (cópias de work do knowledge_basis)
      <slug>/             ← conteúdo do curso (markdown)
    agentic/              ← staging gerado de assets públicos do pacote
      manifest.json       ← versão do pacote, schema, hashes e timestamp
      agents/
      commands/
      rules/
      skills/
      scripts/
      templates/
    reports/
      architect-agent-review/  ← reports do architect-agent
      specs-sdd-review/        ← reports do product-auditor-agent
      bugs/
        soft-engineer-report/  ← bug reports do soft-engineer-agent
    scripts/
      ctx-inject.sh       ← hook script: lê DADAIA_CONTEXT ou primary_context.json
    states/
      spec_contexts.json  ← fonte da verdade: todos os contextos + estados
      primary_context.json ← ponteiro do contexto primário; lido pelo hook
      academy.json        ← estado persistido de todos os cursos da academy
    src/
      repos.xlsx          ← whitelist de repos disponíveis para Spec Contexts
    dist/                 ← artefatos de export gerados por `dadaia export`
    tmp/
      python/             ← scripts efêmeros de agentes
      json/               ← outputs JSON efêmeros de agentes
```

### Princípio operacional

- `repos/` é a **fonte canônica de todos os repositórios e specs**. Specs nunca são copiadas para fora dos repos.
- `repos/<slug>/` existe em disco **somente** enquanto o contexto correspondente está `ativo`. É criado por `activate` (clone) e removido por `deactivate` (após git sync).
- `.dadaia/states/spec_contexts.json` é o único estado persistido de todos os contextos. Escrito atomicamente.
- `.dadaia/states/primary_context.json` é o ponteiro do contexto primário. Escrito quando um contexto é promovido a primário, deletado quando não há primário.
- `AGENTS.md` é o documento universal de instruções para OpenCode, Codex e qualquer agente que leia o workspace root.
- `.agents/skills/` contém skills universais instaladas a partir de `.dadaia/agentic/skills/`.
- `.dadaia/agentic/` é staging gerado pela CLI a partir de `dadaia_workspace/public/`; não é fonte canônica e pode ser recriado.
- `.dadaia/agentic/manifest.json` registra schema version, package version, generated_at e hashes dos assets staged.
- `.dadaia/scripts/ctx-inject.sh` é o hook de contexto para runtimes que suportam injeção por prompt. No Claude Code, ele roda via `UserPromptSubmit`; outros runtimes usam mecanismos próprios documentados na feature universal.
- `.dadaia/.venv/` é o ambiente Python isolado do workspace.
- `.dadaia/tmp/python/` e `.dadaia/tmp/json/` são as únicas áreas válidas para artefatos efêmeros de agentes.
- `.dadaia/reports/` contém relatórios persistentes organizados por agente: `architect-agent-review/`, `specs-sdd-review/`, `bugs/soft-engineer-report/`. Criados por `dadaia init`.
- `.dadaia/academy/` contém cursos criados pelo operador. Cada `<slug>/` é uma cópia de trabalho de um módulo do knowledge_basis.
- `.dadaia/states/academy.json` é o estado persistido de todos os cursos da academy. Escrito atomicamente.
- `.dadaia/src/repos.xlsx` é a whitelist de repos disponíveis para criação de Spec Contexts.
- `.dadaia/dist/` contém artefatos de export gerados por `dadaia export`. Criado on-demand pelo ExportService; não é criado por `dadaia init`. Não deve ser apagado por `dadaia doctor`.
- `.claude/` contém projeção Claude Code gerada por `dadaia public install --target claude|all`.
- `.codex/` contém projeção Codex gerada por `dadaia public install --target codex|all`.
- `.opencode/` e `opencode.json` contêm projeção OpenCode gerada por `dadaia public install --target opencode|all`.
- `.agents/skills/` contém projeção universal gerada por `dadaia public install --target agents|all`.
- `.claude/agents/` contém os 4 sub-agentes especializados no formato Claude Code.
- `.opencode/agents/` contém a projeção equivalente para OpenCode quando suportado pelo modelo de configuração do OpenCode.
- Codex usa `AGENTS.md`, `.codex/rules/`, hooks e `.agents/skills/`; não deve fingir suporte a sub-agentes Claude Code quando o runtime não oferece esse mecanismo.
- **Não existem**: `.dadaia/data/dadaia.db` (SQLite removido), `.dadaia/contexts/` (materialização gerenciada removida).

### Política de efemeridade

- O conteúdo de `.dadaia/tmp/` pode ser recriado, limpo ou substituído sem impacto no estado durável.
- O conteúdo de `.dadaia/states/` é durável: somente o sistema que escreve um state file pode atualizá-lo ou removê-lo.
- O conteúdo de `.dadaia/scripts/` é durável: scripts persistem entre sessões.
- O conteúdo de `.dadaia/dist/` é durável: artefatos de export persistem até remoção explícita pelo operador.

---

## State Machine: Spec Context Project (v4.0)

```
create ──────▶ INATIVO (is_primary=False)
                  │
                  │ activate <name>
                  │ (clone repo se ausente)
                  ▼
               ATIVO (is_primary=False)
                  │
           ┌──────┴──────┐
           │             │
           │ promote     │ deactivate <name>
           ▼             │ (git sync + remove repo)
    ATIVO (is_primary=True)
           │             │
           │ deactivate  │
           │ (error se   │
           │ há outros   ▼
           │  ativos)  INATIVO (is_primary=False)

INATIVO ─── delete ─▶ [remove do JSON]
ATIVO ───── delete ─▶ executa deactivate + remove do JSON
```

### Definição dos Estados

| Estado | Repo em disco | is_primary | Significado |
|---|---|---|---|
| `inativo` | Não | `False` | Contexto registrado; sem repo local; sem ponteiro de workspace |
| `ativo` | Sim | `False` | Repo clonado; specs disponíveis; não é o foco primário |
| `ativo` + `is_primary=True` | Sim | `True` | Repo clonado; `primary_context.json` aponta para ele; ambiente do workspace focado aqui |

### Regras

- **`create`**: sempre começa em `inativo`.
- **`activate`**: clona repo se ausente. Marca `ativo`. Se não há contexto primário, auto-promove.
- **`promote`**: exige que o contexto seja `ativo`. Remove `is_primary` do anterior. Escreve `primary_context.json`.
- **`deactivate`**: exige que o contexto NÃO seja `is_primary` (erro se for — deve promover outro primeiro). Executa git sync. Remove repo do disco. Marca `inativo`.
- **`delete`**: se `ativo`, executa deactivate primeiro. Remove do JSON.
- Múltiplos contextos podem ser `ativo` simultaneamente.
- Somente um contexto pode ter `is_primary=True`.

---

## Ciclo de Vida de Repositórios

### activate (clone)

```
activate <name>
    ├── carregar contexto do spec_contexts.json
    ├── SE repos/<slug>/ não existe: git clone <repo_url> repos/<slug>/
    ├── resolver specs_dir = repos/<slug>/specs/ (warn se ausente)
    ├── marcar state = ativo no JSON
    ├── SE nenhum contexto é is_primary: marcar is_primary=True
    ├── SE is_primary: escrever primary_context.json
    └── salvar spec_contexts.json atomicamente
```

### deactivate (git sync + remoção)

```
deactivate <name>
    ├── verificar que contexto existe e é ativo
    ├── SE is_primary=True: ERRO → promova outro contexto primeiro
    ├── SE repos/<slug>/ existe e tem mudanças: git add -A && git commit
    ├── SE has_remote: git push → SE falhar: ABORT (não alterar estado)
    ├── remover repos/<slug>/ do disco
    ├── marcar state = inativo, is_primary = False no JSON
    └── salvar spec_contexts.json atomicamente
```

---

## Arquivos de Estado JSON

### `spec_contexts.json`

```json
{
  "version": "1",
  "contexts": [
    {
      "name": "dadaia-workspace",
      "state": "ativo",
      "is_primary": true,
      "repo_slug": "dadaia-workspace",
      "repo_url": "https://github.com/marcoaureliomenezes/dadaia-workspace.git",
      "specs_dir": "/workspace/repos/dadaia-workspace/specs",
      "created_at": "2026-05-09T10:00:00Z",
      "activated_at": "2026-05-09T10:00:00Z"
    }
  ]
}
```

Escrita sempre atômica: write to `spec_contexts.tmp` → `os.replace()` para `spec_contexts.json`.

### `primary_context.json`

```json
{
  "name": "dadaia-workspace",
  "repo_slug": "dadaia-workspace",
  "specs_dir": "/workspace/repos/dadaia-workspace/specs"
}
```

---

## Mecanismo de Descoberta de Contexto

### Hooks suportados

Runtimes com hook de prompt suportado podem executar `ctx-inject.sh` antes de processar mensagens do usuário. O stdout do script é injetado na conversa como bloco de contexto do sistema.

Configuração Claude Code instalada em `<workspace-root>/.claude/settings.json` por `dadaia public install --target claude`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [{"command": "<workspace-root>/.dadaia/scripts/sdd-spec-gate.sh", "type": "command"}],
        "matcher": ""
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [{"command": "<workspace-root>/.dadaia/scripts/ctx-inject.sh", "type": "command"}],
        "matcher": ""
      }
    ]
  }
}
```

Cada evento mapeia para um array de entradas `{matcher: string, hooks: [{type, command}]}`. O campo `matcher` é string vazia para interceptar todos os tools. Codex usa formato próprio em `.codex/hooks.json`; OpenCode não suporta hooks (ADR-UAA-004).

### Lógica de `ctx-inject.sh`

1. Se `DADAIA_CONTEXT` está definida: usar `repos/$DADAIA_CONTEXT/specs/` diretamente. Não ler `primary_context.json`.
2. Se `primary_context.json` existe: ler `name` e `specs_dir` e imprimir linha de contexto.
3. Se nenhum dos dois: imprimir que não há contexto primário ativo.

### Isolamento de sessão via `DADAIA_CONTEXT`

A env var `DADAIA_CONTEXT=<name>` tem prioridade absoluta sobre `primary_context.json` para scripts e instruções que resolvem contexto. Isso permite que sessões de Claude Code, OpenCode, Codex, bots e terminais distintos trabalhem em contextos diferentes sem conflito.

```bash
# Terminal A: usa o contexto primário global
claude

# Terminal B: sessão isolada no projeto X
DADAIA_CONTEXT=dadaia-agents claude

# Bot ao iniciar sessão do agente:
DADAIA_CONTEXT=dadaia-agents opencode
```

---

## Whitelist de Repositórios

`.dadaia/src/repos.xlsx` define os repos válidos para criação de Spec Contexts. Colunas:

| Repo Name | Repo URL | Description |
|---|---|---|
| dadaia-workspace | https://github.com/marcoaureliomenezes/dadaia-workspace.git | CLI e lib do workspace |
| dadaia-agents | https://github.com/marcoaureliomenezes/dadaia-agents.git | Agentes AI |
| portifolio | https://github.com/marcoaureliomenezes/portifolio.git | Portfólio |
| tauan-games | https://github.com/marcoaureliomenezes/tauan-games.git | Projeto de jogos |

O arquivo é distribuído com o pacote em `dadaia_workspace/public/data/repos.xlsx` e copiado para `.dadaia/src/repos.xlsx` durante `dadaia init`.

---

## `dadaia doctor`

Diagnóstico e reparo do estado do workspace.

### Verificações

1. `spec_contexts.json` é JSON válido.
2. Para cada contexto `ativo`: `repos/<slug>/` existe no disco.
3. Para cada contexto `inativo`: `repos/<slug>/` NÃO existe no disco.
4. No máximo um contexto tem `is_primary=True`.
5. `primary_context.json` existe se e somente se algum contexto tem `is_primary=True`.
6. Nenhum `repo_slug` duplicado entre contextos `ativo`.

### Ações de reparo (`--fix`)

| Issue | Ação |
|---|---|
| Contexto `ativo`, repo ausente | Re-clone via `repo_url` |
| Contexto `inativo`, repo presente | Remove repo do disco |
| `primary_context.json` ausente, is_primary no JSON | Regenera o arquivo |
| `primary_context.json` presente, sem is_primary no JSON | Deleta o arquivo |
| Múltiplos is_primary no JSON | Mantém o primeiro, remove dos demais |
| JSON malformado | Reporta; não pode auto-reparar |

---

## Contrato JSON de Descoberta (`dadaia context show --json`)

Contexto primário ativo:

```json
{
  "name": "dadaia-workspace",
  "state": "ativo",
  "is_primary": true,
  "repo_slug": "dadaia-workspace",
  "specs_dir": "/workspace/repos/dadaia-workspace/specs"
}
```

Sem contexto primário:

```json
{
  "context": null
}
```

---

## Scaffold de Specs

Quando `activate` clona um repo que não tem `repos/<slug>/specs/`: o sistema cria o diretório com um scaffold mínimo (estrutura de diretórios + `SPEC.md` template) e emite aviso. O scaffold vem de `dadaia_workspace/public/scaffold/`. O comando `create` nunca clona o repo nem cria scaffold — isso é responsabilidade exclusiva de `activate`.

---

## Ambiente Python do Workspace

- O bootstrap de `dadaia init` cria `<workspace-root>/.dadaia/.venv/`.
- Dependências Python do `dadaia-workspace` vivem dentro dessa venv.
- Após o bootstrap, agentes devem usar `<workspace-root>/.dadaia/.venv/bin/python` e `<workspace-root>/.dadaia/.venv/bin/pip`.

---

## Camada de Integração com Agentes

### Modelo em três níveis

1. **Fonte versionada no pacote:** `dadaia_workspace/public/` dentro deste repositório.
2. **Staging gerado:** `.dadaia/agentic/` no workspace runtime.
3. **Projeções runtime:** `.agents/`, `.claude/`, `.codex/`, `.opencode/`, `opencode.json` e `AGENTS.md`.

`dadaia-workspace/.agents/`, `.claude/`, `.codex/` e `.opencode/` não fazem parte do produto como source of truth local.

### Artefatos distribuídos

| Tipo | Fonte | Destino |
|---|---|---|
| Staging | `dadaia_workspace/public/` | `.dadaia/agentic/` |
| Universal instructions | `.dadaia/agentic/data/AGENTS.md` | `AGENTS.md` (workspace root) |
| Universal skills | `.dadaia/agentic/skills/` | `.agents/skills/` |
| Claude Code rules | `.dadaia/agentic/rules/` | `.claude/rules/` |
| Claude Code agents | `.dadaia/agentic/agents/` | `.claude/agents/` |
| Claude Code commands | `.dadaia/agentic/commands/` | `.claude/commands/` |
| Claude Code skills | `.dadaia/agentic/skills/` | `.claude/skills/` |
| Claude Code hooks | `_claude_settings()` (generated) | `.claude/settings.json` |
| Codex rules | `.dadaia/agentic/rules/` | `.codex/rules/` |
| Codex hooks | `_codex_hooks()` (generated) | `.codex/hooks.json` |
| Codex skills | `.dadaia/agentic/skills/` | `.agents/skills/` (shared) |
| OpenCode agents | `.dadaia/agentic/agents/` | `.opencode/agents/` |
| OpenCode commands | `.dadaia/agentic/commands/` | `.opencode/commands/` |
| OpenCode skills | `.dadaia/agentic/skills/` | `.opencode/skills/` |
| OpenCode config | `_opencode_config()` (generated) | `opencode.json` |
| Scripts | `.dadaia/agentic/scripts/` | `.dadaia/scripts/` |

### Agentes especializados

4 agentes especializados são versionados em `dadaia_workspace/public/agents/` e projetados para runtimes conforme suporte nativo:

| Agente | Papel | Escreve somente em |
|---|---|---|
| `architect-agent` | Revisão de arquitetura e qualidade de código | `.dadaia/reports/architect-agent-review/` |
| `product-auditor-agent` | Auditoria de specs vs. implementação | `.dadaia/reports/specs-sdd-review/` |
| `product-engineer-agent` | Refinamento de Specs, Plans e Tasks | `specs/` do repositório em contexto |
| `soft-engineer-agent` | Implementação SDD+TDD + bug reports | código + `.dadaia/reports/bugs/soft-engineer-report/` |

A skill `dadaia-grill-me` é instalada em `.agents/skills/` e compartilhada pelo `architect-agent` e `product-auditor-agent` para revisão crítica de specs.

### Descoberta do contexto primário

O mecanismo universal de descoberta é a CLI. Runtimes com hook suportado podem receber contexto automaticamente; todos os runtimes devem conseguir resolver o contexto com:

```bash
dadaia context list
dadaia context show --json
```

Agentes não devem ler `primary_context.json` diretamente quando `dadaia context show --json` estiver disponível.

---

## dadaia-academy

### Modelo de dois componentes

1. **Knowledge basis** (imutável, no pacote): `dadaia_workspace/features/academy/knowledge_basis/` — 6 módulos de conteúdo de aprendizagem. Nunca copiado para o workspace do usuário.
2. **Working copies** (no workspace): `.dadaia/academy/<slug>/` — cópias criadas pelo operador via `dadaia academy create`.

### Estado persistido

`.dadaia/states/academy.json` — lista de cursos ativos. Escrito atomicamente.

### Interface

- **CLI** (`dadaia academy list/create/delete/update/modules`): CRUD de cursos — Python puro, sem LLM.
- **Slash command** (`/dadaia-academy`): Claude lê o conteúdo do curso e tutora/personaliza com base no prompt do usuário.
