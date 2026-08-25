"""Security review of the 0.4.3 mint — the write sites must never follow a link, and one
bad atom must never strand a half-migrated tree.

Intent: REGRESSION (security-reviewer findings on the 0.4.3 develop delta: CWE-59/CWE-61
link following, CWE-73 externally supplied path, CWE-703 unchecked exceptional condition,
CWE-674 uncontrolled recursion; bug
``atomic-writer-drift-guard-is-brittle-and-covers-only-two-of-eight-writers`` — T-044-35).
Size: SMALL.

This repo has already paid for the link-following class once (the dangling
``tests/AGENTS.md`` symlink). These tests pin the doctrine at every write site introduced
or touched by the retired-frontmatter-keys work, so the third recurrence cannot happen
quietly.

The ``AtomicWriterCase`` battery below pins BEHAVIOUR, not source text, across every one
of the package's 10 atomic-writer primitives (mkstemp/uuid tmp-file + ``os.replace``) —
replacing a prior guard that sliced two of them on triple-quote boundaries and compared
stripped lines (broke on a reworded comment, mis-sliced on an embedded triple-quoted
literal, raised ``IndexError`` instead of asserting on a missing docstring, and never
looked at the other 6 writers at all).

A ninth writer (``state_v3._atomic_write_json``) was added by S4, after the original
8-writer census, with a fixed symlink-followable tmp name — invisible to a census scoped
to named helpers that already existed. T-044-45 F-4 fixed the writer (unique ``uuid4``
name, matching the idiom below) and added it here as the 9th entry, plus a self-enforcing
scan test (``test_census_covers_every_atomic_writer_def_in_the_package``) so the *next*
new writer cannot silently escape the same way.

A 10th, ``core.atomic_write.atomic_write`` (v0.4.5 FR2/T-045-12, architect ruling AR-1),
is the eleven writers' eventual single replacement — pinned here at its default
configuration only, so this census stays green; the full preserve-mode x content-kind x
failure-point matrix it actually supports lives in
``tests/unit/core/test_atomic_write.py``. EXPAND phase (D7): no call site below moves or
is deleted by this addition.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from dadaia_workspace.core.atomic_write import atomic_write as _core_atomic_write
from dadaia_workspace.features.migrate.agent_tier_frontmatter import (
    migrate_agent_tier_frontmatter,
)
from dadaia_workspace.features.migrate.frontmatter_keys import write_text_atomic
from dadaia_workspace.features.migrate.retired_frontmatter_keys import (
    migrate_retired_frontmatter_keys,
)
from dadaia_workspace.features.migrate.state_v3 import (
    _atomic_write_json as _state_v3_atomic_write_json,
)
from dadaia_workspace.features.spec_context.presence import (
    _atomic_write_json as _presence_atomic_write_json,
)
from dadaia_workspace.features.spec_context.session_identity import (
    _atomic_write_text as _session_identity_atomic_write_text,
)
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_structural import (
    _write_text_atomic as _doctor_structural_write_text_atomic,
)
from dadaia_workspace.features.specs.template_history import (
    SHIPPED_HASHES_FILENAME,
    load_shipped_hashes,
)
from dadaia_workspace.hooks._common import atomic_write_text as _hooks_common_atomic_write_text
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)
from dadaia_workspace.infrastructure.public_assets_common import (
    _atomic_write_text as _public_assets_atomic_write_text,
)

_REPO_ROOT = Path(__file__).parents[4]
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_CANONICAL_TEXT = (_TEMPLATES_DIR / "specs-AGENTS.md").read_text(encoding="utf-8")

_ATOM_WITH_RETIRED_KEYS = "---\nslug: x\nagent_tier: self-pull\ntoken_estimate: 999\n---\n\nBody.\n"


def _specs_with_memory(root: Path) -> Path:
    specs = root / "specs"
    (specs / "memory").mkdir(parents=True)
    return specs


def test_migrations_never_write_through_a_symlinked_atom(tmp_path: Path) -> None:
    """A symlinked atom points at a file outside the tree being migrated; both migration
    steps must leave it — and its target — untouched."""
    for name, migrate in (
        ("retired", migrate_retired_frontmatter_keys),
        ("agent-tier", migrate_agent_tier_frontmatter),
    ):
        outside = tmp_path / f"{name}-outside.md"
        outside.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")
        specs = _specs_with_memory(tmp_path / name)
        (specs / "memory" / "linked.md").symlink_to(outside)

        result = migrate(specs, dry_run=False)

        assert outside.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS, (
            f"{name} migration wrote through a symlink"
        )
        assert result.moved == []
        assert any("symlink" in note for note in result.skipped)


def test_one_unreadable_atom_does_not_strand_the_tree(tmp_path: Path) -> None:
    """A dangling link must not abort the run: every healthy atom still migrates and the
    skip is reported instead of raised."""
    specs = _specs_with_memory(tmp_path / "mixed")
    (specs / "memory" / "dangling.md").symlink_to(tmp_path / "nope.md")
    healthy = specs / "memory" / "healthy.md"
    healthy.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert "token_estimate" not in healthy.read_text(encoding="utf-8")
    assert result.moved and result.skipped


def test_fix_tree5_refuses_a_symlinked_projection(tmp_path: Path) -> None:
    """The repair must not write the canonical template through a link, and must ignore a
    caller-supplied path — the target is always derived from the specs dir."""
    stale = "# stale\n"
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    import hashlib

    (templates / SHIPPED_HASHES_FILENAME).write_text(
        json.dumps(
            {
                "specs-AGENTS.md": [
                    hashlib.sha256(t.encode("utf-8")).hexdigest() for t in (_CANONICAL_TEXT, stale)
                ]
            }
        ),
        encoding="utf-8",
    )

    outside = tmp_path / "outside_agents.md"
    outside.write_text(stale, encoding="utf-8")
    specs = _specs_with_memory(tmp_path / "linked")
    (specs / "AGENTS.md").symlink_to(outside)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    doctor.fix(doctor.check())

    assert outside.read_text(encoding="utf-8") == stale, "fix_tree5 wrote through a symlink"


def test_corrupt_history_degrades_instead_of_killing_the_doctor(tmp_path: Path) -> None:
    """A deeply nested history blows the JSON parser's stack; it must degrade to "nothing
    is provably ours" like every other malformation."""
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / SHIPPED_HASHES_FILENAME).write_text("[" * 200_000, encoding="utf-8")

    assert load_shipped_hashes(templates) == {}


