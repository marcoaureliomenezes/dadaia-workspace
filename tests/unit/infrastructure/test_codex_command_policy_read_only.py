"""Intent: CONTRACT — sa-codex-policy-allows-write-capable-commands (0.5.0 WP-13, AC1.5).

#B1: the rendered Codex ``.rules`` allows no write- or exec-capable prefix: an unprompted
command is one of ``rg``, ``ls``, ``cat``, or ``sed -n`` (git diff/log/show take ``--output``, a write).
Size: SMALL (parses the rendered text, no codex binary).
"""

from __future__ import annotations

import ast
import itertools
import re

import pytest

from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _render_codex_command_policy_rules,
)

pytestmark = pytest.mark.unit

_RULE = re.compile(r"prefix_rule\((.*?)\n\)", re.S)
_FIELD = re.compile(r"^\s*(\w+) = (.*?),?$", re.M)


def _allowed_prefixes() -> set[tuple[str, ...]]:
    """Every argv prefix a rule with ``decision = "allow"`` expands to."""
    allowed: set[tuple[str, ...]] = set()
    for body in _RULE.findall(_render_codex_command_policy_rules()):
        fields = {k: v for k, v in _FIELD.findall(body)}
        if ast.literal_eval(fields["decision"]) != "allow":
            continue
        tokens = [t if isinstance(t, list) else [t] for t in ast.literal_eval(fields["pattern"])]
        allowed.update(itertools.product(*tokens))
    return allowed


def test_b1_the_allow_set_is_read_only() -> None:
    assert _allowed_prefixes() == {
        ("rg",),
        ("ls",),
        ("cat",),
        ("sed", "-n"),
    }
