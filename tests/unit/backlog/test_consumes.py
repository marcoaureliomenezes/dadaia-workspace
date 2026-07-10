"""Unit tests for the ``**Consumes:**`` parser + anchor binder (v0.1.27, SPEC §3.1).

* T-1 — :func:`parse_consumes_line` extracts the bold-key ``**Consumes:**`` line from a
  release SPEC and returns an ordered, de-duplicated bare-slug tuple (whitespace-tolerant,
  ``.md``-stripping; absent line ⇒ empty tuple).
* T-2 — :func:`shipped_anchors_for` returns the UNION of the declared slugs' bound anchors.
* T-3/T-4 — :func:`shipped_anchors_for` fails loud (``ConsumesBindError``) on an unknown
  slug or unbindable intents, never returning a partial set.

All roots are injected under ``tmp_path`` — no cwd reads.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.consumes import (
    ConsumesBindError,
    parse_consumes_line,
    shipped_anchors_for,
)
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry

# ── T-1: parse_consumes_line ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        pytest.param(
            "# SPEC\n\n**Status:** Aprovado\n**Consumes:** my-feature\n\nbody\n",
            ("my-feature",),
            id="present-single-slug",
        ),
        pytest.param(
            "**Consumes:** alpha, beta, gamma\n",
            ("alpha", "beta", "gamma"),
            id="multi-slug-comma-separated-ordered",
        ),
        pytest.param(
            "**Consumes:** alpha, beta, alpha, gamma, beta\n",
            ("alpha", "beta", "gamma"),
            id="dedups-preserving-first-order",
        ),
        pytest.param(
            "**Consumes:**   foo.md ,  bar.md  \n",
            ("foo", "bar"),
            id="strips-trailing-md-and-whitespace",
        ),
        pytest.param(
            "# SPEC\n\n**Status:** Aprovado\n\nbody only\n",
            (),
            id="absent-line-returns-empty",
        ),
        pytest.param("**Consumes:**\n", (), id="empty-consumes-line-returns-empty"),
        pytest.param("**Consumes:**    \n", (), id="whitespace-only-consumes-line-returns-empty"),
    ],
)
def test_parse_consumes_line_matrix(spec: str, expected: tuple[str, ...]) -> None:
    assert parse_consumes_line(spec) == expected


# ── T-2/T-3/T-4: shipped_anchors_for ───────────────────────────────────────────────

_REF_A = "pkg/a.py#alpha_fn"
_REF_B = "pkg/b.py#beta_fn"


def _plant(tmp_path: Path) -> tuple[Path, Registry]:
    """Plant a backlog dir + source tree and return ``(backlog_dir, registry)``."""
    specs = tmp_path / "specs"
    backlog = specs / "backlog"
    backlog.mkdir(parents=True)
    item_a = f"""\
---
name: item-a
status: candidate
intents:
  - subject: {{ kind: code, ref: "{_REF_A}" }}
    change: "alpha shipped"
---

# item a
"""
    item_b = f"""\
---
name: item-b
status: candidate
intents:
  - subject: {{ kind: code, ref: "{_REF_B}" }}
    change: "beta shipped"
---

# item b
"""
    (backlog / "item-a.md").write_text(item_a, encoding="utf-8")
    (backlog / "item-b.md").write_text(item_b, encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def alpha_fn() -> None:\n    pass\n", encoding="utf-8")
    (pkg / "b.py").write_text("def beta_fn() -> None:\n    pass\n", encoding="utf-8")
    registry = build_registry(
        source_root=tmp_path,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )
    return backlog, registry


@pytest.mark.parametrize(
    ("slugs", "expected"),
    [
        pytest.param(("item-a",), frozenset({_REF_A}), id="single-slug"),
        pytest.param(("item-a", "item-b"), frozenset({_REF_A, _REF_B}), id="union-of-two-slugs"),
        pytest.param((), frozenset(), id="empty-slugs-returns-empty"),
    ],
)
def test_shipped_anchors_for_matrix(
    tmp_path: Path, slugs: tuple[str, ...], expected: frozenset[str]
) -> None:
    backlog, registry = _plant(tmp_path)
    assert shipped_anchors_for(slugs, backlog_dir=backlog, registry=registry) == expected


def test_unknown_slug_unresolved_intent_and_zero_intents_all_fail_loud(
    tmp_path: Path,
) -> None:
    """T-3/T-4: an unknown slug, an item whose intent's subject does not resolve
    against the registry, and an item with zero intents all raise
    ``ConsumesBindError`` naming the offending slug/ref — never a partial set."""
    backlog, registry = _plant(tmp_path)
    with pytest.raises(ConsumesBindError) as exc:
        shipped_anchors_for(("does-not-exist",), backlog_dir=backlog, registry=registry)
    assert "does-not-exist" in str(exc.value)

    bad = """\
---
name: bad-item
status: candidate
intents:
  - subject: { kind: code, ref: "pkg/ghost.py#nonexistent" }
    change: "this never shipped"
---

# bad
"""
    (backlog / "bad-item.md").write_text(bad, encoding="utf-8")
    with pytest.raises(ConsumesBindError) as exc:
        shipped_anchors_for(("bad-item",), backlog_dir=backlog, registry=registry)
    msg = str(exc.value)
    assert "bad-item" in msg
    assert "pkg/ghost.py#nonexistent" in msg

    empty = """\
---
name: empty-item
status: candidate
---

# no intents
"""
    (backlog / "empty-item.md").write_text(empty, encoding="utf-8")
    with pytest.raises(ConsumesBindError) as exc:
        shipped_anchors_for(("empty-item",), backlog_dir=backlog, registry=registry)
    assert "empty-item" in str(exc.value)
