---
name: context-injection-role-phase-canon
status: candidate
opened: 2026-07-02
owner: project-manager (curates)
source: operator architectural deep-review 2026-07-02 (lane D — context injection, both layers)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/context_selector.py#ContextSelector" }
    change: "introduce a declarative role->memory-atom default map consumed at Layer-2 prompt assembly (software-architect -> specs/memory/architecture.md, qa-engineer -> specs/memory/quality-assurance.md, product-engineer -> product catalog) so role grounding stops depending on per-fragment luck; immediate fix: the implementation qa-review fragment must inject quality_assurance_atom (spec_review_qa already does, implementation.qa_review does not); thread the active release phase (ACTIVE.md) into SpecContext so selectors and fragments can declare optional phase gates — today NOTHING in either layer is phase-aware"
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/fragments/loader.py#FragmentLoader" }
    change: "fragment/persona coherence doctor: every role appearing in public/lifecycle_fragments/** must resolve to a persona atom (a missing atom silently yields persona=None today); decide the constitution-injection story (the sel_constitution selector exists with ZERO fragment consumers) and support per-input max_context_policy overrides (the policy is fragment-global today)"
  - subject: { kind: code, ref: "dadaia_workspace/hooks/ctx_inject.py#main" }
    change: "Layer-1 injection decision (grill): the bootstrap digest injects tech-stack + catalog tldr only — constitution/architecture/quality-assurance are NEVER injected on Layer 1 and reach agents only via self-pull discipline (step0 skill); either ratify self-pull and make it verifiable (a mechanical audit line in handoffs proving the atoms were read), or add bounded phase-aware digests to the bootstrap"
---

# BACKLOG — Context-injection role/phase canon

**Priority:** HIGH. Operator expectation: injection must be role- and phase-aware on
both agentic layers — constitution/architecture/quality-assurance reaching Layer-1
sessions per lifecycle phase, and every dadaia-workflow step receiving the correct
fragment + persona + model + spec file + role-matching memory atom. The 2026-07-02
review verified what already holds: persona injection is solid on every model-driven
step of every verb; spec_arch_review injects architecture.md (static input);
SPEC/PLAN/TASKS reach the steps that declare them. The gaps are the three intents
above. Mandatory grill before SPEC: the Layer-1 half is a design decision
(self-pull vs injected digest), not a bug fix.