def test_migrations_never_write_through_a_hardlink(tmp_path: Path) -> None:
    """A hard link is not a symlink, so the link guard alone misses it: writing must
    rebind the name (temp file + os.replace) instead of writing through the inode."""
    import os

    outside = tmp_path / "hardlink-outside.md"
    outside.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")
    specs = _specs_with_memory(tmp_path / "hardlink")
    os.link(outside, specs / "memory" / "linked.md")

    migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert outside.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS, (
        "migration wrote through a hard link into a file outside the tree"
    )
    assert "token_estimate" not in (specs / "memory" / "linked.md").read_text(encoding="utf-8")


def test_symlinked_projection_is_not_advertised_as_fixable(tmp_path: Path) -> None:
    """The repair refuses a symlinked projection, so the check must not promise it —
    a reported fix that never happens is its own defect."""
    import hashlib

    stale = "# stale\n"
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    (templates / SHIPPED_HASHES_FILENAME).write_text(
        json.dumps(
            {
                "specs-AGENTS.md": [
                    hashlib.sha256(t.encode("utf-8")).hexdigest() for t in (_CANONICAL_TEXT, stale)
                ]
            }
        ),
        encoding="utf-8",
    )
    outside = tmp_path / "outside.md"
    outside.write_text(stale, encoding="utf-8")
    specs = _specs_with_memory(tmp_path / "advertise")
    (specs / "AGENTS.md").symlink_to(outside)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    tree5 = [i for i in doctor.check() if i.code == "TREE-5"]
    assert tree5 and not tree5[0].fixable
    assert doctor.fix(doctor.check()) == [] or all(i.code != "TREE-5" for i in doctor.fix())


