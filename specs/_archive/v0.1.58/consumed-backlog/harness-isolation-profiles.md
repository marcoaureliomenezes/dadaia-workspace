---
name: harness-isolation-profiles
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: operator /goal directive 2026-07-01 (grill v0.1.47 D-7/D-8 code half)
intents:
  - subject: { kind: cli, ref: "init" }
    change: "dadaia init --harness <set> profiles: scaffold only the chosen harness projections (claude-only / codex-only / pi-only / any combination), including hook registration per chosen harness"
  - subject: { kind: code, ref: "dadaia_workspace/core/harness_models.py#harnesses" }
    change: "centralize harness identity in one core registry owning the harness names + Layer-1/Layer-2 capability typing (L1 entry = {claude, codex, pi}; L2 workers = {codex, pi}; claude never L2), consumed everywhere: replace the 61+ scattered 'claude'/'codex'/'pi' string literals across lifecycle/panel/telemetry/workflows and the prose-only layer distinction with typed lookups (2026-07-02 review, lane A)"
---

# BACKLOG — Harness isolation profiles

**Priority:** MEDIUM. Isolation is documented as a first-class concept in the
`memory/product/harness/` atoms (v0.1.47); this entry makes it mechanical at init time
and at workflow-spawn time. The workflow-spawn half (entry-harness auto-default:
enter codex => --harness codex, enter pi => --harness pi, explicit flag wins) is
body-owned scope; its code surface is decided at release definition.

**Acceptance bar (operator 2026-07-02):** each profile ships with a sandboxed E2E that
scaffolds via the real CLI and asserts the EXACT default structure for that harness —
claude-only (`.claude/` + hooks in settings, no `.codex/`/`.pi/`), codex-only
(`.codex/` + `.dadaia/hooks/codex-*` wrappers), pi-only (`.pi/` post-trust projection),
and the all-harness default — extending the existing all-harness public-pipeline E2E
(`tests/e2e/features/test_public_pipeline.py`) rather than duplicating it.
