# Plan: Release — sdd-release-lifecycle-v1

> **Status:** Aprovado
> **Release ID:** sdd-release-lifecycle-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16

---

## Estratégia

Sete frentes de trabalho sequenciais, com Phase 1 (bootstrap) já completa ao escrever este
PLAN. Phase 2 refatora o agente; 3 atualiza skills e cria templates; 4 evolui o gate; 5
implementa o CLI doctor; 6 migra dadaia-workspace.

A ordem importa: agente e skills referenciam estruturas (releases/, memory.html, doctor)
que precisam existir antes da migração de Phase 6 disparar. Gate v3 e doctor são pré-
condição para que a migração possa ser validada.

## Camadas afetadas

| Camada | Mudança |
|--------|---------|
| `dadaia_workspace/public/agents/` | product-engineer.md reescrito |
| `dadaia_workspace/public/skills/` | 3 skills atualizadas + 1 nova (release-closure) |
| `dadaia_workspace/public/templates/` | 3 templates Jinja2 novos (memory HTML) |
| `dadaia_workspace/cli/commands/` | specs.py novo (subcommand group) |
| `dadaia_workspace/features/` | specs/doctor.py novo |
| `dadaia_workspace/cli/main.py` | wire-up do subcommand specs |
| `.dadaia/scripts/sdd-spec-gate.sh` | v2 → v3 |
| `repos/dadaia-workspace/specs/` | reorganização estrutural completa |
| `tests/unit/features/specs/` | test_doctor.py novo |

## Ordem de execução

1. **Phase 1 — Bootstrap** (concluído com a escrita deste PLAN, TASKS, ACTIVE, backlog
   placeholders e `_archive/releases/.gitkeep`).
2. **Phase 2 — Refactor product-engineer agent**: reescrever canonical + propagar com
   `dadaia public install --target all`.
3. **Phase 3 — Skills release-aware + closure skill + templates**: atualizar 3 skills,
   criar 1 nova, criar 3 templates Jinja2.
4. **Phase 4 — Gate v3**: cirurgia no script bash, adicionar regras de memory HTML,
   archive read-only, log de release-id.
5. **Phase 5 — CLI doctor**: implementar `dadaia specs doctor` em Python + testes pytest.
6. **Phase 6 — Migração dadaia-workspace**: triagem das 23 features + memory HTML
   atomizado em fase CLOSURE.

## Riscos técnicos

- **Dogfood paradox**: durante Phases 2–5 o tooling ainda não está pronto. Bootstrap manual
  da Phase 1 quebra o paradoxo — o scaffold existe antes do tooling reconhecê-lo.
- **Gate v3 falhar fechado em paths que antes eram permitidos**: env `SDD_LEGACY_FEATURES=1`
  durante a release; doctor flip para `0` em Phase 6 final.
- **Templates Jinja2 sem dependency declarada**: adicionar `jinja2` em `pyproject.toml`
  se ausente. Verificar antes de assumir.
- **dadaia public install sobrescrevendo projeções editadas manualmente**: nenhuma
  projeção foi editada manualmente — todas devem vir do canonical.
- **Doctor reportar falsos positivos para a própria meta-release**: phase = IMPLEMENTATION
  até fim de Phase 6; sem CLOSURE.md exigido durante essa janela.

## Plano de validação

Por phase:

- **Phase 2:** `dadaia public stage && dadaia public install --target all` + `dadaia public doctor` → `[ok]`
- **Phase 3:** skills propagadas, navigator carrega meta-release ativa, reviewer flagra legacy
- **Phase 4:** testes bash inline:
  - block em `specs/memory/product.html` com phase ≠ CLOSURE
  - allow em `specs/memory/product.html` com phase = CLOSURE
  - block em `_archive/releases/x/SPEC.md`
  - allow em production path com `[-]` na release ativa
- **Phase 5:** `pytest tests/unit/features/specs/test_doctor.py` + `dadaia specs doctor` no
  próprio workspace retorna 0 errors (warnings esperados durante migração)
- **Phase 6:** `find specs/features -name SPEC.md -not -path '*/_archive/*'` vazio;
  `find specs/_archive/releases -name CLOSURE.md | wc -l` ≥ 7; `dadaia specs doctor`
  retorna 0 warnings de legacy

## Compactação

PLAN abaixo de 300 linhas por escolha — atende ao self-test do limite D5. Detalhe linha-a-
linha de implementação fica nos arquivos canonical das skills/agente/gate/doctor; o PLAN
descreve estratégia e fases, não código.

## Out of scope deste plano

Referência cruzada com SPEC.md, seção "Fora de escopo". Não duplicado aqui.
