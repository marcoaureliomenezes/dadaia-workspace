---
name: central-bind-resolution-seam
status: candidate
opened: 2026-07-09
owner: project-manager (curates)
source: "2026-07-09 150-bug recurrence audit — family F2: 8 reports, 5 partial per-command fixes v0.1.47→v0.1.71, still recurring; the resolution law mandates a class-level fix"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/core/specs_resolver.py#resolve_specs_dir" }
    change: "make the persisted-bind resolution a SINGLE seam every resolver-driven CLI verb consumes, and lock it with a contract test. The contract 'a successful `dadaia context bind` is visible to every resolver-driven command' was never fixed centrally: each F2 fix patched one command surface (specs-doctor v0.1.47, bugs-append v0.1.50/55, codex-thread-id v0.1.69, context-show named form v0.1.69, no-arg form v0.1.71) and the family re-reported within days each time. Deliver: (1) one resolution path (env -> session record -> incumbent pointer -> ancestry marker) consumed by EVERY resolver-driven verb — no verb-local resolution logic; (2) a parametrized executed-path contract test enumerating the full resolver-driven verb list, asserting each targets the bound context after a bare bind, so a future verb added without the seam fails the contract test; (3) per the resolution law, no further per-command patches are accepted for this family."
---

# BACKLOG — Central bind-resolution seam (recurrence family F2, class-level fix)

**Problem.** 8 reports, 5 partial fixes (v0.1.47→v0.1.71) on the same contract; every fix
patched one command surface and the family kept recurring (median re-report <11h in the
July arc).

**Acceptance.** After a bare `context bind <ctx>`: every resolver-driven verb targets
`<ctx>` (parametrized executed-path test over the full verb list); removing the seam from
any one verb fails the contract test.
