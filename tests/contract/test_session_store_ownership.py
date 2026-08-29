"""Session-store ownership residue contract (T-010-07, WS-R3 / FR-R3-01).

`core.session_store` (release K1: moved here from ``features.spec_context.session_identity``
— core cannot import features, and :mod:`core.invocation` needs to read a session
record directly) is the single owner of the session-identity stores. This contract
greps the active product surface for the two forbidden idioms:

  1. **Pointer-namespace construction** — building a ``sessions/runtime/*.ptr`` path.
     This retired namespace must not be constructed anywhere.

  2. **Session-record open** — building a ``sessions/<id>.json`` path to read/write the
     record. Every consumer (ctx_inject, spec_context.doctor, hooks/sdd_post_gate,
     core.invocation, cli.commands.context) routes through the owner now — release K1
     retired the last documented exception (the old ``core/specs_resolver.py``, which
     had to reimplement the read itself because ``core`` could not import the
     ``features``-layer owner; ``core.invocation`` has no such problem, since the owner
     moved into ``core`` alongside it). The allowlist is therefore EMPTY.

The allowlist is closed: any NEW module that constructs a session-record path, and ANY
module other than the owner that constructs a pointer-namespace path, fails this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.helpers.scan_population import assert_populated

OWNER_RELPATH = "dadaia_workspace/core/session_store.py"

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
#: ``session_store`` accessors; this guards against the pattern's return.
RECORD_IDIOMS: tuple[str, ...] = (
    '"sessions" / f"{',
    '".dadaia" / "sessions"',
)


@dataclass(frozen=True)
class AllowedConsumer:
    relpath: str
    disposition: str


#: Modules permitted to construct a ``sessions/<id>.json`` record path despite not being
#: the owner. EMPTY (release K1): the owner now lives in ``core``, so every consumer —
#: including ``core.invocation`` — can (and does) import it directly; no layering
#: exception is needed any more.
ALLOWED_RECORD_CONSUMERS: tuple[AllowedConsumer, ...] = ()

ACTIVE_PRODUCT_ROOT = "dadaia_workspace"

TEXT_SUFFIXES: frozenset[str] = frozenset({".py"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _iter_py_files(root: Path):  # type: ignore[no-untyped-def]
    for path in root.rglob("*.py"):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def test_pointer_and_record_namespace_residue_is_owner_or_allowlisted_only() -> None:
    """FR-R3-01: only session_store may construct sessions/runtime/*.ptr (0 residue
    outside the owner), and session-record paths are built only by the owner (the
    allowlist is empty since release K1)."""
    repo = _repo_root()
    py_files = list(_iter_py_files(repo / ACTIVE_PRODUCT_ROOT))
    # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted ACTIVE_PRODUCT_ROOT would
    # degrade this walk to zero files, under which both `== []` assertions below pass
    # vacuously green.
    assert_populated(py_files, sentinel=repo / OWNER_RELPATH)
    allowed = {c.relpath for c in ALLOWED_RECORD_CONSUMERS}
    pointer_failures: list[str] = []
    record_failures: list[str] = []
    for path in py_files:
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
    """The owner module exists and the allowlist is empty (release K1: the owner moved
    into ``core``, so the one prior not-migrated reader — a core-layer module that
    could not import the old ``features``-layer owner — no longer needs an exception)."""
    repo = _repo_root()
    assert (repo / OWNER_RELPATH).exists()
    for consumer in ALLOWED_RECORD_CONSUMERS:
        assert (repo / consumer.relpath).exists(), consumer.relpath
        assert consumer.disposition.strip(), consumer.relpath
    relpaths = {c.relpath for c in ALLOWED_RECORD_CONSUMERS}
    assert relpaths == set()
