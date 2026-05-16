# Spec: Feature — Release Pipeline (PyPI v0.1.0)

> **Status:** Em revisão
> **Versão:** 0.1
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/SPEC.md`, `specs/foundation/SPEC.md`, `specs/features/devops-engineer/SPEC.md`, `specs/features/dev-workspace-governance/SPEC.md`
> **Report de entrada:** `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-14T122340Z-pypi-pipeline.md`

---

## Contexto

O `dadaia-workspace` chegou à v3.0 das specs sem qualquer pipeline de CI/CD. O repositório não possui `.github/workflows/`. Não existem tags git. O nome `dadaia-workspace` no PyPI ainda **não está reservado**. Pull requests entram em `main` sem validação automática de lint, typecheck ou testes; a branch `main` não está protegida.

Esta feature **fecha a porta de saída**: define o gitflow mínimo, o pipeline de CI e o pipeline de release v0.1.0 no PyPI usando **OIDC trusted publishing** (sem token estático). A meta operacional concreta é que `pip install dadaia-workspace==0.1.0` em ambiente limpo dispare `dadaia --help` sem erros — e que o caminho automatizado para chegar lá seja gravado em código e em documentação.

Right-sizing é princípio explícito: **1 OS (ubuntu-latest), 1 Python version (3.12), sem matrix**. Tudo o que não entra na v0.1 está enumerado no "Fora de Escopo".

---

## Glossário

| Termo | Definição |
|---|---|
| **OIDC trusted publishing** | Mecanismo do PyPI que permite GitHub Actions publicar sem token estático, autenticando via OpenID Connect (`id-token: write`). |
| **Pending publisher** | Recurso do PyPI que cria o projeto como "aguardando publicação" + permite configurar o trusted publisher antes da primeira publicação real (caminho recomendado para reservar nome sem expor token). |
| **Environment `pypi`** | Recurso do GitHub Actions que age como gate (opcional com required reviewers) e cujo nome deve bater com o trusted publisher configurado no PyPI. |
| **Coverage gate** | Step do CI que falha se a cobertura cair abaixo de um threshold. Implementado via `pytest-cov --cov-fail-under`. |
| **Smoke test** | Teste pós-publicação que instala o pacote em venv limpa e verifica que `dadaia --help` e `dadaia init` funcionam. |

---

## Usuários e Goals

### US-REL-001: Garantir qualidade automatizada em todo PR

- **Como** mantenedor do produto
- **Quero** que todo PR seja validado por lint, typecheck e testes antes do merge
- **Para** evitar regressões silenciosas em `main`

**Critérios de Aceite:**
- Dado um PR aberto contra `main`, quando o GitHub Actions executa o workflow `ci.yml`, então 3 jobs rodam em paralelo: `lint`, `typecheck`, `test`.
- Dado o job `test`, quando executa `pytest --cov-fail-under=80`, então falha se a cobertura cair abaixo de 80%.
- Dado um PR com título não-Conventional-Commits, quando o job `pr-title` valida o título, então o PR é bloqueado.
- Dado branch protection ativa em `main`, quando algum dos jobs `lint`/`typecheck`/`test` falha, então o merge fica bloqueado até correção.

### US-REL-002: Publicar v0.1.0 no PyPI via tag

- **Como** mantenedor
- **Quero** que `git push origin v0.1.0` dispare a publicação automatizada
- **Para** evitar `poetry publish` manual com token local

**Critérios de Aceite:**
- Dado uma tag `v0.1.0` em `main`, quando faço `git push origin v0.1.0`, então `release.yml` é disparado.
- Dado o pipeline disparado, então 3 jobs rodam em sequência: `validate` → `build` → `publish`.
- Dado `validate`, então a tag (`v0.1.0`) é comparada com `pyproject.toml` (`0.1.0`); divergência falha o pipeline.
- Dado `build`, então `poetry build` produz `dadaia_workspace-0.1.0.tar.gz` (sdist) e `dadaia_workspace-0.1.0-py3-none-any.whl` (wheel).
- Dado `publish`, então `pypa/gh-action-pypi-publish@release/v1` autentica via OIDC trusted publishing (sem secret) e publica em `https://pypi.org/project/dadaia-workspace/0.1.0/`.

### US-REL-003: Smoke test pós-publicação

- **Como** mantenedor
- **Quero** confirmar automaticamente que a publicação está consumível
- **Para** detectar bugs de empacotamento antes que usuários reportem

