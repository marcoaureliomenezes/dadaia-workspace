"""The CLI surface: its verb tree, its rendered help and what `capabilities --json` advertises.

backlog cli-help-architecture (T-053-24) one-line-help ratchet; 0.4.7 FR5
(T-047-78) verb ceiling and citation; cli-help-leaks-internal-spec-ids;
help-texts-and-bug-schema-cite-behaviour-that-is-gone;
capabilities-advertises-verbs-and-surfaces-that-do-not-exist; dadaia-capabilities-v3 schema.
Size: SMALL (in-process Click tree and CliRunner).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from typer.main import get_command
from typer.testing import CliRunner

from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.features.capabilities import build_capabilities

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
_ENV = {"COLUMNS": "400", "NO_COLOR": "1"}


def _tree() -> list[tuple[tuple[str, ...], Any]]:
    """Every command path (root first) with its Click command."""
    out: list[tuple[tuple[str, ...], Any]] = []

    def walk(cmd: Any, path: tuple[str, ...]) -> None:
        out.append((path, cmd))
        for name, sub in (getattr(cmd, "commands", {}) or {}).items():
            walk(sub, (*path, name))

    walk(get_command(app), ())
    return out


def _leaves() -> list[tuple[tuple[str, ...], Any]]:
    return [(p, c) for p, c in _tree() if not getattr(c, "commands", None)]


def _help(*argv: str) -> str:
    """Rendered --help as plain words: CI forces colour and Rich wraps inside its box."""
    result = CliRunner().invoke(app, [*argv, "--help"], env=_ENV)
    assert result.exit_code == 0, result.output
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    return " ".join(re.sub(r"[─-╿]", " ", plain).split())


def test_deleted_groups_are_gone_and_reports_keeps_validate() -> None:
    """0.4.6 AC4 (FR4): `doctor --fix` is the one reaper — no `clean`/`tmp`/`academy` group;
    0.4.7 FR2 (T-047-64): bugs.py is the ledger's one writer — no `bugs` group."""
    groups = dict(get_command(app).commands)  # type: ignore[attr-defined]
    assert not {"clean", "tmp", "academy", "bugs"} & set(groups)
    assert set(groups["reports"].commands) == {"validate"}


def test_the_verb_surface_is_bounded_documented_and_cited() -> None:
    """At most 30 leaf verbs, a new one only when an old one leaves (ADR 0018); at most 30 with a
    one-line help (both ratchet down); every leaf is invoked (`dadaia`, `$D`, `$DADAIA`) by some
    public asset — an uncited verb is a verb nobody runs."""
    leaves = _leaves()
    assert len(leaves) <= 30, [" ".join(p) for p, _ in leaves]
    one_line = [
        p for p, c in leaves if len([ln for ln in (c.help or "").splitlines() if ln.strip()]) <= 1
    ]
    assert len(one_line) <= 30, one_line
    texts = [
        p.read_text(encoding="utf-8")
        for p in sorted(_PUBLIC.rglob("*"))
        if p.is_file()
        and not p.is_symlink()
        and p.suffix in {".md", ".json", ".sh", ".txt", ".yml", ".yaml", ""}
    ]
    uncited = [
        " ".join(path)
        for path, _ in leaves
        if not any(
            re.search(r"(?:dadaia|\$D|\$DADAIA)\s+" + r"\s+".join(map(re.escape, path)) + r"\b", t)
            for t in texts
        )
    ]
    assert uncited == [], f"cite each in the one skill that owns it (dd-cli-library): {uncited}"


_LEAK = re.compile(
    r"\bFR\d|\bADR \d{4}|SPEC v\d|\bA\d+\.\d|T-\d{3}-\d|\bv\d+\.\d+\.\d+\b|container\.|cli-no-infrastructure"
)


def test_no_command_help_leaks_an_internal_id() -> None:
    """cli-help-leaks-internal-spec-ids: every rendered --help states behaviour in the reader's
    words — no requirement, task or audit id, no code seam name."""
    leaks = [
        f"{' '.join(p) or '<root>'}: {m.group(0)!r}"
        for p, _ in _tree()
        for m in _LEAK.finditer(_help(*p))
    ]
    assert leaks == [], "\n".join(leaks)


@pytest.mark.parametrize(
    ("argv", "present", "absent", "at_most_once"),
    [
        # bind carries no retired-flag history
        pytest.param(("context", "bind"), (), ("--mode", "--release", "--force", "--reason", "0.4.7"), (), id="bind-no-history"),
        pytest.param(("ci", "push-gate-check"), (), (), ("dd-gitflow-default",), id="push-gate-branch-model-once"),
    ],
)  # fmt: skip
def test_help_states_current_behaviour(
    argv: tuple[str, ...],
    present: tuple[str, ...],
    absent: tuple[str, ...],
    at_most_once: tuple[str, ...],
) -> None:
    """help-texts-and-bug-schema-cite-behaviour-that-is-gone."""
    text = _help(*argv)
    assert [w for w in present if w not in text] == []
    assert [w for w in absent if w in text] == []
    assert [w for w in at_most_once if text.count(w) > 1] == []


def test_reports_validate_help_shows_each_example_once() -> None:
    output = CliRunner().invoke(app, ["reports", "validate", "--help"], env=_ENV).output
    lines = [ln.strip() for ln in output.splitlines() if "--all" in ln and "validate" in ln]
    assert len(lines) == len(set(lines)), lines


def test_capabilities_json_matches_service_and_public_schema() -> None:
    """`capabilities --json` is the service payload and validates against the v3 schema; it pins
    context safety and names verbs, never a hand-spelled `dadaia ` command
    (sa-fix-lines-not-built-by-cli-line#S7)."""
    result = CliRunner().invoke(app, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload == build_capabilities(command_paths())
    schema = json.loads(
        (_PUBLIC / "schemas" / "dadaia-capabilities-v3.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    assert "workflows" not in payload
    assert payload["contexts"]["selection_contract"] == "explicit-or-caller-owned-bind"
    assert payload["consumer_requirements"]["exact_provider_version"] is True
    assert payload["certification"] == {"schema_version": "dadaia-certification-v1"}
    assert "dadaia " not in json.dumps(payload)


def test_every_advertised_verb_and_harness_exists() -> None:
    """capabilities-advertises-verbs-and-surfaces-that-do-not-exist: each advertised verb is a
    path of the live tree, and the harness list is the harness registry."""
    payload = build_capabilities(command_paths())
    live = command_paths()
    contexts, surfaces = payload["contexts"], payload["surfaces"]
    assert "modes" not in contexts and "heartbeat" not in contexts["commands"]
    assert {("context", verb) for verb in contexts["commands"]} <= live
    assert {(group, verb) for group, verbs in surfaces.items() for verb in verbs} <= live
    assert "panel" not in surfaces
    assert payload["harnesses"]["layer_1"] == list(L1_ENTRY_HARNESSES)


def test_every_help_example_renders_the_venv_cli() -> None:
    """help-examples-spell-the-blocked-bare-cli: the gate blocks a bare `dadaia` first token,
    so a command path in any --help follows only the `fix_line` rendering of the CLI."""
    leaf = "|".join(r"\s+".join(p) for p in sorted(command_paths(), key=len, reverse=True) if p)
    bare = re.compile(rf"(?<!Usage: )\bdadaia\s+(?:{leaf})(?=[\s'\"`]|$)")
    hits = [
        f"{' '.join(p) or '<root>'}: {m.group(0)!r}"
        for p, _ in _tree()
        for m in bare.finditer(_help(*p).replace(fix_line(None), "<cli>"))
    ]
    assert hits == [], "\n".join(hits)
