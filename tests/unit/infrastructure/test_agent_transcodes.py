"""Intent: CONTRACT — AC3.1: each newly registered harness projects exactly its own view.

The three records added here are data rows, so the only thing worth asserting is what
each row makes the table emit: the directory it touches, the agent files it owns, and —
the part a golden of the whole table states weakly — that it owns nothing else.

``devin`` is the interesting row: its transcode declares that Devin reads the authored
``.agents/agents`` tree natively, so its builder yields ZERO rules. That is asserted
here rather than left implicit, because "no rules" is the claim, not an oversight.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS, L1_ENTRY_HARNESSES
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.projection_rules import projection_rules
from dadaia_workspace.infrastructure.public_assets_common import OverwritePolicy, iter_public_files

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"


def _rows(workspace_root: Path, harness: str) -> list[tuple[str, str]]:
    """(label, root-relative dst) for the rules *harness* alone contributes."""
    plan = InstallPlan(
        workspace_root=workspace_root,
        agentic_dir=_PUBLIC,
        target=harness,
        scope="all",
        only=None,
        overwrite=OverwritePolicy.PRESERVE,
        guardrail_targets=frozenset(),
        harness_targets=(harness,),
        active_harnesses=frozenset({harness}),
        overlay=None,
        resolved_models={},
    )
    return sorted(
        (rule.label, rule.dst.relative_to(workspace_root).as_posix())
        for rule in projection_rules(plan)
        if rule.harness == harness
    )


def _authored_agent_names() -> list[str]:
    return sorted(path.stem for path in (_PUBLIC / "agents").glob("*.md"))


def test_cursor_projects_one_link_per_authored_persona_and_nothing_else(tmp_path: Path) -> None:
    rows = _rows(tmp_path, "cursor")
    expected = sorted(
        (
            f"cursor:agents/{src.relative_to(_PUBLIC / 'agents').as_posix()}",
            f".cursor/agents/{src.relative_to(_PUBLIC / 'agents').as_posix()}",
        )
        for src in iter_public_files(_PUBLIC / "agents")
    )
    assert rows == expected
    assert all(
        rule.link_to is not None
        for rule in projection_rules(
            InstallPlan(
                workspace_root=tmp_path,
                agentic_dir=_PUBLIC,
                target="cursor",
                scope="all",
                only=None,
                overwrite=OverwritePolicy.PRESERVE,
                guardrail_targets=frozenset(),
                harness_targets=("cursor",),
                active_harnesses=frozenset({"cursor"}),
                overlay=None,
                resolved_models={},
            )
        )
        if rule.harness == "cursor"
    ), "a cursor persona view is a link onto the authored set, never a second copy"


def test_devin_projects_nothing_because_it_reads_the_authored_tree_natively(
    tmp_path: Path,
) -> None:
    assert _rows(tmp_path, "devin") == []


def test_copilot_renders_one_agent_markdown_per_authored_persona(tmp_path: Path) -> None:
    rows = _rows(tmp_path, "copilot")
    assert rows == sorted(
        (f"copilot:agents/{name}.agent.md", f".github/agents/{name}.agent.md")
        for name in _authored_agent_names()
    )
    assert all(not dst.startswith(".github/workflows") for _, dst in rows)


def test_the_copilot_transcode_keeps_only_the_frontmatter_copilot_reads(tmp_path: Path) -> None:
    """A Copilot custom agent is `name`/`description`/optional `tools` plus the body —
    the dadaia dispatch fields are not its vocabulary, so the bytes differ from the
    authored file and the rule is a transcode, not a link."""
    plan_rules = [
        rule
        for rule in projection_rules(
            InstallPlan(
                workspace_root=tmp_path,
                agentic_dir=_PUBLIC,
                target="copilot",
                scope="all",
                only=None,
                overwrite=OverwritePolicy.PRESERVE,
                guardrail_targets=frozenset(),
                harness_targets=("copilot",),
                active_harnesses=frozenset({"copilot"}),
                overlay=None,
                resolved_models={},
            )
        )
        if rule.label.endswith("dd-software-engineer.agent.md")
    ]
    assert len(plan_rules) == 1
    rule = plan_rules[0]
    assert rule.link_to is None
    text = rule.render(None).decode("utf-8")
    head, _, body = text[4:].partition("\n---\n")
    keys = [line.split(":", 1)[0] for line in head.splitlines() if not line.startswith((" ", "-"))]
    assert keys == ["name", "description", "tools"]
    assert "dispatch_band" not in head and "model" not in head
    assert body.lstrip().startswith("# Software Engineer")


@pytest.mark.parametrize("harness", ["cursor", "devin", "copilot"])
def test_each_new_record_is_registered_with_a_directory_and_a_hook_format(harness: str) -> None:
    record = HARNESS_RECORDS[harness]
    assert harness in L1_ENTRY_HARNESSES
    assert record.directory is not None
    assert record.hooks.value.endswith("-hooks")
