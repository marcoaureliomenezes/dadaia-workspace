"""The onboarding journey in three levels, driven through ``uvx`` over file:// bare repos.

The autopilot loop executes only printed fix lines.

Owner: dd-sw-engineer-sr (LARGE-tier e2e; tests/AGENTS.md "every file names an owner").

Size: LARGE, justified — the journey is a statement about the *published shape* of the tool: an
operator runs ``uvx --from <wheel> dadaia-workspace …`` and walks level 1 (workspace),
level 2 (Spec Context Project) and level 3 (canonical specs). Every seam the journey
crosses — uvx's own environment, the workspace venv provisioning, the clone, the hook,
the specs scaffold, doctor — is crossed by REAL child processes; no in-process runner
reaches them.

Layout — ONE workspace carries the journey: born on this checkout's wheel (level 1), upgraded
by re-init with the same code rebuilt under the next ``rc`` label, then levels 2 and 3 — a real
workspace venv is the journey's cost, so it is paid once. Only builds of this checkout are
installed. After every level doctor reports 0 errors and the user repo's HEAD equals its remote's.

Real venvs are built here by CHILD processes (``uvx`` and ``init``);
``tests/conftest.py``'s ``_no_real_venv_in_tests`` backstop is an in-process monkeypatch
and does not reach them — the same accommodation ``test_one_line_bootstrap`` documents.
Needs network for dependency resolution. CI puts ``uv`` on PATH and sets
``DADAIA_REQUIRE_UVX``; without uvx the launcher is a child-built venv holding
the same wheel, and only the verbatim-quickstart test (a literal ``uvx`` line) skips.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.platform import PLATFORM
from tests.conftest import GIT_QUIET_INCLUDE
from tests.e2e.test_one_line_bootstrap import _build_wheel
from tests.fixtures.harness_env import suite_env
from tests.helpers.oslib import read_text, write_text
from tests.helpers.oslib import run as os_run

_UVX = shutil.which("uvx")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow(reason="uvx + real workspace venvs + git clones per level"),
    # Justified over the e2e default: a first level provisions two real venvs (uvx's and
    # the workspace's) from the network; the memoized first test of a scenario pays it.
    pytest.mark.timeout(900),
]
# CI sets DADAIA_REQUIRE_UVX=1 so the journey drives `uvx --from` there and an absent uvx
# fails; without it (a dev box with no uv) the launcher is a child-built venv holding the
# same wheel, so the journey still runs locally.
_REQUIRE_UVX = bool(os.environ.get("DADAIA_REQUIRE_UVX"))

_TIMEOUT = 600.0
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_VERSION: str = tomllib.loads(read_text(_REPO_ROOT / "pyproject.toml"))["tool"]["poetry"][
    "version"
]
# The upgrade's target: the same code under the next label.
_NEXT_VERSION = (
    re.sub(r"rc(\d+)$", lambda m: f"rc{int(m[1]) + 1}", _SOURCE_VERSION)
    if "rc" in _SOURCE_VERSION
    else f"{_SOURCE_VERSION}.post1"
)


# ── the harness ──────────────────────────────────────────────────────────────────


class Env:
    """Child-process environment and the bare-repo factory for one scenario."""

    def __init__(self, root: Path, wheel: Path) -> None:
        self.root = root
        self.wheel = wheel
        self.home_dir = root / "home"
        self.fixtures = root / "fixtures"
        self.home_dir.mkdir(parents=True)
        self.fixtures.mkdir()
        # No inherited session identity: a scenario that wants one sets DADAIA_SESSION_ID.
        self.env = {k: v for k, v in suite_env(os.environ, Path.home()).items()
                    if not k.startswith("DADAIA_") or k == "DADAIA_FENCED_ROOTS"}  # fmt: skip
        # The journey is a consumer: it must import the uvx-installed wheel, never this checkout.
        self.env.pop("PYTHONPATH", None)
        self.env.pop("VIRTUAL_ENV", None)
        self.env.update(
            HOME=str(self.home_dir),
            XDG_CONFIG_HOME=str(self.home_dir / ".config"),
            COLUMNS="200",
            NO_COLOR="1",
            GIT_AUTHOR_NAME="t",
            GIT_AUTHOR_EMAIL="t@example.invalid",
            GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL="t@example.invalid",
            GIT_CONFIG_GLOBAL=str(self.home_dir / "gitconfig"),
            GIT_CONFIG_SYSTEM=os.devnull,
        )
        write_text(self.home_dir / "gitconfig", GIT_QUIET_INCLUDE)
        self.git("config", "--global", "init.defaultBranch", "main", cwd=root)
        self._launchers: dict[str, Path] = {}

    def run(self, *argv: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return os_run(list(argv), cwd=cwd, env=self.env, timeout=_TIMEOUT)

    def git(self, *args: str, cwd: Path) -> str:
        done = self.run("git", *args, cwd=cwd)
        assert done.returncode == 0, f"git {args} failed:\n{done.stderr}"
        return done.stdout.strip()

    def uvx(self, *argv: str, source: str | None = None) -> subprocess.CompletedProcess[str]:
        """``uvx --from <source> dadaia-workspace …`` — or, with no uvx and no CI demand
        for it, the same *source* pip-installed once into a child-built launcher venv."""
        spec = source or str(self.wheel)
        if _UVX is not None or _REQUIRE_UVX:
            assert _UVX is not None, "DADAIA_REQUIRE_UVX is set but uvx is not on PATH"
            return self.run(_UVX, "--from", spec, "dadaia-workspace", *argv, cwd=self.root)
        return self.run(str(self._launcher(spec)), *argv, cwd=self.root)

    def _launcher(self, spec: str) -> Path:
        if spec not in self._launchers:
            venv = self.root / "launchers" / str(len(self._launchers))
            self.run(sys.executable, "-m", "venv", str(venv), cwd=self.root).check_returncode()
            bin_dir = venv / PLATFORM.venv_scripts_dir
            pip = self.run(
                str(bin_dir / "python"), "-m", "pip", "install", "-q", spec, cwd=self.root
            )
            assert pip.returncode == 0, pip.stderr
            self._launchers[spec] = bin_dir / "dadaia-workspace"
        return self._launchers[spec]

    def bare(self, name: str, specs: str = "none", tag: str | None = None) -> str:
        """A file:// bare repo ``<name>.git`` with one commit, tagged *tag* when given;
        *specs* seeds its tree."""
        work = self.fixtures / f"src-{name}"
        (work / "app").mkdir(parents=True)
        write_text(work / "README.md", f"# {name}\n")
        write_text(work / "app" / "core.py", "def f():\n    return 1\n")
        if specs == "foreign":
            (work / "specs" / "features").mkdir(parents=True)
            write_text(work / "specs" / "features" / "login.md", "# my spec\n")
            write_text(work / "specs" / "README.md", "x\n")
        elif specs == "dadaia6":
            (work / "specs").mkdir()
            write_text(
                work / "specs" / "constitution.md",
                "---\nspecs_pattern_version: 6\n---\n# constitution\n",
            )
        self.git("init", "-q", cwd=work)
        self.git("add", "-A", cwd=work)
        self.git("commit", "-qm", "init", cwd=work)
        if tag:
            self.git("tag", tag, cwd=work)
        bare = self.fixtures / f"{name}.git"
        self.git("clone", "-q", "--bare", str(work), str(bare), cwd=self.root)
        return f"file://{bare}"


class Workspace:
    """One workspace under test and the clean-level assertions over it."""

    def __init__(self, env: Env, name: str) -> None:
        self.env = env
        self.path = env.root / name
        self.dadaia_bin = self.path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / "dadaia"

    def dadaia(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return self.env.run(str(self.dadaia_bin), *argv, cwd=self.path)

    def doctor_json(self, context: str | None = None) -> dict[str, Any]:
        argv = ["doctor", "--json"] + (["--context", context] if context else [])
        done = self.dadaia(*argv)
        payload: dict[str, Any] = json.loads(done.stdout)
        errors = [
            f
            for section in payload["sections"].values()
            for f in section["findings"]
            if f["verdict"] == "error"
        ]
        assert done.returncode == 0 and not errors, f"doctor not clean:\n{done.stdout}{done.stderr}"
        return payload

    def assert_level_clean(self, context: str, repo_slug: str, url: str) -> None:
        """Doctor 0 errors and the user repo's principal branch equals the remote's HEAD."""
        self.doctor_json(context)
        repo = self.path / "repos" / repo_slug
        symref, tip = self.env.git("ls-remote", "--symref", url, "HEAD", cwd=repo).splitlines()
        principal = self.env.git("rev-parse", symref.split()[1], cwd=repo)
        assert principal == tip.split()[0], f"{repo_slug}: {symref} {principal} != remote {tip}"


# ── fixtures ─────────────────────────────────────────────────────────────────────


def _wheel(root: Path, version: str) -> Path:
    """This checkout built offline, its pyproject version replaced by *version*."""
    source = root / "src"
    source.mkdir()
    shutil.copy2(_REPO_ROOT / "README.md", source / "README.md")
    pyproject = read_text(_REPO_ROOT / "pyproject.toml")
    write_text(
        source / "pyproject.toml",
        pyproject.replace(f'version = "{_SOURCE_VERSION}"', f'version = "{version}"', 1),
    )
    shutil.copytree(
        _REPO_ROOT / "dadaia_workspace",
        source / "dadaia_workspace",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return _build_wheel(source, root / "dist")


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _wheel(tmp_path_factory.mktemp("wheel"), _SOURCE_VERSION)


@pytest.fixture(scope="module")
def next_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _wheel(tmp_path_factory.mktemp("next"), _NEXT_VERSION)


@pytest.fixture
def env(tmp_path: Path, wheel: Path) -> Env:
    return Env(tmp_path, wheel)


# ── one operator's journey: born on this build, upgraded to the next label, then levels 2 and 3 ──


def test_an_operator_journey_through_an_upgrade(env: Env, next_wheel: Path) -> None:
    """Level 1 is ``init --repo`` on this checkout's wheel; re-``init`` with the same code under
    the next label is the upgrade. On that workspace, level 2: a failed ``context
    create`` leaves nothing, its retry and a second project with an associated
    repo clone clean; the guidance names level 3; level 3 ``specs init``. Clean after
    every level. A fresh level 1 is ``test_one_line_bootstrap``'s."""
    green = env.bare("green")
    ws = Workspace(env, "up")
    born = env.uvx("init", "up", "--harness", "claude", "--repo", green)
    assert born.returncode == 0, f"{born.stdout}\n{born.stderr}"
    # The upgrade must not move the user repo's HEAD.
    repo = ws.path / "repos" / "green"
    head = env.git("rev-parse", "HEAD", cwd=repo)
    done = env.uvx("init", "up", source=str(next_wheel))  # no --harness needed
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
    assert f"upgraded {_SOURCE_VERSION} -> {_NEXT_VERSION}" in done.stdout, done.stdout
    version = ws.dadaia("--version")
    assert _NEXT_VERSION in version.stdout, version.stdout
    # The upgrade never writes a user repo; level 3 commits only the scaffold on the work branch.
    refreshed = ws.dadaia("specs", "init", "--context", "green")
    assert refreshed.returncode == 0, f"{refreshed.stdout}\n{refreshed.stderr}"
    ws.doctor_json("green")
    assert env.git("rev-parse", "HEAD~1", cwd=repo) == head
    assert env.git("log", "-1", "--format=%s", cwd=repo) == "chore: scaffold the dadaia specs"
    again = env.uvx("init", "up", source=str(next_wheel))
    assert again.returncode == 0 and f"already at {_NEXT_VERSION}" in again.stdout

    bad = f"file://{env.fixtures / 'nothere.git'}"
    failed = ws.dadaia("context", "create", "retry", "--main-repo", bad)
    assert failed.returncode == 1, failed.stdout + failed.stderr
    assert "fix:" in failed.stdout + failed.stderr
    assert not (ws.path / "repos" / "nothere").exists()
    assert "retry" not in ws.dadaia("context", "list", "--json").stdout  # no context record

    for slug, associated in (("retry", ()), ("second", ("assoc",))):
        repos = {name: env.bare(name) for name in (slug, *associated)}
        argv = ["context", "create", slug, "--main-repo", repos[slug]]
        for name in associated:
            argv += ["--associated-repo", repos[name]]
        done = ws.dadaia(*argv)
        assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
        assert "specs upgrade" not in done.stdout + done.stderr
        for name, url in repos.items():
            assert env.git("status", "--porcelain", cwd=ws.path / "repos" / name) == ""
            ws.assert_level_clean(slug, name, url)

    payload = ws.doctor_json("second")
    fixes = [f["fix"] for s in payload["sections"].values() for f in s["findings"]
             if f["verdict"] == "info"]  # fmt: skip
    assert any("specs init --context second" in fix for fix in fixes), fixes
    done = ws.dadaia("specs", "init", "--context", "second")
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
    ws.assert_level_clean("second", "second", repos["second"])


