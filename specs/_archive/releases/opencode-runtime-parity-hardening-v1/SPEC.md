# SPEC — opencode-runtime-parity-hardening-v1

**Status:** Aprovado
**Release ID:** opencode-runtime-parity-hardening-v1
**Fase inicial:** SPEC
**Data de abertura:** 2026-05-28
**Owners:** product-engineer (spec), software-engineer-python (Track A code + Track B + Track C tests), ai-engineer (Track A assets + Track C agent edits)

---

## Investigação T-OC-01 — Resultados (2026-05-29, confirmado via `@opencode-ai/plugin` type defs)

Fontes: <https://opencode.ai/docs/plugins/>, <https://opencode.ai/docs/agents/>,
<https://opencode.ai/docs/permissions/>, type defs `@opencode-ai/plugin/dist/index.d.ts`
(via unpkg). Resolve os pré-requisitos bloqueantes de FR-OC-2, FR-OC-3 e FR-OC-4:

1. **`permission:` por-agent — SUPORTADO.** O frontmatter de `.opencode/agent/<name>.md` aceita
   `permission:` como objeto com categorias (`edit`, `bash`, `webfetch`, `task`, `read`, `glob`,
   `grep`, `list`, …) e valores `allow` | `deny` | `ask`. Permissões de agente fazem merge com a
   config global e **têm precedência**. → FR-OC-2 segue o caminho "implementar transform".
   **Tabela de mapeamento (Claude `tools:` → OpenCode `permission:`):** `Edit`/`Write` → `edit`,
   `Bash` → `bash`, `WebFetch` → `webfetch`, `Agent` → `task`. Sem equivalente: `WebSearch`
   (emite comentário `# [opencode-unsupported]: WebSearch`). Categorias read-only (`read`/`glob`/
   `grep`/`list`) ficam no default `allow` do OpenCode — não emitidas. Política: para cada
   categoria mapeada de mutação/exec/dispatch (`edit`, `bash`, `webfetch`, `task`) emite-se
   `allow` se o agente declara a tool Claude correspondente, senão `deny` — preservando o
   boundary de capacidade do agente (honestidade de projeção, Pilar 3).

2. **Evento de hook de tool use — `tool.execute.before` CONFIRMADO.** Assinatura
   `(input, output) => Promise<void>`; `input.tool` é o nome da tool; args mutáveis em
   `output.args`; bloqueio via `throw new Error(...)`. → FR-OC-3 usa este evento. Tools de escrita
   no OpenCode: `write`, `edit`, `patch` (aliases defensivos `write_file`/`edit_file`/`apply_patch`
   cobrem variações de versão). Path do arquivo em `output.args.filePath` (fallback `path`).

