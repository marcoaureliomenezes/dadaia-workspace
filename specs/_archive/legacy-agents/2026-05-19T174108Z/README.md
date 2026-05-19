# Legacy agents — archive `2026-05-19T174108Z`

Retired by release `agents-r3-v1` on 2026-05-19.

## Files

- `software-engineer.md` — generic Python + Node + tooling persona.

## Reason for retirement

Surface too generic. The legacy persona bundled Python implementation, Node tooling, and
adjacent automation under a single agent. Per operator decision recorded in
`specs/_archive/releases/.../agents-r3-v1/` (when archived) and in the plan
`/home/marco/.claude/plans/i-inspect-the-agents-glistening-sparrow.md`, the surface is
split into two specialists.

## Successor agents

- `dadaia_workspace/public/agents/software-engineer-python.md` — Python lib code, scripts,
  pytest, packaging, Docker, AWS Lambda, FastAPI / Flask.
- `dadaia_workspace/public/agents/software-engineer-node.md` — Node 20 LTS+ server-side
  surface: CLIs, runtimes, npm tooling, agent runtimes (redacted-infra, workflow-tools), API
  adapters. ESM-only; never crosses into browser surfaces (frontend-engineer territory).

The split landed alongside three new specialist additions: `data-engineer`,
`data-analyst`, and `ai-engineer`. Net count: 16 -> 20 personas.

## Status

Read-only archive. New work uses the successor personas.
