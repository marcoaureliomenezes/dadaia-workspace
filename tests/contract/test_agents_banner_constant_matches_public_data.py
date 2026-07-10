"""FR9 contract (v0.1.60 / Ruling 15) — the banner constant is byte-equal to public/data.

``workspace_guardrail._CANONICAL_AGENTS_BANNER`` is the provenance discriminator for the
consumer-repo AGENTS.md fan-out. It is a FIXED LITERAL (never a runtime read of
``public/data``); this contract asserts it is byte-equal to the actual leading banner block
of ``dadaia_workspace/public/data/AGENTS.md``. Drift on EITHER side fails here — so the
constant and the shipped banner can never silently diverge (which would either re-open the
clobber bug or start clobbering real projections).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.infrastructure.workspace_guardrail import _CANONICAL_AGENTS_BANNER

pytestmark = pytest.mark.contract

_PUBLIC_DATA_AGENTS = (
    Path(dadaia_workspace.__file__).resolve().parent / "public" / "data" / "AGENTS.md"
)


def test_banner_constant_matches_public_data_agents_md() -> None:
    text = _PUBLIC_DATA_AGENTS.read_text(encoding="utf-8")
    # The shipped file must begin with the constant, byte-for-byte.
    assert text.startswith(_CANONICAL_AGENTS_BANNER), (
        "public/data/AGENTS.md no longer starts with _CANONICAL_AGENTS_BANNER — the "
        "provenance discriminator drifted from the shipped banner."
    )
    # And the constant must be EXACTLY the leading '>' banner block (no more, no less):
    # reconstruct the leading blockquote block from the file and compare byte-for-byte.
    banner_block = ""
    for line in text.splitlines(keepends=True):
        if line.startswith(">"):
            banner_block += line
        else:
            break
    assert banner_block == _CANONICAL_AGENTS_BANNER, (
        "the banner constant must equal the full leading blockquote block byte-for-byte.\n"
        f"  constant:\n{_CANONICAL_AGENTS_BANNER!r}\n  file block:\n{banner_block!r}"
    )
    # Subsumed non-trivial-literal guard: byte-equality above already fails loudly if the
    # constant were accidentally blanked or truncated.
    assert _CANONICAL_AGENTS_BANNER.startswith("> **AI agent rules.**")
    assert _CANONICAL_AGENTS_BANNER.count("\n") == 4
