---
name: ctx-inject-ignores-session-bind-first-alive-proxy
status: Closed
severity: HIGH
reported: 2026-06-11
surface: hooks/ctx_inject.py context resolution (UserPromptSubmit/SessionStart injection)
session_id: 82c8408f
---

**Symptom:** Context-memory injection is bind-agnostic. `_resolve_context()`
(`dadaia_workspace/hooks/ctx_inject.py:79-92`) resolves `DADAIA_CONTEXT` env →
else the FIRST registry entry whose state is "alive" → else nothing. It never
reads the session record that `dadaia context bind` writes. Consequences:

1. In a workspace with multiple ALIVE contexts, a session bound to context Y is
   injected with the first-ALIVE context X's tech-stack + catalog (wrong-context
   memory bootstrap).
2. Injection fires at the first prompt — before any bind exists — and the
   once-per-session sentinel is then consumed, so a later `bind` never triggers
   (re-)injection. Bind and injection are fully disconnected mechanisms.

**Repro:**
1. Workspace with ≥2 ALIVE contexts (e.g. `dadaia-workspace` first, `portifolio`).
2. Start a session, first prompt → injection carries `dadaia-workspace` memory.
3. `dadaia context bind portifolio` → no re-injection; session continues on
   `dadaia-workspace`'s injected memory while bound to `portifolio`.

**Expected:** Operator-confirmed model (grill 2026-06-11, ADR-G5): binding a
session to a Spec Context is the ONLY trigger for context-memory injection.
Unbound sessions receive the generic dispatcher preflight + list of alive
contexts only. `bind` invalidates the session's injection sentinel so the next
prompt deterministically injects the bound context's memory; re-bind re-injects
the new context. Aliveness must not act as a context-selection proxy for
injection ("being alive or not doesn't influence the context").

**Notes:** Behaved this way since the hook's introduction ("how it must behave
since the beginning" — operator). Fix is scoped as W2 of the backlog epic
`deterministic-lifecycle-kernel-v0114` (also rewrites `workspace-protocol §2`,
whose "context resolves automatically / bind is optional convenience" wording
encodes the wrong model for injection). The first-ALIVE fallback remains valid
only inside the SDD gate's lease-context resolution, which is a different job.

**Resolution (2026-06-12):** Closed by v0.1.14 FR-W2 (strict bind-driven injection: env → session bind record → generic preflight; first-ALIVE fallback deleted from injection; bind invalidates the sentinel) — commit `f94e953` on `feature/v0.1.14`.
