# Spec: Release — infra-correctness-v1

> **Status:** Aprovado
> **Release ID:** infra-correctness-v1
> **Owner:** product-engineer
> **Created:** 2026-05-20
> **Phase:** SPEC
> **Branch:** `release/infra-correctness-v1` (cut from `main` after `codex-agent-orchestration-parity-v1` CLOSURE)
> **Predecessor:** `codex-agent-orchestration-parity-v1` (CLOSED + ARCHIVED 2026-05-20)
> **Discovery inputs:**
> - Backlog entries: `specs/backlog/candidates.md` lines 22–23, 28, 44–47
> - specialist audit 2026-05-20: software-architect (7-item list), software-engineer-python
>   (implementation detail with file:line citations), frontend-engineer (panel surface),
>   design-specialist (token system + dark mode design), qa-engineer (coverage baseline),
>   researcher (CSP mechanics + migration patterns)
> - CLOSURE drifts: `_archive/releases/agents-r3-v1/CLOSURE.md § Drifts` (DRIFT-3, DRIFT-4),
>   `_archive/releases/multi-platform-parity-v1/CLOSURE.md § Drifts §1`,
>   `_archive/releases/dadaia-workspace-panel-r3-v1/SPEC.md §8.2` + CLOSURE Drifts §csp

---

## 1. Objetivo

Liquidar 7 itens de dívida técnica confirmada que atravessaram múltiplas releases sem
resolução — todos com evidência concreta, escopo delimitado e sem dependências de ADR.
Nenhum item aqui é especulativo: cada um tem file:line de origem, bug reproduzível ou
métrica de cobertura verificável.

Esta release **não inclui** trabalho que requer grill-me ou ADR prévia (dark mode,
workflow-run-dispatcher, cli-asset-granular, codex-design-pilot). Aqueles ficam em
backlog até as sessões de grill-me agendadas no Step 4.

---

## 2. Contexto

Após o fechamento de `codex-agent-orchestration-parity-v1` o workspace está com 20
agentes funcionais, projeção multi-runtime completa e SDD gate ativo. O acúmulo de
dívida técnica nos itens abaixo foi deliberado nas releases anteriores — todos marcados
como `# DEAD:`, `xfail`, ou "deferred from r2 explicitly" — e agora é o momento de
liquidar antes que a próxima release funcional (provavelmente `codex-design-frontend-
projection-pilot-v1`) comece.

---

## 3. Itens da release

### Item 1 — cli-reports-exit-code-alignment-v1

**Problema:** `dadaia_workspace/cli/commands/reports.py:138` chama
`resolve_workspace_root()` FORA do bloco `try/except WorkspaceNotInitializedError`
(que começa na linha 141). Quando o workspace não está inicializado, a exceção se
propaga sem tratamento → Typer sai com código 1 em vez do código 3 esperado.

**Evidência:** `tests/integration/test_cli_reports.py::test_10_workspace_not_initialized_exits_3`
marcado `xfail` com comentário explícito referenciando esta candidata. Qualquer
`dadaia reports` fora de um workspace inicializado falha silenciosamente.

**Fix:** mover a linha 138 (`workspace_root = resolve_workspace_root()`) para dentro
do `try` que começa na linha 141. Remover o `xfail` do teste e adicionar assertion
positiva de exit code 3.

**Ficheiro:** `dadaia_workspace/cli/commands/reports.py:130-160`
**Owner:** software-engineer-python
**Esforço:** 0.5 h

---

### Item 2 — agent-topology-guard-i6-skill-link-validation-v1

**Problema:** `scripts/check_agent_topology.py` tem invariantes I1–I5, mas não I6.
A frontmatter de cada agente em `dadaia_workspace/public/agents/*.md` declara
`skills: [...]` porém nenhum check valida que os diretórios de skill referenciados
existem em `dadaia_workspace/public/skills/`. O skill `frontend-design` ainda está
ausente (`codex-design-frontend-projection-pilot-v1` pré-requisito), o que significa
que ao ser adicionado à frontmatter do `frontend-engineer` ANTES que o diretório
exista, I6 deve falhar ruidosamente.

