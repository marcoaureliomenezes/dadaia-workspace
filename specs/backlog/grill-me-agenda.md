# Grill-Me Agenda — Itens Bloqueados

> Criado em: 2026-05-20
> Autor: product-engineer
> Itens abaixo NÃO podem avançar para PLAN sem decisões humanas explícitas.
> Cada sessão é invocada com `/dadaia-grill-me <item-id>`.

---

## Sessão 1 — codex-design-frontend-projection-pilot-v1

**Arquivo de referência:** `specs/backlog/codex-design-frontend-projection-pilot-v1.md`

**Por que bloqueado:** 5 ADRs arquitetônicas não foram fechadas. Sem elas, o PLAN não
pode especificar paths, projeção, ou contratos de runtime. O software-architect confirmou
que todas as 5 são decisões humanas, não técnicas.

**Contexto para atualizar antes de iniciar:**
- Remover referências a "parent of codex-agent-orchestration-parity-v1" (release encerrada)
- Atualizar "16 agents" → 20
- Remover referências a `panel-r4-v1` / `panel-r5-v1` (ambos arquivados)
- Reescrever framing: esta é agora release standalone focada em skills + agent boundaries

**ADRs a fechar nesta sessão:**

### ADR-CX-001 — Runtime-scoped public asset layout

> Onde vivem os assets exclusivos de cada runtime (Codex-only, OpenCode-only)?

Opções em disputa:
- **A:** `dadaia_workspace/public/runtime/<runtime>/` (ex: `public/runtime/codex/`)
- **B:** `dadaia_workspace/public/plugins/` (existente; atualmente projetado só para OpenCode)
- **C:** Convenção de prefixo dentro de `public/skills/` (ex: `skills/codex-*`)

Implicações de A: novo nível de diretório, `_install_codex` precisa ler de path diferente.
Implicações de B: reutilizar pasta; `_install_opencode` precisa filtrar por target.
Implicações de C: sem mudança estrutural, mas naming carregado.

**Pergunta:** Qual layout aprovamos?

---

### ADR-CX-002 — Codex plugin projection format

> O runtime Codex consome plugins de onde, em que formato?

Evidência atual: `.codex/config.toml` tem `[skills] paths = [".agents/skills"]`. Não há
`.codex/plugins/` ou similar. O runtime não está documentado como consumindo plugins além
dos skills paths.

Opções:
- **A:** Usar apenas `[skills] paths` (já documentado) — sem plugins nativos Codex
- **B:** Declarar e provar `.codex/plugins/` como destino válido antes de projetar
- **C:** Usar `[agents.<name>] config_file` (já implementado para personas TOML)

**Pergunta:** Projetar plugins Codex requer prova de consumo primeiro, ou aprovamos sem prova?

---

### ADR-CX-003 — Shared skill vs Codex-only classification

> Como distinguir um skill compartilhado (Claude + Codex) de um adapter Codex-only?

Proposta do software-architect: critério de namespace — `dadaia_workspace/public/skills/<name>/`
= shared; `dadaia_workspace/public/runtime/codex/<name>/` = Codex-only. Doctor valida
que Codex-only nunca vaza para `.claude/skills/`.

**Pergunta:** Aprovamos o critério de namespace como separador oficial?

---

### ADR-CX-004 — Null-regression methodology

> Como garantir que adicionar assets Codex-only não altera `.claude/**` ou `.opencode/**`?

Proposta: teste de snapshot que computa SHA dos diretórios `.claude/` e `.opencode/` antes e
depois de `dadaia public install --target codex`. Qualquer diferença = falha.

**Pergunta:** Snapshot diff é suficiente, ou precisamos de algo mais rigoroso (ex: hash de manifesto gerado pelo doctor)?

---

### ADR-CX-005 — UX/frontend role boundary hardening

> Frontmatter de `design-specialist` e `frontend-engineer` precisam de atualização.
> Quais ferramentas/skills são explicitamente proibidas vs permitidas?

Proposta (design-specialist audit 2026-05-20):
- `design-specialist`: skills OK → `frontend-design`, `ux-ui-review`, `design-reference-research`, `design-report-quality-gate`, `dadaia-handoff-emitter`. PROIBIDO: Edit, Bash, Playwright, geração de raster.
- `frontend-engineer`: skills OK → `dadaia-workspace-spec-navigator`, `dadaia-task-manager`, `dev-server-registry`, `frontend-implementation-quality`, `dadaia-handoff-emitter`. PROIBIDO: ux-ui-review ownership, E2E ownership, specs ownership.

**Pergunta:** Aprovamos estas listas exatas, ou há ajustes?

---

## Sessão 2 — panel-workflow-run-dispatcher

**Arquivo de referência:** `specs/backlog/candidates.md` linha 48

**Por que bloqueado:** O feature request é "Run this workflow" via POST no painel. Sem
decisão de arquitetura, qualquer SPEC vai gerar PLAN inconsistente.

**Decisões a fechar nesta sessão:**

### Q1 — Modelo de execução: sync vs async

O painel é um HTTP server singlethreaded (`BaseHTTPRequestHandler`). Um dispatch para
`ClaudeAgentDispatcher` é bloqueante (pode durar minutos).

Opções:
- **A (sync blocking):** POST aguarda, UI mostra spinner, timeout em 30s. Simples, mas bloqueia o servidor.
- **B (fire-and-forget):** POST enfileira em thread/subprocess, retorna `202 Accepted` + job-id, UI faz polling.
- **C (streaming SSE):** POST abre SSE stream, UI recebe chunks do output do dispatcher.