3. **`ctx-inject.ts` (`chat.message`) — HOOK VÁLIDO, MAS ASSINATURA DESATUALIZADA.** `chat.message`
   existe nos type defs (`(input, output: { message, parts }) => Promise<void>`, mutar `output`,
   retornar void). O `ctx-inject.ts` atual usa a assinatura antiga `(message) => { return { message } }`
   e **não funciona** em 1.14.x. → FR-OC-4 segue "corrigir": migrar para `(input, output)` mutando
   `output.parts`. `experimental.chat.system.transform` foi descartado por bug conhecido de runtime
   que descarta mutações silenciosamente (issue anomalyco/opencode#17100).

**Atualizações de AC desbloqueadas:** AC-OC-2 segue o ramo "suportado"; AC-OC-3 usa
`tool.execute.before`; AC-OC-4 segue o ramo "corrigir" (assinatura migrada).

---

## Contexto e Motivação

Esta release fecha três lacunas de completude do produto:

1. **OpenCode está parcialmente quebrado** — três agentes falham com `color: yellow/orange/purple`
   (frontmatter inválido no runtime OpenCode 1.14.x). O campo `tools:` já é stripped na projeção
   OpenCode por `_prepare_agent_for_opencode` em `public_assets.py`, mas `color:` não é removido.
   Adicionalmente: o SDD gate não tem equivalente de hook em OpenCode, e `ctx-inject.ts` não foi
   validado contra a documentação oficial do runtime 1.14.x. O comportamento exato de `permission:`
   por-agent no OpenCode precisa ser verificado contra os docs antes de qualquer implementação.

2. **`dadaia reports next` não existe** — o CLI tem `validate` e `lint` mas não tem o subcomando
   de descoberta de próximo handoff esperado, bloqueando o uso de reports como primitivo de
   orquestração.

3. **6 de 21 agents ainda sem `handoff-emitter`** — `qa-engineer`, `devops-engineer`,
   `backend-engineer`, `game-designer`, `game-developer`, `game-tester` não emitem sidecar
   `.handoff.json`, quebrando a cadeia de validação de reports.

O backlog item `context-gate-cross-repo-fix-v1` foi removido do escopo: a inspeção confirmou que
a v3.2 do `sdd-spec-gate.sh` já implementa o fix (linha 99: `# v3.2: derive specs_dir from FPATH,
not primary_context`).

---

## Ordem de execução entre tracks

**Track C deve ser concluído antes dos testes de regressão do Track A (FR-OC-6).** O FR-OC-6
valida propriedades de todos os agentes OpenCode projetados, incluindo os 6 agents migrados em
Track C. Se Track A rodar seus testes antes de Track C estar completo, os 6 novos agents falharão.
AC-AC-2 (`dadaia public doctor [ok]` para todos os 21 agents) é o gate de integração final e deve
ser verificado após Track A e Track C estarem ambos completos.

Tracks A e B são independentes entre si e podem ser desenvolvidos em paralelo.

---

## Escopo

### Track A — OpenCode Runtime Parity Hardening (T-OC-*)

**Superfícies afetadas:** `dadaia_workspace/infrastructure/public_assets.py`, `.opencode/plugins/`

#### FR-OC-1 — Strip de `color:` na projeção OpenCode

O campo `color:` é específico de Claude Code e causa falha de parse no OpenCode 1.14.x. A função
`_prepare_agent_for_opencode` em `public_assets.py` (linha ~388) já strips `tools:` via
`_FRONTMATTER_TOOLS_RE`. O fix consiste em estender essa função adicionando um segundo regex para
o campo escalar `color:`.

**Implementação:**
1. Adicionar constante de regex em `public_assets.py` (junto às existentes na linha ~30):
   ```python
   _FRONTMATTER_COLOR_RE = re.compile(r"^color:[^\n]*\n", re.MULTILINE)
   ```
   Padrão de scalar-field strip, análogo ao `_FRONTMATTER_OPENCODE_MODEL_FIELD_RE` já existente.
2. Chamar `_FRONTMATTER_COLOR_RE.sub("", content)` dentro de `_prepare_agent_for_opencode`,
   após o strip de `tools:`.
3. Adicionar caso de teste à classe `TestPrepareAgentForOpencode` já existente em `tests/`.

O campo `color:` permanece intacto nos agents source e nas projeções Claude Code (painel) e
Codex — apenas a projeção OpenCode é afetada.

#### FR-OC-2 — Verificar e implementar `permission:` na projeção OpenCode

**Pré-requisito de investigação (bloqueante):** Verificar nos docs oficiais do OpenCode 1.14.x se
o campo `permission:` é suportado em arquivos de agente individuais (`.opencode/agents/<name>.md`)
ou apenas no `opencode.json` global. A decisão de implementação depende desta verificação:

- **Se `permission:` é por-agent:** Implementar transform em `_prepare_agent_for_opencode` que
  emite `permission:` com a lista de ferramentas mapeadas. Tools sem equivalente OpenCode devem
  gerar um comentário `# [opencode-unsupported]: <tool-name>` na projeção (honestidade de
  projeção per Pilar 3 da constituição). Tabela de mapeamento mínima a ser definida pelo
  implementer após consulta aos docs:
  `Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Agent` → equivalentes OpenCode.

- **Se `permission:` é somente global:** Nenhum campo por-agent é necessário. O `opencode.json`
  já contém `"permission": "allow"` (linha ~1742 de `public_assets.py`). Documentar como
  comportamento confirmado e remover AC-OC-2 ou reescrevê-lo como "OpenCode não suporta
  `permission:` por-agent — campo não emitido, global `permission: allow` no opencode.json
  permanece como está."

> ⚠️ Enquanto esta investigação não for concluída, AC-OC-2 e ADR-OC-1 permanecem em aberto.
> O implementer deve resolver este ponto antes de qualquer escrita de código para FR-OC-2.

#### FR-OC-3 — SDD gate hook para OpenCode

**Pré-requisito de investigação (bloqueante):** Verificar nos docs oficiais do OpenCode 1.14.x se
o evento `tool.execute.before` existe na API de plugins. O único plugin existente (`ctx-inject.ts`)
usa `chat.message` — o nome do evento de bloqueio de tool use é desconhecido até confirmação
documental. Se `tool.execute.before` não existir, identificar o evento correto (ex: `tool.use`,
`before_tool_use`) antes de implementar.

Após confirmação do evento correto, implementar plugin TypeScript separado
(`.opencode/plugins/sdd-gate.ts`) que:
- Intercepta ferramentas de escrita equivalentes (`write_file`, `edit_file`, `apply_patch`)
- Invoca `.dadaia/scripts/sdd-spec-gate.sh` com o mesmo contrato JSON de stdin
- Bloqueia se o gate retornar `{"decision":"block",...}`
- Fail-open em erros internos do plugin (mesma semântica do gate atual)

> ⚠️ AC-OC-3 é condicionado ao evento correto — o AC deve ser atualizado com o nome verificado
> antes de CLOSURE.

#### FR-OC-4 — Revisão de `ctx-inject.ts` contra documentação oficial

Auditar `ctx-inject.ts` contra a documentação oficial do OpenCode 1.14.x. Verificar:
- Se o evento `chat.message` ainda existe e tem o contrato documentado
- Se existe evento mais adequado para injeção de contexto (ex: `system.message` ou similar)
- Corrigir ou documentar divergências encontradas

Qualquer divergência encontrada deve ser registrada como comentário inline no arquivo
`ctx-inject.ts`, citando a versão OpenCode e a URL do doc relevante. "Documentar sem corrigir"
só é aceitável quando o OpenCode não oferece alternativa — neste caso o comentário deve dizer
explicitamente isso.

#### FR-OC-5 — Universalidade de `.agents/skills/*/SKILL.md`

Verificar que os arquivos em `.agents/skills/*/SKILL.md` permanecem funcionais no OpenCode após
as mudanças de projeção. `dadaia public doctor` com status `[ok]` para todos os entries de tipo
`agents:skills/` é o critério de aceitação.

#### FR-OC-6 — Testes de regressão cross-runtime

Adicionar testes em `tests/` que validam (**executar após Track C concluído**):
- Ausência de `color:` nos agentes projetados para `.opencode/agents/`
- **Presença de `color:` nos agentes projetados para `.claude/agents/`** (parity check — garante
  que o strip OpenCode não afeta Claude Code)
- Presença/ausência de `permission:` nos agentes OpenCode (conforme resultado da investigação
  FR-OC-2)
- Presença do plugin `sdd-gate.ts` em `.opencode/plugins/`
- `dadaia public doctor` retorna `[ok]` para todos os assets após propagação

---

### Track B — `dadaia reports next` CLI (T-RN-*)

**Superfícies afetadas:** `dadaia_workspace/cli/commands/reports.py`,
`dadaia_workspace/features/reports_validation/` (novo módulo ou extensão)

A lógica de negócio de `reports next` deve viver em `dadaia_workspace/features/`, não inline na
CLI, para satisfazer o floor de 80% de cobertura da camada `features/` exigido pela constituição.

#### FR-RN-1 — Subcomando `dadaia reports next`

Implementar `dadaia reports next [--context <ctx>] [--json]` que descobre o próximo agent
esperado dado o estado atual dos reports do workspace.

**Algoritmo (workflow-aware):**

1. Resolve o Spec Context ativo (`primary_context.json` ou `DADAIA_CONTEXT`).
2. Lê `specs/releases/<active-release>/PLAN.md` e extrai a lista ordenada de agents esperados.

   **Contrato de extração do PLAN.md:** O parser busca, em ordem, as seguintes formas de
   declaração de owner (case-insensitive, qualquer posição na linha):
   - `(owner: <agent-name>)` — padrão do backlog/candidates
   - `**Owner:** <agent-name>` — padrão de seção de PLAN
   - `owner: <agent-name>` — forma YAML inline

   A sequência de agents é a ordem de primeira ocorrência de cada nome único no PLAN.md.
   Nomes de agents válidos são os 21 nomes canônicos (ex: `qa-engineer`, `devops-engineer`).

   Se PLAN.md não existir ou não contiver nenhum owner identificável → exit 3 com mensagem:
   `"No agent sequence found in PLAN.md. Ensure PLAN.md declares owners using (owner: <agent>) pattern."`

3. Lê `.dadaia/reports/<context>/<agent>/` para cada agent da sequência — verifica se existe
   pelo menos um `.handoff.json` com `release_id` igual à release ativa.
4. Retorna o primeiro agent da sequência que ainda não emitiu handoff para a release ativa.

**Output padrão (texto):**
```
Next expected agent: qa-engineer
  Release: opencode-runtime-parity-hardening-v1
  Pending since: 2026-05-28 (release open)
  Already completed: software-architect, product-engineer, software-engineer-python
```

**Output `--json`:**
```json
{
  "next_agent": "qa-engineer",
  "release_id": "opencode-runtime-parity-hardening-v1",
  "completed_agents": ["software-architect", "product-engineer", "software-engineer-python"],
  "pending_agents": ["qa-engineer", "devops-engineer"]
}
```

**Edge cases:**
- Nenhuma release ativa → exit 3 com mensagem orientando `dadaia context activate`
- Todos os agents completaram → `next_agent: null`, mensagem "All agents have emitted handoffs for this release."
- PLAN.md sem owners → exit 3 com mensagem de orientação (ver acima)

#### FR-RN-2 — Testes unitários para `reports next`

Cobertura mínima (80% da camada features conforme constituição):
- Sem release ativa → exit 3
- PLAN.md sem owners → exit 3
- Todos completaram → mensagem correta
- Próximo agent identificado corretamente (mock de `.dadaia/reports/`)
- Output `--json` emite JSON válido e parseable

---

### Track C — agent-comms waves 2-7 (T-AC-*)

**Superfícies afetadas:** `dadaia_workspace/public/agents/*.md` (6 agents), propagação via
`dadaia public stage && install`

**Owner:** `ai-engineer` — `dadaia_workspace/public/agents/**` é superfície de write
**exclusiva** de `ai-engineer` (write_allowlist; ver `memory/architecture.html` §path-scope).
O path-scope gate (`sdd-spec-gate.sh` passo 6) bloquearia `product-engineer` nesta superfície.
Testes de regressão (FR-AC-3, em `tests/`) são de `software-engineer-python`. `product-engineer`
permanece owner da spec, não da edição de agentes.

**Nota sobre `<ctx>` no write_allowlist dos game agents:** O gate resolve `<ctx>` em runtime
substituindo pelo `PRIMARY_SLUG` (linha 268 de `sdd-spec-gate.sh`: `glob="${raw_glob//<ctx>/$ctx_val}"`).
O write_allowlist `.dadaia/reports/<ctx>/game-tester/**` é corretamente expandido para
`.dadaia/reports/tauan-games/game-tester/**` (ou o slug do contexto ativo). Sem conflito.

Os 6 agents recebem o tratamento padrão:
1. Adicionar `dadaia-handoff-emitter` à lista `skills:` no frontmatter
2. Adicionar parágrafo "Emitting handoffs" no body do agent invocando a skill
3. Propagar via `dadaia public stage && dadaia public install --target all`
4. Verificar `dadaia public doctor` → todos `[ok]`

**Agents a migrar:**

| Agent | Wave (histórica) | Observação |
|---|---|---|
| `qa-engineer` | 2 | Piloto da wave |
| `devops-engineer` | 3 | — |
| `backend-engineer` | 4 | — |
| `game-designer` | 5 | `<ctx>` no write_allowlist resolvido corretamente pelo gate |
| `game-developer` | 6 | Idem |
| `game-tester` | 7 | Body já contém seção de sidecar-first emission (linhas ~163-174) — adicionar apenas o `skills:` frontmatter e o parágrafo de invocação da skill, sem duplicar a seção existente |

#### FR-AC-1 — Adicionar handoff-emitter aos 6 agents

Para cada agent: adicionar `dadaia-handoff-emitter` em `skills:` frontmatter + parágrafo de
instrução no body. Referência: `data-analyst.md`. Para `game-tester` especificamente, o parágrafo
deve invocar a skill sem repetir o bloco de schema já existente no body.

#### FR-AC-2 — Propagação e validação

`dadaia public stage && dadaia public install --target all` após todas as edições.
`dadaia public doctor` deve retornar `[ok]` para todos os 6 agents nos runtimes suportados.

#### FR-AC-3 — Testes de regressão

Adicionar/atualizar testes que verificam presença de `dadaia-handoff-emitter` no frontmatter dos
6 agents source e nas projeções.

---

## NFRs

- **NFR-1 — Testes verdes:** `poetry run pytest` passa com 100% dos testes existentes + novos
  antes de cada commit de implementação.
- **NFR-2 — Doctor limpo:** `dadaia public doctor` retorna `[ok]` para todos os assets após
  propagação.
- **NFR-3 — Sem regressão de runtime:** mudanças na projeção OpenCode não afetam projeções
  Claude Code ou Codex. Garantido pela arquitetura de pipeline particionada em
  `_install_opencode` / `_install_claude` / `_install_codex`. Verificado por teste explícito
  em FR-OC-6 (parity check de `color:` na projeção Claude Code).
- **NFR-4 — Copilot compatibility:** assets universais (`public/agents/`, `public/skills/`)
  preservam compatibilidade com GitHub Copilot (que reutiliza instruções Claude Code).
- **NFR-5 — Cobertura:** nova lógica de negócio em `features/` mantém floor de 80% exigido
  pela constituição. Baseline de referência: executar `poetry run pytest --cov` antes de
  iniciar o Track B e registrar o valor como baseline no PLAN.md.

---

## ADRs

### ADR-OC-1 — `tools:` já é stripped; `permission:` por-agent requer verificação documental

**Decisão:** O strip de `tools:` em `_prepare_agent_for_opencode` já está implementado e correto.
A decisão sobre emitir `permission:` por-agent está pendente de verificação dos docs OpenCode
1.14.x (ver FR-OC-2). Se `permission:` por-agent não for suportado, ADR-OC-1 é encerrado como
"comportamento já correto — nenhum campo de permissão por-agent é emitido." Se for suportado, o
transform será adicionado em `_prepare_agent_for_opencode` com a tabela de mapeamento definida
pelo implementer após consulta documental. Tools sem equivalente OpenCode geram comentário
`# [opencode-unsupported]: <tool>` para preservar honestidade de projeção (Pilar 3).

**Razão:** Evita implementar comportamento errado para `permission:` sem confirmação do formato
esperado pelo runtime.

### ADR-OC-2 — SDD gate OpenCode = plugin TypeScript separado (não extensão de ctx-inject.ts)

**Decisão:** O SDD gate OpenCode vive em `.opencode/plugins/sdd-gate.ts`, separado de
`ctx-inject.ts`. O nome do evento de intercepção (`tool.execute.before` ou equivalente) deve
ser verificado nos docs antes de implementar.

**Razão:** ctx-inject.ts trata `chat.message` (injeção de contexto); sdd-gate.ts trata eventos
de tool use (bloqueio de escrita). Responsabilidades distintas, separação clara. O nome do
evento ainda é uma hipótese — não um fato estabelecido.

### ADR-RN-1 — reports-next lê PLAN.md para extrair sequência de agents

**Decisão:** A sequência de agents esperados é extraída do PLAN.md da release ativa usando o
contrato de parsing definido em FR-RN-1 (`(owner: <agent>)`, `**Owner:** <agent>`, `owner: <agent>`).

**Razão:** PLAN.md é o artefato mais confiável que declara quem faz o quê na release. TASKS.md
tem markers `[-]/[x]/[ ]` mas não declara owners de forma padronizada nos arquivos históricos
existentes. O contrato de parsing é suficientemente explícito para ser estável.

---

## Out of Scope

- Suporte a um 4º runtime (Gemini CLI, Cursor, Aider) — emenda constitucional per Pilar 3
- `reports-mcp-server` (v3) — diferido para próxima release
- `reports-evaluator` semântico (v4) — diferido
- `reports-ci-gate` — diferido (requer 100% adoção dos 21 agents primeiro; esta release fecha a adoção)
- `reports-hash-mismatch-enforcement` — diferido
- `agents-md-hierarchical-v1` — diferido (avaliar se ainda faz sentido dado TOML approach)
- Conteúdo dos módulos Academy (knowledge basis 01-06) — diferido
- Fail-open residual no gate para repos não-primários — gap documentado, não bloqueante

---

## Critérios de Aceitação da Release

- [ ] AC-OC-1: `dadaia public install --target all` não gera nenhum agente OpenCode com `color:` no frontmatter
- [ ] AC-OC-2: *(FR-OC-2 confirmado: `permission:` por-agent SUPORTADO)* — agentes OpenCode com tools de mutação/exec/dispatch declaradas emitem bloco `permission:` mapeado (`edit`/`bash`/`webfetch`/`task` → `allow`/`deny`); tools sem equivalente geram `# [opencode-unsupported]: <tool>`; `opencode.json` mantém `"permission": "allow"` global
- [ ] AC-OC-3: `.opencode/plugins/sdd-gate.ts` existe e invoca `sdd-spec-gate.sh` via o evento **`tool.execute.before`** (confirmado nos type defs `@opencode-ai/plugin`)
- [ ] AC-OC-4: `ctx-inject.ts` auditado e **corrigido** — `chat.message` é válido mas a assinatura estava desatualizada; migrado para `(input, output)` mutando `output.parts`, com comentário citando version + type-def URL
- [ ] AC-OC-5: `dadaia public doctor` retorna `[ok]` para todos os entries de tipo `agents:skills/` (`.agents/skills/*/SKILL.md` inalterados)
- [ ] AC-RN-1: `dadaia reports next` retorna próximo agent correto dado reports state simulado (testes unitários em FR-RN-2 passam)
- [ ] AC-RN-2: `dadaia reports next --json` emite JSON válido com `next_agent`, `release_id`, `completed_agents`, `pending_agents`
- [ ] AC-AC-1: Todos os 6 agents têm `dadaia-handoff-emitter` em `skills:` na source e nas projeções
- [ ] AC-AC-2: `dadaia public doctor` retorna `[ok]` para todos os 21 agents após propagação *(gate de integração final — verificar após Track A e Track C completos)*
- [ ] AC-ALL: `poetry run pytest` verde (testes existentes + novos); cobertura da camada `features/` ≥ 80% (floor constitucional)
