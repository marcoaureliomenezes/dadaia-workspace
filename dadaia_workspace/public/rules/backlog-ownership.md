---
name: backlog-ownership
description: Only project-manager creates or edits specs/backlog/** entries; all other agents are read-only consumers.
always_on: true
---

# backlog-ownership

This rule is always active.

`project-manager` is the sole owner of `specs/backlog/**`. Only it may **create or
edit** backlog entries. Every other agent — including `product-engineer` and all
specialists — is a **read-only consumer** of the backlog.

`product-engineer` **reads** PM-created backlog to author SPEC/PLAN/TASKS for a
release; it never authors or edits backlog entries itself.

A non-`project-manager` Write/Edit to `specs/backlog/**` is a hard gate violation and
is blocked, naming the offending agent.

How a picked backlog set matures into a release is governed separately by
`release-governance`; this rule governs only **who may write backlog entries**.
