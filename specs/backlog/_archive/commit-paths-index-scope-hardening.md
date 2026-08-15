---
title: "commit_paths index-scope hardening: checked git add + path-scoped commit (CWE-754/CWE-668)"
status: candidate
opened: 2026-08-14
description: >-
  Materializes the single LOW finding of the APPROVED security review covering the
  v0.5.2 hotfix (handoff 2026-08-14T172631Z-security-reviewer-hotfix-v0.5.2-
  scaffold-commit-scope). GitSubprocessClient.commit_paths discards the exit status
  of its `git add -- <paths>` and then commits the WHOLE INDEX (`git commit -m
  <msg>` with no pathspec). Two reachable divergences between `paths` and the index:
  (1) the target repo's .gitignore covers a scaffold path (e.g. specs/), git add
  exits non-zero and the failure is swallowed; (2) the operator had already staged
  unrelated content before `dadaia context alive`. Either way that content lands in
  the scaffold-titled commit — the same consent class as bug
  context-alive-sweeps-unrelated-worktree-changes (fixed in v0.5.2), narrowed to
  index-staged content. CWE-754 (Improper Check for Unusual or Exceptional
  Conditions) with a CWE-668 consequence; OWASP A08. Declared non-blocking for that
  push and routed as follow-up — this entry is that routing. Residual of the v0.5.2
  fix; orbits the git_subprocess component alongside its v0.5.2 sibling surface.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_subprocess.py#GitSubprocessClient
    change: >-
      Make commit_paths honest by construction: (a) check the `git add -- <paths>`
      CompletedProcess and abort (raise GitSyncError) when returncode != 0, so a
      stage that did not happen never becomes a commit; (b) path-scope the commit
      itself — `git commit -m <msg> -- <paths>` — so unrelated index entries
      (operator pre-staged content) are ignored entirely. Option (b) subsumes (a)
      for the consent property; keep (a) anyway so silent stage failures surface
      instead of being swallowed by the caller's contextlib.suppress.
  - subject:
      kind: code
      ref: dadaia_workspace/core/protocols/git_client.py#GitClient
    change: >-
      Defence in depth on the protocol-level primitive (reviewer INFO residual,
      unreachable today): git pathspec magic (`:/`, `:(glob)`, `:(exclude)`)
      survives the `--` separator, so a future caller passing an
      externally-influenced `:`-leading path would re-widen commit_paths back to a
      sweep. Prefix each element with `:(literal)` magic, or feed paths via
      `git add --pathspec-file-nul --pathspec-from-file=-` on stdin (which also
      removes the ARG_MAX ceiling noted at _stage_files_safe).
---

# commit_paths index-scope hardening (checked add + path-scoped commit)

## Description

See frontmatter. Evidence — the APPROVED pre-push security handoff
`.dadaia/handoff/dadaia-workspace/2026-08-14T172631Z-security-reviewer-hotfix-v0.5.2-scaffold-commit-scope.handoff.json`,
finding 1 (the only LOW; `metrics.findings_low: 1`), covering the v0.5.2 hotfix
range `dff167e8..db753b1c` (bug `context-alive-sweeps-unrelated-worktree-changes`):

- **LOW (CWE-754 → CWE-668):** `git_subprocess.py:150-151` runs
  `_run(["git", "add", "--", *paths], cwd=path)` and discards the
  `CompletedProcess`, then calls `_commit(path, msg)` whose command
  (`git_subprocess.py:98`) is `git commit -m <msg>` with **no pathspec** — it
  commits the entire index, not the `paths` argument. The caller
  (`features/spec_context/service.py:435-440`) wraps the block in
  `contextlib.suppress(Exception)` and `_run` never raises, so a failed/partial
  stage is invisible. Reproduced by the reviewer in a throwaway repo: a
  `.gitignore` covering `specs/` makes `git add` fail while operator pre-staged
  content still lands in the scaffold-titled commit. Severity LOW, not MEDIUM:
  preconditions are cumulative and narrow, `alive()` commits locally only (no push
  path), and the v0.5.2 fix strictly reduced the blast radius versus the
  `commit_all` sweep it replaced.
- **INFO residual (hardened, unreachable today):** pathspec magic survives `--`;
  every current caller-built path begins alphanumeric (`specs`, `AGENTS.md`,
  `tests/AGENTS.md`), so no magic prefix can form today, but `commit_paths` is a
  general-purpose `GitClient` protocol primitive and a future caller could
  resurrect the risk.

## Traceability note (why this entry exists now)

The handoff's `fix_recommendation` and `verdict_reason` both declare "not blocking
this push — route as a follow-up". This entry is that routing, materialized by the
PM in the same session the handoff was consumed — not asserted without a file (the
lesson of `python-env-interpreter-probe-hardening`, which needed three
materialization passes). Residual of the v0.5.2 Arm B fix; pairs with entry #9's
Arm-B hardening lane and should ride the next hotfix/patch window touching
`git_subprocess`.

## Acceptance criteria

- A non-zero `git add -- <paths>` exit aborts `commit_paths` before any commit
  (surfaced as `GitSyncError`); an integration test against the real
  `GitSubprocessClient` proves a gitignored scaffold path never produces a
  scaffold-titled commit.
- The commit is path-scoped (`git commit -m <msg> -- <paths>`): an integration
  test proves operator pre-staged unrelated content never enters the tool-authored
  commit and remains staged afterwards.
- Defence-in-depth pathspec hardening (`:(literal)` prefix or
  `--pathspec-from-file`) applied, with a unit test pinning that a `:`-leading
  path is treated literally, not as pathspec magic.
- Existing `alive()` scaffold-commit behavior on clean repos unchanged (full
  suite green).

## Ownership

`software-engineer` implements; `security-reviewer` verifies the finding closed in
the covering push review.
