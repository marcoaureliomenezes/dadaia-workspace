"""Intent: CONTRACT — 0.4.6 AC11 (Layer-1 bootstrap byte-identical lock).

Size: SMALL. ``_build_memory`` emits exactly: the tech-stack digest, the fixed law
blocks of ``memory/ARCHITECTURE.md`` and ``memory/QUALITY.md`` (the marked body only,
never the rest of the atom), and the lean catalog digest. The constitution and every
unmarked memory body stay self-pull. The golden is the mutation check: any growth, a
header change or a join change fails the byte equality. The output carries no host
path, so the golden is identical on every platform.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.hooks import ctx_inject

# A heavy ``summary`` body: the catalog digest MUST drop it (kept only on disk for
# self-pull depth). Its absence from the golden is part of the lock.
_HEAVY_SUMMARY = (
    "handoff-v1.1 separates human evidence (HTML reports under "
    ".dadaia/reports/<context>/<agent>/) from agent coordination (JSON handoffs "
    "under .dadaia/handoff/<context>/). The CLI validates the schema and the "
    "content hash of artifact.path within the workspace root. " * 3
)

# The fixture catalog carries the full field set (rank / summary / tags / token_estimate
# / agent_tier / depends_on) precisely so the golden proves the digest strips everything
# except slug / title / tldr / path (``_DIGEST_FIELDS``), and drops ``rank`` (F-77).
_CATALOG: dict[str, object] = {
    "generated_at": "2026-07-04T00:00:00+00:00",
    "context": "dadaia-workspace",
    "features": [
        {
            "rank": 1,
            "slug": "agent-comms",
            "title": "agent-comms — Handoff Contract v1",
            "category": "product",
            "tldr": "handoff-v1.1 separates HTML reports from JSON handoffs.",
            "summary": _HEAVY_SUMMARY,
            "tags": ["agent-comms", "handoff", "schema"],
            "token_estimate": 1230,
            "agent_tier": "self-pull",
            "path": "specs/memory/product/agents/agent-comms.md",
            "depends_on": ["public-asset-distribution"],
        },
        {
            "rank": 2,
            "slug": "context-injection",
            "title": "context-injection — Layer-1 self-pull bootstrap",
            "category": "platform",
            "tldr": (
                "ctx_inject injects a lean tech + catalog digest; deeper atoms are self-pulled."
            ),
            "summary": _HEAVY_SUMMARY,
            "tags": ["context", "injection"],
            "token_estimate": 980,
            "agent_tier": "self-pull",
            "path": "specs/memory/product/platform/context-management.md",
            "depends_on": [],
        },
    ],
}

# A small tech-stack atom (≤ the 24 non-empty-line cap) is emitted verbatim (stripped).
_TECH_STACK = "# Tech Stack\n\nPython 3.12 + poetry\npytest + mypy --strict + ruff\n"

# The constitution never reaches the bootstrap; of ARCHITECTURE.md and QUALITY.md only
# the marked fixed block does — the sentinel bodies outside the markers prove it.
_CONSTITUTION = "# Constitution\nSENTINEL_CONSTITUTION_BODY\n"
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

# The frozen golden. Captured from ``_build_memory`` under the fixture below; any Layer-1
# expansion (a new section, an appended atom, a header change, a join change) diverges
# from this literal and fails the lock. Assembled as explicit adjacent string literals so
# the exact bytes — the leading "\n", every indent level of the digested catalog JSON, and
# the absence of a trailing newline — are auditable in source.
_EXPECTED_BOOTSTRAP = (
    "\n"
    "=== workspace memory (tech + catalog) ===\n"
    "# Tech Stack\n"
    "\n"
    "Python 3.12 + poetry\n"
    "pytest + mypy --strict + ruff\n"
    "=== workspace law (fixed) ===\n"
    "### Slop — code (fixed)\n"
    "- LAW_CODE_BULLET\n"
    "### Slop — tests (fixed)\n"
    "- LAW_TESTS_BULLET\n"
    "{\n"
    '  "features": [\n'
    "    {\n"
    '      "slug": "agent-comms",\n'
    '      "title": "agent-comms — Handoff Contract v1",\n'
    '      "tldr": "handoff-v1.1 separates HTML reports from JSON handoffs.",\n'
    '      "path": "specs/memory/product/agents/agent-comms.md"\n'
    "    },\n"
    "    {\n"
    '      "slug": "context-injection",\n'
    '      "title": "context-injection — Layer-1 self-pull bootstrap",\n'
    '      "tldr": "ctx_inject injects a lean tech + catalog digest; deeper atoms are '
    'self-pulled.",\n'
    '      "path": "specs/memory/product/platform/context-management.md"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "=== end memory bootstrap ==="
)


def _build_fixture_specs(tmp_path: Path) -> Path:
    """Plant the fixture specs tree (tech digest, catalog, constitution, two marked atoms)."""
    specs = tmp_path / "specs"
    mem = specs / "memory"
    (mem / "product").mkdir(parents=True)
    (mem / "TECHSTACK.md").write_text(_TECH_STACK, encoding="utf-8")
    (mem / "product" / "catalog.json").write_text(
        json.dumps(_CATALOG, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (specs / "constitution.md").write_text(_CONSTITUTION, encoding="utf-8")
    (mem / "ARCHITECTURE.md").write_text(_ARCHITECTURE, encoding="utf-8")
    (mem / "QUALITY.md").write_text(_QUALITY, encoding="utf-8")
    return specs


def test_build_memory_bootstrap_is_byte_identical_golden(tmp_path: Path) -> None:
    """``_build_memory`` output equals the frozen golden byte-for-byte; the asserts
    after it are human-readable guards the golden already proves."""
    specs = _build_fixture_specs(tmp_path)
    built = ctx_inject._build_memory(specs)
    assert built == _EXPECTED_BOOTSTRAP

    # The constitution and the unmarked memory bodies stay self-pull.
    for sentinel in (
        "SENTINEL_CONSTITUTION_BODY",
        "SENTINEL_ARCHITECTURE_BODY",
        "SENTINEL_QA_BODY",
    ):
        assert sentinel not in built
    assert "=== workspace memory (tech + catalog) ===" in built
    assert built.rstrip("\n").endswith("=== end memory bootstrap ===")

    # The digest strips summary / rank / tags — only the lean 4 fields survive.
    assert _HEAVY_SUMMARY not in built
    assert '"summary"' not in built
    assert '"rank"' not in built
    assert '"tags"' not in built
    assert '"slug": "agent-comms"' in built
    assert '"path": "specs/memory/product/agents/agent-comms.md"' in built

    # Platform-invariance (v0.1.55): the host `specs_dir` path never leaks into output.
    # The golden is built purely from fixture file CONTENT, so the tmp_path sandbox path
    # (an absolute, OS-specific host path) must not appear anywhere in the bootstrap.
    assert str(tmp_path) not in built
    assert str(specs) not in built

    # No `memory/` dir ⇒ empty bootstrap (the guard clause).
    empty_specs = tmp_path / "empty-specs"
    empty_specs.mkdir()
    assert ctx_inject._build_memory(empty_specs) == ""
