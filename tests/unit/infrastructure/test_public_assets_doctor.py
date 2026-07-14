"""Doctor-time behavior extracted from ``public_assets`` (T-2, v0.1.75 split of
``test_public_assets.py`` by concern — 3/4: doctor).

Covers: the ``_compare``/``_compare_content`` primitives, ``doctor()`` status matrix
(missing-manifest raises / [ok] / [drift] / CLAUDE.md-stub check), the git-dirty check
(dirty lines / no-dirty / not-a-repo / git-not-found / timeout), read-only doctor
behavior, ``list_all()``, ``_runtime_expectations`` (including the
no-consumer-yield regression), and the D-CX-1..6 doctor-check matrix (one function per
check, each already carrying its own accept/reject param table).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _make_agent_md(
    name: str, model: str = "claude-sonnet-4-6", tools: list[str] | None = None
) -> str:
    tools_block = ""
    if tools:
        items = "\n".join(f"  - {t}" for t in tools)
        tools_block = f"tools:\n{items}\n"
    return f"---\nname: {name}\nmodel: {model}\n{tools_block}---\n# Body of {name}\n"


def _register_context(workspace_root: Path, slug: str, state: str = "alive") -> None:
    states_dir = workspace_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True, exist_ok=True)
    registry = states_dir / "spec_contexts.json"
    data = (
        json.loads(registry.read_text(encoding="utf-8"))
        if registry.exists()
        else {"schema_version": "2", "contexts": []}
    )
    data["contexts"].append(
        {
            "name": slug,
            "state": state,
            "repo_slug": slug,
            "repo_url": f"https://example.test/{slug}.git",
            "created_at": "2026-07-04T00:00:00Z",
            "alive_since": "2026-07-04T00:00:00Z" if state == "alive" else None,
            "dead_since": None if state == "alive" else "2026-07-04T00:00:00Z",
            "current_branch": "main",
        }
    )
    registry.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _add_marker_consumer(workspace_root: Path, slug: str, pkg_version: str = "0.0.1") -> Path:
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1", "package_version": pkg_version}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _register_context(workspace_root, slug)
    return consumer


def _build_minimal_agentic_dir(tmp_path: Path) -> tuple[Path, Path]:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "1",
        "package_version": "0.0.0-test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "assets": [],
    }
    (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return agentic_dir, workspace_root


def _make_manager_with_fake_public(public_dir: Path) -> FileSystemPublicAssetManager:
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir
    return manager


def _make_minimal_workspace(tmp_path: Path) -> tuple[Path, Path]:
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "1",
        "package_version": "0.0.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "assets": [],
    }
    (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return public_dir, workspace_root


# ---------------------------------------------------------------------------
# doctor() — status matrix + CLAUDE.md-stub check, plus the _compare /
# _compare_content primitives doctor() is built on.
# ---------------------------------------------------------------------------


def test_doctor_status_matrix(tmp_path: Path) -> None:
    from dadaia_workspace.core.exceptions import PublicAssetError

    compare_manager = FileSystemPublicAssetManager()
    cmp_src = tmp_path / "src.txt"
    cmp_dst = tmp_path / "dst.txt"
    cmp_content = b"hello\n"
    cmp_src.write_bytes(cmp_content)
    cmp_dst.write_bytes(cmp_content)
    assert compare_manager._compare(cmp_src, cmp_dst, "test:label") == "[ok] test:label"

    cmp_src.write_bytes(b"aaa")
    cmp_dst.write_bytes(b"bbb")
    assert compare_manager._compare(cmp_src, cmp_dst, "test:label") == "[drift] test:label"

    assert (
        compare_manager._compare(cmp_src, tmp_path / "absent.txt", "test:label")
        == "[missing] test:label"
    )

    cmp_dst2 = tmp_path / "out.txt"
    cmp_dst2.write_text("hello\n", encoding="utf-8")
    assert compare_manager._compare_content("hello\n", cmp_dst2, "lbl") == "[ok] lbl"
    assert compare_manager._compare_content("different\n", cmp_dst2, "lbl") == "[drift] lbl"
    assert compare_manager._compare_content("x", tmp_path / "no.txt", "lbl") == "[missing] lbl"

    # missing public_dir -> raises
    missing_manager = _make_manager_with_fake_public(tmp_path / "nonexistent")
    with pytest.raises(PublicAssetError, match="not found"):
        missing_manager.doctor(tmp_path)

    # missing manifest -> [missing] stage:manifest.json
    public_dir_a = tmp_path / "public-a"
    public_dir_a.mkdir()
    workspace_a = tmp_path / "workspace-a"
    workspace_a.mkdir()
    (workspace_a / ".dadaia" / "agentic").mkdir(parents=True)
    manager_a = _make_manager_with_fake_public(public_dir_a)
    reports_a = manager_a.doctor(workspace_a)
    assert "[missing] stage:manifest.json" in reports_a

    # in-sync staged file -> [ok]; modified -> [drift]
    public_dir_b = tmp_path / "public-b"
    public_dir_b.mkdir()
    (public_dir_b / "testfile.txt").write_text("content\n", encoding="utf-8")
    workspace_b = tmp_path / "workspace-b"
    workspace_b.mkdir()
    agentic_b = workspace_b / ".dadaia" / "agentic"
    agentic_b.mkdir(parents=True)
    (agentic_b / "testfile.txt").write_text("content\n", encoding="utf-8")
    (agentic_b / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "package_version": "0",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "assets": [],
            }
        ),
        encoding="utf-8",
    )
    manager_b = _make_manager_with_fake_public(public_dir_b)
    reports_b = manager_b.doctor(workspace_b)
    assert any(r == "[ok] stage:testfile.txt" for r in reports_b)

    (agentic_b / "testfile.txt").write_text("modified\n", encoding="utf-8")
    reports_b2 = manager_b.doctor(workspace_b)
    assert any(r == "[drift] stage:testfile.txt" for r in reports_b2)

    # CLAUDE.md-stub check: AGENTS.md correct, CLAUDE.md wrong -> [drift]
    public_dir_c = tmp_path / "public-c"
    public_dir_c.mkdir()
    workspace_c = tmp_path / "workspace-c"
    workspace_c.mkdir()
    agentic_c = workspace_c / ".dadaia" / "agentic"
    agentic_c.mkdir(parents=True)
    data_dir_c = agentic_c / "data"
    data_dir_c.mkdir()
    (data_dir_c / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (agentic_c / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "package_version": "0",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "assets": [],
            }
        ),
        encoding="utf-8",
    )
    (workspace_c / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (workspace_c / "CLAUDE.md").write_text("# WRONG\n", encoding="utf-8")
    manager_c = _make_manager_with_fake_public(public_dir_c)
    reports_c = manager_c.doctor(workspace_c)
    assert any("[drift]" in r and "CLAUDE.md" in r for r in reports_c)


# ---------------------------------------------------------------------------
# git-dirty check
# ---------------------------------------------------------------------------


def test_doctor_git_dirty_states_are_reported_without_side_effects(tmp_path: Path) -> None:
    """Doctor reports dirty/not-applicable states and remains a read-only diagnostic."""
    import subprocess

    public_dir, workspace_root = _make_minimal_workspace(tmp_path)
    manager = _make_manager_with_fake_public(public_dir)

    dirty_result = subprocess.CompletedProcess(
        args=["git", "diff", "--name-only", "HEAD"],
        returncode=0,
        stdout="dadaia_workspace/public/agents/data-analyst.md\ndadaia_workspace/public/rules/some-rule.md\n",
        stderr="",
    )
    with patch("subprocess.run", return_value=dirty_result):
        reports = manager.doctor(workspace_root)
    assert "[warn] git-dirty: dadaia_workspace/public/agents/data-analyst.md" in reports
    assert "[warn] git-dirty: dadaia_workspace/public/rules/some-rule.md" in reports

    clean_result = subprocess.CompletedProcess(
        args=["git", "diff", "--name-only", "HEAD"], returncode=0, stdout="", stderr=""
    )
    with patch("subprocess.run", return_value=clean_result):
        reports_clean = manager.doctor(workspace_root)
    assert [r for r in reports_clean if r.startswith("[warn] git-dirty:")] == []

    cases = [
        (
            {
                "return_value": subprocess.CompletedProcess(
                    args=["git", "diff", "--name-only", "HEAD"],
                    returncode=128,
                    stdout="",
                    stderr="fatal: not a git repository",
                )
            },
            "[not-applicable] git-dirty check (not a git repo)",
        ),
        (
            {"side_effect": FileNotFoundError("git not found")},
            "[not-applicable] git-dirty check (git not found)",
        ),
        (
            {"side_effect": subprocess.TimeoutExpired(cmd="git", timeout=5)},
            "[warn] git-dirty check timed out",
        ),
    ]
    for patch_kwargs, expected in cases:
        with patch("subprocess.run", **patch_kwargs):
            reports_case = manager.doctor(workspace_root)
        assert expected in reports_case

    assert not (workspace_root / ".dadaia" / "bugs").exists()


def test_list_all_reports_current_public_asset_categories(tmp_path: Path) -> None:
    manager_empty = FileSystemPublicAssetManager()
    manager_empty._public_dir = tmp_path / "nonexistent"
    assert manager_empty.list_all() == {}

    public_dir = tmp_path / "public"
    (public_dir / "agents").mkdir(parents=True)
    (public_dir / "skills").mkdir(parents=True)
    (public_dir / "rules").mkdir(parents=True)
    (public_dir / "agents" / "my-agent.md").write_text("# agent", encoding="utf-8")
    (public_dir / "skills" / "my-skill").mkdir()
    (public_dir / "rules" / "my-rule.md").write_text("# rule", encoding="utf-8")
    (public_dir / "README.md").write_text("# readme", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir
    result = manager.list_all()

    assert set(result.keys()) == {"agents", "skills", "rules"}
    assert "my-agent.md" in result["agents"]
    assert "my-skill" in result["skills"]
    assert "my-rule.md" in result["rules"]
    assert "README.md" not in result  # non-directories at root are skipped


# ---------------------------------------------------------------------------
# _runtime_expectations
# ---------------------------------------------------------------------------


def test_runtime_expectations(tmp_path: Path) -> None:
    manager = FileSystemPublicAssetManager()

    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    no_agents = list(manager._runtime_expectations(agentic_dir, workspace_root))
    assert "root:AGENTS.md" not in [t[2] for t in no_agents]

    data_dir = agentic_dir / "data"
    data_dir.mkdir()
    (data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (data_dir / "reports-AGENTS.md").write_text("# REPORTS AGENTS\n", encoding="utf-8")
    (data_dir / "handoff-AGENTS.md").write_text("# HANDOFF AGENTS\n", encoding="utf-8")
    items = list(manager._runtime_expectations(agentic_dir, workspace_root))
    labels = [t[2] for t in items]
    assert "root:AGENTS.md" in labels
    assert "reports:AGENTS.md" in labels
    assert "handoff:AGENTS.md" in labels

    claude_md_items = [t for t in items if t[2] == "root:CLAUDE.md"]
    assert len(claude_md_items) == 1
    src, dst, label, transform = claude_md_items[0]
    assert src is None  # sentinel
    assert transform is True  # stub mode

    # FR9 no-consumer-yield regression: runtime_expectations no longer yields the
    # consumer repos/<slug>: pairs — those flow through the provenance-aware
    # _doctor_consumer_pair_lines authority instead.
    _add_marker_consumer(workspace_root, "my-repo")
    items2 = list(manager._runtime_expectations(agentic_dir, workspace_root))
    labels2 = [t[2] for t in items2]
    assert not any(label.startswith("repos/my-repo:") for label in labels2), labels2
    assert "root:AGENTS.md" in labels2

    rules_dir = agentic_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "exec.md").write_text("---\nname: exec\n---\nbody\n", encoding="utf-8")
    (rules_dir / "prose.md").write_text("# Prose rule (no frontmatter)\n", encoding="utf-8")
    items3 = list(manager._runtime_expectations(agentic_dir, workspace_root))
    codex_rule_labels = [t[2] for t in items3 if t[2].startswith("codex:rules/")]
    assert codex_rule_labels == []


# ---------------------------------------------------------------------------
# D-CX-1..6 doctor checks — one function per check.
# ---------------------------------------------------------------------------


def _dcx1_toml_present(agentic_dir: Path, workspace_root: Path) -> Path:
    agents_dir = agentic_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
    codex_dir = workspace_root / ".codex"
    codex_agents = codex_dir / "agents"
    codex_agents.mkdir(parents=True)
    (codex_agents / "my-agent.toml").write_text(
        'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\nbody\n"""\n',
        encoding="utf-8",
    )
    return codex_dir


