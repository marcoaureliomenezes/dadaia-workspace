"""Help-quality ratchet (backlog cli-help-architecture, T-053-24): a leaf command must
not be born with a one-line docstring — the help IS the documentation surface now.
Ratchet: the offender count only goes down. Intent: contract; size: unit."""

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
_RATCHET = 42


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
