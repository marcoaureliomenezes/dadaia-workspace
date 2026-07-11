# SPEC — Release v0.1.79 — Panel agentic-layers reorg

**Status:** Aprovado
**Source:** backlog `20260708-panel-tab-reorg-agentic-layers` (P2, operator-ratified
2026-07-08, re-ratified at consolidation 2026-07-10). The entry carries the full
confirmed target; this SPEC binds it.

## FRs

- **FR1 — 7→6 primary tabs** in `features/panel/views/index.py#render_index`, final
  order: Projects | 1º Agentic Layer | 2º Agentic Layer | Reports | Academy | Servers.
  (1) `tab-subagents` label → "1º Agentic Layer" (id may stay); (2) the standalone
  Sessions tab MERGES into the 1º Agentic Layer tabpanel as a sub-section (the
  `/api/sessions` cost/telemetry dashboard relocates; `tab-sessions` button +
  `section-sessions` panel removed); (3) `tab-workflows` label → "2º Agentic Layer";
  (4) Projects/Reports/Academy/Servers unchanged.
- **FR2 — CSP integrity:** if ANY inline `<script>` changes, recompute the sha256
  allowlist (`_CSP_SCRIPT_HASH_*` in `features/panel/handler.py`); served CSP hashes
  must equal the sha256 of every inline script body.
- **FR3 — API surfaces UNCHANGED:** `/api/sessions`, agent-model-policy,
  workflow-catalog renderers keep their signatures/contracts — UI placement move only.
- **FR4 — Tests:** DOM-contract tests re-pin the 6-tab truth via the single-sourced
  `PANEL_PRIMARY_TABS` fixture (v0.1.75 architecture — one-list change); Playwright
  e2e specs updated to the new labels on the hermetic harness (port 5065); v0.1.59
  semantic-token / one-control-language grep gates pass. No lease/lock label may
  resurrect (v0.1.76 doctrine — panel surfaces are presence-based).

## Acceptance

- Exactly 6 primary tabs in order; zero `tab-sessions`/`section-sessions` remnants;
  the Sessions dashboard renders inside the 1º Agentic Layer tabpanel.
- CSP header hashes verified equal to served inline scripts (test-pinned).
- Full suite + Playwright green; mypy; doctors; per-sha security APPROVE.
