# 03. Customizacao: Extensions, Skills e Packages

Consulta oficial: 2026-05-09.

## Filosofia de extensao do Pi

Pi intencionalmente nao inclui tudo no core. Em vez disso, voce compoe o
ambiente com recursos carregaveis.

Blocos principais:

- extensions (TypeScript, ferramentas/eventos/UI);
- skills (capabilidades reutilizaveis);
- prompt templates;
- themes;
- packages (empacotam assets).

## Carregamento controlado

Flags uteis para controlar exatamente o que entra:

```bash
pi --no-extensions -e ./minha-extension.ts
pi --skill ./skills/meu-skill
pi --prompt-template ./prompts/review.md
```

Regra: em debugging, desligue auto-discovery e carregue so o minimo.

## Built-in tools e allowlist

Pi permite restringir ferramentas por execucao:

```bash
pi --tools read,grep,find,ls -p "Audit this repo"
pi --no-tools -p "Only reason over provided text"
```

Isso e util para:

- auditoria segura;
- reproducao de bugs;
- evitar writes acidentais.

## Packages

Comandos de pacote no CLI:

```bash
pi install <source>
pi update
pi list
pi remove <source>
```

Use package quando o workflow precisa ser compartilhado entre maquinas/time.

## System prompt e contexto

Voce pode substituir ou complementar system prompt por flag:

```bash
pi --system-prompt "You are a strict reviewer"
pi --append-system-prompt "Always cite file paths"
```

E pode usar arquivos de sistema:

- `.pi/SYSTEM.md` (projeto)
- `~/.pi/agent/SYSTEM.md` (global)

## Quando usar o que

- ajuste pontual: slash command;
- politica persistente: AGENTS.md;
- fluxo reutilizavel: skill;
- integracao robusta com tools/UI: extension;
- distribuicao de stack: package.

## Antipadroes

1. Criar extension para algo que um AGENTS.md simples resolve.
2. Ligar muitas extensoes sem isolamento e culpar o modelo por conflito.
3. Nao versionar skills/prompts e perder reprodutibilidade.
4. Misturar objetivo de produto com ajuste local de terminal.
