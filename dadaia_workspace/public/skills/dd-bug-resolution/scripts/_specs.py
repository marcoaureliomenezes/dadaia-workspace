#!/usr/bin/env python3
"""Which specs tree a ledger script acts on, and the ONE fix-line builder every ledger
script prints through, staged beside each one like `_ledger.py`."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))  # loadable alone, not only by name

from _ledger import parse as parse  # noqa: E402  (the one door to the sibling skill)
from _ledger import workspace_of as workspace_of  # noqa: E402


def find_specs(given: Path | None, *, ledger: str | None = None) -> Path:
    """*given*, else the nearest git-rooted ``specs/`` at or above the cwd — never created:
    a missing tree refuses, its fix rerunning on the bound context's tree — for a verb
    writing *ledger* (repo-relative), the repo's first open worktree."""
    here = Path.cwd().resolve()
    trees = (
        [given] if given else [d / "specs" for d in (here, *here.parents) if (d / ".git").exists()]
    )
    if tree := next((t for t in trees if t.is_dir()), None):
        return tree.resolve()
    fix, note = _bound_fix(here, _rerun(), ledger)
    print(f"error: no specs tree at {given or f'or above {here}'} — nothing was written{note}",
          f"fix: {fix}", sep="\n", file=sys.stderr)  # fmt: skip
    raise SystemExit(1)


def _bound_fix(here: Path, rerun: str, ledger: str | None) -> tuple[str, str]:
    for root, venv in ((d, d / ".dadaia" / ".venv") for d in filter(None, [workspace_of(here)])):
        if cli := shutil.which("dadaia", path=f"{venv / 'bin'}{os.pathsep}{venv / 'Scripts'}"):
            shown = subprocess.run(
                [cli, "context", "show", "--json"], capture_output=True, text=True
            )
            try:
                repo = str(json.loads(shown.stdout)["main_repo"])
            except (ValueError, LookupError, TypeError):
                return f"{head(cli)} context list", ""
            if ledger is None or ledger.startswith("specs/audits/"):  # rc-5 AC1.1
                return with_specs(rerun, root / "repos" / repo / "specs"), ""
            if trees := sorted(p for p in (root / "worktrees" / repo).glob("*/*") if _job(p)):
                many = f"; the first by name of {len(trees)} open worktrees"
                return with_specs(rerun, trees[0] / "specs"), many if trees[1:] else ""
            return f"{script(_GITFLOW / 'worktree.py')} list", ""
    return "Operator action: re-run inside a repo that holds its specs/ tree", ""


_GITFLOW = Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts"


def _job(tree: Path) -> bool:
    """*tree* is a job worktree by the one name grammar (`_worktree_names.NAME_RE`)."""
    sys.path.append(str(_GITFLOW))
    from _worktree_names import NAME_RE

    match = NAME_RE.match(f"{tree.parent.name}/{tree.name}")
    return (
        tree.is_dir()
        and match is not None
        and match["job"] not in (None, "define", "reconcile")
        and not match["task"]
    )


def quote(word: str) -> str:
    """One shell word as `core/cli_line.shell_line` spells it: ``shlex`` on POSIX; on
    Windows forward slashes, double quotes only around a blank."""
    if os.name != "nt":
        return shlex.quote(word)
    word = word.replace("\\", "/")
    return word if word and not any(c in word for c in ' \t"') else f'"{word}"'


def head(word: str) -> str:
    """A command's first word as `core/cli_line.shell_line` spells it: on Windows a quote
    opens after the drive letter, so the line never opens with one PowerShell reads as an
    expression."""
    word = quote(word)
    return f'{word[1]}"{word[2:]}' if os.name == "nt" and word.startswith('"') else word


def git_line(repo: Path | str, *argv: str) -> str:
    """``git -C <repo> argv…`` quoted, as `core/cli_line.git_line` spells it."""
    return " ".join(map(quote, ("git", "-C", str(repo), *argv)))


def script(path: Path) -> str:
    """The ONE script-command prefix: this interpreter + *path*, absolute and quoted."""
    return f"{head(sys.executable)} {quote(str(path.resolve()))}"


def with_specs(fix: str, specs: Path | str) -> str:
    """The ONE ledger fix-line builder: a :func:`script` command gains ``--specs`` once;
    ``worktree.py``, the one script resolving no specs tree, never does."""
    ledger = not fix.startswith(script(_GITFLOW / "worktree.py"))
    named = fix.startswith(f"{head(sys.executable)} ") and ledger and " --specs " not in fix
    return f"{fix} --specs {quote(str(specs))}" if named else fix


def _rerun(*drop: str) -> str:
    """This invocation again, without ``--specs`` and *drop*: a flag with its value, or a
    positional value (a token no flag precedes)."""
    argv, flags = sys.argv, ("--specs", *(d for d in drop if d.startswith("-")))
    rest = [w for i, w in enumerate(argv) if i and w.split("=")[0] not in flags
            and argv[i - 1] not in flags and not (w in drop and not argv[i - 1].startswith("-"))]  # fmt: skip
    return " ".join((script(Path(argv[0])), *map(quote, rest)))


def choice[E: Exception](refusal: E, words: str, *drop: str) -> E:
    """Make *refusal*'s fix the operator's choice (ADR 0158): its command — its own fix, else
    this invocation without *drop* — and *words* naming what to supply."""
    refusal.choice = (words, drop)  # type: ignore[attr-defined]
    return refusal


def refuse(refusal: Exception, specs: Path) -> int:
    """Print *refusal* and its one fix, ``--specs`` kept in any command it quotes."""
    words, drop = getattr(refusal, "choice", ("", ()))
    fix = with_specs(str(getattr(refusal, "fix", "")) or (_rerun(*drop) if words else ""), specs)
    fix = f"Operator action: run `{fix}` {words}" if words else fix
    print(f"[error] {refusal}", f"fix: {fix}", sep="\n", file=sys.stderr)
    return 1