def test_repair_preserves_file_mode_and_newlines(tmp_path: Path) -> None:
    """Atomic replacement must not leak mkstemp's 0600 onto the target, nor let Windows
    text mode rewrite LF as CRLF — the write is byte-exact by contract."""
    import os
    import stat

    specs = _specs_with_memory(tmp_path / "mode")
    atom = specs / "memory" / "a.md"
    atom.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8", newline="")  # T-044-36
    os.chmod(atom, 0o644)
    # Assert PRESERVATION against the mode actually on disk, never a hard-coded 0o644:
    # Windows has no POSIX mode bits (chmod only toggles the read-only attribute, so every
    # file reads back 0o666) and the contract under test is "the repair does not change the
    # mode", which is exactly what this comparison states on every platform.
    before = stat.S_IMODE(atom.stat().st_mode)

    migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert stat.S_IMODE(atom.stat().st_mode) == before, "repair changed the atom's mode"
    assert b"\r\n" not in atom.read_bytes(), "repair introduced CRLF"


def test_symlinked_memory_directory_is_refused(tmp_path: Path) -> None:
    """The walk ROOT can itself be a link out of the tree: the per-file guard cannot see
    it, because every atom inside is a regular file."""
    outside = tmp_path / "outside-memory"
    outside.mkdir()
    victim = outside / "c.md"
    victim.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")

    specs = tmp_path / "rootlink" / "specs"
    specs.mkdir(parents=True)
    (specs / "memory").symlink_to(outside, target_is_directory=True)

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert victim.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS
    assert result.moved == []
    assert any("symlink" in note for note in result.skipped)


def test_read_only_atom_is_left_alone(tmp_path: Path) -> None:
    """Replacement needs only directory permission, so a read-only atom would be rewritten
    silently; the operator's flag is honoured instead."""
    import os

    specs = _specs_with_memory(tmp_path / "readonly")
    atom = specs / "memory" / "ro.md"
    atom.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")
    os.chmod(atom, 0o444)
    try:
        result = migrate_retired_frontmatter_keys(specs, dry_run=False)
        assert atom.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS
        assert any("read-only" in note for note in result.skipped)
    finally:
        os.chmod(atom, 0o644)


@dataclass(frozen=True)
class AtomicWriterCase:
    """One of the package's 10 atomic-writer primitives, called at its real entry point.

    ``preserves_mode``/``cleans_up_on_failure`` are the ACTUAL, empirically-verified
    contract of the writer named by ``id`` — not an aspiration. Where a writer's real
    behaviour is a known gap, the field says so and the test below pins that gap
    (with a bug reference) rather than asserting something false.
    """

    id: str
    write: Callable[[Path, str], None]
    replace_target: str
    preserves_mode: bool
    cleans_up_on_failure: bool
    lf_bytes_guaranteed: bool  # newline="" or binary mode — CRLF-proof on every platform


def _write_frontmatter_keys(path: Path, marker: str) -> None:
    write_text_atomic(path, f"{marker}\n")


def _write_doctor_structural(path: Path, marker: str) -> None:
    _doctor_structural_write_text_atomic(path, f"{marker}\n")


def _write_hooks_common(path: Path, marker: str) -> None:
    _hooks_common_atomic_write_text(path, f"{marker}\n")


def _write_public_assets_common(path: Path, marker: str) -> None:
    _public_assets_atomic_write_text(path, f"{marker}\n")


def _write_session_identity(path: Path, marker: str) -> None:
    _session_identity_atomic_write_text(path, f"{marker}\n")


def _write_presence_json(path: Path, marker: str) -> None:
    _presence_atomic_write_json(path, {"marker": marker})


def _write_policy_store_text(path: Path, marker: str) -> None:
    # workspace_root is irrelevant here — _atomic_write takes the target path
    # explicitly; the store instance only supplies the method (the real entry point).
    JsonAgentModelPolicyStore(path.parent)._atomic_write(path, marker)


def _write_policy_store_bytes(path: Path, marker: str) -> None:
    JsonAgentModelPolicyStore(path.parent)._atomic_write_bytes(path, f"{marker}\n".encode())


def _write_state_v3(path: Path, marker: str) -> None:
    _state_v3_atomic_write_json(path, {"marker": marker})


def _write_core_primitive(path: Path, marker: str) -> None:
    # Default-configured call (preserve_mode=False, newline="" LF-forced) — the ONE
    # combination this shared battery characterizes. The full preserve-mode x
    # content-kind x failure-point parameter matrix (v0.4.5 FR2/T-045-12) is the
    # dedicated subject of tests/unit/core/test_atomic_write.py; this entry exists only
    # so the primitive's own def does not silently escape this census (T-044-45's
    # documented purpose), now that core/atomic_write.py is the eleven writers'
    # eventual replacement (T-045-13/14 switch the call sites; none moved here — EXPAND
    # only, D7).
    _core_atomic_write(path, f"{marker}\n")


