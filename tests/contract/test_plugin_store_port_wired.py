"""AC-5 (v0.1.61 FR4, Ruling 61-D) — the ``PluginStore`` port is wired through the composition root.

**Primary lens — EXECUTED-PATH (Ruling 61-D / QA61-1).** Static analysis cannot prove the CLI
*reaches* ``container.build_plugin_store`` at runtime, and the byte-lock goldens cannot
discriminate a behavior-preserving refactor. So the primary acceptance is a ``CliRunner``
**spy test**: monkeypatch ``container.build_plugin_store`` at the composition root and assert
BOTH ``dadaia plugin list`` and the mutating ``dadaia plugin install <pack>`` consume the
spy's store at runtime (factory call recorded; the returned store's ``read`` — and ``write``
for install — invoked).

RED-first: FAILS on the pre-FR4 tree, where ``cli/commands/plugin.py`` constructed
``JsonPluginStore()`` directly (the spy is never reached).

**Secondary lens — AST/grep.** Production ``JsonPluginStore(`` construction appears ONLY in
``container.py``, ``infrastructure/json_plugin_store.py``, and the ``public_assets`` default
parameter; and ``container.build_plugin_store()`` returns a ``PluginStore``-satisfying object.

**Mutation-sanity AC-9(a):** re-inlining ``JsonPluginStore()`` in ``cli/commands/plugin.py``
(bypassing the container) makes the spy tests FAIL — and the secondary lens too.

QA-atom law (v0.1.57): ``CliRunner`` with NO ``mix_stderr`` kwarg; no width-dependent output
asserts needed here (we assert spy state, not rendered text).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dadaia_workspace
from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.plugin_pack import InstalledPlugins
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore

_runner = CliRunner()

_PKG_ROOT = Path(dadaia_workspace.__file__).parent

# The ONLY production files allowed to construct the concrete adapter (secondary lens).
_ALLOWED_CONSTRUCTION_FILES = {
    _PKG_ROOT / "container.py",
    _PKG_ROOT / "infrastructure" / "json_plugin_store.py",
    # Same-layer constructor default (``plugin_store: PluginStore = JsonPluginStore()``).
    _PKG_ROOT / "infrastructure" / "public_assets.py",
}


def _workspace(tmp_path: Path) -> Path:
    """Create a minimal initialized workspace (the ``resolve_workspace_root`` sentinel).

    Mirrors the fixture pattern of ``tests/unit/cli/test_plugin_cli.py``.
    """
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    return tmp_path


class _SpyPluginStore:
    """A recording proxy that satisfies the ``PluginStore`` protocol.

    Delegates to the real JSON adapter so CLI behavior stays real (byte-lock intact) while
    recording that the *injected* store — not an inline construction — served the calls.
    """

    def __init__(self) -> None:
        self._real = JsonPluginStore()
        self.read_calls: list[Path] = []
        self.write_calls: list[Path] = []

    def read(self, states_dir: Path) -> InstalledPlugins | None:
        self.read_calls.append(states_dir)
        return self._real.read(states_dir)

    def write(self, states_dir: Path, installed: InstalledPlugins) -> None:
        self.write_calls.append(states_dir)
        self._real.write(states_dir, installed)


@pytest.fixture()
def spy(monkeypatch: pytest.MonkeyPatch) -> tuple[_SpyPluginStore, list[int]]:
    """Monkeypatch ``container.build_plugin_store`` with a factory-call-recording spy."""
    store = _SpyPluginStore()
    factory_calls: list[int] = []

    def _spy_factory() -> _SpyPluginStore:
        factory_calls.append(1)
        return store

    monkeypatch.setattr(container, "build_plugin_store", _spy_factory)
    return store, factory_calls


# ---------------------------------------------------------------------------
# Primary lens — executed path (Ruling 61-D)
# ---------------------------------------------------------------------------


def test_plugin_list_consumes_container_built_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    spy: tuple[_SpyPluginStore, list[int]],
) -> None:
    """``dadaia plugin list`` reaches ``container.build_plugin_store`` and reads via its store."""
    store, factory_calls = spy
    monkeypatch.chdir(_workspace(tmp_path))

    result = _runner.invoke(app, ["plugin", "list"])

    assert result.exit_code == 0, result.output
    assert factory_calls, "plugin list never called container.build_plugin_store"
    assert store.read_calls, "plugin list never read through the container-built store"


def test_plugin_install_consumes_container_built_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    spy: tuple[_SpyPluginStore, list[int]],
) -> None:
    """``dadaia plugin install <pack>`` reads AND writes through the container-built store."""
    store, factory_calls = spy
    ws = _workspace(tmp_path)
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["plugin", "install", "frontend-design"])

    assert result.exit_code == 0, result.output
    assert factory_calls, "plugin install never called container.build_plugin_store"
    assert store.read_calls, "plugin install never read through the container-built store"
    assert store.write_calls, "plugin install never wrote through the container-built store"
    # The spy's write is real — the canonical ledger exists with the pack recorded.
    ledger = json.loads(
        (ws / ".dadaia" / "states" / "installed_plugins.json").read_text(encoding="utf-8")
    )
    assert "frontend-design" in ledger["plugins"]


# ---------------------------------------------------------------------------
# Secondary lens — AST/grep over production sources
# ---------------------------------------------------------------------------

_CONSTRUCTION_RE = re.compile(r"\bJsonPluginStore\(")


def test_adapter_construction_sites_limited_to_composition_and_same_layer() -> None:
    """Production ``JsonPluginStore(`` construction only in the allowed files."""
    offenders: list[str] = []
    for py in sorted(_PKG_ROOT.rglob("*.py")):
        if py in _ALLOWED_CONSTRUCTION_FILES:
            continue
        if _CONSTRUCTION_RE.search(py.read_text(encoding="utf-8")):
            offenders.append(str(py.relative_to(_PKG_ROOT)))
    assert not offenders, f"JsonPluginStore constructed outside the composition root: {offenders}"


def test_build_plugin_store_returns_plugin_store_satisfying_object() -> None:
    """``container.build_plugin_store()`` exists and satisfies the ``PluginStore`` protocol."""
    store = container.build_plugin_store()
    assert callable(getattr(store, "read", None)), "store lacks a callable read()"
    assert callable(getattr(store, "write", None)), "store lacks a callable write()"
