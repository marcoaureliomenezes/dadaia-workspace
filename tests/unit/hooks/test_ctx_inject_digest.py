"""T-011-14 / FR-W4-03 / AC-W4-03 — ctx-inject catalog tldr-digest.

**tldr-digest of the injected catalog.** ``ctx_inject`` must inject a digest of
``catalog.json`` that keeps ``slug``/``title``/``tldr``/``path`` and drops the heavy
``summary`` field plus ``rank`` (F-77, v0.1.48: rank is alphabetical file order, not
priority — it must not reach the session digest). The catalog ON DISK must stay
byte-identical (self-pull depth intact). The injected payload must be measurably
smaller than injecting the raw catalog; the before/after byte sizes are asserted here
and recorded for CLOSURE. Driven through the harness-real subprocess runner (never an
in-process ``main()`` + ``sys.stdin`` simulation — banned by the harness-env contract).

Sentinel GC used to be pinned to inject time here (T-011-14); release 0.5.1 K2 retired
that leg — sentinels are now reaped by the ONE reaper,
``features.spec_context.presence.gc``, tested in ``tests/unit/features/spec_context/
test_presence_gc.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

# A realistic catalog fragment: each feature carries the heavy ``summary`` plus the lean
# fields the digest must preserve. Two entries so the size delta is unmistakable.
_HEAVY_SUMMARY = (
    "contrato handoff-v1.1 separa evidencia humana de coordenacao entre agentes: reports "
    "HTML em .dadaia/reports/<context>/<agent>/ e handoffs JSON em "
    ".dadaia/handoff/<context>/. O CLI valida schema e hash de artifact.path dentro do "
    "workspace; reports next e o gate QA/security consomem a raiz canonica. " * 4
)
_CATALOG = {
    "generated_at": "2026-06-10T15:19:56.146465+00:00",
    "context": "dadaia-workspace",
    "features": [
        {
            "rank": 1,
            "slug": "agent-comms",
            "title": "agent-comms — Handoff Contract v1",
            "category": "product",
            "tldr": "handoff-v1.1 separa reports HTML de handoffs JSON.",
            "summary": _HEAVY_SUMMARY,
            "tags": ["agent-comms", "handoff", "schema"],
            "token_estimate": 1230,
            "agent_tier": "self-pull",
            "path": "specs/memory/product/agents/agent-comms.md",
            "depends_on": ["public-asset-distribution"],
        },
        {
            "rank": 2,
            "slug": "agent-monitoring",
            "title": "agent-monitoring",
            "category": "product",
            "tldr": "telemetria local stdlib-only.",
            "summary": _HEAVY_SUMMARY,
            "tags": ["telemetry"],
            "token_estimate": 980,
            "agent_tier": "self-pull",
            "path": "specs/memory/product/agents/agent-monitoring.md",
            "depends_on": [],
        },
    ],
}


def _ws_with_catalog(tmp_path: Path, slug: str = "ctx") -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": slug, "state": "alive"}]}),
        encoding="utf-8",
    )
    mem = tmp_path / "repos" / slug / "specs" / "memory"
    (mem / "product").mkdir(parents=True)
    (mem / "TECHSTACK.md").write_text("# tech\nPython 3.12\n", encoding="utf-8")
    (mem / "product" / "catalog.json").write_text(
        json.dumps(_CATALOG, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tmp_path


def _run(tmp_path: Path, session_id: str, *, context: str | None = "ctx") -> str:
    """Invoke ctx_inject. ``context`` binds via the ``DADAIA_CONTEXT`` env leg so the
    catalog digest is injected (FR-W2-01: an UNBOUND session injects no memory). Pass
    ``context=None`` to exercise the unbound generic-preflight path.
    """
    extra = {"DADAIA_CONTEXT": context} if context else None
    env = claude_hook_env(tmp_path, extra=extra)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    if context is None:
        env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


def _injected_catalog_block(out: str) -> str:
    """Slice the catalog JSON object out of the emitted bootstrap payload."""
    start = out.index("{")
    # The catalog block is the last JSON object in the payload (after tech-stack.md).
    end = out.rindex("}") + 1
    return out[start:end]


def test_injected_catalog_is_tldr_digest_and_measurably_smaller(tmp_path: Path) -> None:
    ws = _ws_with_catalog(tmp_path)
    raw_catalog = (
        ws / "repos" / "ctx" / "specs" / "memory" / "product" / "catalog.json"
    ).read_text(encoding="utf-8")
    before = len(raw_catalog.encode("utf-8"))

    out = _run(tmp_path, "dig1")
    # The digest must be present and parseable.
    block = _injected_catalog_block(out)
    digest = json.loads(block)
    assert digest["features"], "digest must carry the feature entries"
    for feat in digest["features"]:
        # summary is the heavy field that must be dropped.
        assert "summary" not in feat
        # rank must be dropped too (F-77: alphabetical file order, not priority).
        assert "rank" not in feat
        # the lean fields the digest must preserve.
        assert set(feat) == {"slug", "title", "tldr", "path"}
    # Spot-check a concrete value survived the digest.
    first = digest["features"][0]
    assert first["slug"] == "agent-comms"
    assert first["path"] == "specs/memory/product/agents/agent-comms.md"

    # AC-W4-03 before/after byte assertion (numbers recorded for CLOSURE): a strict,
    # substantial reduction — summary is the bulk of the bytes.
    after = len(block.encode("utf-8"))
    assert after < before
    assert after < before * 0.5, (
        f"expected >50% reduction; before={before}B after={after}B ratio={after / before:.3f}"
    )

    # catalog.json on disk must stay byte-identical (self-pull depth intact) across a
    # SEPARATE inject run — the digest is a projection, never a rewrite of the source.
    catalog_path = ws / "repos" / "ctx" / "specs" / "memory" / "product" / "catalog.json"
    on_disk_before = catalog_path.read_bytes()
    _run(tmp_path, "dig3")
    on_disk_after = catalog_path.read_bytes()
    assert on_disk_before == on_disk_after, "catalog.json on disk must stay byte-identical"
    # The full summary must still be present on disk (self-pull depth intact).
    on_disk = json.loads(on_disk_after.decode("utf-8"))
    assert "summary" in on_disk["features"][0]


def test_index_md_fallback_emitted_verbatim_when_no_catalog(tmp_path: Path) -> None:
    """When catalog.json is absent the index.md fallback path is unaffected by the digest."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": "ctx", "state": "alive"}]}),
        encoding="utf-8",
    )
    mem = tmp_path / "repos" / "ctx" / "specs" / "memory"
    (mem / "product").mkdir(parents=True)
    (mem / "TECHSTACK.md").write_text("# tech\n", encoding="utf-8")
    (mem / "product" / "index.md").write_text("# product index\n- feature A\n", encoding="utf-8")
    out = _run(tmp_path, "idx1")
    assert "product index" in out
    assert "feature A" in out
