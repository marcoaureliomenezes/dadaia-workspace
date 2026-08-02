"""Removal-on-release must actually fire on a real, segment-nested release.

The consumer-side validator drove the full lifecycle (R-19) and found the closing half
broken by two independent defects that compose: no real release ever clears its consumed
backlog, and the doctor never says so.

* ``_release_still_in_flight`` looked for ``releases/<id>/CLOSURE.md``, but the canonical
  layout every release actually uses is segmented — ``releases/<id>/<segment>/CLOSURE.md``.
  The check therefore always answered "still in flight", ``read_consumed`` always returned
  ``{}``, and BL-STALE could never fire. Same segment-nesting class as the SPEC-path bug.
* ``_residual_intents`` bound each intent through ``registry.bind()`` directly, without the
  ``surface: new`` special case ``consumes.py`` applies when it records shipped anchors. A
  ``surface: new`` item is recorded as ``new:<kind>:<ref>`` and looked up as a registry
  anchor, so it never matched and never left the live backlog.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.backlog.ledger import _release_still_in_flight


def _release(specs: Path, release_id: str, *, segment: str | None, closed: bool) -> None:
    base = specs / "releases" / release_id
    target = base / segment if segment else base
    target.mkdir(parents=True)
    (target / "SPEC.md").write_text("# SPEC\n", encoding="utf-8")
    if closed:
        (target / "CLOSURE.md").write_text("# CLOSURE\n", encoding="utf-8")


def test_a_closed_segmented_release_is_not_in_flight(tmp_path: Path) -> None:
    """The shape every real release has: CLOSURE.md inside the segment."""
    specs = tmp_path / "specs"
    _release(specs, "v0.1.0", segment="alpha-1", closed=True)

    assert _release_still_in_flight(specs, "v0.1.0") is False


def test_an_open_segmented_release_is_still_in_flight(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _release(specs, "v0.1.0", segment="alpha-1", closed=False)

    assert _release_still_in_flight(specs, "v0.1.0") is True


def test_closure_in_any_segment_closes_the_release(tmp_path: Path) -> None:
    """A release matures alpha-1 -> rc-1; closure lands in the segment that shipped."""
    specs = tmp_path / "specs"
    _release(specs, "v0.1.0", segment="alpha-1", closed=False)
    _release(specs, "v0.1.0", segment="rc-1", closed=True)

    assert _release_still_in_flight(specs, "v0.1.0") is False


def test_the_flat_layout_still_behaves(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _release(specs, "v0.1.0", segment=None, closed=True)
    _release(specs, "v0.2.0", segment=None, closed=False)

    assert _release_still_in_flight(specs, "v0.1.0") is False
    assert _release_still_in_flight(specs, "v0.2.0") is True


def test_an_archived_release_is_final(tmp_path: Path) -> None:
    """No live directory at all — the ledger is final, never 'in flight'."""
    specs = tmp_path / "specs"
    (specs / "releases").mkdir(parents=True)

    assert _release_still_in_flight(specs, "v9.9.9") is False


def _new_surface_item() -> tuple[object, object]:
    """One backlog item declaring a CLI surface that does not exist yet, plus an empty registry."""
    from dadaia_workspace.core.models.backlog import Intent, Subject, SubjectKind
    from dadaia_workspace.features.backlog.preview import BacklogItem
    from dadaia_workspace.features.backlog.subject_registry import Registry

    subject = Subject(kind=SubjectKind.CLI, ref="brand-new-verb", surface="new")
    item = BacklogItem(
        slug="adds-brand-new-verb",
        path=Path("specs/backlog/adds-brand-new-verb.md"),
        intents=(Intent(subject=subject, change="add the verb"),),
        status="candidate",
    )
    return item, Registry(anchors={}, aliases={})


def test_a_surface_new_intent_is_recognised_as_shipped() -> None:
    """`consumes` records a new surface as `new:<kind>:<ref>`; removal must look it up the same way.

    `_residual_intents` bound every intent through `registry.bind()`, which by definition
    cannot resolve a surface that does not exist yet. So the anchor `consumes` recorded and
    the anchor `removal` searched for could never be the same string, and a `surface: new`
    item stayed in the live backlog forever after its release shipped
    (bug backlog-remove-consumed-never-clears-surface-new).
    """
    from dadaia_workspace.features.backlog.preview import bound_anchor_changes
    from dadaia_workspace.features.backlog.removal import _residual_intents

    item, registry = _new_surface_item()

    # What `consume` writes into the ledger for this item:
    recorded, unresolved = bound_anchor_changes(item, registry)
    assert not unresolved
    shipped = frozenset(recorded)
    assert shipped == {"new:cli:brand-new-verb"}

    # What `remove-consumed` must then recognise:
    residual, any_shipped = _residual_intents(item, registry, shipped)

    assert any_shipped is True, "the shipped new surface was not recognised"
    assert residual == [], "a fully shipped item must have no residual intents"


def test_an_unshipped_intent_is_still_kept() -> None:
    """The guard must not start removing intents nobody shipped."""
    from dadaia_workspace.features.backlog.removal import _residual_intents

    item, registry = _new_surface_item()

    residual, any_shipped = _residual_intents(item, registry, frozenset({"new:cli:something-else"}))

    assert any_shipped is False
    assert len(residual) == 1


def test_a_terminal_backlog_item_needs_no_resolvable_intents() -> None:
    """A rejected/deferred item is never consumed, so its refs need not still resolve.

    The demolition deleted `features/lifecycle/`, and a backlog item that had asked for a
    workflow body there still pointed at those files. `backlog doctor` reported BL-SCHEMA
    on it forever: the refs resolve to no anchor because the anchors were deleted. The
    only ways out were to DELETE the file (forbidden — never delete a backlog file) or to
    falsify its refs. Neither is right: an item that will never be consumed does not need
    bindable intents, exactly as an `idea` does not.
    """
    from dadaia_workspace.core.models.backlog import is_intents_exempt

    assert is_intents_exempt("idea") is True
    for terminal in ("rejected", "deferred", "delivered", "consumed", "superseded", "resolved"):
        assert is_intents_exempt(terminal) is True, terminal
    for live in ("open", "picked", "candidate", None):
        assert is_intents_exempt(live) is False, live


def test_one_vocabulary_answers_for_the_whole_product() -> None:
    """Three modules each carried their own idea of what a backlog status IS.

    core knew six terminal tokens, `features/backlog/doctor` knew four — two of which
    (`done`, `closed`) nobody else had ever heard of — and `doctor_governance` knew a
    third four. Worse than drift: `consumed` is TERMINAL to the governance doctor, which
    demands such an item be moved into `_archive/`, while the backlog doctor rejected the
    very same token as an unknown status. Two laws of the same product contradicting each
    other, so no operator could satisfy both.
    """
    from dadaia_workspace.core.models.backlog import (
        BACKLOG_STATUSES,
        BACKLOG_TERMINAL_STATUSES,
    )
    from dadaia_workspace.features.backlog.doctor import _KNOWN_STATUSES, _TERMINAL_STATUSES
    from dadaia_workspace.features.specs.doctor_governance import _BACKLOG_TERMINAL_PREFIXES

    assert BACKLOG_TERMINAL_STATUSES <= BACKLOG_STATUSES
    assert _KNOWN_STATUSES == BACKLOG_STATUSES, "the backlog doctor must not keep its own copy"
    assert _TERMINAL_STATUSES == BACKLOG_TERMINAL_STATUSES
    assert set(_BACKLOG_TERMINAL_PREFIXES) <= BACKLOG_TERMINAL_STATUSES


def test_a_status_may_carry_the_release_suffix_the_skill_documents() -> None:
    """`DELIVERED — v0.4.2` is the documented disposition; it must parse to `delivered`.

    Bug closure-skill-delivered-suffix-rejected-by-bl-schema: the skill documented the
    format, the doctor exact-matched, and following our own instructions produced an error.
    """
    from dadaia_workspace.core.models.backlog import normalize_backlog_status

    assert normalize_backlog_status("DELIVERED — v0.4.2") == "delivered"
    assert normalize_backlog_status("delivered - v0.4.2") == "delivered"
    assert normalize_backlog_status("  Superseded — by other-slug ") == "superseded"
    assert normalize_backlog_status("candidate") == "candidate"
    assert normalize_backlog_status(None) is None
    assert normalize_backlog_status("") is None