# ── the quickstart block, verbatim ────────────────────────────────────────


@pytest.mark.skipif(_UVX is None, reason="the quickstart block is a `uvx` line, run as printed")
class TestQuickstartVerbatim:
    """The quickstart fixture's three bash blocks run as printed with only ``REPO_URL``
    set — the one other substitution points ``uvx`` at the built wheel instead of PyPI;
    the second files the first backlog entry in a ``backlog`` worktree, the third opens the
    release candidate in its ``wt-rc`` tree. The project's repo carries a version tag, so
    the work branch's version is read from the repo, never typed. The fixture is
    byte-equal to ``docs/quickstart.md`` (the ``workspace-quickstart-fixture`` guard)."""

    def test_the_quickstart_block_runs_as_printed(self, env: Env) -> None:
        text = read_text(_REPO_ROOT / "tests" / "fixtures" / "quickstart.md")
        block, filing, birth = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)[:3]
        url = env.bare("quick", tag="v0.7.3")
        script, count = re.subn(r"^REPO_URL=.*$", f"REPO_URL={url}", block, flags=re.M)
        assert count == 1, block
        script = script.replace("uvx dadaia-workspace", f"uvx --from {env.wheel} dadaia-workspace")
        done = env.run("bash", "-euo", "pipefail", "-c", script, cwd=env.root)
        assert done.returncode == 0, f"quickstart failed:\n{done.stdout}\n{done.stderr}"
        ws = Workspace(env, "demo")
        ws.assert_level_clean("quick", "quick", url)
        version = "0.7.4"
        for n, rest in enumerate((filing, birth), start=2):
            done = env.run("bash", "-euo", "pipefail", "-c", f"SLUG=quick\n{rest}", cwd=ws.path)
            assert done.returncode == 0, (
                f"quickstart block {n} failed:\n{done.stdout}\n{done.stderr}"
            )
        wt = ws.path / "worktrees" / "quick" / version / "wt-backlog-my-first-idea"
        assert env.git("log", "-1", "--format=%s", cwd=wt) == "chore(backlog): new my-first-idea"
        assert "my-first-idea" in env.git("show", "HEAD:specs/backlog/BACKLOG.json", cwd=wt)
        rc = ws.path / "worktrees" / "quick" / version / "rc-1" / "wt-rc"
        candidate = rc / "specs" / "releases" / version
        assert (candidate / "rc-1" / "SPEC.md").is_file()
        assert (candidate / "_RELEASE.json").is_file()
