"""``lease._main_pid_probe`` resolves the PUBLIC infra builder (T-54-13, FR6 / AC-4).

v0.1.54 FR6 consolidates the three private probe-builder wrappers into a single public
factory ``infrastructure.process_probe_adapter.build_pid_probe``. The lease
side-door probe resolver (``_main_pid_probe``) retargets its dynamic ``importlib`` lookup
to that public builder — staying **dynamic** so the static import graph keeps ZERO
``features -> infrastructure`` edge (the import-linter ignore-cap stays 26).

Positive / invariant unit tests mandated by architect A8 + AC-4:

    resolves the public builder  -> ``_main_pid_probe()`` returns exactly what
                                    ``process_probe_adapter.build_pid_probe`` produces
                                    (retarget proof — RED against the pre-FR6 tree, which
                                    resolved the private hook builder)
    live probe                   -> the resolved probe reports THIS process alive
    builder None                 -> ``_main_pid_probe()`` degrades to None (TTL-only)
    builder raises               -> ``_main_pid_probe()`` degrades to None (fail-open)
"""

from __future__ import annotations

import os

import pytest

from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.infrastructure import process_probe_adapter


def test_main_pid_probe_resolves_the_public_infra_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_main_pid_probe`` resolves ``process_probe_adapter.build_pid_probe`` (retarget proof).

    Monkeypatching the PUBLIC builder must change what ``_main_pid_probe`` returns; this
    fails against the pre-FR6 tree (which resolved the private hook builder).
    """

    def sentinel(_pid: int) -> bool:
        return True

    monkeypatch.setattr(process_probe_adapter, "build_pid_probe", lambda: sentinel)

    assert lease._main_pid_probe() is sentinel


def test_main_pid_probe_returns_a_live_probe() -> None:
    """Through the real wiring, the resolved probe reports THIS process (getpid) alive."""
    probe = lease._main_pid_probe()

    assert probe is not None
    assert probe(os.getpid()) is True


def test_main_pid_probe_degrades_to_none_when_builder_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """builder yields None ⇒ ``_main_pid_probe`` is None ⇒ lease degrades to TTL-only."""
    monkeypatch.setattr(process_probe_adapter, "build_pid_probe", lambda: None)

    assert lease._main_pid_probe() is None


def test_main_pid_probe_degrades_to_none_when_builder_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """builder raising ⇒ fail-open None (the side door never deadlocks the gate)."""

    def _boom() -> lease.PidProbe | None:
        raise RuntimeError("adapter unavailable")

    monkeypatch.setattr(process_probe_adapter, "build_pid_probe", _boom)

    assert lease._main_pid_probe() is None
