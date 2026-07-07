---
release: v0.1.63
phase: IMPLEMENTATION
---

# Active release: v0.1.63 — Plugin Platform Completion

Third of the **defined-and-reviewed queue of four releases** (fixed order
v0.1.61 → 62 → 63 → 64 per Ruling 61-A; CLOSURE follows the same order per
Ruling 61-B — later-closing releases rebase shared memory atoms, never revert):

1. **v0.1.61 — Audit Remediation & Memory Truth** — **CLOSED and ARCHIVED**
   (merged `3965df4c`, PR #116; 41/41 dispositions).
2. **v0.1.62 — Injection Contract & Fan-out Containment** — **CLOSED and
   ARCHIVED** (merged `352969da`, PR #118; HIGH bug
   `reports-sidecar-version-detection-misroutes-future-tokens` resolved).
3. **v0.1.63 — Plugin Platform Completion** (ACTIVE): `dadaia plugin uninstall`
   (ADR-U1..U4: drift-restore, no-op/exit-2, profile-scoped,
   files-first/ledger-last) + the 3+3 named pack skill corpora. **Rebases on
   v0.1.61's landed `cli/commands/plugin.py` + `infrastructure/public_assets.py`
   (PluginStore via composition root) — Ruling 61-A.**
4. **v0.1.64 — Platform Ergonomics & Tiering**: shared golden
   platform-invariance module; entry-harness auto-default + PI Ring-1 pin;
   `tier:`→`dispatch_band:` rename (v61 AC-1 frontmatter cross-check + v62
   AC-6 adoption contract re-run after its W3); fast-tier item REJECTED
   (operator-overridable).

Open bug ledger note: `backlog-doctor-yaml-parse-misdiagnosis` (LOW) +
`e2e-panel-harness-toggle-ci-flake` (LOW) — to be picked/dispositioned before
the queue closes.
