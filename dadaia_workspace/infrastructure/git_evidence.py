"""Git evidence adapter — subprocess-backed diff text for the lifecycle context selector.

``dadaia_workspace.features.lifecycle.context_selector`` is a **feature** module and may
not import ``subprocess`` or any ``dadaia_workspace.infrastructure`` module directly
(``features-no-subprocess`` / ``features-no-infrastructure`` import-linter contracts,
``setup.cfg``). Real diff evidence for a lifecycle step's ``sel_git_diff`` selector
therefore lives here, at the sanctioned subprocess boundary, and reaches
:class:`~dadaia_workspace.features.lifecycle.context_selector.ContextSelector` only
through its injected ``diff_provider: Callable[[], str]`` constructor parameter — the
same ports-and-adapters seam ``container.py`` already uses for the lock/telemetry
adapters (see ``features-no-infrastructure`` ``ignore_imports`` in ``setup.cfg`` for the
documented precedent). ``container.py`` is the sole composition root that may import both
this module and ``context_selector``; wiring one to the other there keeps the feature
layer subprocess-free.

This is a narrower, read-only, single-purpose sibling of
``dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient`` (which owns
clone/commit/push repo-sync operations for a different feature). Introducing a
dependency on that broader client here would couple prompt-evidence rendering to
repo-sync concerns it does not need; this module owns exactly one job — bounded,
honest diff text for a prompt.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

_DEFAULT_MAX_DIFF_LINES = 400
_GIT_TIMEOUT_SECONDS = 10.0


def _run_git(repo_root: Path, *args: str) -> str | None:
    """Run a read-only git subcommand in *repo_root*; ``None`` on any failure.

    Never raises: a missing git binary, a non-git directory, a non-zero exit, or a
    timeout all degrade to ``None`` so the caller can render an honest fallback
    message instead of crashing prompt assembly.
    """
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def git_diff_text(
    repo_root: Path,
    *,
    max_lines: int = _DEFAULT_MAX_DIFF_LINES,
    paths: tuple[str, ...] = (),
) -> str:
    """Return the working tree's uncommitted diff (staged + unstaged), bounded.

    Format: a leading ``Changed files (N):`` block (one ``- <path>`` line per entry
    from ``git status --porcelain``), a blank line, then the unified diff
    (``git diff HEAD``, falling back to ``git diff`` when there is no ``HEAD`` yet)
    truncated to *max_lines* lines with an explicit truncation note appended when the
    diff is longer.

    Never returns an empty string and never raises: any git/subprocess failure, a
    non-git directory, or a clean working tree all render as an explicit one-line
    ``"no diff evidence: ..."`` note, so a reader can tell "no changes" apart from
    "evidence was never wired" (the defect this replaces — see review finding R-04).
    """
    if not repo_root.is_dir():
        return f"no diff evidence: repo root not found ({repo_root})"
    # Optional path scoping (write-set globs): a pre-dirty tree outside the release's
    # declared write set must never pollute review evidence. Globs are reduced to their
    # non-glob directory/file prefix for git pathspec use.
    scoped = tuple(
        prefix
        for prefix in (raw.split("*", 1)[0].rstrip("/") for raw in paths)
        if prefix and ".." not in prefix.split("/")
    )
    pathspec = ("--", *scoped) if scoped else ()
    status = _run_git(repo_root, "status", "--porcelain", *pathspec)
    if status is None:
        return "no diff evidence: git status failed (not a git work tree, or git is unavailable)"
    changed = [line[3:].strip() for line in status.splitlines() if line.strip()]
    diff = _run_git(repo_root, "diff", "HEAD", *pathspec)
    if diff is None:
        diff = _run_git(repo_root, "diff", *pathspec) or ""
    if not changed and not diff.strip():
        return "no diff evidence: working tree is clean (no staged or unstaged changes)"
    lines = diff.splitlines()
    truncated = len(lines) > max_lines
    body = "\n".join(lines[:max_lines])
    header = f"Changed files ({len(changed)}):\n" + "\n".join(f"- {p}" for p in changed)
    parts = [header, ""]
    if body:
        parts.append(body)
    if truncated:
        omitted = len(lines) - max_lines
        parts.append(f"... (diff truncated at {max_lines} lines; {omitted} more line(s) omitted)")
    return "\n".join(parts).strip()


def build_git_diff_provider(
    repo_root: Path,
    *,
    max_lines: int = _DEFAULT_MAX_DIFF_LINES,
    paths: tuple[str, ...] = (),
) -> Callable[[], str]:
    """Build a zero-arg diff provider closed over *repo_root* (container DI seam).

    Intended wiring (``container.py``, not this module):

        from dadaia_workspace.infrastructure.git_evidence import build_git_diff_provider
        selector = ContextSelector(
            SpecContext(...),
            diff_provider=build_git_diff_provider(source_root),
        )
    """

    def _provider() -> str:
        return git_diff_text(repo_root, max_lines=max_lines, paths=paths)

    return _provider


def build_executed_test_gate(
    repo_root: Path,
    *,
    paths: tuple[str, ...] = (),
    timeout_seconds: float = 300.0,
) -> Callable[[], tuple[bool | None, str]]:
    """Build the deterministic executed-test CLOSE gate (container DI seam).

    Bug implementation-review-approves-unexecuted-validation: closure must never rest
    on a worker's "planned / not run" self-report. The gate RUNS pytest
    (``-p no:cacheprovider``) over the test paths inside the release's declared write
    set and yields ``(ok, evidence)``: ``ok=True``/``False`` is the real exit status,
    ``ok=None`` means the release declares no test paths (gate does not apply). The
    evidence string carries the exact command + bounded output tail.
    """
    test_targets = tuple(
        prefix
        for prefix in (raw.split("*", 1)[0].rstrip("/") for raw in paths)
        if prefix.startswith("tests") and ".." not in prefix.split("/")
    )

    def _gate() -> tuple[bool | None, str]:
        if not test_targets:
            return None, "no test paths declared in the release write set"
        existing = [t for t in test_targets if (repo_root / t).exists()]
        if not existing:
            return None, "declared test paths do not exist on disk"
        cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *existing]
        try:
            proc = subprocess.run(  # noqa: S603 — fixed argv, read-only evidence run
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"pytest run failed to execute: {exc}"
        merged = (proc.stdout + "\n" + proc.stderr).strip().splitlines()
        note = f"$ {' '.join(cmd)}  (exit {proc.returncode})"
        return proc.returncode == 0, "\n".join([note, *merged[-40:]])

    return _gate


def build_test_output_provider(
    repo_root: Path,
    *,
    paths: tuple[str, ...] = (),
    max_lines: int = 120,
    timeout_seconds: float = 300.0,
) -> Callable[[], str]:
    """Build a zero-arg executed-test-evidence provider (container DI seam).

    Runs pytest (``-p no:cacheprovider``) over the test files/dirs inside the
    release's declared write set and returns the bounded tail of its output, prefixed
    with the exact command — honest, executed evidence for review steps. Degrades to
    an explicit one-line note (never raises, never empty) when no test paths are
    declared or the run cannot start.
    """
    test_targets = tuple(
        prefix
        for prefix in (raw.split("*", 1)[0].rstrip("/") for raw in paths)
        if prefix.startswith("tests") and ".." not in prefix.split("/")
    )

    def _provider() -> str:
        if not test_targets:
            return "no test evidence: the release write set declares no tests/ paths"
        existing = [t for t in test_targets if (repo_root / t).exists()]
        if not existing:
            return "no test evidence: declared test paths do not exist yet"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            *existing,
        ]
        try:
            proc = subprocess.run(  # noqa: S603 — fixed argv, read-only evidence run
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"no test evidence: pytest run failed to execute ({exc})"
        merged = (proc.stdout + "\n" + proc.stderr).strip().splitlines()
        tail = merged[-max_lines:]
        note = f"$ {' '.join(cmd)}  (exit {proc.returncode})"
        return "\n".join([note, *tail])

    return _provider