# The 10 atomic-writer primitives in the package: every ``def`` (module- or class-level)
# whose name contains "atomic" as a whole snake_case token — see
# ``_atomic_writer_def_names`` below, which is this same criterion made executable
# (T-044-45 F-4: the original grep-by-hand census missed ``state_v3``'s writer because
# it had no named helper at all; giving it one, matching the package's own naming idiom,
# both fixes the writer AND makes it fall out of this same criterion automatically).
# Behaviour verified empirically before being pinned here, never assumed from reading the
# source (dd-bug-fix phase 4's discipline, applied to characterizing existing behaviour
# rather than a production hypothesis).
_ATOMIC_WRITER_CASES: list[AtomicWriterCase] = [
    AtomicWriterCase(
        id="frontmatter_keys.write_text_atomic",
        write=_write_frontmatter_keys,
        replace_target="dadaia_workspace.features.migrate.frontmatter_keys.os.replace",
        preserves_mode=True,
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=True,  # os.fdopen(..., newline="")
    ),
    AtomicWriterCase(
        id="doctor_structural._write_text_atomic",
        write=_write_doctor_structural,
        replace_target="dadaia_workspace.features.specs.doctor_structural.os.replace",
        preserves_mode=True,
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=True,  # os.fdopen(..., newline="")
    ),
    AtomicWriterCase(
        id="hooks._common.atomic_write_text",
        write=_write_hooks_common,
        replace_target="dadaia_workspace.hooks._common.os.replace",
        preserves_mode=False,
        # T-045-13: now a thin shim delegating to core.atomic_write.atomic_write (AR-1),
        # whose temp cleanup is unconditional on every failure path (T-045-12 condition
        # 5). Fixes bug `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`
        # by construction, not by a patch at this call site — this test is the regression
        # evidence for THIS writer; public_assets_common._atomic_write_text carries the
        # same fix in the next commit (T-045-13 infrastructure family).
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=False,  # newline=None — platform-default translation preserved
    ),
    AtomicWriterCase(
        id="public_assets_common._atomic_write_text",
        write=_write_public_assets_common,
        replace_target="dadaia_workspace.core.atomic_write.os.replace",  # T-045-13: delegates
        preserves_mode=False,
        # T-045-13: same delegation and same fix as hooks._common.atomic_write_text
        # (previous commit) — this was the second and last of the 2 leaking writers;
        # bug two-atomic-writers-leak-temp-file-on-injected-os-replace-failure is now
        # fully closed by construction across the battery.
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=True,  # newline="" (this primitive's default) — LF-preserving
    ),
    AtomicWriterCase(
        id="session_identity._atomic_write_text",
        write=_write_session_identity,
        replace_target="dadaia_workspace.features.spec_context.session_identity.os.replace",
        preserves_mode=False,
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=False,  # Path.write_text(...) with no newline= override
    ),
    AtomicWriterCase(
        id="presence._atomic_write_json",
        write=_write_presence_json,
        replace_target="dadaia_workspace.features.spec_context.presence.os.replace",
        preserves_mode=False,
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=False,  # Path.write_text(json.dumps(...)) with no newline=
    ),
    AtomicWriterCase(
        id="json_agent_model_policy_store._atomic_write",
        write=_write_policy_store_text,
        replace_target="dadaia_workspace.core.atomic_write.os.replace",  # T-045-13: delegates
        preserves_mode=False,
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=True,  # os.fdopen(fd, "wb") — binary mode, no translation
    ),
    AtomicWriterCase(
        id="json_agent_model_policy_store._atomic_write_bytes",
        write=_write_policy_store_bytes,
        replace_target="dadaia_workspace.core.atomic_write.os.replace",  # T-045-13: delegates
        preserves_mode=False,
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=True,  # os.fdopen(fd, "wb") — binary mode, no translation
    ),
    AtomicWriterCase(
        id="state_v3._atomic_write_json",
        write=_write_state_v3,
        replace_target="dadaia_workspace.features.migrate.state_v3.os.replace",
        preserves_mode=False,
        cleans_up_on_failure=True,
        lf_bytes_guaranteed=False,  # Path.write_text(json.dumps(...)) with no newline=
    ),
    AtomicWriterCase(
        id="core.atomic_write.atomic_write",
        write=_write_core_primitive,
        replace_target="dadaia_workspace.core.atomic_write.os.replace",
        preserves_mode=False,  # default preserve_mode=False at this call site
        cleans_up_on_failure=True,  # unconditional, by design (AR-1 condition 5)
        lf_bytes_guaranteed=True,  # default newline="" — LF-preserving on every platform
    ),
]


