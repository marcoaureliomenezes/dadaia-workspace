"""SPEC-DOC-034 — constitution must cite, never enumerate, the runtime/harness roster.

The AgentRuntimeKind roster is product truth that lives in ``specs/memory/tech-stack.md``
(anchor ``agent-runtimes``); the constitution may only cite it. This check fails when the
constitution hard-codes concrete runtime-kind tokens or a roster-size count, so the
duplicated roster cannot silently go stale when a kind is added/removed (recurrence guard
for the v0.1.42 single-source rewrite).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor import Severity, SpecsDoctor, SpecsDoctorIssue


def _enumeration_issues(specs_dir: Path) -> list[SpecsDoctorIssue]:
    return SpecsDoctor(specs_dir)._check_constitution_no_runtime_enumeration()  # noqa: SLF001


def _write_constitution(specs_dir: Path, body: str) -> None:
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "constitution.md").write_text(body, encoding="utf-8")


def test_constitution_enumerating_kind_tokens_is_error(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    _write_constitution(
        specs_dir,
        "# Constitution\n\n"
        "The Layer-2 worker runtimes are FAKE, CODEX_EXEC, CLAUDE_SDK and PI_HEADLESS.\n",
    )

    issues = _enumeration_issues(specs_dir)

    assert [(issue.code, issue.severity) for issue in issues] == [("SPEC-DOC-034", Severity.ERROR)]
    assert "tech-stack" in issues[0].description


def test_constitution_naming_retired_kind_token_is_error(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    _write_constitution(
        specs_dir,
        "# Constitution\n\nKinds: CLAUDE_SDK and the removed OPENCODE_RUN are listed.\n",
    )

    issues = _enumeration_issues(specs_dir)

    assert [issue.code for issue in issues] == ["SPEC-DOC-034"]
    assert "OPENCODE_RUN" in issues[0].description


def test_constitution_enumerating_roster_size_count_is_error(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    _write_constitution(
        specs_dir,
        "# Constitution\n\nThere are five AgentRuntimeKinds in the worker layer.\n",
    )

    issues = _enumeration_issues(specs_dir)

    assert [(issue.code, issue.severity) for issue in issues] == [("SPEC-DOC-034", Severity.ERROR)]
    assert "five AgentRuntimeKinds" in issues[0].description


def test_constitution_citing_memory_is_clean(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    _write_constitution(
        specs_dir,
        "# Constitution\n\n"
        "The canonical Layer-2 worker runtime/harness roster lives in memory "
        "(`specs/memory/tech-stack.md`, anchor `agent-runtimes`); the constitution "
        "cites it and never duplicates it.\n",
    )

    assert _enumeration_issues(specs_dir) == []


def test_single_incidental_kind_token_does_not_trip(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    _write_constitution(
        specs_dir,
        "# Constitution\n\n"
        "A dry-run uses the FAKE runtime; the full roster is in `[[tech-stack]]`.\n",
    )

    assert _enumeration_issues(specs_dir) == []


def test_missing_constitution_is_noop(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir(parents=True)

    assert _enumeration_issues(specs_dir) == []
