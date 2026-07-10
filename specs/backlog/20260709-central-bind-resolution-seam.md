---
name: central-bind-resolution-seam
status: candidate
opened: 2026-07-09
owner: project-manager (curates)
source: "2026-07-09 150-bug recurrence audit — family F2: 8 reports, 5 partial per-command fixes v0.1.47→v0.1.71, still recurring; the resolution law mandates a class-level fix"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/core/specs_resolver.py#resolve_specs_dir" }
    change: "make the persisted-bind resolution a SINGLE seam every resolver-driven CLI verb consumes, and lock it with a contract test. The contract 'a successful `dadaia context bind` is visible to every resolver-driven command' was never fixed centrally: each F2 fix patched one command surface (specs-doctor v0.1.47, bugs-append v0.1.50/55, codex-thread-id v0.1.69, context-show named form v0.1.69, no-arg form v0.1.71) and the family re-reported within days each time. Deliver — grill-corrected 2026-07-09: (1) ONE canonical resolution path consumed by EVERY resolver-driven verb. A partial seam already exists (cli/_specs_resolution.py#resolve_specs_dir_for_cli, consumed by specs/bugs/memory/migrate/newartifacts — ~15 call sites); NOT on it: `context show` (private incumbent-pointer algorithm, cli/commands/context.py:202-260) and the ~12 lifecycle verbs whose --context Typer default is the hardcoded string 'dadaia-workspace' passed as explicit — the bind is never consulted (masked in this self-hosting workspace, wrong-context in any consumer). The SPEC must declare the canonical order (core resolve_bound_context_name today: explicit -> env -> session record -> ancestry marker; decide whether context show's incumbent-pointer folds in or stays show-only) and must scope the lifecycle --context default change (hardcoded default -> unset-resolves-bound) as a user-visible CLI change; (2) a contract test with DYNAMIC enumeration (Typer-app walk over ~25-30 resolver-driven subcommands + per-verb resolution probe) — a static parametrized list cannot catch a future verb — PLUS an import-boundary contract (lint-imports: nothing outside the seam module imports resolve_bound_context_name/_session_context/session records); lifecycle verbs need a read-only probe path or the test stops at the seam boundary; (3) per the resolution law, no further per-command patches are accepted for this family."
---

# BACKLOG — Central bind-resolution seam (recurrence family F2, class-level fix)

**Problem.** 8 reports, 5 partial fixes (v0.1.47→v0.1.71) on the same contract; every fix
patched one command surface and the family kept recurring (median re-report <11h in the
July arc).

**Acceptance.** After a bare `context bind <ctx>`: every resolver-driven verb targets
`<ctx>` (parametrized executed-path test over the full verb list); removing the seam from
any one verb fails the contract test.
