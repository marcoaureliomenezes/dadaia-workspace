"""ReposService — reads the consultive repos catalog."""

from pathlib import Path

from dadaia_workspace.infrastructure.excel_reader import OpenpyxlExcelReader


class ReposService:
    def __init__(self, excel_reader: OpenpyxlExcelReader) -> None:
        self._reader = excel_reader

    def list_known(self, workspace_root: Path) -> list[dict[str, str]]:
        catalog = workspace_root / ".dadaia" / "agentic" / "data" / "repos.xlsx"
        return self._reader.read_rows(catalog)
