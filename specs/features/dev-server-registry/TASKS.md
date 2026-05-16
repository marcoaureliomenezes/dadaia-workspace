# TASKS: dev-server-registry

> **Status:** Em revisão
> **Versão:** 0.1
> **Referência:** `specs/features/dev-server-registry/PLAN.md`

## Convenção de estado

| Marcador | Estado | Semântica |
|---|---|---|
| `[ ]` | OPEN | Não iniciada |
| `[-]` | IN PROGRESS | Agente está trabalhando — não pegar sem desmarcar a anterior |
| `[x]` | DONE | Implementada, verificada, commitada |

---

## Task 1 — Domain Models and Exceptions

**Files:**
- Create: `dadaia_workspace/core/models/server_registry.py`
- Modify: `dadaia_workspace/core/exceptions.py`

- [x] Step 1.1: Create `dadaia_workspace/core/models/server_registry.py`
- [x] Step 1.2: Add exceptions to `dadaia_workspace/core/exceptions.py`
- [x] Step 1.3: Verify import
- [x] Step 1.4: Commit

---

## Task 2 — Protocols

- [x] Step 2.1: Create `dadaia_workspace/core/protocols/server_registry_store.py`
- [x] Step 2.2: Create `dadaia_workspace/core/protocols/process_probe.py`
- [x] Step 2.3: Verify import
- [x] Step 2.4: Commit

---

## Task 3 — Fakes

- [x] Step 3.1: Add `FakeServerRegistryStore` and `FakeProcessProbe` to `tests/fakes.py`
- [x] Step 3.2: Verify fakes import cleanly
- [x] Step 3.3: Commit

---

## Task 4 — Infrastructure Store + Unit Tests (TDD)

- [-] Step 4.1: Write failing tests first
- [ ] Step 4.2: Run tests — verify they all fail
- [ ] Step 4.3: Implement `dadaia_workspace/infrastructure/json_server_registry_store.py`
- [ ] Step 4.4: Run tests — verify they all pass
- [ ] Step 4.5: Commit

---

## Task 5 — Service + Unit Tests (TDD)

- [ ] Step 5.1: Create empty `__init__.py`
- [ ] Step 5.2: Write failing service tests
- [ ] Step 5.3: Run tests — verify they fail
- [ ] Step 5.4: Implement `dadaia_workspace/features/server_registry/service.py`
- [ ] Step 5.5: Run tests — verify they all pass
- [ ] Step 5.6: Commit

---

## Task 6 — Dashboard + Unit Tests (TDD)

- [ ] Step 6.1: Write failing dashboard tests
- [ ] Step 6.2: Run tests — verify they fail
- [ ] Step 6.3: Implement `dadaia_workspace/features/server_registry/dashboard.py`
- [ ] Step 6.4: Run tests — verify they all pass
- [ ] Step 6.5: Commit

---

## Task 7 — Workspace Init Update + Tests

- [ ] Step 7.1: Write the failing test
- [ ] Step 7.2: Run — verify it fails
- [ ] Step 7.3: Update `dadaia_workspace/features/workspace/service.py`
- [ ] Step 7.4: Run — verify it passes
- [ ] Step 7.5: Commit

---

## Task 8 — Container Wiring

- [ ] Step 8.1: Add `build_server_registry_service()` to `container.py`
- [ ] Step 8.2: Verify import
- [ ] Step 8.3: Commit

---

## Task 9 — CLI Commands

- [ ] Step 9.1: Create `dadaia_workspace/cli/commands/server.py`
- [ ] Step 9.2: Register the sub-app in `dadaia_workspace/cli/main.py`
- [ ] Step 9.3: Smoke-test CLI
- [ ] Step 9.4: Commit

---

## Task 10 — Integration Tests

- [ ] Step 10.1: Write integration tests
- [ ] Step 10.2: Run integration tests
- [ ] Step 10.3: Commit

---

## Task 11 — E2E Acceptance Tests

- [ ] Step 11.1: Write E2E tests (one per user story)
- [ ] Step 11.2: Run E2E tests
- [ ] Step 11.3: Commit

---

## Task 12 — Skill File

- [ ] Step 12.1: Create skill directory and file
- [ ] Step 12.2: Run the full test suite including E2E skill test
- [ ] Step 12.3: Run type and lint checks
- [ ] Step 12.4: Commit skill + full suite

---

## Task 13 — Final Verification

- [ ] Step 13.1: Run full test suite
- [ ] Step 13.2: Smoke-test CLI end-to-end in a real workspace
- [ ] Step 13.3: Propagate skill to runtime projections
- [ ] Step 13.4: Final commit
