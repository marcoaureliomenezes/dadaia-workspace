---
name: dadaia-grill-me
description: >
  Modo de refinamento de backlog — entrevista o operador sobre as SPECs do projeto dadaia Labs
  (ou sobre uma feature específica) até atingir entendimento compartilhado completo.
  Resolve inconsistências, gaps de escopo e decisões em aberto.
  Finaliza gerando um report em .dadaia/reports/<context-name>/product-engineer/<YYYY-MM-DDTHHMMSSZ>-refine-specs.html.
  Use quando o operador mencionar "grill", "refine specs", "revisar backlog" ou "/dadaia-grill-me".
applyTo: "specs/**"
---

# dadaia-grill-me — Refinamento de Specs SDD

## Propósito

Identificar e resolver — antes da implementação — os problemas que destroem specs:

| Tipo de problema | Exemplo real neste projeto |
|---|---|
| **Inconsistência entre specs** | `platform/snapshots` referencia paths de `mnt/` mas `volume-migration` não foi feita ainda |
| **Spec vs implementação** | `opencode/telegram-bot` SEC8 diz socket `:ro` mas o bot precisa de escrita para compose |
| **Pergunta aberta que o código já responde** | "Qual o ID do operador?" — está em `hermes.env` |
| **Nomes divergentes para a mesma coisa** | `TELEGRAM_ALLOWED_USERS` na security spec vs `TELEGRAM_OPERATOR_CHAT_ID` no hermes.env |
| **Sintaxe ambígua** | `{{VAR}}` na instance-templates mas `envsubst` usa `${VAR}` |
| **Dependência não declarada** | snapshots depende de volume-migration; volume-migration não declara isso |
| **Categoria incorreta** | `openclaw/guardrails` chama de "guardrails" mas especifica backups de config |
| **Constitution desatualizada** | constitution.md diz NVIDIA é provider primário; routing-v2 implementou OpenRouter como primário |

**O operador responde apenas o que o código não pode responder.** O modelo faz a inspeção primeiro.

---

## Como Invocar

```
/dadaia-grill-me                       → todo o backlog (14 specs)
/dadaia-grill-me <feature-id>          → uma spec específica + suas dependências
/dadaia-grill-me report                → gera report com Q&A acumulado na sessão
```

---

## Protocolo em 3 Fases

---

### Fase 0 — Inspeção (antes de qualquer pergunta)

**Nunca pergunte o que pode ser descoberto. Inspecione primeiro.**

```bash
# 1. Listar todas as specs e status
grep -r "Status:" specs/ --include="SPEC.md" -l | xargs grep "Status:" | sort

# 2. Verificar estado real dos containers vs o que as specs afirmam
docker compose -f /home/workspace/services/docker-compose.yml ps
docker inspect vps-hermes-1 --format '{{range .Mounts}}{{.Source}}→{{.Destination}} {{end}}'
docker inspect vps-openclaw-1 --format '{{range .Mounts}}{{.Source}}→{{.Destination}} {{end}}'

# 3. Verificar env vars reais vs o que as specs dizem
grep -r "TELEGRAM\|OPENROUTER\|NVIDIA\|HERMES_WRITE" /home/workspace/services/conf/

# 4. Verificar paths que as specs referenciam mas podem não existir
ls /home/workspace/mnt/ 2>/dev/null || echo "mnt/ não existe"
ls /docker/hermes-agent-wqps/data/ 2>/dev/null | head -3
```

Após inspeção, montar internamente uma lista de **achados** por tipo antes de começar a entrevistar:

```
ACHADOS (internos — não mostrar ao operador ainda):
  [INCONSISTÊNCIA] ...
  [DRIFT spec↔código] ...
  [PERGUNTA ABERTA RESPONDÍVEL] → já respondida: <valor>
  [PERGUNTA ABERTA IRRESPONDÍVEL] → precisa do operador
  [DEPENDÊNCIA NÃO DECLARADA] ...
  [NOMENCLATURA DIVERGENTE] ...
  [CONSTITUTION DESATUALIZADA] ...
```

