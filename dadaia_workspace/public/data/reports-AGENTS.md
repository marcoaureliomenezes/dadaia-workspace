# .dadaia/reports/AGENTS.md — Report Rules

Scope: this file governs only `.dadaia/reports/**`.

Reports are operational evidence for humans and `dadaia panel`. They must be
small, self-contained, and machine-linkable through handoff JSON in
`.dadaia/handoff/<context>/`.

## File Contract

Write one HTML report per agent run:

```text
.dadaia/reports/<context>/<agent>/<YYYY-MM-DDTHHMMSSZ>-<slug>.html
```

Do not write Markdown reports. Do not store temporary logs here; use
`.dadaia/tmp/`.

## HTML Minimum

Every report must be valid standalone HTML:

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{agent} — {slug}</title>
</head>
<body>
  <header>
    <h1>{Report title}</h1>
    <p><strong>Agent:</strong> {agent}</p>
    <p><strong>Context:</strong> {context}</p>
    <p><strong>Generated:</strong> {YYYY-MM-DDTHHMMSSZ}</p>
  </header>
  <main>
    <!-- report sections -->
  </main>
</body>
</html>
```

Inline CSS is allowed when useful. External assets are allowed only when they
are committed under `.dadaia/reports/<context>/<agent>/` or referenced as
evidence with stable relative paths.

## Required Sections

All reports:

- `Summary` — outcome in one short paragraph.
- `Evidence` — commands, screenshots, file paths, URLs, or citations used.
- `Result` — `pass`, `fail`, `blocked`, or `informational`.
- `Next action` — one concrete next step or `none`.

Implementation reports:

- `Changed files`
- `Validation`
- `Risks`

Review/audit reports:

- `Findings`
- `Severity`
- `Recommendations`

Design/QA reports:

- `Coverage`
- `Screenshots or traces`
- `Open issues`

Spec/refinement reports:

- `Question resolved`
- `Decision needed`
- `Spec impact`

## Findings

Use these severity labels exactly:

```text
CRITICAL
HIGH
MEDIUM
LOW
INFO
```

Each finding must include:

- Location (`file:line`, URL, screenshot path, or artifact path)
- Issue
- Impact
- Recommendation

## Handoff JSON

The machine-readable handoff is written under `.dadaia/handoff/<context>/` and
is consumed by downstream agents and validation tooling. It must identify:

- producing agent
- context
- status/result
- report path
- key findings or outputs
- next recommended agent/action when applicable

Use the `dadaia-handoff-emitter` skill immediately after writing the HTML.

## Panel Compatibility

`dadaia panel` expects stable paths and valid HTML. If a report is renamed,
update the matching handoff JSON under `.dadaia/handoff/<context>/`. Do not move
reports between agents after creation.
