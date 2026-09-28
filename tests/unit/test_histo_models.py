"""Intent: CONTRACT — the backlog doctor's BL-STALE vocabulary: ``is_terminal_disposition``
reads the one terminal vocabulary. Size: SMALL.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.histo import (
    TERMINAL_DISPOSITIONS,
    is_terminal_disposition,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("token", [*TERMINAL_DISPOSITIONS, "Delivered", " REJECTED "])
def test_is_terminal_disposition_accepts_the_one_vocabulary(token: str) -> None:
    assert is_terminal_disposition(token)


@pytest.mark.parametrize("token", [None, "", "picked", "candidate", "idea"])
def test_is_terminal_disposition_refuses_a_live_status(token: str | None) -> None:
    assert not is_terminal_disposition(token)