@pytest.mark.parametrize("case", _ATOMIC_WRITER_CASES, ids=[c.id for c in _ATOMIC_WRITER_CASES])
def test_atomic_writer_rebinds_a_hardlinked_target(case: AtomicWriterCase, tmp_path: Path) -> None:
    """A hard link is not a symlink, so refusing links alone cannot keep a write inside
    the tree (CWE-59/CWE-367 TOCTOU): every writer must rebind the target NAME to a new
    inode via tmp-file + ``os.replace`` rather than write through whatever it points at."""
    outside = tmp_path / "outside.md"
    original = "original outside content\n"
    outside.write_text(original, encoding="utf-8")
    target = tmp_path / "linked.md"
    os.link(outside, target)
    before_ino = target.stat().st_ino

    case.write(target, "REBOUND")

    assert outside.read_text(encoding="utf-8") == original, (
        f"{case.id} wrote through a hard link into a file outside the write target"
    )
    assert target.stat().st_ino != before_ino, f"{case.id} did not rebind the name to a new inode"
    assert "REBOUND" in target.read_text(encoding="utf-8")


@pytest.mark.parametrize("case", _ATOMIC_WRITER_CASES, ids=[c.id for c in _ATOMIC_WRITER_CASES])
def test_atomic_writer_never_leaves_crlf_bytes(case: AtomicWriterCase, tmp_path: Path) -> None:
    """The bytes landing on disk never carry CRLF — universal-newline translation must be
    disabled (``newline=""``) or bypassed (binary mode) at every write site, the same
    byte-preserving guarantee ``test_repair_preserves_file_mode_and_newlines`` pins for
    the doctor's repair path.

    Platform-aware by construction (companion bug T-044-36 is about a fixture asserting
    this for the wrong reason — this dimension avoids that trap directly): 3 of the 8
    writers pass no ``newline=""`` and are not byte-exact on Windows, where Python's text
    mode rewrites LF to CRLF. That is a real, harmless divergence for those 3 (internal
    `.dadaia/` runtime state, never git-diffed) — this test skips rather than asserting a
    false platform-independent claim for them."""
    if not case.lf_bytes_guaranteed and sys.platform.startswith("win"):
        pytest.skip(
            f'{case.id} has no newline=""/binary-mode guarantee; Windows text-mode '
            "CRLF translation is a known, harmless gap for this internal-state writer."
        )
    target = tmp_path / "atom.md"

    case.write(target, "line-one")

    assert b"\r\n" not in target.read_bytes(), f"{case.id} wrote CRLF bytes"


@pytest.mark.parametrize("case", _ATOMIC_WRITER_CASES, ids=[c.id for c in _ATOMIC_WRITER_CASES])
def test_atomic_writer_mode_preservation_matches_its_contract(
    case: AtomicWriterCase, tmp_path: Path
) -> None:
    """Pin each writer's REAL mode-preservation contract against the mode actually on
    disk, never a hard-coded POSIX value — mirrors
    ``test_repair_preserves_file_mode_and_newlines``'s before/after comparison, which is
    exactly right on every platform (Windows has no POSIX mode bits: ``os.chmod`` only
    toggles the read-only attribute there, so every file reads back the same value
    regardless of ``shutil.copymode``, and a before==after comparison still states
    precisely what it means)."""
    target = tmp_path / "atom.md"
    target.write_text("orig\n", encoding="utf-8")
    # Deliberately NOT 0o600 (mkstemp's own creation mode) — 0o640 makes the two
    # non-preserving json_agent_model_policy_store writers fail this dimension for the
    # real reason instead of coincidentally matching mkstemp's default.
    os.chmod(target, 0o640)
    before = stat.S_IMODE(target.stat().st_mode)

    case.write(target, "new")

    after = stat.S_IMODE(target.stat().st_mode)
    if case.preserves_mode:
        assert after == before, f"{case.id} was expected to preserve the target's mode"
        return
    if sys.platform.startswith("win"):
        pytest.skip(
            "os.chmod only toggles the read-only attribute on Windows — every file "
            "reads back the same mode regardless of copymode, so non-preservation "
            "cannot be observed on this platform."
        )
    # Documented, not a bug: only the 2 writers with an explicit shutil.copymode call
    # (frontmatter_keys / doctor_structural — the git-tracked memory-atom writers)
    # preserve mode. The other 6 write internal `.dadaia/` runtime state that is
    # always created fresh, so no CWE-732 mode-narrowing concern applies to them.
    assert after != before, (
        f"{case.id} was expected NOT to preserve mode (documented); it did — if this "
        "is now intentional, flip preserves_mode=True above."
    )


