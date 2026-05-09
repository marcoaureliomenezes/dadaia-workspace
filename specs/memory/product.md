# Product: dadaia-workspace

## O que é

**dadaia-workspace** é uma biblioteca Python com CLI para criar um workspace AI-native guiado por SDD. O produto organiza:

- um workspace runtime fora do repositório da biblioteca;
- o estado de Spec Context Projects em um arquivo JSON de fácil leitura e reparo;
- o ciclo de vida de repositórios (clone ao ativar, sincronização e remoção ao desativar);
- os artefatos de agente instalados no `.claude/` do workspace.

---

## Problema que Resolve

Times e agentes de IA perdem consistência quando o contexto de trabalho se espalha por múltiplos repositórios sem controle. Sem um contrato explícito, decisões de escopo ficam implícitas:

- qual repo é o foco corrente;
- onde ficam as specs;
- qual contexto é primário;
- e quais repos estão presentes em disco.

O dadaia-workspace resolve isso com **Spec Context Projects** que registram, clonam e mantêm repositórios de forma rastreável, com um contexto primário que orienta o ambiente do workspace automaticamente.

---

## Usuários

| Usuário | Como usa |
|---|---|
| Engenheiro de software | Inicializa workspace, cria contextos, ativa/desativa repos, promove primário, instala artefatos de agente |
| Agente de IA | Descobre contexto primário via hook automático ou CLI estável, carrega specs, segue rules/skills instalados |
| Mantenedor do produto | Versiona artefatos em `dadaia_workspace/public/`, valida extração para `.claude/` do workspace, governa o padrão SDD |

---

## Conceitos Chave

### Workspace
Diretório de trabalho do usuário, fora do repositório da biblioteca, inicializado por `dadaia init` com `.dadaia/` e `.claude/` prontos para uso.

### Template `.dadaia`
Estrutura canônica de runtime do workspace. Contém o JSON de estado, scripts de automação, whitelist de repos e a venv isolada do workspace.

### Ambiente Python Isolado
Venv em `<workspace-root>/.dadaia/.venv/`, usada por automações e agentes para manter as dependências do `dadaia-workspace` isoladas.

### Spec Context Project
Entidade que representa um foco de trabalho SDD com:
- nome único;
- estado (`inativo` ou `ativo`);
- flag `is_primary` (somente um contexto pode ser primário ao mesmo tempo);
- repositório associado (`repo_slug` + `repo_url`);
- estado do repo em disco (clonado quando `ativo`, removido quando `inativo`).

### Whitelist de Repositórios
Arquivo Excel em `.dadaia/src/repos.xlsx` com colunas `Repo Name`, `Repo URL`, `Description`. Define os repos válidos para criação de contextos. Distribuído com o pacote e copiado ao inicializar o workspace.

### Ciclo de Vida de Repositórios
- **activate**: garante que o repo está clonado localmente em `repos/<slug>/`. Se ausente, clona automaticamente a partir de `repo_url`.
- **deactivate**: executa commit+push obrigatório no repo (para evitar perda de dados), depois remove `repos/<slug>/` do disco.

### Primário (`is_primary`)
O contexto primário é o único que o ambiente do workspace aponta automaticamente. O hook `UserPromptSubmit` lê `primary_context.json` e injeta o contexto primário em cada mensagem do agente. Somente um contexto pode ser primário. O operador promove um contexto ativo a primário via `dadaia context promote`.

### `dadaia doctor`
Comando de diagnóstico e reparo do estado do workspace. Verifica se o estado em `spec_contexts.json` é consistente com o disco (repos presentes/ausentes, primary_context.json correto) e, com `--fix`, repara automaticamente o que conseguir.

### Artefatos de Agente
Rules, skills e workflows versionados em `dadaia_workspace/public/` e instalados no workspace do usuário em `.claude/`. O repositório da biblioteca não mantém uma `.claude/` própria.

---

## Proposta de Valor

- **Para o engenheiro:** ciclo de vida de repos controlado — sem repos desnecessários em disco; sem perda de dados na remoção.
- **Para agentes de IA:** contexto primário injetado automaticamente em cada sessão; specs sempre na fonte canônica.
- **Para o produto:** estado simples em JSON — legível, reparável, sem dependências de banco de dados.
- **Para operações:** `dadaia doctor` permite reparar estado corrompido sem recriar o workspace do zero.
