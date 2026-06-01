---
slug: specs-doctor
title: specs-doctor
category: product
tldr: '19 checks estruturais SDD: 12 SPEC-DOC (memory HTML atômico, ACTIVE.md, CLOSURE
  evidence triples, broken images, Mermaid script, D-OC-1 bidirectional) + 7 TR...'
summary: '19 checks estruturais SDD: 12 SPEC-DOC (memory HTML atômico, ACTIVE.md,
  CLOSURE evidence triples, broken images, Mermaid script, D-OC-1 bidirectional) +
  7 TREE-1..7 (canonical tree v2 shape: foundation depreciada, root SPEC.md depreciado,
  product/index.html, backlog/bugs/releases dirs, AGENTS.md, release artifacts, bug
  frontmatter). --fix auto-repara TREE-3/4; migration guard para TREE-1/2.'
tags:
- specs
- doctor
- validation
- sdd
agent_tier: self-pull
token_estimate: 1073
last_updated: '2026-06-01'
release_origin: panel-kanban-v1
---

CLI surface: `dadaia specs doctor [--specs-dir PATH] [--json] [--fix]` · Closure: memory-structured-source-v1

## Propósito

Valida invariantes estruturais do diretório `specs/` sob o modelo SDD release-lifecycle. Três grupos de checks:

  * **SPEC-DOC-001..012** (12 checks): presença de `constitution.md`, memory HTML com folder catalog em `product/`, `ACTIVE.md` bem formada, status canônicos, PLAN ≤ 300 linhas, CLOSURE com evidence triples, atomicidade do memory sem changelog, links de imagem resolvendo, presença do script Mermaid quando há diagramas, link integrity do `product/index.html` para suas feature HTMLs, e o invariante **D-OC-1** bidirectional orchestration registry consistency.
  * **TREE-1..7** (7 checks): canonical `specs/` tree v2 shape.
  * **STRUCT-1..4, SYNC-1, YAML-absent guard** (6 checks, added in memory-structured-source-v1): schema-based validation of YAML memory atoms and committed-HTML sync — see below.



Exit code 1 se houver errors; 0 se só warnings ou tudo verde. Suporta `--json` para integração com CI/automação e `--fix` para auto-repair dos invariantes tratáveis.

### Invariantes STRUCT-1..4 + SYNC-1 + YAML-absent guard (memory-structured-source-v1)

Código| O que detecta| Severity| Notas  
---|---|---|---  
STRUCT-1| YAML atom `specs/memory/architecture.yaml` falha schema validation| ERROR| Extra field (incl. `changelog`) ou campo obrigatório ausente  
STRUCT-2| YAML atom `specs/memory/tech-stack.yaml` falha schema validation| ERROR| Idem  
STRUCT-3| YAML atom `specs/memory/product/index.yaml` falha schema validation| ERROR| Idem; inclui `rank` e `keywords` como campos required por entry  
STRUCT-4| Qualquer YAML atom em `specs/memory/product/<slug>.yaml` falha schema validation| ERROR| Os 6 campos required: `purpose`, `flow_steps`, `typical_trigger`, `differential`, `runtime_state`, `dependencies`  
SYNC-1| Committed HTML diverge do renderer output para um YAML atom válido| WARN| Indica que `dadaia memory render` não foi rodado após edição do YAML; nomeia o(s) atom(s) específico(s)  
YAML-absent| Nenhum YAML source presente para um atom (atom ainda em HTML-source)| WARN| Mensagem inclui `dadaia migrate memory-yaml`; STRUCT e SYNC pulados; check #8 (changelog grep) continua ativo para esses atoms; `dadaia specs doctor` exits 0  
  
Quando YAML source existe e passa STRUCT validation, o check #8 (heurística grep-for-"Changelog" no HTML) é suprimido — o schema enforça atomicidade estruturalmente.

### Invariantes TREE-1..7 (canonical tree v2)

