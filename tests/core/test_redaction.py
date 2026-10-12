"""public doctor shows a private match only as first…last.

Private-shaped values are composed at run time, never tracked literals.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _lines(tmp_path: Path, text: str) -> list[str]:
    lib = tmp_path / "lib"
    public_dir = lib / "pkg" / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(text, encoding="utf-8")
    (lib / "AGENTS.md").write_text(text, encoding="utf-8")
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    ws = tmp_path / "ws"
    ws.mkdir()
    return [line.render() for line in manager.doctor(ws) if "public-privacy:" in line.render()]


def test_an_operator_term_is_shown_first_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An operator denylist term shows as z…x, never raw, in the public asset and in the library's
    root AGENTS.md alike."""
    term = "zorb" + "lax"
    denylist = tmp_path / "denylist.json"
    denylist.write_text(json.dumps({term: "zz fixture term"}), encoding="utf-8")
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(denylist))

    lines = _lines(tmp_path, "made by Zorb" + "lax-Corp\n")

    assert (
        "[error] public-privacy:pkg/public/data/AGENTS.md: contains 'z…x' (zz fixture term)"
        in lines
    )
    assert "[error] public-privacy:AGENTS.md: contains 'z…x' (zz fixture term)" in lines
    assert not any("orbla" in line for line in lines)


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        (".".join(("10", "99", "99", "99")), "'1…9'"),
        ("bastion" + "." + "internal", "'b…l'"),
        ("/Users/" + "zz-fixture-user", "'/…r'"),
        ("C:\\Users\\" + "zz-fixture-user", "'C…r'"),
        ("/hom" + "e/jdoe42", "'/…2'"),
        ("someone" + "else" + "@" + "anthropic" + "." + "com", "'s…m'"),
    ],
    ids=["ip", "hostname", "macos-home", "windows-home-prose", "linux-home", "email"],
)
def test_a_baseline_match_is_shown_first_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str, shown: str
) -> None:
    """A baseline match (IP, hostname, home path, email) shows as first…last."""
    monkeypatch.delenv("DADAIA_PRIVACY_DENYLIST", raising=False)
    monkeypatch.chdir(tmp_path)

    lines = _lines(tmp_path, f"seen at {value} and more prose follows\n")

    assert any(f"baseline match {shown}" in line for line in lines), lines
    assert not any(value in line for line in lines)
