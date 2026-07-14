"""Session-store ownership residue contract (T-010-07, WS-R3 / FR-R3-01).

`features.spec_context.session_identity` is the single owner of the session-identity
stores. This contract greps the active product surface for the two forbidden idioms:

  1. **Pointer-namespace construction** — building a ``sessions/runtime/*.ptr`` path.
     This retired namespace must not be constructed anywhere.

  2. **Session-record open** — building a ``sessions/<id>.json`` path to read/write the
     record. R3 routes the in-scope consumers (ctx_inject, spec_context.doctor,
     hooks/sdd_post_gate) through the owner. One consumer remains NOT migrated and carries an
     explicit, documented allowlist disposition:
       - ``core/specs_resolver.py`` — a core-layer READER that cannot import the
         ``features`` owner without violating the layering law (constitution §6); it
         performs a self-contained, read-only, fail-soft read of the same canonical path.

  The rc-2 amendment (NF-3) routed ``hooks/sdd_post_gate.py`` through
  ``session_identity.read_session`` / ``write_session``, dropping it from this allowlist.

The allowlist is closed: any NEW module that constructs a session-record path, and ANY
module other than the owner that constructs a pointer-namespace path, fails this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OWNER_RELPATH = "dadaia_workspace/features/spec_context/session_identity.py"

#: Idiom for the retired pointer namespace ``sessions/runtime/*.ptr``.
POINTER_IDIOMS: tuple[str, ...] = (
    '"sessions" / "runtime"',
    '"runtime" / f"{',
)

#: Idiom for the session-record path ``sessions/<id>.json`` — code that builds a session
#: record file from the sessions directory. Allowlisted consumers are enumerated below.
#:
#: T-011-05 (FR-W1-05 / ADR-12) extends this to also catch the SESSIONS-DIRECTORY
#: construction idiom (``"sessions"`` joined onto ``.dadaia``) — the 3 legal sites
#: (``cli/commands/context.py:76``, ``spec_context/doctor.py:124``,
#: ``panel/views/kanban.py:85``) previously built the directory and appended ``<id>.json``
#: themselves, slipping past the ``f"{`` interpolation grep. They are now migrated to the
#: ``session_identity`` accessors; this guards against the pattern's return.
RECORD_IDIOMS: tuple[str, ...] = (
    '"sessions" / f"{',
    '".dadaia" / "sessions"',
)


@dataclass(frozen=True)
class AllowedConsumer:
    relpath: str
    disposition: str


#: Modules permitted to construct a ``sessions/<id>.json`` record path despite not being
#: the owner. Closed set — adding to it requires a deliberate edit + justification.
ALLOWED_RECORD_CONSUMERS: tuple[AllowedConsumer, ...] = (
    AllowedConsumer(
        relpath="dadaia_workspace/core/specs_resolver.py",
        disposition="core-layer read-only reader; cannot import features owner (constitution §6)",
    ),
)

ACTIVE_PRODUCT_ROOT = "dadaia_workspace"

TEXT_SUFFIXES: frozenset[str] = frozenset({".py"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _iter_py_files(root: Path):  # type: ignore[no-untyped-def]
    for path in root.rglob("*.py"):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def test_pointer_and_record_namespace_residue_is_owner_or_allowlisted_only() -> None:
    """FR-R3-01: only session_identity may construct sessions/runtime/*.ptr (0 residue
    outside the owner), and session-record paths are built only by the owner or an
    allowlisted consumer."""
    repo = _repo_root()
    allowed = {c.relpath for c in ALLOWED_RECORD_CONSUMERS}
    pointer_failures: list[str] = []
    record_failures: list[str] = []
    for path in _iter_py_files(repo / ACTIVE_PRODUCT_ROOT):
        relpath = path.relative_to(repo).as_posix()
        text = path.read_text(encoding="utf-8")
        for idiom in POINTER_IDIOMS:
            if idiom in text:
                pointer_failures.append(f"{relpath}: constructs pointer-namespace path ({idiom!r})")
        if relpath != OWNER_RELPATH and relpath not in allowed:
            for idiom in RECORD_IDIOMS:
                if idiom in text:
                    record_failures.append(f"{relpath}: constructs session-record path ({idiom!r})")
    assert pointer_failures == [], (
        f"retired pointer-namespace residue must be 0: {pointer_failures}"
    )
    assert record_failures == [], (
        f"unexpected session-record opener (not owner/allowlisted): {record_failures}"
    )


def test_owner_and_allowlist_are_grounded_closed_and_minimal() -> None:
    """The owner module exists, the allowlist points at real documented files, and the
    allowlist is exactly the one not-migrated reader (NF-3/rc-2 migrated
    ``hooks/sdd_post_gate.py`` to ``session_identity``; only the core-layer reader,
    which cannot import the features owner under constitution §6, remains)."""
    repo = _repo_root()
    assert (repo / OWNER_RELPATH).exists()
    for consumer in ALLOWED_RECORD_CONSUMERS:
        assert (repo / consumer.relpath).exists(), consumer.relpath
        assert consumer.disposition.strip(), consumer.relpath
    relpaths = {c.relpath for c in ALLOWED_RECORD_CONSUMERS}
    assert relpaths == {
        "dadaia_workspace/core/specs_resolver.py",
    }
