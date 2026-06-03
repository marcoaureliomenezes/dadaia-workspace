---
slug: specs-doctor
title: specs-doctor
category: product
tldr: 'Valida invariantes estruturais SDD de specs/: SPEC-DOC + TREE-1..7 + LINT-1 (atomicidade .md); --fix auto-repara TREE-3/4.'
summary: '14 checks estruturais SDD pós memory-markdown-source-v1: 12 SPEC-DOC (memory
  .md atômico via LINT-1, ACTIVE.md, CLOSURE evidence triples, D-OC-1 bidirectional)
  + 7 TREE-1..7 (canonical tree v2 shape). STRUCT-1..4/SYNC-1/YAML-absent removidos;
  SPEC-DOC-008 byte-identity retirado; check #2 aceita ## headings .md; check #8 grep
  direto no .md body. --fix auto-repara TREE-3/4.'
tags:
- specs
- doctor
- validation
- sdd
agent_tier: self-pull
token_estimate: 1073
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia specs doctor [--specs-dir PATH] [--json] [--fix]` · Closure: memory-markdown-source-v1

## Propósito

Valida invariantes estruturais do diretório `specs/` sob o modelo SDD release-lifecycle. Dois grupos de checks:

  * **SPEC-DOC-001..012** (12 checks): presença de `constitution.md`, memory `.md` com folder catalog em `product/`, `ACTIVE.md` bem formada, status canônicos, PLAN ≤ 300 linhas, CLOSURE com evidence triples, atomicidade do memory sem changelog (check #8 agora greppa diretamente o corpo `.md`, sem escape hatch), links de imagem resolvendo, **LINT-1** (invoca `lint-memory-atoms.py`; ERROR em violação de frontmatter ou heading proibido; WARN em token drift), link integrity do `product/index.md` para suas feature `.md` files, o invariante **D-OC-1** bidirectional orchestration registry consistency, e **SPEC-DOC-002L** que sinaliza stray `.html` ainda presentes sob `specs/memory/` (devem ser deletados).
  * **TREE-1..7** (7 checks): canonical `specs/` tree v2 shape.

Os checks STRUCT-1..4, SYNC-1 e YAML-absent guard foram removidos nesta release (eram específicos ao modelo YAML/HTML). O invariante SPEC-DOC-008 (byte-identity do HTML commitado) também foi retirado.

Exit code 1 se houver errors; 0 se só warnings ou tudo verde. Suporta `--json` para integração com CI/automação e `--fix` para auto-repair dos invariantes tratáveis.

### Invariante LINT-1 (memory-markdown-source-v1)

Código| O que detecta| Severity| Notas  
---|---|---|---  
LINT-1| Qualquer atom `.md` em `specs/memory/` ou `specs/memory/product/` falha validação de `lint-memory-atoms.py`| ERROR (frontmatter) / WARN (token drift)| Frontmatter: required fields, no extra fields, forbidden headings, wikilink resolution. Token drift: `words × 1.35` vs `token_estimate` > 20% → WARN  
SPEC-DOC-002| Check #2: memory files existem como `.md`| ERROR| Agora requer `.md`, não `.html`; aceita headings `##` conforme allowlist  
SPEC-DOC-002L| Stray `.html` presentes sob `specs/memory/`| ERROR| Esses arquivos devem ser deletados; D-4 proíbe HTML commitado na pasta memory  
SPEC-DOC-008| Byte-identity do HTML commitado| —| **Removido** — não aplicável ao modelo MD-source (D-4: HTML é efêmero, renderizado in-memory)

### Invariantes TREE-1..7 (canonical tree v2)

