"""Session-store ownership residue contract (T-010-07, WS-R3 / FR-R3-01).

`features.spec_context.session_identity` is the single owner of the session-identity
stores. This contract greps the active product surface for the two forbidden idioms:

  1. **Pointer-namespace construction** — building a ``sessions/runtime/*.ptr`` path.
     This namespace is FULLY collapsed by R3: only ``session_identity`` may construct it.
     The grep is ratchet-free and MUST be 0 outside the owner.

  2. **Session-record open** — building a ``sessions/<id>.json`` path to read/write the
     record. R3 routes the in-scope consumers (lease, ctx_inject, spec_context.doctor)
     through the owner. Two consumers are NOT migrated by this task and carry an explicit,
     documented allowlist disposition:
       - ``hooks/sdd_post_gate.py`` — the PostToolUse heartbeat, owned by T-010-04 (next
         wave). It will route through ``session_identity.write_session`` then.
       - ``core/specs_resolver.py`` — a core-layer READER that cannot import the
         ``features`` owner without violating the layering law (constitution §6); it
         performs a self-contained, read-only, fail-soft read of the same canonical path.

The allowlist is closed: any NEW module that constructs a session-record path, and ANY
module other than the owner that constructs a pointer-namespace path, fails this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OWNER_RELPATH = "dadaia_workspace/features/spec_context/session_identity.py"

#: Idiom for the pointer namespace ``sessions/runtime/*.ptr`` — code that builds the
#: runtime pointer directory. Ratchet-free: 0 hits allowed outside the owner.
POINTER_IDIOMS: tuple[str, ...] = (
    '"sessions" / "runtime"',
    '"runtime" / f"{',
)

#: Idiom for the session-record path ``sessions/<id>.json`` — code that builds a session
#: record file from the sessions directory. Allowlisted consumers are enumerated below.
RECORD_IDIOMS: tuple[str, ...] = ('"sessions" / f"{',)


@dataclass(frozen=True)
class AllowedConsumer:
    relpath: str
    disposition: str


#: Modules permitted to construct a ``sessions/<id>.json`` record path despite not being
#: the owner. Closed set — adding to it requires a deliberate edit + justification.
ALLOWED_RECORD_CONSUMERS: tuple[AllowedConsumer, ...] = (
    AllowedConsumer(
        relpath="dadaia_workspace/hooks/sdd_post_gate.py",
        disposition="PostToolUse heartbeat — migrated to session_identity by T-010-04 (next wave)",
    ),
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


def test_pointer_namespace_has_no_residue_outside_owner() -> None:
    """FR-R3-01: only session_identity may construct sessions/runtime/*.ptr (0 residue)."""
    repo = _repo_root()
    failures: list[str] = []
    for path in _iter_py_files(repo / ACTIVE_PRODUCT_ROOT):
        relpath = path.relative_to(repo).as_posix()
        if relpath == OWNER_RELPATH:
            continue
        text = path.read_text(encoding="utf-8")
        for idiom in POINTER_IDIOMS:
            if idiom in text:
                failures.append(f"{relpath}: constructs pointer-namespace path ({idiom!r})")
    assert failures == [], f"pointer-namespace residue must be 0 outside the owner: {failures}"


def test_session_record_open_is_owner_or_allowlisted() -> None:
    """FR-R3-01: session-record paths are built only by the owner or an allowlisted consumer."""
    repo = _repo_root()
    allowed = {c.relpath for c in ALLOWED_RECORD_CONSUMERS}
    failures: list[str] = []
    for path in _iter_py_files(repo / ACTIVE_PRODUCT_ROOT):
        relpath = path.relative_to(repo).as_posix()
        if relpath == OWNER_RELPATH or relpath in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        for idiom in RECORD_IDIOMS:
            if idiom in text:
                failures.append(f"{relpath}: constructs session-record path ({idiom!r})")
    assert failures == [], f"unexpected session-record opener (not owner/allowlisted): {failures}"


def test_allowlisted_record_consumers_exist_and_are_documented() -> None:
    """The allowlist must point at real files with a non-empty disposition."""
    repo = _repo_root()
    for consumer in ALLOWED_RECORD_CONSUMERS:
        assert (repo / consumer.relpath).exists(), consumer.relpath
        assert consumer.disposition.strip(), consumer.relpath


def test_owner_module_exists() -> None:
    assert (_repo_root() / OWNER_RELPATH).exists()


def test_allowlist_is_closed_and_minimal() -> None:
    """Guard against silent growth: the allowlist is exactly the two not-yet-migrated readers."""
    relpaths = {c.relpath for c in ALLOWED_RECORD_CONSUMERS}
    assert relpaths == {
        "dadaia_workspace/hooks/sdd_post_gate.py",
        "dadaia_workspace/core/specs_resolver.py",
    }
