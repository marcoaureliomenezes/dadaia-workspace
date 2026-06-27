---
release: v0.1.32
phase: DEFINITION
---

# Active release: v0.1.32 — harden real-worker workflows (coherent worker-output contract)

**Phase: DEFINITION.** Follow-on to v0.1.31. v0.1.31 proved the workflows run on a real
Layer-2 worker but only the *create* path, and only because the extractor *tolerates*
inconsistent real-worker output. v0.1.32 makes the worker-output contract **coherent by
design** (one transport schema in the `schema` field; step-kind-aware output instruction
aligned with the review-only gate; reconciled field name) and proves the **review/verdict
path** live.

- Grill: `specs/releases/v0.1.32/GRILL.md` (`status: Aprovado`), decisions D-1..D-7.
- Picked: bug `lifecycle-prompt-names-two-schemas-confusing-real-workers` (the v0.1.31 C-02
  residual) + the broader prompt/extractor contract drift + a live review-path e2e + codex parity.

**DEFINE-ONLY checkpoint.** SPEC/PLAN/TASKS authored by `product-engineer`; markers stay `[ ]`;
implementation begins only after the operator approves and this phase advances to
IMPLEMENTATION. **No push.** Branch `feature/v0.1.32` stacks on `feature/v0.1.31` (unmerged) →
`feature/v0.1.30` (unmerged).

---

Prior release v0.1.31 (make the dadaia-workflows run on a real Layer-2 worker) is **CLOSED and
ARCHIVED** at `specs/_archive/releases/v0.1.31/`, NOT pushed. v0.1.30 likewise. Ship path
unchanged (re-stamp security APPROVE → push → CI green → PR → squash-merge), sequencing the
three stacked releases.
