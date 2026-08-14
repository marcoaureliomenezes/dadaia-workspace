---
title: "python_env interpreter-probe hardening: absolute-path filter (CWE-426) + probe timeout/stdin isolation"
status: candidate
opened: 2026-08-14
description: >-
  Materializes the two LOW findings of the APPROVED security review covering the
  v0.5.1 hotfix (handoff 2026-08-14T151941Z-security-reviewer-v0.8.0-plus-hotfix-
  full-range). (1) CWE-426 untrusted search path: interpreter candidates from
  shutil.which and from the running venv's pyvenv.cfg executable value are executed
  and handed to subprocess.run without an os.path.isabs check — under a malformed
  PATH shutil.which can return a bare relative name that subprocess.run then
  PATH-resolves. (2) _interpreter_version runs its probe subprocess with no timeout=
  and stdin inherited, so an unresponsive candidate (stale mount, stdin-reading
  wrapper) hangs dadaia init indefinitely. Both are defence-in-depth, declared
  non-blocking for that push and routed to the backlog — this entry is that routing,
  materialized after being asserted twice without a file existing.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/python_env.py#_path_candidates
    change: >-
      Reject any interpreter candidate for which os.path.isabs() is false — filter
      shutil.which results here and apply the same check to the
      _current_venv_pyvenv_executable() return value — before any candidate reaches
      _interpreter_version or subprocess.run. Optionally resolve with
      os.path.realpath and record the resolved path in the diagnostics string
      (CWE-426 closure, including the pyvenv.cfg bare-name case).
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/python_env.py#_interpreter_version
    change: >-
      Pass a bounded timeout= and stdin=subprocess.DEVNULL to the probe subprocess so
      a hung candidate degrades to None and is skipped (TimeoutExpired is already a
      SubprocessError subclass, so the existing except clause suffices once timeout=
      is supplied). Consider python -I isolated mode so inherited
      PYTHONPATH/sitecustomize cannot perturb the probe's stdout.
---

# python_env interpreter-probe hardening (CWE-426 filter + probe timeout)

## Description

See frontmatter. Evidence — the APPROVED pre-push security handoff
`.dadaia/handoff/dadaia-workspace/2026-08-14T151941Z-security-reviewer-v0.8.0-plus-hotfix-full-range.handoff.json`,
findings 1 and 2 (the only two LOWs; `metrics.findings_low: 2`), covering the
v0.5.1 hotfix increment `1abe524a..b622c17c`
(bug `init-venv-bootstrap-inherits-degraded-base-python`):

- **LOW 1 (CWE-426):** `_path_candidates(min_minor)` returns `shutil.which`
  results that `_resolve_child_venv_interpreter` executes
  (`python_env.py:229-241`, executed at `:177-183` and `:294-299`) with no shape
  validation — neither `os.path.isabs` nor `os.path.realpath`. Verified
  empirically by the reviewer: with an empty PATH component and a matching binary
  in cwd, `shutil.which('python3.99')` returns the bare relative name, which
  `subprocess.run` then PATH-resolves (`execvp`). Preconditions are narrow and
  cumulative (attacker-influenced PATH AND both higher-priority candidates failing
  Requires-Python); no privilege boundary crossed — hence LOW, defence-in-depth.
  The recommended `isabs` filter also closes the theoretical `pyvenv.cfg`
  bare-name case (reviewer finding 4/INFO).
- **LOW 2 (availability):** `_interpreter_version` runs
  `subprocess.run([executable, "-c", ...], capture_output=True, ...)` with no
  `timeout=` and stdin inherited (`python_env.py:177-183`). The documented
  "candidate is simply skipped, never a hard failure" contract does not hold for a
  candidate that neither fails nor returns. Same omission exists on the
  venv-creation call at `:294-299`.

## Traceability note (why this entry exists now)

This routing was declared and not materialized **twice**: (1) the handoff's own
`verdict_reason` closes with "Two LOW findings … are defence-in-depth and are
routed to the backlog, not to this push"; (2) the v0.8.0 CLOSURE "Backlog returns"
recorded that a grep of `specs/backlog/` for `CWE-426`, `isabs`, `python_env` and
`subprocess timeout` returned zero files. This file is the third and final
materialization of that routing. Belongs to the hotfix's Arm B lane; surfaced at
the v0.8.0 closure because that is where it was caught.

## Acceptance criteria

- No candidate for which `os.path.isabs()` is false is ever executed or passed to
  `subprocess.run`, from either the PATH-derived or the `pyvenv.cfg`-derived
  source; a unit test proves the bare-relative-name case is skipped.
- `_interpreter_version` bounds its probe with `timeout=` and
  `stdin=subprocess.DEVNULL`; a unit test proves a hung candidate degrades to
  `None` and is skipped with diagnostics.
- Existing bootstrap behavior on healthy hosts is unchanged (full suite green).

## Ownership

`software-engineer` implements; `security-reviewer` verifies the two findings
closed in the covering push review.