def _dcx1_empty_agents_dir(agentic_dir: Path, workspace_root: Path) -> Path:
    (agentic_dir / "agents").mkdir()
    codex_dir = workspace_root / ".codex"
    codex_dir.mkdir()
    return codex_dir


def _dcx1_no_agents_dir(agentic_dir: Path, workspace_root: Path) -> Path:
    codex_dir = workspace_root / ".codex"
    codex_dir.mkdir()
    return codex_dir


def test_dcx1_dcx2_dcx3(tmp_path: Path) -> None:
    """D-CX-1: reports [missing] for an unprojected source agent (incl. name-parse
    fallback to stem), and nothing when every source agent already has its TOML or
    there are no source agents to project at all. D-CX-2: reports [missing] for an
    agent TOML absent from config.toml, [] once present, [] with no codex agents."""
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    agents_dir = agentic_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
    codex_dir = workspace_root / ".codex"
    codex_dir.mkdir()
    manager = FileSystemPublicAssetManager()
    out = manager._dcx1_missing_toml(agentic_dir, codex_dir)
    assert any("my-agent.toml" in line and "[missing]" in line for line in out)

    # Frontmatter-less agent falls back to using the file stem as the reported name.
    stem_agentic, stem_ws = _build_minimal_agentic_dir(tmp_path / "stem-case")
    stem_agents_dir = stem_agentic / "agents"
    stem_agents_dir.mkdir()
    (stem_agents_dir / "fallback-agent.md").write_text("# No frontmatter\n", encoding="utf-8")
    stem_codex_dir = stem_ws / ".codex"
    stem_codex_dir.mkdir()
    stem_out = manager._dcx1_missing_toml(stem_agentic, stem_codex_dir)
    assert any("fallback-agent.toml" in line and "[missing]" in line for line in stem_out)

    for i, setup in enumerate((_dcx1_toml_present, _dcx1_empty_agents_dir, _dcx1_no_agents_dir)):
        clean_agentic, clean_ws = _build_minimal_agentic_dir(tmp_path / f"clean-{i}")
        clean_codex_dir = setup(clean_agentic, clean_ws)
        assert manager._dcx1_missing_toml(clean_agentic, clean_codex_dir) == []

    dcx2_agentic, dcx2_ws = _build_minimal_agentic_dir(tmp_path / "dcx2")
    dcx2_codex_dir = dcx2_ws / ".codex"
    dcx2_codex_agents = dcx2_codex_dir / "agents"
    dcx2_codex_agents.mkdir(parents=True)
    (dcx2_codex_agents / "my-agent.toml").write_text(
        'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\nbody\n"""\n',
        encoding="utf-8",
    )
    (dcx2_codex_dir / "config.toml").write_text("", encoding="utf-8")
    dcx2_out = manager._dcx2_config_toml_entries(dcx2_agentic, dcx2_codex_dir)
    assert any("my-agent" in line and "[missing]" in line for line in dcx2_out)

    config_text = 'config_file = "agents/my-agent.toml"\n'
    (dcx2_codex_dir / "config.toml").write_text(config_text, encoding="utf-8")
    assert manager._dcx2_config_toml_entries(dcx2_agentic, dcx2_codex_dir) == []

    no_agents_agentic, no_agents_ws = _build_minimal_agentic_dir(tmp_path / "no-agents")
    no_agents_codex = no_agents_ws / ".codex"
    no_agents_codex.mkdir()
    assert manager._dcx2_config_toml_entries(no_agents_agentic, no_agents_codex) == []


