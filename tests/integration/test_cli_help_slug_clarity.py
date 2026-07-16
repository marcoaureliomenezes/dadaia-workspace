"""CLI help must render the slug/id constraint intelligibly.

Bug (found by the dd-chain-capture Hermes consumer, recipe F-22 clareza): a Typer
Option/Argument help string that embeds a regex like ``^[a-z][a-z0-9-]+$`` is rendered
through Rich markup mode, which interprets ``[a-z]`` / ``[a-z0-9-]`` as style tags and
EATS them — the consumer sees ``Must match ^+$.``, a meaningless pattern. The help must
convey the real constraint (lowercase kebab-case) and must NOT show the mangled form.
"""

from __future__ import annotations

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

# (argv-to-help, must-not-contain-mangled, must-contain-any-of)
_CASES = [
    (["backlog", "new", "--help"], "^+$", ("a-z0-9", "kebab")),
    (["memory", "product", "add", "--help"], "^+$", ("a-z0-9", "kebab")),
    (["release", "new", "--help"], "^+$", ("a-z0-9", "kebab")),
]


def _help_text(argv: list[str]) -> str:
    result = _runner.invoke(app, argv)
    assert result.exit_code == 0, f"{argv} exited {result.exit_code}: {result.output}"
    return result.output


def test_slug_help_is_not_mangled_by_rich_markup() -> None:
    for argv, mangled, wanted in _CASES:
        out = _help_text(argv)
        # collapse the box-drawing wraps so a pattern split across lines still matches
        flat = out.replace("\n", " ").replace("│", " ")
        assert mangled not in flat, f"{argv}: help shows mangled regex {mangled!r}: {out}"
        assert any(w in flat for w in wanted), (
            f"{argv}: help does not convey the slug constraint (want one of {wanted}): {out}"
        )
