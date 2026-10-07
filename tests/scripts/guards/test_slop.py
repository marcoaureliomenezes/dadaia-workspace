"""``v33`` reads a dotted task id whole: ``J10.S1.T1`` is one witness a dotted-id constant
reads, while a family no constant reads stays an orphan (v33-witness-cuts-dotted-task-ids)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_GUARDS = Path(__file__).resolve().parents[3] / "scripts" / "guards"
sys.path.insert(0, str(_GUARDS))
import slop  # noqa: E402

_TASK_READER = 'ID = r"J(?:\\d+|R)\\.S\\d+\\.T\\d+"\n'


class _Tree:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files

    def tracked(self, *spec: str) -> list[str]:
        return [p for p in self.files if p.startswith(spec)]

    def read(self, rel: str) -> str:
        return self.files[rel]


@pytest.mark.small
@pytest.mark.parametrize(
    ("spec", "reader", "orphans"),
    [
        pytest.param(
            "J10.S1.T1 done",
            _TASK_READER,
            "",
            id="dotted-id-read-whole",
        ),
        pytest.param("J10.S1.T1 done", "X = 1\n", "J", id="dotted-id-unread-stays-orphan"),
        pytest.param("end of J10. Next", 'R = r"J\\d+$"\n', "", id="trailing-dot-not-joined"),
        pytest.param("J1.S10.T1 done", _TASK_READER, "", id="dotted-id-joined-leftwards"),
    ],
)
def test_v33_dotted_task_id_is_one_witness(
    monkeypatch: pytest.MonkeyPatch, spec: str, reader: str, orphans: str
) -> None:
    monkeypatch.setattr(slop, "V33_ORPHANS", 0)
    tree = _Tree({"specs/a.md": spec, "tests/test_r.py": reader})
    expected = [f"orphan-families: 1 > 0: ['{orphans}']"] if orphans else []
    assert slop.v33(tree) == expected  # type: ignore[arg-type]
