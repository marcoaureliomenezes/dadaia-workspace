# .dadaia/handoff/AGENTS.md — Handoff Rules

Scope: this file governs only `.dadaia/handoff/**`.

- Handoffs are machine-readable coordination records between agents; HTML reports: the root `AGENTS.md` (Where things are written).
- A missing or invalid required handoff stops the work: report it to the main thread.
- Handoff-first: a JSON handoff by default; an HTML report only on operator request or when the next hop is human.
- Path shape, emission and ack-on-consume: `dd-handoff-emitter`; a reviewer verdict is not one of these handoffs: `worktrees/AGENTS.md` (Merges, gates, review).
- Validate with `.dadaia/.venv/bin/dadaia reports validate <path>.handoff.json`; an HTML report's integrity rides on its `content_hash`.
- Expiry: the zone table in `.dadaia/AGENTS.md`.
- The main thread deletes a coordination handoff once the agent it names has acted on it.
- Schema: `.dadaia/agentic/schemas/handoff-v1.schema.json` — its `schema_version` enum is the one source.

## 1. Write rules

- Record in `self_pull.refs` the memory atoms this session actually read, as `specs/`-prefixed context-relative paths.
- Keep the file concise: status, findings, decisions, next action; stable workspace-relative paths only.
- HTML, screenshots and logs go to `.dadaia/reports/` or `.dadaia/tmp/`.

## 2. Read rules

- Before a review or a candidate closure, read the newest `.dadaia/handoff/<context>/*.handoff.json` whose `next_handoff.agent` names you.
