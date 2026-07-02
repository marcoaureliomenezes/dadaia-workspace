---
name: consumer-agents-md-fanout-redesign
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: audit 20260701T201136Z-0bcd6c19 (A-7)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/workspace_guardrail.py#_consumer_repos_for_root" }
    change: "redesign consumer-repo AGENTS.md detection: the in-repo .dadaia/agentic/ marker requirement contradicts the repo-cleanliness law, so the fan-out never fires in a compliant workspace; detect Spec Context repos via spec_contexts.json instead; public doctor must flag stale consumer copies instead of [skip]ping them"
---

# BACKLOG — Consumer-repo AGENTS.md fan-out redesign

**Priority:** MEDIUM. v0.1.47 hand-synced `repos/dadaia-workspace/AGENTS.md` once as a
sanctioned exception (header records it); this entry owns the mechanism so consumer
copies refresh automatically and drift is visible.
