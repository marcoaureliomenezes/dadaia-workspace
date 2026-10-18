"""The ``reference-transaction`` hook: routes raw ref moves to the ref gate.

The shim runs this module on git's ``prepared`` firing, unmarked (``DADAIA_WT=1`` passes every
line there), with ``<old> <new> <ref>`` lines on STDIN. A zero old sha is read against the ref
itself, since ref packing hands one for refs that exist: only a missing ``refs/heads/wt/*`` ref is
a creation, refused with the runner's fix; any other ``refs/heads/*`` update whose new sha is not
origin's goes to ``dadaia ci ref-gate-check``, which owns the policy. Only that command's
``[ref-gate] BLOCKED`` refusal exits 3, which the shim turns into a refusal: an unrunnable or
faulting runner warns and passes, since this fires on every ref update and failing closed would
brick ``git commit``; the pre-push gate stays the fail-closed chokepoint.

A firing that needs no git imports only ``sys``.
"""

from __future__ import annotations

import sys

TYPE_CHECKING = False  # `typing` itself is an import the common firing does not pay
if TYPE_CHECKING:
    from types import ModuleType

_HEADS, _WT = b"refs/heads/", b"refs/heads/wt/"
_BLOCKED = 3


def _zero(sha: bytes) -> bool:
    return not sha.strip(b"0")


def _kernel() -> ModuleType:
    from dadaia_workspace.core import platform

    platform.use_utf8_stdio()
    return platform


def _creation_refusal(ref: bytes) -> int:
    from pathlib import Path

    from dadaia_workspace.core import cli_line

    platform, venv = _kernel(), Path(sys.prefix)
    common = platform.run(["git", "rev-parse", "--git-common-dir"]).stdout.strip()
    ref_name = platform.decode(ref)
    slug, name = Path(common).resolve().parent.name, ref_name.removeprefix("refs/heads/wt/")
    runnable = platform.is_executable(platform.venv_tool(venv, "dadaia"))
    fix = (
        cli_line.fix_line(None, "worktree", "new", slug, name)
        if runnable
        else cli_line.reinstall_fix(venv)
    )
    sys.stderr.write(
        f"[ref-gate] BLOCKED {ref_name}: wt/ branches are created by the worktree runner\n"
    )
    sys.stderr.write(cli_line.spell_fix(fix) + "\n")
    return 1


def main(stdin: bytes) -> int:
    """The hook's exit code for the ref lines *stdin*: 1 only on a refusal."""
    gated = []
    for line in stdin.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        old, new, ref = parts
        if ref.startswith(_HEADS) and _zero(old) and not _zero(new):
            platform = _kernel()
            existing = platform.run(["git", "rev-parse", "-q", "--verify", platform.decode(ref)])
            old = existing.stdout.strip().encode() or old
        if ref.startswith(_WT):
            if _zero(old) and not _zero(new):
                return _creation_refusal(ref)
        elif ref.startswith(_HEADS):
            platform = _kernel()
            tracking = f"refs/remotes/origin/{platform.decode(ref[len(_HEADS) :])}"
            held = platform.run(["git", "rev-parse", "-q", "--verify", tracking]).stdout.strip()
            if platform.decode(new) != held:
                gated.append(platform.decode(b" ".join((old, new, ref))))
    if not gated:
        return 0
    from pathlib import Path

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
    sys.exit(_BLOCKED if code else 0)
