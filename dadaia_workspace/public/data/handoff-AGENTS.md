# .dadaia/handoff/AGENTS.md — Handoff Rules

Scope: this file governs only `.dadaia/handoff/**`.

Handoffs are machine-readable coordination records between agents.
HTML reports live in the repo (`DADAIA.md` §5.2); handoff JSON stays here.

## 1. File contract

Write one handoff per completed report or review decision:

```text
.dadaia/handoff/<context>/<YYYY-MM-DDTHHMMSSZ>-<agent>-<slug>.handoff.json
```

Use the canonical schema:

```text
.dadaia/agentic/schemas/handoff-v1.schema.json
```

Set `artifact.path` to the report or artifact being handed off (report home: `DADAIA.md` §5.2).

Validate before handing work to another agent:

```bash
dadaia reports validate <handoff-json-path>
```

## 2. Write rules

- Emit `schema_version: "handoff-v1.2"`.
- Record in `self_pull.refs` the memory atoms this session actually self-pulled/read.
- Use step-0 atoms plus any deep atom read during the task, as `specs/`-prefixed context-relative paths.
- Never list an atom that was not read — with zero atoms read, the emitter's honest legacy fallback applies.
- Keep the file concise: status, findings, decisions, and next action only.
- Use stable workspace-relative paths.
- Include only information needed by the next agent.
- Do not store HTML, screenshots, logs, or temporary notes here.
- A handoff expires one day after its mtime and `dadaia doctor` reaps it — no importance marker, no pairing with a report.

## 3. Read rules

- Before implementation review, QA, security review, or release closure, read the latest relevant handoff.
- Handoffs live under `.dadaia/handoff/<context>/`.
- If a required handoff is missing or invalid, stop and request the producing agent to emit or fix it.
