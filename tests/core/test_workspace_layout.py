"""The zone registry's creators and the Windows-form law the stage and shipped history read.

``core.workspace_layout.DADAIA_ZONES`` is the one record of what may live in ``.dadaia/``; the
guards own every scan of the package and the law over it.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import Capabilities
from dadaia_workspace.core.template_history import was_shipped
from dadaia_workspace.core.workspace_layout import DADAIA_ZONES, Creator
from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    render_registry_tables,
)

#: The module that creates each ``Creator``'s zones. ``None`` = no single package module
#: (a runtime writer is any feature; the operator's hands are outside the package).
_CREATOR_HOME: dict[Creator, str | None] = {
    Creator.INIT: "dadaia_workspace.features.workspace.service",
    Creator.INSTALL: "dadaia_workspace.infrastructure.public_assets",
    Creator.RUNTIME: None,
    Creator.OPERATOR: None,
}


def test_every_zone_creator_exists() -> None:
    """Each ``Creator`` used by a row maps to a live module (or, for runtime/operator, to an
    explicit ``None``); a row whose creator was retired fails the build."""
    assert set(_CREATOR_HOME) == set(Creator)
    used = {z.creator for z in DADAIA_ZONES}
    assert used <= set(_CREATOR_HOME)
    for creator, module in _CREATOR_HOME.items():
        if module is not None:
            assert creator in used, f"{creator} names a module but creates no zone"
            importlib.import_module(module)


def test_law_staged_under_win32_names_the_scripts_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The staged root law names the workspace CLI in the host's venv form: under win32
    it is ``.dadaia/.venv/Scripts/dadaia.exe`` and the POSIX path appears nowhere."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    FileSystemPublicAssetManager().stage(tmp_path)
    text = (tmp_path / ".dadaia" / "agentic" / "data" / "AGENTS.md").read_text("utf-8")
    assert ".dadaia/.venv/Scripts/dadaia.exe" in text
    assert ".venv/bin/dadaia" not in text


def test_shipped_history_reads_the_forward_rendered_windows_law(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    source = "run `.dadaia/.venv/bin/dadaia doctor`"
    rendered = "run `.dadaia/.venv/Scripts/dadaia.exe doctor`"
    (tmp_path / "shipped-hashes.json").write_text(
        json.dumps({"law.md": [hashlib.sha256(rendered.encode()).hexdigest()]}), encoding="utf-8"
    )

    assert render_registry_tables(source) == render_registry_tables(rendered) == rendered
    assert was_shipped(rendered, "law.md", tmp_path)
    assert not was_shipped(rendered + " --edited", "law.md", tmp_path)
