"""The doctor's `ledgers` delegation seam.

Each `specs/` ledger has exactly ONE validator since FR2: the skill script that also
writes it.  Before this module the doctor carried a second implementation of every
ledger schema (`features/specs/ledgers.py`, deleted here) — two readers of one
contract, drifting apart by construction.

This module runs each script's `check --specs <dir> --json` and re-emits its findings.
It lives in `infrastructure/` because running a subprocess is an infrastructure act
(`features` may not import `subprocess` — setup.cfg). Its rows are the one table of
the scripts' paths: every `fix:` naming a ledger script spells it by `<ROW>.invocation`.

The interpreter is always `sys.executable`: the installed script may have no exec bit
(Windows), and the venv's Python is the one that must read the tree.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from dadaia_workspace.core.cli_line import fix_line, script_line
from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.workspace_resolver import own_workspace_root
from dadaia_workspace.infrastructure.subprocess_runner import SubprocessProcessRunner

__all__ = [
    "AUDIT_SCRIPT",
    "BACKLOG_SCRIPT",
    "BUGS_SCRIPT",
    "LEDGER_SCRIPTS",
    "MEMORY_SCRIPT",
    "RELEASE_SCRIPT",
    "LedgerScript",
    "resolve_script",
    "script_findings",
    "script_repairs",
    "worktree_rows",
]

#: The package's own copy of the skills — the fallback when the doctored tree is a bare
#: `--specs-dir` with no workspace above it (CI over a checkout).
_PACKAGE_SKILLS = Path(__file__).resolve().parents[1] / "public" / "skills"

#: A `check` run may only exit 0 (clean) or 1 (findings); anything else is a broken
#: script, not a broken ledger.
_CHECK_EXITS = (0, 1)

_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class LedgerScript:
    """One ledger's script: which skill ships it and what the doctor calls its findings."""

    name: str
    skill: str
    filename: str
    #: The script's own verb that re-derives a DERIVED ledger from its source — empty
    #: for a ledger of record, which no repair may rewrite.
    regenerate: tuple[str, ...] = ()

    @property
    def code(self) -> str:
        return f"LEDGER-{self.name}-SCHEMA"

    @property
    def invocation(self) -> str:
        """The `fix:` spelling — the installed path, run through the interpreter."""
        return script_line(f".agents/skills/{self.skill}/scripts/{self.filename}")


#: One row per ledger script (0.4.7 FR2's table). A new ledger is a row, never a branch.
BUGS_SCRIPT = LedgerScript("BUGS", "dd-bug-resolution", "bugs.py")
BACKLOG_SCRIPT = LedgerScript("BACKLOG", "dd-backlog-definition", "backlog.py")
RELEASE_SCRIPT = LedgerScript("RELEASE", "dd-release-implementation", "release.py")
AUDIT_SCRIPT = LedgerScript("FINDINGS", "dd-audit-project", "audit.py")
MEMORY_SCRIPT = LedgerScript("MEMORY", "dd-spec-navigator", "memory.py", ("catalog", "generate"))
#: Not a ledger: the worktrees' owner, read by `worktree_rows` alone (ADR 0135).
WORKTREE_SCRIPT = LedgerScript("WORKTREES", "dd-gitflow-default", "worktree.py")
LEDGER_SCRIPTS = (BUGS_SCRIPT, BACKLOG_SCRIPT, RELEASE_SCRIPT, AUDIT_SCRIPT, MEMORY_SCRIPT)


class _Runner(Protocol):
    def run(
        self, argv: Sequence[str], *, cwd: Path | None = ..., timeout: float | None = ...
    ) -> Any: ...


def _skill_roots(specs_dir: Path) -> Iterator[Path]:
    """The skills tree whose scripts this run may execute, most-trusted first.

    ONE resolution, and it is a trust decision: `specs_dir` is caller-supplied, so a
    walk-up for `.agents/skills/` would execute whatever script a foreign tree happens
    to carry (CWE-427). The installed tree is used only when `specs_dir` sits inside the
    workspace this process was launched from — the operator's own. Every other tree,
    including a bare `--specs-dir` checkout in CI, reads the packaged copy.
    """
    workspace = own_workspace_root()
    here = specs_dir.resolve()
    if workspace is not None and (workspace == here or workspace in here.parents):
        installed = workspace / ".agents" / "skills"
        if installed.is_dir():
            yield installed
    yield _PACKAGE_SKILLS


