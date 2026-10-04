"""Path taxonomy and bind scope of the SDD gate (v0.4.5 A1.2; 0.4.7 FR1, FR3 AC3.1).

T-050-97 (AC1.1): no repos/ path is ADDITIVE; LAW is decided by origin (the
projected set), never by basename; a write out of the bind's scope names `context bind`, and
every write under repos/<r>/ outside specs/audits/ names the worktree of the right kind.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import mkdir_line, script_line
from dadaia_workspace.features.spec_context.gate_policy import (
    Decision,
    PathClass,
    classify_path,
    evaluate,
)

_ROOT = Path("/ws")
A, M, P = PathClass.ADDITIVE, PathClass.MUTATING, PathClass.PROTECTED
_IN_REPO = (
    "specs/bugs/BUGS.jsonl",
    "specs/audits/20260101-x/index.md",
    "src/engine/run.py",
    "README.md",
)


# fmt: off
@pytest.mark.parametrize(("path", "expected"), [
    # additive-globs-hand-kept-beside-the-canon: no specs path is always writable (ADR 0124)
    *[pytest.param(f"repos/sample-engine/{rel}", M, id=f"in-repo-{rel}") for rel in _IN_REPO],
    *[pytest.param(rel, M, id=f"root-{rel}") for rel in _IN_REPO],
    pytest.param("/repos/foo/specs/bugs/a.md", M, id="leading-slash-stripped"),
    pytest.param(".dadaia/reports/ctx/r.html", A, id="root-dadaia-reports"),
    pytest.param(".dadaia/handoff/ctx/h.json", A, id="root-dadaia-handoff"),
    pytest.param(".dadaia/tmp/agent/x.txt", A, id="root-dadaia-tmp"),
    # gate-protects-nothing-without-install-ledger: the code floor needs no ledger (ADR 0133)
    *[pytest.param(p, P, id=f"floor-{p}") for p in ("AGENTS.md", ".dadaiaignore", ".dadaia/sessions/runtime/ctx.ptr", ".dadaia/states/spec_contexts.json", ".dadaia/hooks/x.sh")],
    pytest.param("repos/sample-engine/AGENTS.md", M, id="repo-agents-md-is-not-the-floor"),
    pytest.param("CLAUDE.md", M, id="AC3.1-root-claude-md-is-not-law"),
    *[pytest.param(p, M, id=f"AC3.1-retired-mirror-{p}") for p in (".codex/AGENTS.md", ".kimi-code/AGENTS.md", ".agents/AGENTS.md", ".claude/rules/AGENTS.md")],
])
# fmt: on
def test_classification_matrix(path: str, expected: PathClass) -> None:
    assert classify_path(path)[0] == expected


_A: dict[str, object] = {"context": "ctx-a", "repos": frozenset({"ctx-a", "ctx-a-infra"})}
_DADAIA = "/ws/.dadaia/.venv/Scripts/dadaia.exe" if sys.platform == "win32" else "/ws/.dadaia/.venv/bin/dadaia"


def _wt(repo: str, kind: str) -> str:
    return "fix: " + script_line(".agents/skills/dd-gitflow-default/scripts/worktree.py", "new", repo, "--kind", kind)


def _at(zone: str, repo: str, owner: str | None = None, **session: object) -> dict[str, object]:
    return {"zone": zone, "repo": repo, "owner": owner or repo, **session}


# fmt: off
@pytest.mark.parametrize(("path", "kwargs", "fix"), [
    pytest.param("specs/releases/_archive/releases_histo.jsonl", {}, None, id="root-path-in-scope-under-any-bind"),
    pytest.param("worktrees/ctx-a/0.5.0a-impl/src/x.py", _at("worktree", "ctx-a", **_A), None, id="AC1.1-own-worktree-allowed"),
    pytest.param("worktrees/ctx-a-infra/0.5.0a-impl/main.tf", _at("worktree", "ctx-a-infra", "ctx-a", **_A), None, id="associated-repo-worktree-in-scope"),
    pytest.param("repos/ctx-a/specs/audits/20260101-x/index.md", _at("audit", "ctx-a", **_A), None, id="AC1.1-own-audit-allowed"),
    pytest.param("repos/ctx-a/src/x.py", _at("repo", "ctx-a", **_A), _wt("ctx-a", "impl"), id="AC1.1-own-repo-code-is-merge-only"),
    pytest.param("repos/ctx-a/specs/bugs/BUGS.jsonl", _at("repo", "ctx-a", **_A), _wt("ctx-a", "bug"), id="ADR0124-ledger-no-longer-always-writable"),
    pytest.param("repos/ctx-a/specs/bugs/notes.md", _at("repo", "ctx-a", **_A), "fix: Operator action: edit repos/ctx-a/specs/bugs/notes.md by hand; no worktree kind merges it", id="F5-no-kind-merges-it-names-the-operator"),
    pytest.param("repos/ctx-b/src/x.py", _at("repo", "ctx-b", **_A), f"fix: {_DADAIA} context bind ctx-b", id="write-outside-the-bind-scope-names-the-bind"),
    pytest.param("worktrees/ctx-b/0.5.0a-impl/src/x.py", _at("worktree", "ctx-b"), f"fix: {_DADAIA} context bind ctx-b", id="unbound-native-session-refused-names-the-bind"),
    pytest.param("worktrees/ctx-b/0.5.0a-impl/src/x.py", _at("worktree", "ctx-b", has_id=False), None, id="ADR0116-id-less-unbound-worktree-is-the-declared-gap"),
    pytest.param("repos/ctx-b/src/x.py", _at("repo", "ctx-b", has_id=False), _wt("ctx-b", "impl"), id="ADR0105-repos-refused-for-every-session"),
    pytest.param("repos/stranger/src/x.py", {**_at("repo", "stranger", **_A), "owner": None}, _wt("stranger", "impl"), id="unregistered-slug-still-merge-only"),
    pytest.param("repos/beta/x.py", _at("repo", "beta", context="alpha", repos=frozenset({"alpha"}), has_id=False), "fix: Operator action: relaunch this session with DADAIA_CONTEXT=beta", id="sa-bind-has-two-stores#S5-env-bound-is-told-an-operator-step"),
    pytest.param("AGENTS.md", {}, f"fix: {_DADAIA} public install", id="S6-floor-law-one-restore-command"),
    pytest.param(".dadaia/sessions/x.json", _A, f"fix: {_DADAIA} context bind ctx-a", id="AC4.4-session-floor-names-the-bound-context"),
    pytest.param(".dadaia/sessions/x.json", {}, f"fix: {_DADAIA} context list", id="AC4.4-session-floor-unbound-lists-contexts"),
    pytest.param(".dadaia/states/install_ledger.json", {"projected": frozenset({".dadaia/states/install_ledger.json"})}, f"fix: {_DADAIA} public install", id="H1-ledgered-floor-path-is-projected-law-first"),
    pytest.param("repos/x/secrets/k", {"protected": ("secrets",)}, f"fix: {mkdir_line(_ROOT / '.dadaia' / 'tmp')}", id="AC2.5-protected-glob-operator-drafts-in-tmp"),
])
# fmt: on
def test_evaluate_decides_allow_or_block_with_one_fix(path: str, kwargs: dict[str, object], fix: str | None) -> None:
    """unbound-native-session-writes-freely-into-repos and additive-globs-hand-kept-beside-the-canon
    (restoring either ALLOW turns its row red); sa-fix-lines-not-built-by-cli-line#S6 (a BLOCK ends
    in ONE command, no `&&`); memory authorship is audited, never gated (0.4.7 FR1)."""
    decision, message = evaluate(path, root=_ROOT, **kwargs)  # type: ignore[arg-type]
    assert decision == (Decision.ALLOW if fix is None else Decision.BLOCK)
    if fix is None:
        assert "[GATE]" not in message
    else:
        assert message.splitlines()[-1] == fix and "&&" not in message
        assert "protected" not in kwargs or "'secrets'" in message and "<agent>/<YYYYMMDD>/" in message