Código| O que detecta| Severity| `--fix` policy  
---|---|---|---  
TREE-1| Diretório `specs/foundation/` presente (depreciado)| WARN| warn-only; **migration guard** impresso independente de `--fix` — instrução: `dadaia migrate tree-v2`  
TREE-2| Arquivo `specs/SPEC.md` na raiz (pre-release-model)| WARN| warn-only; **migration guard** impresso — instrução: `dadaia migrate tree-v2`  
TREE-3| `specs/memory/product/index.md` ausente| ERROR| **auto-fix** : regenera `index.md` stub do template canônico  
TREE-4| Um ou mais de `specs/backlog/`, `specs/bugs/`, `specs/releases/` ausentes| ERROR| **auto-fix** : recria diretório(s) ausente(s) com `.gitkeep`  
TREE-5| `specs/AGENTS.md` ausente (drift em relação ao template canônico)| WARN| warn-only (sem auto-overwrite — arquivo pode ter customizações do consumer)  
TREE-6| Diretório de release em `specs/releases/` sem pelo menos um artefato SDD obrigatório (`SPEC.md`)| ERROR| no-fix (decisão humana)  
TREE-7| Arquivo de bug em `specs/bugs/` sem campo `session_id` no frontmatter| ERROR| no-fix (campo requer valor real)  
  
**Migration guard (TREE-1/2):** quando detectados, o doctor imprime a mensagem de migration guard independentemente do flag `--fix` — o auto-move de `foundation/` e root `SPEC.md` para `releases/legacy/` é feito exclusivamente por `dadaia migrate tree-v2`.

## Fluxo de uso

  1. `dadaia specs doctor` — resolve `specs_dir` via `primary_context.json` ou `--specs-dir`, roda todos os checks em ordem (12 SPEC-DOC + 7 TREE), exibe issues formatados com código + severity + path. LINT-1 invoca `lint-memory-atoms.py` nos átomos `.md`; token drift é WARN; violações de frontmatter ou heading proibido são ERROR.
  2. `dadaia specs doctor --fix` — executa os checks e auto-repara os invariantes com policy `auto-fix` (TREE-3, TREE-4); emite migration guard para TREE-1/2; deixa TREE-5..7 como warnings/errors sem alterar arquivos.
  3. Para automação: `dadaia specs doctor --json` emite payload `{specs_dir, issues[], summary{errors, warnings}}`.
  4. Em CI: usado como gate de PR para bloquear merge se houver erros estruturais nos specs.



Códigos de erro: `SPEC-DOC-001` a `SPEC-DOC-012` + `D-OC-1` (bidirectional orchestration registry consistency) + `TREE-1` a `TREE-7` (canonical tree v2 shape) + `LINT-1` (memory-markdown-source-v1: lint-memory-atoms.py; frontmatter, heading allowlist, wikilinks, forbidden headings, token drift) + sufixo `L` para legacy (stray `.html` em memory — SPEC-DOC-002L).

## Trigger típico

CI gate antes de merge; manualmente após qualquer movimentação grande de specs (migração, archive, criação de release nova) para confirmar que a estrutura ainda está sã.

## Diferencial

Sem este validador, drift entre modelo SDD e a realidade no disco vira bug latente — memory virando changelog, releases sem CLOSURE, status não-canônicos passando despercebidos. Os checks são post-hoc (não bloqueiam edição como o gate faz) mas detectam violações que o gate não consegue capturar (por exemplo, conteúdo de CLOSURE.md, broken images, link integrity).

## Estado runtime tocado

  * Read-only sobre todo `specs_dir` (modo padrão).
  * **Com`--fix`:** escreve em `specs_dir` apenas para os invariantes com policy `auto-fix`: regenera `specs/memory/product/index.md` stub (TREE-3) e recria diretórios ausentes com `.gitkeep` (TREE-4). Todos os outros invariantes permanecem read-only mesmo com `--fix`.



## Dependências

  * Resolução de `specs_dir`: [[context-management]] (via `primary_context.json`).
  * Complementar a [[sdd-gate-v3]] (gate previne writes inválidos; doctor detecta inconsistências post-hoc).
  * Complementar a [[workspace-doctor]] (workspace state vs specs structure).
