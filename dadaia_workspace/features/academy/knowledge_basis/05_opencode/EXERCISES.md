# Exercicios e Checkpoints — Sessao 3: Open Code Quick Start

Estes exercicios consolidam a operacao pratica do Open Code: CLI, commands, rules e controle de permissao.

---

## Exercicio 1 — Explore o CLI

**Objetivo:** Mapear os modos de operacao do Open Code antes de usar qualquer um.

**Instrucao:**

No terminal, execute:

```bash
opencode --help
```

Liste por escrito os modos ou subcomandos disponíveis e descreva em uma frase o que cada um faz.

Depois execute o mesmo para o modo run, se disponivel:

```bash
opencode run --help
```

**Criterio de validacao:**

Voce passou se conseguir responder sem hesitacao:

- Qual modo e interativo (TUI)?
- Qual modo executa um comando e encerra automaticamente?
- Como voce passaria um prompt via linha de comando sem abrir o modo interativo?

---

## Exercicio 2 — Crie um Command Customizado

**Objetivo:** Praticar a estrutura de frontmatter e o fluxo de ativacao de commands no Open Code.

**Instrucao:**

Crie um arquivo `.claude/commands/listar-contextos.md` com conteudo similar ao abaixo:

```markdown
---
description: Lista os repositorios materializados no workspace atual.
---

## Passos

1. Execute `ls .dadaia/contexts/` para listar os contextos disponíveis.
2. Para cada contexto encontrado, informe o nome do repositorio.
3. Se `.dadaia/contexts/` estiver vazio, informe que nenhum contexto foi materializado.
```

Depois test no Open Code:

```text
/listar-contextos
```

**Criterio de validacao:**

O agente executou o fluxo e listou os contextos ou informou que estao vazios.
Se ele nao reconheceu o command, verifique o frontmatter.

Apos o exercicio, voce pode deletar o arquivo se nao quiser manter.

---

## Exercicio 3 — Compatibilidade com .claude/

**Objetivo:** Confirmar que commands existentes em `.claude/` sao acessíveis no Open Code.

**Instrucao:**

Abra o Open Code no diretorio do workspace e tente invocar:

```text
/dadaia-academy
```

Observe se o agente reconheceu o command que vive em `.claude/commands/dadaia-academy.md`.

**Criterio de validacao:**

Voce passou se o agente iniciou o fluxo de navegacao da Academy.
Se ele nao reconheceu, verifique se o Open Code esta com as configuracoes de compatibilidade com `.claude/` ativas.

---

## Exercicio 4 — Modo Nao Interativo

**Objetivo:** Usar o Open Code para executar uma tarefa simples sem abrir o TUI.

**Instrucao:**

Execute no terminal:

```bash
opencode run "Liste os arquivos em .claude/commands/ e retorne apenas os nomes, um por linha."
```

Observe o output.

**Criterio de validacao:**

Voce passou se recebeu uma lista de nomes de arquivos no terminal sem precisar abrir o modo interativo.
Se o tool retornou erro, verifique se o Open Code esta instalado e autenticado corretamente.

---

## Checkpoint Final — Sessao 3

Voce esta pronto para avancar para a Sessao 4 se:

- [ ] Sabe a diferenca entre modo interativo (TUI) e modo `run` do Open Code
- [ ] Criou e invocou um command customizado com frontmatter
- [ ] Confirmou compatibilidade com commands existentes em `.claude/`
- [ ] Executou uma tarefa em modo nao interativo e recebeu output util

Se algum item ficou incompleto, volte para o modulo especifico antes de continuar.