**Evidência:** `_archive/releases/agents-r3-v1/CLOSURE.md § Drifts DRIFT-3`. Script
inspecionado: apenas 5 funções `check_i*`, sem I6. Sem I6, deploys com skill refs
quebradas passam silenciosamente.

**Fix:** adicionar `check_i6_skill_links(agents: dict, errors: list[str]) -> None`
que itera sobre `frontmatter["skills"]` de cada agente e verifica que
`SKILLS_DIR / skill_name` é diretório existente. Conectar em `main()` após I5.

**Ficheiros:** `scripts/check_agent_topology.py`
**Owner:** ai-engineer
**Esforço:** 1 h

---

### Item 3 — public-assets-coverage-lift-v1

**Problema:** `dadaia_workspace/infrastructure/public_assets.py` tem 1,390 linhas e
cobertura de **55%** (714 statements, ~323 missed). Os caminhos críticos sem cobertura
incluem:
- `doctor()` + D-CX-1..5 drift checks (~130 linhas)
- `_install_workspace_guardrail_pair` + `_doctor_guardrail_pair` (~90 linhas)
- `_runtime_expectations` (~80 linhas)
- `_install_codex_agents`, `_install_opencode` (~50 linhas)

O arquivo `tests/unit/infrastructure/test_public_assets.py` **não existe**. O arquivo
`tests/unit/test_public_assets.py` (280+ linhas) existe mas cobre caminhos diferentes.

**Evidência:** `_archive/releases/multi-platform-parity-v1/CLOSURE.md § Drifts §1`.
Ranges originais (378–433, 595–650, 675–696) estão stale após
`codex-agent-orchestration-parity-v1` — requerer nova medição (`pytest --cov`) antes
de começar a escrita dos testes.

**Fix:** criar `tests/unit/infrastructure/test_public_assets.py` com 12–15 funções de
teste cobrindo `doctor()`, `_install_workspace_guardrail_pair`, `_doctor_guardrail_pair`,
`_runtime_expectations`, `_install_codex_agents` e `_install_opencode`. Meta: ≥ 80%
de cobertura no módulo.

**Passo 0 obrigatório:** rodar `pytest --cov=dadaia_workspace/infrastructure/public_assets --cov-report=term-missing`
para identificar os ranges reais antes de escrever os testes.

**Ficheiros:** `dadaia_workspace/infrastructure/public_assets.py`,
`tests/unit/infrastructure/test_public_assets.py` (novo)
**Owner:** software-engineer-python
**Esforço:** 3–4 h

---

### Item 4 — panel-csp-script-src-harden

**Problema:** `dadaia_workspace/features/panel/handler.py:392` tem CSP:
```
"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
```

`'unsafe-inline'` em `script-src` é desnecessário: os dois scripts inline no panel
são completamente estáticos (zero interpolação de runtime). Podem ser substituídos por
hashes SHA-256.

**Evidência:** dois scripts inline identificados:
- `dadaia_workspace/features/panel/views/index.py:62-63` — dois scripts (provavelmente
  distintos; verificar)
- `dadaia_workspace/features/panel/views/wrapper.py:35` — um script

`'unsafe-inline'` em `style-src` pode permanecer por ora — CSS inline é mais
difícil de hash (tema dinâmico via `var(--color-*)`) e não é vetor de ataque XSS
equivalente a scripts.

**Fix:**
1. Computar SHA-256 de cada script único (base64-encoded, prefixo `sha256-`).
2. Substituir `'unsafe-inline'` em `script-src` por `'sha256-<hash1>' 'sha256-<hash2>'`
   (tantos hashes quantos scripts distintos).
3. Adicionar teste unitário que verifica que o header CSP não contém `unsafe-inline`
   na diretiva `script-src`.

