#!/usr/bin/env python3
"""Which specs tree a ledger script acts on, and the ONE fix-line builder every ledger
script prints through."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _ledger import parse as parse
from _platform import cli_argv, cli_path, command, inline, run, venv_dir
from _refusal import Refusal, report
from _root import workspace_of as workspace_of

CATALOG = "memory/product/catalog.json"


def find_specs(given: Path | None, *, ledger: str | None = None) -> Path:
    """*given*, else the nearest git-rooted ``specs/`` at or above the cwd — never created:
    a missing tree refuses, its fix rerunning on the bound context's tree — for a verb
    writing *ledger* (repo-relative), the fix lists the repo's worktrees."""
    here = Path.cwd().resolve()
    trees = (
        [given] if given else [d / "specs" for d in (here, *here.parents) if (d / ".git").exists()]
    )
    if tree := next((t for t in trees if t.is_dir()), None):
        return tree.resolve()
    fix, note = _bound_fix(here, _rerun(), ledger)
    report(f"no specs tree at {given or f'or above {here}'} — nothing was written{note}", fix)
    raise SystemExit(1)


def workspace_cli(root: Path) -> Path:
    """The installed workspace CLI under *root*. Raises `Refusal` carrying the install fix."""
    if (cli := cli_path(root)).exists():
        return cli
    raise Refusal("no workspace CLI", _install(root))


def run_cli(
    root: Path,
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    stdin: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """The ONE spawn of the workspace CLI: *args* run from *cwd* (default *root*).
    Raises `Refusal` carrying the install fix when the CLI is missing or cannot start."""
    try:
        return run([str(workspace_cli(root)), *args], cwd=cwd or root, env=env, stdin=stdin)
    except OSError as error:
        raise Refusal(f"the workspace CLI cannot start: {error}", _install(root)) from error


def _install(root: Path) -> str:
    return command("uvx", "dadaia-workspace", "init", str(root))


def _bound_fix(here: Path, rerun: Script, ledger: str | None) -> tuple[str, str]:
    if not (root := workspace_of(here)):
        return "Agent action: re-run inside a repo that holds its specs/ tree", ""
    try:
        repo = str(json.loads(run_cli(root, "context", "show", "--json").stdout)["main_repo"])
    except Refusal as refusal:
        return refusal.fix, ""
    except (ValueError, LookupError, TypeError):
        return command(*cli_argv(venv_dir(root)), "context", "list"), ""
    if ledger is None or ledger.startswith("specs/audits/"):
        return rerun(specs=root / "repos" / repo / "specs"), ""
    return command(*cli_argv(venv_dir(root)), "worktree", "list"), ""


class Fix(str):
    """A finished fix line that keeps the words it was spelled from, so a refusal can render it
    again (with ``--specs``, or inside a sentence) without reading its text."""

    words: tuple[str, ...]

    def __new__(cls, words: tuple[str, ...]) -> Fix:
        line = super().__new__(cls, command(*words))
        line.words = words
        return line


class Script(tuple[str, ...]):
    """The argv prefix of a script: calling it gives the finished :class:`Fix` over every word,
    and :meth:`inline` the same words as text inside an ``Agent action:`` sentence. *specs* adds
    ``--specs <path>``."""

    def _argv(self, words: tuple[str, ...], specs: Path | str | None) -> tuple[str, ...]:
        return (*self, *words, *(("--specs", str(specs)) if specs is not None else ()))

    def __call__(self, *words: str, specs: Path | str | None = None) -> Fix:
        return Fix(self._argv(words, specs))

    def inline(self, *words: str, specs: Path | str | None = None) -> str:
        return inline(*self._argv(words, specs))

    def __str__(self) -> str:
        return self.inline()


def script(path: Path) -> Script:
    """The ONE script prefix: this interpreter + *path*, absolute."""
    return Script((sys.executable, str(path.resolve())))


def _rerun(*drop: str) -> Script:
    """This invocation again, without ``--specs`` and *drop*: a flag with its value, or a
    positional value (a token no flag precedes)."""
    argv, flags = sys.argv, ("--specs", *(d for d in drop if d.startswith("-")))
    rest = [w for i, w in enumerate(argv) if i and w.split("=")[0] not in flags
            and argv[i - 1] not in flags and not (w in drop and not argv[i - 1].startswith("-"))]  # fmt: skip
    return Script((sys.executable, str(Path(argv[0]).resolve()), *rest))


def choice[E: Exception](refusal: E, words: str, *drop: str) -> E:
    """Make *refusal*'s fix the operator's choice: its command — its own :class:`Fix`, else
    this invocation without *drop* — and *words* naming what to supply."""
    refusal.choice = (words, drop)  # type: ignore[attr-defined]
    return refusal


def refuse(refusal: Exception, specs: Path) -> int:
    """Print *refusal* and its one fix. A fix that is a command of this entry point (which takes
    ``--specs``) is spelled again with the tree; a choice is spelled once, as a sentence."""
    supply, drop = getattr(refusal, "choice", ("", ()))
    fix = getattr(refusal, "fix", "")
    argv = fix.words if isinstance(fix, Fix) else (_rerun(*drop) if supply and not fix else None)
    if argv is not None and "--specs" not in argv and argv[:2] == _rerun()[:2]:
        argv = (*argv, "--specs", str(specs))
    if argv is not None:
        fix = f"Agent action: run `{inline(*argv)}` {supply}" if supply else command(*argv)
    elif supply and fix:
        fix = f"{fix} ({supply})"
    report(refusal, str(fix))
    return 1
