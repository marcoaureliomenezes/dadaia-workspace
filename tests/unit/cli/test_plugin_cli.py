"""AC-3 (v0.1.60 FR2) — the ``dadaia plugin`` CLI surface (install / list / doctor).

RED-first: before FR2 there was no ``plugin`` command at all (``dadaia plugin ...`` → exit 2,
``No such command 'plugin'``). This suite pins the W1 machinery — ``install`` validates a pack
against the in-package descriptors and records it in ``installed_plugins.json`` (idempotent),
``list`` shows available vs installed, ``doctor`` reports installed-pack descriptor status. The
actual projection is W2 (T-60-20); W1 records the ledger only.

**Mutation-sanity AC-11(0a) (W1, born falsifiable):** making ``install`` accept any pack (skip
the ``pack not in available`` validation) makes
:func:`test_plugin_install_bad_value_is_bad_parameter` FAIL — a bogus pack would no longer be a
clean exit-2 ``BadParameter``. That is the discriminating proof the pack name is genuinely
validated.

QA-atom law (v0.1.57): ``CliRunner`` is built with NO ``mix_stderr`` kwarg (removed in Click
8.2; TypeErrors on the installed 8.4.1); ``result.stderr``/``result.stdout`` are read as
separate channels; the error assert is width-independent (strip ANSI + Rich box glyphs,
collapse whitespace) BEFORE the substring check — Rich box-wrap passes locally, fails on the
CI width.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.golden_platform import norm_stderr

# _norm_stderr: consolidated into tests/helpers/golden_platform.norm_stderr (v0.1.64 FR1).


# NEVER pass mix_stderr (removed in Click 8.2; the installed 8.4.1 TypeErrors on it).
_runner = CliRunner()


def _workspace(tmp_path: Path) -> Path:
    """Create a minimal initialized workspace (the ``resolve_workspace_root`` sentinel)."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    return tmp_path


def _ledger(tmp_path: Path) -> dict[str, object]:
    return json.loads(
        (tmp_path / ".dadaia" / "states" / "installed_plugins.json").read_text(encoding="utf-8")
    )


