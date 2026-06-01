---
slug: tech-stack
title: Tech Stack Memory
category: core
tldr: Approved toolchain, runtimes, approved deps, and canonical commands for dadaia-workspace.
summary: Catalogs approved Python/Node runtimes, core dependencies, formatting/lint
  tools, agent runtimes, and canonical CLI commands. Injected at every session start.
tags:
- tech-stack
- dependencies
- toolchain
- constraints
agent_tier: inject
token_estimate: 1034
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

## Linguagens

Linguagem| Versão| Uso  
---|---|---  
Python| ^3.12| CLI inteira, features, infrastructure, container, testes pytest. `html.parser` (stdlib) usado por `strip-memory-html.py` para stripping de boilerplate HTML na injeção de memória — sem dependência PyPI adicional.  
Bash| 4+ POSIX-compatível| Hooks (`sdd-spec-gate.sh`, `ctx-inject.sh`), entry scripts. `ctx-inject.sh` injeta lean payload (tech-stack + catalog, ~4.6K tokens) em sessões Claude Code e OpenCode via first-message sentinel guard.  
HTML5 + Mermaid| Mermaid via CDN| Memory files atômicos em `specs/memory/*.html` e reports em `.dadaia/reports/<ctx>/<agent>/*.html`  
Markdown| CommonMark| SPEC/PLAN/TASKS/CLOSURE, constitution, backlog, skill/agent definitions  
YAML frontmatter| YAML 1.2| Frontmatter de agents/skills/workflows  
JSON| stdlib| Estado runtime em `.dadaia/states/`, `manifest.json`; `specs/memory/product/catalog.json` (gerado por `dadaia memory catalog generate`, committed, índice machine-readable de features)  
  
## Runtimes e ferramentas

Ferramenta| Versão| Função  
---|---|---  
Poetry| core (build-backend)| Build, lock, virtualenv via `.venv` ou poetry-managed env  
pytest| ^8| Test runner (unit/integration/e2e). Coverage gate 80%  
pytest-cov| ^5| Coverage measurement  
ruff| >=0.15| Linter + formatter (line-length 100, target py312)  
mypy| ^1.10| Type checker  
git| 2.x| VCS; `git_subprocess.py` wrapeia comandos  
  
## Agent runtimes

  * **Claude (Anthropic)** : runtime nativo; agents projetados verbatim para `.claude/agents/` via `dadaia public install --target claude`.
  * **Codex (OpenAI)** : parity guard ativo desde codex-agent-orchestration-parity-v1 (2026-05-20). Doctor checks D-CX-1..5. 20 agentes TOML em `.codex/agents/`. Zero leak `claude-*`. Workflows em `.codex/workflows/`.
  * **OpenCode** : projeção via strip de frontmatter de tools; workflows e skills projetados em `.opencode/`.
  * **CLI** : agentes invocados via `claude --agent <name>` ou equivalente; modo manual sem paralelização automática.



## Model assignments (20 agentes)

Modelo padrão da topologia: `claude-sonnet-4-6` para todos os 20 agentes. Override per-dispatch via `DADAIA_MODEL_OVERRIDE=opus` para tarefas que exijam Opus (greenfield architecture, multi-spec drift, memory atomicity writes). Constitucional em ADR-X4.

Agente| Modelo| Nota  
---|---|---  
project-manager| `claude-sonnet-4-6`| Tier 1 orquestrador  
project-auditor| `claude-sonnet-4-6`| Tier 1 orquestrador  
product-engineer| `claude-sonnet-4-6`| Tier 2 curator  
software-architect| `claude-sonnet-4-6`| Tier 3 leaf  
ai-engineer| `claude-sonnet-4-6`| Tier 3 leaf  
game-designer| `claude-sonnet-4-6`| Tier 3 leaf  
game-tester| `claude-sonnet-4-6`| Tier 3 leaf  
researcher| `claude-haiku-4-5-20251001`| Haiku 4.5; canônico em fan-out evidence-heavy (ADR-X6)  
security-reviewer| `claude-sonnet-4-6` (triage) / `claude-haiku-4-5` (scan)| Dispatcher declara o modo explicitamente  
code-reviewer, software-engineer-python, software-engineer-node, backend-engineer, frontend-engineer, qa-engineer, devops-engineer, design-specialist, data-engineer, data-analyst, game-developer| `claude-sonnet-4-6`| Tier 3 leaves restantes (11)  
  
