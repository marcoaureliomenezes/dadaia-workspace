"""Intent: CONTRACT — `specs upgrade` rewrites the retired Portuguese status tokens in the
live release trio (0.4.7 FR4 / T-047-58), and never inside published history. Size: SMALL."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.upgrade import (
    plan_status_token_rewrites,
    rewrite_status_tokens,
)

pytestmark = pytest.mark.unit


def _trio(root: Path, status: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (root / name).write_text(f"# doc\n\n> **Status:** {status}\n", encoding="utf-8")


# fmt: off
@pytest.mark.parametrize(("dirs", "expected"), [
    pytest.param({"0.4.7": "Aprovado", "0.4.7/rc-1": "Em revisão", "0.4.7/rc-2": "Rascunho"},
                 {"0.4.7": "Approved", "0.4.7/rc-1": "In review", "0.4.7/rc-2": "Draft"}, id="live-root-and-rc-folders"),
    pytest.param({"0.9.9": "Em revisao"}, {"0.9.9": "In review"}, id="accent-stripped-worker-spelling"),
    pytest.param({"_archive/0.4.6": "Aprovado", "_archive/0.4.6/rc-1": "Aprovado"}, {}, id="published-archive-never-rewritten"),
    pytest.param({"0.4.7": "Approved"}, {}, id="already-english-no-op"),
])
# fmt: on
def test_upgrade_rewrites_retired_status_tokens_only_in_the_live_trio(tmp_path: Path, dirs: dict[str, str], expected: dict[str, str]) -> None:
    for rel, status in dirs.items():
        _trio(tmp_path / "releases" / rel, status)
    touched = {tmp_path / "releases" / rel / n for rel in expected for n in ("SPEC.md", "PLAN.md", "TASKS.md")}

    assert set(plan_status_token_rewrites(tmp_path)) == touched
    assert set(rewrite_status_tokens(tmp_path)) == touched
    for rel, status in dirs.items():
        text = (tmp_path / "releases" / rel / "PLAN.md").read_text(encoding="utf-8")
        assert text.splitlines()[2] == f"> **Status:** {expected.get(rel, status)}"
