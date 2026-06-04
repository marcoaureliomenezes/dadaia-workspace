# PLAN: v0.1.5 — session-bind and codex-orchestration bug fix

**Status:** Aprovado
**Release ID:** v0.1.5
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Strategy

Fix the reported bugs as one patch release because they share the same product
truth problem: runtime behavior and projected instructions must not overclaim
what the system actually does.

The default Codex orchestration decision is manual/reference-only unless a
supported runtime integration point is found during T-BUG-04. The release should
not invent subprocess-based spawning that Codex cannot support.

## 2. Layers affected

| Layer | What changes |
|-------|--------------|
| `dadaia_workspace/cli/commands/` | Context help and specs/memory/orchestration command guidance |
| `dadaia_workspace/features/spec_context/` | Session-bound context resolution surfaces if needed |
| `dadaia_workspace/features/specs/` | Doctor context resolution and message text |
| `dadaia_workspace/core/` | Remove or quarantine primary-context protocols if unused |
| `dadaia_workspace/infrastructure/` | Remove/quarantine primary-context stores; fix Codex dispatcher capabilities |
| `dadaia_workspace/public/` | Agent/skill/rule/data wording and gate script terminology |
| `specs/memory/` | Closure-only product truth updates |
| `tests/` | Regression coverage for both bugs |

## 3. Execution order

```
T-BUG-01 → T-BUG-02 → T-BUG-03
                  ↘
                    T-BUG-04 → T-BUG-05 → T-BUG-06 → T-BUG-07
```

## 4. Technical risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legacy migration cleanup still needs primary strings | Medium | Allow only explicit deletion/migration code and assert exceptions in tests |
| Doctor context resolution touches several CLI paths | Medium | Add focused CLI tests before broad text cleanup |
| Codex real spawning is unsupported | High | Prefer manual/reference-only mode and make capabilities truthful |
| Public projection drift after text changes | Medium | Run the full asset chain in T-BUG-07 |

## 5. Implementation notes

### Session-bound context cleanup

Treat `DADAIA_CONTEXT` and `DADAIA_SESSION_ID` as the active runtime contract.
Commands that need specs must resolve from the bound session/context or accept an
explicit `--specs-dir`. Error messages must mention `dadaia context bind`, not
removed verbs.

`primary_context` strings are allowed only in migration/deletion code paths and
tests that prove legacy files are removed or ignored.

### Codex orchestration

Use manual/reference-only Codex orchestration unless a supported Codex runtime
API exists in the local tool surface. For manual mode:

- `CodexAgentDispatcher.dispatch()` may continue writing invocation files.
- `dispatch_parallel()` must not claim parallel runtime execution.
- Capabilities and projected text must describe manual handoff behavior.
- Public doctor may report Codex workflows/orchestration as reference-only or
  partial, not green parity.

## 6. Validation plan

Run these commands before closure:

```bash
rg -n "primary_context|is_primary|context promote|context activate" \
  dadaia_workspace/public dadaia_workspace/cli dadaia_workspace/core \
  dadaia_workspace/infrastructure specs/memory

rg -n "Agent tool|supports_parallel|CodexAgentDispatcher|manual/reference-only" \
  dadaia_workspace/public dadaia_workspace/infrastructure specs/memory

source /home/marco/workspace/dadaia/.dadaia/.venv/bin/activate
poetry run pytest -q -p no:cacheprovider -m "unit and not slow" tests/unit
poetry run pytest -q -p no:cacheprovider tests/unit/features/specs/

DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia public stage
DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia public install --target all --force
DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia public doctor
DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia specs doctor
```