def test_plugin_install_bad_value_is_bad_parameter(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """``plugin install bogus`` → exit 2, width-independent stderr naming the bad value, empty stdout.

    Validation precedes workspace resolution, so a bad value is a clean exit-2 regardless of
    workspace state. AC-11(0a) sabotage target.
    """
    monkeypatch.chdir(_workspace(tmp_path))
    result = _runner.invoke(app, ["plugin", "install", "bogus"])
    assert result.exit_code == 2
    norm = norm_stderr(result.stderr)
    assert "bogus" in norm, norm
    assert "plugin" in norm, norm
    # The UsageError is on stderr — no partial payload leaks to stdout.
    assert result.stdout == ""


def test_plugin_install_records_ledger(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """``plugin install frontend-design`` records the pack in the canonical ledger shape."""
    monkeypatch.chdir(_workspace(tmp_path))
    result = _runner.invoke(app, ["plugin", "install", "frontend-design"])
    assert result.exit_code == 0, result.output
    assert _ledger(tmp_path) == {"schema_version": "1", "plugins": ["frontend-design"]}


def test_plugin_install_is_idempotent(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A re-install of the same pack is a no-op — the ledger is unchanged (single entry)."""
    monkeypatch.chdir(_workspace(tmp_path))
    assert _runner.invoke(app, ["plugin", "install", "frontend-design"]).exit_code == 0
    result = _runner.invoke(app, ["plugin", "install", "frontend-design"])
    assert result.exit_code == 0, result.output
    assert "already installed" in result.stdout
    assert _ledger(tmp_path) == {"schema_version": "1", "plugins": ["frontend-design"]}


def test_plugin_install_second_pack_appends(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Installing a second pack appends it — both packs recorded (devops enables devops-engineer)."""
    monkeypatch.chdir(_workspace(tmp_path))
    _runner.invoke(app, ["plugin", "install", "frontend-design"])
    result = _runner.invoke(app, ["plugin", "install", "devops"])
    assert result.exit_code == 0, result.output
    assert _ledger(tmp_path)["plugins"] == ["frontend-design", "devops"]


def test_plugin_list_shows_available_and_installed(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """``plugin list`` shows both distributed packs, marking the installed one distinctly."""
    monkeypatch.chdir(_workspace(tmp_path))
    fresh = _runner.invoke(app, ["plugin", "list"])
    assert fresh.exit_code == 0, fresh.output
    assert "[available] frontend-design" in fresh.stdout
    assert "[available] devops" in fresh.stdout

    _runner.invoke(app, ["plugin", "install", "frontend-design"])
    after = _runner.invoke(app, ["plugin", "list"])
    assert "[installed] frontend-design" in after.stdout
    assert "[available] devops" in after.stdout


def test_plugin_doctor_reports_installed_pack(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """``plugin doctor`` reports the descriptor status of each installed pack."""
    monkeypatch.chdir(_workspace(tmp_path))
    none_yet = _runner.invoke(app, ["plugin", "doctor"])
    assert none_yet.exit_code == 0, none_yet.output
    assert "no plugin packs installed" in none_yet.stdout

    _runner.invoke(app, ["plugin", "install", "frontend-design"])
    after = _runner.invoke(app, ["plugin", "doctor"])
    assert after.exit_code == 0, after.output
    assert "[ok] plugin:frontend-design (descriptor present)" in after.stdout


# ---------------------------------------------------------------------------
# v0.1.63 FR1 — `dadaia plugin uninstall` (AC-1). RED-first: pre-fix the verb
# does not exist (`No such command 'uninstall'`, exit 2).
# ---------------------------------------------------------------------------


def test_plugin_uninstall_unknown_pack_is_bad_parameter(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """``plugin uninstall bogus`` → exit 2, stderr names the pack, empty stdout (AC-1).

    Descriptor validation precedes workspace resolution (mirrors install). AC-8(d)
    sabotage target: accepting an unknown pack makes this FAIL.
    """
    monkeypatch.chdir(_workspace(tmp_path))
    result = _runner.invoke(app, ["plugin", "uninstall", "bogus"])
    assert result.exit_code == 2
    norm = norm_stderr(result.stderr)
    assert "bogus" in norm, norm
    assert result.stdout == ""


def test_plugin_uninstall_known_not_installed_is_exit_zero_no_change(  # type: ignore[no-untyped-def]
    tmp_path: Path, monkeypatch
) -> None:
    """A known-but-not-installed pack is an idempotent no-op — exit 0, `no change` (ADR-U2)."""
    monkeypatch.chdir(_workspace(tmp_path))
    _runner.invoke(app, ["plugin", "install", "frontend-design"])
    ledger_path = tmp_path / ".dadaia" / "states" / "installed_plugins.json"
    before = ledger_path.read_bytes()

    result = _runner.invoke(app, ["plugin", "uninstall", "devops"])
    assert result.exit_code == 0, result.output
    assert "no change" in result.stdout
    assert ledger_path.read_bytes() == before, "not-installed uninstall mutated the ledger"


def test_plugin_uninstall_drops_ledger_and_prints_restored_agents(  # type: ignore[no-untyped-def]
    tmp_path: Path, monkeypatch
) -> None:
    """Success drops the pack from the ledger and prints the restored agents (AC-1)."""
    monkeypatch.chdir(_workspace(tmp_path))
    _runner.invoke(app, ["plugin", "install", "frontend-design"])
    assert _ledger(tmp_path)["plugins"] == ["frontend-design"]

    result = _runner.invoke(app, ["plugin", "uninstall", "frontend-design"])
    assert result.exit_code == 0, result.output
    assert "frontend-engineer" in result.stdout
    assert "design-specialist" in result.stdout
    assert _ledger(tmp_path) == {"schema_version": "1", "plugins": []}
