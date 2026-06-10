---
title: panel-token-file-chmod-toctou
severity: Medium
opened: 2026-06-07
session_id: null
status: Closed
shipped_in: 0.1.5
resolved_in: main (post-v0.1.5, T-016-P0x)
---

**Resolution (verified 2026-06-09, code-reviewer root-cause investigation):** fixed in current `main` (T-016-P0x pass). Source evidence cited in handoff `.dadaia/handoff/dadaia-workspace/2026-06-09T032430Z-code-reviewer-panel-bug-cluster-root-cause.handoff.json`; named E2E regression tests present (E2E-GUARD-01/02, E2E-SCP-03..06, E2E-THM-10). Closed; E2E suite is the standing guard.


# Bug: panel-token-file-chmod-toctou

## Description

The panel Bearer token file is created with `path.write_text(token)` and only
then `os.chmod(path, 0o600)`. Between the two calls the file exists with the
process umask (typically `0o644`, world-readable). Any other local process can
read the 32-byte token — which grants full panel API access — during that
window.

## Location

- `dadaia_workspace/features/panel/auth.py:~46-47` — `write_text` then `chmod`.

## Impact

Brief world-readable exposure of a full-access API token on multi-user or
compromised-process systems. Low likelihood, high impact.

## Environment

- dadaia version: 0.1.5 + current `main`
- Python: 3.12

## Fix direction

Atomic restricted-mode create:
`fd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL, 0o600); os.write(fd, ...)`.
`O_EXCL` also closes a generate-race where two processes both write the token.
