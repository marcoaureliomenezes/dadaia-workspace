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
token_estimate: 1800
last_updated: '2026-06-25'
release_origin: pi-fourth-harness-v1
---

## Linguagens

Linguagem| Versão| Uso
---|---|---
Python| ^3.12| CLI inteira, features, infrastructure, container, testes pytest.
Bash| 4+ POSIX-compatível| Um único shell asset no produto: `pre-push-ci-gate.sh` (git hook, deliberadamente shell; git-for-Windows ships bash) — todos os hooks de governança são o pacote Python `dadaia_workspace/hooks/`. Python hooks inject lean payload (tech-stack.md verbatim + catalog.json, ~2.4K tokens) **uma vez por sessão** — Codex via `SessionStart`, Claude Code/OpenCode via first-message sentinel keyed num `SESSION_ID` estável (env ou `session_id` do stdin; sem fallback de PID).
HTML5 + Mermaid| Mermaid via CDN| Reports em `.dadaia/reports/<ctx>/<agent>/*.html`; memory atoms são `.md` renderizados in-memory (D-4)
Markdown| CommonMark| Memory atoms atômicos em `specs/memory/*.md` (frontmatter `memory-frontmatter-v1` + corpo Markdown); SPEC/PLAN/TASKS/CLOSURE, constitution, backlog, skill/agent definitions
YAML frontmatter| YAML 1.2| Frontmatter de agents/skills/workflows e memory atoms (`memory-frontmatter-v1`: `additionalProperties: false`)
JSON| stdlib| Estado runtime em `.dadaia/states/`, `manifest.json`; `specs/memory/product/catalog.json` (gerado a partir de frontmatter `.md`, committed, índice machine-readable de features)

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

  * **Claude (Anthropic)** : runtime nativo; agents projetados verbatim para `.claude/agents/` via `dadaia public install --target claude`. O `ClaudeSdkAdapter` (`infrastructure/claude_sdk_runtime.py`) dirige um worker Claude por trás de `AgentRuntimePort` num step do lifecycle; depende do extra **opcional** `claude-agent-sdk` (lazy-imported — NÃO é dependência travada; build offline-first preservado; ausência ⇒ resultado FAILED com `pip install claude-agent-sdk` acionável).
  * **Codex (OpenAI)** : parity guard ativo desde codex-agent-orchestration-parity-v1 (2026-05-20). Doctor checks D-CX-1..8 (D-CX-4 lint inclui tool-names Claude e tier-names Anthropic). 9 agentes core TOML em `.codex/agents/` com tiering registry-derived (model id × `model_reasoning_effort` via `core/model_registry.codex_tier_views()`; deep→high, dispatch→medium; collapse guard loud-fail). Zero leak `claude-*`/Opus/Sonnet/Haiku. Command policy `.codex/rules/*.rules` em `prefix_rule(...)` com paths venv-form. **Hooks executam só em sessão interativa** — `codex exec` headless não dispara hooks (codex-cli 0.139.0, live-verified; harness opt-in `tests/integration/codex_live/`, `DADAIA_CODEX_LIVE=1`). Workflows em `.codex/workflows/` (reference-only).
  * **OpenCode** : projeção via strip de frontmatter de tools; workflows e skills projetados em `.opencode/`.
  * **PI (`@earendil-works/pi-coding-agent`)** : quarto second-layer harness, peer de Claude/Codex/OpenCode, selecionável por step via `--harness pi` / `--step-harness x=pi`. O `PiHeadlessAdapter` (`infrastructure/pi_runtime.py`) dirige um worker PI por trás de `AgentRuntimePort` via `pi --mode json` (subprocess, runner injetável, sem PI client em module-load). PI é um **runtime CLI externo OPCIONAL instalado pelo operador** (Node + binário `pi` + `ANTHROPIC_API_KEY`), invocado como binário externo — **NUNCA** uma dependência Python/Node travada/pinned: não entra em `poetry.lock`, não é importado em build/test, e o build permanece offline-first sem ele. O schema do event stream `pi --mode json` (especificamente a forma de `AgentMessage.content`: string vs array de content-blocks) é o único seam upstream não-verificado, verificado pelo teste de integração opt-in `DADAIA_PI_LIVE=1` (`tests/integration/pi_live/`, **não** CI-gated). A versão exata de `pi` verificada deve ser capturada/pinada na primeira execução do live seam num ambiente com rede — não é pinável offline agora.
  * **CLI** : agentes invocados via `claude --agent <name>` ou equivalente; modo manual sem paralelização automática.



## Model assignments (9 core agents + 3 plugin stubs)

Atribuição em dois tiers: `claude-fable-5` para os leaves de raciocínio profundo
(spec authoring, QA, harness, arquitetura, auditoria) e `claude-opus-4-8` para
dispatchers e gate leaves. Override per-dispatch via `DADAIA_MODEL_OVERRIDE`
quando a política do dispatcher justificar. Optional packs podem definir agentes
e modelos próprios fora do default público.

**Single source:** `dadaia_workspace/core/model_registry.py` é a única fonte de
ids/pricing/tier de modelo (`ModelEntry{claude_id, codex_id, pricing dated
append-only, tier}`); `MODEL_MAP` (runtime transforms) e `PRICING_TABLE`
(telemetry) são views derivadas, com contract test de key-equality. `dadaia
public doctor` falha em `model:` frontmatter que não resolve no registry.

