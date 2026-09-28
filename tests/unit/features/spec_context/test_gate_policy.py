"""Path taxonomy and bind scope of the SDD gate (v0.4.5 A1.2; 0.4.7 FR1, FR3 AC3.1).

Intent: CONTRACT — the class of a path depends only on its context-relative remainder, never on
the slug; LAW is decided by origin (the projected set), never by basename; the bind scope is
the third gate block.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context.gate_policy import (
    Decision,
    PathClass,
    classify_path,
    evaluate,
)

_ROOT = Path("/ws")
A, M, P = PathClass.ADDITIVE, PathClass.MUTATING, PathClass.PROTECTED
_SLUGS = ("dadaia-workspace", "sample-engine")
_CTX_REL = (
    ("specs/bugs/concurrency-warning.md", A),
    ("specs/backlog/epic.md", A),
    ("specs/audits/2026-01-01T000000Z-abc12345/index.md", A),
    ("specs/releases/_archive/releases_histo.jsonl", A),
    ("specs/memory/architecture.md", M),
    ("specs/memory/product/catalog.md", M),
    ("specs/releases/_archive/v0.1.9/SPEC.md", M),
    ("specs/releases/v0.1.10/SPEC.md", M),
    ("specs/constitution.md", M),
    ("specs/some-loose-file.md", M),
    ("dadaia_workspace/features/spec_context/gate_policy.py", M),
    ("src/engine/run.py", M),
    ("pyproject.toml", M),
    ("README.md", M),
    ("Makefile", M),
    ("tests/unit/test_x.py", M),
    # repo-agents-md-law-gate-contradicts-template: a repo's own AGENTS.md is never LAW
    ("AGENTS.md", M),
)


# fmt: off
@pytest.mark.parametrize(("path", "expected"), [
    *[pytest.param(f"repos/{slug}/{rel}", cls, id=f"in-repo-{slug}-{rel}") for rel, cls in _CTX_REL for slug in _SLUGS],
    # sa-gate-allows-root-entries-the-reaper-moves#E5: root specs/ is no entry, so no ADDITIVE verdict applies at the root.
    *[pytest.param(rel, M, id=f"root-{rel}") for rel, _ in _CTX_REL],
    pytest.param("/specs/bugs/x.md", M, id="leading-slash-stripped"),
    pytest.param("/repos/foo/specs/bugs/a.md", A, id="leading-slash-in-repo-additive"),
    pytest.param(".dadaia/mcps/server/s.json", A, id="root-dadaia-mcps"),
    pytest.param(".dadaia/handoff/ctx/h.json", A, id="root-dadaia-handoff"),
    pytest.param(".dadaia/tmp/agent/x.txt", A, id="root-dadaia-tmp"),
    pytest.param(".dadaia/sessions/runtime/ctx.ptr", P, id="root-session-state-protected"),
    pytest.param("some/loose/path.txt", M, id="root-loose"),
    pytest.param("repos/foo", M, id="bare-repo-no-remainder"),
    pytest.param("repos/foo/", M, id="bare-repo-trailing-slash"),
    pytest.param("CLAUDE.md", M, id="AC3.1-root-claude-md-is-not-law"),
    *[pytest.param(p, M, id=f"AC3.1-retired-mirror-{p}") for p in (".codex/AGENTS.md", ".kimi-code/AGENTS.md", ".agents/AGENTS.md", ".claude/rules/AGENTS.md")],
])
# fmt: on
def test_classification_matrix(path: str, expected: PathClass) -> None:
    assert classify_path(path) == expected


_BOUND_A: dict[str, object] = {"bound_context": "ctx-a", "bound_repos": frozenset({"ctx-a", "ctx-a-infra"})}
_B = {**_BOUND_A, "target_slug": "ctx-b", "target_owner": "ctx-b"}
_OWN = {**_BOUND_A, "target_slug": "ctx-a", "target_owner": "ctx-a"}


# fmt: off
@pytest.mark.parametrize(("path", "kwargs", "fix"), [
    pytest.param("specs/audits/_archive/audits_histo.jsonl", {}, None, id="area-histo-append"),
    pytest.param("specs/releases/_archive/releases_histo.jsonl", {}, None, id="releases-histo-append"),
    pytest.param("specs/bugs/20260701T00Z-00.jsonl", {}, None, id="live-bugs-write"),
    pytest.param("repos/existing/AGENTS.md", {}, None, id="A1.2-existing-nonmanifest-repo-agents-md-editable"),
    pytest.param("repos/ctx-b/src/x.py", _B, "fix: /ws/.dadaia/.venv/bin/dadaia context bind ctx-b", id="write-outside-the-bind-scope-names-the-bind"),
    pytest.param("repos/ctx-a-infra/main.tf", {**_BOUND_A, "target_slug": "ctx-a-infra", "target_owner": "ctx-a"}, None, id="associated-repo-in-scope"),
    pytest.param("repos/ctx-b/src/x.py", {"target_slug": "ctx-b", "target_owner": "ctx-b"}, None, id="unbound-session-never-scope-blocked"),
    pytest.param("repos/stranger/src/x.py", {**_BOUND_A, "target_slug": "stranger"}, None, id="unregistered-slug-fails-open"),
    pytest.param("repos/ctx-b/specs/bugs/BUGS.jsonl", _B, None, id="B39-4-foreign-ledger-stays-writable"),
    pytest.param("repos/ctx-b/specs/releases/_archive/releases_histo.jsonl", _B, None, id="B39-4-foreign-histo-stays-writable"),
    pytest.param("specs/memory/ARCHITECTURE.md", _OWN, None, id="memory-write-allowed-every-phase"),
    pytest.param("repos/ctx-a/specs/memory/product/catalog.json", _OWN, None, id="in-repo-memory-write-allowed"),
    pytest.param("AGENTS.md", {"projected": frozenset({"AGENTS.md"})}, "fix: /ws/.dadaia/.venv/bin/dadaia public install", id="S6-projected-law-one-restore-command"),
])
# fmt: on
def test_evaluate_decides_allow_or_block_with_one_fix(path: str, kwargs: dict[str, object], fix: str | None) -> None:
    """sa-gate-path-classes-diverge-from-the-law#B39-4 (any `_archive/*_histo.jsonl` and ledger ALLOW, a
    foreign repo's included); sa-fix-lines-not-built-by-cli-line#S6 (a BLOCK ends in ONE command, no `&&`);
    the MEMORY class is deleted — memory authorship is audited, never gated (0.4.7 FR1)."""
    decision, message = evaluate(path, root=_ROOT, **kwargs)  # type: ignore[arg-type]
    assert decision == (Decision.ALLOW if fix is None else Decision.BLOCK)
    if fix is None:
        assert "[GATE]" not in message
    else:
        assert message.splitlines()[-1] == fix and "&&" not in message
