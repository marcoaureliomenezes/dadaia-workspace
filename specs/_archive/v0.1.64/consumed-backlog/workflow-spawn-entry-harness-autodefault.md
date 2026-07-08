---
name: workflow-spawn-entry-harness-autodefault
status: delivered
delivered_in: v0.1.64
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.58 closure backlog return (FR6 / Ruling F — deferred at release definition)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/core/session_env.py#harness_session_id" }
    change: "auto-default the workflow-spawn entry harness from the entry session: enter codex ⇒ --harness codex, enter pi ⇒ --harness pi, an explicit --harness/--step-harness always wins. Deferred at v0.1.58 (Ruling F) because clean entry-harness detection is incomplete — core/session_env.py resolves only CLAUDE_CODE_SESSION_ID + CODEX_SESSION_ID (there is NO PI session env var), and claude is Layer-1-only so never a valid workflow --harness. Design the PI entry-signal seam (or a codex-only best-effort default) before wiring the auto-default into the lifecycle spawn path; until then the operator passes --harness explicitly."
---

# BACKLOG — Workflow-spawn entry-harness auto-default

**Priority:** MEDIUM. v0.1.58 ("Harness & Projection Distribution") delivered the init-time
half of harness isolation (`dadaia init --harness <set>` + the typed
`core/harness_registry.py`). The **workflow-spawn** half — defaulting the Layer-2 worker
harness from the entry harness so a Codex or PI entry session runs its workflow steps on the
matching worker without an explicit flag — was deliberately **deferred** (FR6 / Ruling F,
operator-overridable) rather than ballooning R10's surface.

The blocker is detection honesty: `core/session_env.py` (the single source of harness-native
session-id env names) carries only `CLAUDE_CODE_SESSION_ID` and `CODEX_SESSION_ID` — **PI has
no session env var**, so "which harness am I entering from" cannot be resolved cleanly for PI
today. And Claude is L1-only (cost bound), so it is never a valid workflow `--harness`. A
correct default needs its own design: either a PI entry-signal seam or an explicit
codex-only best-effort default with a documented PI fallback.

**Override:** the operator may accept a **codex-only best-effort default now** (enter codex ⇒
`--harness codex`; PI + everything else keep the current explicit-flag requirement), rather
than waiting for the full PI detection seam.
