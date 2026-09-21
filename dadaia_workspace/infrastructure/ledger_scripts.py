"""The doctor's `ledgers` delegation seam.

Each `specs/` ledger has exactly ONE validator since FR2: the skill script that also
writes it.  Before this module the doctor carried a second implementation of every
ledger schema (`features/specs/ledgers.py`, deleted here) — two readers of one
contract, drifting apart by construction.

This module runs each script's `check --specs <dir> --json` and re-emits its findings.
It lives in `infrastructure/` because running a subprocess is an infrastructure act
(`features` may not import `subprocess` — setup.cfg), and the CLI composition root is
the only caller.

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

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.infrastructure.subprocess_runner import SubprocessProcessRunner

__all__ = [
    "LEDGER_SCRIPTS",
    "LedgerScript",
    "resolve_script",
    "script_findings",
]

#: The package's own copy of the skills — the fallback when the doctored tree is a bare
#: `--specs-dir` with no workspace above it (CI over a checkout).
_PACKAGE_SKILLS = Path(__file__).resolve().parents[1] / "public" / "skills"

#: The one remediation for a script that cannot run at all: re-project the skills.
_INSTALL_FIX = f"{DADAIA_BIN} public install --target all"

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

    @property
    def code(self) -> str:
        return f"LEDGER-{self.name}-SCHEMA"

    @property
    def invocation(self) -> str:
        """The `fix:` spelling — the installed path, run through the interpreter."""
        return f"python3 .agents/skills/{self.skill}/scripts/{self.filename}"


#: One row per ledger script (0.4.7 FR2's table). A new ledger is a row, never a branch.
LEDGER_SCRIPTS: tuple[LedgerScript, ...] = (
    LedgerScript("BUGS", "dd-bug-resolution", "bugs.py"),
    LedgerScript("BACKLOG", "dd-backlog-definition", "backlog.py"),
    LedgerScript("RELEASE", "dd-release-implementation", "release.py"),
    LedgerScript("FINDINGS", "dd-audit-project", "audit.py"),
    LedgerScript("MEMORY", "dd-spec-navigator", "memory.py"),
)


class _Runner(Protocol):
    def run(
        self, argv: Sequence[str], *, cwd: Path | None = ..., timeout: float | None = ...
    ) -> Any: ...


def _running_workspace() -> Path | None:
    """The workspace this process runs FROM: the root whose `.dadaia/.venv/` holds our
    interpreter, or ``None`` when `dadaia` runs from anywhere else (a bare pip install).
    """
    for directory in Path(sys.executable).resolve().parents:
        if directory.name == ".venv" and directory.parent.name == ".dadaia":
            return directory.parent.parent
    return None


def _skill_roots(specs_dir: Path) -> Iterator[Path]:
    """The skills tree whose scripts this run may execute, most-trusted first.

    ONE resolution, and it is a trust decision: `specs_dir` is caller-supplied, so a
    walk-up for `.agents/skills/` would execute whatever script a foreign tree happens
    to carry (CWE-427). The installed tree is used only when `specs_dir` sits inside the
    workspace this process was launched from — the operator's own. Every other tree,
    including a bare `--specs-dir` checkout in CI, reads the packaged copy.
    """
    workspace = _running_workspace()
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
        fix=_INSTALL_FIX,
    )


def _finding(script: LedgerScript, record: dict[str, Any]) -> SectionFinding:
    unit = f"{record.get('path', '')}:{record.get('line', 0)}".strip(":")
    return SectionFinding(
        code=str(record.get("code") or script.code),
        verdict=str(record.get("verdict") or "error"),
        message=f"{unit} {record.get('message', '')}".strip(),
        canonical=False,
        error=str(record.get("verdict") or "error") == "error",
        fix=f"{script.invocation} check --specs specs",
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
        findings.extend(_finding(script, record) for record in records)
    return findings


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
