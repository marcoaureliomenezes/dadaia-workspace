"""ReposService — reads the consultive repos catalog."""

from pathlib import Path

from dadaia_workspace.core.protocols.storage import ExcelReader


class ReposService:
    def __init__(self, excel_reader: ExcelReader) -> None:
        self._reader = excel_reader

    def list_known(self, workspace_root: Path) -> list[dict[str, str]]:
        catalog = workspace_root / "repos.xlsx"
        return self._reader.read_rows(catalog)
