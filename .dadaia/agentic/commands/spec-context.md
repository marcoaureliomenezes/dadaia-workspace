# /spec-context — Spec Context Project switcher

Use this command to list Spec Context Projects and switch the active context.

## Usage

- `/spec-context` — list all contexts and show the currently active one
- `/spec-context <name>` — activate the named context (or confirm it is already active)

## Workflow

### No argument

1. Run `dadaia context list` to list all registered contexts with their state and repo slug.
2. Run `dadaia context show --json` to identify the currently active context.
3. Display the list and highlight the active context. If none is active, say so explicitly and suggest `dadaia context activate <name>`.

### With `<name>`

1. Run `dadaia context list` to resolve the current state of the named context.
2. If the context does not exist: report `Context '<name>' not found` and list available contexts.
3. If the context is already `ativo`: confirm it is already active. Do not change state.
4. If the context is `inativo`: run `dadaia context activate <name>`.
   - On success: report the new active context and its `specs_dir`.
   - On failure: report the exact error from `dadaia`. Do not leave the workspace in an inconsistent state.

## Rules

- Never read state files (`primary_context.json`, `spec_contexts.json`) directly. Use the `dadaia` CLI exclusively.
- `dadaia context show --json` is the authoritative source for the active context state.
- Always show the `dadaia` command being executed so the operator knows what ran.
- Do not create, delete, or add-repo via this command — those require the terminal directly.
- This command operates on the global context (`primary_context.json` / `spec_contexts.json`). For per-session isolation, the operator must start the bot with `DADAIA_CONTEXT=<name>` in the environment.