Agente| Modelo| Nota
---|---|---
project-manager| `claude-opus-4-8`| Dispatcher / lease coordinator
project-auditor| `claude-fable-5`| Dispatcher / audit fan-out
product-engineer| `claude-fable-5`| Curator / memory guardian
software-engineer| `claude-opus-4-8`| Implementation leaf (absorbs python/node/backend)
ai-engineer| `claude-fable-5`| AI-entity surface owner (harness-mastery synthesis workload)
software-architect| `claude-fable-5`| Architectural review leaf (ADDITIVE)
qa-engineer| `claude-fable-5`| Review → commit gate leaf
security-reviewer| `claude-opus-4-8`| Review → push gate leaf
code-reviewer| `claude-opus-4-8`| Review → PR gate leaf
frontend-engineer (plugin)| `claude-sonnet-4-6`| Plugin stub (frontend-design); no behavior without plugin
design-specialist (plugin)| `claude-sonnet-4-6`| Plugin stub (frontend-design); no behavior without plugin
devops-engineer (plugin)| `claude-sonnet-4-6`| Plugin stub (devops); no behavior without plugin

## Plugin inventory

Plugin| Status| Escopo
---|---|---
`playwright`| Retido| Universal — utilizado por `qa-engineer` (E2E) e `frontend-engineer`; optional packs podem ampliar uso.
`frontend-design`| Retido, escopo restrito| Apenas `frontend-engineer` e `design-specialist` podem invocar; outros agentes recusam com `[PLUGIN SCOPE ERROR]` per ADR-X7. Enforcement via `dadaia_workspace/public/rules/plugin-scope.md`.
`superpowers`| Removido| Uninstalled em P1; substitutos nativos via skills Tier-A.
`skill-creator`| Removido| Uninstalled em P1; autoria de skills é responsabilidade de `ai-engineer` editando diretamente `dadaia_workspace/public/skills/`.
`code-simplifier`| Removido| Uninstalled em P1; refactoring fica em `software-architect` + implementers.

## Schema handoff-v1.1

O contrato de sidecar JSON entre agentes é versionado em `dadaia_workspace/public/schemas/handoff-v1.schema.json`. A versão corrente é **v1.1** (ADR-X5). Campos obrigatórios novos: `findings[].detail_md`, `findings[].fix_recommendation`, `scope`, `metrics`. Campo `artifact.path` tornou-se opcional. `schema_version` aceita `"handoff-v1"` e `"handoff-v1.1"`. Validação via `dadaia reports validate`; lint orphan/oversized/missing-fields via `dadaia reports lint <dir>`. Default de emissão dos 9 agentes core: sidecar-only; HTML apenas sob `--with-report` ou `next_handoff.agent == "human"`.

## Dependências aprovadas

Dependência| Versão| Camada| Justificativa
---|---|---|---
typer| >=0.25 (extras=[all])| cli/| CLI framework com auto-completion e rich formatting
rich| >=13,<16| cli/| Pretty terminal output
openpyxl| ^3.1| infrastructure/| Leitura de planilhas Excel (academy)
pyyaml| ^6.0| infrastructure/ + features/| YAML frontmatter parsing (memory atoms, agents/skills/workflows); `yaml.safe_load` used by lint and catalog scripts
jsonschema| ^4| features/specs/| JSON Schema validation; now used for `memory-frontmatter-v1.schema.json` validation in `lint-memory-atoms.py`. The per-atom YAML schemas (memory-structured-source-v1) were deleted; `jsonschema` remains for frontmatter validation.
mistune| ~=3.0| features/panel/views/| Markdown → HTML render in-memory for the memory viewer (D-1, memory-markdown-source-v1). Pure-Python, zero transitive deps. Custom hooks: mermaid fence, `wikilink`, sanitiser.
types-PyYAML| >=6| dev| Type stubs para mypy
jinja2| ^3.1| features/specs/| Dependência **direta** de runtime: `features/specs/scaffolder.py` renderiza os templates de scaffold SDD via `SandboxedEnvironment`. NÃO é usada para memory rendering (memory atoms são `.md` renderizados por mistune).
import-linter| latest| dev| Architecture contract enforcement; `setup.cfg` declares `features → infrastructure` import ban and `core → OS-primitive modules` ban; runs in CI `lint` job via `lint-imports`. Zero runtime impact.

**Pins de tooling do workspace (não são deps do projeto):** `poetry` ≥ 2.3.4 e
`dulwich` ≥ 1.2.5 nos ambientes de operação (CVEs nomeados em comentário no
`pyproject.toml`); não entram em `poetry.lock` — o build-backend é `poetry-core`.

## Restrições e proibições

  * NÃO adicionar dependências fora desta lista sem release aprovada que justifique.
  * NÃO usar libs com network em build/test (offline-first).
  * `claude-agent-sdk` é um **runtime extra OPCIONAL instalado pelo operador**, NÃO uma dependência travada/pinned: não entra em `poetry.lock`, não é importado em module-load, e é lazy-imported apenas pelo `ClaudeSdkAdapter` quando o operador escolhe rodar um step no harness Claude SDK. O build e os testes permanecem offline-first sem ele.
  * `pi` / `@earendil-works/pi-coding-agent` é um **runtime CLI externo OPCIONAL instalado pelo operador** (Node + `ANTHROPIC_API_KEY`), invocado como binário externo pelo `PiHeadlessAdapter` via subprocess — **NÃO** uma dependência Python/Node travada/pinned: não entra em `poetry.lock`, não é importado em module-load, e os testes são totalmente faked (offline-first preservado). A versão verificada de `pi` deve ser pinada/registrada aqui na primeira execução do live seam (`DADAIA_PI_LIVE=1`) num ambiente com rede.
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