Resolver os "RESPONDÍVEIS" internamente. Só levar ao operador os "IRRESPONDÍVEIS".

---

### Fase 1 — Entrevista Focada em Problemas Reais

**Uma pergunta por vez. Sempre ancorada em specs e arquivos reais.**

Formato obrigatório de cada turno:

```
**Inconsistência/Gap #N:**
📄 Spec(s) envolvida(s): `specs/.../SPEC.md` (seção X) e `specs/.../SPEC.md` (seção Y)
❓ Problema: [descrição precisa do conflito, gap ou ambiguidade]
💡 Minha recomendação: [solução sugerida com justificativa]
→ Como quer resolver isso?
```

**Nunca duas perguntas no mesmo turno.**

**Ordem de prioridade:**

1. **Inconsistências que bloqueiam implementação** — se implementar X com base na spec Y vai gerar retrabalho imediato
2. **Drift spec↔código** — o que foi implementado diverge do que a spec diz; qual prevalece?
3. **Dependências de ordem** — qual feature deve vir antes de qual, e isso está declarado?
4. **Nomenclatura** — o mesmo conceito tem dois nomes; qual padronizar?
5. **Critérios de aceitação irrespondíveis** — FRs sem "como verificar" definido
6. **Constitution desatualizada** — o documento de leis está mentindo sobre o estado atual

**Não pergunte sobre:**
- Preferências estéticas de formatação
- Escolhas de implementação já feitas e funcionando
- Detalhes que o operador claramente não se importa (tudo que pode ser "qualquer coisa razoável")

---

### Fase 2 — Síntese por Spec (no final de cada spec)

```
## Síntese: <feature-id>

**Problema central resolvido:** [1 frase]
**Status pós-refinamento:** Pronta para aprovação | Precisa de edição | Bloqueada por <dependência>

**Mudanças necessárias no SPEC.md:**
  - [ ] [seção] → [o que mudar e por quê]

**Dependências declaradas:** [lista ou "nenhuma nova"]
**ADRs registrados nesta sessão:**
  - [decisão] — razão: [justificativa curta]
```

---

### Fase 3 — Gerar Report

Ao terminar (ou em `/dadaia-grill-me report`), escrever `.dadaia/reports/<context-name>/product-engineer/<YYYY-MM-DDTHHMMSSZ>-refine-specs.html`:

---

## Formato do Report (`.dadaia/reports/<context-name>/product-engineer/<YYYY-MM-DDTHHMMSSZ>-refine-specs.html`)

```markdown
# Refinamento de Specs — dadaia Labs
> Gerado em: <ISO 8601>
> Escopo: <todo o backlog | feature-id>
> Problemas encontrados: <N> | Resolvidos: <M> | Abertos: <P>

---

## Sumário de Problemas

| # | Tipo | Specs envolvidas | Status |
|---|------|-----------------|--------|
| 1 | Inconsistência | platform/snapshots ↔ platform/volume-migration | ✅ Resolvido |
| 2 | Drift spec↔código | opencode/telegram-bot SEC8 | ✅ Resolvido |
| 3 | Constitution desatualizada | constitution.md provider primário | ⚠️ Pendente |
| ... | | | |

---

## Backlog Priorizado (pós-refinamento)

Ordem recomendada com justificativa de dependências:

| Ordem | Feature | Depende de | Razão |
|-------|---------|-----------|-------|
| 1 | hermes/guardrails | — | 1 env var, zero risco, desbloqueia segurança |
| 2 | platform/volume-migration | — | desbloqueia snapshots e instance-templates |
| 3 | platform/snapshots | volume-migration | paths assumem mnt/ já existente |
| ... | | | |

---

## Detalhes por Problema

### Problema #N — <título curto>

**Tipo:** Inconsistência | Drift | Dependência | Nomenclatura | Critério irrespondível | Constitution
**Specs:** `specs/.../SPEC.md` seção X; `specs/.../SPEC.md` seção Y
**Descrição:** [o que está errado, com citação literal do texto problemático]
**Pergunta feita:** [texto da pergunta ao operador]
**Resposta:** [resposta do operador ou "respondida via inspeção: <valor>"]
**Resolução:** [como a spec deve ser atualizada]
**Pendência:** [o que ainda precisa mudar no arquivo — ou "nenhuma"]

---

## Edições Pendentes nas Specs

Lista consolidada de todas as mudanças a fazer:

| Arquivo | Seção | O que mudar |
|---------|-------|-------------|
| `specs/constitution.md` | Stack | Atualizar provider primário para OpenRouter |
| `specs/releases/<release-id>/SPEC.md` | FR1/FR2 | Declarar dependência de volume-migration |
| ... | | |

---

## Próximos Passos

1. Editar os arquivos listados acima (em ordem de dependência)
2. Marcar `[x] Approved` nas specs prontas
3. Criar PLAN.md para specs aprovadas sem PLAN
```

