---
name: implement-review-write-scope-from-tasks-parity
status: candidate
opened: 2026-07-09
owner: project-manager (curates)
source: "v0.1.68 closure return — code-reviewer LOW: FR3 write-scope derivation wired into the `pipeline` verb only; the `implement-review` verb has no equivalent"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/cli/commands/lifecycle.py#implement_review" }
    change: "extend the FR3 (v0.1.68) TASKS.md write-scope derivation to the `implement-review` CLI verb, matching what the `pipeline` verb gained. Today `implement-review` (lifecycle.py:1656-1753 at HEAD 7b08beef) has neither the write_scope_from_tasks union nor a --write-scope flag, so a release driven through implement-review under-scopes its implement worker exactly as the pipeline verb did pre-v0.1.68. Wire write_scope_from_tasks(specs_dir, release_id) into the implement step of run_implement_review_loop the same way the pipeline verb does, and add a --write-scope escape hatch for parity. Requires threading specs_dir/release into the implement-review pipeline builder."
---

# BACKLOG — Give `implement-review` the same TASKS.md write-scope derivation as `pipeline`

**Priority:** MEDIUM. v0.1.68 FR3 fixed the filed bug
`pipeline-does-not-derive-write-scope-from-tasks` for the `dadaia lifecycle
pipeline` verb (the exact surface the operator reported). The code-reviewer noted
that `dadaia lifecycle implement-review` — a real, separately-invokable release
verb that also runs an implement step — did **not** receive the same derivation
(nor a `--write-scope` flag). An operator progressing a release through
`implement-review` would still hit the under-scoped-implement-worker behavior.

**Why not folded into v0.1.68:** the filed bug and its SPEC (FR3) were scoped to
`pipeline`; QA/security/architect validated that surface. Extending to
`implement-review` is a genuine adjacent gap, not part of the picked bug — routed
here as a follow-up per the reviewer's recommendation rather than expanding a
validated, approved release.

**Acceptance sketch:** an executed-path test drives `dadaia lifecycle
implement-review` with no `--write-scope` and asserts the implement step's
`allowed_paths` includes the reserved task's `Write set:` globs; `--write-scope`
works as an additive hatch; review steps stay handoff-only.
