"""v0.5.1 T-051-22 rework: MEM-DRIFT-1, the features package-map
diagram in ARCHITECTURE.md vs the live ``dadaia_workspace/features`` packages (bug
push-gate-test-pins-memory-package-count-that-only-closure-may-change).

The live-package introspection is monkeypatched in the table; one smoke test runs it for
real.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import doctor_memory
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

_HEADING = "### `dadaia_workspace/features` — package map ({n} packages)"


def _architecture_md(pkgs: tuple[str, ...]) -> str:
    return (
        "# Architecture\n\n## Part 2 — Implementation\n\n"
        f"{_HEADING.format(n=len(pkgs))}\n\n```mermaid\nflowchart TB\n"
        '    subgraph features["dadaia_workspace/features"]\n'
        f'      pkgs["{" · ".join(pkgs)}"]\n'
        "    end\n```\n\n### next section\n\nunrelated\n"
    )


@pytest.mark.parametrize(
    ("architecture", "live", "needle"),
    [
        pytest.param(
            _architecture_md(("panel", "spec_artifacts")),
            {"panel"},
            "spec_artifacts",
            id="stale-node",
        ),
        pytest.param(
            _architecture_md(("panel",)), {"panel", "repos"}, "repos", id="missing-live-package"
        ),
        pytest.param(_architecture_md(("panel", "repos")), {"panel", "repos"}, None, id="matching"),
        pytest.param(
            "# Architecture\n\nnothing relevant.\n",
            {"panel"},
            None,
            id="consumer-no-heading-silent",
        ),
        pytest.param(None, {"panel"}, None, id="no-architecture-md"),
    ],
)
def test_mem_drift1_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    architecture: str | None,
    live: set[str],
    needle: str | None,
) -> None:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    if architecture is not None:
        (specs / "memory" / "ARCHITECTURE.md").write_text(architecture, encoding="utf-8")
    monkeypatch.setattr(doctor_memory, "_live_feature_package_names", lambda: live)

    issues = MemoryValidator(specs).check_mem_drift1_features_package_map()

    if needle is None:
        assert issues == []
    else:
        [issue] = issues
        assert (issue.code, issue.verdict, issue.fixable) == ("MEM-DRIFT-1", "warning", False)
        assert needle in issue.message


def test_mem_drift1_real_live_introspection_returns_package_names() -> None:
    live = doctor_memory._live_feature_package_names()
    assert "specs" in live and all(isinstance(name, str) and name for name in live)
