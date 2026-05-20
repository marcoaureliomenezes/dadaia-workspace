# CLOSURE: codex-agent-orchestration-parity-v1

> **Status:** CLOSURE
> **Data:** 2026-05-20
> **Owner:** product-engineer

## Evidências de Acceptance Criteria

### AC1 — Null Claude Regression Suite
- Comando: `find .claude -type f -print0 | xargs -0 sha256sum | sort > /tmp/post-codex.txt && diff /tmp/pre-codex.txt /tmp/post-codex.txt`
- Resultado: diff vazio — zero mudanças em `.claude/**`
- Snapshot baseline: `.dadaia/tmp/json/pre-codex-snapshot.txt` (56 arquivos)

### AC2 — 20 TOMLs parseáveis
- Comando: `python3 -c "import tomllib, glob; [tomllib.loads(open(f,'rb').read()) for f in glob.glob('.codex/agents/*.toml')]"`
- Resultado: 20 TOMLs em `.codex/agents/`, todos parseáveis, `developer_instructions` não-vazio

### AC3 — Zero strings claude-*
- Comando: `grep -rE '(^|[^a-zA-Z0-9_-])claude-' .codex/`
- Resultado: zero linhas (exit 1) — nenhuma fuga de identifier Claude

### AC4 — Sequential dispatch
- Comando: `pytest tests/unit/features/agents/test_codex_dispatcher_sequential.py`
- Resultado: 6 passed

### AC5 — Parallel best-effort
- Comando: `pytest tests/unit/features/agents/test_codex_dispatcher_parallel.py`
- Resultado: 9 passed

### AC6 — Unsupported capability
- Comando: `pytest tests/unit/features/agents/test_codex_dispatcher_unsupported.py`
- Resultado: 7 passed

### AC7 — Workflow removal detected
- Teste: `test_ac7_missing_workflow_detected`
- Resultado: PASS

### AC8 — Corrupted TOML detected
- Teste: `test_ac8_corrupted_toml_detected`
- Resultado: PASS

### AC9 — Missing TOML no ok
- Teste: `test_ac9_missing_toml_no_ok_reported`
- Resultado: PASS

### AC10 — Specs doctor
- Comando: `dadaia specs doctor`
- Resultado: `[ok] 0 errors, 0 warnings`

## ADRs desta release

- ADR-1: Codex Agent Projection Format (TOML: name, model, developer_instructions)
- ADR-2: Runtime-Specific Prompt Transform (transform_for_codex)
- ADR-3: Dispatcher Capability Matrix (sequential NATIVE, parallel best-effort)
- ADR-4: Workflow Runtime Boundary (render-at-install)
- ADR-5: Model Mapping (claude-sonnet-4-6 → gpt-5.3-codex, etc.)
- ADR-6: Null Claude Regression Suite (snapshot post-FR13)

## Operador — confirmação AC12

[ ] Operador leu as 6 ADRs end-to-end e registra OK aqui.

## AC12 — ADRs lidas end-to-end

O operador confirmará leitura das 6 ADRs ao revisar este CLOSURE.
ADRs em: `specs/releases/codex-agent-orchestration-parity-v1/adrs/`

- [ ] ADR-1 lida: adr-1-codex-agent-projection-format.md
- [ ] ADR-2 lida: adr-2-runtime-specific-prompt-transform.md
- [ ] ADR-3 lida: adr-3-dispatcher-capability-matrix.md
- [ ] ADR-4 lida: adr-4-workflow-runtime-boundary.md
- [ ] ADR-5 lida: adr-5-model-mapping.md
- [ ] ADR-6 lida: adr-6-null-claude-regression-suite.md
