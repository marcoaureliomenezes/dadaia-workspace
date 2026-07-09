"""Code-review remediation (v0.1.69 FR2.2, HIGH): ``specs doctor --context`` must reuse
the SAME context->specs resolver the FR3 preflight-input probe already uses
(``container._context_specs_dir`` / its public seam ``resolve_context_specs_dir``),
not a hand-rolled ``repos/<context>/specs`` path.

On current code, ``dadaia_workspace/cli/commands/specs.py``'s ``doctor --context``
resolves unconditionally to ``<workspace_root>/repos/<context>/specs`` — which does not
exist for a *self-hosting* workspace (one whose active context's specs live at the
workspace-root ``specs/`` tree, exactly like this very repo). That nonexistent path
still "resolves" (``Path.resolve()`` never raises for a missing path) and the doctor
then reports a FABRICATED ``SPEC-DOC-001: specs/constitution.md is missing`` — not
because the context's specs are actually broken, but because the CLI looked in the
wrong place entirely.

The fix reuses ``container.resolve_context_specs_dir`` (the v0.1.68 public seam over
``_context_specs_dir``), which falls back to the workspace-root ``specs/`` tree when
``repos/<ctx>/specs`` is absent — the exact resolution ``lifecycle pipeline`` already
relies on for the implement step's write-scope derivation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.scaffolder import scaffold

_runner = CliRunner()

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


def _make_self_hosting_workspace(root: Path) -> Path:
    """A tmp workspace root whose specs live at workspace-root ``specs/`` (self-hosting
    shape) — mirrors this very repo's layout. Deliberately has NO ``repos/<ctx>/specs``.
    """
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"contexts": []}', encoding="utf-8")
    specs = root / "specs"
    result = scaffold(
        specs_dir=specs,
        project_name="self-hosting-ctx",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], result.errors
    return specs


def test_doctor_context_resolves_workspace_root_specs_for_self_hosting_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``specs doctor --context <ctx>`` for a self-hosting-style tmp workspace (no
    ``repos/<ctx>/specs`` on disk) must resolve to the REAL workspace-root ``specs/``
    tree — never fabricate ``SPEC-DOC-001`` because it looked at a nonexistent
    ``repos/<ctx>/specs`` path.

    FAILS on current code: the hand-rolled resolver in ``specs.py`` always targets
    ``repos/<ctx>/specs`` regardless of whether it exists, so the doctor reports the
    fabricated missing-constitution error even though the context's real specs tree
    (at workspace-root) is a fully valid scaffold.
    """
    _make_self_hosting_workspace(tmp_path)
    ctx = "self-hosting-ctx"

    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["specs", "doctor", "--context", ctx])

    assert "SPEC-DOC-001" not in result.output, result.output
    assert "constitution.md is missing" not in result.output, result.output
    assert str(tmp_path / "specs") in result.output, result.output
    assert result.exit_code == 0, result.output
