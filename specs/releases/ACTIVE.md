---
release: v0.1.31
phase: DEFINITION
---

# Active release: v0.1.31 — make the dadaia-workflows actually run on a real Layer-2 worker

**Phase: DEFINITION.** Bug-driven release. The first real `dadaia lifecycle release define
--harness pi` run (operator demo, 2026-06-27) proved the workflow engine **governs and
dispatches** a Layer-2 worker correctly, but **no real worker run has ever advanced past
step 1**. Two HIGH bugs blocked it; this release fixes both and adds an anti-fake real-worker
e2e so the fake runtime can never again mask a worker-contract gap.

- Grill record: `specs/releases/v0.1.31/GRILL.md` (`status: Aprovado`). Binding decisions
  D-1..D-7 (verdict gate is **review-only**, Option 2; create steps gate on schema-valid
  payload; PI command fix adopted+hardened; mandatory env-gated real-worker e2e).
- Picked set: bugs `pi-headless-command-trailing-dash-breaks-layer2` (HIGH, fix landed
  `c8513fa5`) and `lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate` (HIGH, open).

**DEFINE-ONLY checkpoint.** SPEC/PLAN/TASKS are being authored by `product-engineer`. Every
TASKS marker stays `[ ]`; implementation begins only after the operator approves DEFINITION
and this phase advances to IMPLEMENTATION. **No push** (standing operator constraint).

Branch `feature/v0.1.31` is off `feature/v0.1.30` (unmerged) + the `c8513fa5` PI fix.

---

Prior release v0.1.30 (super release: PI/Codex Layer-2 + workflow system maturation) is
**CLOSED and ARCHIVED** at `specs/_archive/releases/v0.1.30/` (CLOSURE.md), **NOT pushed /
NOT merged** (operator: closure only). Ship path unchanged: re-stamp security APPROVE on the
final HEAD sha, push, watch CI until green (incl. the GH-only `e2e-panel` job), PR →
squash-merge to `main`.

Pre-existing drift (not in scope): `specs/releases/v0.1.23/` remains unarchived on `main`
(an `Aprovado` SPEC with no CLOSURE) — a future cleanup.
