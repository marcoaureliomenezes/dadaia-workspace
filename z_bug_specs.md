# z_bug_specs.md

Atualizado em: 2026-05-08
Escopo: redesign completo da feature Spec Context Project (v3.0) — encerramento de todos os gaps anteriores

## Gaps encerrados nesta rodada

### GAP-001 — RF-ARCH-006 sem `is_selected` (FECHADO)
`is_selected` foi descartado junto com todo o modelo v2.0. O conceito não existe na v3.0.

### GAP-002 — `deactivate` sem parâmetro com múltiplos ativos (FECHADO)
Múltiplos ativos foram descartados. Apenas um contexto pode estar `ativo` por vez. `deactivate` sem parâmetro opera sobre o único contexto ativo — comportamento não-ambíguo.

### GAP-003 — Topologia dos bots (FECHADO)
Claude Code, Opencode e Codex compartilham o mesmo `.claude/commands/` do workspace root. Resolvido em `spec-context-agent-command/SPEC.md v2.0`.

### GAP-004 — Alias `/ctx` (FECHADO como fora de escopo)
Decidido: v2.0 do command distribui apenas o nome canônico `/spec-context`. Alias pode ser adicionado como arquivo separado em versão futura sem necessidade de spec nova.

### GAP-005 — Timeout para ativações lentas (FECHADO como não-aplicável)
Na v3.0 não há clonagem ou cópia de repositórios. `activate` apenas escreve um JSON — operação instantânea. O timeout de materialização não existe mais.

### G3 — CLI sem operações granulares de assets (MANTIDO como baixa prioridade)
CLI granular para assets (`list`, `install --only rules`, etc.) continua fora de escopo da v3.0.
Pode ser abordado em feature separada após aprovação e implementação do Spec Context v3.0.

---

## Gaps abertos

*Nenhum gap bloqueante no momento. Esta versão das specs está pronta para revisão e aprovação.*

---

## Uso deste arquivo

- Este é o registro vivo de gaps remanescentes antes da implementação.
- Adicione entradas aqui somente quando um conflito, buraco ou ambiguidade permanecer sem resolução ao fim de uma revisão.