**Ficheiros:** `dadaia_workspace/features/panel/handler.py:392`,
`dadaia_workspace/features/panel/views/index.py`,
`dadaia_workspace/features/panel/views/wrapper.py`
**Owner:** devops-engineer (CSP) / software-engineer-python (test)
**Esforço:** 1.5 h

---

### Item 5 — panel-sqlite-workflows-drop

**Problema:** `dadaia_workspace/features/telemetry/store/schema.py` tem
`SCHEMA_VERSION = 5`. A migração 5 cria tabelas `workflows` e `workflow_agents`
marcadas `# DEAD:` (substituídas pelo canonical workflow reader no panel-r3). As tabelas
existem em todo banco SQLite vivo mas têm zero linhas de produção.

**Fix:** adicionar migração 6:
```sql
DROP TABLE IF EXISTS workflow_agents;  -- filho antes do pai (FK)
DROP TABLE IF EXISTS workflows;
```
Incrementar `SCHEMA_VERSION` para 6. Adicionar teste que verifica que após migration
as tabelas não existem.

**Nota:** `workflow_agents` deve ser dropada ANTES de `workflows` se houver FK ativa
(por segurança, mesmo que SQLite não enforce FKs por padrão).

**Ficheiros:** `dadaia_workspace/features/telemetry/store/schema.py`
**Owner:** software-engineer-python
**Esforço:** 0.5 h

---

### Item 6 — install-scope-flags-r3

**Problema:** `dadaia public install` aceita apenas `--target` e `--force`. Internamente
o comando já distingue entre assets do workspace-root (guardrail pair) e assets de repos
consumidores, mas não há forma de o operador restringir o escopo de instalação pela CLI.
Isso foi diferido explicitamente em `_archive/releases/agents-r2-v1/PLAN.md §8.6`.

**Fix:**
1. Adicionar parâmetro `scope: Literal["all", "repos-only", "workspace-only"] = "all"`
   à assinatura de `FileSystemPublicAssetManager.install()`.
2. Adicionar flags `--repos-only` e `--workspace-only` ao comando `dadaia public install`
   em `dadaia_workspace/cli/commands/public.py`. Mutuamente exclusivos; sem ambos = `all`.
3. Propagar o scope para `_install_workspace_guardrail_pair` e para o loop de repos.
4. Adicionar teste de integração para cada scope.

**Ficheiros:** `dadaia_workspace/cli/commands/public.py`,
`dadaia_workspace/infrastructure/public_assets.py`
**Owner:** software-engineer-python
**Esforço:** 2 h

---

### Item 7 — init-legacy-resolver-fix

**Problema:** `dadaia_workspace/cli/commands/init.py:14-22` define `_resolve_workspace()`
que sobe do cwd procurando por `.claude/` OR `.dadaia/` **sem verificar o sentinel**
`states/spec_contexts.json`. O resolver canônico em
`dadaia_workspace/core/workspace_resolver.py` usa o sentinel
`.dadaia/states/spec_contexts.json` como critério definitivo.

Cenário de falha: `dadaia init` rodado de dentro de `repos/dadaia-workspace/` encontra
o `.dadaia/` do sub-repo (sem sentinel) e retorna o sub-repo como root em vez do
workspace-root real. Isso pode sobrescrever assets em local errado.

**Fix:** adicionar `resolve_workspace_root_for_init(cwd: Path) -> Path` em
`dadaia_workspace/core/workspace_resolver.py`. Esta função:
1. Tenta o sentinel walk (idêntico ao `resolve_workspace_root` atual).
2. Se não encontrar sentinel → retorna `cwd` (comportamento seguro para first-time init).
3. `init.py` passa a chamar esta função em vez de `_resolve_workspace()`.
4. Remover `_resolve_workspace()` de `init.py` (dead code após a migração).

**Ficheiros:** `dadaia_workspace/core/workspace_resolver.py`,
`dadaia_workspace/cli/commands/init.py`
**Owner:** software-engineer-python
**Esforço:** 1 h

---

## 4. Fora de escopo

- `panel-dark-mode` — requer grill-me (paleta × dark mode interaction; 4 operator
  decisions da design-specialist pendentes)
