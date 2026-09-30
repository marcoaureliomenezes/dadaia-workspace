"""Intent: CONTRACT — sa-registry-schema-version-has-three-grammars.

The store, ``migrate`` and the doctor ask ONE grammar (``parse_schema_version``), so a
registry the context verbs read is exactly one ``migrate --yes`` leaves untouched.
Supersedes test_cli_migrate_state.py and the store's legacy-refusal table.

size: MEDIUM (in-process CLI over a tmp workspace; one POSIX subprocess runs the fix).
"""

from __future__ import annotations

import json
import os
import shlex
import site
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()
_ALIVE = {"name": "alpha", "state": "alive", "repo_slug": "alpha", "repo_url": "u",
          "created_at": "t", "associated_repos": [{"slug": "beta", "url": "u2"}]}  # fmt: skip
_DEAD = {**_ALIVE, "name": "gamma", "state": "dead"}
_ATIVO = {"name": "delta", "state": "ativo", "repo_slug": "delta", "repo_url": "",
          "created_at": "t", "is_primary": True, "activated_at": "2026-05-01"}  # fmt: skip


@pytest.fixture
def ws(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _registry(ws: Path, version: object, rows: list[dict[str, object]]) -> Path:
    path = ws / ".dadaia" / "states" / "spec_contexts.json"
    body = {"contexts": rows} if version is None else {"schema_version": version, "contexts": rows}
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("version", "rows", "readable"),
    [(2, [_ALIVE], True), ("2", [_ALIVE], True), (3, [_ALIVE], True), ("3", [_ALIVE], True),
     (None, [_ALIVE], True), (None, [_ATIVO], False), (0, [_ALIVE], False),
     ("1", [_ATIVO], False), ("3", [_ALIVE, _ATIVO], False), (4, [_ALIVE], False),
     ("4", [_ALIVE], False), ("banana", [_ALIVE], False)],
)  # fmt: skip
def test_readable_iff_migrate_is_a_no_op(
    ws: Path, version: object, rows: list[dict[str, object]], readable: bool
) -> None:
    """sa-registry-schema-version-has-three-grammars#B1, sa-registry-schema-version-has-three-grammars#B2,
    sa-registry-schema-version-has-three-grammars#B3: int/str 2 and 3 read in
    `context list` and `context show`; a newer version says "newer than this dadaia",
    never advises migrate, and migrate changes nothing; the store reads it ⇔ migrate is
    a no-op, and once migrated the store reads it."""
    path = _registry(ws, version, rows)
    before = path.read_bytes()

    listed = _runner.invoke(app, ["context", "list"])
    migrated = _runner.invoke(app, ["migrate", "--yes"])

    assert (listed.exit_code == 0) is readable, listed.output
    assert (migrated.exit_code == 0 and path.read_bytes() == before) is readable
    if readable:
        shown = _runner.invoke(app, ["context", "show", "alpha", "--json"])
        assert json.loads(shown.stdout)["name"] == "alpha"
    elif str(version) == "4":
        assert "newer than this dadaia" in listed.output
        assert "migrate" not in listed.output.replace(str(ws), "")
        assert migrated.exit_code == 1
        assert path.read_bytes() == before
    if migrated.exit_code == 0:
        assert _runner.invoke(app, ["context", "list"]).exit_code == 0


@pytest.mark.parametrize("version", ["1", "0"])
def test_migrate_rewrites_only_v1_rows(ws: Path, version: str) -> None:
    """sa-registry-schema-version-has-three-grammars#B4: schema "1"/"0" with v3 rows — only
    ativo/inativo rows are rewritten; alive/dead rows are preserved, associated_repos included."""
    path = _registry(ws, version, [_ALIVE, _DEAD, _ATIVO])

    assert _runner.invoke(app, ["migrate", "--yes"]).exit_code == 0
    rows = {r["name"]: r for r in json.loads(path.read_text(encoding="utf-8"))["contexts"]}
    assert (rows["alpha"], rows["gamma"]) == (_ALIVE, _DEAD)
    assert (rows["delta"]["state"], rows["delta"]["alive_since"]) == ("alive", "2026-05-01")


@pytest.mark.skipif(sys.platform == "win32", reason="the dadaia shim is a POSIX sh script")
def test_the_refusal_fix_line_migrates_with_no_tty(tmp_path: Path) -> None:
    """sa-registry-schema-version-has-three-grammars#B5: the refusal carries one fix line,
    `dadaia migrate --yes`, and it works with no TTY (a workspace whose OWN venv runs it)."""
    bin_dir = tmp_path / "ws" / ".dadaia" / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    base = Path(sys.executable).resolve()
    (bin_dir / "python").symlink_to(base)
    (bin_dir.parent / "pyvenv.cfg").write_text(f"home = {base.parent}\n")
    cli = bin_dir / "dadaia"
    cli.write_text(f'#!/bin/sh\nexec "{bin_dir / "python"}" -m dadaia_workspace "$@"\n')
    cli.chmod(0o755)
    (tmp_path / "ws" / ".dadaia" / "states").mkdir()
    _registry(tmp_path / "ws", "1", [_ATIVO])
    path = os.pathsep.join([str(Path(__file__).resolve().parents[3]), *site.getsitepackages()])
    env = {**os.environ, "PYTHONPATH": path}

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(argv, cwd=tmp_path, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=120, check=False)  # fmt: skip

    refused = run([str(cli), "context", "list"])
    fixes = [ln[5:] for ln in refused.stderr.splitlines() if ln.startswith("fix: ")]
    assert (refused.returncode, fixes) == (1, [f"{cli} migrate --yes"])
    assert run(shlex.split(fixes[0])).returncode == 0
    assert run([str(cli), "context", "list"]).returncode == 0


@pytest.mark.parametrize(
    ("version", "rows", "fix_head"),
    [("1", [_ATIVO], None), ("4", [_ALIVE], "Operator action: "),
     ("banana", [_ALIVE], "Operator action: ")],
)  # fmt: skip
def test_doctor_on_a_bad_registry_gives_a_finding_with_a_fix(
    ws: Path, version: str, rows: list[dict[str, object]], fix_head: str | None
) -> None:
    """sa-registry-schema-version-has-three-grammars#B6: on a bad registry, doctor gives a
    finding with a fix and no traceback."""
    _registry(ws, version, rows)

    result = _runner.invoke(app, ["doctor", "--json"])

    assert isinstance(result.exception, SystemExit), result.exception
    sections = json.loads(result.stdout)["sections"].values()
    (fix,) = [f["fix"] for s in sections for f in s["findings"] if f["code"] == "REG-SCHEMA"]
    if fix_head is None:
        assert shlex.split(fix)[1:] == ["migrate", "--yes"]
    else:
        assert fix.startswith(fix_head) and str(ws) in fix
