"""FR19 (v0.4.4, T-044-30) A19.1 — one place of control: bind-driven injection never
leaks an associated repo's own memory.

Intent: CONTRACT — A19.1

G13 (v0.4.4 grill ADR, ratified): a Spec Context's associated repos are cloned clean and
their OWN ``specs/`` (if any) are **ignored** by the spec context — specs, bind and
memory resolve ONLY from the MAIN repo. This suite proves that invariant at the
``ctx_inject`` injection seam, the same seam ``tests/unit/hooks/test_ctx_inject.py``
already exercises (bind-driven injection, real subprocess, ``run_hook_subprocess`` — see
that file's module docstring for the harness-real rationale): a bind to a context with an
associated repo injects the MAIN repo's memory only, whether the trigger is a real bind
(self-keyed session record) or the cwd-based resolution walk (rung 3, T-044-27/A16.4)
from inside the associated repo's own directory.

The associated repo carries its OWN, COMMITTED ``specs/memory/`` tree — deliberately: a
real associated repo IS a repo with its own git history, and A16.3
(``tests/integration/test_associated_repos_alive_dead.py``) already proves ``alive()``
clones it clean and leaves that tree untouched. Its tech-stack digest carries a marker
that must NEVER reach the injected bootstrap — that marker leaking into the output IS
the failure this suite pins.

Extends T-044-27's A16.4 resolution-walk coverage
(``tests/unit/core/test_specs_resolver_associated_repo_walk.py``) up to the injection
hook itself. Fixture SHAPE is reused, not shared: that suite's own docstring establishes
the "reuse the same fixture conventions locally" pattern for this feature, and
``test_ctx_inject.py`` already establishes the same convention for hook fixtures.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

#: The context's main repo slug AND registered name (kept equal, deliberately — a
#: divergent name/slug pair is an orthogonal, pre-existing concern this task does not
#: touch; see ``core.specs_resolver.repo_slug_for_context``).
_MAIN_SLUG = "ctx"
_ASSOC_SLUG = "assoc-repo"
_ASSOC_MARKER = "ASSOC-ONLY-MARKER"


def _git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-c", "user.email=t@test", "-c", "user.name=t", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30.0,
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr or proc.stdout}"


def _mk_workspace_with_associated_repo(tmp_path: Path) -> Path:
    """One ALIVE context (name == main repo slug ``ctx``) with ONE associated repo
    (``assoc-repo``) that carries its OWN, git-committed ``specs/memory`` tree."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "contexts": [
                    {
                        "name": _MAIN_SLUG,
                        "repo_slug": _MAIN_SLUG,
                        "state": "alive",
                        "associated_repos": [
                            {"slug": _ASSOC_SLUG, "url": "https://example.invalid/assoc.git"}
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    main_mem = tmp_path / "repos" / _MAIN_SLUG / "specs" / "memory"
    main_mem.mkdir(parents=True)
    (main_mem / "tech-stack.md").write_text("# tech\nPython 3.12\n", encoding="utf-8")
    (main_mem / "product").mkdir()
    (main_mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")

    assoc_repo = tmp_path / "repos" / _ASSOC_SLUG
    assoc_mem = assoc_repo / "specs" / "memory"
    assoc_mem.mkdir(parents=True)
    (assoc_mem / "tech-stack.md").write_text(
        f"# the associated repo's OWN tech stack\n{_ASSOC_MARKER}\n", encoding="utf-8"
    )
    (assoc_mem / "product").mkdir()
    (assoc_mem / "product" / "catalog.json").write_text(
        '{"features": [{"slug": "assoc-only-feature"}]}', encoding="utf-8"
    )
    _git(assoc_repo, "-c", "init.defaultBranch=main", "init")
    _git(assoc_repo, "add", "-A")
    _git(assoc_repo, "commit", "-m", "seed: the associated repo's own specs tree")

    return tmp_path


def _bind_session(tmp_path: Path, session_id: str, context: str) -> None:
    """Mirrors ``dadaia context bind`` — the same helper shape as ``test_ctx_inject.py``."""
    session_identity.write_session(
        tmp_path,
        session_id,
        {
            "session_id": session_id,
            "context": context,
            "mode": "read",
            "bound_at": datetime.now(tz=UTC).isoformat(),
        },
    )


def _inject(tmp_path: Path, session_id: str, *, cwd: Path | None = None) -> str:
    env = claude_hook_env(tmp_path)
    env.pop("CLAUDE_CODE_SESSION_ID", None)  # force resolution off the stdin field / cwd walk
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env, cwd=cwd)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_bind_to_context_with_associated_repo_injects_main_memory_only(tmp_path: Path) -> None:
    ws = _mk_workspace_with_associated_repo(tmp_path)
    sid = "a19-1-bind"
    _bind_session(ws, sid, _MAIN_SLUG)

    out = _inject(ws, sid)

    assert f"[{_MAIN_SLUG}]" in out
    assert "end memory bootstrap" in out
    assert "Python 3.12" in out
    assert _ASSOC_MARKER not in out
    assert "assoc-only-feature" not in out


def test_cwd_inside_associated_repo_resolves_owning_context_injects_main_memory_only(
    tmp_path: Path,
) -> None:
    """A16.4's rung-3 walk, proven at the injection seam: cwd inside
    ``repos/assoc-repo/`` with NO bind and NO ``DADAIA_CONTEXT`` still resolves the
    OWNING context (never a second context named after the associated repo, per
    ``core.specs_resolver.context_name_for_repo_slug``) and injects ONLY the main
    repo's memory."""
    ws = _mk_workspace_with_associated_repo(tmp_path)
    sid = "a19-1-cwd"

    out = _inject(ws, sid, cwd=ws / "repos" / _ASSOC_SLUG)

    assert f"[{_MAIN_SLUG}]" in out
    assert "end memory bootstrap" in out
    assert "Python 3.12" in out
    assert _ASSOC_MARKER not in out
    assert "assoc-only-feature" not in out