def _dcx4_clean_gpt_toml(tmp_path: Path) -> Path:
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "test.toml").write_text('model = "gpt-4o"\n', encoding="utf-8")
    return codex_dir


def _dcx4_nonexistent_dir(tmp_path: Path) -> Path:
    return tmp_path / "no-such-dir"


def _dcx4_non_text_suffix(tmp_path: Path) -> Path:
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "binary.bin").write_bytes(b"claude-something")
    return codex_dir


def _dcx4_registry_tier_toml(tmp_path: Path) -> Path:
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "ai-engineer.toml").write_text(
        'developer_instructions = """\n'
        "Recommend the deep / dispatch / fast registry tiers; tune "
        "model_reasoning_effort per workload.\n"
        '"""\n',
        encoding="utf-8",
    )
    return codex_dir


def _dcx4_harness_skill_name(tmp_path: Path) -> Path:
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "ai-engineer.toml").write_text(
        'developer_instructions = """\n'
        "Use the ai-harness-claude-code skill when auditing projections.\n"
        '"""\n',
        encoding="utf-8",
    )
    return codex_dir


def _dcx4_binary_non_utf8(tmp_path: Path) -> Path:
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "bad.toml").write_bytes(b"\xff\xfe" + b"claude-" + b"\x80\x81")
    return codex_dir


