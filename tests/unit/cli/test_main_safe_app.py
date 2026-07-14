"""The CLI entry point surfaces failures without creating legacy bug state."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def test_safe_app_propagates_unexpected_failure() -> None:
    from dadaia_workspace.cli.main import _safe_app

    with patch("dadaia_workspace.cli.main.app", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            _safe_app()