def resolve_script(script: LedgerScript, specs_dir: Path) -> Path | None:
    """Where *script* really lives for this run, or ``None`` when it is not installed."""
    for root in _skill_roots(specs_dir):
        candidate = root / script.skill / "scripts" / script.filename
        if candidate.is_file():
            return candidate
    return None


def _unrunnable(script: LedgerScript, reason: str) -> SectionFinding:
    return SectionFinding(
        code=script.code,
        verdict="error",
        message=f"{script.skill}/scripts/{script.filename} {reason}",
        canonical=False,
        error=True,
        # The one remediation for a script that cannot run at all: re-project the skills.
        fix=fix_line(None, "public", "install"),
    )


def _finding(script: LedgerScript, record: dict[str, Any], specs_dir: Path) -> SectionFinding:
    unit = f"{record.get('path', '')}:{record.get('line', 0)}".strip(":")
    return SectionFinding(
        code=str(record.get("code") or script.code),
        verdict=str(record.get("verdict") or "error"),
        message=f"{unit} {record.get('message', '')}".strip(),
        canonical=False,
        error=str(record.get("verdict") or "error") == "error",
        fix=str(
            record.get("fix")
            or f"Operator action: {specs_dir.resolve() / record['path']} line "
            f"{record.get('line', 0)} is invalid; repair that line by hand, then commit."
        ),
    )


def script_findings(specs_dir: Path, runner: _Runner | None = None) -> list[SectionFinding]:
    """Every ledger finding of every script, re-emitted as one section's findings."""
    process = runner if runner is not None else SubprocessProcessRunner()
    findings: list[SectionFinding] = []
    for script in LEDGER_SCRIPTS:
        path = resolve_script(script, specs_dir)
        if path is None:
            findings.append(_unrunnable(script, "is not installed"))
            continue
        argv = [sys.executable, str(path), "check", "--specs", str(specs_dir), "--json"]
        try:
            result = process.run(argv, cwd=specs_dir.parent, timeout=_TIMEOUT_SECONDS)
        except (OSError, TimeoutError) as exc:
            findings.append(_unrunnable(script, f"could not run: {type(exc).__name__}"))
            continue
        records = _parse(result)
        if records is None:
            findings.append(_unrunnable(script, f"check exited {result.returncode} with no JSON"))
            continue
        findings.extend(_finding(script, record, specs_dir) for record in records)
    return findings


def script_repairs(specs_dir: Path, runner: _Runner | None = None) -> list[str]:
    """Re-derive every derived ledger whose check has findings, through its ONE writer —
    the repair never writes a ledger itself."""
    process = runner if runner is not None else SubprocessProcessRunner()
    repaired: list[str] = []
    for script in LEDGER_SCRIPTS:
        path = resolve_script(script, specs_dir) if script.regenerate else None
        if path is None:
            continue
        run = [sys.executable, str(path)]
        tail = ["--specs", str(specs_dir)]
        checked = process.run(
            [*run, "check", *tail], cwd=specs_dir.parent, timeout=_TIMEOUT_SECONDS
        )
        if checked.returncode == 1:
            process.run(
                [*run, *script.regenerate, *tail], cwd=specs_dir.parent, timeout=_TIMEOUT_SECONDS
            )
            repaired.append(f"[ledgers] {script.code}: {' '.join(script.regenerate)}")
    return repaired


def _parse(result: Any) -> list[dict[str, Any]] | None:
    """The script's findings, or ``None`` when it did not answer in the contract."""
    if result.returncode not in _CHECK_EXITS:
        return None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        return None
    if not isinstance(payload, list):
        return None
    return [record for record in payload if isinstance(record, dict)]


def worktree_rows(root: Path, runner: _Runner | None = None) -> tuple[list[dict[str, Any]], str]:
    """``worktree.py list --json``'s rows for the workspace at *root*, or ``([], reason)`` —
    bounded, since SessionStart waits on it."""
    path = resolve_script(WORKTREE_SCRIPT, root)
    if path is None:
        return [], "list failed: worktree.py is not installed"
    process = runner if runner is not None else SubprocessProcessRunner()
    try:
        done = process.run([sys.executable, str(path), "list", "--json"], cwd=root, timeout=10.0)
        found = json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, TimeoutError, ValueError) as exc:
        return [], f"list failed: {type(exc).__name__}"
    if not isinstance(found, list):
        return [], f"list failed: {done.stderr.strip()}"
    return found, ""
