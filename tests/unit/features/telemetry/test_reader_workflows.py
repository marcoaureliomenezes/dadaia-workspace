"""Unit tests for features/telemetry/reader/workflows.py (T-AM-09).

All fixtures are synthesized in tmp_path — no real workspace skill files are read.
"""
from __future__ import annotations

import pathlib
import sqlite3

import pytest

from dadaia_workspace.features.telemetry.reader.workflows import ReadResult, read_workflows
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

NOW_ISO = "2026-05-17T10:00:00Z"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dao() -> TelemetryDao:
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    return TelemetryDao(conn)


def _count_table(dao: TelemetryDao, table: str) -> int:
    row = dao._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: SLF001
    return row[0]


def _make_skill_file(
    workspace: pathlib.Path,
    skill_dir_rel: str,
    skill_name: str,
    content: str,
) -> pathlib.Path:
    """Write a SKILL.md file at <workspace>/<skill_dir_rel>/<skill_name>/SKILL.md."""
    skill_dir = workspace / skill_dir_rel / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


_VALID_FRONTMATTER = """\
---
name: sample-workflow
description: Orchestrates multi-agent discovery pattern.
applyTo: product-engineer
---

# Sample Workflow

This skill is used by the software-architect and product-engineer agents.
"""

_NO_FRONTMATTER = """\
# No Frontmatter

This skill has no YAML frontmatter block at all.
"""

_MISSING_NAME = """\
---
description: A workflow without a name field.
applyTo: qa-engineer
---

Body text.
"""

_VALID_NO_APPLY_TO = """\
---
name: minimal-workflow
description: A minimal workflow with no applyTo.
---

Body of the minimal workflow. Used by qa-engineer.
"""

_LIST_APPLY_TO = """\
---
name: multi-apply-workflow
description: Has applyTo as a list.
applyTo: [software-engineer, product-engineer]
---

Multi apply workflow body.
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_parses_frontmatter(self, tmp_path: pathlib.Path) -> None:
        """Valid SKILL.md → 1 workflow ingested."""
        _make_skill_file(tmp_path, ".claude/skills", "sample", _VALID_FRONTMATTER)
        dao = _make_dao()

        result = read_workflows(tmp_path, dao, [], NOW_ISO)

        assert result.workflows_ingested == 1
        assert result.workflows_skipped == 0
        assert _count_table(dao, "workflows") == 1

        workflows = dao.list_workflows()
        assert len(workflows) == 1
        assert workflows[0].name == "sample-workflow"
        assert workflows[0].description == "Orchestrates multi-agent discovery pattern."
        assert workflows[0].apply_to == "product-engineer"


class TestMissingFrontmatter:
    def test_missing_frontmatter_skips(self, tmp_path: pathlib.Path) -> None:
        """SKILL.md with no --- block → skipped, 0 ingests."""
        _make_skill_file(tmp_path, ".claude/skills", "no-fm", _NO_FRONTMATTER)
        dao = _make_dao()

        result = read_workflows(tmp_path, dao, [], NOW_ISO)

        assert result.workflows_ingested == 0
        assert result.workflows_skipped == 1
        assert _count_table(dao, "workflows") == 0

    def test_missing_name_skips(self, tmp_path: pathlib.Path) -> None:
        """Frontmatter without 'name' field → skipped."""
        _make_skill_file(tmp_path, ".agents/skills", "no-name", _MISSING_NAME)
        dao = _make_dao()

        result = read_workflows(tmp_path, dao, [], NOW_ISO)

        assert result.workflows_ingested == 0
        assert result.workflows_skipped == 1


class TestApplyToOptional:
    def test_applyTo_optional(self, tmp_path: pathlib.Path) -> None:
        """SKILL.md without applyTo → workflow.apply_to is None."""
        _make_skill_file(tmp_path, ".claude/skills", "minimal", _VALID_NO_APPLY_TO)
        dao = _make_dao()

        read_workflows(tmp_path, dao, [], NOW_ISO)

        workflows = dao.list_workflows()
        assert len(workflows) == 1
        assert workflows[0].apply_to is None

    def test_applyTo_list_joined(self, tmp_path: pathlib.Path) -> None:
        """applyTo as a YAML list → stored as comma-joined string."""
        _make_skill_file(tmp_path, ".claude/skills", "multi", _LIST_APPLY_TO)
        dao = _make_dao()

        read_workflows(tmp_path, dao, [], NOW_ISO)

        workflows = dao.list_workflows()
        assert len(workflows) == 1
        assert workflows[0].apply_to is not None
        assert "software-engineer" in workflows[0].apply_to
        assert "product-engineer" in workflows[0].apply_to


class TestSubstringMatchAgentLink:
    def test_substring_match_agent_link(self, tmp_path: pathlib.Path) -> None:
        """Workflow body mentions 'software-architect' → workflow_agents row exists."""
        _make_skill_file(tmp_path, ".claude/skills", "sample", _VALID_FRONTMATTER)
        # Also need to pre-insert the agent so FK constraint is satisfied
        dao = _make_dao()
        from dadaia_workspace.features.telemetry.store.models import Agent
        dao.upsert_agent(
            Agent(
                name="software-architect",
                provider="claude",
                is_subagent=0,
                first_seen_at=NOW_ISO,
                last_seen_at=NOW_ISO,
            )
        )

        read_workflows(tmp_path, dao, ["software-architect", "qa-engineer"], NOW_ISO)

        row = dao._conn.execute(  # noqa: SLF001
            "SELECT * FROM workflow_agents WHERE workflow_name = ? AND agent_name = ?",
            ("sample-workflow", "software-architect"),
        ).fetchone()
        assert row is not None

    def test_no_match_for_absent_agent(self, tmp_path: pathlib.Path) -> None:
        """Agent name not in body → no workflow_agents row."""
        _make_skill_file(tmp_path, ".claude/skills", "sample", _VALID_FRONTMATTER)
        dao = _make_dao()

        read_workflows(tmp_path, dao, ["devops-engineer"], NOW_ISO)

        count = dao._conn.execute(  # noqa: SLF001
            "SELECT COUNT(*) FROM workflow_agents"
        ).fetchone()[0]
        assert count == 0

    def test_case_insensitive_match(self, tmp_path: pathlib.Path) -> None:
        """Substring match is case-insensitive."""
        content = """\
