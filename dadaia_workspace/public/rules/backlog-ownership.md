---
name: backlog-ownership
description: project-manager curates and coordinates specs/backlog/**; other agents route backlog changes through PM by convention (not a gate).
always_on: true
---

# backlog-ownership

This rule is always active.

`project-manager` is the **curating owner and coordinator** of `specs/backlog/**`. It
is responsible for what enters, matures, and leaves the backlog. Every other agent —
including `product-engineer` and all specialists — should treat the backlog as
**PM-curated**: read it freely, and route backlog additions or edits through
`project-manager` rather than writing them unilaterally.

`product-engineer` **reads** PM-curated backlog to author SPEC/PLAN/TASKS for a
release; it does not curate the backlog itself.

This is a **coordination convention, not a gate.** The SDD gate does **not** block
backlog writes — `specs/backlog/` is an ADDITIVE path class (workspace-root and
in-repo alike) that always flows, like bugs and audits.
Enforcing ownership as a deterministic file-write lock was removed in 0.1.7 rc-3: that
lock had no key (no harness can assert an agent's persona to the hook, in any runtime),
so it blocked the legitimate owner instead of protecting the backlog. Ownership is now
upheld by agent discipline and PM coordination.

The **only** deterministic lock in the workspace is the single-session-per-Spec-Context
lease (release-definition / implementation+review). No workflow — research,
backlog-definition, release-definition, implementation+review, or audits — is ever
gate-blocked for ownership reasons.

How a picked backlog set matures into a release is governed separately by
`release-governance`; this rule governs only **who curates backlog entries**.
