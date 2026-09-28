"""The reaper's holds die only at their TTL — text and source contracts.

Intent: CONTRACT — sa-reaper-destroys-its-own-hold-before-ttl#B6 (#B8 is a row of test_core_file_io_purity). Size: SMALL.
"""

from __future__ import annotations

from pathlib import Path

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"


def test_the_cli_skill_never_claims_expired_only_spares_slop() -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B6."""
    text = (_PKG / "public" / "skills" / "dd-cli-library" / "SKILL.md").read_text(encoding="utf-8")
    assert "without touching slop" not in text
    assert "`--expired-only` narrows only the report" in text
