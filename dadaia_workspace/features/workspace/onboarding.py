"""The derived onboarding status (0.4.8 FR6, D11) — the ONE next-step derivation.

The next unmet level is read from disk on every call and never stored: no ALIVE context
(level 2 missing) -> ``context create``; an ALIVE context whose main repo carries no
current dadaia specs tree -> ``specs init``; a context never first-pass audited (no
``audits_histo.jsonl`` record) -> the ``dd-audit-project`` first-pass worklist; else
``None``. ``doctor``, ``init``, ``context create`` and the SessionStart hook all print
:meth:`Step.text` — one derivation, four callers. The registry read is the caller's
(features never import the resolution authority): the input is the name->tree map.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION, read_pattern_version

CODE = "ONBOARDING"

_AUDITS_HISTO = Path("audits") / "_archive" / "audits_histo.jsonl"
_MEMORY_SCRIPT = Path(".agents") / "skills" / "dd-spec-navigator" / "scripts" / "memory.py"


def cli_path(root: Path) -> Path:
    """The workspace CLI's real executable (``Scripts\\dadaia.exe`` on Windows)."""
    return (
        root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )


@dataclass(frozen=True)
class Step:
    """The next unmet onboarding level: why it is unmet, and the one command to run."""

    reason: str
    command: str

    def text(self) -> str:
        return f"Next: {self.reason}\nfix: {self.command}"


def specs_ready(specs_dir: Path) -> bool:
    """True once ``specs init`` has run: the tree is stamped at the canonical version.
    Absent, foreign and older trees are all level 2 — nothing for a specs doctor yet."""
    return specs_dir.is_dir() and read_pattern_version(specs_dir) >= CANONICAL_SPECS_VERSION


def _first_pass_done(specs_dir: Path) -> bool:
    try:
        text = (specs_dir / _AUDITS_HISTO).read_text(encoding="utf-8")
    except OSError:
        return False
    return any(line.strip() for line in text.splitlines())


def next_step(root: Path, trees: Mapping[str, Path], focus: str | None = None) -> Step | None:
    """The *focus* context's lowest unmet level (the doctored, just-created or bound one),
    else the lowest across *trees* (every ALIVE context name -> its ``specs/`` dir,
    ``invocation.alive_context_trees``), else ``None``."""
    if focus in trees and (step := _lowest(root, {focus: trees[focus]})):
        return step
    return _lowest(root, trees)


def _lowest(root: Path, trees: Mapping[str, Path]) -> Step | None:
    cli = cli_path(root)
    if not trees:
        return Step(
            "no ALIVE Spec Context — create one from its main repo",
            f"{cli} context create <name> --main-repo <clone-url>",
        )
    for name, specs in trees.items():
        if not specs_ready(specs):
            return Step(
                f"'{name}' carries no current specs tree", f"{cli} specs init --context {name}"
            )
    for name, specs in trees.items():
        if not _first_pass_done(specs):
            repo = specs.parent
            return Step(
                f"'{name}' has no first-pass audit — dd-audit-project §3 (first pass) worklist",
                f"python3 {root / _MEMORY_SCRIPT} drift --since "
                f"$(git -C {repo} rev-list --max-parents=0 HEAD) --specs {specs}",
            )
    return None
