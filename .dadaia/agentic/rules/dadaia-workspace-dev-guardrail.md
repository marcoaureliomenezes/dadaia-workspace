# dadaia-workspace-dev-guardrail

This rule is always active in workspaces where dadaia-workspace is installed.

## Prohibited

- NEVER directly edit a lib-originated file in `.agents/`, `.claude/`, `.codex/`, or `.opencode/`
- NEVER delete a lib-originated projection without running `dadaia public install` after

A file is lib-originated if its path appears in `.dadaia/agentic/manifest.json`. Files with no counterpart in that manifest are project-specific and may be edited freely.

## Correct workflow for changes to lib assets

1. Edit the source in `dadaia_workspace/public/<type>/<file>` (inside the dadaia-workspace repo)
2. Run `dadaia public stage && dadaia public install --target all` to propagate
3. Run `dadaia public doctor` to verify — all entries must be `[ok]`

To force-repair drift: `dadaia public install --target all --force`
