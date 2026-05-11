# 01. Quickstart, Modelos e Config

Consulta oficial: 2026-05-09.

## Instalacao curta

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

## Regra de ouro do quickstart

Primeiro faca um chat simples funcionar. Depois adicione gateway, cron, skills e
camadas avancadas.

## Escolha de provider/modelo

Comando principal:

```bash
hermes model
```

A documentacao destaca que Hermes separa:

- secrets em `~/.hermes/.env`
- config nao sensivel em `~/.hermes/config.yaml`

## Requisito importante de contexto

Hermes exige modelo com contexto minimo de 64k tokens para workflows mais
longos de tool calling.

## Primeiro chat validado

```bash
hermes
# ou
hermes --tui
```

Sinais de sucesso:

- banner mostra provider/modelo correto;
- resposta sem erro de auth;
- fluxo continua em mais de um turno.

## Sessao e continuidade

```bash
hermes --continue
hermes -c
```

Se continuidade falhar, valide profile e store de sessao antes de culpar modelo.

## Recovery sequence recomendada

1. `hermes doctor`
2. `hermes model`
3. `hermes setup`
4. `hermes sessions list`
5. `hermes --continue`
