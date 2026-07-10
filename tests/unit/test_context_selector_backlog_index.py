"""T-26-01 — the ``backlog_index`` dynamic context selector (SPEC §3.5, ADR-D).

The selector returns, for **every** surviving ``specs/backlog/*.md`` item (excluding
``ideas.md``/``candidates.md``/the catalog), a compact record: the item's **bound intents**
(canonical anchor + change) and its **status**, parsed from the R1 ``intents[]`` frontmatter
only (never the body). All paths are resolved under the injected ``SpecContext``, never cwd.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    MaxContextPolicy,
    SpecContext,
    known_dynamic_inputs,
)

_RELEASE = "v0.1.26"

# A code anchor planted under the injected source root, so the registry binds it directly.
_LIVE_CODE_REF = "pkg/mod.py#do_thing"

_ITEM_ALPHA = f"""\
---
name: alpha-item
status: candidate
intents:
  - subject: {{ kind: code, ref: "{_LIVE_CODE_REF}" }}
    change: "alpha touches classify"
---

# alpha
Body prose that must NEVER be read by the index selector.
"""

_ITEM_BETA = f"""\
---
name: beta-item
status: picked
intents:
  - subject: {{ kind: code, ref: "{_LIVE_CODE_REF}" }}
    change: "beta touches classify differently"
---

# beta
"""

_IDEAS = "# ideas\n\nfree-form ideas, no intents.\n"
_CANDIDATES = "# candidates\n\nfree-form candidates.\n"


def _ctx(tmp_path: Path) -> SpecContext:
    """A minimal context tree with a planted source module so the registry binds the anchor."""
    specs = tmp_path / "specs"
    backlog = specs / "backlog"
    backlog.mkdir(parents=True)
    (backlog / "alpha-item.md").write_text(_ITEM_ALPHA, encoding="utf-8")
    (backlog / "beta-item.md").write_text(_ITEM_BETA, encoding="utf-8")
    (backlog / "ideas.md").write_text(_IDEAS, encoding="utf-8")
    (backlog / "candidates.md").write_text(_CANDIDATES, encoding="utf-8")
    # The registry derives code anchors from the injected source root (specs_dir.parent),
    # module-relative. Plant pkg/mod.py#do_thing so _LIVE_CODE_REF resolves directly.
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def do_thing() -> None:\n    pass\n", encoding="utf-8")
    return SpecContext(specs_dir=specs, release_id=_RELEASE)


def test_backlog_index_registered_and_does_not_read_body(tmp_path: Path) -> None:
    """FRONTMATTER-ONLY CONTRACT: this test proves the selector's registration AND the
    single load-bearing guarantee (the body prose is never leaked)."""
    assert "backlog_index" in known_dynamic_inputs()

    selector = ContextSelector(_ctx(tmp_path))
    result = selector.select("backlog_index", MaxContextPolicy.SUMMARY)

    assert "must NEVER be read" not in result.content


def test_backlog_index_returns_bound_intents_status_and_excludes_non_items(
    tmp_path: Path,
) -> None:
    selector = ContextSelector(_ctx(tmp_path))
    result = selector.select("backlog_index", MaxContextPolicy.SUMMARY)

    content = result.content
    # Both items appear with their status.
    assert "alpha-item" in content
    assert "candidate" in content
    assert "beta-item" in content
    assert "picked" in content
    # Bound canonical anchor + change is present (anchor id is the module-relative code ref).
    assert _LIVE_CODE_REF in content
    assert "alpha touches classify" in content
    assert "beta touches classify differently" in content
    # The item refs are recorded, item files only.
    assert any("alpha-item.md" in ref for ref in result.refs)
    assert any("beta-item.md" in ref for ref in result.refs)

    # ideas.md/candidates.md/catalog.json are excluded from both content and refs.
    assert "ideas" not in content.lower().replace("candidate", "")
    assert not any("ideas.md" in ref for ref in result.refs)
    assert not any("candidates.md" in ref for ref in result.refs)
    assert not any("catalog.json" in ref for ref in result.refs)


def test_backlog_index_empty_when_no_backlog(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir(parents=True)
    selector = ContextSelector(SpecContext(specs_dir=specs, release_id=_RELEASE))
    result = selector.select("backlog_index", MaxContextPolicy.SUMMARY)
    assert result.content == ""
    assert result.refs == ()
