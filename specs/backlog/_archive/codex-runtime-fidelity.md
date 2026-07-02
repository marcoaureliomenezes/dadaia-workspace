---
name: codex-runtime-fidelity
status: delivered
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/runtime_transforms/codex.py#transform_for_codex" }
    change: "WS-CDX-PROTOCOL: make the by-name rule-law corpus reachable from a Codex session (on-disk path transform + read instruction, or a Codex-visible projection)"
  - subject: { kind: catalog, ref: "ai-harness-codex" }
    change: "WS-CDX-HYGIENE: surface the Codex interactive-vs-headless trust boundary honestly in onboarding + doctor INFO; resolve the .codex/workflows keep-or-drop decision; drop inert config keys"
---

# BACKLOG-CODEX-RUNTIME-FIDELITY — Codex projection fidelity residual

**ID:** BACKLOG-CODEX-RUNTIME-FIDELITY
**Status:** DELIVERED — WS-CDX-VERIFY / WS-CDX-BUGFIX / WS-CDX-MODEL shipped in
v0.1.13 (Codex interactive gate verified, the 4 Claude-ism bugs fixed, Codex-native model
mapping landed). WS-CDX-PROTOCOL and WS-CDX-HYGIENE are also delivered in the current
tree: the root `AGENTS.md` source documents the `.claude/rules/<rule-name>.md` rule-law
surface for every harness, `codex_doctor.check_codex_rule_corpus_reachable` verifies
Codex by-name citations resolve, and `codex_trust_boundary_info` surfaces the
interactive-vs-headless trust boundary in doctor output.
**Owner:** project-manager (curates) → ai-engineer (execution when picked).
**Source of truth:** `specs/audits/2026-06-12T001813Z/codex-runtime-fidelity-review.md`.

## Delivered outcome

Codex is a Layer-1 entry harness (`{claude, codex, pi}`). The projection is substantially
faithful. The two historical tails are now closed:

- The markdown **rule-law corpus** (`workspace-protocol`, `release-governance`, …) is
  reachable from Codex through `.claude/rules/<rule-name>.md`, documented in the
  lib-originated root `AGENTS.md`, and verified by doctor.
- The Codex **trust model** is surfaced honestly: interactive hooks fire and block;
  `codex exec` headless does not, and the headless path is protected by git chokepoints.

## Residual workstreams

1. **WS-CDX-PROTOCOL** — delivered by the on-disk rule-law surface documented in
   `public/data/AGENTS.md` and verified by `check_codex_rule_corpus_reachable`.
2. **WS-CDX-HYGIENE** — delivered by `codex_trust_boundary_info`, the
   `ai-harness-codex` onboarding text, the recorded `.codex/workflows/` KEEP decision,
   and doctor checks that reject inert/forbidden Codex config keys.

## Acceptance shape (for grill)

- The load-bearing rule corpus is demonstrably reachable from a Codex session.
- The Codex interactive-vs-headless trust boundary is stated honestly in onboarding +
  doctor; no Codex-projected artifact claims behavior Codex lacks by default.
