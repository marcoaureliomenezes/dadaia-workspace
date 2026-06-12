---
name: agents-md-instructs-html-report-validation-unsupported
status: Open
severity: LOW
reported: 2026-06-12
session_id: null
surface: dadaia reports validate / public AGENTS.md (Reports and Panel section)
---

**Symptom:** The projected root `AGENTS.md` ("Reports and Panel" section, generated
from `dadaia_workspace/public/data/AGENTS.md`) instructs, immediately after the HTML
report path contract: "Validate it: `dadaia reports validate <path>`". Running that
command on an HTML report fails: `INVALID … $root: malformed JSON: Expecting value:
line 1 column 1 (char 0)`.

**Repro:** Write any HTML report under `.dadaia/reports/<ctx>/<agent>/`, then run
`.dadaia/.venv/bin/dadaia reports validate <that .html path>`.

**Expected:** Either (a) `reports validate` supports HTML report artifacts (at minimum
existence/size/path-contract checks), or (b) the AGENTS.md source stops instructing
HTML validation via this command — its own `--help` states it validates "agent handoff
JSON files" only (`*.handoff.json`). Doc and tool contract must agree.

**Notes:** Reproduced 2026-06-12 on the live self-hosting workspace (library at
`repos/dadaia-workspace/`). The JSON-parse error message is also misleading for `.html`
input — an extension guard with an actionable message would suffice. No operator-local
paths/secrets included.
