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


def find_specs(given: Path | None) -> Path:
    """*given*, else the nearest git-rooted ``specs/`` at or above the cwd — never created:
    a missing tree refuses, its fix naming the tree of the context `dadaia` reports bound."""
    here, argv = Path.cwd().resolve(), sys.argv
    trees = (
        [given] if given else [d / "specs" for d in (here, *here.parents) if (d / ".git").exists()]
    )
    if tree := next((t for t in trees if t.is_dir()), None):
        return tree.resolve()
    rest = (w for i, w in enumerate(argv) if i and "--specs" not in (w, argv[i - 1]))
    rerun = " ".join((script(Path(argv[0])), *map(quote, rest)))
    print(f"error: no specs tree at {given or f'or above {here}'} — nothing was written",
          f"fix: {_bound_fix(here, rerun)}", sep="\n", file=sys.stderr)  # fmt: skip
    raise SystemExit(1)


#: The worktree kind each ledger script writes through; `audit.py` writes `specs/audits/`
#: in the repo tree directly (rc-5 AC1.1).
_KIND = {"bugs": "bug", "backlog": "backlog", "release": "release", "memory": "release"}


def _bound_fix(here: Path, rerun: str) -> str:
    """*rerun* on a writable tree of the bound context's main repo: the open worktree of
    the ledger's kind, else the command opening one."""
    for root, venv in ((d, d / ".dadaia" / ".venv") for d in (here, *here.parents)):
        if cli := shutil.which("dadaia", path=f"{venv / 'bin'}{os.pathsep}{venv / 'Scripts'}"):
            shown = subprocess.run(
                [cli, "context", "show", "--json"], capture_output=True, text=True
            )
            try:
                repo = str(json.loads(shown.stdout)["main_repo"])
            except (ValueError, LookupError, TypeError):
                return f"{quote(cli)} context list"
            if (kind := _KIND.get(Path(sys.argv[0]).stem)) is None:
                return with_specs(rerun, root / "repos" / repo / "specs")
            if trees := sorted((root / "worktrees" / repo).glob(f"*-{kind}")):
                return with_specs(rerun, trees[0] / "specs")
            worktree = (
                Path(__file__).resolve().parents[2] / "dd-gitflow-default/scripts/worktree.py"
            )
            return f"{script(worktree)} new {quote(repo)} --kind {kind}"
    return "Operator action: re-run inside a repo that holds its specs/ tree"


def quote(word: str) -> str:
    """One shell word as `core/cli_line.shell_line` spells it: ``shlex`` on POSIX; on
    Windows forward slashes, double quotes only around a blank."""
    if os.name != "nt":
        return shlex.quote(word)
    word = word.replace("\\", "/")
    return word if word and not any(c in word for c in ' \t"') else f'"{word}"'


def script(path: Path) -> str:
    """The ONE script-command prefix: this interpreter + *path*, absolute and quoted."""
    return f"{quote(sys.executable)} {quote(str(path.resolve()))}"


def with_specs(fix: str, specs: Path | str) -> str:
    """The ONE ledger fix-line builder: a :func:`script` command gains ``--specs`` once."""
    named = fix.startswith(f"{quote(sys.executable)} ") and " --specs " not in fix
    return f"{fix} --specs {quote(str(specs))}" if named else fix


def refuse(refusal: Exception, specs: Path) -> int:
    fix = with_specs(str(getattr(refusal, "fix", "")), specs)
    print(f"[error] {refusal}", f"fix: {fix}", sep="\n", file=sys.stderr)
    return 1