def _dcx4_claude_model_string(tmp_path: Path) -> Path:
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "test.toml").write_text('model = "claude-sonnet-4-6"\n', encoding="utf-8")
    return codex_dir


def _dcx4_standalone_anthropic_tier_name(tmp_path: Path) -> Path:
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "ai-engineer.toml").write_text(
        'developer_instructions = """\nRecommend Sonnet for mid-tier work.\n"""\n',
        encoding="utf-8",
    )
    return codex_dir


@pytest.mark.parametrize(
    ("setup", "expect_clean"),
    [
        pytest.param(_dcx4_clean_gpt_toml, True, id="clean-gpt-toml"),
        pytest.param(_dcx4_nonexistent_dir, True, id="nonexistent-codex-dir"),
        pytest.param(_dcx4_non_text_suffix, True, id="non-text-suffix-skipped"),
        pytest.param(_dcx4_registry_tier_toml, True, id="registry-tier-terms-clean"),
        pytest.param(_dcx4_harness_skill_name, True, id="harness-skill-name-not-false-positive"),
        pytest.param(
            _dcx4_binary_non_utf8, True, id="binary-file-with-text-suffix-skipped-non-utf8"
        ),
        pytest.param(_dcx4_claude_model_string, False, id="claude-model-string-flagged"),
        pytest.param(
            _dcx4_standalone_anthropic_tier_name,
            False,
            id="standalone-anthropic-tier-name-flagged",
        ),
    ],
)
def test_dcx4_claude_strings(
    tmp_path: Path, setup: Callable[[Path], Path], expect_clean: bool
) -> None:
    codex_dir = setup(tmp_path)
    out = FileSystemPublicAssetManager()._dcx4_claude_strings(codex_dir)
    if expect_clean:
        assert out == []
    else:
        assert any("[error]" in line for line in out)


