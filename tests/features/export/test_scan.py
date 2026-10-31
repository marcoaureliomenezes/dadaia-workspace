"""`scan.scan_bundle` reads the objects a bundle adds to a repo and hands them to an injected
matcher; every refusal carries its one fix. Size: SMALL — real git in a tmp repo; the matcher and
the read-failure fix are fakes, since the export feature may not import the chokepoints.
"""

import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import git_line
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.git_scan import GitObjectReadError, ScannedObject
from dadaia_workspace.core.platform import act
from dadaia_workspace.features.export import scan
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.helpers.oslib import write_text
from tests.helpers.worktree_ws import git

_FOUND = {"notes.md": "denylist 'a…z' (line 1)"}
_READ_FIX = act("operator", "the injected read-failure act")


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    """A workspace root holding `repos/r` with an `origin` and one commit beyond it."""
    repo = tmp_path / "repos/r"
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    write_text(repo / "base.md", "base\n")
    git(repo, "add", "base.md")
    git(repo, "commit", "-q", "-m", "base")
    git(tmp_path, "init", "-q", "--bare", str(tmp_path / "origin.git"))
    git(repo, "remote", "add", "origin", str(tmp_path / "origin.git"))
    git(repo, "push", "-q", "origin", "main")
    git(repo, "fetch", "-q", "origin")
    write_text(repo / "notes.md", "carried\n")
    git(repo, "add", "notes.md")
    git(repo, "commit", "-q", "-m", "notes")
    return tmp_path


def _bundle(ws: Path, where: str) -> Path:
    path = ws / where
    path.parent.mkdir(parents=True, exist_ok=True)
    git(ws / "repos/r", "bundle", "create", "-q", str(path), "main", "^origin/main")
    return path


def _match(seen: list[str]) -> Callable[[Iterable[ScannedObject]], dict[str, str]]:
    def match(objects: Iterable[ScannedObject]) -> dict[str, str]:
        seen.extend(o.path for o in objects)
        return _FOUND

    return match


def _scan(ws: Path, bundle: Path, seen: list[str] | None = None) -> dict[str, str]:
    return scan.scan_bundle(ws, bundle, ws / "repos/r", _match([] if seen is None else seen), _fix)


def _fix(_exc: GitObjectReadError, _repo: Path) -> str:
    return _READ_FIX


def test_a_good_bundle_returns_the_matchers_findings_over_the_objects_it_adds(ws: Path) -> None:
    seen: list[str] = []

    assert _scan(ws, _bundle(ws, "out/lane.bundle"), seen) == _FOUND
    assert "notes.md" in seen and "base.md" not in seen


@pytest.mark.parametrize(
    ("where", "fix"),
    [
        ("out/lane.bundle", lambda repo, _bundle: git_line(repo, "fsck")),
        (
            ".dadaia/dist/r/lane.bundle",
            lambda _repo, bundle: act(
                "operator", f"rule whether {bundle} is restored from a copy or discarded"
            ),
        ),
    ],
    ids=["open-lane-fsck", "pause-bundle-operator-act"],
)
def test_a_damaged_header_refuses_with_fsck_or_the_operators_ruling(
    ws: Path, where: str, fix: Callable[[Path, Path], str]
) -> None:
    (bundle := ws / where).parent.mkdir(parents=True)
    bundle.write_bytes(b"# v2 git bundle\n-\n\n")

    with pytest.raises(DadaiaError) as refused:
        _scan(ws, bundle)

    assert refused.value.fix == fix(ws / "repos/r", bundle)
    assert bundle.read_bytes() == b"# v2 git bundle\n-\n\n"


def test_an_object_read_failure_carries_the_injected_fix(
    ws: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: object, **_kwargs: object) -> object:
        raise GitObjectReadError("listing the range failed")

    monkeypatch.setattr(GitSubprocessObjectReader, "new_objects", broken)

    with pytest.raises(DadaiaError) as refused:
        _scan(ws, _bundle(ws, "out/lane.bundle"))

    assert refused.value.fix == _READ_FIX
    assert "listing the range failed" in str(refused.value)


_PAUSE = ".dadaia/dist/r/lane.bundle"


@pytest.mark.parametrize("where", ["out/lane.bundle", _PAUSE], ids=["open-lane", "pause-bundle"])
def test_an_unbundle_out_of_space_refuses_with_gits_reason_and_the_space_act(
    ws: Path, monkeypatch: pytest.MonkeyPatch, where: str
) -> None:
    bundle = _bundle(ws, where)
    real = subprocess.run

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if "unbundle" in argv:
            return subprocess.CompletedProcess(
                argv, 128, b"", b"fatal: write error: No space left on device\n"
            )
        return real(argv, **kwargs)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(DadaiaError) as refused:
        _scan(ws, bundle)

    assert "No space left on device" in str(refused.value)
    assert refused.value.fix == act(
        "agent",
        f"free space and write permission under {ws / '.dadaia/tmp'}, then rerun the export",
    )


def test_a_pause_bundle_whose_pack_is_damaged_still_asks_the_operators_ruling(ws: Path) -> None:
    bundle = _bundle(ws, _PAUSE)
    data = bundle.read_bytes()
    bundle.write_bytes(data[: len(data) - 20])

    with pytest.raises(DadaiaError) as refused:
        _scan(ws, bundle)

    assert refused.value.fix == act(
        "operator", f"rule whether {bundle} is restored from a copy or discarded"
    )


def test_a_git_call_that_hangs_refuses_instead_of_raising_the_timeout(
    ws: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _bundle(ws, "out/lane.bundle")

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        assert kwargs.get("timeout"), "git ran with no timeout and would hang"
        raise subprocess.TimeoutExpired(argv, float(str(kwargs["timeout"])))

    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(DadaiaError) as refused:
        _scan(ws, bundle)

    assert refused.value.fix == _READ_FIX
