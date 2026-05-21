# Design Report Quality Gate

Validates design report completeness before handoff to `frontend-engineer`.

---

## Purpose

Before `design-specialist` emits a design report and its `.handoff.json` sidecar, this skill provides a structured checklist to confirm all required sections exist and are non-empty. An incomplete report blocks `frontend-engineer` from starting implementation. This skill catches missing sections early, in the same session, so that one report covers the full handoff surface.

---

## Required sections checklist

A design report is considered complete only when ALL of the following sections are present and non-empty. "Non-empty" means the section contains at least one concrete finding, token, or observation — not a placeholder or a heading with no body.

| # | Required section | Heading to look for | Pass condition |
|---|---|---|---|
| 1 | Surface context | `## Surface` | Names the surface ID, describes current state (from screenshots if available), and states the scope of the review |
| 2 | A11y findings | `## A11y findings` | Lists at least one WCAG 2.1 AA criterion evaluated; each entry states pass/fail with evidence and fix direction |
| 3 | Visual hierarchy analysis | `## Visual hierarchy findings` | At least one finding or explicit "no issues found" with rationale |
| 4 | Design token spec | `## Design specification` | Contains a token table; all values use named tokens (no raw hex, no arbitrary px values) |
| 5 | ASCII sketches | `## ASCII sketches` | At least one ASCII sketch per new or changed component; sketches must label at least one token |
| 6 | Reference citations | `## References` | At least one citation in the format `- [Title](URL)\n  Relevance: ...` |
| 7 | Handoff notes | `## Handoff notes` | Lists each new/changed component with: component name, props, states, token list, a11y requirements, edge cases |

---

## Protocol

Apply this checklist by reading the draft design report text before invoking `dadaia-handoff-emitter`. Do not run any Bash command or file-editing tool during this check — this is a read-and-assess step only.

For each section in the checklist:

1. Locate the heading in the report text.
2. Confirm the section body is non-empty and meets the pass condition above.
3. Mark it `[PASS]` or `[FAIL: <reason>]`.

After checking all sections:

- If all sections are `[PASS]`: proceed to `dadaia-handoff-emitter`.
- If any section is `[FAIL]`: emit an `[INCOMPLETE]` list before emitting the report. The `[INCOMPLETE]` list must appear at the top of the report's `## Handoff notes` section. Format:

```
[INCOMPLETE] Design report is missing required sections:
- [ ] Section 2 (A11y findings): no WCAG criteria evaluated
- [ ] Section 5 (ASCII sketches): no sketch provided for CardComponent
```

Do NOT emit the `.handoff.json` sidecar until all `[FAIL]` items are resolved and the report is updated.

---

## Additional validation rules

Beyond section existence, flag these specific conditions as `[FAIL]`:

| Condition | Section | Fail message |
|---|---|---|
| Raw hex value found in token table (e.g. `#3B82F6`) | Design token spec | `Raw hex found — replace with named token` |
| Arbitrary px value not referencing a spacing token (e.g. `margin: 14px`) | Design token spec | `Arbitrary px value — replace with --space-N` |
| A11y section present but no contrast ratio evidence | A11y findings | `Contrast ratio not evaluated — add measurement` |
| No reference citations | References | `Zero citations — at least one required` |
| ASCII sketch missing for a new component listed in handoff | ASCII sketches | `No sketch for <ComponentName> listed in handoff` |

---

## Guardrails

- This skill does NOT execute Bash, Edit, or Playwright. It reads the report draft and emits a text checklist only.
- This skill does NOT modify the design report — it only informs `design-specialist` of what to fix.
- This skill does NOT block reading; it only blocks sidecar emission when sections are incomplete.
- This skill applies only to design reports in `.dadaia/reports/<ctx>/design-specialist/`. It is not applicable to other report types.
