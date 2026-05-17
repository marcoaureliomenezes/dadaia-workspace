# Plan: Release — multi-platform-parity-v1

> **Status:** Aprovado
> **Release ID:** multi-platform-parity-v1
> **Phase:** PLAN (SPEC Aprovado 2026-05-17; ACTIVE.md remains `release: none / phase: none` — flips only at IMPLEMENTATION)
> **Owner:** product-engineer
> **Created:** 2026-05-17
> **Plan version:** 1
> **SPEC:** `specs/releases/multi-platform-parity-v1/SPEC.md` (Status: Aprovado)

---

## Resumo do plano

- **O que:** 4 patches (T-PB-1..T-PB-4) fechando G1+G2+G3+G5 do Pilar 3 — `infrastructure/public_assets.py` + `cli/commands/public.py`. ~148 LoC, 18 testes, 0 deps novas.
- **Ordem:** 3 commits (ADR-ENG-3): Phase 1 (T-PB-3 classifier) → Phase 2 (T-PB-1+T-PB-4 squash, TOML emit) → Phase 3 (T-PB-2 delete + cleanup).
- **Riscos:** drift intencional de `.codex/config.toml` (doctor surface); parser YAML em frontmatter inusitado (parametrize gate); cleanup de `.codex/workflows/` (dev-guardrail + log visível).
- **Zero overlap:** nenhum arquivo colide com `agent-comms-v1` (NFR-8 / AC-13). Sem mudança em `core/`, `features/`, `container.py`, `dadaia_workspace/public/` (NFR-5 / AC-11). Manifest SHA256 intocado (NFR-2).

---

## Decisões arquiteturais

Inherited da SPEC (linhas 64–83). Restate de uma linha cada:

- **ADR-ARCH-1** — Option B (staged pipeline, fixed); layer contract + manifest + `dadaia-workspace-dev-guardrail` preserved.
- **ADR-ARCH-2** — Codex agents = sub-tables `[agents.<name>]` em `.codex/config.toml` (single-file write, `_compare_content()`).
- **ADR-ARCH-3** — Renderer = private method em `FileSystemPublicAssetManager` (`infrastructure/public_assets.py`); sem novo Protocol/feature/container edit.
- **ADR-ARCH-4** — Pillar 3 scope: skills/agents/commands/rules paridade; `parallel_group` workflows = Claude-exclusive (OpenCode `[partial]`, Codex `[not-applicable]`).

Engineer ADRs (operationalize):

