"""The ``reference-transaction`` hook: routes raw ref moves to the ref gate.

The shim execs this module on git's ``prepared`` firing with ``<old> <new> <ref>`` lines on STDIN.
``DADAIA_WT=1`` (the worktree runner sets it) passes every line. Unmarked, creating
``refs/heads/wt/*`` is refused with the runner's fix; updating it passes; any other
``refs/heads/*`` update whose new sha is not origin's goes to ``dadaia ci ref-gate-check``, which
owns the policy. Only that command's ``[ref-gate] BLOCKED`` refusal blocks: an unrunnable or
faulting runner warns and passes, since this fires on every ref update and failing closed would
brick ``git commit``; the pre-push gate stays the fail-closed chokepoint.

The kernel costs ~55 ms to import, so a firing that needs no git (a commit in a ``wt/`` tree,
the marker) loads none.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

_HEADS, _WT = "refs/heads/", "refs/heads/wt/"


def _zero(sha: str) -> bool:
    return not sha.strip("0")


def _kernel() -> ModuleType:
    from dadaia_workspace.core import platform

    platform.use_utf8_stdio()
    return platform


def _creation_refusal(ref: str) -> int:
    from dadaia_workspace.core import cli_line

    platform = _kernel()
    venv = Path(sys.prefix)
    common = platform.run(["git", "rev-parse", "--git-common-dir"]).stdout.strip()
    slug, name = Path(common).resolve().parent.name, ref.removeprefix(_WT)
    runnable = platform.is_executable(platform.venv_tool(venv, "dadaia"))
    fix = (
        cli_line.fix_line(None, "worktree", "new", slug, name)
        if runnable
        else cli_line.reinstall_fix(venv)
    )
    sys.stderr.write(f"[ref-gate] BLOCKED {ref}: wt/ branches are created by the worktree runner\n")
    sys.stderr.write(cli_line.spell_fix(fix) + "\n")
    return 1


def main(stdin: bytes) -> int:
    """The hook's exit code for the ref lines *stdin*: 1 only on a refusal."""
    if os.environ.get("DADAIA_WT") == "1":
        return 0
    gated = []
    for line in stdin.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        old, new, ref = parts
        if ref.startswith(_WT):
            if _zero(old) and not _zero(new):
                return _creation_refusal(ref)
        elif ref.startswith(_HEADS):
            platform = _kernel()
            tracking = f"refs/remotes/origin/{ref.removeprefix(_HEADS)}"
            if new != platform.run(["git", "rev-parse", "-q", "--verify", tracking]).stdout.strip():
                gated.append(line)
    if not gated:
        return 0
    platform = _kernel()
    try:
        done = platform.run(
            [*platform.cli_argv(Path(sys.prefix)), "ci", "ref-gate-check"],
            input="\n".join(gated) + "\n",
        )
    except OSError:
        sys.stderr.write(
            "reference-transaction: could not locate the dadaia runner; ref gate skipped\n"
        )
        return 0
    out = (done.stdout + done.stderr).strip()
    if out:
        sys.stderr.write(out + "\n")
    if done.returncode == 0:
        return 0
    if "[ref-gate] BLOCKED" in out:
        return 1
    sys.stderr.write(
        f"reference-transaction: the ref gate failed (exit {done.returncode}); update allowed\n"
    )
    return 0


if __name__ == "__main__":
    try:
        code = main(sys.stdin.buffer.read())
    except Exception as exc:  # noqa: BLE001 — fail open: this hook fires on every ref update
        sys.stderr.write(f"reference-transaction: {exc!r}; update allowed\n")
        code = 0
    sys.exit(code)
