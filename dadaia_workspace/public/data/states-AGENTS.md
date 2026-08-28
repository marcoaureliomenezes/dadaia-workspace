# .dadaia/states/AGENTS.md — Runtime State

Scope: this file governs `.dadaia/states/**`.

State files are machine-owned JSON records used by dadaia services, hooks, and the panel.
They are not documentation and not an implementation workspace.

## 1. State ownership

| File | Owner |
|---|---|
| `spec_contexts.json` | context lifecycle commands (`dadaia context bind/show/list`) |
| `server_registry.json` | `dadaia server register/list/unregister` |
| other `*.json` | owning feature/service code |

## 2. Rules

- Prefer dadaia CLI commands over manual edits.
- Preserve valid JSON, stable keys, and atomic-write semantics.
- Do not store secrets, tokens, private keys, or credentials.
- Do not hand-edit state to bypass SDD gates, task locks, or context locks.
- If a state schema changes, update migration/doctor logic and tests.

## 3. When manual repair is acceptable

- Only for corrupted local state, after diagnosing the owner and recording what changed in a report.
- Keep the edit minimal; run the owning doctor/command immediately after.

## 4. Validation

```bash
dadaia context show --json
dadaia server list
dadaia public doctor
```
