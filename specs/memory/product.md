# Product: dadaia-workspace

## O que é

**dadaia-workspace** é uma biblioteca Python com CLI para criar um workspace AI-native guiado por SDD. O produto organiza:

- um workspace runtime fora do repositório da biblioteca;
- o estado do workspace;
- os Spec Context Projects;
- os clones gerenciados necessários para cada contexto;
- e os artefatos de agente instalados no `.claude/` do workspace.
- e o material de aprendizagem da Dadaia Academy em `.dadaia/academy/`.

---

## Problema que Resolve

Times e agentes de IA perdem consistência quando o contexto de trabalho se espalha por múltiplos repositórios e por múltiplas sessões. Sem um contrato explícito, a implementação tende a decidir no código:

- qual repo é o foco;
- onde ficam as specs;
- qual contexto está ativo;
- e quais regras de agente precisam estar carregadas.

O dadaia-workspace resolve isso com um **Spec Context Project** que registra e materializa esse foco de trabalho de forma rastreável e previsível.

O produto também precisa reduzir a fricção de onboarding e de evolução de prática. Por isso, a **Dadaia Academy** funciona como a camada de aprendizagem do workspace: um conjunto de sessões, exemplos e referências que ensina o usuário a operar o próprio produto e o ecossistema agentic ao redor dele.

---

## Usuários

| Usuário | Como usa |
|---|---|
| Engenheiro de software | Inicializa workspace, cria contextos, ativa contextos, instala artefatos de agente e usa a Dadaia Academy para aprender o fluxo do produto |
| Agente de IA | Descobre contexto ativo via CLI estável, carrega specs, segue rules/skills instalados e futuramente aciona `/dadaia-academy` para gerar cursos vivos |
| Mantenedor do produto | Versiona artefatos em `dadaia_workspace/public/`, valida a extração para `.claude/` do workspace, governa o padrão SDD e evolui o material base da academy |

---

## Conceitos Chave

### Workspace
Diretório de trabalho do usuário, fora do repositório da biblioteca, inicializado por `dadaia init` com `.dadaia/` e `.claude/` prontos para uso.

### Template `.dadaia`
Estrutura canônica de runtime do workspace. Ela contém estado persistido, relatórios, catálogo consultivo, área efêmera para agentes e a venv isolada do workspace.

### Ambiente Python Isolado
Venv localizada em `<workspace-root>/.dadaia/.venv/`, usada por automações e por agentes para manter as dependências do `dadaia-workspace` isoladas.

### Spec Context Project
Entidade que representa um foco de trabalho SDD com:
- nome único;
- estado (`inativo`, `standby`, `ativo`);
- repositório principal;
- repositórios secundários;
- materialização gerenciada dentro de `.dadaia/contexts/`.

### Artefatos de Agente
Rules, skills e workflows versionados neste repositório em `dadaia_workspace/public/` e instalados no workspace do usuário em `.claude/`. O repositório da biblioteca não mantém uma `.claude/` própria como fonte de verdade do produto.

### Dadaia Academy
Camada de aprendizagem do workspace. No runtime atual, o material base da academy vive em `<workspace-root>/.dadaia/academy/` como sessões numeradas, exemplos e referências. Em fases posteriores, esse conteúdo poderá ser promovido para assets versionados do produto e consumido por slash commands e skills especializados.

---

## Proposta de Valor

- **Para o engenheiro:** contexto de trabalho multi-repo organizado sem decisões implícitas em disco.
- **Para agentes de IA:** descoberta estável de contexto e regras sempre presentes para evitar implementação fora do SDD.
- **Para o produto:** evolução segura das specs com revisão sistemática antes de qualquer código.
- **Para onboarding e capacitação:** material vivo e prático para aprender o workspace e o ecossistema agentic usando o próprio runtime do produto.
