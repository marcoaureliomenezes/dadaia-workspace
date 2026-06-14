---
name: agents-md-says-validate-html-reports-with-json-only-validator
status: Open
severity: LOW
reported: 2026-06-12
surface: public/data/AGENTS.md (Reports and Panel section) vs `dadaia reports validate`
session_id: null
---

**Symptom:** The root AGENTS.md projection instructs, right after describing the HTML
report channel: "Validate it: `dadaia reports validate <path>`". Running that against
an HTML report fails with `$root: malformed JSON: Expecting value: line 1 column 1` —
the command's own `--help` says it validates "agent handoff JSON files" only.

**Repro:** write any `.dadaia/reports/<ctx>/<agent>/<ts>-x.html`, then
`dadaia reports validate <that path>` → INVALID, malformed JSON.

**Expected:** Either the validator supports HTML reports, or AGENTS.md scopes the
validate instruction to handoff JSON files only.

**Notes:** Doc-drift between the projected instruction and the CLI contract. Agents
following AGENTS.md literally will mis-validate every HTML report. Fix is a one-line
clarification in `dadaia_workspace/public/data/AGENTS.md` (+ restage/install) or a
`--kind html` mode on the validator.
