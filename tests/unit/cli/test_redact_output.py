"""``--redact`` output mode (SPEC v0.9.0 FR8a, T-090-07).

v0.9.0 A8.1, A8.3, A8.4; v0.11.0 A6.4, A6.5;
sa-private-match-rendering-has-three-renderers#B4, #B5, #B6.

Three layers: ``core.redaction`` (the primitive the push gate's render boundary also consumes),
:class:`ContextRedactor` in isolation, and the ``doctor``/``context list``/``context show`` verbs
over a real workspace. ``tests/contract/test_cli_output_stability.py`` pins A8.2 (no flag, no change).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.cli.redact import ContextRedactor
from dadaia_workspace.core.redaction import Redactor, compile_candidates
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.unit

_runner = CliRunner()


# fmt: off
@pytest.mark.parametrize(("candidates", "fmt", "text", "expected"), [
    pytest.param(["foo", "bar"], "[X-{n}]", "bar foo bar", "[X-1] [X-2] [X-1]", id="ordinal-by-first-appearance"),
    pytest.param(["dadaia"], "[X-{n}]", "dadaia-workspace lives at dadaia.", "dadaia-workspace lives at [X-1].", id="word-boundary"),
    pytest.param(["term"], "<<masked-{n}>>", "term appears", "<<masked-1>> appears", id="placeholder-is-the-callers"),
    pytest.param([], "[X-{n}]", "nothing to mask", "nothing to mask", id="inactive-with-no-candidates"),
])
# fmt: on
def test_core_redactor_masks_by_word_with_stable_ordinals(candidates: list[str], fmt: str, text: str, expected: str) -> None:
    """sa-private-match-rendering-has-three-renderers#B6."""
    redactor = Redactor(candidates, placeholder_fmt=fmt)
    assert redactor.mask(text) == expected
    assert redactor.active is bool(candidates)


def test_compile_candidates_orders_longest_first_and_drops_empties() -> None:
    """sa-private-match-rendering-has-three-renderers#B6."""
    assert compile_candidates(["", ""]) is None
    pattern = compile_candidates(["ab", "abcdef", "abc"])
    assert pattern is not None and pattern.match("abcdef").group(0) == "abcdef"  # type: ignore[union-attr]


def test_redactor_ordinal_by_first_appearance_and_caller_exclusion() -> None:
    """sa-private-match-rendering-has-three-renderers#B5: A8.3 first-appearance ordinals; the caller stays visible."""
    redactor = ContextRedactor(["foo-ctx", "bar-ctx", "own-ctx"], exclude=("own-ctx",))
    rendered = redactor.text("own-ctx bar-ctx foo-ctx bar-ctx")
    assert rendered == "own-ctx [REDACTED-CONTEXT-1] [REDACTED-CONTEXT-2] [REDACTED-CONTEXT-1]"


def test_redactor_json_value_preserves_key_set_and_non_string_leaves() -> None:
    """sa-private-match-rendering-has-three-renderers#B4: A8.4 only string leaves change; keys and the rest pass through."""
    redactor = ContextRedactor(["foreign-ctx"])
    payload = {
        "name": "foreign-ctx",
        "state": "alive",
        "count": 3,
        "active": True,
        "parent": None,
        "nested": {"repo_slug": "foreign-ctx", "id": 7},
        "list": ["foreign-ctx", 1, None],
    }
    redacted = redactor.json_value(payload)
    assert set(redacted.keys()) == set(payload.keys())
    assert set(redacted["nested"].keys()) == set(payload["nested"].keys())
    assert redacted["name"] == "[REDACTED-CONTEXT-1]"
    assert redacted["nested"]["repo_slug"] == "[REDACTED-CONTEXT-1]"
    assert redacted["count"] == 3
    assert redacted["active"] is True
    assert redacted["parent"] is None
    assert redacted["list"] == ["[REDACTED-CONTEXT-1]", 1, None]
    assert json.loads(json.dumps(redacted)) == redacted


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, harnesses=("claude",))
    from dadaia_workspace.core.platform import PLATFORM

    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True, exist_ok=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
        "DADAIA_CONTEXT",
    ):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _write_contexts(workspace: Path, contexts: list[dict]) -> None:
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": contexts})
    )


def _ctx_row(
    name: str,
    *,
    repo_slug: str | None = None,
    state: str = "alive",
) -> dict:
    return {
        "name": name,
        "state": state,
        "repo_slug": repo_slug or name,
        "repo_url": f"https://example.com/{repo_slug or name}.git",
        "created_at": "2026-01-01T00:00:00Z",
        "alive_since": "2026-01-01T00:00:00Z" if state == "alive" else None,
        "dead_since": "2026-05-01T00:00:00Z" if state == "dead" else None,
        "current_branch": "main",
    }


