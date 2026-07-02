---
slug: dadaia-workflows
title: dadaia-workflows
category: product
tldr: The 7 governed Layer-2 workflows; 4 operator-invocable verbs today (release define, backlog define, pipeline, close); every model step gets fragment + persona.
summary: >-
  The roster and invocability truth of the dadaia-workflows: 7 workflows defined in
  the governed catalog (release_definition, implementation, backlog_definition,
  closure, audit, research, bug_report), of which 4 workflow verbs are
  operator-invocable today — release define, backlog define, pipeline (with its
  single-step verbs implement / review qa|security|code), and close.
  audit/research/bug_report have real fragment+gate bodies but no CLI verb yet
  (backlog lifecycle-verb-governance-uniformity). Every model-driven step prompt on
  every verb carries its fragment AND its persona. Engine mechanics live in
  lifecycle-foundation.
tags:
- sdd
- workflows
- lifecycle
- layer-2
agent_tier: self-pull
token_estimate: 950
last_updated: '2026-07-01'
release_origin: v0.1.47
---

## Propósito

Um **dadaia-workflow** é um corpo Python que dirige workers Layer-2 por steps: importa
o **fragment** do step (a instrução single-step: inputs, task, contrato de output),
injeta a **persona** do role (a diretiva operativa "quem você é"), seleciona contexto
dinâmico, chama um worker `(harness, model)` discreto e avança **gates
Python-validados** — o modelo recomenda, Python decide a legalidade da transição.
Este atom é a fonte única do ROSTER e da INVOCABILIDADE; a mecânica do engine
(pipeline, gates, run store, data plane) é [[lifecycle-foundation]].

**Os 7 workflows do catálogo governado** (`features/workflows/dadaia_catalog.py` —
`governed_workflow_catalog()`):

| Workflow | Corpo | Availability | Verbo CLI hoje |
|----------|-------|--------------|----------------|
| `release_definition` | `workflows/release_definition.py` | available | `dadaia lifecycle release define` |
| `backlog_definition` | `workflows/backlog_definition.py` | available | `dadaia lifecycle backlog define` |
| `implementation` | `pipeline.py` / `phase_workflow.py` | partial | `dadaia lifecycle pipeline` (+ steps avulsos `implement`, `review qa\|security\|code`) |
| `closure` | step `close` + `closure_removal_gate` | partial | `dadaia lifecycle close` |
| `audit` | `workflows/audit.py` (real, fragment+gate) | available no catálogo | **sem verbo** — pendente |
| `research` | `workflows/research.py` (real, fragment+gate) | available no catálogo | **sem verbo** — pendente |
| `bug_report` | `workflows/bug_report.py` (real, fragment+gate) | available no catálogo | **sem verbo** — pendente |

**Invocabilidade honesta: 4 verbos de workflow hoje** — `release define`,
`backlog define`, `pipeline`, `close`. `audit`/`research`/`bug_report` são entradas
governadas do catálogo com corpos reais mas **nenhum verbo CLI os invoca ainda**
(wiring de verbo + container builders é o backlog
`lifecycle-verb-governance-uniformity`). Não afirmar 7 invocáveis.

## Fluxo de uso

1. Um harness de entrada (ou o operador) invoca um verbo:
   `dadaia lifecycle <verbo> --release-id <id> --harness {pi|codex|fake} [--model …]`.
2. O policy resolver congela o snapshot `(harness, profile, model)` por step antes do
   step 1 ([[lifecycle-foundation]] — control plane).
3. Para cada step model-driven, o prompt é montado como **persona (role directive) +
   fragment bundle + contexto dinâmico + contrato de output** — a injeção de persona
   vale para TODOS os verbos (helper compartilhado threaded nos 5 corpos de workflow
   E no `_run_phase_step` da CLI), não só no pipeline.
4. O worker responde com o payload `schema: agent-run-result-v1`; o gate typed
   (review-only) decide: review steps exigem `verdict == APPROVED`; create steps
   exigem payload estrutural + `artifact_refs`; Ring-2 valida `changed_paths`.
5. Steps comunicam via o workflow-step handoff ledger; um required upstream ausente
   BLOQUEIA antes do próximo prompt.

## Trigger típico

Definição de release ou de item de backlog num harness de entrada Codex/PI (onde
dadaia-workflows são o caminho de execução preferido); o pipeline
implementation→review numa release; o close no fim.

## Diferencial

A autoridade do workflow fica em Python (ordem de steps, gates, ledger), não em texto
livre de agente — um worker não consegue "se aprovar" fora do contrato. Fragment e
persona separam o QUE do step do QUEM do role, cada um com um único home
(`public/lifecycle_fragments/`, `public/personas/`).

## Estado runtime tocado

- `.dadaia/states/lifecycle/<run_id>.json` — run records (snapshot de policy + step
  ledger).
- `.dadaia/runs/lifecycle/<run_id>/steps/*.step-payload.json` — payloads imutáveis.
- `.dadaia/states/workflow_model_policy.json` — overlay de política (panel/CLI).
- `specs/` do contexto — os artefatos que cada workflow produz (SPEC/PLAN/TASKS,
  backlog item, CLOSURE), sob o gate SDD normal.

## Dependências

- [[lifecycle-foundation]] — o engine (pipeline, gates, run store, data plane,
  model/harness governance).
- [[agent-orchestration]] — a superfície de personas Layer-2.
- [[tech-stack]] — o roster de harness/modelo que os verbos aceitam.
- [[sdd-gate-v3]] — o gate e os chokepoints sob os quais os writes dos workers caem.
- [[panel]] — a superfície do operador (diagram-cards + model pickers) sobre o mesmo
  catálogo governado.
