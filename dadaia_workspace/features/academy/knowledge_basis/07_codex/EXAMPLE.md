# Example: Mapping a Codex Surface Change in dadaia

Scenario: the operator says Codex is not behaving like Claude Code for
agent-orchestrated work.

## Step 1: Classify the Complaint

This is not a normal application bug. It touches AI-entity surfaces:

- projected custom agents;
- skills;
- workflow docs;
- hooks;
- Codex Rules;
- config trust boundaries.

The owning role is `ai-engineer` for public AI-surface files and
`software-engineer` for Python projection code and tests.

## Step 2: Read Official Codex Semantics

The relevant docs are:

- AGENTS.md for scoped durable instructions;
- Skills for reusable workflows;
- Hooks for lifecycle commands;
- Rules for command approval policy;
- Subagents for explicit delegation;
- Config for trust boundaries and custom agents.

The critical finding: custom agents can be configured, but Codex only spawns
subagents when explicitly asked.

## Step 3: Compare With dadaia Projection

Check:

```bash
sed -n '1,120p' .codex/config.toml
find .codex/agents -maxdepth 1 -type f | sort
sed -n '1,120p' .codex/hooks.json
sed -n '1,120p' .codex/rules/dadaia-command-policy.rules
dadaia public doctor
```

Interpretation:

- `.codex/agents/*.toml` means roles are spawnable.
- `.codex/workflows/*.workflow.md` means workflow references are visible.
- `.codex/hooks.json` means lifecycle enforcement may run if trusted.
- `.codex/rules/*.rules` must use Codex's documented Starlark Rule shape.
- `dadaia public doctor` tells you whether projection drift is detected, not
  whether Codex will auto-execute an orchestration graph.

## Step 4: Decide the Fix

Use the right primitive:

- Course: teach the operator the true Codex model.
- Skill: give `ai-engineer` operational decision tables.
- Projection code: fix invalid Rules and sandbox boundaries.
- Workflow docs: say "reference-only" unless a real dispatcher executes the graph.
- Hooks: keep SDD/root enforcement mechanical.

Do not fix this by stuffing more prose into root `AGENTS.md`. That increases context
load but does not create automatic delegation.
