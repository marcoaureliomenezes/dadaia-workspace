# 02. CLI: Agents, Models e Sessions

Consulta oficial: 2026-05-09.

## Agents isolados por workspace

OpenClaw permite criar agentes separados com workspace, sessoes e auth proprios.

Exemplo:

```bash
openclaw agents add work \
  --workspace ~/.openclaw/workspace-work \
  --model openai/gpt-5.5 \
  --non-interactive
```

Comandos base:

- `openclaw agents list`
- `openclaw agents bindings`
- `openclaw agents bind --agent <id> --bind <canal[:conta]>`
- `openclaw agents unbind ...`
- `openclaw agents delete <id>`

## Bindings e roteamento

Binding define para qual agente vai o trafego de um canal/conta.

Exemplo:

```bash
openclaw agents bind --agent work --bind telegram:ops
```

## Models e auth profiles

Comandos centrais:

```bash
openclaw models status
openclaw models list
openclaw models set <provider/model>
openclaw models scan
openclaw models auth list --provider openai-codex
```

`models status --probe` faz teste real de auth/modelo e pode consumir tokens.

## Sessions

Comandos principais:

```bash
openclaw sessions
openclaw sessions --agent work
openclaw sessions --all-agents
openclaw sessions --json
```

Manutencao:

```bash
openclaw sessions cleanup --dry-run
openclaw sessions cleanup --enforce
```

## Diagnostico padrao de operacao

Quando algo parece errado, ordem util:

1. `openclaw models status --probe`
2. `openclaw agents list --bindings`
3. `openclaw sessions --agent <id>`
4. `openclaw status --deep`

Isso reduz tentativa-cega e mostra onde o problema realmente esta.
