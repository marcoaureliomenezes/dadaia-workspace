# .dadaia/handoff/AGENTS.md — Handoff Rules

Scope: this file governs only `.dadaia/handoff/**`.

Handoffs are machine-readable coordination records between agents. Reports stay
in `.dadaia/reports/`; handoff JSON stays here.

## File Contract

Write one handoff per completed report or review decision:

```text
.dadaia/handoff/<context>/<YYYY-MM-DDTHHMMSSZ>-<agent>-<slug>.handoff.json
```

Use the canonical schema:

```text
.dadaia/agentic/schemas/handoff-v1.schema.json
```

Set `artifact.path` to the report or artifact being handed off, usually:

```text
.dadaia/reports/<context>/<agent>/<YYYY-MM-DDTHHMMSSZ>-<slug>.html
```

Validate before handing work to another agent:

```bash
dadaia reports validate <handoff-json-path>
```

## Write Rules

- Keep the file concise: status, findings, decisions, and next action only.
- Use stable workspace-relative paths.
- Include only information needed by the next agent.
- Do not store HTML, screenshots, logs, or temporary notes here.
- Do not write handoff JSON under `.dadaia/reports/`.

## Read Rules

Before implementation review, QA, security review, or release closure, read the
latest relevant handoff under:

```text
.dadaia/handoff/<context>/
```

If a required handoff is missing or invalid, stop and request the producing
agent to emit or fix it.
