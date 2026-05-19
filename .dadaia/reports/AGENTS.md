# Report Format Standard — dadaia-workspace

**Rule:** Every file written to this directory must be a valid, self-contained HTML file.
Do not write Markdown. Open any report in a browser to verify it renders correctly.

---

## File naming

```
{YYYY-MM-DDTHHMMSSZ}-{type}.html
{YYYY-MM-DDTHHMMSSZ}-{task_id}-{type}.html
```

Examples:
- `2026-05-15T142030Z-discovery.html`
- `2026-05-15T142030Z-T123-red.html`

---

## Mandatory HTML template

Every report must use this template exactly (swap `{...}` placeholders):

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{Report Title}</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 15px;
    line-height: 1.65;
    color: #1a1a1a;
    background: #fff;
    max-width: 960px;
    margin: 2rem auto;
    padding: 0 1.5rem 4rem;
  }
  h1 { font-size: 1.75rem; border-bottom: 2px solid #333; padding-bottom: .5rem; margin-top: 0; }
  h2 { font-size: 1.3rem; border-bottom: 1px solid #ddd; padding-bottom: .25rem; margin-top: 2.5rem; }
  h3 { font-size: 1.1rem; margin-top: 1.75rem; }
  h4 { font-size: 1rem; margin-top: 1.25rem; }
  a  { color: #0969da; }
  code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 87.5%;
    background: #f6f8fa;
    padding: .15em .4em;
    border-radius: 3px;
  }
  pre {
    background: #f6f8fa;
    border: 1px solid #e4e8ec;
    border-radius: 6px;
    padding: 1rem 1.25rem;
    overflow-x: auto;
  }
  pre code { background: none; padding: 0; font-size: 90%; }
  table { border-collapse: collapse; width: 100%; margin: 1.25rem 0; font-size: .95rem; }
  th, td { border: 1px solid #d0d7de; padding: .45rem .75rem; text-align: left; vertical-align: top; }
  th { background: #f6f8fa; font-weight: 600; }
  tr:nth-child(even) { background: #fafafa; }
  blockquote {
    border-left: 4px solid #d0d7de;
    margin: 1rem 0;
    padding: .5rem 1rem;
    color: #555;
  }
  ul, ol { padding-left: 1.5rem; }
  li { margin: .25rem 0; }
  .meta {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: .75rem 1rem;
    margin-bottom: 2rem;
    font-size: .9rem;
    display: flex;
    flex-wrap: wrap;
    gap: .5rem 2rem;
  }
  .meta span { color: #555; }
  .meta strong { color: #1a1a1a; }
  .badge {
    display: inline-block;
    padding: .15em .5em;
    border-radius: 3px;
    font-size: .8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .04em;
  }
  .badge-critical { background: #ffd7d7; color: #a00; }
  .badge-high     { background: #fff0d0; color: #c05000; }
  .badge-medium   { background: #fffad0; color: #806000; }
  .badge-low      { background: #daffd0; color: #1a5c00; }
  .badge-pass     { background: #daffd0; color: #1a5c00; }
  .badge-fail     { background: #ffd7d7; color: #a00; }
  .badge-pending  { background: #e0eaff; color: #0550ae; }
  .finding { border: 1px solid #e4e8ec; border-radius: 6px; padding: 1rem; margin: 1rem 0; }
  .finding h3 { margin-top: 0; }
</style>
</head>
<body>

<div class="meta">
  <span><strong>Agente:</strong> {agent_name}</span>
  <span><strong>Gerado em:</strong> {YYYY-MM-DDTHHMMSSZ}</span>
  <span><strong>Contexto:</strong> {context}</span>
  <span><strong>Run:</strong> <code>{run_id}</code></span>
</div>

<h1>{Report Title}</h1>

<!-- report sections go here -->

</body>
</html>
```

---

## Required sections by agent role

### product-engineer — discovery report

```html
<h2>Findings</h2>
<!-- bullet list of key findings from spec review and operator interview -->

<h2>Riscos</h2>
<!-- table or list of identified risks -->

<h2>Decisões necessárias</h2>
<!-- open questions that require operator decision before synthesis -->
```

### product-engineer — synthesis (SPEC file)

The synthesis output `specs/features/{topic}/SPEC.md` is a **Markdown spec file**, not an HTML report.
Write it as Markdown following the SDD SPEC template. It must contain the strings `Status` and `Critérios de Aceite`.

### software-architect — architecture reports

```html
<h2>Executive Summary</h2>
<!-- one paragraph: overall health verdict -->

<h2>Findings</h2>
<!-- one .finding div per item, with a severity badge: -->
<div class="finding">
  <h3><span class="badge badge-critical">CRITICAL</span> {title}</h3>
  <p><strong>Location:</strong> <code>file:line</code></p>
  <p><strong>Issue:</strong> ...</p>
  <p><strong>Why it matters:</strong> ...</p>
  <p><strong>Trade-off if fixed:</strong> ...</p>
  <p><strong>Recommendation:</strong> ...</p>
</div>

<h2>Improvement Backlog</h2>
<table>
  <thead><tr><th>#</th><th>Priority</th><th>Item</th><th>Why</th><th>Trade-off</th><th>Effort</th></tr></thead>
  <tbody>
    <tr><td>1</td><td>P1</td><td>...</td><td>...</td><td>...</td><td>S</td></tr>
  </tbody>
</table>
```

For `onboard` reports also include: `<h2>Project Understanding</h2>`, `<h2>Architecture Status</h2>`, `<h2>Gap Analysis</h2>`, `<h2>Recommended Next Steps</h2>`.

For `review` reports also include: `<h2>Stale and Dead Code</h2>`, `<h2>OOP &amp; Design Pattern Audit</h2>`, `<h2>Verdict Rationale</h2>`.

### qa-engineer — red-phase TDD report

```html
<h2>Failing tests</h2>
<!-- list every test that must fail before implementation begins -->
<ul>
  <li><code>test_module::test_name</code> — why this test validates the requirement</li>
</ul>

<h2>Test file locations</h2>
<!-- where the test files were written -->
```

### software-engineer / frontend-engineer — green-phase report

```html
<h2>All tests pass</h2>
<!-- paste the pytest / vitest output showing 0 failures -->
<pre><code>===== X passed in Ys =====</code></pre>

<h2>Implementation summary</h2>
<!-- what was changed and why -->
```

### software-engineer / frontend-engineer — refactor report

```html
<h2>Refactor summary</h2>
<!-- what was improved and the rationale -->

<h2>Test suite after refactor</h2>
<pre><code>===== X passed in Ys =====</code></pre>
```

### devops-engineer — audit report

```html
<h2>Pipeline Inventory</h2>
<!-- table of all CI/CD workflows found -->

<h2>Findings</h2>
<!-- severity-tagged finding blocks (same .finding pattern as software-architect) -->

<h2>Recommendations</h2>
<!-- ordered action list -->
```

### game-developer — implementation report

```html
<h2>Implementation summary</h2>
<!-- feature delivered, design decisions -->

<h2>Playability notes</h2>
<!-- any issues or improvements spotted during testing -->
```

---

## Badges reference

| Class | Use for |
|-------|---------|
| `badge-critical` | Critical findings, blocking issues |
| `badge-high` | High-severity findings |
| `badge-medium` | Medium-severity findings |
| `badge-low` | Low-severity / style findings |
| `badge-pass` | Test pass / deploy success |
| `badge-fail` | Test fail / deploy failure |
| `badge-pending` | Awaiting operator decision |