@pytest.mark.parametrize("case", _ATOMIC_WRITER_CASES, ids=[c.id for c in _ATOMIC_WRITER_CASES])
def test_atomic_writer_temp_file_on_injected_replace_failure(
    case: AtomicWriterCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``os.replace`` itself fails, the temp file must not survive — a leaked
    ``.tmp`` sibling next to a real atom/state file is exactly the drift class this
    guard exists to catch. As of T-045-13 every named writer in this battery cleans up
    (the former 2-writer gap, bug
    `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`, closed by
    delegating those 2 call sites onto ``core.atomic_write.atomic_write``, whose cleanup
    is unconditional). The ``else`` branch below stays live for any future writer that
    reintroduces the gap."""
    target = tmp_path / "atom.md"
    target.write_text("orig\n", encoding="utf-8")
    before = set(tmp_path.iterdir())

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected os.replace failure")

    monkeypatch.setattr(case.replace_target, _boom)

    with pytest.raises(OSError, match="injected os.replace failure"):
        case.write(target, "new")

    leftover = set(tmp_path.iterdir()) - before
    if case.cleans_up_on_failure:
        assert leftover == set(), (
            f"{case.id} leaked a temp file on injected os.replace failure: {leftover}"
        )
    else:
        assert leftover, (
            f"{case.id} was expected to leak (documented gap, bug "
            "`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`); if this "
            "now passes, the bug is fixed — flip cleans_up_on_failure=True above and "
            "close it with this test as the regression evidence."
        )


_DEF_LINE = re.compile(r"^[ \t]*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)


def _atomic_writer_def_names(package_root: Path) -> set[str]:
    """The census, made executable (T-044-45 F-4).

    Every ``def`` (module- or class-level — indentation is not part of the match, so a
    method like ``JsonAgentModelPolicyStore._atomic_write`` is found the same way a
    module-level function is) whose name contains ``atomic`` as a whole snake_case
    token. "Whole token" is the load-bearing part: it is what tells
    ``check_memory_atomicity`` (token ``atomicity``) apart from an actual atomic writer
    — a plain substring grep (``*atomic*``) would wrongly pull that doctor check in.
    """
    hits: set[str] = set()
    for path in sorted(package_root.rglob("*.py")):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in _DEF_LINE.finditer(text):
            name = match.group(1)
            if "atomic" in name.strip("_").split("_"):
                line_no = text.count("\n", 0, match.start()) + 1
                hits.add(f"{path.relative_to(package_root)}:{line_no}:{name}")
    return hits


def test_census_covers_every_atomic_writer_def_in_the_package() -> None:
    """Self-enforcing census: the NEXT atomic-writer def added anywhere in the package
    must either join ``_ATOMIC_WRITER_CASES`` or this test fails loudly — the exact
    silent-escape state_v3's writer pulled off against the hand-maintained 8-writer
    census (T-044-45 F-4)."""
    discovered = _atomic_writer_def_names(_REPO_ROOT / "dadaia_workspace")

    assert len(discovered) == len(_ATOMIC_WRITER_CASES), (
        "atomic-writer def census drifted from the behavioural battery: found "
        f"{len(discovered)} def(s) whose name contains the 'atomic' token, but "
        f"{len(_ATOMIC_WRITER_CASES)} case(s) are pinned above — add the missing "
        f"writer(s) to _ATOMIC_WRITER_CASES: {sorted(discovered)}"
    )
