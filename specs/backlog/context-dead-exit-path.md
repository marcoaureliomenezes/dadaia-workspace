---
name: context-dead-exit-path
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: audit 20260701T201136Z-0bcd6c19 (B/platform)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/git_subprocess.py#GitSubprocessClient" }
    change: "push(): use an explicit refspec HEAD:<upstream-branch> parsed from the tracking ref (fixes push.default=simple failure when the upstream branch name differs); skip the push entirely when rev-list @{u}..HEAD is empty"
  - subject: { kind: catalog, ref: "context-management" }
    change: "dead(): replace the per-file non-writable rglob scan with shutil.rmtree(onexc=chmod-and-retry) — git loose objects are 0444 by design and POSIX unlink needs parent-dir write, not file write; run any remaining pre-check BEFORE the push phase so a late failure cannot strand a half-dead context"
---

# BACKLOG — context dead() exit path

**Priority:** MEDIUM. `dadaia context dead` is currently broken for any repo with at
least one local commit; both failure legs share this exit path. Bugs deferred here:
`context-dead-nonwritable-guard-rejects-standard-git-objects`,
`context-dead-plain-git-push-fails-mismatched-upstream`.
