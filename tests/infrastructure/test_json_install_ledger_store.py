"""JsonInstallLedgerStore: round-trip, idempotent write, and every unreadable ledger reads
as None (bootstrap: prune nothing), never a raise.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore
from tests.helpers.oslib import Undecodable, write_text


def _entry(rel: str = ".codex/AGENTS.md") -> LedgerEntry:
    return LedgerEntry(relpath=rel, sha256="a" * 64, family="law")


def test_write_read_roundtrip_is_idempotent(tmp_path: Path) -> None:
    store = JsonInstallLedgerStore()
    ledger = InstallLedger.of([_entry(), _entry(".claude/rules/dd-policy.md")])
    store.write(tmp_path, ledger)
    mtime = (tmp_path / "install_ledger.json").stat().st_mtime_ns
    store.write(tmp_path, ledger)
    assert store.read(tmp_path) == ledger
    assert (tmp_path / "install_ledger.json").stat().st_mtime_ns == mtime
    assert set(ledger.by_relpath()) == {".codex/AGENTS.md", ".claude/rules/dd-policy.md"}


def _ledger_with(relpath: str) -> str:
    entry = {"relpath": relpath, "sha256": "a" * 64, "family": "law"}
    return json.dumps({"schema_version": "1", "entries": [entry]})


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(None, id="absent"),
        pytest.param("{not json", id="corrupt"),
        pytest.param('{"schema_version": 3}', id="wrong-shape"),
        pytest.param(_ledger_with("../x"), id="FR3-traversal-relpath"),
        pytest.param(_ledger_with("/etc/passwd"), id="FR3-absolute-relpath"),
    ],
)
def test_an_unreadable_ledger_reads_as_none(tmp_path: Path, payload: str | None) -> None:
    if payload is not None:
        write_text(tmp_path / "install_ledger.json", payload)
    assert JsonInstallLedgerStore().read(tmp_path) is None


def test_a_ledger_that_is_not_utf8_reads_as_none_and_refuses_the_compare_on_write(
    tmp_path: Path,
) -> None:
    path = JsonInstallLedgerStore.path(tmp_path)
    path.write_bytes(b'{"entries": "caf\xe9"}')

    assert JsonInstallLedgerStore().read(tmp_path) is None
    with pytest.raises(Undecodable) as refused:
        JsonInstallLedgerStore().write(tmp_path, InstallLedger.of([]))
    assert refused.value.path == path
