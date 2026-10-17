"""HOOKS-DRIFT-1 — the installed git hooks match the shipped ones.

A git chokepoint is the ONE mechanical backstop that runs outside every harness hook
(`.dadaia/AGENTS.md`). An installed copy that has drifted from what the library ships is a
chokepoint enforcing yesterday's contract, silently — the doctor is the only place that
can notice.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService, workspace_rules
from tests.helpers.oslib import read_text, run


class _Store:
    def __init__(self, contexts: list[SpecContextProject]) -> None:
        self._contexts = contexts

    def list_all(self) -> list[SpecContextProject]:
        return self._contexts

    def get(self, name: str) -> SpecContextProject | None:
        return next((c for c in self._contexts if c.name == name), None)


def _install_hook(root: Path) -> str:
    return fix_line(root, "ci", "install-hook", "--force", "--repo", str(root / "repos" / "demo"))


def _ctx(name: str, state: ContextState = ContextState.ALIVE) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        repo_slug=name,
        repo_url=f"git@example.invalid:{name}.git",
        state=state,
        created_at="2026-09-13T00:00:00Z",
    )


def _workspace(
    tmp_path: Path,
    *,
    drifted: bool = False,
    installed: bool = True,
    missing: bool = False,
    git: bool = True,
) -> Path:
    repo = tmp_path / "repos" / "demo"
    repo.mkdir(parents=True)
    if not git:
        return tmp_path
    run(["git", "init", "-q", str(repo)], check=True)
    for target, source in workspace_layout.INSTALLED_GIT_HOOKS if installed else ():
        if target == "pre-push" and missing:
            continue
        shipped = (workspace_layout.public_scripts_dir() / source).read_bytes()
        (repo / ".git" / "hooks" / target).write_bytes(
            b"# hand-edited\n" + shipped if drifted and target == "pre-push" else shipped
        )
    return tmp_path


# fmt: off
@pytest.mark.parametrize(("layout", "state", "finding"), [
    pytest.param({}, ContextState.ALIVE, False, id="matching-shipped-hooks"),
    pytest.param({"drifted": True}, ContextState.ALIVE, True, id="drifted-hook"),
    pytest.param({"missing": True}, ContextState.ALIVE, True, id="missing-hook-is-the-same-finding"),
    pytest.param({"drifted": True}, ContextState.DEAD, False, id="dead-context-never-checked"),
    pytest.param({"git": False}, ContextState.ALIVE, False, id="not-a-git-checkout-never-a-finding"),
])
# fmt: on
def test_hooks_drift_1_flags_an_installed_hook_that_is_not_the_shipped_one(
    tmp_path: Path, layout: dict[str, bool], state: ContextState, finding: bool
) -> None:
    service = DoctorService(_Store([_ctx("demo", state)]), None, _workspace(tmp_path, **layout))  # type: ignore[arg-type]
    assert [i.code for i in service.check_installed_hooks()] == (["HOOKS-DRIFT-1"] if finding else [])


def test_a_named_context_checks_only_its_own_repos(tmp_path: Path) -> None:
    """`doctor --context X` judges X's hooks, never another context's."""
    root = _workspace(tmp_path, drifted=True)
    service = DoctorService(_Store([_ctx("demo"), _ctx("other")]), None, root)  # type: ignore[arg-type]
    assert service.check_installed_hooks("other") == []
    assert [i.code for i in service.check_installed_hooks("demo")] == ["HOOKS-DRIFT-1"]


def test_a_gate_git_never_runs_is_a_finding(tmp_path: Path) -> None:
    """The gate sits in .git/hooks but
    core.hooksPath sends git elsewhere — an error finding with a runnable fix, never healthy."""
    root = _workspace(tmp_path)
    run(["git", "-C", str(root / "repos" / "demo"), "config", "core.hooksPath", ".husky"])
    rule = next(r for r in workspace_rules() if "HOOKS-DRIFT-1" in r.codes)
    found = rule.run(DoctorService(_Store([_ctx("demo")]), None, root))  # type: ignore[arg-type]
    assert [f.error for f in found] == [True, True]
    assert [f.message.split(" ")[0] for f in found] == [
        "repos/demo/.husky/pre-push",
        "repos/demo/.husky/reference-transaction",
    ]


def test_no_module_computes_the_hooks_dir_itself() -> None:
    """Installer and doctor share ONE
    resolver (`git rev-parse --git-path hooks`); no code builds `.git/hooks` by hand."""
    package = Path(workspace_layout.__file__).parents[1]
    hand_built = re.compile(r"""["']\.git["']\s*/\s*["']hooks["']|["']\.git/hooks""")
    offenders = [p for p in package.rglob("*.py") if hand_built.search(read_text(p))]
    assert offenders == []


# fmt: off
@pytest.mark.parametrize(("layout", "observed", "other"), [
    pytest.param({"drifted": True}, r"differs from the shipped \S+$", "absent", id="edited-hook-differs"),
    pytest.param({"missing": True}, r"is absent$", "differs", id="deleted-hook-is-absent"),
])
# fmt: on
def test_hooks_drift_1_names_the_observed_state_with_one_code_and_one_fix(
    tmp_path: Path, layout: dict[str, bool], observed: str, other: str
) -> None:
    """The message states what was observed; one code and one fix line serve both."""
    root = _workspace(tmp_path, **layout)
    found = DoctorService(_Store([_ctx("demo")]), None, root).check_installed_hooks()  # type: ignore[arg-type]
    assert {f.code for f in found} == {"HOOKS-DRIFT-1"}
    for f in found:
        head = f.message.split(" — ")[0]
        assert head.startswith("repos/demo/.git/hooks/") and re.search(observed, head)
        assert other not in f.message
        assert f.fix == _install_hook(root)


def test_an_unreadable_hook_is_said_unreadable_never_differing(tmp_path: Path) -> None:
    """The `OSError` arm names the failed read, not a content difference."""
    root = _workspace(tmp_path)
    for target, _ in workspace_layout.INSTALLED_GIT_HOOKS:
        hook = root / "repos" / "demo" / ".git" / "hooks" / target
        hook.unlink()
        hook.mkdir()  # reading a directory raises an OSError that is not FileNotFoundError
    found = DoctorService(_Store([_ctx("demo")]), None, root).check_installed_hooks()  # type: ignore[arg-type]
    assert found
    for f in found:
        assert re.search(r"is unreadable \(.+\) — ", f.message) and "differs" not in f.message


def test_a_non_git_repo_listed_first_never_hides_a_drifted_one(tmp_path: Path) -> None:
    root = _workspace(tmp_path, drifted=True)
    (root / "repos" / "plain").mkdir()
    store = _Store([_ctx("plain"), _ctx("demo")])
    found = DoctorService(store, None, root).check_installed_hooks()  # type: ignore[arg-type]
    assert {f.code for f in found} == {"HOOKS-DRIFT-1"}
    assert all(f.message.startswith("repos/demo/") for f in found)


def test_a_repo_without_the_reference_transaction_hook_is_told_so(tmp_path: Path) -> None:
    """The ref-gate hook is a shipped row: a repo holding only the pre-push gate lacks it."""
    root = _workspace(tmp_path, installed=False)
    hooks = root / "repos" / "demo" / ".git" / "hooks"
    shipped = workspace_layout.public_scripts_dir() / "pre-push-ci-gate.sh"
    (hooks / "pre-push").write_bytes(shipped.read_bytes())
    found = DoctorService(_Store([_ctx("demo")]), None, root).check_installed_hooks()  # type: ignore[arg-type]
    [finding] = [f for f in found if "reference-transaction" in f.message]
    assert finding.code == "HOOKS-DRIFT-1"
    assert finding.message.startswith("repos/demo/.git/hooks/reference-transaction is absent — ")
    assert finding.fix == _install_hook(root)
    assert len(found) == 1
