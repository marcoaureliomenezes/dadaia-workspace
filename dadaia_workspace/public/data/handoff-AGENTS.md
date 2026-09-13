# .dadaia/handoff/AGENTS.md — Handoff Rules

Scope: this file governs only `.dadaia/handoff/**`.

- Handoffs are machine-readable coordination records between agents; HTML reports live in the repo (`DADAIA.md` §5.2).
- Emission, path shape, validation and ack-on-consume: `dd-handoff-emitter`.
- Schema: `.dadaia/agentic/schemas/handoff-v1.schema.json` — its `schema_version` enum is the one source.

## 1. Write rules

- Record in `self_pull.refs` the memory atoms this session actually read, as `specs/`-prefixed context-relative paths.
- Never list an atom that was not read.
- Keep the file concise: status, findings, decisions, next action; stable workspace-relative paths only.
- Never store HTML, screenshots, logs or temporary notes here.

## 2. Read rules

- Before implementation review, QA, security review or release closure, read the latest relevant handoff.
- Handoffs live under `.dadaia/handoff/<context>/`.
- A missing or invalid required handoff stops the work: ask the producing agent to emit or fix it.