def test_dcx5_empty_developer_instructions(tmp_path: Path) -> None:
    manager = FileSystemPublicAssetManager()

    codex_dir1 = tmp_path / "case1" / ".codex"
    (codex_dir1 / "agents").mkdir(parents=True)
    (codex_dir1 / "agents" / "my-agent.toml").write_text(
        'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = "   "\n',
        encoding="utf-8",
    )
    out1 = manager._dcx5_empty_developer_instructions(codex_dir1)
    assert any("[error]" in line and "developer_instructions is empty" in line for line in out1)

    codex_dir2 = tmp_path / "case2" / ".codex"
    (codex_dir2 / "agents").mkdir(parents=True)
    (codex_dir2 / "agents" / "my-agent.toml").write_text(
        'name = "my-agent"\nmodel = "gpt-4o"\n', encoding="utf-8"
    )
    out2 = manager._dcx5_empty_developer_instructions(codex_dir2)
    assert any("[error]" in line for line in out2)

    codex_dir3 = tmp_path / "case3" / ".codex"
    (codex_dir3 / "agents").mkdir(parents=True)
    (codex_dir3 / "agents" / "my-agent.toml").write_text(
        'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\nYou are helpful.\n"""\n',
        encoding="utf-8",
    )
    assert manager._dcx5_empty_developer_instructions(codex_dir3) == []

    codex_dir4 = tmp_path / "case4" / ".codex"
    (codex_dir4 / "agents").mkdir(parents=True)
    (codex_dir4 / "agents" / "broken.toml").write_text("NOT VALID TOML ][[\n", encoding="utf-8")
    out4 = manager._dcx5_empty_developer_instructions(codex_dir4)
    assert any("[error]" in line and "unparseable TOML" in line for line in out4)

    codex_dir5 = tmp_path / "case5" / ".codex"
    codex_dir5.mkdir(parents=True)
    assert manager._dcx5_empty_developer_instructions(codex_dir5) == []


