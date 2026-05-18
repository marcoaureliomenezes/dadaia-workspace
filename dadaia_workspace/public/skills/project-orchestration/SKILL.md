---
name: project-orchestration
description: >
  Reference for project-manager and project-auditor agents. Provides agent inventory,
  workflow inventory, dispatch protocol, mediation patterns, escalation triggers,
  and forbidden actions. Load when dispatching agents or arbitrating conflicts.
applyTo: ".dadaia/reports/**"
---

# project-orchestration — Agent Dispatch & Mediation

## TODO

Full content lands in AGT-22 (P3). This stub is sufficient for P2 agent frontmatter
references to resolve via `dadaia public stage && install`.

Outline:
- Agent inventory matrix (16 agents × primary mission + escalation target).
- Workflow inventory matrix (15 workflows × trigger + entry agent).
- Dispatch protocol (Agent tool primitives, input contract injection, output path).
- Decision Authority Matrix template (cross-domain).
- Anti-deadlock protocol (positions documented → synthesis → grill-me).
- Escalation triggers (3+ unresolved conflicts, missing context, unknown workflow).
- Forbidden actions (no file edits outside `.dadaia/reports/`, no nested dispatch).
