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
token_estimate: 2500
last_updated: '2026-07-01'
release_origin: v0.1.47
---

## Linguagens

Linguagem| Versão| Uso
---|---|---
Python| ^3.12| CLI inteira, features, infrastructure, container, testes pytest.
Bash| 4+ POSIX-compatível| Shell assets no produto: apenas os git chokepoints `pre-commit-lease-gate.sh` + `pre-push-ci-gate.sh` (git hooks, deliberadamente shell; git-for-Windows ships bash) — todos os hooks de governança de harness são o pacote Python `dadaia_workspace/hooks/`. Python hooks injetam payload lean (digest bounded de tech-stack.md + tldr-digest de catalog.json) **uma vez por sessão** — Codex via `SessionStart`, Claude Code via first-message sentinel keyed num `SESSION_ID` estável (env ou `session_id` do stdin; sem fallback de PID). PI lê a law nativamente up-tree (sem hook de injeção de Layer 1).
HTML5 + Mermaid| fences `mermaid` em Markdown| Reports em `.dadaia/reports/<ctx>/<agent>/*.html`; memory atoms são `.md` renderizados in-memory. O panel NÃO carrega Mermaid de CDN (CSP `script-src 'self'`): fences viram `<pre class="mermaid">` exibidos como source
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

**Esta seção é a ÚNICA fonte do roster de harness/runtime** (constitution §0, invariante
de roster; SPEC-DOC-037 impede a constitution de enumerá-lo). O roster:

  * **Layer 1 — entry harnesses (o que o operador lança no terminal):** exatamente **`{claude, codex, pi}`**.
  * **Layer 2 — workflow worker harnesses (selecionáveis em `dadaia lifecycle`):** exatamente **`{pi, codex}`** (+ **`fake`** test-only). `claude` é rejeitado como `--harness` de workflow — **Claude Code é Layer-1-only por lei** (cost bound).
  * **`AgentRuntimeKind` (`core/models/lifecycle.py`) — 4 membros:** `FAKE`, `CODEX_EXEC`, `CLAUDE_SDK`, `PI_HEADLESS`. `CLAUDE_SDK` é mantido importável + unit-tested mas **não é selecionável** como workflow harness.

Por harness (verdade per-runtime em `specs/memory/product/harness/` — [[harness-claude-code]], [[harness-codex]], [[harness-pi]]):

  * **Claude (Anthropic)** : runtime Layer-1 nativo; agents projetados verbatim para `.claude/agents/` via `dadaia public install --target claude`. O `ClaudeSdkAdapter` (`infrastructure/claude_sdk_runtime.py`) permanece por trás de `AgentRuntimePort`; depende do extra **opcional** `claude-agent-sdk` (lazy-imported — NÃO é dependência travada; build offline-first preservado; ausência ⇒ resultado FAILED com `pip install claude-agent-sdk` acionável).
  * **Codex (OpenAI)** : Layer 1 (TUI) e Layer 2 (`CODEX_EXEC` via `codex exec`). Doctor checks D-CX-1..8 (D-CX-4 lint inclui tool-names Claude e tier-names Anthropic). 9 agentes core TOML em `.codex/agents/` com tiering registry-derived (model id × `model_reasoning_effort` via `core/model_registry.codex_tier_views()`; deep→high, dispatch→medium; collapse guard loud-fail). Zero leak `claude-*`/Opus/Sonnet/Haiku. Command policy `.codex/rules/*.rules` em `prefix_rule(...)` com paths venv-form. **Hooks executam só em sessão interativa** — `codex exec` headless não dispara hooks (codex-cli 0.139.0, live-verified; harness opt-in `tests/integration/codex_live/`, `DADAIA_CODEX_LIVE=1`). Workflows em `.codex/workflows/` (reference-only). Modelos Layer-2: `(gpt-5.5,high)` / `(gpt-5.5,medium)`.
  * **PI (`@earendil-works/pi-coding-agent`)** : Layer 1 (harness de entrada) **e** Layer 2 (`PI_HEADLESS`), selecionável por step via `--harness pi` / `--step-harness x=pi`. O `PiHeadlessAdapter` (`infrastructure/pi_runtime.py`) dirige um worker PI via `pi --mode json` (subprocess, runner injetável, sem PI client em module-load). PI é um **runtime CLI externo OPCIONAL instalado pelo operador**, invocado como binário externo — **NUNCA** dependência travada/pinned: não entra em `poetry.lock`, não é importado em build/test, e o build permanece offline-first sem ele. **Auth: PI roda sob a subscrição Codex do operador via `~/.pi/agent/auth.json`** (provider openai-codex) — nenhuma chave Anthropic é requerida. **Modelos Layer-2 (4):** `(gpt-5.5,high)` / `(gpt-5.5,low)` / `(gpt-5.3-codex,medium)` / **`kimi-2.7:high`** — o id OpenRouter curado via `LAYER2_EXTRA_MODEL_IDS` (`core/harness_models.py`), selecionável pelo profile built-in `pi-openrouter-kimi-high`; ids `kimi-*` não têm pricing row no registry (custo `None`, nunca fabricado). O schema do event stream `pi --mode json` é verificado pelos testes opt-in `DADAIA_PI_LIVE=1` / `DADAIA_E2E_REAL_WORKER=1` (`tests/integration/pi_live/`, **não** CI-gated). Build live-verificado: `pi` **0.79.3**. **Telemetria PI:** `features/telemetry/reader/pi.py` ingere **só metadata** de `~/.pi/agent/sessions/` (invariant T1 — nenhum body/conteúdo; custo nunca fakeado); degrada idle em falha de IO/parse.
  * **Versões CLI:** `pi` 0.79.3 live-verificado; a versão verificada de `codex` ainda não foi capturada (não inventar).



