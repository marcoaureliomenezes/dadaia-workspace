"""Intent: CONTRACT — 0.4.6 AC11 (the bootstrap prefix carries the two memory law blocks).

Size: SMALL. The hook runs as a real subprocess for the bound-session path; the
no-block case drives ``_build_memory`` directly (a pure function of the specs dir).
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.hooks import ctx_inject
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

_ARCHITECTURE = (
    "# Architecture\n"
    "SENTINEL_ARCHITECTURE_BODY\n"
    "\n"
    "<!-- dadaia:fixed slop-code -->\n"
    "### Slop — code (fixed)\n"
    "- LAW_CODE_BULLET\n"
    "<!-- /dadaia:fixed slop-code -->\n"
)
_QUALITY = (
    "# Quality\n"
    "SENTINEL_QA_BODY\n"
    "\n"
    "<!-- dadaia:fixed slop-tests -->\n"
    "### Slop — tests (fixed)\n"
    "- LAW_TESTS_BULLET\n"
    "<!-- /dadaia:fixed slop-tests -->\n"
)
_TECH = "# tech\nPython 3.12\n"
_CATALOG = {
    "features": [{"slug": "a", "title": "A", "tldr": "t", "path": "specs/memory/product/a.md"}]
}


def _workspace(tmp_path: Path, *, with_law: bool) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": "ctx", "state": "alive"}]}), encoding="utf-8"
    )
    mem = tmp_path / "repos" / "ctx" / "specs" / "memory"
    (mem / "product").mkdir(parents=True)
    (mem / "TECHSTACK.md").write_text(_TECH, encoding="utf-8")
    (mem / "product" / "catalog.json").write_text(json.dumps(_CATALOG), encoding="utf-8")
    if with_law:
        (mem / "ARCHITECTURE.md").write_text(_ARCHITECTURE, encoding="utf-8")
        (mem / "QUALITY.md").write_text(_QUALITY, encoding="utf-8")
    return mem.parent


def test_bound_session_bootstrap_carries_the_law_blocks_between_tech_and_catalog(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path, with_law=True)
    env = claude_hook_env(tmp_path, extra={"DADAIA_CONTEXT": "ctx"})
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": "law1"}, env)
    assert result.returncode == 0, result.stderr
    out = result.stdout

    expected = (
        "Python 3.12\n"
        "=== workspace law (fixed) ===\n"
        "### Slop — code (fixed)\n"
        "- LAW_CODE_BULLET\n"
        "### Slop — tests (fixed)\n"
        "- LAW_TESTS_BULLET\n"
        "{"
    )
    assert expected in out
    assert "SENTINEL_ARCHITECTURE_BODY" not in out
    assert "SENTINEL_QA_BODY" not in out


def test_build_memory_emits_no_law_header_when_no_memory_file_carries_a_block(
    tmp_path: Path,
) -> None:
    specs = _workspace(tmp_path, with_law=False)
    built = ctx_inject._build_memory(specs)
    assert "=== workspace law (fixed) ===" not in built
    assert built == (
        "\n=== workspace memory (tech + catalog) ===\n"
        "# tech\nPython 3.12\n"
        '{\n  "features": [\n    {\n      "slug": "a",\n      "title": "A",\n'
        '      "tldr": "t",\n      "path": "specs/memory/product/a.md"\n    }\n  ]\n}\n'
        "=== end memory bootstrap ==="
    )


def test_build_memory_emits_only_the_blocks_present(tmp_path: Path) -> None:
    specs = _workspace(tmp_path, with_law=False)
    (specs / "memory" / "QUALITY.md").write_text(_QUALITY, encoding="utf-8")
    built = ctx_inject._build_memory(specs)
    assert (
        "Python 3.12\n=== workspace law (fixed) ===\n### Slop — tests (fixed)\n- LAW_TESTS_BULLET\n{"
        in built
    )
    assert "slop-code" not in built
