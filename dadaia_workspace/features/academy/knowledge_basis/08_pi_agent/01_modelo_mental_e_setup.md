# 01. Modelo Mental e Setup

Consulta oficial: 2026-05-09.

## O que e o Pi

Pi e um coding harness de terminal com nucleo pequeno. Ele evita virar um
monolito de features internas e empurra personalizacao para extensoes, skills,
prompt templates e packages.

Regra pratica: o Pi entrega o motor; o workflow e seu.

## Instalacao rapida

Opcao curl:

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

Opcao npm:

```bash
npm install -g @earendil-works/pi-coding-agent
```

Depois:

```bash
cd /caminho/do/projeto
pi
```

## Autenticacao

Voce pode autenticar por assinatura (`/login`) ou API key no ambiente.

Exemplo API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pi
```

## Primeira sessao util

Exemplo de prompt inicial:

```text
Summarize this repository and tell me how to run its checks.
```

Em setup default, Pi expoe ferramentas principais para ciclo de trabalho:

- read
- write
- edit
- bash

Ferramentas de leitura como grep/find/ls podem ser liberadas por opcoes.

## AGENTS.md como contrato do projeto

Pi carrega contexto de `AGENTS.md` e `CLAUDE.md` do global e da arvore atual.

Regra operacional:

- politica de projeto vai em `AGENTS.md`;
- regra global de usuario vai em `~/.pi/agent/AGENTS.md`;
- sempre reinicie ou use `/reload` apos alterar contexto.

## Erros comuns no setup

1. Instalar e ja sair pedindo mudanca sem validar autenticacao.
2. Rodar em diretorio errado e achar que o Pi perdeu contexto.
3. Esquecer AGENTS.md e culpar o modelo por resposta inconsistente.

## Checklist de pronto

- `pi` inicia sem erro.
- `/login` ou API key estao validos.
- primeira resposta vem sem erro de provider.
- `AGENTS.md` do projeto esta sendo carregado.
