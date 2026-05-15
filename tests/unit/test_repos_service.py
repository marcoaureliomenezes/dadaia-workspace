"""Unit tests for ReposService."""

from pathlib import Path

from dadaia_workspace.features.repos.service import ReposService
from tests.fakes import FakeExcelReader


def test_list_known_returns_rows_from_reader(tmp_path: Path) -> None:
    reader = FakeExcelReader(
        rows=[
            {"Repo Name": "alpha", "Repo URL": "https://x/alpha.git"},
            {"Repo Name": "beta", "Repo URL": "https://x/beta.git"},
        ]
    )
    svc = ReposService(excel_reader=reader)
    rows = svc.list_known(tmp_path)
    assert len(rows) == 2
    assert {r["Repo Name"] for r in rows} == {"alpha", "beta"}


def test_list_known_returns_empty_when_catalog_absent(tmp_path: Path) -> None:
    reader = FakeExcelReader()
    svc = ReposService(excel_reader=reader)
    assert svc.list_known(tmp_path) == []


def test_list_known_reads_from_dadaia_src_path(tmp_path: Path) -> None:
    """ReposService must read repos.xlsx from .dadaia/src/."""
    expected_path = tmp_path / ".dadaia" / "src" / "repos.xlsx"

    captured_paths: list[Path] = []

    class CapturingReader:
        def read_rows(self, file_path: Path) -> list[dict[str, str]]:
            captured_paths.append(file_path)
            return []

    svc = ReposService(excel_reader=CapturingReader())
    svc.list_known(tmp_path)
    assert captured_paths == [expected_path]
