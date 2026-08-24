"""``frontmatter_keys.py`` — bug
``migration-normalises-crlf-atoms-to-lf-contradicting-its-byte-preserve-wording`` (LOW,
T-044-37).

Intent: REGRESSION (bug
migration-normalises-crlf-atoms-to-lf-contradicting-its-byte-preserve-wording). Size:
SMALL.

DECIDED (per the module docstring, this task): the migration is LF-canonical, not
byte-preserving of line endings — consistent with the platform-wide LF-canonical write
contract (``write_text_atomic``'s own ``newline=""`` guarantee, matched by
``infrastructure/public_assets_common``'s writer for projected assets, FR-RC2-2). This
module pins both halves of that decision so the composition cannot silently regress
either way:

1. ``strip_frontmatter_keys``/``write_text_atomic`` are themselves line-ending AGNOSTIC —
   fed CRLF text directly (bypassing ``Path.read_text``), they reproduce CRLF verbatim.
   A future change that makes either function itself rewrite line endings would be a new,
   undecided third behaviour and must fail this test.
2. The composed migration — every registered step's real
   ``Path.read_text()`` -> ``strip_frontmatter_keys`` -> ``write_text_atomic`` pipeline —
   normalises a CRLF atom to LF on disk, because ``Path.read_text()``'s universal-newline
   translation runs before this module ever sees the text. This is the DECIDED, pinned
   end-to-end contract.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.migrate.frontmatter_keys import (
    strip_frontmatter_keys,
    write_text_atomic,
)
from dadaia_workspace.features.migrate.retired_frontmatter_keys import (
    migrate_retired_frontmatter_keys,
)


def test_strip_frontmatter_keys_preserves_crlf_given_directly() -> None:
    """Fed CRLF text directly, the scanner/reassembler keep every surviving line's own
    terminator — the function is line-ending agnostic, not a CRLF normaliser itself."""
    text = "---\r\nslug: x\r\nagent_tier: self-pull\r\n---\r\n\r\nBody.\r\n"

    result = strip_frontmatter_keys(text, drop=lambda key: key == "agent_tier")

    assert result == "---\r\nslug: x\r\n---\r\n\r\nBody.\r\n"


def test_write_text_atomic_preserves_crlf_given_directly(tmp_path: Path) -> None:
    """``newline=""`` only stops LF being expanded to CRLF on Windows; it does not
    collapse a CRLF the caller already put in ``text``."""
    target = tmp_path / "atom.md"

    write_text_atomic(target, "line one\r\nline two\r\n")

    assert target.read_bytes() == b"line one\r\nline two\r\n"


def test_migration_normalises_a_crlf_atom_to_lf_on_disk(tmp_path: Path) -> None:
    """The composed migration is LF-canonical end to end: a CRLF atom carrying a retired
    key leaves with LF on every line, not only the ones the key removal touched — the
    pinned, DECIDED contract this task's docstring update states."""
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    atom = specs / "memory" / "a.md"
    original = (
        "---\r\nslug: x\r\nagent_tier: self-pull\r\n---\r\n\r\nBody line one.\r\nBody line two.\r\n"
    )
    atom.write_bytes(original.encode("utf-8"))

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    migrated_bytes = atom.read_bytes()
    assert b"\r\n" not in migrated_bytes, (
        "migration left CRLF on disk — contradicts the LF-canonical contract"
    )
    assert migrated_bytes == b"---\nslug: x\n---\n\nBody line one.\nBody line two.\n"
    assert len(result.moved) == 1