**Critérios de Aceite:**
- Dado um `publish` bem-sucedido, quando o job `smoke-test` roda em seguida, então `pip install dadaia-workspace==<tag>` em venv limpa termina exit 0.
- Dado a instalação, quando o smoke executa `dadaia --help`, então a saída contém os grupos de comando esperados (`init`, `context`, `repos`, `public`, `doctor`, `academy`, `export`, `import`, `orchestrate`).
- Dado a instalação, quando o smoke executa `dadaia init` em tmpdir limpo, então `.dadaia/states/spec_contexts.json` é criado sem erros.

### US-REL-004: Versionamento e disciplina de release

- **Como** mantenedor
- **Quero** uma fonte única de verdade da versão e um passo a passo documentado
- **Para** evitar inconsistências entre git, PyPI e CHANGELOG

**Critérios de Aceite:**
- Dado o repositório, quando consulto a versão, então `pyproject.toml` é a única fonte de verdade.
- Dado `RELEASING.md`, quando sigo os passos, então a tag, o `pyproject.toml` e o `CHANGELOG.md` ficam sincronizados antes do push.
- Dado `CHANGELOG.md`, quando registro uma release, então o formato segue Keep a Changelog 1.1.0 com seção `[Unreleased]` no topo.

---

## Requisitos Funcionais

### Gitflow e Branch Protection

