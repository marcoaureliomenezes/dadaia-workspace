"""The store, ``migrate`` and the doctor ask ONE grammar (``parse_schema_version``), so a
registry the context verbs read is exactly one ``migrate --yes`` leaves untouched.
Supersedes test_cli_migrate_state.py and the store's legacy-refusal table. An
unreadable registry (truncated, `{}`) is REG-SCHEMA at every reader.

size: MEDIUM (in-process CLI over a tmp workspace; one subprocess runs the fix).
"""

from __future__ import annotations

import json
import os
import site
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core import context_registry
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess, suite_env
from tests.fixtures.stores import fake_venv
from tests.helpers.oslib import command, read_text, run_line, venv_dir, venv_tool, write_text
from tests.helpers.oslib import run as os_run

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
    write_text(path, json.dumps(body))
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
    """int/str 2 and 3 read in
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
    """Schema "1"/"0" with v3 rows — only
    ativo/inativo rows are rewritten; alive/dead rows are preserved, associated_repos included."""
    path = _registry(ws, version, [_ALIVE, _DEAD, _ATIVO])

    assert _runner.invoke(app, ["migrate", "--yes"]).exit_code == 0
    rows = {r["name"]: r for r in json.loads(read_text(path))["contexts"]}
    assert (rows["alpha"], rows["gamma"]) == (_ALIVE, _DEAD)
    assert (rows["delta"]["state"], rows["delta"]["alive_since"]) == ("alive", "2026-05-01")


def test_the_refusal_fix_line_migrates_with_no_tty(tmp_path: Path) -> None:
    """The refusal carries one fix line,
    `dadaia migrate --yes`, and it works with no TTY (a workspace whose OWN venv runs it)."""
    source = "#!python\nimport runpy\nrunpy.run_module('dadaia_workspace', run_name='__main__')\n"
    fake_venv(tmp_path / "ws", cli=source)
    cli = venv_tool(venv_dir(tmp_path / "ws"), "dadaia")
    (tmp_path / "ws" / ".dadaia" / "states").mkdir()
    _registry(tmp_path / "ws", "1", [_ATIVO])
    path = os.pathsep.join([str(Path(__file__).resolve().parents[2]), *site.getsitepackages()])
    env = suite_env(os.environ, Path.home()) | {"PYTHONPATH": path}

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return os_run(argv, cwd=tmp_path, env=env, stdin=subprocess.DEVNULL, timeout=120, check=False)  # fmt: skip

    refused = run([str(cli), "context", "list"])
    fixes = [ln[5:] for ln in refused.stderr.splitlines() if ln.startswith("fix: ")]
    assert (refused.returncode, fixes) == (1, [command(str(cli), "migrate", "--yes")])
    assert run_line(fixes[0], cwd=tmp_path, env=env, timeout=120).returncode == 0
    assert run([str(cli), "context", "list"]).returncode == 0


_TRUNCATED, _SHAPE = '{"contexts": [{"na', '{"contexts": [...]}'
_DEEP = '{"contexts": ' + "[" * 100_000  # past json's recursion limit (CWE-674)


@pytest.mark.parametrize(
    ("body", "fix_head"),
    [(json.dumps({"schema_version": "1", "contexts": [_ATIVO]}), None),
     (json.dumps({"schema_version": "4", "contexts": [_ALIVE]}), "Agent action: "),
     (json.dumps({"schema_version": "banana", "contexts": [_ALIVE]}), "Operator action: "),
     (_TRUNCATED, "Operator action: rewrite "), ("{}", "Operator action: rewrite "),
     (_DEEP, "Operator action: rewrite ")],
    ids=["v1", "newer", "banana", "AC3.9-truncated", "AC3.9-empty-object", "AC3.9-deep-nesting"],
)  # fmt: skip
def test_doctor_on_a_bad_registry_gives_a_finding_with_a_fix(
    ws: Path, body: str, fix_head: str | None
) -> None:
    """On a bad registry —
    truncated and `{}` included — doctor gives one REG-SCHEMA finding with a fix and no
    traceback."""
    write_text(ws / ".dadaia" / "states" / "spec_contexts.json", body)

    result = _runner.invoke(app, ["doctor", "--json"])

    assert isinstance(result.exception, SystemExit), result.exception
    sections = json.loads(result.stdout)["sections"].values()
    (fix,) = [f["fix"] for s in sections for f in s["findings"] if f["code"] == "REG-SCHEMA"]
    if fix_head is None:
        assert fix == fix_line(ws, "migrate", "--yes")
    else:
        assert fix.startswith(fix_head) and str(ws) in fix


@pytest.mark.parametrize(
    "body", [_TRUNCATED, "{}", _DEEP], ids=["truncated", "empty-object", "deep-nesting"]
)
def test_ac3_9_an_unreadable_registry_is_reg_schema_at_every_reader(ws: Path, body: str) -> None:
    """`context
    list|show|create` refuse with the one fix line and no traceback; SessionStart prints
    REG-SCHEMA, never "create a context"; the layout check admits every slug (`*`)."""
    path = ws / ".dadaia" / "states" / "spec_contexts.json"
    write_text(path, body)
    fix = f"fix: Operator action: rewrite {path} as one {_SHAPE} object"

    for argv in (
        ["list"],
        ["show", "alpha"],
        ["create", "--main-repo", "https://example.invalid/alpha.git"],
    ):
        refused = _runner.invoke(app, ["context", *argv])
        fixes = [ln for ln in refused.output.splitlines() if ln.startswith("fix: ")]
        assert (refused.exit_code, fixes) == (1, [fix]), (argv, refused.output)
        assert isinstance(refused.exception, SystemExit), refused.exception

    env = claude_hook_env(ws, session_id="s")
    started = run_hook_subprocess("ctx_inject", {"hook_event_name": "SessionStart"}, env)
    assert "REG-SCHEMA" in started.stdout and "Operator action: rewrite" in started.stdout
    assert "create a context" not in started.stdout.lower(), started.stdout
    assert context_registry.registered_slugs(ws) == (frozenset("*"), frozenset("*"))


def test_ac3_9_doctor_fix_acts_on_nothing_over_an_unreadable_registry(ws: Path) -> None:
    """An unreadable registry makes every `doctor --fix` lane act on nothing — a root
    slop file stays where it is."""
    write_text(ws / ".dadaia" / "states" / "spec_contexts.json", _TRUNCATED)
    write_text(ws / "junk.txt", "slop")

    _runner.invoke(app, ["doctor", "--fix"])

    assert read_text(ws / "junk.txt") == "slop"


def test_a_registry_row_missing_a_key_is_reg_schema(ws: Path) -> None:
    """A row without ``created_at`` is unreadable, never a ``KeyError``:
    `context list` exits 1 with one ``Operator action:`` fix line, and doctor gives one
    REG-SCHEMA finding carrying it."""
    _registry(ws, "2", [{k: v for k, v in _ALIVE.items() if k != "created_at"}])

    refused = _runner.invoke(app, ["context", "list"])
    doctor = _runner.invoke(app, ["doctor", "--json"])

    assert isinstance(refused.exception, SystemExit), refused.exception
    fixes = [ln for ln in refused.output.splitlines() if ln.startswith("fix: ")]
    assert refused.exit_code == 1 and len(fixes) == 1, refused.output
    assert fixes[0].startswith("fix: Operator action: ")
    sections = json.loads(doctor.stdout)["sections"].values()
    (fix,) = [f["fix"] for s in sections for f in s["findings"] if f["code"] == "REG-SCHEMA"]
    assert fix.startswith("Operator action: ")


def _ctx(name: str) -> SpecContextProject:
    return SpecContextProject(
        name=name, state=ContextState.DEAD, repo_slug=name, repo_url="u", created_at="t"
    )


def test_every_write_stamps_the_one_schema_version_and_restore_puts_back_the_bytes(
    tmp_path: Path,
) -> None:
    """``replace_raw``, ``save`` and ``update`` write ``"3"`` over any older stamp; an empty
    registry spells it the same; ``restore`` returns a snapshot byte for byte."""
    store = JsonContextStore(tmp_path)
    store.seed_if_absent()
    assert store.read_raw() == {"schema_version": "3", "contexts": []}

    path = tmp_path / "spec_contexts.json"
    stale = json.dumps({"schema_version": "2", "contexts": []})
    write_text(path, stale)
    snapshot = store.snapshot()

    store.save(_ctx("a"))
    assert store.read_raw()["schema_version"] == "3"
    row = {"name": "a", "state": "dead", "repo_slug": "a", "repo_url": "u", "created_at": "t"}
    write_text(path, json.dumps({"schema_version": "2", "contexts": [row]}))
    store.update(_ctx("a"))
    assert store.read_raw()["schema_version"] == "3"
    store.replace_raw({"contexts": []})
    assert store.read_raw() == {"schema_version": "3", "contexts": []}

    store.restore(snapshot)
    assert path.read_text() == stale
