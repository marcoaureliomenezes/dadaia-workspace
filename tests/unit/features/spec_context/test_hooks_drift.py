"""HOOKS-DRIFT-1 — the installed git hooks match the shipped ones (0.4.7 FR6c, T-047-21).

Intent: CONTRACT — 0.4.7 FR6c / T-047-21. Size: SMALL (unit).

A git chokepoint is the ONE mechanical backstop that runs outside every harness hook
(DADAIA.md 3.4). An installed copy that has drifted from what the library ships is a
chokepoint enforcing yesterday's contract, silently — the doctor is the only place that
can notice.
"""

from __future__ import annotations

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
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
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


def test_a_byte_differing_installed_hook_is_a_finding(tmp_path: Path) -> None:
    assert "HOOKS-DRIFT-1" in _codes(_workspace(tmp_path, drifted=True), [_ctx("demo")])


def test_a_missing_installed_hook_is_the_same_finding(tmp_path: Path) -> None:
    assert "HOOKS-DRIFT-1" in _codes(_workspace(tmp_path, installed=False), [_ctx("demo")])


def test_a_dead_context_is_never_checked(tmp_path: Path) -> None:
    root = _workspace(tmp_path, drifted=True)
    assert "HOOKS-DRIFT-1" not in _codes(root, [_ctx("demo", ContextState.DEAD)])


def test_a_repo_that_is_not_a_git_checkout_is_never_a_finding(tmp_path: Path) -> None:
    (tmp_path / "repos" / "demo").mkdir(parents=True)
    assert "HOOKS-DRIFT-1" not in _codes(tmp_path, [_ctx("demo")])


def test_the_finding_carries_the_runnable_install_verb() -> None:
    """The fix must be one executable line, and the verb must exist (0.4.7 FR2)."""
    rule = next(r for r in workspace_rules() if "HOOKS-DRIFT-1" in r.codes)
    assert rule.fix_help == ".dadaia/.venv/bin/dadaia ci install-hook --force"
    assert rule.section == "workspace"


def test_the_shipped_hook_registry_names_both_chokepoints() -> None:
    assert workspace_layout.INSTALLED_GIT_HOOKS == (
        ("pre-commit", "pre-commit-presence-gate.sh"),
        ("pre-push", "pre-push-ci-gate.sh"),
    )
    for _, source in workspace_layout.INSTALLED_GIT_HOOKS:
        assert (workspace_layout.public_scripts_dir() / source).is_file()
