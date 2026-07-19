---
id: audit.audit_report
role: project-auditor
workflow: audit
step: audit_report
static_inputs: [specs/memory/architecture.md]
dynamic_inputs: [open_bugs, backlog_index, architecture_summary]
output_schema: audit-report-v1
max_context_policy: summary
---

# Audit report — scope, scan, and route in one pass

You run a complete audit pass in a single step: state the question this audit
answers, scan the bounded lenses for drift, and route every finding to a
disposition. There is no separate scoping or triage step — own the whole arc,
tight and evidence-led.

## Inputs you reason over

| Input | Use |
|---|---|
| `open_bugs` | Known bugs that may already cover a surface — do not re-file what is tracked. |
| `backlog_index` | Existing backlog items a finding can fold into instead of duplicating. |
| `architecture_summary` | The layer rules and module map your findings are judged against. |

## Context-budget guard

Inspect only the surfaces the audit question requires. Never read a source or
test file wholesale past 300 lines: use `rg`, `wc`, AST queries, focused test
commands, or bounded excerpts of at most 160 lines per call. Do not paste
full source files or unbounded command output back into context. Evidence
cites exact paths and lines, never the whole file.

Run Python/pytest with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`,
and every other tool with its cache disabled or redirected under workspace
`.dadaia/tmp/`. A read-only audit must not dirty the repository it measures.

## Procedure

1. **State the question.** Name the concrete soundness question this pass
   answers. A question-free scan is a fishing trip.
2. **Pick the lenses.** Name the review lenses this question requires (e.g.
   security, architecture, drift, test fidelity) — each lens earns its place
   with evidence, never added for completeness.
3. **Scan each lens.** For every lens, examine its surfaces and record a
   finding for every real divergence from its declared contract. No
   divergence, no finding — an empty `findings` list is a legitimate,
   evidence-backed result.
4. **Route every finding.** Assign each finding exactly one route: `bug`
   (file an additive bug record), `backlog` (fold into or open a backlog
   item), `accepted-risk` (record and accept, no action now), or `resolved`
   (already fixed, evidence cited). Nothing is dropped silently — routing is
   never a deletion.

## Output

Write one `agent-run-result-v1` object whose domain fields have this exact
shape:

```json
{
  "summary": "one sentence",
  "question": "the concrete soundness question this pass answers",
  "lenses": ["architecture"],
  "findings": [
    {
      "id": "stable-kebab-case-id",
      "severity": "HIGH",
      "lens": "architecture",
      "summary": "concrete contract violation",
      "evidence": "path:line or measured behavior"
    }
  ],
  "dispositions": [
    {
      "finding_id": "stable-kebab-case-id",
      "route": "bug",
      "reason": "one sentence justification, evidence-cited"
    }
  ]
}
```

Every finding `id` is unique; every disposition `finding_id` copies one
exactly. Dispose every finding exactly once; never dispose an id that is not
a finding. Severity and lens live only on the finding, never repeated on the
disposition. Empty `lenses`, an undisposed finding, and artifact-only
transport objects fail the Python gate.

Every finding MUST carry exactly the keys `id`, `severity`, `lens`, `summary`,
and `evidence` — no substitutes. Persona-level analysis habits (scorecards,
drift inventories, recommended actions, `memory_claim`/`actual_state` field
names) are INPUT to your reasoning: fold their substance into the finding's
`summary`/`evidence` text, never emit them as replacement keys or as a
competing top-level envelope alongside `question`/`lenses`/`findings`/
`dispositions`. The Python gate validates exactly this shape and rejects
anything else.
