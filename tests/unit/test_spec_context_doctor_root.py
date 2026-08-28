"""Unit tests for DoctorService ROOT-* invariants (T-SANI-05).

The whole file is a doctor code-emission table — a prime param-table candidate. The
``.dadaia/hooks`` ROOT-4 regression survives as a named row (bug
workspace-doctor-root4-false-positive-dadaia-hooks).
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402


def _make_doctor(workspace_root: Path) -> DoctorService:
    """Build DoctorService with empty context store for ROOT-only tests."""
    ctx_store = FakeContextStore()
    git_client = FakeGitClient()
    return DoctorService(ctx_store, git_client, workspace_root)


def _init_workspace(root: Path) -> None:
    """Create the minimal workspace skeleton expected by DoctorService."""
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}'
    )
    (root / "repos").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents")


# ---------------------------------------------------------------------------
# ROOT-1: workspace root contains only whitelisted entries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "setup_fn"),
    [
        ("stray_file", lambda tp: (tp / "random_junk.txt").write_text("oops")),
        ("stray_dir", lambda tp: (tp / "my_project").mkdir()),
        (
            "comment_line_not_an_exception",
            lambda tp: (
                (tp / "stray.txt").write_text("junk"),
                (tp / ".dadaia" / "states" / "root_exceptions.txt").write_text(
                    "# this is a comment\n"
                ),
            ),
        ),
    ],
)
def test_root1_block_table(tmp_path: Path, name: str, setup_fn: object) -> None:
    _init_workspace(tmp_path)
    setup_fn(tmp_path)  # type: ignore[operator]
    svc = _make_doctor(tmp_path)
    issues = svc.check()
    codes = {i.code for i in issues}
    assert "ROOT-1" in codes
    if name == "stray_file":
        # ROOT-1 issues are not auto-fixable (requires human relocation).
        root1_issues = [i for i in issues if i.code == "ROOT-1"]
        assert len(root1_issues) == 1
        assert root1_issues[0].fixable is False


@pytest.mark.parametrize(
    ("name", "setup_fn"),
    [
        ("clean_workspace", lambda tp: None),
        (
            "whitelisted_dirs",
            lambda tp: [
                (tp / name).mkdir(exist_ok=True)
                for name in [".agents", ".claude", ".codex", ".kimi-code"]
            ],
        ),
        # `.kimi-code/` (Kimi Code Layer-1 harness home, v0.2.8) does not trigger ROOT-1.
        ("kimi_code_dir", lambda tp: (tp / ".kimi-code").mkdir(exist_ok=True)),
        (".gitignore", lambda tp: (tp / ".gitignore").write_text("*.pyc\n")),
        # Root-law-allowed files need NO exception list (bug
        # doctor-root-whitelist-contradicts-root-law).
        ("claude_bridge", lambda tp: (tp / "CLAUDE.md").write_text("@AGENTS.md")),
        ("operator_prompt", lambda tp: (tp / "prompt.md").write_text("# notes")),
        (
            "operator_exception_exact",
            lambda tp: (
                (tp / "prompt.md").write_text("# notes"),
                (tp / "screenshot.png").write_bytes(b"PNG"),
                (tp / ".dadaia" / "states" / "root_exceptions.txt").write_text(
                    "prompt.md\nscreenshot.png\n"
                ),
            ),
        ),
        (
            "operator_exception_glob",
            lambda tp: (
                (tp / "session-tab-1280.png").write_bytes(b"PNG"),
                (tp / ".dadaia" / "states" / "root_exceptions.txt").write_text("*.png\n"),
            ),
        ),
    ],
)
def test_root1_allow_table(tmp_path: Path, name: str, setup_fn: object) -> None:
    _init_workspace(tmp_path)
    setup_fn(tmp_path)  # type: ignore[operator]
    svc = _make_doctor(tmp_path)
    codes = {i.code for i in svc.check()}
    assert "ROOT-1" not in codes


# ---------------------------------------------------------------------------
# ROOT-2: no forbidden caches/outputs at workspace root
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [".ruff_cache", ".pytest_cache", ".coverage", ".playwright-mcp", ".mypy_cache", ".hypothesis"],
)
def test_root2_flags_each_forbidden_cache_kind(tmp_path: Path, name: str) -> None:
    _init_workspace(tmp_path)
    target = tmp_path / name
    if name == ".coverage":
        target.write_text("")
    else:
        target.mkdir()
    svc = _make_doctor(tmp_path)
    codes = {i.code for i in svc.check()}
    assert "ROOT-2" in codes


def test_root2_clean_fixable_and_fix_removes_caches_recursively(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    svc = _make_doctor(tmp_path)
    assert "ROOT-2" not in {i.code for i in svc.check()}

    cache_dir = tmp_path / ".ruff_cache"
    cache_dir.mkdir()
    coverage_file = tmp_path / ".coverage"
    coverage_file.write_text("")
    svc2 = _make_doctor(tmp_path)
    root2_issues = [i for i in svc2.check() if i.code == "ROOT-2"]
    assert len(root2_issues) >= 1
    assert root2_issues[0].fixable is True

    # fix() deletes forbidden cache dirs at workspace root.
    actions = svc2.fix()
    assert not cache_dir.exists(), ".ruff_cache should have been deleted"
    assert not coverage_file.exists(), ".coverage should have been deleted"
    root2_actions = [a for a in actions if "ROOT-2" in a]
    assert len(root2_actions) >= 2

    # fix() recursively removes a cache dir that contains files.
    pytest_cache = tmp_path / ".pytest_cache"
    pytest_cache.mkdir()
    (pytest_cache / "v").mkdir()
    (pytest_cache / "v" / "cache.json").write_text("{}")
    svc3 = _make_doctor(tmp_path)
    svc3.fix()
    assert not pytest_cache.exists()


# ---------------------------------------------------------------------------
# ROOT-3: tool configs in canonical homes or exception list (WARN, not fixable)
# ---------------------------------------------------------------------------


def test_root3_table(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    assert "ROOT-3" not in {i.code for i in _make_doctor(tmp_path).check()}

    mcp_dir = tmp_path / "mcp"
    mcp_dir.mkdir()
    # (reuse the same workspace for the mcp.json + CLAUDE.md ROOT-3 rows below, each
    # in its own subordinate check to avoid cross-row interaction).

    # .mcp.json at root (not in exception list) triggers ROOT-3.
    (tmp_path / ".mcp.json").write_text("{}")
    codes_mcp = {i.code for i in _make_doctor(tmp_path).check()}
    assert "ROOT-3" in codes_mcp
    (tmp_path / ".mcp.json").unlink()

    # CLAUDE.md at root is root-law-allowed (required Claude bridge) — no ROOT-3 WARN;
    # its ROOT-1 cleanliness is covered by the allow-table above (bug
    # doctor-root-whitelist-contradicts-root-law).
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md")
    codes_claude = {i.code for i in _make_doctor(tmp_path).check()}
    assert "ROOT-3" not in codes_claude
    (tmp_path / "CLAUDE.md").unlink()

    # Tool config present in root_exceptions.txt does not trigger ROOT-3.
    (tmp_path / ".mcp.json").write_text("{}")
    (tmp_path / ".dadaia" / "states" / "root_exceptions.txt").write_text(".mcp.json\n")
    codes_exempt = {i.code for i in _make_doctor(tmp_path).check()}
    assert "ROOT-3" not in codes_exempt
    (tmp_path / ".dadaia" / "states" / "root_exceptions.txt").unlink()

    # ROOT-3 is a WARN — not auto-fixable (requires research/relocation).
    root3_issues = [i for i in _make_doctor(tmp_path).check() if i.code == "ROOT-3"]
    assert len(root3_issues) == 1
    assert root3_issues[0].fixable is False


# ---------------------------------------------------------------------------
# ROOT-4: .dadaia/ contains only canonical top-level subdirs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "setup_fn"),
    [
        ("clean_workspace", lambda tp: None),
        (
            "known_canonical_subdirs",
            lambda tp: [
                (tp / ".dadaia" / n).mkdir(exist_ok=True)
                for n in ["agentic", "mcps", "scripts", "tmp", "reports", "states", "logs"]
            ],
        ),
        (
            # v0.1.47 W1-9: .dadaia/hooks/ (Python governance hooks) is canonical,
            # not ROOT-4. Regression for bug
            # workspace-doctor-root4-false-positive-dadaia-hooks.
            "dadaia_hooks_subdir_regression",
            lambda tp: (tp / ".dadaia" / "hooks").mkdir(),
        ),
        (
            # Dotfiles (non-directories) inside .dadaia/ are allowed (e.g. .gitkeep).
            "dotfile_inside_dadaia",
            lambda tp: (tp / ".dadaia" / ".gitkeep").write_text(""),
        ),
        (
            # Operator ruling O4 (v0.4.5, T-045-23, FR10): .dadaia/references/<clone>/
            # is the sanctioned home for an operator-placed reference clone — no longer
            # ROOT-4. See test_dadaia_references_lifecycle_sanction.py for the paired
            # A10.2 proof that no lifecycle verb can ever act on it.
            "dadaia_references_reference_clone",
            lambda tp: (tp / ".dadaia" / "references" / "some-clone").mkdir(parents=True),
        ),
    ],
)
def test_root4_allow_table(tmp_path: Path, name: str, setup_fn: object) -> None:
    _init_workspace(tmp_path)
    if setup_fn is not None:
        setup_fn(tmp_path)  # type: ignore[operator]
    svc = _make_doctor(tmp_path)
    codes = {i.code for i in svc.check()}
    assert "ROOT-4" not in codes


@pytest.mark.parametrize("name", ["figma-bridge", "imgs"])
def test_root4_flags_retired_junk_drawer_dirs(tmp_path: Path, name: str) -> None:
    """Bug doctor-whitelist-legitimizes-slop-dirs (2026-07-15).

    The retired 'Additional dirs observed in practice' junk-drawer entries
    (figma-bridge, imgs) are NO LONGER canonical — they have no
    architectural purpose (MCP state -> mcps/, evidence -> tmp/<agent>/<date>/).
    Doctor must flag them ROOT-4 so slop stops accumulating at the .dadaia root.

    ``references`` was a third entry in this same 2026-07-15 sweep; operator ruling O4
    (v0.4.5, T-045-23, FR10) re-sanctions it under a new, explicit purpose (operator
    reference clones) — it moved to the ROOT-4 allow-table above and is no longer
    flagged here.
    """
    _init_workspace(tmp_path)
    (tmp_path / ".dadaia" / name).mkdir()
    svc = _make_doctor(tmp_path)
    codes = {i.code for i in svc.check()}
    assert "ROOT-4" in codes


def test_root4_unknown_subdir_flags_not_fixable_and_absent_dadaia_dir_no_root4(
    tmp_path: Path,
) -> None:
    _init_workspace(tmp_path)
    (tmp_path / ".dadaia" / "mystery-tool-output").mkdir()
    svc = _make_doctor(tmp_path)
    root4_issues = [i for i in svc.check() if i.code == "ROOT-4"]
    assert len(root4_issues) == 1
    assert root4_issues[0].fixable is False

    # If .dadaia/ is absent entirely, ROOT-4 is not triggered (pathological but defensive).
    ctx_store = FakeContextStore()
    git_client = FakeGitClient()
    absent_svc = DoctorService(ctx_store, git_client, tmp_path.parent / (tmp_path.name + "-bare"))
    issues = absent_svc._check_root_4()
    assert issues == []
