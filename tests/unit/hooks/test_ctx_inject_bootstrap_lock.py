"""AC-7 (v0.1.57 FR4 / Ruling A) — Layer-1 self-pull bootstrap byte-identical lock.

FR4 RATIFIES self-pull: constitution / architecture / quality-assurance stay
self-pull-only at Layer-1, and ``ctx_inject._build_memory`` remains **byte-identical**
to pre-release — a bounded ``tech-stack.md`` digest + the lean ``catalog.json`` digest,
never the full memory tree. This module is the enforcement of that ruling: a
byte-identical golden on ``_build_memory``'s output for a fixed fixture specs tree. Any
future Layer-1 expansion (appending an atom to the bootstrap — architecture, QA, the
constitution, or anything else) breaks :data:`_EXPECTED_BOOTSTRAP` and this test goes
RED. That is exactly the AC-10(f) mutation-sanity check: append any atom to
``_build_memory``'s L1 bootstrap ⇒ this assert FAILS.

Why a golden and not a hard gate — Layer-2 grounding is the verifiable surface.
This wave adds **no** new gate. The mechanical proof that role grounding actually fired
lives on **Layer-2**: FR2 records each resolved role→atom ref in the run record's
``InjectedContext.refs``, and FR3's **FRAG-COH-4** doctor check asserts every
model-driven step's role-mapped atom appears in its injected refs. Layer-1 memory
grounding is deliberately kept as self-pull **discipline** (the deferred
``layer1-selfpull-handoff-audit-line`` backlog return would add a schema-level "prove
the atoms were read" field); this golden only *locks* that the L1 bootstrap does not
silently grow, it does not attempt to verify the atoms were read.

Platform-invariance (v0.1.55 law).
``_build_memory`` emits only the CONTENT of the fixture's ``tech-stack.md`` and
``catalog.json`` — never the host ``specs_dir`` path itself. The catalog ``path`` fields
in the golden are forward-slash, workspace-relative (``specs/memory/...``), so the
expected bytes carry no host path and no OS-specific separator; no normalization is
required and the golden is identical on every platform. A dedicated assertion pins that
the host ``tmp_path`` never leaks into the output.

``_build_memory`` is a pure function of ``specs_dir`` (no stdin, no subprocess), so it is
exercised in-process here — the harness-real subprocess contract applies to ``main()``
(which the sibling ``test_ctx_inject.py`` / ``test_ctx_inject_digest.py`` cover and which
stay green, unchanged in behaviour, under this ratification).
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

# Sentinel content for the three atoms that MUST NOT reach the L1 bootstrap under
# Ruling A. They exist in the fixture memory tree — proving the bootstrap deliberately
# ignores them (self-pull-only), not that the tree merely lacks them.
_FORBIDDEN_ATOMS: dict[str, str] = {
    "constitution.md": "# Constitution\nSENTINEL_CONSTITUTION_BODY\n",
    "architecture.md": "# Architecture\nSENTINEL_ARCHITECTURE_BODY\n",
    "quality-assurance.md": "# Quality Assurance\nSENTINEL_QA_BODY\n",
}

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
    """Plant the fixed fixture specs tree and return its ``specs`` dir.

    Writes ``tech-stack.md`` + ``product/catalog.json`` (the two atoms the L1 bootstrap
    digests) **and** the three forbidden atoms (constitution / architecture /
    quality-assurance) so the golden proves the bootstrap ignores them.
    """
    specs = tmp_path / "specs"
    mem = specs / "memory"
    (mem / "product").mkdir(parents=True)
    (mem / "tech-stack.md").write_text(_TECH_STACK, encoding="utf-8")
    (mem / "product" / "catalog.json").write_text(
        json.dumps(_CATALOG, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for name, body in _FORBIDDEN_ATOMS.items():
        (mem / name).write_text(body, encoding="utf-8")
    return specs


def test_build_memory_bootstrap_is_byte_identical_golden(tmp_path: Path) -> None:
    """AC-7 core lock: ``_build_memory`` output equals the frozen golden byte-for-byte."""
    specs = _build_fixture_specs(tmp_path)
    built = ctx_inject._build_memory(specs)
    assert built == _EXPECTED_BOOTSTRAP


def test_bootstrap_excludes_self_pull_only_atoms(tmp_path: Path) -> None:
    """Ruling A: constitution / architecture / quality-assurance never reach the L1 bootstrap.

    A redundant, human-readable guard alongside the byte golden: the AC-10(f) mutation
    (append any of these atoms) fails here too, and the intent is explicit in source.
    """
    specs = _build_fixture_specs(tmp_path)
    built = ctx_inject._build_memory(specs)
    for sentinel in (
        "SENTINEL_CONSTITUTION_BODY",
        "SENTINEL_ARCHITECTURE_BODY",
        "SENTINEL_QA_BODY",
    ):
        assert sentinel not in built
    # Only the two digest sections appear, framed by the fixed markers.
    assert "=== workspace memory (tech + catalog) ===" in built
    assert built.rstrip("\n").endswith("=== end memory bootstrap ===")


def test_bootstrap_drops_heavy_and_rank_catalog_fields(tmp_path: Path) -> None:
    """The digest strips ``summary`` / ``rank`` / ``tags`` — only the lean 4 fields survive."""
    specs = _build_fixture_specs(tmp_path)
    built = ctx_inject._build_memory(specs)
    assert _HEAVY_SUMMARY not in built
    assert '"summary"' not in built
    assert '"rank"' not in built
    assert '"tags"' not in built
    # The lean fields the digest preserves are present.
    assert '"slug": "agent-comms"' in built
    assert '"path": "specs/memory/product/agents/agent-comms.md"' in built


def test_bootstrap_carries_no_host_path(tmp_path: Path) -> None:
    """Platform-invariance (v0.1.55): the host ``specs_dir`` path never leaks into output.

    The golden is built purely from fixture file CONTENT, so the ``tmp_path`` sandbox
    path (an absolute, OS-specific host path) must not appear anywhere in the bootstrap.
    """
    specs = _build_fixture_specs(tmp_path)
    built = ctx_inject._build_memory(specs)
    assert str(tmp_path) not in built
    assert str(specs) not in built


def test_bootstrap_empty_when_no_memory_dir(tmp_path: Path) -> None:
    """No ``memory/`` dir ⇒ empty bootstrap (the guard clause), unchanged under FR4."""
    specs = tmp_path / "specs"
    specs.mkdir()
    assert ctx_inject._build_memory(specs) == ""
