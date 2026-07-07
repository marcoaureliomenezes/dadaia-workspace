---
name: selfrepo-agents-md-doubled-header
status: delivered
delivered_in: v0.1.61
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.58 closure backlog return (doc-pass — pre-existing v0.1.47 hand-sync artifact)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/workspace_guardrail.py#_is_self_repo" }
    change: "sanction a one-time hand-sync of repos/dadaia-workspace/AGENTS.md to remove its DOUBLED workspace-law header. The v0.1.47 hand-sync left two stacked headers (the one-time re-sync note block + the canonical short header) on the self-repo root AGENTS.md. Because the consumer fan-out RETAINS the _is_self_repo skip (v0.1.58 FR4 — the source tree keeps its hand-synced copy and install [skip]s self-projection), the fan-out never rewrites this file, so the duplicate persists indefinitely. Fix: collapse to a single canonical header via a sanctioned hand-sync (the file is git-tracked and lib-owned canonical), documented as the successor to the v0.1.47 T-47-32 exception. Not gate-relevant; purely a doc-hygiene pass."
---

# BACKLOG — Self-repo AGENTS.md doubled header (doc-pass)

**Priority:** LOW (doc-pass). `repos/dadaia-workspace/AGENTS.md` (the self-repo root) carries a
**doubled** workspace-law header — the v0.1.47 one-time hand-sync note stacked above the
canonical short header (lines 1–7 + 9–12). This is a pre-existing v0.1.47 hand-sync artifact,
surfaced (not introduced) during the v0.1.58 (R10) consumer fan-out redesign.

The redesigned fan-out RETAINS the `_is_self_repo` skip (the source tree deliberately keeps its
hand-synced `AGENTS.md`, and `dadaia public install` `[skip]`s self-projection), so the fan-out
will never auto-rewrite this file — the duplicate needs a **sanctioned hand-sync** to collapse
to a single canonical header. The file is git-tracked and lib-owned canonical; this is
doc-hygiene only, not a gate or behaviour issue.

**Anchor:** the `_is_self_repo` skip in `workspace_guardrail.py` (why the file is never
auto-fixed) + `repos/dadaia-workspace/AGENTS.md` (the doubled-header target).
