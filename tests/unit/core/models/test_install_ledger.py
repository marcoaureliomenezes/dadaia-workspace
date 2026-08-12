"""``LedgerEntry.__post_init__`` — the one relpath-validation authority (FR3 item 1).

Bug class (install-ledger relpath, CWE-22 class): a malformed ``relpath`` (absolute,
escaping via ``..``, a Windows backslash, or a non-normalized POSIX form) must never
reach a persisted ledger through ANY construction path — direct construction,
``InstallLedger.from_dict`` (parsing a persisted/foreign file), or the installer's own
writer. Validating once, in ``__post_init__``, is what makes that guarantee total instead
of a per-call-site convention that the next caller forgets.
"""

from __future__ import annotations

from pathlib import PureWindowsPath

import pytest

from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry


def _entry(relpath: str) -> LedgerEntry:
    return LedgerEntry(relpath=relpath, sha256="a" * 64, family="law")


class TestValidRelpathConstructs:
    @pytest.mark.parametrize(
        "relpath",
        [
            ".claude/rules/DADAIA.md",
            "AGENTS.md",
            "a/b/c/d.txt",
            ".dadaia/agentic/manifest.json",
        ],
    )
    def test_well_formed_relpath_constructs(self, relpath: str) -> None:
        entry = _entry(relpath)
        assert entry.relpath == relpath


class TestRejectedShapes:
    """One RED case per shape FR3 item 1 names: empty, absolute, '..', backslash,
    non-normalized POSIX form."""

    def test_rejects_empty_relpath(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            _entry("")

    @pytest.mark.parametrize("relpath", ["/etc/passwd", "/", "/a/b"])
    def test_rejects_absolute_relpath(self, relpath: str) -> None:
        with pytest.raises(ValueError, match="absolute"):
            _entry(relpath)

    @pytest.mark.parametrize(
        "relpath",
        [
            "../x",
            "../../etc/passwd",
            "a/../b",
            "a/b/..",
            "..",
        ],
    )
    def test_rejects_any_dotdot_part(self, relpath: str) -> None:
        with pytest.raises(ValueError, match=r"\.\."):
            _entry(relpath)

    @pytest.mark.parametrize(
        "relpath",
        [
            "a\\b",
            "..\\..\\etc\\passwd",
            "C:\\Windows\\System32",
            "a/b\\c",
        ],
    )
    def test_rejects_any_backslash(self, relpath: str) -> None:
        with pytest.raises(ValueError, match="backslash"):
            _entry(relpath)

    @pytest.mark.parametrize(
        "relpath",
        [
            "a//b",
            "a/b/",
            "./a/b",
            "a/./b",
            ".",
        ],
    )
    def test_rejects_non_normalized_posix_form(self, relpath: str) -> None:
        with pytest.raises(ValueError, match="normalized"):
            _entry(relpath)


class TestFromDictAbsorbsMalformedPersistedLedger:
    """``from_dict``'s existing ``ValueError`` (bootstrap-to-None at the store) must
    still fire when a persisted entry carries a shape ``__post_init__`` now rejects."""

    @pytest.mark.parametrize("bad_relpath", ["../x", "/etc/passwd", "a\\b", "a//b"])
    def test_from_dict_raises_valueerror_on_rejected_shape(self, bad_relpath: str) -> None:
        data = {
            "schema_version": "1",
            "entries": [{"relpath": bad_relpath, "sha256": "a" * 64, "family": "law"}],
        }
        with pytest.raises(ValueError):
            InstallLedger.from_dict(data)


class TestCrossOsWriterGuard:
    """Mirrors the installer writer (``public_assets.py:753-765``):
    ``candidate.resolve().relative_to(ws)`` then ``.as_posix()``. On Windows this
    produces a ``WindowsPath`` whose ``.as_posix()`` NEVER contains a backslash — the
    validator must accept every such rel_posix string, on every OS, so the validator
    can never brick ``dadaia public install`` on the one OS that natively produces
    backslash-separated paths.
    """

    @pytest.mark.parametrize(
        "windows_root,windows_candidate",
        [
            ("C:/workspace/dadaia", "C:/workspace/dadaia/.claude/rules/DADAIA.md"),
            ("C:/workspace/dadaia", "C:/workspace/dadaia/.codex/skills/dadaia-cli/SKILL.md"),
            ("C:/workspace/dadaia", "C:/workspace/dadaia/AGENTS.md"),
            (
                "C:/workspace/dadaia",
                "C:/workspace/dadaia/.kimi-code/rules/watch-ci-until-green.md",
            ),
        ],
    )
    def test_windows_shaped_rel_posix_always_validates(
        self, windows_root: str, windows_candidate: str
    ) -> None:
        ws = PureWindowsPath(windows_root)
        candidate = PureWindowsPath(windows_candidate)
        rel = candidate.relative_to(ws)
        rel_posix = rel.as_posix()

        assert "\\" not in rel_posix, "PureWindowsPath.as_posix() must not leak a backslash"

        entry = _entry(rel_posix)  # must not raise
        assert entry.relpath == rel_posix