## Model assignments (9 core agents + 3 plugin stubs)

**Tier único na prática:** os **9 agentes core** rodam em `claude-opus-4-8` — não
há tier-split em produção (verificável: os 9 frontmatter `model:` resolvem todos
para `claude-opus-4-8`). Override per-dispatch via `DADAIA_MODEL_OVERRIDE` quando a
política do dispatcher justificar. Optional packs podem definir agentes e modelos
próprios fora do default público.

**Single source:** `dadaia_workspace/core/model_registry.py` é a única fonte de
ids/pricing/tier de modelo (`ModelEntry{claude_id, codex_id, pricing dated
append-only, tier}`); `MODEL_MAP` (runtime transforms) e `PRICING_TABLE`
(telemetry) são views derivadas, com contract test de key-equality. `dadaia
public doctor` falha em `model:` frontmatter que não resolve no registry.

**Entrada reservada (não usada por nenhum agente):** o registry ainda define
`claude-fable-5` com `tier="deep"` (e o mapeamento Codex `deep→high`), mas **zero
agente core resolve para ela** — todos os 9 são `dispatch`-tier opus-4-8.
`claude-fable-5` é region-restricted; a regra do operador é **NUNCA** pinar um
agente a Fable-5. A entrada permanece como definição reservada do registry, não
como atribuição viva.

Agente| Modelo| Nota
---|---|---
project-manager| `claude-opus-4-8`| Dispatcher / lease coordinator
project-auditor| `claude-opus-4-8`| Dispatcher / audit fan-out
product-engineer| `claude-opus-4-8`| Curator / memory guardian
software-engineer| `claude-opus-4-8`| Implementation leaf (absorbs python/node/backend)
ai-engineer| `claude-opus-4-8`| AI-entity surface owner (harness-mastery synthesis workload)
software-architect| `claude-opus-4-8`| Architectural review leaf (ADDITIVE)
qa-engineer| `claude-opus-4-8`| Review → commit gate leaf
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
pytest-randomly| ^4.1| dev| Ordem de testes aleatória por run — flusha dependências de ordem entre testes
hypothesis| >=6.100| dev| Property-based testing (database redirecionado fora do repo — repo-hygiene)
jinja2| ^3.1| features/specs/| Dependência **direta** de runtime: `features/specs/scaffolder.py` renderiza os templates de scaffold SDD via `SandboxedEnvironment`. NÃO é usada para memory rendering (memory atoms são `.md` renderizados por mistune).
import-linter| >=2.11| dev| Contratos de camada em `setup.cfg` (`features → infrastructure` ban; `core → OS-primitives` ban). **Definidos mas NÃO rodam em CI** — nenhum job invoca `lint-imports`; vários contratos estão vermelhos. Wiring em CI + fix das chains é o backlog `import-boundary-enforcement`.

