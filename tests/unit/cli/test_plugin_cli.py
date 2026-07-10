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
validated. AC-8(d): the same holds for ``uninstall`` (both verdicts live in the same
parametrized bad-value fn below).

QA-atom law (v0.1.57): ``CliRunner`` is built with NO ``mix_stderr`` kwarg (removed in Click
8.2; TypeErrors on the installed 8.4.1); ``result.stderr``/``result.stdout`` are read as
separate channels; the error assert is width-independent (strip ANSI + Rich box glyphs,
collapse whitespace) BEFORE the substring check — Rich box-wrap passes locally, fails on the
CI width.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.golden_platform import norm_stderr

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
    data: dict[str, object] = json.loads(
        (tmp_path / ".dadaia" / "states" / "installed_plugins.json").read_text(encoding="utf-8")
    )
    return data


@pytest.mark.parametrize(
    ("verb",),
    [("install",), ("uninstall",)],
)
def test_bad_pack_value_is_bad_parameter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    """``plugin install|uninstall bogus`` → exit 2, width-independent stderr naming the bad
    value, empty stdout. Validation precedes workspace resolution, so a bad value is a clean
    exit-2 regardless of workspace state. AC-11(0a) / AC-8(d) sabotage target."""
    monkeypatch.chdir(_workspace(tmp_path))
    result = _runner.invoke(app, ["plugin", verb, "bogus"])
    assert result.exit_code == 2
    norm = norm_stderr(result.stderr)
    assert "bogus" in norm, norm
    # The UsageError is on stderr — no partial payload leaks to stdout.
    assert result.stdout == ""


def test_plugin_uninstall_drops_ledger_and_prints_restored_agents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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


def test_ledger_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """install records the canonical ledger shape; re-install is idempotent (single entry);
    a second pack appends (devops enables devops-engineer); uninstalling a known-but-not-
    installed pack is an idempotent no-op (exit 0, 'no change', ledger byte-identical)."""
    monkeypatch.chdir(_workspace(tmp_path))

    result = _runner.invoke(app, ["plugin", "install", "frontend-design"])
    assert result.exit_code == 0, result.output
    assert _ledger(tmp_path) == {"schema_version": "1", "plugins": ["frontend-design"]}

    reinstall = _runner.invoke(app, ["plugin", "install", "frontend-design"])
    assert reinstall.exit_code == 0, reinstall.output
    assert "already installed" in reinstall.stdout
    assert _ledger(tmp_path) == {"schema_version": "1", "plugins": ["frontend-design"]}

    ledger_path = tmp_path / ".dadaia" / "states" / "installed_plugins.json"
    before = ledger_path.read_bytes()
    not_installed = _runner.invoke(app, ["plugin", "uninstall", "devops"])
    assert not_installed.exit_code == 0
    assert "no change" in not_installed.stdout
    assert ledger_path.read_bytes() == before, "not-installed uninstall mutated the ledger"

    second = _runner.invoke(app, ["plugin", "install", "devops"])
    assert second.exit_code == 0, second.output
    assert _ledger(tmp_path)["plugins"] == ["frontend-design", "devops"]


def test_list_and_doctor_reflect_install_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``plugin list`` shows both distributed packs, marking the installed one distinctly;
    ``plugin doctor`` reports the descriptor status of each installed pack."""
    monkeypatch.chdir(_workspace(tmp_path))

    fresh = _runner.invoke(app, ["plugin", "list"])
    assert fresh.exit_code == 0, fresh.output
    assert "[available] frontend-design" in fresh.stdout
    assert "[available] devops" in fresh.stdout

    none_yet = _runner.invoke(app, ["plugin", "doctor"])
    assert none_yet.exit_code == 0, none_yet.output
    assert "no plugin packs installed" in none_yet.stdout

    _runner.invoke(app, ["plugin", "install", "frontend-design"])

    after_list = _runner.invoke(app, ["plugin", "list"])
    assert "[installed] frontend-design" in after_list.stdout
    assert "[available] devops" in after_list.stdout

    after_doctor = _runner.invoke(app, ["plugin", "doctor"])
    assert after_doctor.exit_code == 0, after_doctor.output
    assert "[ok] plugin:frontend-design (descriptor present)" in after_doctor.stdout
