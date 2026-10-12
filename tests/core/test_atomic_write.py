"""``atomic_write`` is the one temp-then-replace writer: every parameter is
honoured and no temp survives any failure (two-atomic-writers-leak-temp-file-on-injected-os-replace-failure)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.atomic_write import SymlinkRefusedError, atomic_write

_REAL = {"write_text": Path.write_text, "write_bytes": Path.write_bytes}


def test_none_restores_an_existing_file_to_absence(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    target.write_bytes(b"previous state")

    atomic_write(target, None)  # type: ignore[arg-type]

    assert not target.exists()


def test_none_refuses_a_symlink_before_restoring_absence(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"operator state")
    target = tmp_path / "state.json"
    target.symlink_to(outside)

    with pytest.raises(SymlinkRefusedError):
        atomic_write(target, None)  # type: ignore[arg-type]

    assert target.is_symlink()
    assert outside.read_bytes() == b"operator state"


@pytest.mark.parametrize("existing", [True, False], ids=["existing-target", "new-target"])
@pytest.mark.parametrize("preserve_mode", [False, True], ids=["preserve-off", "preserve-on"])
@pytest.mark.parametrize(
    ("content", "newline"),
    [("hello\n", None), ("hello\n", ""), (b"hello\n", "")],
    ids=["text-default-newline", "text-lf-forced", "binary"],
)
@pytest.mark.parametrize("failure_point", ["create_fails", "write_fails"])
def test_no_temp_sibling_survives_any_injected_failure(
    failure_point: str,
    content: str | bytes,
    newline: str | None,
    preserve_mode: bool,
    existing: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A2.3: every combination raises, leaves no ``.tmp`` sibling, and leaves the target
    byte-identical (or still absent)."""
    target = tmp_path / "atom.md"
    if existing:
        target.write_text("original\n", encoding="utf-8")
    method = "write_bytes" if isinstance(content, bytes) else "write_text"

    def boom(self: Path, *args: object, **kwargs: object) -> None:
        if failure_point == "write_fails":  # bytes land on disk, then the write raises
            _REAL[method](self, *args, **kwargs)  # type: ignore[operator]
        raise OSError("injected failure")

    monkeypatch.setattr(Path, method, boom)

    with pytest.raises(OSError, match="injected failure"):
        atomic_write(target, content, preserve_mode=preserve_mode, newline=newline)

    assert [p.name for p in tmp_path.iterdir()] == (["atom.md"] if existing else [])
    if existing:
        assert target.read_text(encoding="utf-8") == "original\n"
