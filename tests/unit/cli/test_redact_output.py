"""``--redact`` output mode (SPEC v0.9.0 FR8a, T-090-07).

Intent: CONTRACT — v0.9.0 A8.1, A8.3, A8.4; v0.11.0 A6.4, A6.5.

Three layers are pinned here:

0. ``dadaia_workspace.core.redaction`` — the stdlib-pure masking primitive extracted
   from :class:`ContextRedactor` at v0.11.0 (FR6/ADR D1-a): word-boundary alternation,
   longest-first ordering, stable first-appearance ordinal placeholders. Pinned
   directly (not only through the CLI wrapper) since this is now the SAME primitive the
   push-range denylist gate's own render boundary consumes.
1. :class:`dadaia_workspace.cli.redact.ContextRedactor` in pure isolation (ordinal
   assignment by first appearance, exclusion of the caller's own context, word-boundary
   matching, JSON key-set preservation). Its assertions are UNCHANGED by the v0.11.0
   extraction (A6.4) — the regression proof that the extraction was mechanical.
2. The three operator-facing verbs (``dadaia doctor``, ``dadaia context list``,
   ``dadaia context show``) wired to it, over a real ``CliRunner`` workspace: no foreign
   Spec Context name or repo slug survives ``--redact`` in either table or ``--json``
   rendering, including the doctor lines the SPEC calls out by name
   (``PRESENCE-GC``/``[stale-presence]``, ``INV-4``, ``INV-5``).

``tests/contract/test_cli_output_stability.py`` pins the companion property (A8.2):
default output — no ``--redact`` flag — is unchanged.
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


# ---------------------------------------------------------------------------
# Layer 0 — core/redaction.py, the extracted primitive (v0.11.0 A6.4/A6.5), in pure
# isolation: no CLI, no filesystem, no I/O of any kind.
# ---------------------------------------------------------------------------


def test_compile_candidates_returns_none_for_no_candidates() -> None:
    assert compile_candidates([]) is None
    assert compile_candidates(["", ""]) is None


def test_compile_candidates_orders_longest_first() -> None:
    pattern = compile_candidates(["ab", "abcdef", "abc"])
    assert pattern is not None
    match = pattern.match("abcdef")
    assert match is not None
    assert match.group(0) == "abcdef"


def test_redactor_ordinal_by_first_appearance() -> None:
    """The same property A8.3 pins through :class:`ContextRedactor`, asserted directly
    against the extracted primitive."""
    redactor = Redactor(["foo", "bar"], placeholder_fmt="[X-{n}]")
    assert redactor.mask("bar foo bar") == "[X-1] [X-2] [X-1]"


def test_redactor_inactive_with_no_candidates_returns_value_unchanged() -> None:
    redactor = Redactor([], placeholder_fmt="[X-{n}]")
    assert redactor.active is False
    assert redactor.mask("nothing to mask here") == "nothing to mask here"


def test_core_redactor_word_boundary_does_not_partially_match_longer_string() -> None:
    redactor = Redactor(["dadaia"], placeholder_fmt="[X-{n}]")
    assert redactor.mask("dadaia-workspace lives at dadaia.") == (
        "dadaia-workspace lives at [X-1]."
    )


def test_redactor_placeholder_format_is_caller_controlled() -> None:
    """Two independent :class:`Redactor` instances with different placeholder formats
    (e.g. the CLI's ``[REDACTED-CONTEXT-n]`` vs a future gate-renderer format) never
    collide — the format string is entirely the caller's own."""
    redactor = Redactor(["term"], placeholder_fmt="<<masked-{n}>>")
    assert redactor.mask("term appears") == "<<masked-1>> appears"


# ---------------------------------------------------------------------------
# Layer 1 — ContextRedactor, pure unit tests (no CLI, no filesystem).
# ---------------------------------------------------------------------------


def test_redactor_ordinal_by_first_appearance_and_caller_exclusion() -> None:
    """A8.3: ordinal is assigned by first appearance in the text actually scanned, is
    stable for repeat occurrences, and never touches the excluded caller context."""
    redactor = ContextRedactor(["foo-ctx", "bar-ctx", "own-ctx"], exclude=("own-ctx",))
    rendered = redactor.text("own-ctx bar-ctx foo-ctx bar-ctx")
    assert rendered == "own-ctx [REDACTED-CONTEXT-1] [REDACTED-CONTEXT-2] [REDACTED-CONTEXT-1]"


def test_redactor_word_boundary_does_not_partially_match_longer_string() -> None:
    """A short candidate that is a mere prefix of a longer, unrelated hyphenated
    string is never partially redacted (hyphens count as word characters here)."""
    redactor = ContextRedactor(["dadaia"])
    rendered = redactor.text("dadaia-workspace lives at dadaia.")
    assert rendered == "dadaia-workspace lives at [REDACTED-CONTEXT-1]."


def test_redactor_no_candidates_is_inactive_and_returns_text_unchanged() -> None:
    redactor = ContextRedactor([])
    assert redactor.active is False
    assert redactor.text("nothing to redact here") == "nothing to redact here"


def test_redactor_json_value_preserves_key_set_and_non_string_leaves() -> None:
    """A8.4: recursive redaction touches only string leaves; keys and every
    non-string value pass through unchanged."""
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
    # Round-trips through json.dumps/json.loads without error (still valid JSON).
    assert json.loads(json.dumps(redacted)) == redacted


# ---------------------------------------------------------------------------
# Layer 2 — CLI wiring, real workspace via CliRunner.
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
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


def _write_corrupt_presence(workspace: Path, ctx: str, sid: str) -> None:
    path = workspace / ".dadaia" / "states" / "presence" / ctx / f"{sid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")