**Pins de tooling do workspace (não são deps do projeto):** `poetry` ≥ 2.3.4 e
`dulwich` ≥ 1.2.5 nos ambientes de operação (CVEs nomeados em comentário no
`pyproject.toml`); não entram em `poetry.lock` — o build-backend é `poetry-core`.

Onde cada dependência vive, e os bans de import que os contratos do `import-linter`
descrevem (camadas hexagonais — seta = direção de import permitida; contratos ainda
não CI-enforced, ver a row acima):

```mermaid
graph TD
  CLI["cli/<br/>typer · rich"]
  FEAT["features/<br/>pyyaml · jsonschema · jinja2 · mistune"]
  INFRA["infrastructure/<br/>openpyxl · pyyaml · git_subprocess · adapters de harness"]
  CORE["core/<br/>stdlib only<br/>model_registry · scope_match · models · protocols"]
  CLI --> FEAT
  CLI --> INFRA
  FEAT --> CORE
  INFRA --> CORE
  FEAT -. "BANIDO (contrato): features ✗→ infrastructure" .-> INFRA
  CORE -. "BANIDO: core ✗→ os/subprocess/fcntl" .-> OSP["OS primitives"]
```

`features/` fala com o mundo externo apenas por `core/protocols/*`, implementados em
`infrastructure/` e injetados no `container.py` (hexagonal port/adapter). `core/` é
puro: zero I/O, zero OS primitive — por isso é testável e cross-platform.

## Restrições e proibições

  * NÃO adicionar dependências fora desta lista sem release aprovada que justifique.
  * NÃO usar libs com network em build/test (offline-first).
  * `claude-agent-sdk` é um **runtime extra OPCIONAL instalado pelo operador**, NÃO uma dependência travada/pinned: não entra em `poetry.lock`, não é importado em module-load, e é lazy-imported apenas pelo `ClaudeSdkAdapter` quando o operador escolhe rodar um step no harness Claude SDK. O build e os testes permanecem offline-first sem ele.
  * `pi` / `@earendil-works/pi-coding-agent` é um **runtime CLI externo OPCIONAL instalado pelo operador**, invocado como binário externo pelo `PiHeadlessAdapter` via subprocess — **NÃO** uma dependência Python/Node travada/pinned: não entra em `poetry.lock`, não é importado em module-load, e os testes são totalmente faked (offline-first preservado). Auth via `~/.pi/agent/auth.json` (subscrição Codex do operador) — ver `#Agent runtimes`.
  * NÃO usar threading/multiprocessing nas features — orquestração concorrente fica em `features/orchestration/`.
  * NÃO chamar `os.system`/`subprocess` fora de `infrastructure/` — features usam protocols.
  * NÃO importar Python <3.12 backports — runtime mínimo é 3.12 (match/case, generic types nativos, type statement).
  * NÃO escrever em `.claude/`, `.codex/`, `.pi/`, `.agents/` diretamente — apenas via `dadaia public install` a partir de `public/`.



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

    # Backlog-consistency engine (features/backlog/, v0.1.25)
    dadaia backlog subjects                 # lista o anchor set canônico vivo (opcional --kind / --resolve "<ref>")
    dadaia backlog doctor                   # BL-SCHEMA/DUP/CONFLICT/STALE; exit !=0 em violação (wired no pre-commit + CI)
    dadaia backlog doctor --explain         # mostra como um subject proposto resolve (anchor | UNRESOLVED | AMBIGUOUS)

    # backlog_definition dadaia-workflow (features/lifecycle/workflows/backlog_definition.py, v0.1.26)
    dadaia lifecycle backlog define --harness {pi|codex|fake} --model <id>   # workflow §4 ORIENTED; gates Python-owned; LAW 1/LAW 2 (claude rejeitado)
