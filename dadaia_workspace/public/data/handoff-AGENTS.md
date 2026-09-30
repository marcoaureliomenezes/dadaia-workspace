# .dadaia/handoff/AGENTS.md — Handoff Rules

Scope: this file governs only `.dadaia/handoff/**`.

- Handoffs are machine-readable coordination records between agents; HTML reports: the root `AGENTS.md` map §4.
- Handoff-first: a JSON handoff by default; an HTML report only on operator request or when the next hop is human.
- Path shape: `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`; emission and ack-on-consume: `dd-handoff-emitter`.
- The one Markdown record here: the grill questionnaire `<UTC>-main-thread-grill-<slug>.md` (`dd-grill-me`), consumed like any handoff once its substance is in ADRs.
- Validate with `.dadaia/.venv/bin/dadaia reports validate <path>.handoff.json`; an HTML report's integrity rides on its `content_hash`.
- Split a report over 30 KB into multiple files behind an `index.html`.
- Expiry is the zone table's (`.dadaia/AGENTS.md`): a handoff one day after its mtime, a report never.
- A consumed coordination handoff is deleted in the same turn — a surviving copy is slop.
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