- **FR-REL-001:** The repository shall enforce branch protection on `main` with: require PR before merging; required approvals = 1; dismiss stale approvals on push; require status checks `lint`, `typecheck`, `test` (and `pr-title` when applicable); require branches up to date before merging; require conversation resolution; block force push; block deletion; include administrators.
- **FR-REL-002:** A `.github/CODEOWNERS` file shall declare `marcoaureliomenezes` (or replacement operator) as global fallback owner, with explicit ownership rules for `.github/`, `pyproject.toml`, `Makefile`, and `scripts/`.
- **FR-REL-003:** Branch naming convention shall be: `feature/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `ci/<slug>`, `release/v<X.Y.Z>` (release branch optional for PATCH).
- **FR-REL-004:** PR titles shall follow Conventional Commits (`feat(scope): desc`, `fix(scope): desc`, etc.). Validation is enforced by a step in `ci.yml`.

### CI Workflow (`.github/workflows/ci.yml`)

- **FR-REL-005:** The CI workflow shall trigger on `push` to `main` and on `pull_request` (opened, synchronize, reopened).
- **FR-REL-006:** The CI workflow shall run **exactly four jobs in parallel** (3 always + 1 conditional): `lint`, `typecheck`, `test`; plus `pr-title` only on `pull_request` events.
- **FR-REL-007:** Every job shall run on `ubuntu-latest` with Python 3.12. No matrix in v0.1.
- **FR-REL-008:** Every job shall use Poetry installed via `pip install poetry` and cache `.venv` keyed on `hashFiles('poetry.lock')`. `poetry.lock` shall be committed in the repository.
- **FR-REL-009:** The `lint` job shall run: `poetry run ruff check dadaia_workspace/ tests/`, `poetry run ruff format --check dadaia_workspace/ tests/`, and `bash scripts/check_no_repo_local_claude.sh`.
- **FR-REL-010:** The `typecheck` job shall run: `poetry run mypy dadaia_workspace/` with the configuration declared in `pyproject.toml` (strict mode).
- **FR-REL-011:** The `test` job shall run: `poetry run pytest tests/ -v --tb=short --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80`. Coverage gate threshold = 80% on the `features/` layer per RF-QA-003. Threshold may be temporarily lowered during a gap-closing sprint **only by an explicit revision of this spec**; it shall not be silently relaxed.
- **FR-REL-012:** The `pr-title` job shall reject PR titles that do not match the regex `^(feat|fix|docs|style|refactor|test|chore|ci|perf|build|revert)(\([a-z0-9_-]+\))?: .+`.

### Release Workflow (`.github/workflows/release.yml`)

- **FR-REL-013:** The release workflow shall trigger on `push` of tags matching `v*.*.*`.
- **FR-REL-014:** The release workflow shall declare `permissions: contents: read` at workflow level and `id-token: write` at job level for the `publish` job only (principle of least privilege).
- **FR-REL-015:** The release workflow shall run 3 jobs in sequence: `validate` → `build` → `publish`. A 4th job `smoke-test` runs after `publish` (FR-REL-022).
- **FR-REL-016:** The `validate` job shall:
  - extract the tag version via `${GITHUB_REF_NAME#v}`;
  - extract the `pyproject.toml` version via `grep '^version = ' pyproject.toml`;
  - fail with a clear error if the two values differ.
- **FR-REL-017:** The `build` job shall run `poetry build` and upload the resulting `dist/` directory as an artifact named `dist-${{ github.ref_name }}` with `retention-days: 7`.
- **FR-REL-018:** The `publish` job shall:
  - depend on `build`;
  - set `environment: pypi`;
  - download the `dist-*` artifact;
  - run `pypa/gh-action-pypi-publish@release/v1` with no API token (OIDC trusted publishing).
- **FR-REL-019:** No PyPI API token (`PYPI_API_TOKEN` or equivalent) shall be stored as a GitHub Secret. OIDC is the only authentication path.

### PyPI Trusted Publisher (operator action)

- **FR-REL-020:** Before the first release, the operator shall create a **pending publisher** at https://pypi.org/manage/account/publishing/ with: PyPI project name `dadaia-workspace`, workflow file `release.yml`, environment `pypi`, repository owner/name matching the GitHub repo.
- **FR-REL-021:** The operator shall create a GitHub environment named `pypi` in repository settings with deployment branches restricted to tag pattern `v*.*.*`.

### Smoke Test (pós-publish)

- **FR-REL-022:** A `smoke-test` job in `release.yml` shall, after `publish` succeeds:
  - create a clean venv;
  - run `pip install dadaia-workspace==<tag>` (no `==<tag>` if not unstable behaviour observed; use exact pin for safety);
  - run `dadaia --help` and assert exit 0;
  - run `dadaia init` in `/tmp/smoke-ws` and assert `.dadaia/states/spec_contexts.json` exists;
  - run `dadaia context list` and `dadaia doctor` and assert exit 0.

### Versionamento

- **FR-REL-023:** `pyproject.toml` shall be the sole source of truth for the version. No `VERSION` file, no `__version__` hardcoded in code, no env-var-based versioning.
- **FR-REL-024:** Tag format shall be `v` + SemVer (e.g., `v0.1.0`, `v1.2.3`). `validate` job enforces tag↔pyproject equality.
- **FR-REL-025:** SemVer semantics for this library:
  - **PATCH** — bug fix; no CLI interface or JSON state contract changes
  - **MINOR** — new backwards-compatible capability (new command, new public asset type, new optional field)
  - **MAJOR** — breaking change (rename field in `spec_contexts.json`, removal of CLI command, change in default behavior)

### Documentação

- **FR-REL-026:** The repository shall contain `CHANGELOG.md` at root in Keep a Changelog 1.1.0 format with sections `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`. Section `[Unreleased]` shall always be present at the top.
- **FR-REL-027:** The repository shall contain `RELEASING.md` at root with the step-by-step procedure for a release (version bump, CHANGELOG update, commit, tag, push, monitor, smoke verification). Procedure must be safe to follow by a non-author operator.

### Pré-requisitos QA (gaps a fechar antes de v0.1.0)

- **FR-REL-028:** Three pre-existing test failures in the current suite shall be fixed before tagging `v0.1.0`:
  - `test_academy_modules` — Typer API incompatibility (`Parameter.make_metavar()` missing `ctx` argument);
  - `TestStage::test_stage_creates_all_expected_skills` — `EXPECTED_SKILLS` whitelist missing `dadaia-workspace-manager`;
  - `TestInstallAll::test_install_all_populates_universal_skills` — same `dadaia-workspace-manager` whitelist gap.
- **FR-REL-029:** Before tagging `v0.1.0`, unit tests shall be added for the currently-uncovered features so the 80% coverage gate is achievable: `features/export/service.py`, `features/import_/service.py`, `features/repos/service.py`, and CLI command modules `cli/commands/context.py`, `cli/commands/export.py`, `cli/commands/import_.py`, `cli/commands/doctor.py`. Scope, exact test files, and parametrization plan are governed by the QA strategy report referenced above; tasks for each gap closure live in `specs/TASKS.md` under Fase 5 (pré-release).

---

## Requisitos Não-Funcionais

- **NFR-REL-001 [Right-sizing]:** v0.1 explicitly excludes the items listed in the "Fora de Escopo" section below. Each excluded item has a documented justification.
- **NFR-REL-002 [Segurança]:** No PyPI token, no SSH key, no API credential shall be stored as a GitHub Secret in v0.1. OIDC trusted publishing is the only auth path.
- **NFR-REL-003 [Fail-fast]:** Every CI job shall exit on first failure. `validate` blocks `build`; `build` blocks `publish`; `publish` blocks `smoke-test`.
- **NFR-REL-004 [Reprodutibilidade]:** `poetry.lock` is committed; the same lock produces the same wheel.
- **NFR-REL-005 [Diagnosabilidade]:** Failed CI jobs shall provide log output sufficient for an autonomous agent to identify the failing step and the recovery action (consistent with RF-QA-007).
- **NFR-REL-006 [Honestidade]:** `validate` job shall never silently coerce a divergent version; it must fail loud with both values printed.

---

## Pré-Condições Operacionais (one-time, antes da primeira release)

1. **PyPI account ativa com 2FA** (e-mail do operador).
2. **Pending publisher criado** em https://pypi.org/manage/account/publishing/ com nome `dadaia-workspace`, workflow `release.yml`, environment `pypi`, repo owner/name corretos.
3. **GitHub environment `pypi` criado** com deployment branches restritos a tag pattern `v*.*.*`.
4. **GitHub Actions habilitado** no repositório (Settings → Actions → General → Allow all actions).
5. **Branch protection ativa** em `main` (após o primeiro run do `ci.yml` ser visível como required status check).
6. **`poetry.lock` commitado** na branch `main`.
7. **Workflows `ci.yml` e `release.yml`, `CODEOWNERS`, `CHANGELOG.md`, `RELEASING.md` commitados** (via PR aprovado).

---

## Critérios de Aceite v0.1.0 (release oficial)

- [ ] Tag `v0.1.0` em `main` dispara `release.yml`.
- [ ] Job `validate` passa: `v0.1.0` ↔ `pyproject.toml` 0.1.0.
- [ ] Job `build` passa: `dadaia_workspace-0.1.0-py3-none-any.whl` + `dadaia_workspace-0.1.0.tar.gz`.
- [ ] Job `publish` passa via OIDC.
- [ ] `https://pypi.org/project/dadaia-workspace/0.1.0/` exibe a release.
- [ ] Job `smoke-test` passa: `pip install dadaia-workspace==0.1.0` + `dadaia --help` + `dadaia init` exit 0.
- [ ] `ci.yml` passa em `main` (3 jobs) com cobertura ≥80%.
- [ ] Branch `main` protegida.
- [ ] 3 falhas pré-existentes do CI (FR-REL-028) corrigidas.

---

## Fora de Escopo (v0.1)

Cada item abaixo tem justificativa de exclusão; revisão futura pode reabrir.

| Item excluído | Justificativa |
|---|---|
| Matrix multi-OS (macOS, Windows) | NFR-003 restringe a Linux/macOS; sem demanda real para Windows; adicionar quando reportado |
| Matrix multi-Python (3.10, 3.11) | `pyproject.toml` exige `^3.12`; testar versões não-suportadas é ruído |
| Build de wheels manylinux/macos/windows | Pacote Python puro (sem extensões C); sdist + wheel padrão é suficiente |
| Trivy / SAST scan | Lib CLI sem superfície de containerização; sem ataques justificando scan em v0.1 |
| Codecov / coverage report externo | Gate local `--cov-fail-under=80` é suficiente; sem dependência de serviço externo |
| Renovate / Dependabot agressivo | Lib com 4–5 deps; sem necessidade de bumps semanais |
| GitHub Releases com changelog gerado | Changelog é manual (Keep a Changelog) em v0.1 |
| Sentry / error tracking | Fora de escopo de lib CLI |
| pre-commit framework | `scripts/check_no_repo_local_claude.sh` já é invocado como step de CI |
| Semantic-release | Versionamento manual via `pyproject.toml`; semantic-release introduz coupling commit↔versão prematuro |
| Assinatura sigstore de wheels | Considerar em v0.2+ se a comunidade pedir |

---

## Riscos

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| R1 | Nome `dadaia-workspace` no PyPI capturado por outro publisher antes da reserva | Alta | Pré-condição #2 (pending publisher) executada antes de qualquer push de tag |
| R2 | Trusted publisher não configurado antes do primeiro push de tag → `403 Forbidden` no `publish` | Alta | Procedimento RELEASING.md exige checklist de pré-condições antes da release |
| R3 | Tag divergente de `pyproject.toml` causa publicação inconsistente | Média | Job `validate` falha o pipeline (FR-REL-016) |
| R4 | Cobertura abaixo de 80% bloqueia toda branch | Média | FR-REL-029 obriga fechar gaps antes de ativar gate em main; threshold só pode ser relaxado por revisão explícita |
| R5 | Conflito entre branch protection (PR review required) e operador solo | Baixa | "Include administrators" é o padrão de NFR-REL-002; operador concorda em abrir PR mesmo solo (decisão registrada) |

---

## Questões Abertas

*Nenhuma bloqueante.* As pré-condições operacionais dependem do operador executar passos GitHub/PyPI — não há ambiguidade técnica.
