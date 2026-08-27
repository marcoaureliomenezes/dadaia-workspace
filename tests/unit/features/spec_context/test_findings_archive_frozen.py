"""``specs/audits/_archive/`` classifies FROZEN before ADDITIVE for a ``FINDINGS.jsonl``
artifact (v0.5.0 FR13, T-050-23).

Intent: CONTRACT — 0.5.0 A13.2. ``project-auditor``'s write allowlist gains
``specs/audits/**`` (documentation, parsed at *projection* time — ``gate_policy.py``
carries no persona/allowlist concept at all); the fixture proves the ONE thing that IS
mechanically true regardless of any persona's declared allowlist: a file-tool write
under ``specs/audits/_archive/`` classifies FROZEN, matched BEFORE the
``specs/audits/`` ADDITIVE prefix, and is refused identically for every writer,
including this release's own ``FINDINGS.jsonl`` shape (never only the pre-existing
``AUDIT.md``/prose shape ``tests/unit/features/spec_context/test_gate_policy.py``
already covers).

Size: SMALL — pure function calls, no I/O.
"""

from __future__ import annotations

from dadaia_workspace.features.spec_context.gate_policy import PathClass, classify_path


def test_findings_jsonl_under_audits_archive_classifies_frozen_not_additive() -> None:
    """A ``FINDINGS.jsonl`` path under ``specs/audits/_archive/<slug>/`` classifies
    FROZEN — the ``_archive/`` per-artifact subdir is matched BEFORE the
    ``specs/audits/`` ADDITIVE prefix it would otherwise fall under (v0.1.46 AC-4 /
    R-2 ordering, still true at this fold; A13.2 restates it is the actual mechanism,
    not the persona allowlist, that refuses this write)."""
    rel_path = "specs/audits/_archive/2026-08-27T000000Z-abc12345/FINDINGS.jsonl"
    assert classify_path(rel_path) == PathClass.FROZEN


def test_findings_jsonl_under_live_audits_dir_classifies_additive() -> None:
    """The boundary case: the SAME artifact shape, one directory up (no ``_archive/``
    segment), classifies ADDITIVE — proving the FROZEN verdict above is about the
    ``_archive/`` landing zone, never about the ``FINDINGS.jsonl`` filename itself."""
    rel_path = "specs/audits/2026-08-27T000000Z-abc12345/FINDINGS.jsonl"
    assert classify_path(rel_path) == PathClass.ADDITIVE
