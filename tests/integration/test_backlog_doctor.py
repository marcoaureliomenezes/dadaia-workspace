"""Intent: CONTRACT — sa-backlog-status-has-no-single-authority#B1, #B2, #B3, #B8: the
`ledgers` section judges a live entry through `backlog.py check` alone (it carries no
status list); the doctor keeps only anchor resolution (BL-SCHEMA) and BL-CONFLICT.
Size: MEDIUM — the real section, each ledger script a child process.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.cli.commands.doctor import _ledgers_section

pytestmark = pytest.mark.integration

_SOURCE = "class Widget:\n    pass\n"
_LEDGER = "LEDGER-BACKLOG-SCHEMA"


def _active_entry(
    slug: str,
    title: str,
    status: str,
    *,
    ref: str | None = None,
    change: str | None = None,
    kind: str = "code",
) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": slug, "title": title, "opened": "2026-08-10", "status": status,
        "description": f"{slug} needs a change.", "provenance": "operator request",
    }  # fmt: skip
    if ref is not None:
        entry["intents"] = [{"subject": {"kind": kind, "ref": ref}, "change": change}]
    return entry


_ROWS = {  # the live entries (status, ref, change) -> the backlog findings the doctor prints
    "postponed-is-live-for-both": ([("postponed", "pkg/m.py#Widget", "a")], []),
    "uppercase-status-refused": ([("Deferred", "pkg/m.py#Widget", "a")], [_LEDGER]),
    "terminal-status-one-error": ([("delivered", "pkg/m.py#Widget", "a")], [_LEDGER]),
    "divergent-twins-conflict": (
        [("candidate", "pkg/m.py#Widget", "a"), ("candidate", "pkg/m.py#Widget", "b")],
        ["BL-CONFLICT"],
    ),
    "cli-ref-in-the-law-shape": ([("candidate", "cli:dadaia context bind", "x")], []),
    "cli-ref-bare": ([("candidate", "cli:context bind", "x")], []),
    "self-bound-invariant": ([("candidate", "invariant:INV-DOES-NOT-EXIST", "x")], ["BL-SCHEMA"]),
    "api-without-alias": ([("candidate", "api:GET /v1/x", "x")], ["BL-SCHEMA"]),
}


@pytest.mark.parametrize("row", sorted(_ROWS))
def test_the_doctor_judges_a_live_entry_as_backlog_py_check_does(row: str, tmp_path: Path) -> None:
    """sa-backlog-status-has-no-single-authority#B1: doctor ≡ `backlog.py check` on any
    status. sa-backlog-status-has-no-single-authority#B2: "Deferred" is refused, with a fix that is not sed. sa-backlog-status-has-no-single-authority#B3: a terminal token
    on a live entry gives one ERROR; "postponed" is accepted by both. sa-backlog-status-has-no-single-authority#B8: BL-CONFLICT
    stays in the doctor.
    sa-subjects-resolve-is-circular#B1: 'cli:dadaia context bind' resolves; sa-subjects-resolve-is-circular#B2: the bare
    'cli:context bind' gets B1's verdict; sa-subjects-resolve-is-circular#B3: a self-bound invariant is unresolved; sa-subjects-resolve-is-circular#B5: an
    api subject with no alias is refused with the alias-only message."""
    entries, expected = _ROWS[row]
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text(_SOURCE, encoding="utf-8")
    active = [
        _active_entry(
            f"e{n}",
            "t",
            s,
            ref=r.split(":", 1)[-1],
            change=c,
            kind=r.split(":", 1)[0] if ":" in r else "code",
        )  # fmt: skip
        for n, (s, r, c) in enumerate(entries)
    ]
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps({"schema": "backlog-v1", "active": active}), encoding="utf-8"
    )
    section = _ledgers_section(None, specs, str(tmp_path), None)
    found = [f for f in section.findings if f.code.startswith(("BL-", _LEDGER))]
    assert [f.code for f in found] == expected, [f.message for f in found]
    assert all("alias map only" in f.message for f in found if "api" in row)
    assert all(f.error and not f.fix.startswith("sed") for f in found)
