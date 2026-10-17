"""``_toml_escape`` is the one TOML string encoder: every value round-trips through ``tomllib``."""

from __future__ import annotations

import tomllib

import pytest

from dadaia_workspace.infrastructure.public_assets_common import _toml_escape


@pytest.mark.parametrize(
    "value",
    [
        "plain",
        'say "hi"',
        "it's",
        "caf\u00e9 \u2603",
        "a\\b",
        "a\\b\nc",
        "a\nb",
        'a\n"""b',
        'a\nb"',
        "\x01",
        "\x7f",
        "a\x01\nb\x7f",
        "a\rb\nc",
    ],
)
def test_toml_escape_round_trips(value: str) -> None:
    assert tomllib.loads(f"k = {_toml_escape(value)}\n") == {"k": value}


@pytest.mark.parametrize(
    ("value", "text"),
    [("plain", '"plain"'), ('a"b', '"a\\"b"'), ("a\nb", '"""a\nb"""')],
)
def test_toml_escape_keeps_the_shapes_codex_projects(value: str, text: str) -> None:
    assert _toml_escape(value) == text
