# PLAN — Release v0.1.79 — Panel agentic-layers reorg

**Status:** Aprovado

Order: T-1 RED (flip PANEL_PRIMARY_TABS fixture + DOM-contract expectations + Playwright
labels to the 6-tab truth — fails against the 7-tab implementation) → T-2 implement
render_index reorg + Sessions relocation + CSP hash recompute → T-3 full validation +
ship gates. Gotchas from the entry: CSP hash staleness silently breaks tab activation;
grep gates on new labels; hermetic e2e server (no new server).