def test_doctor_redact_masks_presence_and_repo_coherence_lines(
    workspace: Path, monkeypatch
) -> None:
    """A8.1: `dadaia doctor --redact` names no foreign context/slug in the
    PRESENCE-GC ([stale-presence]), INV-4 and INV-5 lines; the caller's own context
    stays visible."""
    caller_repo = workspace / "repos" / "caller-ctx"
    caller_repo.mkdir(parents=True)
    alpha_repo_absent_slug = "alpha-repo"  # INV-4: ALIVE, repo missing on disk
    bravo_repo_present_slug = "bravo-repo"  # INV-5: DEAD, repo present on disk
    (workspace / "repos" / bravo_repo_present_slug).mkdir(parents=True)

    _write_contexts(
        workspace,
        [
            _ctx_row("caller-ctx", repo_slug="caller-ctx", state="alive"),
            _ctx_row("alpha-secret", repo_slug=alpha_repo_absent_slug, state="alive"),
            _ctx_row("bravo-secret", repo_slug=bravo_repo_present_slug, state="dead"),
        ],
    )
    _write_corrupt_presence(workspace, "charlie-secret", "sess-corrupt")
    # A stale presence record for the CALLER's own context too, so the PRESENCE-GC line
    # gives us a positive control: it must stay visible, unlike the foreign ones.
    _write_corrupt_presence(workspace, "caller-ctx", "sess-own-corrupt")
    monkeypatch.setenv("DADAIA_CONTEXT", "caller-ctx")

    # Sanity control: without --redact the foreign names are actually present (proves
    # the fixture triggers the issue codes under test).
    plain = _runner.invoke(app, ["doctor"])
    assert plain.exit_code == 1, plain.output
    assert "alpha-secret" in plain.output
    assert "bravo-secret" in plain.output
    assert "charlie-secret" in plain.output

    result = _runner.invoke(app, ["doctor", "--redact"])
    assert result.exit_code == 1, result.output
    for foreign in (
        "alpha-secret",
        alpha_repo_absent_slug,
        "bravo-secret",
        bravo_repo_present_slug,
        "charlie-secret",
    ):
        assert foreign not in result.output, result.output
    assert "[REDACTED-CONTEXT-" in result.output
    assert "caller-ctx" in result.output


def test_context_list_redact_json_same_key_set_and_masks_foreign(
    workspace: Path, monkeypatch
) -> None:
    """A8.1/A8.4: `context list --redact --json` stays valid JSON with the same key
    set per row; only foreign name/repo_slug values are masked."""
    _write_contexts(
        workspace,
        [
            _ctx_row("caller-ctx"),
            _ctx_row("foreign-one"),
            _ctx_row("foreign-two"),
        ],
    )
    monkeypatch.setenv("DADAIA_CONTEXT", "caller-ctx")

    plain = _runner.invoke(app, ["context", "list", "--json"])
    assert plain.exit_code == 0, plain.output
    plain_rows = json.loads(plain.stdout)

    result = _runner.invoke(app, ["context", "list", "--redact", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)

    assert len(rows) == len(plain_rows) == 3
    for row in rows:
        assert set(row.keys()) == set(plain_rows[0].keys())
    names = {row["name"] for row in rows}
    assert "caller-ctx" in names
    assert "foreign-one" not in names
    assert "foreign-two" not in names
    assert any(n.startswith("[REDACTED-CONTEXT-") for n in names)


def test_context_list_redact_table_masks_foreign_names(workspace: Path, monkeypatch) -> None:
    _write_contexts(
        workspace,
        [
            _ctx_row("caller-ctx"),
            _ctx_row("foreign-one"),
        ],
    )
    monkeypatch.setenv("DADAIA_CONTEXT", "caller-ctx")

    result = _runner.invoke(app, ["context", "list", "--redact"])
    assert result.exit_code == 0, result.output
    assert "foreign-one" not in result.output
    assert "caller-ctx" in result.output
    assert "[REDACTED-CONTEXT-" in result.output


def test_context_show_redact_masks_explicit_foreign_context(workspace: Path, monkeypatch) -> None:
    """A8.1: showing a context OTHER than the caller's own, with --redact, masks
    that context's own name/slug too (it is "other than the caller's resolved
    context" regardless of how it was reached)."""
    _write_contexts(
        workspace,
        [
            _ctx_row("caller-ctx"),
            _ctx_row("foreign-target"),
        ],
    )
    monkeypatch.setenv("DADAIA_CONTEXT", "caller-ctx")

    result = _runner.invoke(app, ["context", "show", "foreign-target", "--redact"])
    assert result.exit_code == 0, result.output
    assert "foreign-target" not in result.output
    assert "[REDACTED-CONTEXT-" in result.output

    json_result = _runner.invoke(app, ["context", "show", "foreign-target", "--redact", "--json"])
    assert json_result.exit_code == 0, json_result.output
    data = json.loads(json_result.stdout)
    plain_json = json.loads(
        _runner.invoke(app, ["context", "show", "foreign-target", "--json"]).stdout
    )
    assert set(data.keys()) == set(plain_json.keys())
    assert data["name"] == "[REDACTED-CONTEXT-1]"
    assert data["repo_slug"] == "[REDACTED-CONTEXT-1]"


def test_context_show_redact_keeps_callers_own_context_visible(
    workspace: Path, monkeypatch
) -> None:
    _write_contexts(
        workspace,
        [
            _ctx_row("caller-ctx"),
            _ctx_row("foreign-other"),
        ],
    )
    monkeypatch.setenv("DADAIA_CONTEXT", "caller-ctx")

    result = _runner.invoke(app, ["context", "show", "caller-ctx", "--redact"])
    assert result.exit_code == 0, result.output
    assert "caller-ctx" in result.output
    assert "[REDACTED-CONTEXT-" not in result.output
