# 03. Hooks, Memoria, Message e Operacao Segura

Consulta oficial: 2026-05-09.

## Hooks como automacao orientada a evento

OpenClaw tem superficie de hooks para eventos de comando e startup.

Comandos uteis:

```bash
openclaw hooks list
openclaw hooks check
openclaw hooks info session-memory
openclaw hooks enable session-memory
openclaw hooks disable command-logger
```

Hook habilitado so passa a valer apos reload/restart do gateway.

## Memoria semantica

Comandos principais:

```bash
openclaw memory status
openclaw memory status --deep
openclaw memory index --force
openclaw memory search "deployment"
openclaw memory promote --limit 10
```

No modo promote, faca preview antes de `--apply`.

## Message CLI para canais

`openclaw message` centraliza envio e acoes multi-canal.

Exemplo envio:

```bash
openclaw message send --channel telegram --target @mychat --message "oi"
```

Exemplo poll:

```bash
openclaw message poll --channel discord \
  --target channel:123 \
  --poll-question "Lunch?" \
  --poll-option Pizza --poll-option Sushi
```

## SecretRef e fail-closed

A documentacao destaca comportamento fail-closed para segredos nao resolvidos
no escopo da acao alvo. Isso e essencial para evitar envio com credencial errada.

## Checklist de operacao segura

1. Sempre explicitar `--channel` quando houver multiplos canais.
2. Evitar config aberta sem allowlists.
3. Revisar hooks ativos (`openclaw hooks list --verbose`).
4. Tratar `memory promote` como alteracao de estado duravel.
5. Usar `--json` em automacao para evitar parsing fragil.

## Padrao de troubleshooting

- falha de envio: validar target + channel + credencial do canal;
- falha de auth modelo: `models status --probe`;
- sessao estranha: `sessions --agent ...` + cleanup dry-run;
- comportamento inesperado: hooks ativos + config efetiva.
