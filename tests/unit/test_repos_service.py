"""Unit tests for ReposService."""

from pathlib import Path

from dadaia_workspace.features.repos.service import ReposService
from tests.fakes import FakeExcelReader


def test_list_known_rows_absent_catalog_empty_and_canonical_path(tmp_path: Path) -> None:
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

    empty_svc = ReposService(excel_reader=FakeExcelReader())
    assert empty_svc.list_known(tmp_path) == []

    # ReposService reads the staged canonical asset; no duplicate .dadaia/src exists.
    expected_path = tmp_path / ".dadaia" / "agentic" / "data" / "repos.xlsx"
    captured_paths: list[Path] = []

    class CapturingReader:
        def read_rows(self, file_path: Path) -> list[dict[str, str]]:
            captured_paths.append(file_path)
            return []

    canonical_svc = ReposService(excel_reader=CapturingReader())
    canonical_svc.list_known(tmp_path)
    assert captured_paths == [expected_path]
