"""``atomic_write`` is the one temp-then-replace writer: every parameter is
honoured and no temp survives any failure (two-atomic-writers-leak-temp-file-on-injected-os-replace-failure)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from dadaia_workspace.core.atomic_write import atomic_write

_REAL = {"write_text": Path.write_text, "write_bytes": Path.write_bytes}


@pytest.mark.parametrize(
    ("content", "kwargs", "expected"),
    [
        pytest.param("hello\n", {}, b"hello\n", id="text-default-lf-no-crlf"),
        pytest.param("line-one\n", {"newline": None}, None, id="newline-none-platform-default"),
        pytest.param('{"name": "café résumé"}', {}, '{"name": "café résumé"}'.encode(), id="accented-utf8-no-bom"),
        pytest.param('{"label": "日本語テスト"}', {}, '{"label": "日本語テスト"}'.encode(), id="cjk-utf8-no-bom"),
        pytest.param(b"\x00\x01hello\xff", {}, b"\x00\x01hello\xff", id="binary-byte-exact"),
        pytest.param("hello\n", {"ensure_parent": True}, b"hello\n", id="ensure-parent-creates-dirs"),
    ],
)  # fmt: skip
def test_write_round_trips_fresh_and_over_an_existing_target(
    tmp_path: Path, content: str | bytes, kwargs: dict[str, object], expected: bytes | None
) -> None:
    """Each parameter is honoured on a fresh write and on an atomic overwrite."""
    target = tmp_path / "nested" / "a.md" if kwargs.get("ensure_parent") else tmp_path / "a.md"
    for _ in range(2):
        atomic_write(target, content, **kwargs)  # type: ignore[arg-type]
        if expected is None:  # platform translation is allowed; the text must survive
            assert target.read_text(encoding="utf-8") == content
        else:
            assert target.read_bytes() == expected


def test_preserve_mode_copies_the_mode_and_a_missing_parent_raises(tmp_path: Path) -> None:
    """preserve_mode keeps the prior mode, not mkstemp's 0600; without ensure_parent nothing is created."""
    target = tmp_path / "a.md"
    target.write_text("orig\n", encoding="utf-8")
    os.chmod(target, 0o640)
    before = stat.S_IMODE(target.stat().st_mode)
    atomic_write(target, "new\n", preserve_mode=True)
    assert stat.S_IMODE(target.stat().st_mode) == before
    with pytest.raises(OSError):
        atomic_write(tmp_path / "nowhere" / "a.md", "hello\n")
    assert not (tmp_path / "nowhere").exists()


def test_hardlink_target_is_rebound_not_written_through(tmp_path: Path) -> None:
    """CWE-59/CWE-367: the target NAME is rebound to a new inode, never written through."""
    outside = tmp_path / "outside.md"
    outside.write_text("original\n", encoding="utf-8")
    target = tmp_path / "linked.md"
    os.link(outside, target)
    before_ino = target.stat().st_ino
    atomic_write(target, "REBOUND\n")
    assert outside.read_text(encoding="utf-8") == "original\n"
    assert target.stat().st_ino != before_ino


@pytest.mark.parametrize("existing", [True, False], ids=["existing-target", "new-target"])
@pytest.mark.parametrize("preserve_mode", [False, True], ids=["preserve-off", "preserve-on"])
@pytest.mark.parametrize(
    ("content", "newline"),
    [("hello\n", None), ("hello\n", ""), (b"hello\n", "")],
    ids=["text-default-newline", "text-lf-forced", "binary"],
)
@pytest.mark.parametrize("failure_point", ["create_fails", "write_fails", "replace_fails"])
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

    if failure_point == "replace_fails":
        monkeypatch.setattr("dadaia_workspace.core.atomic_write.os.replace", boom)
    else:
        monkeypatch.setattr(Path, method, boom)

    with pytest.raises(OSError, match="injected failure"):
        atomic_write(target, content, preserve_mode=preserve_mode, newline=newline)

    assert [p.name for p in tmp_path.iterdir()] == (["atom.md"] if existing else [])
    if existing:
        assert target.read_text(encoding="utf-8") == "original\n"
