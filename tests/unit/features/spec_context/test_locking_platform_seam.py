"""Platform seam: locking.py's lazy adapter selection routes via PLATFORM.has_fcntl
(v0.1.76 T-4, FR6), not an in-body ``sys.platform == "win32"`` check.

Mirrors the composition-root idiom ``container._select_lock_adapter`` already uses
(monkeypatch ``PLATFORM``, assert the selected adapter module). The lazy-import pattern
(SPEC §4.1: no module-level platform reads) is preserved — the ``PLATFORM`` capability
check happens INSIDE the function body at call time, matching the pre-existing docstring
contract of both functions.
"""

from __future__ import annotations

import importlib.util
import sys
import types

import pytest

from dadaia_workspace.features.spec_context import locking


def test_default_workspace_lock_routes_by_platform_has_fcntl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dadaia_workspace.core.platform import Capabilities

    pytest.importorskip("fcntl")
    posix_caps = Capabilities.detect("linux")
    assert posix_caps.has_fcntl is True

    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", posix_caps)

    from dadaia_workspace.infrastructure.file_lock_posix import PosixWorkspaceLock

    adapter = locking._default_workspace_lock()
    assert isinstance(adapter, PosixWorkspaceLock)

    win_caps = Capabilities.detect("win32")
    assert win_caps.has_fcntl is False
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", win_caps)

    module_key = "dadaia_workspace.infrastructure.file_lock_windows"
    if importlib.util.find_spec("fcntl") is None:
        win_adapter = locking._default_workspace_lock()
        assert type(win_adapter).__module__ == module_key
    else:
        _fake_windows_mod = types.ModuleType(module_key)
        _fake_windows_mod.__spec__ = None  # type: ignore[attr-defined]

        class _FakeWindowsWorkspaceLock:
            def acquire(self, *_a: object, **_k: object) -> None:  # pragma: no cover
                raise NotImplementedError

        _fake_windows_mod.WindowsWorkspaceLock = _FakeWindowsWorkspaceLock  # type: ignore[attr-defined]
        original = sys.modules.pop(module_key, None)
        sys.modules[module_key] = _fake_windows_mod
        try:
            win_adapter = locking._default_workspace_lock()
            assert isinstance(win_adapter, _FakeWindowsWorkspaceLock)
        finally:
            sys.modules.pop(module_key, None)
            if original is not None:
                sys.modules[module_key] = original


def test_default_context_lock_routes_by_platform_has_fcntl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dadaia_workspace.core.platform import Capabilities

    pytest.importorskip("fcntl")
    posix_caps = Capabilities.detect("linux")
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", posix_caps)

    from dadaia_workspace.infrastructure.file_lock_posix import PosixContextLock

    adapter = locking._default_context_lock()
    assert isinstance(adapter, PosixContextLock)

    win_caps = Capabilities.detect("win32")
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", win_caps)

    module_key = "dadaia_workspace.infrastructure.file_lock_windows"
    if importlib.util.find_spec("fcntl") is None:
        win_adapter = locking._default_context_lock()
        assert type(win_adapter).__module__ == module_key
    else:
        _fake_windows_mod = types.ModuleType(module_key)
        _fake_windows_mod.__spec__ = None  # type: ignore[attr-defined]

        class _FakeWindowsContextLock:
            def acquire(self, *_a: object, **_k: object) -> None:  # pragma: no cover
                raise NotImplementedError

        _fake_windows_mod.WindowsContextLock = _FakeWindowsContextLock  # type: ignore[attr-defined]
        original = sys.modules.pop(module_key, None)
        sys.modules[module_key] = _fake_windows_mod
        try:
            win_adapter = locking._default_context_lock()
            assert isinstance(win_adapter, _FakeWindowsContextLock)
        finally:
            sys.modules.pop(module_key, None)
            if original is not None:
                sys.modules[module_key] = original