---

## Regras Absolutas

- **Inspecione antes de perguntar** — qualquer dado factual (path, env var, status, ID) deve ser buscado no código ou containers, nunca perguntado ao operador
- **Cite specs literalmente** — toda pergunta deve incluir a seção exata e o texto problemático
- **Uma pergunta por turno** — sem exceção
- **Não sugerir implementação** — output é refinamento de specs, não código
- **Registrar "respondida via inspeção"** — quando resolver algo sem perguntar, documentar no report
- **Não aceitar "depende"** — se o operador diz isso, explore a árvore de decisão até ter uma resposta acionável

---

## Problemas Conhecidos no Backlog Atual (pré-carregados)

Ao iniciar uma sessão sem escopo específico, começar por estes achados já identificados:

1. **constitution.md diz "Provider primário: NVIDIA NIM"** → routing-v2 implementado inverteu a ordem (OpenRouter é primário hoje)
2. **platform/snapshots FR1/FR2** referencia `/home/workspace/mnt/hermes-1/data/` → esses paths só existem após `platform/volume-migration`, que não está declarada como dependência
3. **openclaw/guardrails verificação** usa path `/docker/openclaw-x44i/data/.backups/` → path antigo; se volume-migration for implementada primeiro, esse comando quebra
4. **opencode/telegram-bot SEC8** diz "docker.sock montado `:ro`" → a implementação monta `:rw` (necessário para compose write ops); spec contradiz o código deployado
5. **platform/instance-templates FR2** usa placeholder `{{INSTANCE_NAME}}` → mas FR/NFR diz "via `envsubst` ou `sed`"; `envsubst` usa `${VAR}`, não `{{VAR}}`
6. **openclaw/guardrails vs platform/snapshots** → ambas fazem backups de `openclaw.json`; guardrails: a cada 5 min; snapshots: diário incremental; não há coordenação declarada
7. **hermes/telegram-gateway Open Questions** ainda `[ ]` → "Qual o ID do operador?" já respondível (`hermes.env: TELEGRAM_OPERATOR_CHAT_ID=TELEGRAM_CHAT_ID_REDACTED`); "supervisor já instalado?" → já implementado (supervisord rodando)
8. **security/applications** diz fix aplicado com `TELEGRAM_ALLOWED_USERS=TELEGRAM_CHAT_ID_REDACTED` em `<config-path>/.env` → hermes.env tem `TELEGRAM_OPERATOR_CHAT_ID`; nomes divergem — pode ser variável diferente ou descrição incorreta do fix
9. **openclaw/guardrails** está categorizada como "guardrails" mas especifica backups de config; `hermes/guardrails` especifica restrição de escrita via `HERMES_WRITE_SAFE_ROOT` — categorias com mesmo nome, problemas totalmente diferentes
10. **openclaw/telegram-gateway Open Questions** → trustedProxies IP ainda `[ ]` mas é descobrível: `docker inspect vps-traefik-1 | grep IPAddress`
