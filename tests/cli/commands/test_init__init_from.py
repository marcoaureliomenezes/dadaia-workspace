"""`init DIR --from <artifact>` replicates a workspace from one `export-v1` artifact, soft or hard:
the harnesses it names are installed, its contexts registered DEAD, the repos nobody can reach and
the contexts with no remote listed, a `context alive` line printed for each context ALIVE in it;
then `context alive`, `worktree resume` and doctor leave no finding. A hard artifact's members are
validated before anything is written. Real git over bare origins, the real CLI in-process, the real
worktree script. Size: MEDIUM.
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from tests.fixtures.stores import fake_venv
from tests.helpers.oslib import read_text, write_text
from tests.helpers.worktree_ws import commit, git, run

pytestmark = pytest.mark.medium

_runner = CliRunner()
LANE = "0.5.0/wt-backlog-x"
MEMBER = f"app/{LANE}.bundle"


@pytest.fixture
def source(tmp_path: Path) -> tuple[dict[str, object], Path]:
    """The artifact's JSON and a lane bundle: `app` (ALIVE, reachable) holds a lane whose base
    `feature/0.5.0` was never pushed; `ghost` has an unreachable url; `solo` has no remote."""
    origin = tmp_path / "origin" / "app.git"
    origin.parent.mkdir()
    git(tmp_path, "init", "-q", "--bare", str(origin))
    (src := tmp_path / "src").mkdir()
    git(src, "init", "-q")
    commit(src, "README.md", "seed\n")
    git(src, "remote", "add", "origin", str(origin))
    git(src, "push", "-q", "origin", "main", "main:develop")
    git(src, "checkout", "-q", "-b", "feature/0.5.0")
    commit(src, "base.md", "never pushed\n")
    git(src, "checkout", "-q", "-b", f"wt/{LANE}")
    commit(src, "lane.md", "lane\n")
    git(
        src,
        "bundle",
        "create",
        str(bundle := tmp_path / "lane.bundle"),
        f"wt/{LANE}",
        "--not",
        "--remotes=origin",
    )

    def record(name: str, state: str, url: object) -> dict[str, object]:
        return {"slug": name, "name": name, "state": state, "repo_url": url, "associated_repos": []}

    return {
        "schema_version": "export-v1",
        "dadaia_version": "0.5.0",
        "harnesses": ["claude", "codex"],
        "contexts": [
            record("app", "alive", str(origin)),
            record("ghost", "dead", str(tmp_path / "gone.git")),
            record("solo", "dead", None),
        ],
    }, bundle


def _soft(tmp_path: Path, payload: dict[str, object]) -> Path:
    write_text(file := tmp_path / "spec-contexts.json", json.dumps(payload))
    return file


def _hard(
    tmp_path: Path,
    payload: dict[str, object],
    *members: tarfile.TarInfo,
    bundle: Path | None = None,
) -> Path:
    data = json.dumps(payload).encode()
    with tarfile.open(archive := tmp_path / "workspace-export.tar.gz", "w:gz") as tar:
        head = tarfile.TarInfo("spec-contexts.json")
        head.size = len(data)
        tar.addfile(head, io.BytesIO(data))
        for member in members:
            tar.addfile(member, io.BytesIO(b"x" * member.size))
        if bundle:
            tar.add(bundle, arcname=MEMBER)
    return archive


def _findings(output: str) -> set[str]:
    verdicts = json.loads(output)["sections"]
    return {f["verdict"] for section in verdicts.values() for f in section["findings"]}


@pytest.mark.parametrize("kind", ["soft", "hard"])
def test_init_from_replicates_the_workspace_and_what_follows_leaves_no_finding(
    tmp_path: Path,
    source: tuple[dict[str, object], Path],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    payload, bundle = source
    if kind == "soft":
        artifact = _soft(tmp_path, payload)
    else:
        artifact = _hard(tmp_path, payload, bundle=bundle)
    ws = tmp_path / "ws"

    result = _runner.invoke(app, ["init", str(ws), "--from", str(artifact)])

    assert result.exit_code == 0, result.output
    states = ws / ".dadaia" / "states"
    assert JsonHarnessProfileStore().resolve(states, ws).harnesses == ("claude", "codex")
    assert (ws / ".claude").is_dir() and (ws / ".codex").is_dir()
    registry = json.loads(read_text(states / "spec_contexts.json"))["contexts"]
    assert {(c["name"], c["state"]) for c in registry} == {("app", "dead"), ("ghost", "dead")}
    assert "None" not in read_text(states / "spec_contexts.json")
    lines = result.output.splitlines()
    assert [ln for ln in lines if "not replicated: no remote" in ln and "solo" in ln]
    assert [ln for ln in lines if "unreachable" in ln and "ghost" in ln]
    [remote_fix] = [ln for ln in lines if ln.startswith("fix: Agent action: add a remote to")]
    assert "repos/solo" in remote_fix
    assert fix_line(ws, "context", "alive", "app") in result.output
    assert fix_line(ws, "context", "alive", "ghost") not in result.output

    monkeypatch.chdir(ws)
    assert _runner.invoke(app, ["context", "alive", "app"]).exit_code == 0
    fake_venv(ws, cli=True)
    if kind == "hard":
        assert (ws / ".dadaia/dist" / MEMBER).is_file()
        tree = ws / "worktrees" / "app" / LANE
        resumed = run(ws, "resume", str(tree))
        assert resumed.returncode == 0, resumed.stderr
        assert (tree / "lane.md").is_file()
        assert "base.md" in git(ws / "repos/app", "log", "--format=%s", f"wt/{LANE}")
        assert not (ws / ".dadaia/dist" / MEMBER).exists()
    doctor = _runner.invoke(app, ["doctor", "--context", "app", "--json"])
    assert doctor.exit_code == 0, doctor.output
    assert _findings(doctor.stdout) <= {"info"}


def _evil(name: str, kind: bytes, link: str = "") -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type, info.linkname = kind, link
    info.size = 0 if link else 1
    return info


@pytest.mark.parametrize(
    "member",
    [
        _evil("/tmp/dadaia-evil.bundle", tarfile.REGTYPE),
        _evil("../evil.bundle", tarfile.REGTYPE),
        _evil("app/../../evil.bundle", tarfile.REGTYPE),
        _evil(MEMBER, tarfile.SYMTYPE, "../../outside"),
        _evil(MEMBER, tarfile.LNKTYPE, "spec-contexts.json"),
        _evil("README.md", tarfile.REGTYPE),
    ],
    ids=["absolute", "dotdot", "nested-dotdot", "symlink", "hardlink", "unlisted-name"],
)
def test_a_hard_member_outside_the_pattern_refuses_before_anything_is_written(
    tmp_path: Path, source: tuple[dict[str, object], Path], member: tarfile.TarInfo
) -> None:
    artifact = _hard(tmp_path, source[0], member)
    ws = tmp_path / "ws"

    result = _runner.invoke(app, ["init", str(ws), "--from", str(artifact)])

    assert result.exit_code == 1, result.output
    assert len([ln for ln in result.output.splitlines() if ln.startswith("fix: ")]) == 1
    assert not ws.exists()
    assert not (tmp_path / "evil.bundle").exists()


@pytest.mark.parametrize("version", ["export-v0", "export-v2"])
def test_an_artifact_of_another_format_refuses_with_the_re_export_fix_and_writes_nothing(
    tmp_path: Path, source: tuple[dict[str, object], Path], version: str
) -> None:
    artifact = _soft(tmp_path, {**source[0], "schema_version": version})
    ws = tmp_path / "ws"

    result = _runner.invoke(app, ["init", str(ws), "--from", str(artifact)])

    assert result.exit_code == 1, result.output
    assert "fix: Agent action: re-export the artifact with the current dadaia-workspace" in (
        result.output.splitlines()
    )
    assert not ws.exists()
