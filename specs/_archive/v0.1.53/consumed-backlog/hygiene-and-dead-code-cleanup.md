---
name: hygiene-and-dead-code-cleanup
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: audit 20260701T201136Z-0bcd6c19 (C)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/hooks/sdd_gate.py#main" }
    change: "sweep the audit C dead-code inventory: legacy main() in hooks/sdd_gate.py + hooks/root_whitelist.py (one-release promise, v0.1.14); lease.LEASE_TTL_SECONDS re-export (zero importers); library_workflow_catalog() (test-only consumers); views/_assets.py legacy shim; academy.js dead window.mermaid branch; stale core.js router comments; ADR-1 transitional TODO refresh; relocate .import_linter_cache outside the repo; re-tune the 90s wall-clock perf-test ceiling to a CPU-time or op-count budget"
  - subject: { kind: catalog, ref: "workspace-doctor" }
    change: "repo-hygiene doctor backstop: WARN on repos/*/.dadaia/ directories (the deferred doctor half of subagent-handoff-resolves-dadaia-inside-repo-cwd; the skill-side fix shipped in v0.1.47)"
  - subject: { kind: code, ref: "dadaia_workspace/features/specs/catalog.py#generate_catalog" }
    change: "agent_tier wire-or-remove (v0.1.48 audit F-76, deferred): the frontmatter field is self-pull on all 25 atoms with zero runtime consumers — either wire an inject tier into the ctx-inject digest or remove the field from memory-frontmatter-v1 + atoms; also remove the dead TelemetryService.list_workflows() call at features/telemetry/service.py:445 (aggregator has no such method; workflow ingestion moved to the canonical store) and the unreachable legacy telemetry fallback else-block in panel handler._dispatch_telemetry — api_workflows is always wired by the container, so the fallback can never fire (2026-07-02 review, lane B)"
---

# BACKLOG — Hygiene and dead-code cleanup

**Priority:** LOW. Also owns (security-review LOW, v0.1.47 push checkpoint, CWE-532):
redaction sweep of operator-local `/home/<user>/` paths in ~12 tracked `specs/bugs/**`
files (6 JSONL notes/repro fields + 6 legacy `_archive` .md) and evaluate stripping
`/home/<user>/` in the bug store's `redact()` backstop. Items overlapping `panel-runtime-reliability` (schema.open_connection
factory, panel.token drift-check, kanban CSS) are owned there and cross-referenced.
