"""The fix-line contract: every refusal carries exactly one ``fix:`` line that clears it.

``SITES`` maps a site name to a producer: given a fresh workspace root it returns the refusal
text that site prints. A further adapter adds its sites with ``SITES |= {...}``.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.cli_line import cli_path, fix_line
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
from dadaia_workspace.features.spec_context.service import install_git_hooks
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.hooks import pre_gate
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import VENV_MISSING
from tests.fakes import gate_fixes
from tests.fixtures.real_git import PushRepo

_FIX_LINE_RE = re.compile(r"^fix: (\S.*)$", re.MULTILINE)
#: Not one act: a `<…>` (bar the `<specs>` a rule fix fills), an `&&` chain, an `a|b` menu;
#: a command also no ` or ` / ` then `.
_NOT_ONE_ACT_RE = re.compile(r"<(?!specs>)[^<>\n]+>|&&|\w\|\w")
_NOT_ONE_COMMAND_RE = re.compile(rf"{_NOT_ONE_ACT_RE.pattern}| or | then ")
#: The installer a workspace is born from, absent from CI runners.
_PREREQUISITES = {"uvx"}
#: The executables a fix line opens with (a list, not `which`: a host may ship a prose-named binary).
_HEADS = {"chmod", "gh", "git", "grep", "ls", "mkdir", "rm", "sed", *_PREREQUISITES}
_SHA_B, _ZERO = "b" * 40, "0" * 40


def fix_defect(fix: str) -> bool:
    """True when *fix* is neither `Operator action: <one act>` nor one command whose head is
    no prose word; `·` stands for a value a source walk cannot know."""
    known = fix.split("·", 1)[0]
    if fix.startswith("Operator action: ") or " " not in known and "·" in fix:
        return bool(_NOT_ONE_ACT_RE.search(fix))
    head = known.split(" ", 1)[0]
    prose = re.fullmatch(r"[a-z][a-z0-9-]*", head) and head not in _HEADS
    return bool(prose or _NOT_ONE_ACT_RE.search(fix) or _NOT_ONE_COMMAND_RE.search(known))


def the_fix(message: str | None) -> str:
    """The one ``fix:`` line of *message*; raises AssertionError unless it is one act the
    gate lets run."""
    assert message, "a refusal with an empty message is a stall"
    fixes = _FIX_LINE_RE.findall(message)
    assert len(fixes) == 1, f"expected exactly one 'fix:' line, got {fixes} in:\n{message}"
    fix = fixes[0]
    assert not fix_defect(fix) and "<specs>" not in fix, f"not one act: {fix}"
    if fix.startswith("Operator action: "):
        return fix
    argv0 = shlex.split(fix)[0]  # an absolute file, or a bare name on PATH, never cwd-relative
    on_path = "/" not in argv0 and (shutil.which(argv0) or argv0 in _PREREQUISITES)
    assert on_path or (Path(argv0).is_absolute() and Path(argv0).is_file()), fix
    block = pre_gate.evaluate_payload({"tool_name": "Bash", "tool_input": {"command": fix}})
    assert block is None, f"the fix command is itself blocked:\n{fix}\n{block}"
    return fix


def _workspace(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"contexts": [{"repo_slug": "a", "state": "alive"}]}', encoding="utf-8"
    )
    (root / ".dadaia" / "sessions").mkdir(parents=True)
    (root / ".dadaiaignore").write_text("[protected]\nsecrets\n", encoding="utf-8")
    stand_in = shutil.which("whoami" if sys.platform == "win32" else "true")  # a real exe, exit 0
    assert stand_in, "the host has no stand-in executable"
    cli_path(root).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(stand_in, cli_path(root))
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _workspace(tmp_path, monkeypatch)


@pytest.fixture
def blank_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A workspace whose root holds a blank, so the fix's executable path must be quoted."""
    return _workspace(tmp_path / "my ws", monkeypatch)


def _gate(ws: Path, rel: str) -> str | None:
    return pre_gate.evaluate_payload({"tool_name": "Write", "tool_input": {"file_path": str(ws / rel)}})  # fmt: skip


def _scope_block(ws: Path, *, has_id: bool) -> str:
    """A write into a repo another context owns, outside the bind's repos."""
    from dadaia_workspace.features.spec_context.gate_policy import evaluate

    return evaluate("repos/b/x.py", root=ws, zone="repo", repo="b", owner="b",
                    context="a", repos=frozenset({"a"}), has_id=has_id)[1]  # fmt: skip


def _push(ws: Path, line: str = "", files: dict[str, str] | None = None, **kwargs: Any) -> str:
    """A consumer work clone (``main`` published, one unpublished commit, the installed
    pre-push hook), pushing *line*; the refusal text."""
    (ws / "clone").mkdir()
    repo = PushRepo(ws / "clone")
    repo.commit({"README.md": "r\n"})
    repo.publish("main")
    install_git_hooks(repo.path)
    sha = repo.commit(files or {"a.md": "a\n"})
    fields = {"sha": sha, "other": _SHA_B, "zero": _ZERO, "a": "a" * 40}
    decision = push_gate_decision(
        parse_push_stdin(line.format(**fields))[0] if line else [],
        gitflow=DEFAULT,
        fixes=replace(gate_fixes(), head="feature/0.0.1"),
        object_source=GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
        **{"malformed_lines": 0, "denylist_terms": (), **kwargs},
    )
    assert not decision.allowed, "expected a refusal"
    return decision.message


