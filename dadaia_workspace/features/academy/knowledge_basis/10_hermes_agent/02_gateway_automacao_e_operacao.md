# 02. Gateway, Automacao e Operacao

Consulta oficial: 2026-05-09.

## Quando entrar em gateway

So depois do chat CLI base estar estavel.

Comando inicial:

```bash
hermes gateway setup
```

## Casos comuns de gateway

- bot em Telegram/Discord/Slack/WhatsApp;
- assistente always-on;
- fluxo com alertas e rotinas periodicas.

## Postura de seguranca inicial

1. comecar conservador;
2. restringir origem de mensagens quando aplicavel;
3. evitar abrir ferramenta sem politica clara;
4. testar health/status antes de expor para uso continuo.

## Automacao em camadas

Depois do baseline:

- tools: ajustar permissoes por plataforma;
- skills: instalar fluxos reutilizaveis;
- cron: habilitar somente com operacao estavel;
- backend de terminal: considerar docker/ssh para isolamento.

Exemplos de config:

```bash
hermes config set terminal.backend docker
hermes config set terminal.backend ssh
```

## Operacao de saude

Rotina minima:

- verificar status do gateway
- confirmar sessao ativa
- monitorar erros de auth/token
- validar canal de entrada e canal de saida

## Anti-padroes

1. subir gateway sem validar chat local;
2. habilitar automacao e cron cedo demais;
3. misturar falha de canal com falha de provider;
4. operar sem checklist de recovery.
