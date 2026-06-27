# implementation — partially authored

This workflow drives task-group implementation through review to a gated commit/push.
Three step fragments are now authored (release v0.1.24), supporting the live pipeline's
`implementation` step plus one review step:

- `implement-tdd.md` (`implementation.implement_tdd`, software-engineer) — failing/targeted
  test first, minimal code to pass, run tests and record commands, stay in the declared
  write set, no unrelated refactor, no task-marker-done before review evidence.
- `self-verify.md` (`implementation.self_verify`, software-engineer) — run the repo's
  test/lint commands against the changed paths and record the evidence; no advance on
  unverified claims.
- `qa-review.md` (`implementation.qa_review`, qa-engineer) — assess test architecture and
  coverage of the SPEC acceptance criteria against the diff/test evidence; emit
  APPROVED/REJECTED.

The remaining steps (see the epic, §6.3) stay **deferred to a follow-up release**:
`task_group_select` (Python/PM gate), `security_review` (security-reviewer), and
`code_review` (code-reviewer). The Python gates (`commit_gate`, `push_gate`) carry no
model and need no fragment.

Do not reference a fragment from this directory in any shipped workflow until its file
exists — the loader and workflow checks fail on a dangling fragment id.
