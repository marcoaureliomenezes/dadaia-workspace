# Spec: Release — multi-platform-parity-v1

> **Status:** Aprovado
> **Release ID:** multi-platform-parity-v1
> **Phase:** SPEC
> **Owner:** product-engineer
> **Created:** 2026-05-17
> **Source candidate:** `specs/backlog/candidates.md` (§ Candidatas ativas, topo da lista)
> **Pipeline (3-phase):** PE Discovery (platform-boundaries) → PE Grill-Me → Architect Position + SE Impact (parallel) → PE Synthesis (this SPEC)
> **Discovery inputs:**
> - PE Discovery: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T233537Z-platform-boundaries-analysis.html`
> - PE Grill-Me: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T011435Z-multi-platform-grill-me.html`
> - Architect Position: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-17T012117Z-multi-platform-pillar-position.html`
> - SE Impact: `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-17T012220Z-multi-platform-pillar-impact.html`

---

## Resumo executivo

- Materializa o **Pilar 3 — Multi-AI-platform (Claude Code, Codex, OpenCode)** já codificado em `specs/constitution.md` § "Pilares do Produto" (adicionado em 2026-05-16), fechando 4 dos 5 gaps detectados pela platform-boundaries analysis: **G1** (Codex agents nunca projetados), **G2** (workflows mortos copiados para `.codex/workflows/`), **G3** (OpenCode silenciosamente sequencializa `parallel_group`) e **G5** (doctor `[unsupported]` escondido pelo install que copia mesmo assim).
- **Veredicto arquitetural:** Option B (staged pipeline, fixed) endossada por ADR-MP-2 + ADR-ARCH-1 contra Option A (platform-isolated source). Mantém intactos o contrato de 4 camadas (`CLI → Features → Core ← Infrastructure`), o baseline SHA256 em `.dadaia/agentic/manifest.json` e a rule sempre ativa `dadaia-workspace-dev-guardrail` — Option A quebraria os três.
- **Escopo cirúrgico:** todo o código novo vive em `dadaia_workspace/infrastructure/public_assets.py` (privado em `FileSystemPublicAssetManager`, sem novo Protocol em `core/`, sem novo módulo em `features/`, sem edição em `container.py`). Total ~143 LoC (~89 novas + ~54 modificadas) em 3 commits ordenados, com 15 novos testes unitários/integration.
- **G4 explicitamente deferido** (ADR-MP-4 + ADR-ARCH-4) para release sucessora `agents-md-hierarchical-v1`: G4 toca `spec_context` integration e per-repo materialization — uma camada diferente, ortogonal à projection pipeline; bundle dobraria escopo e blast radius desta release.
- **Zero overlap com `agent-comms-v1`** (já encerrada em CLOSURE em 2026-05-17): aquela release toca `core/protocols/handoff_validator.py`, `core/models/handoff.py`, `infrastructure/stdlib_handoff_validator.py`, `features/reports_validation/` e `cli/commands/reports.py`; esta toca exclusivamente `infrastructure/public_assets.py`, `cli/commands/public.py` e `tests/unit/test_public_assets.py`. Nenhum arquivo colide.

---

## Motivação

A constitution amendada em 2026-05-16 (§ "Pilares do Produto" L15–31) declara como invariante imutável que **os três runtimes oficialmente suportados — Claude Code, Codex e OpenCode — consomem o mesmo conjunto de assets agentic através de uma pipeline única**. O floor mínimo escrito nessa seção é: *"skills, agents, commands e rules têm projeção honesta em todos os runtimes que os suportam nativamente"*. Hoje o Pilar 3 é o mais frágil dos três pilares: a inspeção empírica reportada em 2026-05-16T23:35:37Z, reconfirmada em 2026-05-17T01:14:35Z e novamente em 2026-05-17T01:21:17Z, mostra que **três dos cinco gaps continuam presentes na projeção rodando**:

- `.codex/agents/` está vazio (G1) — o yield `(None, …, "codex:agents", False)` em `infrastructure/public_assets.py:432` é skip intencional.
- `.codex/workflows/` contém 8 arquivos `*.workflow.md` inertes (G2) — sem runtime para dispatchá-los; o `_copy_tree(agentic_dir / "workflows", codex_dir / "workflows", …)` em `public_assets.py:322` os materializa cegamente.
- `_classify_workflows()` em `public_assets.py:240-256` emite `[ok] codex:workflows/<wf>` para workflows lineares (G5 — falso positivo); um operador que pula `doctor` vê install limpo e assume suporte que não existe.

A platform-boundaries analysis também documentou G3 (OpenCode sequencializa `parallel_group` silenciosamente) e G4 (semântica do root `AGENTS.md` divergente entre Claude/OpenCode/Codex). G3 é tratado como **limitação aceita de runtime** (a pillar text já reconhece esse floor); G4 é deferido a uma release separada (ADR-MP-4 + ADR-ARCH-4).

Como o Pilar 3 é constitucional e o gap entre a constituição e o comportamento materializado é uma dívida documental ativa, fechar G1+G2+G3+G5 em uma única release coerente é a forma mais econômica de tornar o Pilar 3 enforcável. ADR-MP-6 + ADR-ARCH-1 ratificam **single release**, não split: os quatro patches compartilham o mesmo modelo mental ("o classifier do doctor vira a superfície de contrato; install honra o classifier") e o patch surface (~143 LoC em um arquivo) é confortavelmente uma release.

---

## Escopo

### In-scope (G1+G2+G3+G5 fechados)

- **T-PB-1 — Codex agent TOML rendering.** Novo método privado `_render_agents_into_codex_config()` em `FileSystemPublicAssetManager` (`infrastructure/public_assets.py`) que parseia o YAML frontmatter dos 10 agentes em `dadaia_workspace/public/agents/*.md` (parser regex stdlib-only, sem `pyyaml`) e emite blocos TOML `[agents.<name>]` apendados a `.codex/config.toml`. Whitelist conservadora de campos (`_TOML_SAFE_AGENT_FIELDS = {"name", "description", "model", "tools"}`); demais campos (`opencode_model`, `input_contract`, `color`, `skills`, `maxTurns`) silenciosamente descartados. Atualiza `_codex_config()`, `_install_codex()`, `doctor()` e remove o tuple `(None, …, "codex:agents", False)` de `_runtime_expectations():432`.
- **T-PB-2 — Stop copying workflows to `.codex/workflows/`.** Remove a chamada `self._copy_tree(agentic_dir / "workflows", codex_dir / "workflows", force, installed)` em `_install_codex():322`. Adiciona cleanup unconditional `shutil.rmtree(codex_dir / "workflows", ignore_errors=True)` (com log line listando arquivos deletados) para purgar instalações prévias. Sem renderização de workflow-summary em AGENTS.md nesta release (escopo enxuto — workflow narrative em AGENTS.md é deferida).
- **T-PB-3 — `[not-applicable]` doctor status.** Estende `_classify_workflows()` em `public_assets.py:240-256` para emitir `[not-applicable] codex:workflows/<wf>` para qualquer workflow em Codex (linear ou paralelo — Codex simplesmente não tem dispatcher). OpenCode mantém `[ok]` para linear e `[partial]` para paralelo. Atualiza o map de styling CLI em `dadaia_workspace/cli/commands/public.py` (ADR-ENG-1: reutiliza `cyan` do `[unsupported]`, adicionado como `elif` antes do branch existente).
- **T-PB-4 — `[skills]` table in `config.toml`.** Adiciona bloco TOML `[skills]\npaths = [".agents/skills"]` ao output de `_codex_config()` para Codex descobrir as skills universais sem hard-coded defaults. Bundle com T-PB-1 no mesmo commit (ambas modificam `_codex_config()`).

### Out-of-scope (deferido)

- **G4 — Hierarchical `AGENTS.md` para Codex.** Toca `spec_context` integration e per-repo materialization (camada CLI + features de contexto), não a projection pipeline. Deferida ao backlog candidate `agents-md-hierarchical-v1` (ADR-MP-4 + ADR-ARCH-4). O `_install_agents_md()` em `public_assets.py:273` **não** é tocado nesta release.
- **T-PB-5 — Edição constitucional adicional.** A constituição já foi amendada em 2026-05-16 com a seção "Pilares do Produto" (incluindo a menção a `[agents.<name>]` em Pilar 3); **nenhuma nova edição em `specs/constitution.md` é feita nesta release**. T-PB-5 do report original do platform-boundaries é considerado fechado pela amendment de 2026-05-16.
- **Workflow-summary em AGENTS.md** (proposto pelo platform-boundaries §6 Patch 2 como substituto textual para a remoção em T-PB-2). Não há renderização de "Workflows disponíveis" em AGENTS.md nesta release — fica como follow-up se o operador quiser.
- **Qualquer quarto runtime** (Gemini CLI, Cursor, Aider, Cline). ADR-MP-3 + ADR-ARCH-4 fixam: a adição de novo runtime é **emenda constitucional**, não release incremental.
- **Mudanças em `.claude/`, `.opencode/` e suas projeções.** A projeção Claude e OpenCode permanece exatamente como hoje; o pipeline OpenCode não ganha tratamento novo para `parallel_group` (essa é a limitação de runtime aceita — pillar text declara floor explicitamente).
- **Mudanças em `core/protocols/`, `core/models/`, `features/public/service.py`, `container.py`.** Por ADR-ARCH-3, nenhum novo Protocol e nenhuma nova feature module — toda a mudança é privada em `FileSystemPublicAssetManager`.
- **CI gate em `.github/workflows/ci.yml`.** Cobertura adicional para o novo código é assegurada via `pytest --cov` dentro do CI já existente (constitution L131 mínimo 80% no feature/infrastructure); nenhum novo job.
- **Mudança no SHA256 baseline em `.dadaia/agentic/manifest.json`.** O staging é intocado — só a renderização da projeção muda; nenhum asset em `public/` muda de SHA.

---

## Decisões arquiteturais

Quatro ADRs do arquiteto (Phase 2) sustentam esta release. Cada ADR tem racional completo no report `.dadaia/reports/dadaia-workspace/software-architect/2026-05-17T012117Z-multi-platform-pillar-position.html` (seção 7).

| ADR | Tema | Decisão (one-liner) |
|-----|------|---------------------|
| ADR-ARCH-1 | Option B vs Option A | **Endosso Option B sem amendment.** Layer contract preserved, `dadaia-workspace-dev-guardrail` rule preserved (lê `.dadaia/agentic/manifest.json` nominalmente citado na constituição), DRY de agent intent mantido (1 markdown × 3 transformers vs 30 source files). |
| ADR-ARCH-2 | Codex rendering target | **`[agents.<name>]` sub-tables dentro do `.codex/config.toml` existente** — opção (a) confirmada contra sibling `agents.toml` (b) e per-agent files (c). Atomic single-file write, content diff via `_compare_content()` já existente, nenhum novo path em `_runtime_expectations()`. |
| ADR-ARCH-3 | Renderer placement | **Private method em `FileSystemPublicAssetManager` (`infrastructure/public_assets.py`)** — opção (a) confirmada contra novo Protocol em `core/` (b — Speculative Generality, 1 caller único) e novo feature module (c — violaria "nenhuma feature importa outra feature"). Pure function sobre dict de frontmatter parsed; sem edição em `container.py`. |
| ADR-ARCH-4 | Pillar 3 scope (que NÃO promete) | **Pillar 3 nomeia explicitamente Claude Code / Codex / OpenCode**, limita parity contract a skills/agents/commands/rules; workflows com `parallel_group` permanecem **Claude-exclusive runtime capability** (degradação documentada: OpenCode `[partial]`, Codex `[not-applicable]`). Quarto runtime requer emenda constitucional. |

Quatro ADRs do engineer (Phase 2) operacionalizam a implementação. Racional em `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-17T012220Z-multi-platform-pillar-impact.html` (seção 9).

| ADR | Tema | Decisão (one-liner) |
|-----|------|---------------------|
| ADR-ENG-1 | `[not-applicable]` CLI styling | **Reutiliza `cyan`** (mesmo color de `[unsupported]`); novo `elif` antes do branch `[unsupported]` em `cli/commands/public.py:70-76`. Semântica relacionada (ambos "platform cannot do this"), sem nova cor para evitar visual noise. |
| ADR-ENG-2 | TOML emit strategy | **Manual block writer** (string concat + `_toml_escape()`) — stdlib only, sem `tomli_w` / `tomlkit`. Schema-fixed renderer de 20 linhas; constitution L17-28 stdlib-only mantida; supply-chain mínimo. |
| ADR-ENG-3 | Migration order | **3 commits ordenados:** T-PB-3 → (T-PB-4 + T-PB-1 squashed) → T-PB-2. T-PB-3 primeiro (additive, doctor honesto antes de remoção); T-PB-1+4 juntos (ambos modificam `_codex_config()`); T-PB-2 por último (removendo cópia depois do classifier estar correto). |
| ADR-ENG-4 | Test pattern | **Parametrized unit tests em pure functions** + 1 integration test por patch usando `tmp_path` e manager real. `_parse_agent_frontmatter` e `_render_agent_toml_block` são module-level (sem instantiation) — fast CI, edge cases isolados. |

---

## Requisitos Funcionais

### FR-1 — Codex agents renderizados como `[agents.<name>]` em `config.toml`

**O que (T-PB-1):** `_render_agents_into_codex_config()` (private em `FileSystemPublicAssetManager`) parseia `dadaia_workspace/public/agents/*.md`, extrai YAML frontmatter via regex (sem `pyyaml`), e emite blocos `[agents.<name>]` apendados ao output de `_codex_config()`. Whitelist `_TOML_SAFE_AGENT_FIELDS = {"name", "description", "model", "tools"}`. Nomes com hífen (`software-engineer`) viram quoted keys (`[agents."software-engineer"]`). Descrições com `>` folded YAML viram TOML multi-line basic strings (`"""..."""`). O tuple `(None, …, "codex:agents", False)` em `_runtime_expectations():432` é removido; `codex:agents` vira content-comparison via `_compare_content()`.

**Verificação:** após `dadaia public install --target codex --force`, `.codex/config.toml` contém 10 blocos `[agents.<name>]` (um por agente em `public/agents/`); `doctor` reporta `[ok] codex:config.toml` (não mais `[unsupported] codex:agents`).

### FR-2 — Cessar cópia de workflows para `.codex/workflows/`

**O que (T-PB-2):** Remove a linha `self._copy_tree(agentic_dir / "workflows", codex_dir / "workflows", force, installed)` em `_install_codex():322`. Adiciona cleanup unconditional `shutil.rmtree(codex_dir / "workflows", ignore_errors=True)` (com log line `[removed] {path} (not-applicable: codex has no workflow runtime)` antes da deleção). Cleanup é unconditional (não respeita `force` flag) porque dead files são sempre incorretos quando o asset type é removido.

**Verificação:** após `dadaia public install --target codex --force`, o diretório `.codex/workflows/` não existe; `find .codex -name "*.workflow.md"` retorna vazio.

### FR-3 — Doctor status `[not-applicable]` + install short-circuit

**O que (T-PB-3):** Estende `_classify_workflows()` em `public_assets.py:240-256` para emitir `[not-applicable] codex:workflows/<wf>` para todo workflow em Codex (linear OU paralelo). OpenCode mantém `[ok]` para linear e `[partial]` para paralelo. CLI styling em `cli/commands/public.py:70-76` adiciona novo branch `elif item.startswith("[not-applicable]"):` antes do branch `[unsupported]`, reutilizando `cyan` (ADR-ENG-1). O install short-circuit é estrutural: depois de T-PB-2, `_install_codex()` simplesmente não tem mais chamada que copie workflows — a curta-circuitação acontece pela ausência da chamada, não por uma checagem explícita do classifier no runtime de install.

**Verificação:** `doctor` emite `[not-applicable] codex:workflows/<wf>` para todos os 12 workflows em `public/workflows/`; emite `[partial] opencode:workflows/<wf>` apenas para os 5 com `parallel_group`; emite `[ok] opencode:workflows/<wf>` para os lineares; emite `[ok] claude:workflows/<wf>` para todos.

### FR-4 — `[skills]` table em `config.toml`

**O que (T-PB-4):** Estende `_codex_config()` para apendar bloco TOML `[skills]\npaths = [".agents/skills"]\n` após o array `approved_commands`. Documentado em `_runtime_expectations()` para que `doctor` valide a presença via `_compare_content()`. Bundle com T-PB-1 (mesmo commit, mesma função).

**Verificação:** após `dadaia public install --target codex --force`, `.codex/config.toml` contém literalmente `[skills]` e `paths = [".agents/skills"]`; `doctor` reporta `[ok] codex:config.toml`.

---

## Requisitos Não-Funcionais

### NFR-1 — Pillar 3 enforcement preserved

A constitution amendment de 2026-05-16 nomeia explicitamente os três runtimes e nomeia o floor. Esta release **não regride** o enforcement: cinco status do doctor (`[ok]`, `[drift]`, `[missing]`, `[unsupported]`, `[not-applicable]`) cobrem todo o spectrum de honestidade; a rule sempre ativa `dadaia-workspace-dev-guardrail` continua lendo `.dadaia/agentic/manifest.json` sem mudança no formato.

### NFR-2 — SHA256 baseline em `.dadaia/agentic/manifest.json` intocado

Nenhum asset em `dadaia_workspace/public/` muda de conteúdo. O staging permanece byte-idêntico; o manifest.json mantém os mesmos SHA256s para os 53 assets. Só a *renderização da projeção* muda. O `dadaia-workspace-dev-guardrail` rule é preservado por construção — não há rewrite do rule file.

### NFR-3 — Surface de comandos doctor inalterada

`dadaia public doctor`, `dadaia public install`, `dadaia public stage` mantêm signature, flags e exit codes idênticos. A única mudança visível para o operador é (a) um novo prefixo `[not-applicable]` em algumas linhas (em cyan), (b) `.codex/workflows/` desaparece e (c) `.codex/config.toml` cresce com blocos `[agents.<name>]` e `[skills]`. Nenhum novo subcomando, nenhum flag novo, nenhum exit code novo.

### NFR-4 — Stdlib only (constitution Stack L17-28)

Sem nova dependência runtime. Sem `pyyaml`, sem `tomli_w`, sem `tomlkit`. Parser de YAML frontmatter usa `re` + string slicing (consistente com `_prepare_agent_for_opencode()` existente em `public_assets.py:62-97`). Writer TOML é manual block construction com `_toml_escape()` (ADR-ENG-2). `pyproject.toml` `[tool.poetry.dependencies]` não ganha nenhuma entrada.

### NFR-5 — 4-layer architecture preservada

Por ADR-ARCH-3, toda a mudança vive dentro de `FileSystemPublicAssetManager` em `infrastructure/public_assets.py`. `core/protocols/storage.py` permanece intocado; `features/public/service.py` permanece 20-line passthrough intocado; `container.py` permanece intocado. O `PublicAssetManager` Protocol (`stage`, `install`, `doctor`) mantém a semântica original — rendering é detalhe de implementação de `install`/`doctor`.

### NFR-6 — Cobertura ≥80% no infrastructure module (constitution L131)

15 testes novos (6 unit T-PB-1 + 2 unit T-PB-2 + 4 unit T-PB-3 + 2 unit T-PB-4 + 1 integration T-PB-1) garantem que `_render_agents_into_codex_config`, `_parse_agent_frontmatter`, `_render_agent_toml_block`, `_toml_escape` e o branch `[not-applicable]` de `_classify_workflows` sejam exercitados. Test pattern (ADR-ENG-4): unit tests em pure functions sem `tmp_path` para velocidade; um integration por patch usando manager real e `tmp_path`.

### NFR-7 — Backwards compatibility por drift detection

Workspaces com `.codex/config.toml` antigo (sem `[agents]` e sem `[skills]`) verão `[drift] codex:config.toml` no próximo `dadaia public doctor` — comportamento correto, não breakage. A correção é `dadaia public install --target codex --force`. Sem data loss; old config é substituído pelo rendered output. Documentar em release notes ao tag final.

### NFR-8 — Zero overlap com `agent-comms-v1` (preserva trabalho concluído)

Auditoria explícita (SE Impact §8): `agent-comms-v1` (CLOSURE 2026-05-17) tocou `core/protocols/handoff_validator.py`, `core/models/handoff.py`, `infrastructure/stdlib_handoff_validator.py`, `features/reports_validation/service.py`, `cli/commands/reports.py`, `public/schemas/handoff-v1.schema.json` e `public/skills/dadaia-handoff-emitter/`. Esta release toca exclusivamente `infrastructure/public_assets.py`, `cli/commands/public.py`, `tests/unit/test_public_assets.py`. **Zero arquivos colidentes.** O schema `handoff-v1.schema.json` e o validator `handoff_validator.py` **não são tocados** nesta release.

---

## Critérios de aceite (verification triples)

| # | FR/NFR | Verificação | Comando | Esperado |
|---|--------|-------------|---------|----------|
| AC-1 | FR-1 | `[agents.<name>]` rendered for all 10 agents | `grep -c "^\[agents\." .codex/config.toml` (após `dadaia public install --target codex --force`) | `10` |
| AC-2 | FR-1 | Hyphenated names get quoted keys | `grep -c '^\[agents\."software-engineer"\]\|^\[agents\."software-architect"\]' .codex/config.toml` | `≥2` |
| AC-3 | FR-1 | Codex agents passa o doctor | `dadaia public doctor 2>&1 \| grep "codex:config.toml"` | linha começa com `[ok]` |
| AC-4 | FR-2 | `.codex/workflows/` não existe após install | `ls .codex/workflows/ 2>&1` | `No such file or directory` |
| AC-5 | FR-2 | Cleanup remove diretório legado | pre-create `.codex/workflows/legacy.workflow.md`, depois `dadaia public install --target codex --force`, depois `ls .codex/workflows/ 2>&1` | `No such file or directory` |
| AC-6 | FR-3 | Doctor emite `[not-applicable]` para Codex workflows | `dadaia public doctor 2>&1 \| grep -c "^\[not-applicable\] codex:workflows/"` | `≥12` (todos workflows em `public/workflows/`) |
| AC-7 | FR-3 | Doctor mantém `[partial]` para OpenCode parallel | `dadaia public doctor 2>&1 \| grep -c "^\[partial\] opencode:workflows/"` | `≥5` (workflows com `parallel_group`) |
| AC-8 | FR-3 | CLI styling cyan aplicado | inspect `cli/commands/public.py` | branch `elif item.startswith("[not-applicable]"):` antes do `[unsupported]`, com `style="cyan"` |
| AC-9 | FR-4 | `[skills]` table presente | `grep -A1 "^\[skills\]" .codex/config.toml` | contém `paths = [".agents/skills"]` |
| AC-10 | NFR-4 | Zero novas dependências | `git diff main -- pyproject.toml \| grep "^+" \| grep -v "^+++"` | vazio (ou só metadata) |
| AC-11 | NFR-5 | `core/` e `features/public/` intocados | `git diff main --name-only \| grep -E "core/protocols/storage\.py\|features/public/service\.py\|container\.py"` | vazio |
| AC-12 | NFR-6 | Cobertura ≥80% no infrastructure | `pytest --cov=dadaia_workspace.infrastructure.public_assets --cov-fail-under=80` | exit 0 |
| AC-13 | NFR-8 | `handoff_validator.py` e schema intocados (agent-comms-v1) | `git diff main --name-only \| grep -E "handoff_validator\|handoff-v1\.schema\.json"` | vazio |
| AC-14 | Global | Doctor verde | `dadaia specs doctor` | `0 errors, 0 warnings` |
| AC-15 | Global | `agent-comms-v1` artifacts intactos no archive | `ls specs/_archive/releases/agent-comms-v1/` | `SPEC.md PLAN.md TASKS.md CLOSURE.md` (sem mudança) |

---

## Estimativa

| Métrica | Valor | Fonte |
|---------|-------|-------|
| LoC novas | ~89 | SE Impact §1 |
| LoC modificadas | ~54 | SE Impact §1 |
| LoC total impactada | ~143 | (89+54) |
| Arquivos modificados | 3 | `infrastructure/public_assets.py`, `cli/commands/public.py`, `tests/unit/test_public_assets.py` |
| Arquivos novos | 0 | SE Impact §1 ("no new files, no new modules") |
| Novas dependências runtime | 0 | NFR-4 — constitution stdlib-only preserved |
| Testes novos | 15 | 6 unit T-PB-1 + 2 unit T-PB-2 + 4 unit T-PB-3 + 2 unit T-PB-4 + 1 integration T-PB-1 |
| Commits planejados | 3 | ADR-ENG-3 ordering: T-PB-3 → (T-PB-1+T-PB-4 squashed) → T-PB-2 |

---

## Risks

Pulled e consolidado do SE Impact §8 risk register e do architect §3.

| # | Risco | Likelihood | Impact | Mitigação |
|---|-------|------------|--------|-----------|
| R1 | Backwards compat de `.codex/config.toml` antigo: drift detection rola em workspaces upgrade | H (todos os users) | L | Intentional drift; doctor surface; `dadaia public install --target codex --force` corrige; documentar em release notes (devops-engineer) |
| R2 | Drift durante transition entre commits (T-PB-3 já mergeado, T-PB-1+4 pendente) | L | L | Squash-merge dos 3 commits no PR final; estado intermediário só visível em feature branch, nunca em released tag |
| R3 | Codex TOML schema drift (sub-table semantics muda em release futura Codex) | M | M | Pin schema version em code comment; teste lê known-good structure; doctor content-compare detecta drift; monitor Codex changelog (software-engineer) |
| R4 | YAML frontmatter parser regression em agent file com shape inusitado (literal block `|`, nested dict, quoted multiline) | M | L | Parser drops unknown shapes silently; `if "name" in fm` guard previne broken section header; parametrized test por agent file conhecido (TDD gate) |
| R5 | `shutil.rmtree` em `.codex/workflows/` deleta user-added files | L | M | `dadaia-workspace-dev-guardrail` rule já proíbe edição direta em `.codex/`; user-added files são out-of-scope por construção; log line lista deletados antes do remove (software-engineer) |
| R6 | Nova cor `cyan` para `[not-applicable]` confunde com `[unsupported]` (mesma cor) | L | L | Aceito; semântica relacionada justifica color reuse (ADR-ENG-1); palavra distinta (`not-applicable` vs `unsupported`); release notes documentam |
| R7 | OpenCode parallel sequentialization permanece (G3) | Aceito | — | Runtime-level platform limit; pillar text documenta floor; revisitar somente se OpenCode shippar parallel orchestrator |
| R8 | Hierarchical AGENTS.md (G4) deferido pode dar a impressão de "trabalho pela metade" | L | L | ADR-MP-4 + ADR-ARCH-4 documentam deferral; backlog candidate `agents-md-hierarchical-v1` registrado; current universal AGENTS.md ainda "works" como single-file persona |

### Open Questions

**Nenhuma.** A grill-me Phase 1 (`2026-05-17T011435Z-multi-platform-grill-me.html` §5) reportou **0 open questions** ao operador — todos os 8 problemas identificados (P1–P8) foram resolvidos por inspeção do código ou por reasonable call documentado como ADR-MP-1..ADR-MP-6. Phase 2 (architect + engineer) reconfirmou independentemente e adicionou 4+4 ADRs sem novas perguntas. Esta Phase 3 (synthesis) não introduz ambiguidade nova. Approval do operador desta SPEC é o único gate restante para PLAN.

---

## Dependencies / Lineage

### Input package autoritativo

Esta SPEC sintetiza quatro reports HTML produzidos no ciclo de discovery 2026-05-16 → 2026-05-17 sobre o Pilar 3:

1. **PE Discovery (Phase 0):** `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T233537Z-platform-boundaries-analysis.html` — Gap analysis G1–G5, Option A vs Option B comparison, recommendation Option B; architect validation embed.
2. **PE Grill-Me (Phase 1):** `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T011435Z-multi-platform-grill-me.html` — Reconfirma gaps, registra 6 ADRs (MP-1..MP-6), brief de Phase 2 para architect e engineer, **0 open questions ao operador**.
3. **Architect Position (Phase 2a):** `.dadaia/reports/dadaia-workspace/software-architect/2026-05-17T012117Z-multi-platform-pillar-position.html` — Independent re-validation de Option B (endorsed), Codex rendering target (a), renderer placement (a), pillar scope definition (ADR-ARCH-1..4).
4. **SE Impact (Phase 2b):** `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-17T012220Z-multi-platform-pillar-impact.html` — Per-patch LoC + tests matrix, parser code sketch, migration order (3 commits), risk register, ADR-ENG-1..4.

### Constitutional framing (binding)

- `specs/constitution.md` § "Pilares do Produto" L15–31 (amended 2026-05-16) — **Pilar 3** é o mandato binding desta release. O texto da pillar nomeia explicitamente Claude Code / Codex / OpenCode, fixa o floor (`workflows com parallel_group` Claude-exclusive; OpenCode `[partial]`; Codex `[not-applicable]`), e cita `.dadaia/agentic/manifest.json` como o detection mechanism preservado.
- `specs/constitution.md` § "Princípios de Arquitetura" L65+ — 4-layer rule (`CLI → Features → Core ← Infrastructure`) preservada por ADR-ARCH-3.
- `specs/constitution.md` § "Stack Tecnológica (Obrigatória)" L33+ — stdlib-only mantido por ADR-ENG-2.

### Release lineage

- **Predecessor:** `agent-comms-v1` (CLOSURE 2026-05-17, archived em `specs/_archive/releases/agent-comms-v1/`) — zero overlap por NFR-8.
- **Successor candidato (deferido):** `agents-md-hierarchical-v1` (G4) — adicionado ao backlog quando esta release alcançar CLOSURE.

### Backlog source

- `specs/backlog/candidates.md` § Candidatas ativas — topo da lista (entry promovida nesta sessão para `## Histórico`).

---

## Out of scope (reafirmado)

- G4 hierarchical AGENTS.md → `agents-md-hierarchical-v1` (backlog).
- Quarto runtime (Gemini CLI, Cursor, Aider, Cline) → emenda constitucional, não release.
- Edição em `specs/constitution.md` — a amendment de 2026-05-16 já fechou T-PB-5; nenhuma nova edição.
- Edição em `.claude/`, `.opencode/`, `.agents/`, `dadaia_workspace/public/` (projeções e source dos assets) — só renderização do output muda.
- Edição em `core/`, `features/`, `container.py` — por ADR-ARCH-3.
- Workflow-summary em AGENTS.md (deferred).
- CI gate adicional.
- Mudança em `agent-comms-v1` artifacts (SPEC/PLAN/TASKS/CLOSURE/schema/validator).

---

## Referências

- PE Discovery (Phase 0): `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T233537Z-platform-boundaries-analysis.html`
- PE Grill-Me (Phase 1): `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T011435Z-multi-platform-grill-me.html`
- Architect Position (Phase 2a): `.dadaia/reports/dadaia-workspace/software-architect/2026-05-17T012117Z-multi-platform-pillar-position.html`
- SE Impact (Phase 2b): `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-17T012220Z-multi-platform-pillar-impact.html`
- Constitution (binding): `specs/constitution.md` § "Pilares do Produto" (L15–31), § "Princípios de Arquitetura" (L65+), § "Stack Tecnológica" (L33+).
- Backlog source: `specs/backlog/candidates.md` (§ Candidatas ativas → § Histórico nesta sessão)
- Predecessor: `specs/_archive/releases/agent-comms-v1/SPEC.md` (CLOSURE 2026-05-17)
- Active lifecycle: `specs/releases/ACTIVE.md` (flipped to `multi-platform-parity-v1 / SPEC` nesta sessão)
- Code sites under audit: `dadaia_workspace/infrastructure/public_assets.py` (linhas 240–256, 273, 289–300, 302–353, 432, 484–489, 496, 528–546), `dadaia_workspace/cli/commands/public.py` (linhas 70–76), `tests/unit/test_public_assets.py` (linha 69)
