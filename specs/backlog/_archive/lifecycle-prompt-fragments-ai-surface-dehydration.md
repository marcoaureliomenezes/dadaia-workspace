---
name: lifecycle-prompt-fragments-ai-surface-dehydration
status: delivered
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/workflows/audit.py#AuditWorkflow" }
    change: "WS-A: replace the fail-loud audit stub with a real fragment+gate workflow body (also research + bug_report) — DELIVERED v0.1.30 Wave E (T-30-E-01..04)"
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/workflows/research.py#ResearchWorkflow" }
    change: "WS-A: replace the fail-loud research stub with a real fragment+gate workflow body recording injected fragments + dynamic context — DELIVERED v0.1.30 Wave E (T-30-E-02)"
  - subject: { kind: code, ref: "dadaia_workspace/hooks/ctx_inject.py#main" }
    change: "WS-C: reduce broad session-memory injection so lifecycle prompts get context from the Python dynamic selector; keep ctx-inject to bind/session safety"
---

# EPIC — Lifecycle Prompt Fragments + AI-Surface Dehydration (completion residual)

**ID:** FEAT-LIFECYCLE-PROMPT-FRAGMENTS-01
**Reported:** 2026-06-25 (operator architecture review after the two-layer shift).
**Owner:** project-manager (curates) → product-engineer (release definition after a
MANDATORY grill).
**Status:** DELIVERED — v0.1.24 shipped the fragment engine (library + loader +
dynamic context selector + Python gates), the release-definition workflow body, the panel
dadaia-workflow catalog, prompt observability, and the discrete pi/codex model catalog.
The deferred workflow-body and ctx-inject residuals were delivered in v0.1.30. This entry
is historical and no longer authorizes release scope.
**Priority:** CRITICAL — the named completion vehicle for the harness-scaffolded →
Python-owned two-layer shift.
**Builds on:** the v0.1.24 lifecycle-fragments engine, `lifecycle-foundation` memory.

---

## 1. Delivered residual

v0.1.24 proved the architecture for the **release-definition** workflow: Python owns the
step sequence, fragments carry the per-step context, gates validate transitions. What
remained was to extend that proven pattern to the rest of the lifecycle and to shrink the
projected AI surface the engine is meant to replace. v0.1.30 delivered the remaining
workflow bodies (`audit`, `research`, `bug_report`) as real fragment+gate workflows,
reduced broad ctx-inject dependence, and left `backlog_definition` to its dedicated
backlog item.

## 2. Residual scope

### WS-A — Remaining workflow bodies — DELIVERED
`audit`, `research`, and `bug_report` now run on the fragment+gate pattern: per-step
role, fragment bundle, dynamic context selector inputs, output schema, and Python
transition gates. Bugs stay additive-safe; audits produce disposition-ready output.

> **`backlog_definition` is NOT here — split out (no divergent duplicate).** Its body has a
> dedicated, much more detailed design with hard dedup/conflict/staleness control in
> `backlog-definition-workflow-dedup-conflict-control.md` (FEAT-BACKLOG-DEFINITION-WORKFLOW-01).
> This epic delegates the backlog workflow there.

### WS-B — Deep AGENTS.md / skill dehydration (beyond pointers)
Shrink root + scoped `AGENTS.md` and the mandatory-lifecycle skills/rules to Layer-1
safety + manual-entry pointers, moving the procedural lifecycle content into fragments and
gates. Add an AI-surface doctor check that fails when mandatory lifecycle ritual text is
reintroduced into public agents/rules/skills instead of fragments/gates.

### WS-C — ctx-inject / hook context reduction — DELIVERED
Broad session-memory injection was reduced so lifecycle prompts receive context from the
Python dynamic selector, not from session-bootstrap side effects. `pre_gate` and the git
chokepoints remain safety rails.

### WS-D — Independent fragment versioning (OQ-6)
Decide and, if accepted, implement independent versioning of prompt fragments so an
archived release can replay its exact prompt bundle.

## 3. Non-negotiable design constraints (unchanged)

- **Workflow-first:** no lifecycle phase enforced by "please remember" instructions in
  `AGENTS.md`, a skill, a persona, or a workflow Markdown file.
- **Harness-universal:** every fragment valid for Codex headless, Claude SDK, PI headless,
  or FAKE — no harness-only tool names outside an adapter layer. (OpenCode is removed.)
- **Step-oriented + context-minimal:** inject only what the step needs; prefer catalog
  summaries over full atoms.
- **Cacheable stable prefix:** large stable material assembled once as a byte-identical
  `PromptPrefix`; step fragments are small variable suffixes.
- **Python gates advance state:** the model recommends; Python decides transition legality
  from structured evidence.

## 4. Acceptance criteria (residual)

1. `audit`, `research`, and `bug_report` run as real fragment+gate workflow bodies (no
   fail-loud stub), each recording injected fragments + dynamic context for auditability.
   (`backlog_definition` is owned by FEAT-BACKLOG-DEFINITION-WORKFLOW-01, not this epic.)
2. Root + scoped `AGENTS.md` and the converted skills/rules no longer carry mandatory
   ordered lifecycle behavior; the AI-surface doctor check fails on reintroduction.
3. Broad session memory injection is not required for any lifecycle prompt to work
   (ctx-inject reduced to bind/session safety).
4. OQ-6 resolved: fragment versioning either implemented or explicitly rejected with a
   recorded rationale.
5. Specs/public doctors pass after projection.

## 5. Out of scope

- Re-doing the v0.1.24-delivered fragment engine / loader / selector / release-definition
  body / panel catalog / observability.
- Removing all Layer-1 safety hooks.
- Changing the SDD specs folder format.
- Adding new harnesses; implementing plugin packs.

## 6. Closure note

This item is closed as delivered. Any future fragment-versioning, prompt-budget, or
dehydration refinements need a fresh backlog item with current evidence rather than
reviving this residual.