def test_dcx6_codex_runtime_adapters(tmp_path: Path) -> None:
    """D-CX-6: [missing]/[drift]/[leak]-to-.claude reported for the codex-only
    runtime-adapter tree; and _check_codex_drift() includes DCX6 output. The
    [leak]-to-.claude param is the sole surviving DCX6-leak coverage after
    test_codex_runtime.py's byte-duplicate copy was deleted."""

    def _mgr(public_dir: Path) -> FileSystemPublicAssetManager:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = public_dir
        return manager

    def _setup_adapter(public_dir: Path, slug: str, content: str = "# Adapter\n") -> None:
        adapter_dir = public_dir / "runtime" / "codex" / slug
        adapter_dir.mkdir(parents=True, exist_ok=True)
        (adapter_dir / "SKILL.md").write_text(content, encoding="utf-8")

    # [missing]
    public_dir1 = tmp_path / "case1" / "public"
    _setup_adapter(public_dir1, "my-adapter")
    ws1 = tmp_path / "case1" / "workspace"
    ws1.mkdir(parents=True)
    out1 = _mgr(public_dir1)._dcx6_codex_runtime_adapters(ws1)
    assert any("[missing]" in line and "my-adapter" in line and "D-CX-6" in line for line in out1)

    # [drift]
    public_dir2 = tmp_path / "case2" / "public"
    _setup_adapter(public_dir2, "my-adapter", "# Source\n")
    ws2 = tmp_path / "case2" / "workspace"
    ws2.mkdir(parents=True)
    dst2 = ws2 / ".codex" / "skills" / "my-adapter" / "SKILL.md"
    dst2.parent.mkdir(parents=True)
    dst2.write_text("# Modified\n", encoding="utf-8")
    out2 = _mgr(public_dir2)._dcx6_codex_runtime_adapters(ws2)
    assert any("[drift]" in line and "my-adapter" in line and "D-CX-6" in line for line in out2)

    # [leak] into .claude/skills/
    public_dir3 = tmp_path / "case3" / "public"
    _setup_adapter(public_dir3, "my-adapter")
    ws3 = tmp_path / "case3" / "workspace"
    ws3.mkdir(parents=True)
    leak_path = ws3 / ".claude" / "skills" / "my-adapter" / "SKILL.md"
    leak_path.parent.mkdir(parents=True)
    leak_path.write_text("# Leak\n", encoding="utf-8")
    out3 = _mgr(public_dir3)._dcx6_codex_runtime_adapters(ws3)
    assert any(
        "[leak]" in line and "claude" in line and "my-adapter" in line and "D-CX-6" in line
        for line in out3
    )

    # in-sync / no-src-root / file-at-src-root / subdir-without-skill -> all clean
    public_dir4 = tmp_path / "case4" / "public"
    content4 = "# My Adapter\n"
    adapter_dir4 = public_dir4 / "runtime" / "codex" / "my-adapter"
    adapter_dir4.mkdir(parents=True)
    (adapter_dir4 / "SKILL.md").write_text(content4, encoding="utf-8")
    ws4 = tmp_path / "case4" / "workspace"
    dst4 = ws4 / ".codex" / "skills" / "my-adapter" / "SKILL.md"
    dst4.parent.mkdir(parents=True)
    dst4.write_text(content4, encoding="utf-8")
    assert _mgr(public_dir4)._dcx6_codex_runtime_adapters(ws4) == []

    public_dir5 = tmp_path / "case5" / "public"
    public_dir5.mkdir(parents=True)
    ws5 = tmp_path / "case5" / "workspace"
    ws5.mkdir(parents=True)
    assert _mgr(public_dir5)._dcx6_codex_runtime_adapters(ws5) == []

    # _check_codex_drift includes DCX6 output.
    agentic_dir6, workspace_root6 = _build_minimal_agentic_dir(tmp_path / "case6")
    public_dir6 = tmp_path / "case6" / "public_dir"
    _setup_adapter(public_dir6, "missing-adapter")
    out6 = _mgr(public_dir6)._check_codex_drift(agentic_dir6, workspace_root6)
    assert any(
        "[missing]" in line and "missing-adapter" in line and "D-CX-6" in line for line in out6
    )