**Pergunta:** Qual modelo aprovamos?

---

### Q2 — CSRF protection

O painel expõe `do_POST` sem autenticação além do localhost. Um request forjado de
outra aba pode disparar um dispatch.

Opções:
- **A:** Token CSRF por sessão (cookie + header check)
- **B:** Header `Origin: localhost` como gate suficiente
- **C:** Nenhuma proteção (workspace local, operador único)

**Pergunta:** Qual nível de proteção é aceitável?

---

### Q3 — Thread safety do BaseHTTPRequestHandler

O server atual (`handler.py`) não é thread-safe. Se adicionarmos dispatch assíncrono
(opção B ou C acima), múltiplos dispatches concorrentes vão competir pelo mesmo handler.

Decisão binária:
- **A:** Aceitar singlethreaded dispatch (sem concorrência, fila de 1)
- **B:** Migrar para `ThreadingMixIn` antes de implementar o dispatcher

**Pergunta:** A ou B?

---

## Sessão 3 — panel-dark-mode

**Arquivo de referência:** `specs/backlog/candidates.md` linha 49

**Por que bloqueado:** Design-specialist entregou análise completa em 2026-05-20 com
token table, hex values WCAG-compliant para todas as 3 paletas, e recomendação de
toggle. 4 decisões do operador ficaram abertas.

**Decisões a fechar nesta sessão:**

### Q1 — Paleta base do dark mode

Cada uma das 3 paletas (Mint, Sage, Warm) pode ter um dark mode independente, ou pode
haver um único dark mode cross-paleta.

Design-specialist recomendou: dark mode independente por paleta (toggle binário
`data-color-mode="dark"` dentro de cada `data-theme="mint|sage|warm"`).

**Pergunta:** Dark mode independente por paleta (recomendado) ou dark mode único cross-paleta?

---

### Q2 — Persistência do toggle dark/light

Onde persiste a preferência de dark/light entre sessões?

Opções:
- **A:** `localStorage` com chave `dadaia-panel-color-mode` (recomendado pelo design-specialist)
- **B:** Cookie de sessão
- **C:** Sem persistência (sempre inicia em light)

**Pergunta:** localStorage (A) aprovado?

---

### Q3 — Dark mode como substituto ou adicional a system preference

Opções:
- **A:** Toggle manual apenas (botão no painel, ignora `prefers-color-scheme`)
- **B:** Default = `prefers-color-scheme`, override manual disponível
- **C:** Apenas `prefers-color-scheme` (sem toggle manual)

**Pergunta:** Qual comportamento default aprovamos?

---

### Q4 — Escopo da release panel-dark-mode

Este item deve entrar como:
- **A:** Item autônomo em `panel-hardening-v1` junto com CSP e SQLite drop (já resolvidos em `infra-correctness-v1`)
- **B:** Release standalone `panel-dark-mode-v1` após `infra-correctness-v1` CLOSURE
- **C:** Parte de `infra-correctness-v1` (estende o escopo já aprovado)

**Pergunta:** Qual release abriga este item?

---

## Sessão 4 — cli-asset-granular

**Arquivo de referência:** `specs/backlog/candidates.md` linha 29

**Por que bloqueado:** O output shape de `dadaia public list` e a semântica de `--only`
não estão especificados. Implementar sem isso cria API difícil de reverter.

**Decisões a fechar nesta sessão:**

### Q1 — Output shape de `dadaia public list`

Opções:
- **A:** Tabela formatada por tipo (agents, skills, rules, workflows, commands, hooks) — estilo `dadaia public doctor`
- **B:** JSON estruturado (para consumo por scripts)
- **C:** Ambos — `--format table|json` flag

**Pergunta:** Output primário é tabela (A), JSON (B), ou com flag (C)?

---

### Q2 — Semântica de `--only`

`dadaia public install --only rules` significa:
- **A:** Instalar apenas arquivos de tipo "rules" (filtra por categoria)
- **B:** Instalar apenas assets cujo nome contém "rules"
- **C:** Instalar apenas o subdiretório `public/rules/`

Escolha afeta o contrato de `FileSystemPublicAssetManager.install()`.

**Pergunta:** Semântica A (por categoria), B (por nome) ou C (por path)?

---

### Q3 — Escopo desta release

`cli-asset-granular` inclui também `dadaia public list`? Ou é separada de `install --only`?

Opções:
- **A:** Uma release cobre `list` + `install --only` juntos
- **B:** `install --only` primeiro (já em scope de `infra-correctness-v1` como Item 6), `list` como follow-up
- **C:** `list` standalone; `--only` fica para depois

Nota: `infra-correctness-v1` Item 6 já cobre `--repos-only`/`--workspace-only` (escopo de
repo). `--only rules` é dimensão diferente (tipo de asset). Podem coexistir na mesma release.

**Pergunta:** A, B ou C?

---

## Como usar este documento

```
# Para iniciar uma sessão grill-me específica:
/dadaia-grill-me codex-design-frontend-projection-pilot-v1
/dadaia-grill-me panel-workflow-run-dispatcher
/dadaia-grill-me panel-dark-mode
/dadaia-grill-me cli-asset-granular

# Após cada sessão, o product-engineer:
# 1. Registra as decisões como ADRs no arquivo de backlog ou release SPEC
# 2. Atualiza este arquivo marcando as perguntas como [x] fechadas
# 3. Se o item estiver desbloqueado, cria a release
```