---
name: case-test-workflow
description: Tests case-insensitive match.
---

The PRODUCT-ENGINEER agent runs this workflow.
"""
        _make_skill_file(tmp_path, ".claude/skills", "case-test", content)
        dao = _make_dao()
        from dadaia_workspace.features.telemetry.store.models import Agent
        dao.upsert_agent(
            Agent(
                name="product-engineer",
                provider="claude",
                is_subagent=0,
                first_seen_at=NOW_ISO,
                last_seen_at=NOW_ISO,
            )
        )

        read_workflows(tmp_path, dao, ["product-engineer"], NOW_ISO)

        row = dao._conn.execute(  # noqa: SLF001
            "SELECT * FROM workflow_agents WHERE workflow_name = ? AND agent_name = ?",
            ("case-test-workflow", "product-engineer"),
        ).fetchone()
        assert row is not None


class TestWalksBothDirs:
    def test_walks_both_dirs(self, tmp_path: pathlib.Path) -> None:
        """Both .claude/skills/foo/SKILL.md and .agents/skills/bar/SKILL.md → 2 workflows."""
        content_a = """\
---
name: workflow-alpha
description: Alpha workflow from .claude.
---

Alpha body.
"""
        content_b = """\
---
name: workflow-beta
description: Beta workflow from .agents.
---

Beta body.
"""
        _make_skill_file(tmp_path, ".claude/skills", "foo", content_a)
        _make_skill_file(tmp_path, ".agents/skills", "bar", content_b)
        dao = _make_dao()

        result = read_workflows(tmp_path, dao, [], NOW_ISO)

        assert result.workflows_ingested == 2
        assert _count_table(dao, "workflows") == 2

        names = {wf.name for wf in dao.list_workflows()}
        assert names == {"workflow-alpha", "workflow-beta"}


class TestIdempotentReread:
    def test_idempotent_reread(self, tmp_path: pathlib.Path) -> None:
        """Running twice with same content → still 1 row per workflow."""
        _make_skill_file(tmp_path, ".claude/skills", "sample", _VALID_FRONTMATTER)
        dao = _make_dao()

        result1 = read_workflows(tmp_path, dao, [], NOW_ISO)
        assert result1.workflows_ingested == 1

        result2 = read_workflows(tmp_path, dao, [], NOW_ISO)
        assert result2.workflows_ingested == 1

        assert _count_table(dao, "workflows") == 1


class TestEmptySkillDirs:
    def test_no_skill_dirs_returns_empty(self, tmp_path: pathlib.Path) -> None:
        """Workspace with no .claude/skills or .agents/skills → 0 ingests."""
        dao = _make_dao()
        result = read_workflows(tmp_path, dao, [], NOW_ISO)
        assert result.workflows_ingested == 0
        assert result.workflows_skipped == 0