- **ADR-ENG-1** — `[not-applicable]` CLI = cyan (mesmo de `[unsupported]`); `elif` em `cli/commands/public.py:70-76`.
- **ADR-ENG-2** — TOML emit = manual block writer + `_toml_escape()`, stdlib-only; cleanup helper `_log_cleanup_error()` (concern #2) substitui `ignore_errors=True` por warning visível em stderr.
- **ADR-ENG-3** — Migration order = 3 commits: T-PB-3 → (T-PB-1+T-PB-4 squashed) → T-PB-2.
- **ADR-ENG-4** — Test pattern = parametrize-on-dict pure functions + 1 integration por patch em `tmp_path`.
- **ADR-ENG-5** — Backwards-compat policy de `.codex/config.toml`: user edits OUT-OF-SCOPE per `.claude/rules/dadaia-workspace-dev-guardrail.md` (projeção lib-originada em `.dadaia/agentic/manifest.json`). Renderer **sobrescreve sem preservação**; doctor `[drift]` é a surface correta. Alinha com `.claude/settings.json`. Extensão user-side = arquivo irmão fora do manifest.
- **ADR-ENG-6** — Atomic write: novo helper `_atomic_write_text(dst, content)` em `infrastructure/public_assets.py` via `dst.with_suffix(dst.suffix + ".tmp")` + `os.replace()` (extensão da constitution L105). `_write_generated()` (`public_assets.py:469-475`, atualmente NÃO atômico — `dst.write_text(...)` direto) refatorado para usar o helper, cobrindo `.codex/config.toml`, `.claude/settings.json`, `.codex/hooks.json`, `opencode.json`.

---

## Resolução de open questions (pre-TASKS review)

**Q1 — Agent name surface: lib-originated only?** → **lib-originated only**. Evidência: `public_assets.py:141` (staging lê só `agentic_dir/agents`); `public_assets.py:432` (runtime expectations conhecem só destino lib); `.claude/rules/dadaia-workspace-dev-guardrail.md` proíbe edits user-side em `.codex/`. Implicação: risco adversarial baixo, mas **defensive escaping permanece obrigatório como floor** (T-PB-1 #7/#8). Sem hardening adicional.

**Q2 — `.codex/config.toml` atômico?** → **NÃO** hoje. Evidência: `_codex_config()` (`public_assets.py:528-546`) produz string; `_install_codex()` (`:330-335`) escreve via `self._write_generated(...)`; `_write_generated()` (`:469-475`) faz `dst.write_text(...)` direto sem `.tmp + os.replace()`. Mitigação: ADR-ENG-6 introduz `_atomic_write_text()` em Phase 2, cobrindo todos os generated files.

---

## Estratégia de execução — 3 commits, 3 phases

| Phase | Commit | Tasks | Tema | Risco | Justificativa |
|-------|--------|-------|------|-------|---------------|
| 1 | C1 | T-PB-3 | `[not-applicable]` doctor status + short-circuit | Baixo (additive) | Estabelece classification API que Phase 2/3 dependem; doctor honesto antes da remoção (ADR-ENG-3). |
| 2 | C2 | T-PB-4 + T-PB-1 | `[skills]` table + Codex `[agents.<name>]` + atomic write helper | Médio (novo TOML emit) | Ambos modificam output de `_codex_config()`; squash evita commit intermediário parcial. Inclui DELETE do teste linha 69 (NÃO ajustar). |
| 3 | C3 | T-PB-2 | Remove `_copy_tree(..."workflows"...)` `:322` + cleanup visível | Baixo (deletion) | Removido após classifier reportar `[not-applicable]`. Cleanup via `shutil.rmtree(..., onerror=_log_cleanup_error)` purga instalações prévias com warning auditável. |

Cada phase = 1 commit, atomicamente revertable (ver § Rollback).

---

## Per-phase breakdown

### Phase 1 — T-PB-3 — `[not-applicable]` doctor status + install short-circuit

**Files touched (LoC):**

| Path | Mudança | LoC est. |
|------|---------|----------|
| `dadaia_workspace/infrastructure/public_assets.py` | Estende `_classify_workflows()` linhas 240–256: novo branch que emite `[not-applicable] codex:workflows/<wf>` para todo workflow em Codex (linear OU paralelo). OpenCode mantém `[ok]`/`[partial]`. | +~12 / -~2 |
| `dadaia_workspace/cli/commands/public.py` | Linhas 70–76: novo branch `elif item.startswith("[not-applicable]"):` antes do branch `[unsupported]`, com `style="cyan"` (ADR-ENG-1). | +~4 |
| `tests/unit/test_public_assets.py` | 4 testes novos parametrize-on-dict para `_classify_workflows` (linear-codex, parallel-codex, linear-opencode, parallel-opencode). | +~30 |

**Funções:**
- Modified: `_classify_workflows()` em `public_assets.py:240`.
- No new private helpers nesta phase (a classification permanece dentro do mesmo método).

**Tests required:**
- 4 unit tests (ADR-ENG-4 parametrize-on-dict, sem `tmp_path`): cobertura dos 4 quadrantes (Codex × Linear/Parallel, OpenCode × Linear/Parallel).

**Acceptance criteria slice (da SPEC):**
- AC-6 — Doctor emite `[not-applicable]` para Codex workflows (`grep -c "^\[not-applicable\] codex:workflows/"` ≥12).
- AC-7 — Doctor mantém `[partial]` para OpenCode parallel (`grep -c "^\[partial\] opencode:workflows/"` ≥5).
- AC-8 — CLI styling cyan aplicado (inspect `cli/commands/public.py`: `elif item.startswith("[not-applicable]"):` antes do `[unsupported]`).

**Verification command:**

```bash
pytest tests/unit/test_public_assets.py -k "classify_workflows" -q
dadaia public doctor 2>&1 | grep -E "^\[(not-applicable|partial|ok)\] (codex|opencode):workflows/"
```

---

### Phase 2 — T-PB-1 + T-PB-4 — Codex `[agents.<name>]` + `[skills]` table

**Files touched (LoC):**

| Path | Mudança | LoC est. |
|------|---------|----------|
| `dadaia_workspace/infrastructure/public_assets.py` | Novos helpers privados: `_parse_agent_frontmatter(text: str) -> dict` (regex stdlib-only, sem `pyyaml`), `_render_agent_toml_block(name: str, fm: dict) -> str`, `_toml_escape(value) -> str`, `_render_agents_into_codex_config(agents_dir: Path) -> str`, `_atomic_write_text(dst: Path, content: str) -> None` (ADR-ENG-6). Whitelist `_TOML_SAFE_AGENT_FIELDS = {"name", "description", "model", "tools"}`. Estende `_codex_config()` para apendar (a) 10 blocos `[agents.<name>]` (T-PB-1) e (b) bloco `[skills]\npaths = [".agents/skills"]` (T-PB-4). Remove tuple `(None, …, "codex:agents", False)` de `_runtime_expectations():432`; adiciona `codex:config.toml` à content-comparison via `_compare_content()`. Refatora `_write_generated()` linhas 469-475 para usar `_atomic_write_text()` em vez de `dst.write_text(...)` direto. | +~70 / -~7 |
| `tests/unit/test_public_assets.py` | DELETAR teste que lock'a `[unsupported] codex:agents` em `tests/unit/test_public_assets.py:69` (NÃO ajustar — `[unsupported]` desaparece como status válido para `codex:agents` nesta release). Adicionar 10 testes novos: 8 unit T-PB-1 (parse hyphenated names → quoted keys, folded YAML `>` → TOML `"""..."""`, drop unknown fields, drop missing `name`, parse `model`/`tools` arrays, end-to-end render single agent, **escape `"` e `]` em name** [#7], **escape `"""` em description** [#8]) + 2 unit T-PB-4 (`[skills]` table emit, paths array literal). 1 integration test T-PB-1 usando manager real em `tmp_path` com 2 fixture agents. | +~108 / -~8 |

**Funções:**
- New: `_parse_agent_frontmatter`, `_render_agent_toml_block`, `_toml_escape`, `_render_agents_into_codex_config`, `_atomic_write_text` (5 helpers privados — o último por ADR-ENG-6).
- Modified: `_codex_config()`, `_runtime_expectations()` (remove tuple linha 432), `_install_codex()` (chama `_render_agents_into_codex_config`), `doctor()` (consome novo path), `_write_generated()` (passa a chamar `_atomic_write_text` — ADR-ENG-6).

**Tests required:**
- 10 unit tests (parametrize-on-dict, ADR-ENG-4, fast, sem filesystem). Distribuídos como 8 T-PB-1 + 2 T-PB-4:
  - **T-PB-1 #1** — `test_parse_agent_frontmatter_extracts_whitelisted_fields` — feed dict-like raw frontmatter, assert apenas `name/description/model/tools` sobrevivem.
  - **T-PB-1 #2** — `test_render_agent_toml_block_quotes_hyphenated_name` — input `{"name": "software-engineer", ...}` → output contém `[agents."software-engineer"]`.
  - **T-PB-1 #3** — `test_render_agent_toml_block_emits_triple_quoted_description` — input com `description` multi-line → output usa `description = """..."""`.
  - **T-PB-1 #4** — `test_render_agent_toml_block_drops_unknown_fields` — input com `foo: bar` → não aparece no output.
  - **T-PB-1 #5** — `test_render_agent_toml_block_drops_missing_name` — input sem `name` → função retorna `""` ou pula bloco.
  - **T-PB-1 #6** — `test_render_agent_toml_block_emits_tools_array_literal` — `tools: [Read, Edit]` → output `tools = ["Read", "Edit"]`.
  - **T-PB-1 #7** — `test_render_agent_toml_block_escapes_quote_in_name` (**adversarial — concern #1**) — input `{"name": "a\"]\nb", "description": "x"}` → assert (a) output passa em `tomllib.loads()` round-trip; (b) chave resultante contém `\"` e `]` escapado; (c) `\n` não quebra o bloco. Floor obrigatório para função que constrói TOML a partir de texto.
  - **T-PB-1 #8** — `test_render_agent_toml_block_escapes_triple_quote_in_description` (**adversarial — concern #1**) — input `{"name": "x", "description": "a\"\"\"b"}` → assert (a) output passa em `tomllib.loads()` round-trip; (b) description não rompe o bloco `"""..."""`; (c) fallback para basic string com `\n` escape se necessário.
  - **T-PB-4 #1** — `test_skills_table_emits_paths_array_literal` — assert output contém `[skills]\npaths = [".agents/skills"]`.
  - **T-PB-4 #2** — `test_skills_table_appears_once_after_agents_blocks` — assert ordem: agents → skills (regex anchored).
- 1 integration test (manager real, `tmp_path`, 2 fixtures de agent — exercita pipeline completo: parse → render → **atomic write via `_atomic_write_text` [ADR-ENG-6]** → diff). O comportamento atômico é verificado nesta integration via assert de que `<dst>.tmp` não existe após sucesso e `dst` contém o conteúdo esperado byte-a-byte.

**Acceptance criteria slice (da SPEC):**
- AC-1 — `[agents.<name>]` rendered for all 10 agents (`grep -c "^\[agents\." .codex/config.toml` = 10).
- AC-2 — Hyphenated names get quoted keys (`grep -c '^\[agents\."software-engineer"\]'` ≥1).
- AC-3 — `doctor` reporta `[ok] codex:config.toml`.
- AC-9 — `[skills]` table presente (`grep -A1 "^\[skills\]" .codex/config.toml` contém `paths = [".agents/skills"]`).
- AC-12 — Cobertura ≥80% no infrastructure (`pytest --cov=dadaia_workspace.infrastructure.public_assets --cov-fail-under=80`).

**Verification command:**

```bash
pytest tests/unit/test_public_assets.py -q
pytest tests/integration/ -k "public_assets" -q
dadaia public install --target codex --force
grep -c "^\[agents\." .codex/config.toml          # expect: 10
grep -A1 "^\[skills\]" .codex/config.toml         # expect: paths = [".agents/skills"]
dadaia public doctor 2>&1 | grep "codex:config.toml"   # expect: [ok] codex:config.toml
# Atomic-write smoke (ADR-ENG-6): no leftover .tmp after install
find .codex -name "*.tmp" 2>&1                    # expect: vazio
# Adversarial frontmatter round-trip (concerns #1, T-PB-1 #7/#8)
python3 -c "import tomllib; tomllib.loads(open('.codex/config.toml').read())"  # expect: no exception
```

---

### Phase 3 — T-PB-2 — Stop copying workflows to `.codex/workflows/`

**Files touched (LoC):**

| Path | Mudança | LoC est. |
|------|---------|----------|
| `dadaia_workspace/infrastructure/public_assets.py` | Remove linha `self._copy_tree(agentic_dir / "workflows", codex_dir / "workflows", force, installed)` em `_install_codex():322`. Adiciona cleanup unconditional: log line `[removed] {path} (not-applicable: codex has no workflow runtime)` listando arquivos a deletar, depois `shutil.rmtree(codex_dir / "workflows", onerror=_log_cleanup_error)` (concern #2 — Option A: visible-but-non-fatal). Novo helper module-level `_log_cleanup_error(func, path, exc_info)` escreve `[cleanup-warning] {path}: {exc}\n` em `sys.stderr`. Cleanup é unconditional (não respeita `force`) porque dead files são sempre incorretos quando o asset type é removido. **Rationale concern #2:** `ignore_errors=True` mascara `PermissionError`/`OSError` reais; install reporta sucesso mas filesystem fica em estado inconsistente. Visible warnings via stderr são o tradeoff correto — não-fatal mas auditável. | +~11 / -~3 |
| `tests/unit/test_public_assets.py` | 3 testes novos unit T-PB-2: (a) cleanup remove existing `.codex/workflows/` directory + arquivos `.workflow.md`; (b) log line `[removed]` emitida listando arquivos deletados antes do `rmtree`; (c) **`test_cleanup_warns_on_permission_error_does_not_raise` [concern #2]** — pré-criar `.codex/workflows/legacy.workflow.md` com `os.chmod(0o000)` no diretório pai, capturar stderr via `capsys`, assert install completa successfully AND stderr contém literal `[cleanup-warning]`. | +~32 |

**Funções:**
- Modified: `_install_codex()` em `public_assets.py:322` (remove `_copy_tree` call, add cleanup block que chama `shutil.rmtree(..., onerror=_log_cleanup_error)`).
- New: `_log_cleanup_error(func, path, exc_info)` module-level helper — escreve `[cleanup-warning] {path}: {exc}\n` em `sys.stderr`, retorna sem re-raise.

**Tests required:**
- 3 unit tests (usando `tmp_path` para pré-criar `.codex/workflows/legacy.workflow.md` e validar deleção + log + permission-error path).

**Acceptance criteria slice (da SPEC):**
- AC-4 — `.codex/workflows/` não existe após install (`ls .codex/workflows/ 2>&1` = `No such file or directory`).
- AC-5 — Cleanup remove diretório legado (pre-create `.codex/workflows/legacy.workflow.md`, depois `dadaia public install --target codex --force`, depois `ls .codex/workflows/ 2>&1` = `No such file or directory`).

**Verification command:**

```bash
mkdir -p .codex/workflows && touch .codex/workflows/legacy.workflow.md
dadaia public install --target codex --force
ls .codex/workflows/ 2>&1                  # expect: No such file or directory
find .codex -name "*.workflow.md"          # expect: vazio
pytest tests/unit/test_public_assets.py -k "cleanup or workflows_removed" -q
```

---

## Test strategy

**Total: 18 new tests** (atualizado pós-review do operador: +2 adversarial em T-PB-1 [concern #1] + 1 permission-error em T-PB-2 [concern #2]).

| Patch | Unit (parametrize-on-dict, sem `tmp_path`) | Integration (manager real, `tmp_path`) | Total |
|-------|-------------------------------------------|---------------------------------------|-------|
| T-PB-3 | 4 (classify_workflows × 4 quadrantes) | 0 | 4 |
| T-PB-1 | 8 (parse, render, hyphen→quoted, folded YAML, drop unknown, drop missing name, **escape `"`/`]`/`\n` em name [#7]**, **escape `"""` em description [#8]**) | 1 (manager real em `tmp_path` com 2 fixture agents — valida atomic write end-to-end via `_atomic_write_text` [ADR-ENG-6]) | 9 |
| T-PB-4 | 2 ([skills] table emit, paths array literal) | 0 | 2 |
| T-PB-2 | 3 (cleanup remove existing, log line emitida, **permission-error path warns to stderr sem raise [#3]**) | 0 | 3 |
| **Total** | **17 unit** | **1 integration** | **18** |

**Pattern (ADR-ENG-4):** `_parse_agent_frontmatter`, `_render_agent_toml_block`, `_toml_escape` são module-level functions — parametrize over `(input_dict, expected_output)` sem instanciar `FileSystemPublicAssetManager`. Resultado: CI fast, edge cases isolados, sem I/O de filesystem para 17 dos 18 testes.

**Adversarial inputs (concern #1):** T-PB-1 #7 e #8 usam fixtures literais com shapes documentados — `{"name": "a\"]\nb", "description": "x"}` e `{"name": "x", "description": "a\"\"\"b"}`. Assertion é round-trip via stdlib `tomllib.loads()` (Python 3.11+). Floor de segurança para qualquer função que constrói output estruturado a partir de texto, mesmo quando o input atual é lib-controlled (ver § Resolução de open questions → Q1).

**DELETE explicitamente:** o teste em `tests/unit/test_public_assets.py:69` que lock'a `[unsupported] codex:agents` como expected status. Após T-PB-1, `codex:agents` deixa de existir como path no `_runtime_expectations()` — esse teste fica logicamente impossível. NÃO ajustar para outro status; deletar e substituir pelos novos 9 tests (8 unit + 1 integration) que cobrem o novo path `codex:config.toml` com `[agents.<name>]` blocks.

**Cobertura:** ≥80% no módulo `dadaia_workspace.infrastructure.public_assets` (constitution L131; AC-12). Comando: `pytest --cov=dadaia_workspace.infrastructure.public_assets --cov-fail-under=80`.

---

## Risk register

Pulled diretamente do SE Impact §8 + architect §3 (consolidado na SPEC § Risks). 5 linhas mandatórias para o PLAN:

| # | Risco | L | I | Mitigação operacional |
|---|-------|---|---|----------------------|
| R1 | Backwards compat de `.codex/config.toml` em workspaces user existentes: novo SHA do rendered output gera `[drift]` ao primeiro `doctor` pós-upgrade. Caso edge: user com `[agents.custom]` hand-edited em `.codex/config.toml` perde edição silenciosamente (concern #3 do review). | H | L | Intentional drift; doctor surface comunica honestly. Release notes (escritas pelo devops-engineer no CLOSURE) devem dizer: "run `dadaia public install --target codex --force` after pulling this release". Sem migration script — drift detection é a UX correta. **Policy (ADR-ENG-5, concern #3):** `.codex/config.toml` é projeção lib-originada listada em `.dadaia/agentic/manifest.json`; user edits são OUT-OF-SCOPE per `dadaia-workspace-dev-guardrail` rule. Renderer sobrescreve sem preservação. Para estender Codex config user-side: criar arquivo irmão fora do manifest (não modificar `config.toml` direto). |
| R2 | Drift detection durante transição: Phase 1 mergeada mas Phases 2/3 pendentes em PR aberto → workspace em estado intermediário onde doctor diz `[not-applicable]` mas install ainda copia | L | L | Squash-merge dos 3 commits no PR final, OU merge sequencial direto em main (não há ramo de release intermediário publicado). Estado intermediário só visível em feature branch, nunca em released tag. CI gate em cada commit garante green no estado intermediário também. |
| R3 | Stdlib-only compliance (NFR-4): tentação de adicionar `pyyaml` para parsear frontmatter ou `tomli_w` para emit TOML | L | M | Constitution L17–28 binding. Parser usa `re` + string slicing (consistente com `_prepare_agent_for_opencode()` em `public_assets.py:62-97` que já faz isso). Writer usa manual block construction (ADR-ENG-2). PR review gate: `git diff main -- pyproject.toml` deve estar vazio (AC-10). |
| R4 | Codex schema drift: `[agents.<name>]` semantics muda em release futura Codex (sub-table convention vira array, ou top-level moves to `agents.toml` sibling file) | M | M | Pin schema version em code comment no helper `_render_agent_toml_block()`. Test reads known-good structure como golden file. `_compare_content()` em doctor detecta drift entre rendered output e disk. Monitor Codex changelog (responsabilidade do devops-engineer no follow-up). |
| R5 | Teste que lock'a `[unsupported] codex:agents` em `tests/unit/test_public_assets.py:69` é "ajustado" em vez de deletado, criando dead test que vai falhar silently no próximo refactor | L | L | **Explicit instruction no PLAN (acima): DELETE, não adjust.** Code review gate: verificar que `git log -p tests/unit/test_public_assets.py` mostra deletion explícita da assertion `assert "[unsupported] codex:agents" in output`. Substituição é 7 testes novos cobrindo `codex:config.toml` content. |

Riscos R6/R7/R8 da SPEC (color reuse cyan, OpenCode parallel sequentialization, G4 deferral) são aceitos sem mitigação operacional adicional — já documentados como aceitos.

---

## Defensive coding policy

Três floors de segurança/correctness obrigatórios para qualquer código tocado nesta release (e candidatos a serem promovidos ao constitution em release futura, se a equipe convergir):

1. **Adversarial input testing.** Helpers que emitem TOML/JSON/YAML a partir de texto livre testam contra inputs adversariais: `]`, `"`, `\n`, `\\`, e `"""` em campos de nome/descrição. Em desta release: T-PB-1 #7 (`test_render_agent_toml_block_escapes_quote_in_name`) e T-PB-1 #8 (`test_render_agent_toml_block_escapes_triple_quote_in_description`). Aplica mesmo quando o input atual é lib-controlled (ver Q1) — defensive escaping é o **floor**, não escalation. Verificação: `tomllib.loads()` round-trip em CI.
2. **Visible failure modes.** Operações de filesystem que "sucedem" deixando side effects stale (arquivos antigos, diretórios corrompidos) são proibidas. `shutil.rmtree` cleanup usa `onerror=_log_cleanup_error` que escreve `[cleanup-warning] {path}: {exc}` em `sys.stderr` — non-fatal mas visível. Substitui `ignore_errors=True` (anti-pattern: silencia `PermissionError`/`OSError` reais). Em desta release: T-PB-2 #3 (`test_cleanup_warns_on_permission_error_does_not_raise`); ADR-ENG-2-amended (cleanup helper rationale).
3. **Atomic file writes.** `.codex/config.toml` (e por extensão `.claude/settings.json`, `.codex/hooks.json`, `opencode.json` — todos os generated files via `_write_generated()`) escrevem via padrão `.tmp` + `os.replace()` da constitution L105. Estado pré-release: `_write_generated()` em `dadaia_workspace/infrastructure/public_assets.py:469-475` NÃO é atômico — usa `dst.write_text(content, encoding="utf-8")` direto. Esta release introduz `_atomic_write_text()` helper (ADR-ENG-6) e refatora `_write_generated()` para usá-lo. Verificação smoke em Phase 2: `find .codex -name "*.tmp"` deve ser vazio após install bem-sucedido.

---

## Rollback strategy

Cada phase = revert independente. Estrutura 3-commits permite revert por phase isolado.

| Phase | Revert efeito |
|-------|---------------|
| C3 (T-PB-2) | Workflows voltam a ser copiados para `.codex/workflows/`; Phase 1 mantém `[not-applicable]` (estado intermediário tolerável). |
| C2 (T-PB-1+4) | `[agents.<name>]` + `[skills]` removidos do `config.toml`; tuple `codex:agents` re-adicionada em `_runtime_expectations()`; doctor volta a `[unsupported]`. Run `dadaia public install --target codex --force` para realinhar. |
| C1 (T-PB-3) | Doctor volta a `[ok]` em Codex workflows lineares (G5 reaparece); cyan styling removido. |

**Full rollback:** `git revert --no-edit <C3> <C2> <C1>` + `dadaia public install --target codex --force` + `dadaia public doctor` (confirma estado pré-release). Recovery após revert parcial: sempre re-rodar install --force + doctor.

---

## Acceptance gate

PLAN → TASKS apenas com confirmação operadora de que **AC-1..AC-15 da SPEC** são testáveis verbatim:

- AC-1/2/3 (Codex agents) → Phase 2; AC-4/5 (workflows purged) → Phase 3; AC-6/7/8 (`[not-applicable]` + cyan) → Phase 1; AC-9 (`[skills]` table) → Phase 2.
- AC-10/11/13/15 (NFRs zero-impact) + AC-14 (specs doctor) → cross-cutting PR/CI gate. AC-12 (cobertura ≥80%) → Phase 2.

Se algum AC não-testável: voltar à SPEC, não criar TASKS contra ambiguidade.

---

## Dependencies / sequence

**Externas:** zero novas deps runtime (NFR-4/AC-10); zero mudança CI (constitution L131 ≥80% já satisfeito); zero infra; sem releases em-vôo (`agent-comms-v1` em CLOSURE).

**Interna (ADR-ENG-3):** Phase 1 (T-PB-3 classifier) → Phase 2 (T-PB-1+T-PB-4 bundle, _codex_config() modificado) → Phase 3 (T-PB-2 delete+cleanup). Cada phase = 1 commit; Phase N+1 só inicia com N=`[x]` no TASKS.md. Sem paralelização — sequência estrita por design.

**Predecessor:** `agent-comms-v1` (CLOSURE 2026-05-17, zero overlap por NFR-8/AC-13/AC-15). **Successor deferido:** `agents-md-hierarchical-v1` (G4) → `specs/backlog/candidates.md` no CLOSURE desta release.

---

## Estimativa final

Re-confirmação dos números da SPEC § Estimativa (linhas 174–184):

| Métrica | Valor | Origem |
|---------|-------|--------|
| LoC novas | ~94 | SE Impact §1 + ADR-ENG-6 helper (+5) |
| LoC modificadas | ~54 | SE Impact §1 |
| LoC total impactada | ~148 | (94+54) |
| Arquivos novos | 0 | SE Impact §1 ("no new files, no new modules") |
| Arquivos modificados | 3 | `infrastructure/public_assets.py`, `cli/commands/public.py`, `tests/unit/test_public_assets.py` |
| Novas dependências runtime | 0 | NFR-4 — constitution stdlib-only preserved |
| Testes novos | 18 | 17 unit + 1 integration (table acima — +2 adversarial concern #1 + 1 permission-error concern #2) |
| Commits planejados | 3 | C1 (Phase 1), C2 (Phase 2 bundle), C3 (Phase 3) |
| Release branches | 1 | branch única `release/multi-platform-parity-v1` (a ser criada em IMPLEMENTATION) |
| Constitution edits | 0 | T-PB-5 considerado fechado pela amendment de 2026-05-16 (SPEC § Out-of-scope) |

---

## Definition of Done (PLAN session)

- PLAN.md citado verbatim na SPEC (`specs/releases/multi-platform-parity-v1/SPEC.md`); 3 phases com files/funções/tests/ACs/verification.
- 18 testes desagregados (17 unit + 1 integration) — +2 adversarial T-PB-1 + 1 permission-error T-PB-2.
- Risk register 5 linhas (R1 estendido com ADR-ENG-5); Defensive coding policy com 3 floors; ADRs ENG-5/ENG-6 registrados; Q1/Q2 resolvidos por inspeção (file:line evidence).
- Rollback per-phase; `dadaia specs doctor` 0/0; TASKS.md **NÃO** criado; ACTIVE.md **NÃO** modificado (release/phase: none).

---

## Referências

- **SPEC:** `specs/releases/multi-platform-parity-v1/SPEC.md` (Aprovado).
- **Discovery inputs:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T233537Z-platform-boundaries-analysis.html`, `.../2026-05-17T011435Z-multi-platform-grill-me.html`, `.../software-architect/2026-05-17T012117Z-multi-platform-pillar-position.html`, `.../software-engineer/2026-05-17T012220Z-multi-platform-pillar-impact.html`.
- **Constitution:** `specs/constitution.md` § Pilares (L15–31), § Arquitetura (L65+), § Stack (L33+), § JSON Source of Truth (L102–106 — atomic write mandate base para ADR-ENG-6).
- **ACTIVE.md:** `specs/releases/ACTIVE.md` (intocado, `release: none / phase: none`). **Predecessor:** `specs/_archive/releases/agent-comms-v1/`.
- **Code sites:** `dadaia_workspace/infrastructure/public_assets.py` (linhas 141, 240–256, 273, 289–300, 302–353, 432, 469–475, 484–489, 496, 528–546), `cli/commands/public.py:70-76`, `tests/unit/test_public_assets.py:69` (DELETAR).
