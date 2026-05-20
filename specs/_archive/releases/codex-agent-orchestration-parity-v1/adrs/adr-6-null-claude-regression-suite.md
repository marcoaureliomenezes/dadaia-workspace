# ADR-6 — Null Claude Regression Suite

> **Status:** Aprovado
> **Release:** codex-agent-orchestration-parity-v1
> **Decided:** 2026-05-20 (grill-me session)
> **Decider:** product-engineer + operador
> **Supersedes:** —

---

## Contexto

O non-goal NG1 proíbe qualquer mudança em `.claude/**` durante o trabalho Codex. O risco
real é uma edição acidental em `public_assets.py` ou em outro módulo que, como
efeito colateral, altere a projeção Claude. Sem um guard automatizado, esse drift seria
detectado apenas na review manual.

Uma complicação: esta release inclui FR13 (deleção intencional dos 4 commands de
`dadaia_workspace/public/commands/`), que irá alterar `.claude/commands/`. O baseline
do guard deve ser capturado **após** FR13, não antes — caso contrário, o diff sempre
mostraria a deleção dos commands como falha.

---

## Decisão

### Baseline timing (OQ10 — decidido em grill-me 2026-05-20)

O golden snapshot de `.claude/**` é capturado em **dois momentos distintos**:

1. **Pre-FR13 snapshot** (informativo, não é o guard): estado antes da deleção dos
   commands. Serve como evidência de CLOSURE de que os commands existiam antes.
2. **Post-FR13 snapshot** (guard — este é o AC1 baseline): capturado imediatamente após
   FR13 (deleção + re-projeção), antes de qualquer mudança Codex. Este é o "ponto zero".

### Comando de captura (post-FR13)

```bash
find .claude -type f -print0 | xargs -0 sha256sum | sort > /tmp/pre-codex.txt
```

### Comando de verificação (pós trabalho Codex)

```bash
find .claude -type f -print0 | xargs -0 sha256sum | sort > /tmp/post-codex.txt
diff /tmp/pre-codex.txt /tmp/post-codex.txt
```

Diff vazio = pass. Qualquer linha no diff = falha de regressão Claude.

### Escopo do guard

O guard cobre **todo** `.claude/**`:
- `.claude/agents/` — 20 arquivos de personas
- `.claude/workflows/` — 7 arquivos de workflows
- `.claude/skills/` — skills projetadas
- `.claude/rules/` — rules projetadas
- `.claude/commands/` — vazio pós-FR13 (intencionalmente)
- `.claude/hooks/` — se existir
- `.claude/settings.json`

### Evidência em CLOSURE

Ambos os snapshots (pre-FR13 e post-FR13/pré-Codex) são commitados como evidência no
report de CLOSURE em `.dadaia/reports/dadaia-workspace/product-engineer/<UTC>-closure.html`.
O diff pós-trabalho-Codex vs baseline também é incluído (deve ser vazio).

---

## Consequências

- FR13 é executado **antes** de qualquer outro trabalho de implementação desta release.
- O baseline é capturado imediatamente após FR13 e commitado como artefato da release.
- Qualquer CI job que toque `infrastructure/public_assets.py` deve re-executar o guard
  e produzir diff vazio (AC1).
- Commands ausentes pós-FR13 são o estado esperado — não são reportados como drift.
