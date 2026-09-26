"""``dadaia init <dir> --harness claude --repo <url>`` end to end, through the console script.

Intent: CONTRACT — 0.4.7 FR1 / AC1.1 (T-047-79); 0.4.8 AC1.1/AC1.4 closing (T-048-04).

Size: LARGE, justified — AC1.1 is a statement about the *installed* distribution, not
about any in-process wiring: an operator types one line and the workspace that appears
must pass its own ``doctor``. Every seam below (venv provisioning, asset install, the
clone, the context store, the session binding, the git chokepoint, the doctor's zone
walk) is crossed by a REAL ``dadaia`` process, so nothing this test asserts survives
being demoted to the CLI runner. This is the suite's ONE test that exercises the
installed console script; every narrower contract of FR1 is already covered MEDIUM in
``tests/integration/test_init_with_repo.py``.

Hermetic by construction — no network, no container:

* ``--repo`` is a LOCAL bare repository, so the clone is the real git path with no remote.
* ``HOME`` is a tmp dir and the child environment carries no inherited ``DADAIA_*``.
* The workspace venv is pre-seeded (see ``_seed_venv_entrypoint``). ``tests/conftest.py``'s
  ``_no_real_venv_in_tests`` backstop is an in-process monkeypatch and cannot reach a
  child process, so this test honours the same law on the child's own terms: it uses
  ``ensure_workspace_venv``'s documented idempotent-repair contract (a venv directory
  that already carries an executable ``dadaia`` entrypoint is left alone), which is also
  exactly what doctor's VENV-1 check asserts. No ``venv.create``, no ``pip install``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.platform import PLATFORM

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

_TIMEOUT = 180.0

_CONSOLE_SCRIPT = Path(sys.executable).parent / f"dadaia{PLATFORM.venv_exe_suffix}"


def _child_env(home: Path) -> dict[str, str]:
    """A clean environment: no inherited ``DADAIA_*`` but the suite's fence (the dev CLI's
    own workspace is never this child's: M1's first rung), a tmp ``HOME``, a git identity."""
    keep = "DADAIA_FENCED_ROOTS"
    env = {k: v for k, v in os.environ.items() if not k.startswith("DADAIA_") or k == keep}
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        PATH=f"{_CONSOLE_SCRIPT.parent}{os.pathsep}{env.get('PATH', '')}",
        COLUMNS="200",
        NO_COLOR="1",
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.invalid",
        GIT_CONFIG_GLOBAL=str(home / "gitconfig"),
        GIT_CONFIG_SYSTEM=os.devnull,
    )
    return env


def _dadaia(
    *argv: str, cwd: Path, home: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = _child_env(home)
    env.update(extra_env or {})
    return subprocess.run(
        [str(_CONSOLE_SCRIPT), *argv],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


def _git(*args: str, cwd: Path, home: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=_child_env(home))


def _seed_venv_entrypoint(workspace: Path) -> None:
    """Materialise ``.dadaia/.venv`` with an executable ``dadaia`` entrypoint.

    The child process' equivalent of the suite's no-real-venv backstop: with the
    entrypoint already present, ``ensure_workspace_venv`` takes its idempotent no-op
    path and the test never builds a 30-50 MB venv nor runs ``pip``.
    """
    bin_dir = workspace / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    bin_dir.mkdir(parents=True)
    entry = bin_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text(f"#!{sys.executable}\n", encoding="utf-8")
    entry.chmod(0o755)


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture()
def origin(tmp_path: Path, home: Path) -> Path:
    """A local bare repo ``demo-project.git`` carrying one commit on ``main``."""
    bare = tmp_path / "origin" / "demo-project.git"
    bare.parent.mkdir(parents=True)
    _git("init", "--bare", "--initial-branch=main", str(bare), cwd=tmp_path, home=home)
    work = tmp_path / "seed"
    work.mkdir()
    _git("init", "--initial-branch=main", cwd=work, home=home)
    (work / "README.md").write_text("# demo-project\n", encoding="utf-8")
    _git("add", "README.md", cwd=work, home=home)
    _git("commit", "-m", "seed", cwd=work, home=home)
    _git("remote", "add", "origin", str(bare), cwd=work, home=home)
    _git("push", "-u", "origin", "main", cwd=work, home=home)
    return bare


@pytest.mark.skipif(
    not _CONSOLE_SCRIPT.is_file(),
    reason=f"the dadaia console script is not installed next to {sys.executable}",
)
def test_one_line_bootstrap_yields_a_doctor_clean_workspace(
    tmp_path: Path, home: Path, origin: Path
) -> None:
    """AC1.1: one line, then ``doctor`` exit 0 and the repo ALIVE as ``main_repo``."""
    workspace = tmp_path / "demo"
    workspace.mkdir()
    _seed_venv_entrypoint(workspace)

    init = _dadaia(
        "init", "demo", "--harness", "claude", "--repo", str(origin), cwd=tmp_path, home=home
    )
    assert init.returncode == 0, f"init failed:\n{init.stdout}\n{init.stderr}"

    # 0.4.8 AC1.1/AC1.4: a short closing that names the CLI by its absolute venv path.
    assert len(init.stdout.splitlines()) <= 12, init.stdout
    cli = workspace / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    assert f"CLI: {cli / f'dadaia{PLATFORM.venv_exe_suffix}'}" in init.stdout.splitlines()

    doctor = _dadaia("doctor", cwd=workspace, home=home)
    assert doctor.returncode == 0, f"doctor is not clean:\n{doctor.stdout}\n{doctor.stderr}"

    # ADR 0038: init binds nothing and prints no export line; `context show` names
    # the context explicitly.
    assert "export DADAIA_" not in init.stdout, init.stdout

    show = _dadaia("context", "show", "demo-project", "--json", cwd=workspace, home=home)
    assert show.returncode == 0, f"context show failed:\n{show.stdout}\n{show.stderr}"
    record = json.loads(show.stdout)
    assert record["main_repo"] == "demo-project"
    assert record["state"] == "alive"

    # The git chokepoint is installed from — and byte-equal to — the shipped gate.
    target, source = workspace_layout.INSTALLED_GIT_HOOKS[0]
    installed = workspace / "repos" / "demo-project" / ".git" / "hooks" / target
    assert installed.read_bytes() == (workspace_layout.public_scripts_dir() / source).read_bytes()


# ── the venv mirrors the RUNNING distribution, never the index ───────────────────
#
# Bug init-venv-installs-index-version-not-running-distribution. The test above
# pre-seeds `.dadaia/.venv`, so it never crosses the provisioning seam — which is
# exactly why a uvx bootstrap could project HEAD's assets into a workspace whose venv
# ran PyPI's 0.4.6. The test below crosses it for real, hermetically.

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DECOY_MODULE = "_decoy_marker_from_the_index.py"


def _build_wheel(source: Path, dest: Path) -> Path:
    """Build *source* into a wheel under *dest*, offline.

    ``--no-build-isolation`` is what makes it offline: the build backend is already
    installed beside this interpreter, so pip never reaches for an index.
    """
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603
        [
            str(Path(sys.executable).parent / "pip"),
            "wheel",
            "--quiet",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(dest),
            str(source),
        ],  # fmt: skip
        check=True,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        env={**os.environ, "PIP_NO_INDEX": "1"},
    )
    built = sorted(dest.glob("dadaia_workspace-*.whl"))
    assert len(built) == 1, f"expected one wheel in {dest}, got {built}"
    return built[0]


def _repack_dependency_closure(dest: Path) -> Path:
    """Re-pack this distribution's installed runtime dependencies into *dest*.

    The offline dependency mirror both venvs resolve against, built with the product's
    OWN :func:`repack_installed_wheel` — the same function the fix under test uses for
    ``dadaia-workspace`` itself. 17 wheels, well under a second.
    """
    from dadaia_workspace.infrastructure.python_env import repack_installed_wheel

    dest.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    stack = ["dadaia-workspace"]
    while stack:
        name = stack.pop()
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        for requirement in dist.requires or []:
            if "extra ==" in requirement:
                continue
            dependency = re.split(r"[<>=!~;\[\s]", requirement.strip())[0]
            if dependency:
                stack.append(dependency)
        if key != "dadaia-workspace":
            repack_installed_wheel(dest, dist=dist)
    return dest


def _decoy_source(tmp_path: Path) -> Path:
    """A copy of this distribution carrying ONE extra module, built at the SAME version.

    This is the index's side of the bug, reproduced without a network: under the
    release-please floor an unpublished build and the last published release declare
    the same version, so a pin on that version resolves to whichever bytes the index
    happens to hold. Here those bytes are marked.
    """
    source = tmp_path / "decoy-src"
    (source / "dadaia_workspace").mkdir(parents=True)
    for name in ("pyproject.toml", "README.md"):
        shutil.copy2(_REPO_ROOT / name, source / name)
    shutil.copytree(
        _REPO_ROOT / "dadaia_workspace", source / "dadaia_workspace", dirs_exist_ok=True
    )
    (source / "dadaia_workspace" / _DECOY_MODULE).write_text("INDEX = True\n", encoding="utf-8")
    return source


@pytest.mark.skipif(
    not _CONSOLE_SCRIPT.is_file(),
    reason=f"the dadaia console script is not installed next to {sys.executable}",
)
def test_the_workspace_venv_carries_the_bootstrappers_own_bytes(tmp_path: Path, home: Path) -> None:
    """Intent: CONTRACT — bug init-venv-installs-index-version-not-running-distribution.

    The consumer shape, end to end and hermetic: a NON-checkout install of this
    distribution (a wheel in its own venv — pipx/uvx/a git bootstrap) runs ``init``, and
    the workspace venv it provisions must carry ITS bytes.

    The index is present and poisoned: ``PIP_FIND_LINKS`` serves a wheel of the same
    version carrying one extra module, and ``PIP_NO_INDEX`` keeps every other resolution
    offline. Under the old ``dadaia-workspace==<running version>`` pin that decoy is
    what pip resolved and installed. The assertion is therefore not "a version matches"
    — the version is identical by construction, which is the whole bug — but "the decoy
    module did not come along", plus the ``<dir>`` argument the pre-c8 published CLI
    does not have.

    Size: LARGE, justified — two real venvs and two real wheel builds. Nothing smaller
    reaches the seam: it exists only between an installed distribution and the venv it
    provisions. ``tests/conftest.py``'s ``_no_real_venv_in_tests`` backstop is an
    in-process monkeypatch; every venv here is built by a CHILD process, which is the
    same accommodation the sibling test documents.
    """
    real_wheel = _build_wheel(_REPO_ROOT, tmp_path / "dist")
    deps = _repack_dependency_closure(tmp_path / "deps")
    decoy_dir = tmp_path / "decoy-dist"
    decoy_wheel = _build_wheel(_decoy_source(tmp_path), decoy_dir)
    assert decoy_wheel.name == real_wheel.name, "the decoy must be indistinguishable by version"

    # The bootstrapper: this distribution installed as a WHEEL, so `_install_spec` takes
    # the consumer path (no pyproject.toml beside the package) rather than the editable
    # self-hosting one.
    bootstrapper = tmp_path / "bootstrapper"
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "venv", str(bootstrapper)], check=True, capture_output=True
    )
    boot_bin = bootstrapper / PLATFORM.venv_scripts_dir
    subprocess.run(  # noqa: S603
        [str(boot_bin / "pip"), "install", "--quiet", str(real_wheel)],
        check=True,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        env={**os.environ, "PIP_NO_INDEX": "1", "PIP_FIND_LINKS": str(deps)},
    )

    env = _child_env(home)
    # The ONE test that must NOT inherit `tests/conftest.py`'s session-wide PYTHONPATH:
    # that law forces every child to import THIS checkout, which is precisely the
    # source-checkout shape this test exists to avoid. The bootstrapper must see its
    # own installed wheel and take the consumer path.
    env.pop("PYTHONPATH", None)
    env.update(PIP_NO_INDEX="1", PIP_FIND_LINKS=f"{deps} {decoy_dir}")
    init = subprocess.run(  # noqa: S603
        [str(boot_bin / f"dadaia{PLATFORM.venv_exe_suffix}"), "init", "ws", "--harness", "claude"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )
    assert init.returncode == 0, f"init failed:\n{init.stdout}\n{init.stderr}"

    venv_bin = tmp_path / "ws" / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    site = sorted((tmp_path / "ws" / ".dadaia" / ".venv").rglob("dadaia_workspace/__init__.py"))
    assert site, "the workspace venv carries no dadaia_workspace at all"
    assert not (site[0].parent / _DECOY_MODULE).exists(), (
        "the workspace venv carries the INDEX's bytes, not the bootstrapper's"
    )

    help_text = subprocess.run(  # noqa: S603
        [str(venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"), "init", "--help"],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        env={k: v for k, v in _child_env(home).items() if k != "PYTHONPATH"},
    )
    assert help_text.returncode == 0, help_text.stderr
    assert "DIR" in help_text.stdout, (
        f"the venv's CLI predates the required <dir> argument:\n{help_text.stdout}"
    )
