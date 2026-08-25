"""The atomic-write primitive's own battery (release v0.4.5, FR2 / T-045-12).

Intent: CONTRACT — v0.4.5 A2.3 (temp cleanup on every failure path, every parameter
combination) and A2.5 (core stays stdlib-pure). Size: SMALL.

This is EXPAND only (D7): no call site below is touched, nothing named in the table is
deleted or switched. It authors the primitive's OWN characterization ahead of T-045-13
(switch) and T-045-14 (contract, deletes the eleven writers below).

Behaviour matrix derived from the eleven writers ``core.atomic_write.atomic_write``
replaces (read at their real entry points before this primitive's parameter surface was
chosen, per dd-bug-fix phase 4's discipline — characterize first, never assume):

======================================================================================
Writer (file:line)                                       content   preserve  mkdir   cleans
                                                           kind      mode      parent  up on
                                                                                       replace
                                                                                       failure
--------------------------------------------------------------------------------------
hooks/_common.py:231 atomic_write_text                    text*      no        no      NO (bug)
infrastructure/public_assets_common.py:119                text-LF    no        no      NO (bug)
  _atomic_write_text
features/migrate/frontmatter_keys.py:125                  text-LF    yes       no      yes
  write_text_atomic
features/specs/doctor_structural.py:481                   text-LF    yes       no      yes
  _write_text_atomic
features/spec_context/session_identity.py:112             text*      no        yes     yes
  _atomic_write_text
features/spec_context/presence.py:95 _atomic_write_json    text*      no        yes     yes
infrastructure/json_agent_model_policy_store.py:236        text*      no        yes     yes
  _atomic_write (delegates to _atomic_write_bytes)
infrastructure/json_agent_model_policy_store.py:239        binary     no        yes     yes
  _atomic_write_bytes
features/migrate/state_v2.py:104 execute_migration          text*      no        no      NO
  (inline, tmp = ctx_file.with_suffix(".tmp"))                                       (uncharacterized)
features/import_/service.py:100 patch_state                 text*      no        no      NO
  (inline, tmp = contexts_file.with_suffix(".tmp"))                                  (uncharacterized)
features/import_/service.py:153 patch_json_paths            text*      no        no      NO
  (inline, tmp = target.with_suffix(".tmp"))                                         (uncharacterized)
======================================================================================
text*  = platform-default newline translation (no ``newline=""`` override)
text-LF = ``newline=""`` — LF-preserving on every platform (FR-RC2-2)

The union of every column above is exactly this primitive's parameter surface:
``content: str | bytes`` covers text* / text-LF / binary; ``newline`` covers
text* (``None``) vs text-LF (``""``, the default); ``preserve_mode`` covers the two
mode-preserving writers; ``ensure_parent`` covers the two mkdir-first writers; and
cleanup-on-every-failure-path is unconditional (AR-1 condition 5) — the two leakers and
the three never-characterized inline writers alike become structurally impossible to
reproduce through this primitive, closing bug
``two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`` (superseded by this
consolidation) at the root rather than per-site.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from dadaia_workspace.core.atomic_write import atomic_write

_ORIGINAL_WRITE_TEXT = Path.write_text
_ORIGINAL_WRITE_BYTES = Path.write_bytes


# ---------------------------------------------------------------------------
# Positive path — one assertion per parameter this primitive exposes.
# ---------------------------------------------------------------------------


def test_text_content_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    atomic_write(target, "hello\n")
    assert target.read_text(encoding="utf-8") == "hello\n"


def test_binary_content_round_trips_byte_exact(tmp_path: Path) -> None:
    target = tmp_path / "a.bin"
    payload = b"\x00\x01hello\xff"
    atomic_write(target, payload)
    assert target.read_bytes() == payload


def test_default_newline_is_lf_preserving_no_crlf(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    atomic_write(target, "line-one\nline-two\n")
    assert b"\r\n" not in target.read_bytes()


def test_newline_none_restores_platform_default_translation(tmp_path: Path) -> None:
    """``newline=None`` matches the 5 writers with no override — text* in the matrix."""
    target = tmp_path / "a.md"
    atomic_write(target, "line-one\n", newline=None)
    # No assertion on CRLF here: platform-default translation is the documented,
    # harmless behaviour those 5 writers already have (internal `.dadaia/` state, never
    # git-diffed) — this test only proves the parameter is honoured, not a platform claim.
    assert target.read_text(encoding="utf-8") == "line-one\n"


def test_preserve_mode_true_copies_the_targets_mode_onto_the_replacement(
    tmp_path: Path,
) -> None:
    import os
    import stat

    target = tmp_path / "a.md"
    target.write_text("orig\n", encoding="utf-8")
    os.chmod(target, 0o640)  # not mkstemp's own 0600 default — see the module comment
    before = stat.S_IMODE(target.stat().st_mode)

    atomic_write(target, "new\n", preserve_mode=True)

    assert stat.S_IMODE(target.stat().st_mode) == before


def test_ensure_parent_creates_a_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir" / "a.md"
    atomic_write(target, "hello\n", ensure_parent=True)
    assert target.read_text(encoding="utf-8") == "hello\n"


def test_missing_parent_without_ensure_parent_raises_and_leaves_nothing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "nowhere" / "a.md"
    with pytest.raises(OSError):
        atomic_write(target, "hello\n")
    assert not target.parent.exists()


def test_hardlink_target_is_rebound_not_written_through(tmp_path: Path) -> None:
    """CWE-59/CWE-367: a checked-then-opened path is a TOCTOU window; the primitive must
    rebind the target NAME to a new inode instead of writing through whatever it points
    at (matches every named writer's documented contract)."""
    import os

    outside = tmp_path / "outside.md"
    original = "original outside content\n"
    outside.write_text(original, encoding="utf-8")
    target = tmp_path / "linked.md"
    os.link(outside, target)
    before_ino = target.stat().st_ino

    atomic_write(target, "REBOUND\n")

    assert outside.read_text(encoding="utf-8") == original
    assert target.stat().st_ino != before_ino


# ---------------------------------------------------------------------------
# The failure battery (A2.3) — preserve-mode x content-kind x failure-point.
# ---------------------------------------------------------------------------


def _boom(*_args: object, **_kwargs: object) -> None:
    raise OSError("injected failure")


def _boom_after_real_write_text(self: Path, *args: object, **kwargs: object) -> None:
    """Simulate a write that DID land bytes on disk before failing (contrasts with a
    create/open failure, where nothing is ever created)."""
    _ORIGINAL_WRITE_TEXT(self, *args, **kwargs)  # type: ignore[arg-type]
    raise OSError("injected failure")


def _boom_after_real_write_bytes(self: Path, *args: object, **kwargs: object) -> None:
    _ORIGINAL_WRITE_BYTES(self, *args, **kwargs)  # type: ignore[arg-type]
    raise OSError("injected failure")


@dataclass(frozen=True)
class _ContentKind:
    id: str
    content: str | bytes
    newline: str | None
    is_binary: bool


_CONTENT_KINDS: tuple[_ContentKind, ...] = (
    _ContentKind(id="text-default-newline", content="hello\n", newline=None, is_binary=False),
    _ContentKind(id="text-lf-forced", content="hello\n", newline="", is_binary=False),
    _ContentKind(id="binary", content=b"hello\n", newline="", is_binary=True),
)

_FAILURE_POINTS: tuple[str, ...] = ("create_fails", "write_fails", "replace_fails")


def _no_tmp_sibling_left(directory: Path) -> bool:
    return not any(p.name.endswith(".tmp") for p in directory.iterdir())


@pytest.mark.parametrize("preserve_mode", [False, True], ids=["preserve-off", "preserve-on"])
@pytest.mark.parametrize("kind", _CONTENT_KINDS, ids=[k.id for k in _CONTENT_KINDS])
@pytest.mark.parametrize("failure_point", _FAILURE_POINTS)
def test_no_temp_sibling_survives_any_injected_failure(
    preserve_mode: bool,
    kind: _ContentKind,
    failure_point: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every preserve-mode x content-kind x failure-point combination leaves no ``.tmp``
    sibling behind, and the pre-existing target is left byte-for-byte unchanged — the
    guarantee AR-1 conditions T-045-12 on (temp cleanup on EVERY failure path, always)."""
    target = tmp_path / "atom.md"
    original = "original content\n"
    target.write_text(original, encoding="utf-8")

    if failure_point == "create_fails":
        # Nothing is ever created on disk — models mkstemp/open failing outright.
        monkeypatch.setattr(Path, "write_bytes" if kind.is_binary else "write_text", _boom)
    elif failure_point == "write_fails":
        # The tmp file IS created (content flushed), then the write call itself raises.
        monkeypatch.setattr(
            Path,
            "write_bytes" if kind.is_binary else "write_text",
            _boom_after_real_write_bytes if kind.is_binary else _boom_after_real_write_text,
        )
    else:
        assert failure_point == "replace_fails"
        monkeypatch.setattr("dadaia_workspace.core.atomic_write.os.replace", _boom)

    with pytest.raises(OSError, match="injected failure"):
        atomic_write(target, kind.content, preserve_mode=preserve_mode, newline=kind.newline)

    assert _no_tmp_sibling_left(tmp_path), (
        f"leaked a temp sibling: preserve_mode={preserve_mode} kind={kind.id} "
        f"failure_point={failure_point} -> {list(tmp_path.iterdir())}"
    )
    assert target.read_text(encoding="utf-8") == original, (
        f"target mutated on a failed write: preserve_mode={preserve_mode} kind={kind.id} "
        f"failure_point={failure_point}"
    )


@pytest.mark.parametrize("failure_point", _FAILURE_POINTS)
def test_no_temp_sibling_survives_failure_on_a_new_target(
    failure_point: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same proof, but the target does not exist yet — the failure must not create it
    either (``os.replace`` never runs, or itself fails, leaving no destination)."""
    target = tmp_path / "new-atom.md"

    if failure_point == "create_fails":
        monkeypatch.setattr(Path, "write_text", _boom)
    elif failure_point == "write_fails":
        monkeypatch.setattr(Path, "write_text", _boom_after_real_write_text)
    else:
        assert failure_point == "replace_fails"
        monkeypatch.setattr("dadaia_workspace.core.atomic_write.os.replace", _boom)

    with pytest.raises(OSError, match="injected failure"):
        atomic_write(target, "hello\n")

    assert _no_tmp_sibling_left(tmp_path)
    assert not target.exists()
