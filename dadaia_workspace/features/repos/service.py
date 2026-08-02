"""ReposService — reads the consultive repos catalog."""

from pathlib import Path

from dadaia_workspace.core.protocols.storage import ExcelReader

#: The placeholder host the shipped `repos.xlsx` template uses for its example rows. A row
#: still pointing there was never authored by the operator — it is the template speaking.
#:
#: Every fresh workspace carries the projected template, so reading the file unconditionally
#: reported three repos that do not exist, indistinguishable from a real catalog (bug
#: ``repos-list-shows-template-examples-as-real-catalog``). Filtering on the placeholder URL
#: rather than the example NAMES matters: an operator may legitimately own a repo called
#: `example-service`, and only the URL says whether the row was ever filled in.
_TEMPLATE_URL_MARKER = "github.com/your-org/"


class ReposService:
    def __init__(self, excel_reader: ExcelReader) -> None:
        self._reader = excel_reader

    def list_known(self, workspace_root: Path) -> list[dict[str, str]]:
        """The repos the OPERATOR catalogued — never the shipped template's examples."""
        catalog = workspace_root / ".dadaia" / "agentic" / "data" / "repos.xlsx"
        # Key-agnostic on purpose: the sheet's headers are the human labels the operator
        # sees ("Repo URL"), not snake_case field names. Reading a fixed key silently
        # matched nothing and filtered nothing — the shape the guard assumed did not exist.
        return [
            row
            for row in self._reader.read_rows(catalog)
            if not any(_TEMPLATE_URL_MARKER in str(value) for value in row.values())
        ]