Código| O que detecta| Severity| `--fix` policy  
---|---|---|---  
TREE-1| Diretório `specs/foundation/` presente (depreciado)| WARN| warn-only; **migration guard** impresso independente de `--fix` — instrução: `dadaia migrate tree-v2`  
TREE-2| Arquivo `specs/SPEC.md` na raiz (pre-release-model)| WARN| warn-only; **migration guard** impresso — instrução: `dadaia migrate tree-v2`  
TREE-3| `specs/memory/product/index.html` ausente| ERROR| **auto-fix** : regenera `index.html` vazio do template canônico  
TREE-4| Um ou mais de `specs/backlog/`, `specs/bugs/`, `specs/releases/` ausentes| ERROR| **auto-fix** : recria diretório(s) ausente(s) com `.gitkeep`  
TREE-5| `specs/AGENTS.md` ausente (drift em relação ao template canônico)| WARN| warn-only (sem auto-overwrite — arquivo pode ter customizações do consumer)  
TREE-6| Diretório de release em `specs/releases/` sem pelo menos um artefato SDD obrigatório (`SPEC.md`)| ERROR| no-fix (decisão humana)  
TREE-7| Arquivo de bug em `specs/bugs/` sem campo `session_id` no frontmatter| ERROR| no-fix (campo requer valor real)  
  
**Migration guard (TREE-1/2):** quando detectados, o doctor imprime a mensagem de migration guard independentemente do flag `--fix` — o auto-move de `foundation/` e root `SPEC.md` para `releases/legacy/` é feito exclusivamente por `dadaia migrate tree-v2`.

## Fluxo de uso

  1. `dadaia specs doctor` — resolve `specs_dir` via `primary_context.json` ou `--specs-dir`, roda todos os checks em ordem (12 SPEC-DOC + 7 TREE + STRUCT/SYNC/YAML-absent para atoms com YAML source), exibe issues formatados com código + severity + path. Para atoms sem YAML source: emite YAML-absent WARN e continua — `dadaia specs doctor` exits 0.
  2. `dadaia specs doctor --fix` — executa os checks e auto-repara os invariantes com policy `auto-fix` (TREE-3, TREE-4); emite migration guard para TREE-1/2; deixa TREE-5..7 como warnings/errors sem alterar arquivos.
  3. Para automação: `dadaia specs doctor --json` emite payload `{specs_dir, issues[], summary{errors, warnings}}`.
  4. Em CI: usado como gate de PR para bloquear merge se houver erros estruturais nos specs.



Códigos de erro: `SPEC-DOC-001` a `SPEC-DOC-012` + `D-OC-1` (bidirectional orchestration registry consistency) + `TREE-1` a `TREE-7` (canonical tree v2 shape) + `STRUCT-1..4` / `SYNC-1` / `YAML-absent` (memory-structured-source-v1) + sufixo `L` para legacy (markdown em memory, `product.html` top-level pre-folder-catalog).

## Trigger típico

CI gate antes de merge; manualmente após qualquer movimentação grande de specs (migração, archive, criação de release nova) para confirmar que a estrutura ainda está sã.

## Diferencial

Sem este validador, drift entre modelo SDD e a realidade no disco vira bug latente — memory virando changelog, releases sem CLOSURE, status não-canônicos passando despercebidos. Os checks são post-hoc (não bloqueiam edição como o gate faz) mas detectam violações que o gate não consegue capturar (por exemplo, conteúdo de CLOSURE.md, broken images, link integrity).

## Estado runtime tocado

  * Read-only sobre todo `specs_dir` (modo padrão).
  * **Com`--fix`:** escreve em `specs_dir` apenas para os invariantes com policy `auto-fix`: regenera `specs/memory/product/index.html` (TREE-3) e recria diretórios ausentes com `.gitkeep` (TREE-4). Todos os outros invariantes permanecem read-only mesmo com `--fix`.



## Dependências

  * Resolução de `specs_dir`: [[context-management]] (via `primary_context.json`).
  * Complementar a [[sdd-gate-v3]] (gate previne writes inválidos; doctor detecta inconsistências post-hoc).
  * Complementar a [[workspace-doctor]] (workspace state vs specs structure).
