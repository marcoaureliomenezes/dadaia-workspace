# Plan: Universal Agentic Assets

> **Status:** Aprovado
> **SPEC:** `specs/features/universal-agentic-assets/SPEC.md`
> **Data:** 2026-05-09

---

## Estratégia

Implementar a distribuição de assets em três etapas explícitas:

1. `stage`: copiar assets do pacote instalado para `.dadaia/agentic/` e gerar manifest.
2. `install`: projetar o staging para destinos universais e runtime-specific.
3. `doctor`: comparar pacote, staging e projeções sem mutar arquivos.

---

## Arquitetura

### Pacote canônico

`dadaia_workspace/public/` continua sendo a única fonte versionada. O código deve ler esse diretório via APIs de pacote/importlib quando possível, para funcionar tanto em editable install quanto em build instalado.

### Staging

`.dadaia/agentic/` deve conter:

```text
.dadaia/agentic/
  manifest.json
  agents/
  commands/
  rules/
  skills/
  scripts/
  templates/
```

O manifest deve registrar:
- `schema_version`
- `package_version`
- `generated_at`
- lista de assets com path relativo, hash e tipo

### Projeções

| Target | Destinos |
|---|---|
| `agents` | `.agents/skills/` |
| `claude` | `.claude/agents/`, `.claude/commands/`, `.claude/skills/`, `.claude/settings.json` |
| `codex` | `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/`, `.agents/skills/` |
| `opencode` | `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/`, `opencode.json` |
| `all` | todos os targets acima + `AGENTS.md` |

OpenCode não recebe hooks. Codex não recebe sub-agentes Claude Code se o runtime não suportar esse modelo.

---

## Arquivos Afetados

| Área | Arquivos |
|---|---|
| CLI | `dadaia_workspace/cli/commands/public.py` |
| Feature | `dadaia_workspace/features/public/service.py`, novos módulos auxiliares se necessário |
| Core protocols | Protocols de leitura de package assets, storage e clock/hash se necessários |
| Infra | `dadaia_workspace/infrastructure/public_assets.py` |
| Public assets | `dadaia_workspace/public/**` |
| Tests | unit, integration e e2e de public assets |

---

## Sequência

1. Modelar manifest e classificação `ok|missing|drift|unsupported`.
2. Implementar staging determinístico.
3. Implementar projeção `agents`.
4. Implementar projeção Claude Code.
5. Implementar projeção Codex.
6. Implementar projeção OpenCode sem hooks.
7. Implementar `public doctor`.
8. Ajustar `dadaia init` para chamar stage/install no bootstrap.
9. Cobrir fresh workspace, no-overwrite e drift detection em testes.

---

## Validação

Comandos mínimos:

```bash
python -m pip install -e .
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

Suites esperadas:

```bash
ruff format
ruff check
mypy --strict
pytest tests/unit/ -v
pytest tests/e2e/features/ -v
```

---

## Riscos

| Risco | Mitigação |
|---|---|
| Sobrescrever customização local | `install` preserva arquivos sem `--force` |
| Falsa paridade entre runtimes | `doctor` reporta `unsupported`; specs proíbem emulação falsa |
| Drift entre package e runtime | manifest com hashes + `public doctor` |
| Editable install divergente | acceptance exige install editable e CLI real |
