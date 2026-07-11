"""Platform seam: telemetry/service.py's lazy refresh-lock selection routes via
PLATFORM.has_fcntl (v0.1.76 T-4, FR6), not an in-body ``sys.platform == "win32"`` check.

Mirrors the composition-root idiom ``container._select_lock_adapter`` /
``spec_context.locking._default_workspace_lock`` already use (monkeypatch ``PLATFORM``,
assert the selected adapter type). The lazy-import pattern (SPEC §4.1: no module-level
platform reads) is preserved.
"""

from __future__ import annotations

import importlib.util
import sys
import types

import pytest

from dadaia_workspace.features.telemetry import service as telemetry_service


def test_default_refresh_lock_routes_by_platform_has_fcntl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dadaia_workspace.core.platform import Capabilities

    pytest.importorskip("fcntl")
    posix_caps = Capabilities.detect("linux")
    assert posix_caps.has_fcntl is True

    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", posix_caps)

    from dadaia_workspace.infrastructure.telemetry_lock_posix import PosixTelemetryRefreshLock

    adapter = telemetry_service._default_refresh_lock()
    assert isinstance(adapter, PosixTelemetryRefreshLock)

    win_caps = Capabilities.detect("win32")
    assert win_caps.has_fcntl is False
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", win_caps)

    module_key = "dadaia_workspace.infrastructure.telemetry_lock_windows"
    if importlib.util.find_spec("fcntl") is None:
        win_adapter = telemetry_service._default_refresh_lock()
        assert type(win_adapter).__module__ == module_key
    else:
        _fake_windows_mod = types.ModuleType(module_key)
        _fake_windows_mod.__spec__ = None  # type: ignore[attr-defined]

        class _FakeWindowsTelemetryRefreshLock:
            def acquire(self, *_a: object, **_k: object) -> None:  # pragma: no cover
                raise NotImplementedError

        _fake_windows_mod.WindowsTelemetryRefreshLock = (  # type: ignore[attr-defined]
            _FakeWindowsTelemetryRefreshLock
        )
        original = sys.modules.pop(module_key, None)
        sys.modules[module_key] = _fake_windows_mod
        try:
            win_adapter = telemetry_service._default_refresh_lock()
            assert isinstance(win_adapter, _FakeWindowsTelemetryRefreshLock)
        finally:
            sys.modules.pop(module_key, None)
            if original is not None:
                sys.modules[module_key] = original
