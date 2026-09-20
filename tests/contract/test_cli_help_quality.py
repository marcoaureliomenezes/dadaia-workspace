"""Intent: CONTRACT — backlog cli-help-architecture (T-053-24) one-line-help ratchet

Help-quality ratchet (backlog cli-help-architecture, T-053-24): a leaf command must
not be born with a one-line docstring — the help IS the documentation surface now.
Ratchet: the offender count only goes down. Size: unit."""

from __future__ import annotations


def _leaves() -> list[tuple[str, object]]:
    from typer.main import get_command

    from dadaia_workspace.cli.main import app

    out: list[tuple[str, object]] = []

    def walk(cmd: object, prefix: str) -> None:
        subs = dict(getattr(cmd, "commands", {}) or {})
        if subs:
            for name, sub in subs.items():
                walk(sub, f"{prefix} {name}")
        else:
            out.append((prefix.strip(), cmd))

    walk(get_command(app), "dadaia")
    return out


#: Leaves whose help was a single line when the ratchet was recorded (2026-08-31).
#: New leaves must ship a multi-line docstring; fixing an offender lowers the pin.
#: 0.4.6 T-046-26: `clean` and six `reports` retention verbs deleted (42 -> 35).
#: 0.4.6 T-046-28: the five `academy` leaves deleted (35 -> 30).
_RATCHET = 30


def test_deleted_reaper_verbs_are_gone_and_reports_keeps_validate() -> None:
    """Intent: CONTRACT — 0.4.6 AC4 (FR4).

    `dadaia doctor --fix` is the one reaper: `dadaia --help` lists no `clean`/`tmp`
    group, no `academy` group (FR10, T-046-28), and `dadaia reports --help` lists
    exactly `validate`.
    """
    from typer.main import get_command

    from dadaia_workspace.cli.main import app

    root = get_command(app)
    groups = dict(getattr(root, "commands", {}) or {})
    assert "clean" not in groups
    assert "tmp" not in groups
    assert "academy" not in groups
    reports = dict(getattr(groups["reports"], "commands", {}) or {})
    assert set(reports) == {"validate"}


def test_the_bugs_group_is_retired_from_the_cli_tree() -> None:
    """0.4.7 FR2 (T-047-64): the bug ledger's ONE writer is
    `dd-bug-resolution/scripts/bugs.py`; no `dadaia bugs` group survives beside it —
    two writers for one ledger is the drift this candidate deletes."""
    from typer.main import get_command

    from dadaia_workspace.cli.main import app

    groups = dict(getattr(get_command(app), "commands", {}) or {})
    assert groups, "the CLI tree walked to zero groups — mis-rooted app?"
    assert "bugs" not in groups
    assert {name for name, _cmd in _leaves() if name.startswith("bugs ")} == set()


def test_one_line_help_leaf_count_only_ratchets_down() -> None:
    offenders = sorted(
        name
        for name, cmd in _leaves()
        if len([ln for ln in (getattr(cmd, "help", None) or "").strip().splitlines() if ln.strip()])
        <= 1
    )
    assert len(offenders) <= _RATCHET, (
        f"{len(offenders)} leaf commands have a one-line/empty help (ratchet {_RATCHET}). "
        f"New leaves must ship a real docstring. Offenders: {offenders}"
    )
