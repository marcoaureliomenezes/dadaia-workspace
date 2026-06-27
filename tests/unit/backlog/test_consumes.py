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


def test_parse_present_single_slug() -> None:
    spec = "# SPEC\n\n**Status:** Aprovado\n**Consumes:** my-feature\n\nbody\n"
    assert parse_consumes_line(spec) == ("my-feature",)


def test_parse_multi_slug_comma_separated_ordered() -> None:
    spec = "**Consumes:** alpha, beta, gamma\n"
    assert parse_consumes_line(spec) == ("alpha", "beta", "gamma")


def test_parse_dedups_preserving_first_order() -> None:
    spec = "**Consumes:** alpha, beta, alpha, gamma, beta\n"
    assert parse_consumes_line(spec) == ("alpha", "beta", "gamma")


def test_parse_strips_trailing_md_and_whitespace() -> None:
    spec = "**Consumes:**   foo.md ,  bar.md  \n"
    assert parse_consumes_line(spec) == ("foo", "bar")


def test_parse_absent_line_returns_empty() -> None:
    assert parse_consumes_line("# SPEC\n\n**Status:** Aprovado\n\nbody only\n") == ()


def test_parse_empty_consumes_line_returns_empty() -> None:
    assert parse_consumes_line("**Consumes:**\n") == ()
    assert parse_consumes_line("**Consumes:**    \n") == ()


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
    )
    return backlog, registry


def test_shipped_anchors_single_slug(tmp_path: Path) -> None:
    backlog, registry = _plant(tmp_path)
    assert shipped_anchors_for(("item-a",), backlog_dir=backlog, registry=registry) == frozenset(
        {_REF_A}
    )


def test_shipped_anchors_union_of_two_slugs(tmp_path: Path) -> None:
    backlog, registry = _plant(tmp_path)
    assert shipped_anchors_for(
        ("item-a", "item-b"), backlog_dir=backlog, registry=registry
    ) == frozenset({_REF_A, _REF_B})


def test_shipped_anchors_empty_slugs_returns_empty(tmp_path: Path) -> None:
    backlog, registry = _plant(tmp_path)
    assert shipped_anchors_for((), backlog_dir=backlog, registry=registry) == frozenset()


def test_unknown_slug_fails_loud(tmp_path: Path) -> None:
    backlog, registry = _plant(tmp_path)
    with pytest.raises(ConsumesBindError) as exc:
        shipped_anchors_for(("does-not-exist",), backlog_dir=backlog, registry=registry)
    assert "does-not-exist" in str(exc.value)


def test_slug_with_unresolved_intent_fails_loud(tmp_path: Path) -> None:
    backlog, registry = _plant(tmp_path)
    # An item whose intent's subject does not resolve against the registry.
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


def test_slug_with_zero_intents_fails_loud(tmp_path: Path) -> None:
    backlog, registry = _plant(tmp_path)
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
