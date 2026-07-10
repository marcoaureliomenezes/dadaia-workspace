"""``lease._main_pid_probe`` resolves the PUBLIC infra builder (T-54-13, FR6 / AC-4).

v0.1.54 FR6 consolidates the three private probe-builder wrappers into a single public
factory ``infrastructure.process_probe_adapter.build_pid_probe``. The lease
side-door probe resolver (``_main_pid_probe``) retargets its dynamic ``importlib`` lookup
to that public builder — staying **dynamic** so the static import graph keeps ZERO
``features -> infrastructure`` edge (the import-linter ignore-cap stays 26).

Positive / invariant behavior mandated by architect A8 + AC-4, merged into one
parametrized decision table:

    resolves the public builder  -> ``_main_pid_probe()`` returns exactly what
                                    ``process_probe_adapter.build_pid_probe`` produces
                                    (retarget proof — RED against the pre-FR6 tree, which
                                    resolved the private hook builder)
    builder None                 -> ``_main_pid_probe()`` degrades to None (TTL-only)
    builder raises               -> ``_main_pid_probe()`` degrades to None (fail-open)

Plus one live-wiring test: the resolved probe reports THIS process alive.
"""

from __future__ import annotations

import os

import pytest

from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.infrastructure import process_probe_adapter


def _sentinel(_pid: int) -> bool:
    return True


def _boom() -> lease.PidProbe | None:
    raise RuntimeError("adapter unavailable")


@pytest.mark.parametrize(
    ("builder", "expected"),
    [
        pytest.param(lambda: _sentinel, "sentinel", id="resolves-the-public-infra-builder"),
        pytest.param(lambda: None, None, id="degrades-to-none-when-builder-returns-none"),
        pytest.param(_boom, None, id="degrades-to-none-when-builder-raises"),
    ],
)
def test_main_pid_probe_resolution_matrix(  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch, builder, expected: str | None
) -> None:
    monkeypatch.setattr(process_probe_adapter, "build_pid_probe", builder)
    result = lease._main_pid_probe()
    if expected == "sentinel":
        assert result is _sentinel
    else:
        assert result is None


def test_main_pid_probe_returns_a_live_probe() -> None:
    """Through the real wiring, the resolved probe reports THIS process (getpid) alive."""
    probe = lease._main_pid_probe()

    assert probe is not None
    assert probe(os.getpid()) is True
