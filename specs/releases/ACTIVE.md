---
release: v0.1.66
phase: CLOSURE
---

# Active release: v0.1.66 — Layer-2 Worker Path Remediation

Defined from 7 registered bugs (`specs/bugs/20260708T15Z-00.jsonl`, all open,
5 HIGH + 2 MEDIUM) surfaced by a remote user blocked running `dd-chain-capture
v0.2.0` through `dadaia lifecycle pipeline` on both the `pi` and `codex`
Layer-2 worker paths. Intake: `specs/backlog/remote-bugs/*.md` (5 reports).
Mandatory `dadaia-grill-me` session completed; refinement report at
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-08T153000Z-refine-v0166.html`.

**Prior release:** v0.1.65 shipped and closed 2026-07-08 (merged `962a23da`,
PR #124). Bug ledger was 0 open before this intake landed.

**Operator hard mandate (folded into SPEC's "Reproduction & TDD mandate"
section):** every FR requires a RED-first executed-path reproduction test
(driving the real `dadaia lifecycle` CLI, not a helper call) that fails for the
exact reason the user hit, a root-cause fix with no workarounds/config
band-aids/test-only shims, and the same test GREEN after the fix.
