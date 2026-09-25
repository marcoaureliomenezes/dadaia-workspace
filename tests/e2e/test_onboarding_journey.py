"""The onboarding journey in three levels, driven through ``uvx`` over file:// bare repos.

Intent: CONTRACT — 0.4.8 FR8 / AC8.1, AC8.2 (T-048-01); 0.5.0 FR10 / AC10.1–AC10.3
(T-050-21: the autopilot loop executes only printed fix lines).

Owner: dd-software-engineer (LARGE-tier e2e; tests/AGENTS.md "every file names an owner").

Size: LARGE, justified — FR8 is a statement about the *published shape* of the tool: an
operator runs ``uvx --from <wheel> dadaia-workspace …`` and walks level 1 (workspace),
level 2 (Spec Context Project) and level 3 (canonical specs). Every seam the journey
crosses — uvx's own environment, the workspace venv provisioning, the clone, the hook,
the specs scaffold, doctor — is crossed by REAL child processes; no in-process runner
reaches them. This is the durable form of the 0.4.8 onboarding audit script.

Layout — one class per AC8.1 scenario, one test per level. Every level of a scenario
runs its predecessors first (memoized on the scenario object), so a test is order-free
and a level flips to green by deleting ONE ``xfail`` marker naming the task that
delivers it: level 1 / init -> T-048-04, level 2 -> T-048-03, level 3 -> T-048-05,
upgrade -> T-048-06, guidance -> T-048-07. After every level (AC8.2) doctor reports
0 errors and the user repo's HEAD equals its remote's.

Real venvs are built here by CHILD processes (``uvx`` and ``init``);
``tests/conftest.py``'s ``_no_real_venv_in_tests`` backstop is an in-process monkeypatch
and does not reach them — the same accommodation ``test_one_line_bootstrap`` documents.
Needs network for dependency resolution. CI puts ``uv`` on PATH and sets
``DADAIA_REQUIRE_UVX`` (T-048-11); without uvx the launcher is a child-built venv holding
the same wheel, and only the verbatim-quickstart test (a literal ``uvx`` line) skips.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.platform import PLATFORM
from tests.helpers.previous_release import previous_release, published_releases

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
_SOURCE_VERSION: str = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text("utf-8"))["tool"][
    "poetry"
]["version"]
# Local version segment: the built wheel differs from the last PyPI release (risk §8).
_E2E_VERSION = f"{_SOURCE_VERSION}+e2e"


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
        harness_ids = ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("DADAIA_") and k not in harness_ids}  # fmt: skip
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
        self.git("config", "--global", "init.defaultBranch", "main", cwd=root)
        # An operator's identity lives in git config; `context baseline` reads it there.
        self.git("config", "--global", "user.name", "t", cwd=root)
        self.git("config", "--global", "user.email", "t@example.invalid", cwd=root)
        self._launchers: dict[str, Path] = {}

    def run(self, *argv: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            list(argv), cwd=cwd, env=self.env, capture_output=True, text=True, timeout=_TIMEOUT
        )

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

    def bare(self, name: str, specs: str = "none") -> str:
        """A file:// bare repo ``<name>.git`` with one commit; *specs* seeds its tree."""
        work = self.fixtures / f"src-{name}"
        (work / "app").mkdir(parents=True)
        (work / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        (work / "app" / "core.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        if specs == "foreign":
            (work / "specs" / "features").mkdir(parents=True)
            (work / "specs" / "features" / "login.md").write_text("# my spec\n", encoding="utf-8")
            (work / "specs" / "README.md").write_text("x\n", encoding="utf-8")
        elif specs == "dadaia6":
            (work / "specs").mkdir()
            (work / "specs" / "constitution.md").write_text(
                "---\nspecs_pattern_version: 6\n---\n# constitution\n", encoding="utf-8"
            )
        self.git("init", "-q", cwd=work)
        self.git("add", "-A", cwd=work)
        self.git("commit", "-qm", "init", cwd=work)
        bare = self.fixtures / f"{name}.git"
        self.git("clone", "-q", "--bare", str(work), str(bare), cwd=self.root)
        return f"file://{bare}"


class Workspace:
    """One workspace under test and the AC8.2 assertions over it."""

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
        """AC8.2: doctor 0 errors and the user repo's HEAD equals its remote's."""
        self.doctor_json(context)
        repo = self.path / "repos" / repo_slug
        head = self.env.git("rev-parse", "HEAD", cwd=repo)
        remote = self.env.git("ls-remote", url, "HEAD", cwd=repo).split()[0]
        assert head == remote, f"{repo_slug}: HEAD {head} != remote {remote}"


class Scenario:
    """Memoized levels: each level runs once, a failure is re-raised to every later caller."""

    def __init__(self, env: Env) -> None:
        self.env = env
        self._done: dict[str, BaseException | None] = {}

    def once(self, key: str, step: Callable[[], None]) -> None:
        if key not in self._done:
            try:
                step()
                self._done[key] = None
            except BaseException as exc:
                self._done[key] = exc
                raise
        failure = self._done[key]
        if failure is not None:
            raise failure


def _assert_init_quiet(ws: Workspace, done: subprocess.CompletedProcess[str]) -> None:
    """AC1.1: exit 0, ≤ 12 lines, the absolute venv entrypoint path, no bare verb (AC1.4)."""
    assert done.returncode == 0, f"init failed:\n{done.stdout}\n{done.stderr}"
    lines = done.stdout.splitlines()
    assert len(lines) <= 12, f"init printed {len(lines)} lines:\n{done.stdout}"
    assert str(ws.dadaia_bin) in done.stdout, done.stdout
    assert not re.search(r"(^|[\s`])dadaia (context|doctor|specs) ", done.stdout), done.stdout


def _specs_scaffolded(ws: Workspace, slug: str) -> None:
    """AC4.1/4.2: canon present, English law sections, nothing committed."""
    specs = ws.path / "repos" / slug / "specs"
    assert (specs / "constitution.md").is_file()
    arch = (specs / "memory" / "ARCHITECTURE.md").read_text("utf-8")
    quality = (specs / "memory" / "QUALITY.md").read_text("utf-8")
    for heading in ("## Principles", "## Tech Stack", "## Structure"):
        assert heading in arch
    for heading in ("## Principles", "## Test architecture", "## Gates"):
        assert heading in quality


# ── fixtures ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """This checkout built offline at ``<version>+e2e``."""
    root = tmp_path_factory.mktemp("wheel")
    source = root / "src"
    source.mkdir()
    shutil.copy2(_REPO_ROOT / "README.md", source / "README.md")
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text("utf-8")
    pyproject = pyproject.replace(
        f'version = "{_SOURCE_VERSION}"', f'version = "{_E2E_VERSION}"', 1
    )
    (source / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    shutil.copytree(
        _REPO_ROOT / "dadaia_workspace",
        source / "dadaia_workspace",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    dist = root / "dist"
    subprocess.run(  # noqa: S603
        [
            str(Path(sys.executable).parent / "pip"),
            "wheel",
            "--quiet",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(dist),
            str(source),
        ],  # fmt: skip
        check=True,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        env={**os.environ, "PIP_NO_INDEX": "1"},
    )
    (built,) = dist.glob("dadaia_workspace-*.whl")
    assert "+e2e" in built.name, built.name
    return built


@pytest.fixture(scope="class")
def env(tmp_path_factory: pytest.TempPathFactory, wheel: Path) -> Env:
    return Env(tmp_path_factory.mktemp("journey"), wheel)


# ── scenario 1: greenfield ───────────────────────────────────────────────────────


class Greenfield(Scenario):
    """``init --repo`` (levels 1+2 in one line, AC1.5) then ``specs init`` (level 3)."""

    def __init__(self, env: Env) -> None:
        super().__init__(env)
        self.url = env.bare("green")
        self.ws = Workspace(env, "demo")

    def level1(self) -> None:
        def step() -> None:
            done = self.env.uvx("init", "demo", "--harness", "claude", "--repo", self.url)
            _assert_init_quiet(self.ws, done)
            repo = self.ws.path / "repos" / "green"
            assert self.env.git("status", "--porcelain", cwd=repo) == ""  # AC3.6
            self.ws.assert_level_clean("green", "green", self.url)

        self.once("level1", step)

    def guidance(self) -> None:
        def step() -> None:
            self.level1()
            payload = self.ws.doctor_json("green")
            fixes = [
                f["fix"]
                for section in payload["sections"].values()
                for f in section["findings"]
                if f["verdict"] == "info"
            ]
            assert any("specs init --context green" in fix for fix in fixes), fixes  # AC6.1

        self.once("guidance", step)

    def level3(self) -> None:
        def step() -> None:
            self.guidance()  # observed before level 3 changes the answer (test order is random)
            done = self.ws.dadaia("specs", "init", "--context", "green")
            assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
            _specs_scaffolded(self.ws, "green")
            self.ws.assert_level_clean("green", "green", self.url)  # HEAD unchanged

        self.once("level3", step)


@pytest.fixture(scope="class")
def greenfield(env: Env) -> Greenfield:
    return Greenfield(env)


class TestGreenfield:
    def test_level1_init_with_repo(self, greenfield: Greenfield) -> None:
        greenfield.level1()

    def test_guidance_names_specs_init(self, greenfield: Greenfield) -> None:
        greenfield.guidance()

    def test_level3_specs_init(self, greenfield: Greenfield) -> None:
        greenfield.level3()


# ── the plain three-verb path shared by the specs-carrying scenarios ────────────


class ThreeLevels(Scenario):
    """``init`` (level 1) -> ``context create --main-repo <url>`` (level 2) -> ``specs init``."""

    specs = "none"
    slug = "proj"
    associated: tuple[str, ...] = ()

    def __init__(self, env: Env) -> None:
        super().__init__(env)
        self.url = env.bare(self.slug, self.specs)
        self.assoc_urls = [env.bare(name) for name in self.associated]
        self.ws = Workspace(env, "ws")

    def level1(self) -> None:
        def step() -> None:
            _assert_init_quiet(self.ws, self.env.uvx("init", "ws", "--harness", "claude"))
            self.ws.doctor_json()

        self.once("level1", step)

    def level2(self) -> None:
        def step() -> None:
            self.level1()
            argv = ["context", "create", self.slug, "--main-repo", self.url]
            for url in self.assoc_urls:
                argv += ["--associated-repo", url]
            done = self.ws.dadaia(*argv)
            assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
            assert "specs upgrade" not in done.stdout + done.stderr  # AC4.7
            for slug in (self.slug, *self.associated):
                repo = self.ws.path / "repos" / slug
                assert self.env.git("status", "--porcelain", cwd=repo) == ""  # AC3.6
            self.ws.assert_level_clean(self.slug, self.slug, self.url)
            for slug, url in zip(self.associated, self.assoc_urls, strict=True):
                self.ws.assert_level_clean(self.slug, slug, url)

        self.once("level2", step)

    def level3(self) -> None:
        def step() -> None:
            self.level2()
            done = self.ws.dadaia("specs", "init", "--context", self.slug)
            assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
            _specs_scaffolded(self.ws, self.slug)
            self.ws.assert_level_clean(self.slug, self.slug, self.url)

        self.once("level3", step)


# ── scenario 2: dadaia v6 specs ──────────────────────────────────────────────────


class DadaiaV6(ThreeLevels):
    specs = "dadaia6"
    slug = "dad6"

    def level3(self) -> None:
        super().level3()
        head = (self.ws.path / "repos" / self.slug / "specs" / "constitution.md").read_text("utf-8")
        assert "specs_pattern_version: 7" in head  # AC4.3


@pytest.fixture(scope="class")
def dadaia_v6(env: Env) -> DadaiaV6:
    return DadaiaV6(env)


class TestDadaiaV6Specs:
    def test_level1_init(self, dadaia_v6: DadaiaV6) -> None:
        dadaia_v6.level1()

    def test_level2_context_create(self, dadaia_v6: DadaiaV6) -> None:
        dadaia_v6.level2()

    def test_level3_upgrades_v6_to_v7(self, dadaia_v6: DadaiaV6) -> None:
        dadaia_v6.level3()


# ── scenario 3: foreign specs ────────────────────────────────────────────────────


class Foreign(ThreeLevels):
    specs = "foreign"
    slug = "foreign"

    def level3(self) -> None:
        def step() -> None:
            self.level2()
            repo = self.ws.path / "repos" / self.slug
            before = {
                p.relative_to(repo / "specs"): p.read_bytes()
                for p in (repo / "specs").rglob("*")
                if p.is_file()
            }
            refused = self.ws.dadaia("specs", "init", "--context", self.slug)
            assert refused.returncode == 2, refused.stdout + refused.stderr  # AC4.4
            assert "--replace-foreign" in refused.stdout + refused.stderr
            done = self.ws.dadaia("specs", "init", "--context", self.slug, "--replace-foreign")
            assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
            after = {rel: (repo / "specs-bkp" / rel).read_bytes() for rel in before}
            assert after == before  # AC4.5 byte-identical
            _specs_scaffolded(self.ws, self.slug)
            self.ws.assert_level_clean(self.slug, self.slug, self.url)
            files = {p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}
            self.ws.dadaia("doctor", "--context", self.slug, "--fix")
            remaining = {p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}
            assert files <= remaining, files - remaining  # AC4.6

        self.once("level3", step)


@pytest.fixture(scope="class")
def foreign(env: Env) -> Foreign:
    return Foreign(env)


class TestForeignSpecs:
    def test_level1_init(self, foreign: Foreign) -> None:
        foreign.level1()

    def test_level2_context_create(self, foreign: Foreign) -> None:
        foreign.level2()

    def test_level3_replace_foreign_keeps_bytes(self, foreign: Foreign) -> None:
        foreign.level3()


# ── scenario 4: second project with an associated repo ───────────────────────────


class SecondProject(ThreeLevels):
    slug = "second"
    associated = ("assoc",)


@pytest.fixture(scope="class")
def second(env: Env) -> SecondProject:
    return SecondProject(env)


class TestSecondProjectWithAssociated:
    def test_level1_init(self, second: SecondProject) -> None:
        second.level1()

    def test_level2_create_clones_main_and_associated(self, second: SecondProject) -> None:
        second.level2()

    def test_level3_specs_init(self, second: SecondProject) -> None:
        second.level3()


# ── scenario 5: failed create, then the corrected retry ─────────────────────────


class FailedCreate(ThreeLevels):
    slug = "retry"

    def level2(self) -> None:
        def step() -> None:
            self.level1()
            bad = f"file://{self.env.fixtures / 'nothere.git'}"
            failed = self.ws.dadaia("context", "create", self.slug, "--main-repo", bad)
            assert failed.returncode == 1, failed.stdout + failed.stderr  # AC3.4
            assert "fix:" in failed.stdout + failed.stderr  # AC3.5
            assert not (self.ws.path / "repos" / "nothere").exists()
            listed = self.ws.dadaia("context", "list", "--json")
            assert self.slug not in listed.stdout, listed.stdout  # no context record
            super(FailedCreate, self).level2()

        self.once("level2-retry", step)


@pytest.fixture(scope="class")
def failed_create(env: Env) -> FailedCreate:
    return FailedCreate(env)


class TestFailedCreateThenRetry:
    def test_level1_init(self, failed_create: FailedCreate) -> None:
        failed_create.level1()

    def test_level2_failure_leaves_nothing_then_retry_succeeds(
        self, failed_create: FailedCreate
    ) -> None:
        failed_create.level2()


# ── scenario 6: re-init is the upgrade ───────────────────────────────────────────


# ── FR10: the autopilot — an agent loops doctor -> printed fix until nothing is pending ──

_AUTOPILOT_CAP = 10


class Autopilot(Scenario):
    """AC10.1: one ``init … --repo`` line, then ONLY the ONBOARDING fix lines doctor prints —
    ``shlex.split`` and run; the ``agent`` step by a scripted stand-in filling memory."""

    def __init__(self, env: Env, specs: str) -> None:
        super().__init__(env)
        self.slug = f"auto-{specs}"
        self.url = env.bare(self.slug, specs)
        self.ws = Workspace(env, f"ws-{specs}")
        self.steps: list[str] = []
        env.env["DADAIA_SESSION_ID"] = f"autopilot-{specs}"

    def _next(self) -> dict[str, Any] | None:
        done = self.ws.dadaia("doctor", "--json")
        payload = json.loads(done.stdout)
        found = [f for sec in payload["sections"].values() for f in sec["findings"]
                 if f["code"] == "ONBOARDING"]  # fmt: skip
        return found[0] if found else None

    def _stand_in_first_pass(self) -> None:
        """What `dd-product-engineer` does in the first pass, scripted: real memory content."""
        specs = self.ws.path / "repos" / self.slug / "specs"
        memory = specs / "memory"
        for name in ("ARCHITECTURE.md", "QUALITY.md"):
            path = memory / name
            path.write_text(
                path.read_text("utf-8") + "\n- `app/core.py` holds the one function `f`.\n",
                encoding="utf-8",
            )
        atom = memory / "product" / "app" / "core.md"
        atom.parent.mkdir(parents=True, exist_ok=True)
        atom.write_text(
            "---\nslug: core\ntitle: core\ntldr: The app's one function.\n"
            "summary: app/core.py exposes f, returning 1.\ntags: [core]\n"
            "sources:\n  - app/core.py\n---\n\n## The contract\n\n- `f()` returns 1.\n",
            encoding="utf-8",
        )
        memory_py = (
            self.ws.path / ".agents" / "skills" / "dd-spec-navigator" / "scripts" / "memory.py"
        )
        for verb in (("catalog", "generate"), ("check",)):
            done = self.env.run(sys.executable, str(memory_py), *verb, "--specs", str(specs),
                                cwd=self.ws.path)  # fmt: skip
            assert done.returncode == 0, f"memory.py {verb}:\n{done.stdout}{done.stderr}"

    def journey(self) -> None:
        def step() -> None:
            done = self.env.uvx(
                "init", self.ws.path.name, "--harness", "claude", "--repo", self.url
            )
            _assert_init_quiet(self.ws, done)
            for _ in range(_AUTOPILOT_CAP):
                finding = self._next()
                if finding is None:
                    break
                self.steps.append(finding["step"])
                if finding["kind"] == "agent":
                    self._stand_in_first_pass()
                    continue
                ran = self.env.run(*shlex.split(finding["fix"]), cwd=self.ws.path)
                assert ran.returncode == 0, (
                    f"fix of step {finding['step']} failed: {finding['fix']}\n"
                    f"{ran.stdout}{ran.stderr}"
                )
            else:
                pytest.fail(f"the autopilot hit the cap of {_AUTOPILOT_CAP}: {self.steps}")

        self.once("journey", step)

    def assert_published(self) -> None:
        """AC10.2/AC10.3: principal, integration and <work>0.1.0 on the remote; the work
        branch carries the gitflow block; doctor clean; HEAD == upstream."""
        self.journey()
        repo = self.ws.path / "repos" / self.slug
        heads = self.env.git("ls-remote", "--heads", self.url, cwd=repo)
        for branch in ("main", "develop", "feature/0.1.0"):
            assert f"refs/heads/{branch}" in heads, heads
        constitution = self.env.git("show", "origin/feature/0.1.0:specs/constitution.md", cwd=repo)
        assert "gitflow:" in constitution, constitution
        self.ws.doctor_json(self.slug)
        head = self.env.git("rev-parse", "HEAD", cwd=repo)
        assert head == self.env.git("rev-parse", "@{u}", cwd=repo)
        assert self.steps[-1] == "publish" and "first-pass" in self.steps, self.steps


@pytest.fixture(scope="class", params=["none", "dadaia6", "foreign"])
def autopilot(request: pytest.FixtureRequest, env: Env) -> Autopilot:
    return Autopilot(env, request.param)


class TestAutopilot:
    def test_the_printed_fix_lines_alone_publish_the_project(self, autopilot: Autopilot) -> None:
        autopilot.assert_published()
        if autopilot.slug == "auto-foreign":
            repo = autopilot.ws.path / "repos" / autopilot.slug
            tree = autopilot.env.git("ls-tree", "-r", "--name-only", "HEAD", cwd=repo)
            assert "specs-bkp/features/login.md" in tree.splitlines(), tree


class Upgrade(Scenario):
    """A workspace born on the previous PyPI release, re-inited with the ``+e2e`` wheel."""

    def __init__(self, env: Env) -> None:
        super().__init__(env)
        self.url = env.bare("green")
        self.ws = Workspace(env, "up")

    def upgrade(self) -> None:
        def step() -> None:
            previous = previous_release(_SOURCE_VERSION, published_releases())
            born = self.env.uvx(
                "init", "up", "--harness", "claude", "--repo", self.url,
                source=f"dadaia-workspace=={previous}",
            )  # fmt: skip
            assert born.returncode == 0, f"{born.stdout}\n{born.stderr}"
            # The previous release committed its specs baseline into the user repo at
            # birth (the behaviour D6 retires); the upgrade must not move HEAD further.
            repo = self.ws.path / "repos" / "green"
            head = self.env.git("rev-parse", "HEAD", cwd=repo)
            done = self.env.uvx("init", "up")  # AC2.1: no --harness needed
            assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
            assert f"upgraded {previous} -> {_E2E_VERSION}" in done.stdout, done.stdout
            version = self.ws.dadaia("--version")
            assert _E2E_VERSION in version.stdout, version.stdout
            # The upgrade never writes a user repo; level 3 re-run refreshes its specs law.
            refreshed = self.ws.dadaia("specs", "init", "--context", "green")
            assert refreshed.returncode == 0, f"{refreshed.stdout}\n{refreshed.stderr}"
            self.ws.doctor_json("green")
            assert self.env.git("rev-parse", "HEAD", cwd=repo) == head
            again = self.env.uvx("init", "up")  # AC2.2
            assert again.returncode == 0 and f"already at {_E2E_VERSION}" in again.stdout

        self.once("upgrade", step)


@pytest.fixture(scope="class")
def upgrade(env: Env) -> Upgrade:
    return Upgrade(env)


class TestReinitUpgrade:
    def test_reinit_upgrades_from_previous_pypi(self, upgrade: Upgrade) -> None:
        upgrade.upgrade()


# ── AC7.1: the quickstart block, verbatim ────────────────────────────────────────


@pytest.mark.skipif(_UVX is None, reason="the quickstart block is a `uvx` line, run as printed")
class TestQuickstartVerbatim:
    """AC7.1: docs/quickstart.md's first bash block runs as printed with only ``REPO_URL``
    set — the one other substitution points ``uvx`` at the built wheel instead of PyPI."""

    def test_the_quickstart_block_runs_as_printed(self, env: Env) -> None:
        text = (_REPO_ROOT / "docs" / "quickstart.md").read_text("utf-8")
        block = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)[0]
        url = env.bare("quick")
        script, count = re.subn(r"^REPO_URL=.*$", f"REPO_URL={url}", block, flags=re.M)
        assert count == 1, block
        script = script.replace("uvx dadaia-workspace", f"uvx --from {env.wheel} dadaia-workspace")
        done = env.run("bash", "-euo", "pipefail", "-c", script, cwd=env.root)
        assert done.returncode == 0, f"quickstart failed:\n{done.stdout}\n{done.stderr}"
        Workspace(env, "demo").assert_level_clean("quick", "quick", url)
