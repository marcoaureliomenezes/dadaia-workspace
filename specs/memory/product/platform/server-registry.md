---
slug: server-registry
title: server-registry
category: product
tldr: registry interno de portas (3000-3999) com TTL+PID para evitar conflito entre
  dev servers de agentes paralelos.
summary: registry interno de portas (3000-3999) com TTL+PID para evitar conflito entre
  dev servers de agentes paralelos.
tags:
- server
- registry
- ports
- ttl
agent_tier: self-pull
token_estimate: 626
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia server {list,register,unregister,clean,scan}` · Closure: v0.1.1 (hotfix)

## Propósito

Registry interno de portas (range 3000-3999) associadas a projetos, com TTL e PID tracking. Previne conflito de portas entre dev servers spawnados em paralelo por agentes diferentes (ex. `web-app` em 3001, `api-service` em 3002) e permite a outras sessões descobrir a URL ativa de um projeto sem hardcoding.

Sweeper automático expira entradas com TTL vencido ou cujo PID não está mais vivo (resistente a entries malformados via skip-and-log) — preserva root-owned PIDs (e.g. docker-proxy) diferenciando `PermissionError` ("alive but unprobable") de `ProcessLookupError` ("dead").

O subcomando `dadaia server scan` reconcilia o registry com listeners reais do SO: faz parse de `ss -tlnp` filtrado pelo uid do operador, lista portas que estão em LISTEN sem entry correspondente no registry e marca `lan_exposed` para binds `0.0.0.0`.

## Fluxo de uso

  1. Um agente ou script spawna um dev server e registra a porta: `register(port=3001, project="web-app", pid=os.getpid(), ttl_hours=8)`.
  2. Outras sessões consultam: `get(port=3001)` → `PortEntry(url="http://localhost:3001", project, pid, expires_at)`.
  3. Antes de spawnar nova porta: `next()` retorna a próxima livre no range.
  4. Sweeper roda periodicamente removendo entradas com PID morto (ProcessLookupError) ou TTL expirado; PIDs unprobable (PermissionError, e.g. root) permanecem ativos.
  5. **Reconciliação manual** : `dadaia server scan` (read-only) lista orphans — listeners não-registrados — com port/bind/pid/cmdline/cwd/lan_exposed. Operador chama `dadaia server register --port <p> --project <name> --pid <pid>` para mover orphan → registry.



## Trigger típico

Quando agentes ou scripts spawn dev servers locais e precisam coordenar para não colidir em porta. `dadaia server scan` é invocado quando o operador suspeita de listener fantasma (porta consumida mas ausente do `list` + panel).

## Diferencial

Sem o registry, agentes paralelos sobreescreveriam portas uns dos outros — bug não-determinístico e difícil de diagnosticar. TTL + PID tracking evita slot leak quando processos morrem inesperadamente; semântica correta de `PermissionError` evita que root-owned PIDs (docker-proxy) sejam auto-swept; resilience do store (skip-and-log per-entry) evita que um único JSON malformado quebre `list_all()` inteiro; `scan` dá observabilidade sobre listeners que ficaram fora do registry (push-only era invisível, agora reconciliável).

## Estado runtime tocado

  * **Read+Write** : `.dadaia/states/server_registry.json` — array de PortEntry com TTL+PID. Load resiliente: `JSONDecodeError` ou per-entry `KeyError/TypeError/ValueError` emitem warning estruturado `registry_entry_malformed` + skip; nunca raise.
  * **Read** : `ss -tlnp` via subprocess (filtrado por uid do user atual; portas <1024 skipped); `/proc/<pid>/cmdline` e `/proc/<pid>/cwd` para enriquecer orphans. Se `ss` ausente: retorna lista vazia + warning.
  * **Resolver** : `resolve_workspace_root(cwd)` em `core/workspace_resolver.py` exige `.dadaia/states/spec_contexts.json` (não apenas `.dadaia/`), evitando que sub-repos com projeção agentic confundam o walk-up.



## Dependências

  * Standalone — não depende de outras features além da estrutura criada por [[workspace-init]].
  * Consumido por [[panel]]: aba Servers lê `list_all()` via `ServerRegistryService` e `list_unregistered_listeners()` via `PanelService`; `/api/servers` retorna `{groups: [...], unregistered: [...]}`.
  * Stdlib only: `subprocess` para `ss`, `pathlib`, `json`, `dataclasses`.
