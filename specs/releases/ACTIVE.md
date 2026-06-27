---
release: none
phase: none
---

# Active release: none

**v0.1.30** — super release: PI/Codex Layer-2 + workflow system maturation — is
**CLOSED and ARCHIVED** at `specs/_archive/releases/v0.1.30/` (CLOSURE.md). All 30 tasks
(waves A–E) implemented, tested, and reviewed; the 5 `**Consumes:**` backlog items flipped
to `DELIVERED — v0.1.30`; `pi-agent-fourth-harness` rewritten to its WS-PI-5 residual (D-2,
not delivered). `specs doctor` 0 errors.

Branch `feature/v0.1.30` is **NOT pushed / NOT merged** — operator decision (closure only,
no push). When the operator is ready to ship: re-stamp a `security-reviewer` APPROVE on the
final HEAD sha, push, watch CI until every job is green (incl. the GH-only `e2e-panel` job),
open a PR, and squash-merge to `main`.

No release is currently active. Open the next release with `dadaia lifecycle release new`
when work is picked.

Pre-existing drift (not v0.1.30 scope, for a future cleanup): `specs/releases/v0.1.23/`
remains unarchived on `main` (an `Aprovado` SPEC with no CLOSURE) — consider archiving it.
