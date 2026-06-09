"""Unit tests for container.py builder functions."""

import json
import sys
import types
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.workspace.service import WorkspaceService


def _init_states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(json.dumps({"version": "1", "contexts": []}))
    return states


def test_build_workspace_service_returns_service(tmp_path: Path) -> None:
    svc = container.build_workspace_service(tmp_path)
    assert isinstance(svc, WorkspaceService)


def test_build_public_service_returns_service() -> None:
    svc = container.build_public_service()
    assert isinstance(svc, PublicAssetService)


def test_guard_initialized_raises_when_not_initialized(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        container.build_spec_context_service(tmp_path)


def test_build_spec_context_service_succeeds_when_initialized(tmp_path: Path) -> None:
    _init_states(tmp_path)
    svc = container.build_spec_context_service(tmp_path)
    assert svc is not None


def test_build_doctor_service_raises_when_not_initialized(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        container.build_doctor_service(tmp_path)


def test_build_academy_service_raises_when_not_initialized(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        container.build_academy_service(tmp_path)


def test_build_academy_service_succeeds_when_initialized(tmp_path: Path) -> None:
    _init_states(tmp_path)
    svc = container.build_academy_service(tmp_path)
    assert svc is not None


def test_build_export_service_raises_when_not_initialized(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        container.build_export_service(tmp_path)


def test_select_dispatcher_returns_claude(monkeypatch) -> None:
    from dadaia_workspace.infrastructure.claude_agent_dispatcher import ClaudeAgentDispatcher

    monkeypatch.delenv("DADAIA_AGENT_RUNTIME", raising=False)
    dispatcher = container._select_dispatcher("claude")
    assert isinstance(dispatcher, ClaudeAgentDispatcher)


def test_select_dispatcher_returns_opencode(monkeypatch) -> None:
    from dadaia_workspace.infrastructure.cli_agent_dispatcher import OpenCodeAgentDispatcher

    monkeypatch.delenv("DADAIA_AGENT_RUNTIME", raising=False)
    dispatcher = container._select_dispatcher("opencode")
    assert isinstance(dispatcher, OpenCodeAgentDispatcher)


def test_select_dispatcher_returns_codex(monkeypatch) -> None:
    from dadaia_workspace.infrastructure.codex_agent_dispatcher import CodexAgentDispatcher

    monkeypatch.delenv("DADAIA_AGENT_RUNTIME", raising=False)
    dispatcher = container._select_dispatcher("codex")
    assert isinstance(dispatcher, CodexAgentDispatcher)


def test_select_dispatcher_defaults_to_cli(monkeypatch) -> None:
    from dadaia_workspace.infrastructure.cli_agent_dispatcher import CliAgentDispatcher

    monkeypatch.delenv("DADAIA_AGENT_RUNTIME", raising=False)
    dispatcher = container._select_dispatcher(None)
    assert isinstance(dispatcher, CliAgentDispatcher)


def test_select_dispatcher_reads_env_var(monkeypatch) -> None:
    from dadaia_workspace.infrastructure.codex_agent_dispatcher import CodexAgentDispatcher

    monkeypatch.setenv("DADAIA_AGENT_RUNTIME", "codex")
    dispatcher = container._select_dispatcher(None)
    assert isinstance(dispatcher, CodexAgentDispatcher)


def test_agent_catalog_returns_empty_when_no_agents_dir(tmp_path: Path) -> None:
    result = container._agent_catalog(tmp_path)
    assert result == ()


def test_agent_catalog_returns_sorted_agent_names(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "product-engineer.md").write_text("# Product Engineer")
    (agents_dir / "software-architect.md").write_text("# Software Architect")
    result = container._agent_catalog(tmp_path)
    assert result == ("product-engineer", "software-architect")


def test_build_orchestration_service_raises_when_not_initialized(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        container.build_orchestration_service(tmp_path)


def test_build_orchestration_service_succeeds_when_initialized(tmp_path: Path) -> None:
    _init_states(tmp_path)
    from dadaia_workspace.features.orchestration.service import OrchestrationService

    svc = container.build_orchestration_service(tmp_path)
    assert isinstance(svc, OrchestrationService)


def test_build_export_service_succeeds_when_initialized(tmp_path: Path) -> None:
    _init_states(tmp_path)
    from dadaia_workspace.features.export.service import ExportService

    svc = container.build_export_service(tmp_path)
    assert isinstance(svc, ExportService)


def test_build_doctor_service_succeeds_when_initialized(tmp_path: Path) -> None:
    _init_states(tmp_path)
    from dadaia_workspace.features.spec_context.doctor import DoctorService

    svc = container.build_doctor_service(tmp_path)
    assert isinstance(svc, DoctorService)


def test_build_repos_service_returns_service() -> None:
    from dadaia_workspace.features.repos.service import ReposService

    svc = container.build_repos_service()
    assert isinstance(svc, ReposService)


def test_build_panel_service_raises_when_not_initialized(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        container.build_panel_service(tmp_path)


def test_build_panel_service_succeeds_when_initialized(tmp_path: Path) -> None:
    _init_states(tmp_path)
    from dadaia_workspace.features.panel.service import PanelService

    svc = container.build_panel_service(tmp_path)
    assert isinstance(svc, PanelService)


# ---------------------------------------------------------------------------
# Platform adapter selection — T-018-08
# ---------------------------------------------------------------------------


def test_select_lock_adapter_returns_posix_when_has_fcntl(monkeypatch: pytest.MonkeyPatch) -> None:
    """With has_fcntl=True, _select_lock_adapter() returns the POSIX adapter module.

    Monkeypatches PLATFORM so the test is platform-neutral (runs on Linux).
    Does NOT use importorskip — this test exercises the selection logic directly.
    """
    from dadaia_workspace.core.platform import Capabilities

    # The POSIX adapter module imports fcntl at module load; on Windows it cannot
    # be imported at all, so selecting it is meaningless there — skip.
    pytest.importorskip("fcntl")

    posix_caps = Capabilities.detect("linux")
    assert posix_caps.has_fcntl is True  # pre-condition

    monkeypatch.setattr("dadaia_workspace.container.PLATFORM", posix_caps, raising=False)
    # Ensure the PLATFORM import inside _select_lock_adapter sees the patch.
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", posix_caps)

    import dadaia_workspace.infrastructure.file_lock_posix as _posix_mod

    adapter = container._select_lock_adapter()
    assert adapter is _posix_mod, (
        f"Expected file_lock_posix adapter, got {adapter!r}. "
        "Container must route to POSIX adapter when PLATFORM.has_fcntl is True."
    )


def test_select_lock_adapter_returns_windows_when_not_has_fcntl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With has_fcntl=False, _select_lock_adapter() returns the Windows adapter module.

    Monkeypatches PLATFORM to simulate Windows capabilities, and injects a fake
    'dadaia_workspace.infrastructure.file_lock_windows' module into sys.modules to
    prevent the module-level Windows platform guard from raising on Linux.
    """
    import importlib.util

    from dadaia_workspace.core.platform import Capabilities

    win_caps = Capabilities.detect("win32")
    assert win_caps.has_fcntl is False  # pre-condition
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", win_caps)

    module_key = "dadaia_workspace.infrastructure.file_lock_windows"

    if importlib.util.find_spec("fcntl") is None:
        # Real Windows runner: the Windows adapter imports cleanly (no module-level
        # guard fires), so assert the genuinely-selected module by name. Avoids the
        # fake-vs-real identity fragility of sys.modules injection on Windows.
        adapter = container._select_lock_adapter()
        assert adapter.__name__ == module_key, (
            f"Expected {module_key} adapter, got {adapter!r}. "
            "Container must route to the Windows adapter when has_fcntl is False."
        )
    else:
        # Linux/macOS: the real module raises PlatformCapabilityError at import time
        # (it is Windows-only), so inject a stub to exercise the selection branch.
        _fake_windows_mod = types.ModuleType(module_key)
        _fake_windows_mod.__spec__ = None  # type: ignore[attr-defined]
        original = sys.modules.pop(module_key, None)
        sys.modules[module_key] = _fake_windows_mod
        try:
            adapter = container._select_lock_adapter()
            assert adapter is _fake_windows_mod, (
                f"Expected file_lock_windows adapter, got {adapter!r}. "
                "Container must route to Windows adapter when PLATFORM.has_fcntl is False."
            )
        finally:
            sys.modules.pop(module_key, None)
            if original is not None:
                sys.modules[module_key] = original
