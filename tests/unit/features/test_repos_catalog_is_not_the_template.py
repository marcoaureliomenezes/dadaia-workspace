"""`repos list` must not present the shipped template's examples as real repos.

A freshly initialized workspace carries the projected `repos.xlsx` TEMPLATE, whose three
rows are placeholders (`example-service` → `github.com/your-org/example-*`). `list_known`
read that file unconditionally, so every fresh workspace reported three repos that do not
exist, indistinguishable from a real catalog (bug
`repos-list-shows-template-examples-as-real-catalog`).

The old fallback message compounded it by telling the operator to "add repos.xlsx to your
workspace root" — a path the Workspace Root Law forbids.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.repos.service import ReposService


class _FakeReader:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows

    def read_rows(self, path: Path) -> list[dict[str, str]]:
        return list(self._rows)

    # The headers below are the sheet's REAL human labels. The first version of this test
    # invented snake_case keys, so the guard it was meant to prove matched nothing and the
    # test passed against a filter that filtered nothing — a fake that could not reject.


_TEMPLATE_ROWS = [
    {"Repo Name": "example-service", "Repo URL": "https://github.com/your-org/example-service"},
    {"Repo Name": "example-web", "Repo URL": "https://github.com/your-org/example-web"},
    {"Repo Name": "example-lib", "Repo URL": "https://github.com/your-org/example-lib"},
]


def test_the_untouched_template_reports_no_repos(tmp_path: Path) -> None:
    service = ReposService(excel_reader=_FakeReader(_TEMPLATE_ROWS))  # type: ignore[arg-type]

    assert service.list_known(tmp_path) == []


def test_a_real_catalog_is_reported(tmp_path: Path) -> None:
    """The guard must not swallow a genuine catalog that happens to sit in the same file."""
    real = [
        {"Repo Name": "dd-chain-capture", "Repo URL": "https://github.com/acme/dd-chain-capture"},
        {"Repo Name": "example-service", "Repo URL": "https://github.com/acme/example-service"},
    ]
    service = ReposService(excel_reader=_FakeReader(real))  # type: ignore[arg-type]

    names = {row["Repo Name"] for row in service.list_known(tmp_path)}
    assert names == {"dd-chain-capture", "example-service"}, (
        "only the shipped placeholder ROWS are filtered — a real repo that reuses the name "
        "is kept, because the giveaway is the your-org placeholder URL, not the name"
    )


def test_a_partially_customized_catalog_keeps_the_real_rows(tmp_path: Path) -> None:
    service = ReposService(
        excel_reader=_FakeReader(
            [*_TEMPLATE_ROWS, {"Repo Name": "mine", "Repo URL": "https://github.com/acme/mine"}]
        )
    )  # type: ignore[arg-type]

    assert [row["Repo Name"] for row in service.list_known(tmp_path)] == ["mine"]