# fmt: off
@pytest.mark.parametrize(("args", "hidden", "shown"), [
    pytest.param(["context", "list", "--json"], ["foreign-one", "foreign-two"], ["caller-ctx", "[REDACTED-CONTEXT-"], id="A8.1-list-json"),
    pytest.param(["context", "list"], ["foreign-one", "foreign-two"], ["caller-ctx", "[REDACTED-CONTEXT-"], id="A8.1-list-table"),
    pytest.param(["context", "show", "foreign-one", "--json"], ["foreign-one"], ['"name": "[REDACTED-CONTEXT-1]"', '"main_repo": "[REDACTED-CONTEXT-1]"'], id="A8.1-show-foreign-json"),
    pytest.param(["context", "show", "foreign-one"], ["foreign-one"], ["[REDACTED-CONTEXT-"], id="A8.1-show-foreign-table"),
    pytest.param(["context", "show", "caller-ctx"], ["[REDACTED-CONTEXT-"], ["caller-ctx"], id="show-own-stays-visible"),
])
# fmt: on
def test_context_verbs_redact_every_foreign_name_and_keep_the_callers(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, args: list[str], hidden: list[str], shown: list[str]
) -> None:
    """sa-private-match-rendering-has-three-renderers#B4 #B5: A8.1 a context other than the caller's is masked
    however it is reached; A8.4 `--json` keeps each row's key set and stays valid JSON."""
    _write_contexts(workspace, [_ctx_row("caller-ctx"), _ctx_row("foreign-one"), _ctx_row("foreign-two")])
    monkeypatch.setenv("DADAIA_CONTEXT", "caller-ctx")

    result = _runner.invoke(app, [*args, "--redact"])

    assert result.exit_code == 0, result.output
    assert not [h for h in hidden if h in result.stdout]
    assert all(s in result.stdout for s in shown)
    if "--json" in args:
        plain, masked = json.loads(_runner.invoke(app, args).stdout), json.loads(result.stdout)
        keys = lambda v: [sorted(r) for r in v] if isinstance(v, list) else sorted(v)  # noqa: E731
        assert keys(masked) == keys(plain)


def test_doctor_redact_masks_an_associated_slug_like_context_list(workspace: Path) -> None:
    """sa-private-match-rendering-has-three-renderers#B4: doctor --redact masks an associated slug as context list --redact does."""
    from dadaia_workspace.cli.commands.doctor import _render_for

    row = _ctx_row("zz-foreign") | {"associated_repos": [{"slug": "zz-assoc", "url": "u"}]}
    _write_contexts(workspace, [row])
    listed = _runner.invoke(app, ["context", "list", "--redact", "--json"])
    assert "zz-assoc" not in listed.stdout
    assert _render_for(workspace, redact=True)("in zz-assoc") == "in [REDACTED-CONTEXT-1]"


def test_doctor_redact_json_prints_no_absolute_workspace_path(workspace: Path) -> None:
    """doctor-redact-json-prints-absolute-home-paths: every leaf of `doctor --redact
    --json` (findings' extras and specs_dir included) goes through the one render
    boundary; the workspace root never survives — paths print workspace-relative."""
    _write_contexts(workspace, [_ctx_row("zz-dead", state="dead")])
    (workspace / "repos" / "zz-dead").mkdir(parents=True)

    from dadaia_workspace.core.platform import PLATFORM

    out = _runner.invoke(app, ["doctor", "--redact", "--json"]).stdout

    cli = f".dadaia/.venv/{PLATFORM.venv_scripts_dir}/dadaia{PLATFORM.venv_exe_suffix}"
    assert "INV-5" in out
    assert f'"fix": "{cli} doctor --fix"' in out
    assert str(workspace) not in out and workspace.as_posix() not in out


# fmt: off
@pytest.mark.parametrize(("text", "expected"), [  # composed at runtime: no private literal is tracked
    pytest.param("see /home/" + "alice/.cache/x", "see /…e/.cache/x", id="home-path"),
    pytest.param("see /home/" + "Alice/x", "see /home/" + "Alice/x", id="capitalised-home-not-matched"),
    pytest.param("at " + ".".join(["999", "1", "1", "1"]), "at " + ".".join(["999", "1", "1", "1"]), id="invalid-quad"),
    pytest.param("mail " + "bob" + "@" + "corp.io", "mail b…o", id="email"),
    pytest.param("at {wsb}\\repos\\r", "at repos\\r", id="workspace-relative-windows-separator"),
])
# fmt: on
def test_the_redact_render_masks_exactly_what_the_push_refuses(workspace: Path, text: str, expected: str) -> None:
    """sa-redact-text-keeps-a-second-privacy-grammar: --redact masks what privacy_matches finds, with mask()."""
    from dadaia_workspace.cli.commands.doctor import _render_for

    rendered = text.format(ws=(ws := workspace.as_posix()), wsb=ws.replace("/", "\\"))
    assert _render_for(workspace, redact=True)(rendered) == expected