- `panel-workflow-run-dispatcher` — requer ADR: sync vs async, CSRF, thread safety
- `codex-design-frontend-projection-pilot-v1` — requer 5 ADRs (CX-001..005) + update
  de framing; blocked em grill-me
- `cli-asset-granular` (`dadaia public list`) — requer decisão de output shape
- `panel-workspace-resolver-fix` — necessita reprodução do bug antes de especificar
  (diferente do Item 7 que tem cenário claro)
- `agents-md-hierarchical-v1` — requer revisão de obsolescência vs TOML approach
- Qualquer mudança em memory HTML (`specs/memory/`)
- Upgrade de dependências ou mudanças de pyproject.toml além de SCHEMA_VERSION

---

## 5. Critérios de aceite

- [ ] `tests/integration/test_cli_reports.py::test_10_workspace_not_initialized_exits_3` passa (sem xfail)
- [ ] `scripts/check_agent_topology.py` tem função `check_i6_skill_links` e reporta I6 FAIL quando skill ref quebrada
- [ ] `pytest --cov=dadaia_workspace/infrastructure/public_assets --cov-report=term-missing` reporta ≥ 80%
- [ ] Header CSP do panel não contém `unsafe-inline` na diretiva `script-src`
- [ ] `SCHEMA_VERSION == 6`; tabelas `workflows` e `workflow_agents` ausentes após migration
- [ ] `dadaia public install --repos-only` e `dadaia public install --workspace-only` funcionam sem erro
- [ ] `dadaia init` rodado de dentro de `repos/dadaia-workspace/` não sobrescreve workspace-root errado

---

## 6. Decisões fixadas

| ID | Tema | Decisão |
|----|------|---------|
| D1 | Scope do fix de exit code | Mover linha 138 para dentro do try; NÃO mudar o código de saída target (3 continua correto) |
| D2 | I6 — scope da validação | Apenas `skills:` frontmatter vs diretórios `public/skills/`; NÃO valida conteúdo dos arquivos de skill |
| D3 | Coverage target | ≥ 80% no módulo `public_assets.py`; NÃO 100% (caminhos de OS error são aceitáveis sem mock) |
| D4 | CSP style-src | `'unsafe-inline'` em `style-src` permanece (CSS dinâmico); apenas `script-src` é hardenado |
| D5 | Migration 6 — ordem | `workflow_agents` antes de `workflows` por segurança FK |
| D6 | install scope flags | Mutuamente exclusivos; ausência de ambos = comportamento atual ("all") |
| D7 | init resolver fallback | `resolve_workspace_root_for_init` retorna `cwd` quando sentinel não encontrado (seguro para fresh init) |

---

## 7. Dependências e riscos

| Risco | Mitigação |
|-------|-----------|
| Ranges de coverage em `public_assets.py` mudaram desde o backlog | Passo 0 obrigatório: rodar `--cov` antes de escrever testes |
| Migration 6 corrompe banco se tiver dados | `DROP TABLE IF EXISTS` é idempotente; tabelas são DEAD com zero linhas |
| Hash SHA-256 muda se script mudar | Teste de regressão no CI valida CSP header; qualquer mudança ao script force atualizar hash |
| `init` fix muda comportamento de cwd detection | Cenário de first-time init sem sentinel cobre o caso legítimo; unit test obrigatório |

---

## 8. Referências

- `_archive/releases/agents-r3-v1/CLOSURE.md` — DRIFT-3 (I6), DRIFT-4 (exit code)
- `_archive/releases/multi-platform-parity-v1/CLOSURE.md` — Drifts §1 (coverage)
- `_archive/releases/dadaia-workspace-panel-r3-v1/SPEC.md §8.2` — CSP + workflows drop
- `specs/backlog/candidates.md` lines 22–23, 28, 44–47
- specialist audit 2026-05-20 (software-architect, software-engineer-python,
  frontend-engineer, design-specialist, qa-engineer, researcher)
