---
description: "Switch the active Spec Context Project to a different repository. Use when changing focus between repos or when asked to 'switch context', 'mudar contexto', 'ativar <repo>', 'ver backlog de <repo>'."
---

# dadaia-switch-context

## Goal

Switch the active Spec Context Project so specs from a different repository become the working focus.

## When to Use

- User says "switch to <repo>", "ativar <repo>", "mudar para <repo>", "ver specs de <repo>"
- User wants to see the backlog, tasks, or specs of a different project
- Before starting work on a repo that is not the currently active context

## Workflow

### Step 1 — Discover available contexts

Run:
```bash
dadaia context list
```

Parse the output to identify:
- Current `ativo` context (if any)
- Available contexts and their states (`inativo`, `standby`, `ativo`)

If no contexts exist, stop and tell the user to run `dadaia context create <name> --repo <path>` for each repo in `repos/`.

### Step 2 — Identify the target context

From the user's request, determine which repo/context they want to activate.

If the repo name does not match any context name exactly, compare against the `Primary Repo` column. For example, `/home/workspace/repos/dadaia-agents` matches context name `dadaia-agents`.

If the target is ambiguous, show the list and ask the user to choose by name.

### Step 3 — Deactivate current context (if any)

If there is a currently `ativo` context and it is different from the target, run:
```bash
dadaia context deactivate
```

### Step 4 — Activate the target context

Run:
```bash
dadaia context activate <name>
```

This will:
- Copy the full repo into `.dadaia/contexts/<name>/repos/<slug>/` (first activation only)
- Set `state = ativo` and persist `specs_dir`
- Move the previous active context to `standby`

### Step 5 — Verify the switch

Run:
```bash
dadaia context show --json
```

Check that:
- `context.state` is `"ativo"`
- `context.specs_dir` is not `null`
- `context.specs_dir` + `/constitution.md` exists (use a shell test or file read)

If `specs_dir` is `null`, warn the user that the repo has no `specs/` directory.

### Step 6 — Report and load specs

Tell the user:
```
Context switched to '<name>'.
specs_dir: <path>
```

Then immediately invoke the `dadaia-workspace-spec-navigator` skill to load the specs from the new context into the working session.

## Error Handling

| Situation | Action |
|---|---|
| `dadaia` not found | Tell user to run `pip3 install -e /home/workspace/repos/dadaia-workspace --break-system-packages` |
| Workspace not initialized | Tell user to run `dadaia init` from `/home/workspace` |
| Context not found | Show available contexts and ask user to choose |
| `specs_dir` is null after activate | Warn that repo has no specs/ and skip navigator |

## Notes

- This command never modifies source repos — it only manages materialized copies inside `.dadaia/contexts/`
- A context in `standby` state preserves its materialized copy — reactivation is instant
- A context in `inativo` state requires a full copy on first activation (may take a few seconds for large repos)