_FEATURE = "refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {zero}"
SITES: dict[str, Callable[[Path], str | None]] = {
    "gate-root-whitelist": lambda ws: _gate(ws, "junk.txt"),
    "gate-protected-sessions": lambda ws: _gate(ws, ".dadaia/sessions/some-session.json"),
    "gate-protected-projected": lambda ws: _gate(ws, ".dadaia/states/install_ledger.json"),
    "gate-protected-glob": lambda ws: _gate(ws, "repos/a/secrets/k"),
    "gate-scope-names-the-bind": lambda ws: _scope_block(ws, has_id=True),
    "gate-id-less-session-relaunch": lambda ws: _scope_block(ws, has_id=False),
    "hook-missing-venv": lambda ws: VENV_MISSING.replace("$ROOT", ws.as_posix()),
    "push-malformed-stdin": lambda ws: _push(ws, malformed_lines=1),
    "push-main": lambda ws: _push(ws, "refs/heads/main {sha} refs/heads/main {other}"),
    "push-develop": lambda ws: _push(ws, "refs/heads/develop {sha} refs/heads/develop {other}"),
    "push-birth-with-content": lambda ws: _push(
        ws, "refs/heads/develop {sha} refs/heads/develop {zero}"
    ),
    "push-invalid-name": lambda ws: _push(ws, "refs/heads/wip/x {sha} refs/heads/wip/x {zero}"),
    "push-not-a-branch-head": lambda ws: _push(ws, "refs/notes/x {sha} refs/notes/x {zero}"),
    "push-refspec": lambda ws: _push(
        ws, "refs/heads/feature/0.0.1 {sha} refs/heads/develop {zero}"
    ),
    "push-specs-canon": lambda ws: _push(ws, _FEATURE, {"specs/not-a-canon-entry.md": "x\n"}),
    "push-denylist": lambda ws: _push(
        ws, _FEATURE, {"b.md": "zz-secret-term\n"}, denylist_terms=[("zz-secret-term", "synthetic")]
    ),
    # a sha the repo does not hold: the real object read fails and the gate fails closed
    "push-git-read-failure": lambda ws: _push(ws, _FEATURE.replace("{sha}", "{a}")),
}


@pytest.mark.parametrize("site", list(SITES))
def test_every_site_carries_one_runnable_fix(workspace: Path, site: str) -> None:
    the_fix(SITES[site](workspace))


def _shells() -> list[list[str]]:
    if sys.platform != "win32":
        return [["sh", "-c"]]
    git_bash = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Git", "bin", "bash.exe")
    return [
        ["cmd", "/d", "/s", "/c"],
        ["powershell", "-NoProfile", "-Command"],
        [str(git_bash), "-c"],
    ]


@pytest.mark.parametrize("shell", _shells(), ids=lambda argv: Path(argv[0]).stem)
def test_a_fix_runs_verbatim_in_every_host_shell(blank_workspace: Path, shell: list[str]) -> None:
    """The root refusal's fix and a CLI fix line run verbatim in each shell the host offers
    (POSIX ``sh``; on Windows cmd, PowerShell and Git Bash): the root fix from ``repos/demo``,
    twice, never writing the exceptions file, in a root that holds a blank."""
    workspace = blank_workspace
    if shell[0].endswith("bash.exe") and not Path(shell[0]).is_file():
        pytest.skip(f"Git Bash is not installed at {shell[0]}")
    (workspace / ".dadaiaignore").unlink()
    root_fix = the_fix(_gate(workspace, "junk.txt"))
    (workspace / "repos" / "demo").mkdir(parents=True)
    runs = [
        subprocess.run(
            # cmd /s strips the outer quotes of its raw tail; list2cmdline's \" is not cmd syntax.
            f'{subprocess.list2cmdline(shell)} "{line}"' if shell[0] == "cmd" else [*shell, line],
            cwd=workspace / "repos" / "demo",
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )  # fmt: skip
        for line in (root_fix, root_fix, fix_line(workspace))
    ]
    assert [r.returncode for r in runs] == [0, 0, 0], [r.stderr for r in runs]
    # The CLI ran, not a shell echo of its quoted path (PowerShell exits 0 on an expression).
    direct = subprocess.run([cli_path(workspace)], capture_output=True, text=True, check=True)
    assert runs[2].stdout.strip() == direct.stdout.strip()
    assert (workspace / ".dadaia" / "tmp").is_dir()
    assert not (workspace / ".dadaiaignore").exists()  # the fix never writes the operator's file
