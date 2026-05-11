# 01. Onboarding e Setup Local

Consulta oficial: 2026-05-09.

## O que OpenClaw e

OpenClaw e um gateway self-hosted que conecta canais (Telegram, WhatsApp,
Discord, Slack e outros) a agentes com workspace, sessoes e roteamento.

## Caminho rapido de setup

Fluxo guiado:

```bash
openclaw onboard
```

Para automacao:

```bash
openclaw onboard --non-interactive \
  --mode local \
  --auth-choice apiKey \
  --secret-input-mode plaintext
```

## O que o wizard configura

- autenticacao e provider/modelo;
- workspace do agente;
- gateway (porta, bind, auth);
- canais e credenciais;
- daemon local (quando aplicavel);
- health check inicial;
- skills opcionais.

## Seguranca ja no primeiro dia

Regras praticas:

1. Nao deixe DM aberto para qualquer origem.
2. Use allowlist por canal (exemplo WhatsApp/Telegram).
3. Mantenha auth do gateway ligada, mesmo em loopback.
4. Prefira refs de secrets quando o ambiente exigir.

## Setup de assistente pessoal

No fluxo de personal assistant, o proprio OpenClaw destaca:

- usar numero dedicado no WhatsApp;
- limitar `allowFrom`;
- comecar com heartbeat desabilitado ate ganhar confianca.

## Artefatos importantes no disco

- `~/.openclaw/openclaw.json` (config)
- `~/.openclaw/agents/<agentId>/...` (estado por agente)
- `~/.openclaw/workspace` (workspace default)

## Check inicial de saude

```bash
openclaw status
openclaw status --deep
openclaw health --json
```

Se onboarding falhar, rode:

```bash
openclaw doctor
```
