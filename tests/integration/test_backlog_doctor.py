"""sa-backlog-status-has-no-single-authority#B1, #B2, #B3, #B8: the
`ledgers` section judges a live entry through `backlog.py check` alone (it carries no
status list); the doctor keeps only anchor resolution (BL-SCHEMA) and BL-CONFLICT.
sa-backlog-intents-have-two-grammars: the schema is the one intents grammar; the doctor
binds only the entries it accepts, never dropping the document for one bad entry.
Size: MEDIUM — the real section, each ledger script a child process.
"""

from __future__ import annotations

import json
import subprocess
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
    extra: dict[str, str] | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": slug, "title": title, "opened": "2026-08-10", "status": status,
        "description": f"{slug} needs a change.", "provenance": "operator request",
    }  # fmt: skip
    if ref is not None:
        entry["intents"] = [
            {"subject": {"kind": kind, "ref": ref}, "change": change, **(extra or {})}
        ]
    return entry


_ROWS = {  # the live entries (status, ref, change) -> the backlog findings the doctor prints
    "postponed-is-live-for-both": ([("postponed", "pkg/m.py#Widget", "a")], []),
    "uppercase-status-refused": ([("Deferred", "pkg/m.py#Widget", "a")], [_LEDGER]),
    "terminal-status-one-error": ([("delivered", "pkg/m.py#Widget", "a")], [_LEDGER]),
    "divergent-twins-conflict": (
        [("candidate", "pkg/m.py#Widget", "a"), ("candidate", "pkg/m.py#Widget", "b")],
        ["BL-CONFLICT"],
    ),
    "go-path-and-word-bind": ([("candidate", "pkg/w.go#Widget", "x")], []),
    "self-bound-invariant": ([("candidate", "invariant:INV-DOES-NOT-EXIST", "x")], ["BL-SCHEMA"]),
    "api-kind-refused": ([("candidate", "api:GET /v1/x", "x")], [_LEDGER]),
    "absolute-code-ref-refused-conflict-kept": (
        [
            ("candidate", "pkg/m.py#Widget", "a"),
            ("candidate", "pkg/m.py#Widget", "b"),
            ("candidate", "/abs/m.py#W", "c"),
        ],
        ["BL-CONFLICT", _LEDGER],
    ),  # fmt: skip
    "extra-intent-key-binds-nothing": (
        [("candidate", "pkg/m.py#Widget", "a"), ("candidate", "pkg/m.py#Widget", "b", {"x": "y"})],
        [_LEDGER],
    ),
}


@pytest.mark.parametrize("row", sorted(_ROWS))
def test_the_doctor_judges_a_live_entry_as_backlog_py_check_does(row: str, tmp_path: Path) -> None:
    """sa-backlog-status-has-no-single-authority#B1: doctor ≡ `backlog.py check` on any
    status. sa-backlog-status-has-no-single-authority#B2: "Deferred" is refused, with a fix that is not sed. sa-backlog-status-has-no-single-authority#B3: a terminal token
    on a live entry gives one ERROR; "postponed" is accepted by both. sa-backlog-status-has-no-single-authority#B8: BL-CONFLICT
    stays in the doctor.
    sa-subjects-resolve-is-circular#B3: a self-bound invariant is unresolved. T-050-154: a
    `.go` path binds, its word grepped; the retired `api` kind fails check.
    sa-backlog-intents-have-two-grammars: an absolute code ref fails check and the real
    BL-CONFLICT beside it survives; an intent with an extra key fails check and binds nothing."""
    entries, expected = _ROWS[row]
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text(_SOURCE, encoding="utf-8")
    (tmp_path / "pkg" / "w.go").write_text("type Widget struct{}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S603, S607
    active = [
        _active_entry(
            f"e{n}",
            "t",
            s,
            ref=r.split(":", 1)[-1],
            change=c,
            kind=r.split(":", 1)[0] if ":" in r else "code",
            extra=x[0] if x else None,
        )  # fmt: skip
        for n, (s, r, c, *x) in enumerate(entries)
    ]
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps({"schema": "backlog-v1", "active": active}), encoding="utf-8"
    )
    section = _ledgers_section(None, specs)
    found = [f for f in section.findings if f.code.startswith(("BL-", _LEDGER))]
    assert [f.code for f in found] == expected, [f.message for f in found]
    assert all(f.error and not f.fix.startswith("sed") for f in found)
