# Tasks: Universal Agentic Assets

> **Status:** Aprovado
> **PLAN:** `specs/features/universal-agentic-assets/PLAN.md`
> **Data:** 2026-05-09

---

## Checklist de Implementação

- [ ] T01: Criar modelo/estrutura de manifest para `.dadaia/agentic/manifest.json`.
- [ ] T02: Implementar `dadaia public stage` copiando `dadaia_workspace/public/` para `.dadaia/agentic/`.
- [ ] T03: Calcular hashes por asset e registrar `schema_version`, `package_version` e `generated_at`.
- [ ] T04: Ajustar `dadaia public install --target all|claude|codex|opencode|agents [--force]`.
- [ ] T05: Fazer `install` gerar staging automaticamente quando `.dadaia/agentic/` estiver ausente.
- [ ] T06: Projetar skills universais em `.agents/skills/`.
- [ ] T07: Projetar Claude Code em `.claude/agents/`, `.claude/commands/`, `.claude/skills/`, `.claude/settings.json`.
- [ ] T08: Projetar Codex em `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/` e `.agents/skills/`.
- [ ] T09: Projetar OpenCode em `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/` e `opencode.json`, sem hook parity.
- [ ] T10: Criar/atualizar `AGENTS.md` a partir do template universal staged.
- [ ] T11: Preservar arquivos existentes quando `--force` não for usado.
- [ ] T12: Implementar `dadaia public doctor` com status `ok`, `missing`, `drift`, `unsupported`.
- [ ] T13: Ajustar `dadaia init` para criar `.dadaia/agentic/`, `.agents/skills/`, `.codex/`, `.opencode/` e `.claude/`.
- [ ] T14: Cobrir fresh workspace scaffold em testes.
- [ ] T15: Cobrir staging mirror de `dadaia_workspace/public/`.
- [ ] T16: Cobrir instalação de universal skills em `.agents/skills/`.
- [ ] T17: Cobrir projeções Claude, OpenCode e Codex sem falsa paridade.
- [ ] T18: Cobrir detecção de drift em asset projetado.
- [ ] T19: Cobrir no-overwrite sem `--force` e overwrite com `--force`.
- [ ] T20: Validar com CLI real:

```bash
python -m pip install -e .
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

---

## Critério de Conclusão

A feature só está concluída quando todos os testes passarem e `dadaia public doctor` reportar `ok` para assets suportados, com `unsupported` apenas para capacidades realmente ausentes no runtime.
