"""Intent: CONTRACT — install-ledger relpath (CWE-22 class), FR3 item 1.

``LedgerEntry.__post_init__`` is the one relpath-validation authority: a malformed relpath
never reaches a ledger through direct construction or ``InstallLedger.from_dict``.
"""

from __future__ import annotations

from pathlib import PureWindowsPath

import pytest

from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry

_WINDOWS_WS = PureWindowsPath("C:/workspace/dadaia")


@pytest.mark.parametrize(
    "relpath",
    [
        ".codex/AGENTS.md",
        "a/b/c/d.txt",
        ".dadaia/agentic/manifest.json",
        # the installer's rel_posix on Windows (``relative_to(ws).as_posix()``) never bricks install
        (_WINDOWS_WS / ".codex/skills/dadaia-cli/SKILL.md").relative_to(_WINDOWS_WS).as_posix(),
        (_WINDOWS_WS / "AGENTS.md").relative_to(_WINDOWS_WS).as_posix(),
    ],
)
def test_well_formed_relpath_constructs(relpath: str) -> None:
    """A normalized POSIX relative path constructs unchanged."""
    assert LedgerEntry(relpath=relpath, sha256="a" * 64, family="law").relpath == relpath


@pytest.mark.parametrize(
    ("relpath", "match"),
    [
        ("", "empty"),
        *((p, "absolute") for p in ("/etc/passwd", "/", "/a/b")),
        *((p, r"\.\.") for p in ("../x", "../../etc/passwd", "a/../b", "a/b/..", "..")),
        *((p, "backslash") for p in ("a\\b", "..\\..\\etc\\passwd", "C:\\Windows\\System32", "a/b\\c")),
        *((p, "normalized") for p in ("a//b", "a/b/", "./a/b", "a/./b", ".")),
    ],
)  # fmt: skip
def test_rejected_shape_is_refused_by_construction_and_from_dict(relpath: str, match: str) -> None:
    """Every shape FR3 item 1 names is refused by name, and a persisted ledger carrying it
    fails ``from_dict`` (the store bootstraps to None)."""
    with pytest.raises(ValueError, match=match):
        LedgerEntry(relpath=relpath, sha256="a" * 64, family="law")
    entries = [{"relpath": relpath, "sha256": "a" * 64, "family": "law"}]
    with pytest.raises(ValueError, match=match):
        InstallLedger.from_dict({"schema_version": "1", "entries": entries})
