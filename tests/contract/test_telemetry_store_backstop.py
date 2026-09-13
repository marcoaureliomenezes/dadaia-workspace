"""Intent: CONTRACT — T-047-26 (governance events must never reach the operator's store).

The telemetry store used to resolve its own directory as
``Path("~/.dadaia/state/telemetry").expanduser()`` inside ``container
.build_telemetry_store()``. With no seam, every governance-event test in the suite
wrote synthetic events (contexts ``ctx-a``, ``seam-ctx-b``, ``meu-projeto`` …) into the
OPERATOR'S real machine store. The seam is now one resolver,
``container.telemetry_state_dir()``, and ``tests/conftest.py`` routes it to ``tmp_path``
for every test — this contract is the backstop's own proof.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from dadaia_workspace import container


def test_build_telemetry_store_takes_its_directory_from_the_caller(tmp_path: Path) -> None:
    """The builder has no home-relative literal: the directory is a parameter."""
    store = container.build_telemetry_store(tmp_path / "state")
    assert store.db_path == tmp_path / "state" / "telemetry.sqlite"
    source = inspect.getsource(container.build_telemetry_store)
    assert "~" not in source, "build_telemetry_store must not resolve a home path itself"


def test_conftest_backstop_routes_the_resolver_away_from_the_operator_store() -> None:
    """Inside any test, the ONE resolver never names the real machine store."""
    resolved = container.telemetry_state_dir()
    real = Path("~/.dadaia/state/telemetry").expanduser()
    assert resolved != real, "conftest backstop is not routing telemetry_state_dir()"
    assert Path.home() not in resolved.parents, (
        f"telemetry state dir {resolved} still resolves under the operator's home"
    )
