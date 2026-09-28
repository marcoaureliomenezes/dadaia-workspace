"""HOOKS-DRIFT-1 — the installed git hooks match the shipped ones (0.4.7 FR6c, T-047-21).

Intent: CONTRACT — 0.4.7 FR6c / T-047-21. Size: SMALL (unit).

A git chokepoint is the ONE mechanical backstop that runs outside every harness hook
(`.dadaia/AGENTS.md`). An installed copy that has drifted from what the library ships is a
chokepoint enforcing yesterday's contract, silently — the doctor is the only place that
can notice.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService, workspace_rules


class _Store:
    def __init__(self, contexts: list[SpecContextProject]) -> None:
        self._contexts = contexts

    def list_all(self) -> list[SpecContextProject]:
        return self._contexts

    def get(self, name: str) -> SpecContextProject | None:
        return next((c for c in self._contexts if c.name == name), None)


def _ctx(name: str, state: ContextState = ContextState.ALIVE) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        repo_slug=name,
        repo_url=f"git@example.invalid:{name}.git",
        state=state,
        created_at="2026-09-13T00:00:00Z",
    )


def _workspace(tmp_path: Path, *, drifted: bool = False, installed: bool = True) -> Path:
    repo = tmp_path / "repos" / "demo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    hooks = repo / ".git" / "hooks"
    if installed:
        for target, source in workspace_layout.INSTALLED_GIT_HOOKS:
            shipped = (workspace_layout.public_scripts_dir() / source).read_bytes()
            (hooks / target).write_bytes(b"# hand-edited\n" + shipped if drifted else shipped)
    return tmp_path


def _codes(root: Path, contexts: list[SpecContextProject]) -> list[str]:
    service = DoctorService(_Store(contexts), None, root)  # type: ignore[arg-type]
    return [issue.code for issue in service.check_installed_hooks()]


def test_hooks_matching_the_shipped_scripts_raise_nothing(tmp_path: Path) -> None:
    assert "HOOKS-DRIFT-1" not in _codes(_workspace(tmp_path), [_ctx("demo")])


def test_a_missing_installed_hook_is_the_same_finding(tmp_path: Path) -> None:
    assert "HOOKS-DRIFT-1" in _codes(_workspace(tmp_path, installed=False), [_ctx("demo")])


def test_a_dead_context_is_never_checked(tmp_path: Path) -> None:
    root = _workspace(tmp_path, drifted=True)
    assert "HOOKS-DRIFT-1" not in _codes(root, [_ctx("demo", ContextState.DEAD)])


def test_a_repo_that_is_not_a_git_checkout_is_never_a_finding(tmp_path: Path) -> None:
    (tmp_path / "repos" / "demo").mkdir(parents=True)
    assert "HOOKS-DRIFT-1" not in _codes(tmp_path, [_ctx("demo")])


def test_a_named_context_checks_only_its_own_repos(tmp_path: Path) -> None:
    """0.4.8 R5 / AC3.7: `doctor --context X` judges X's hooks, never another context's."""
    root = _workspace(tmp_path, drifted=True)
    service = DoctorService(_Store([_ctx("demo"), _ctx("other")]), None, root)  # type: ignore[arg-type]
    assert service.check_installed_hooks("other") == []
    assert [i.code for i in service.check_installed_hooks("demo")] == ["HOOKS-DRIFT-1"]


def test_a_gate_git_never_runs_is_a_finding(tmp_path: Path) -> None:
    """pre-push-gate-never-runs-under-core-hookspath#B2: the gate sits in .git/hooks but
    core.hooksPath sends git elsewhere — an error finding with a runnable fix, never healthy."""
    root = _workspace(tmp_path)
    subprocess.run(
        ["git", "-C", str(root / "repos" / "demo"), "config", "core.hooksPath", ".husky"]
    )
    rule = next(r for r in workspace_rules() if "HOOKS-DRIFT-1" in r.codes)
    [finding] = rule.run(DoctorService(_Store([_ctx("demo")]), None, root))  # type: ignore[arg-type]
    assert finding.error
    assert "repos/demo/.husky/pre-push" in finding.message


def test_no_module_computes_the_hooks_dir_itself() -> None:
    """pre-push-gate-never-runs-under-core-hookspath#B4: installer and doctor share ONE
    resolver (`git rev-parse --git-path hooks`); no code builds `.git/hooks` by hand."""
    package = Path(workspace_layout.__file__).parents[1]
    hand_built = re.compile(r"""["']\.git["']\s*/\s*["']hooks["']|["']\.git/hooks""")
    offenders = [p for p in package.rglob("*.py") if hand_built.search(p.read_text("utf-8"))]
    assert offenders == []
