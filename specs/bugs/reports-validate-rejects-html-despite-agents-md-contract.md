---
name: reports-validate-rejects-html-despite-agents-md-contract
status: Open
severity: LOW
reported: 2026-06-11
surface: dadaia reports validate (CLI) vs root AGENTS.md "Reports and Panel" contract
session_id: 82c8408f
---

**Symptom:** `dadaia reports validate <path-to-html-report>` fails with a raw
JSON-parse error instead of validating (or cleanly rejecting) an HTML report:

```text
INVALID  .../index.html
         $root: malformed JSON: Expecting value: line 1 column 1 (char 0)
```

**Repro:**
1. Write any HTML report under `.dadaia/reports/<ctx>/<agent>/<UTC>-<slug>/index.html`.
2. Run `.dadaia/.venv/bin/dadaia reports validate <that path>`.
3. The validator treats the file as handoff JSON and reports `malformed JSON`.

**Expected:** The generated root `AGENTS.md` ("Reports and Panel" section)
instructs, immediately after describing the HTML report path: "Validate it:
`dadaia reports validate <path>`" — i.e. the documented contract is that HTML
reports are validatable by this command. Either the command should support HTML
report validation (structure/size/multi-HTML index rules), or it should emit a
clear "handoff JSON only — HTML reports are validated via their handoff's
content_hash" message, and the AGENTS.md source
(`dadaia_workspace/public/data/AGENTS.md`) should be corrected to point the
command at the handoff JSON instead.

**Notes:** Validating the *handoff* that references the HTML works correctly
(content_hash recomputed, VALID). So integrity coverage exists; the defect is
the contract/docs/UX mismatch plus the misleading `malformed JSON` error for a
non-JSON input. Found while emitting an operator-requested HTML report in a
READ-bound session (additive paths only).
