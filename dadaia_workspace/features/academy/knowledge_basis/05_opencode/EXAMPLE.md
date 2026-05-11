# Exemplo Pratico - Criando um Command Reutilizavel no Open Code

O melhor jeito de entender o Open Code e ver como ele transforma um prompt recorrente em asset reutilizavel.

## Cenario

Voce revisa specs com frequencia e quer um command local que sempre:

- leia a spec principal;
- considere o estado recente do git;
- e devolva riscos e inconsistencias antes de qualquer implementacao.

## Passo 1: Crie um command em markdown

Crie `.opencode/commands/review-spec.md` com esta estrutura:

```md
---
description: Revisar a spec ativa com foco em coerencia e riscos
agent: plan
---
Leia @specs/SPEC.md.

Considere tambem o estado recente do projeto:
!`git diff --stat`

Entregue:
1. inconsistencias de contrato
2. riscos de implementacao
3. perguntas em aberto
```

## Passo 2: Execute o command

Dentro do TUI, rode:

```text
/review-spec
```

O que acontece:

- o nome do arquivo vira o nome do command;
- `description` aparece na interface;
- `@specs/SPEC.md` injeta o arquivo na prompt;
- `!git diff --stat` injeta output de shell;
- `agent: plan` pode direcionar o workflow para um agente mais apropriado.

## Passo 3: Entenda o ganho estrutural

Voce nao criou apenas um atalho. Criou um asset operacional:

- versionavel;
- revisavel;
- reproduzivel por outras pessoas;
- e adaptavel por projeto.

## Passo 4: Aproveite compatibilidade com `.claude`

Se seu ambiente ja usa `CLAUDE.md` e `.claude/skills`, o Open Code pode aproveitar parte desse ecossistema como fallback, a menos que isso seja explicitamente desabilitado por variaveis como `OPENCODE_DISABLE_CLAUDE_CODE`.

Esse detalhe e importante em migracoes ou ambientes mistos.

## O que este exemplo fixa

1. Open Code transforma workflow em configuracao reutilizavel com pouco atrito.
2. Commands customizados podem combinar prompt, arquivos e shell output.
3. Compatibilidade com `.claude` reduz custo de adocao em ambientes existentes.
4. O maior ganho do Open Code nao e a interface, mas a operacionalizacao de comportamento repetivel.