## Plugin inventory

Plugin| Status| Escopo  
---|---|---  
`playwright`| Retido| Universal — utilizado por `qa-engineer` (E2E), `data-analyst` (dashboard evaluation), `frontend-engineer`.  
`frontend-design`| Retido, escopo restrito| Apenas `frontend-engineer` e `design-specialist` podem invocar; outros agentes recusam com `[PLUGIN SCOPE ERROR]` per ADR-X7. Enforcement via `dadaia_workspace/public/rules/plugin-scope.md`.  
`superpowers`| Removido| Uninstalled em P1; substitutos nativos via skills Tier-A.  
`skill-creator`| Removido| Uninstalled em P1; autoria de skills é responsabilidade de `ai-engineer` editando diretamente `dadaia_workspace/public/skills/`.  
`code-simplifier`| Removido| Uninstalled em P1; refactoring fica em `software-architect` + implementers.  
  
## Schema handoff-v1.1

O contrato de sidecar JSON entre agentes é versionado em `dadaia_workspace/public/schemas/handoff-v1.schema.json`. A versão corrente é **v1.1** (ADR-X5). Campos obrigatórios novos: `findings[].detail_md`, `findings[].fix_recommendation`, `scope`, `metrics`. Campo `artifact.path` tornou-se opcional. `schema_version` aceita `"handoff-v1"` e `"handoff-v1.1"`. Validação via `dadaia reports validate`; lint orphan/oversized/missing-fields via `dadaia reports lint <dir>`. Default de emissão dos 20 agentes: sidecar-only; HTML apenas sob `--with-report` ou `next_handoff.agent == "human"`.

## Dependências aprovadas

Dependência| Versão| Camada| Justificativa  
---|---|---|---  
typer| >=0.25 (extras=[all])| cli/| CLI framework com auto-completion e rich formatting  
rich| ^13| cli/| Pretty terminal output  
openpyxl| ^3.1| infrastructure/| Leitura de planilhas Excel (academy)  
pyyaml| ^6.0| infrastructure/ + features/| YAML frontmatter parsing; also used by `renderer.py` and doctor STRUCT checks via `yaml.safe_load`  
jsonschema| ^4| features/specs/| JSON Schema validation of YAML memory atoms in `renderer.py` and `doctor.py` STRUCT-1..4 checks (memory-structured-source-v1)  
types-PyYAML| >=6| dev| Type stubs para mypy  
  
**Jinja2** (already a transitive dependency) is now the canonical consumer of `dadaia_workspace/public/templates/memory-*.html.j2` via `features/specs/renderer.py` (memory-structured-source-v1). Product-engineer no longer fills templates manually; `dadaia memory render <atom.yaml>` renders them deterministically.

## Restrições e proibições

  * NÃO adicionar dependências fora desta lista sem release aprovada que justifique.
  * NÃO usar libs com network em build/test (offline-first).
  * NÃO usar threading/multiprocessing nas features — orquestração concorrente fica em `features/orchestration/`.
  * NÃO chamar `os.system`/`subprocess` fora de `infrastructure/` — features usam protocols.
  * NÃO importar Python <3.12 backports — runtime mínimo é 3.12 (match/case, generic types nativos, type statement).
  * NÃO escrever em `.claude/`, `.codex/`, `.opencode/`, `.agents/` diretamente — apenas via `dadaia public install` a partir de `public/`.



## Comandos canônicos

Como rodar, testar, lintar e empacotar:
    
    
    # Setup
    poetry install
    
    # Run CLI (dev)
    poetry run dadaia <subcommand>
    # ou globalmente após install
    dadaia <subcommand>
    
    # Tests
    pytest                                  # all
    pytest tests/unit/features/specs/       # specs doctor unit tests
    pytest -k test_clean_tree               # by name
    
    # Lint + format
    ruff check .
    ruff format .
    
    # Type check
    mypy dadaia_workspace
    
    # Asset chain
    dadaia public stage
    dadaia public install --target all      # --force para sobrescrever drift
    dadaia public doctor
    
    # SDD
    dadaia specs doctor                     # estrutura SDD
    dadaia specs doctor --json              # machine-readable
