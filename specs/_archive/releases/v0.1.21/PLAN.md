# PLAN: v0.1.21 — WS-PI-4: PI Layer-1 Ring-1 SDD-gate extension

**Status:** Aprovado
**Release ID:** v0.1.21

## Approach

Single branch (`feature/pi-operational-v1`). The design is fully determined by the
verified pi v0.79.3 extension API; the extension is a thin TS shim over the existing
Python `pre_gate` (the OpenCode `.ts` plugin is the proven precedent for the TS→Python
delegation pattern).

1. **DEFINITION** — SPEC/PLAN/TASKS; constitution + memory honesty updates (PI gains a
   Layer-1 Ring-1 extension, with the post-trust caveat). Memory writable in DEFINITION.
2. **IMPLEMENTATION** — author `public/pi/extensions/dadaia-sdd-gate.ts`; wire `_PI_DIRS`
   + `settings.json`; `dadaia public stage && install --target pi && doctor`; add the
   Python projection/content + gate-enforcement tests. Keep preflight green.
3. **CLOSURE** — CLOSURE.md, archive, gate ladder (QA + code-review + security), gated
   push, CI watched green, drift re-check.

## Key decisions

- **Delegate, don't duplicate.** The `.ts` calls `python -m dadaia_workspace.hooks.pre_gate`
  (the merged entry: root-whitelist → venv-guard → SDD), so PI gets the full Layer-1
  enforcement the canonical gate provides and policy is never re-derived in TS.
- **Map at the shim.** `write→Write`, `edit→Edit` so the path classifier treats PI writes
  exactly like Claude writes; the Python `WRITE_TOOLS` vocabulary stays stable (no shared
  change). `event.input.path` is the target (verified: both write/edit schemas use `path`).
- **Fail-open.** Only the explicit `{"decision":"block"}` envelope blocks; every error path
  allows — never break a legitimate edit by crashing (matches the gate's own contract).
- **Honest caveat.** The extension is post-trust executable TypeScript; its block is live
  once the operator trusts `.pi/` and pi's `tool_call` hook fires. Offline CI verifies the
  Python decision + the projected artifact; the trusted interactive run is the operator's
  verification step (recipe in CLOSURE), the same upstream seam class as the pi-live test.

## Risk & mitigation

- **Settings extension-path resolution form** is part of the trust-gated upstream seam →
  document the guaranteed `pi --extension .pi/extensions/dadaia-sdd-gate.ts` fallback.
- **Cross-platform** → venv resolution POSIX→Windows→bare python; `node:child_process`
  only; no POSIX-only APIs.
- **Privacy** → the `.ts` carries no operator-local path/secret (post-trust executable);
  `public-privacy` gate + content test enforce it.

## Verification

`dadaia public doctor` (`[ok] public-privacy` + pi extension line) · `dadaia ci preflight`
(green) · `dadaia specs doctor` (0) · projection/content + gate-enforcement tests pass ·
security APPROVE keyed to the pushed tip · CI green · drift re-check clean.
