"""Panel must self-register in the server registry (validation-027 F-13).

The dev-server-registry law: every dev server MUST register its port. The panel is a
dev server and served HTTP while `dadaia server list` showed nothing — fixed by
registering on start and releasing on clean shutdown.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app

_runner = CliRunner()


class _StubServer:
    def serve_forever(self) -> None:  # pragma: no cover - trivial
        raise KeyboardInterrupt  # unwind like a Ctrl-C shutdown

    def shutdown(self) -> None:  # pragma: no cover - trivial
        pass


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}'
    )
    (tmp_path / "repos").mkdir()
    (tmp_path / "AGENTS.md").write_text("# agents")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_panel_registers_and_releases_port(workspace: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.cli.commands.panel.build_panel_http_server",
        lambda **kwargs: _StubServer(),
    )
    monkeypatch.setattr(
        "dadaia_workspace.cli.commands.panel.make_handler_class",
        lambda views, telemetry=None: object,
    )
    monkeypatch.setattr(
        "dadaia_workspace.container.build_panel_views", lambda root, telemetry=None: object()
    )

    registered: dict[str, object] = {}
    real_builder = container.build_server_registry_service

    def _spy_builder(root: Path):
        svc = real_builder(root)
        registered["svc"] = svc
        return svc

    monkeypatch.setattr(container, "build_server_registry_service", _spy_builder)

    result = _runner.invoke(app, ["panel", "--no-open", "--port", "4123"])
    assert result.exit_code == 0, result.output

    svc = real_builder(workspace)
    ports = [e.port for e in svc.list_entries()]
    # Registered during serve; released on clean shutdown — the registry must have
    # SEEN the port (spy) and be clean afterward.
    assert registered, "panel never touched the server registry"
    assert 4123 not in ports, "port must be released on clean shutdown"
