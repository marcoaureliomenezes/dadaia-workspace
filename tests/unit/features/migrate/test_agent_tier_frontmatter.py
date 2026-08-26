"""v0.1.72 FR1 — ``agent-tier-frontmatter`` migration (bug
``memory-agent-tier-migration-deadlock``, CRITICAL).

``agent_tier`` was schema-dropped in v0.1.61 (``additionalProperties: false``) with NO
migration: consumer workspaces scaffolded earlier carry atoms with ``agent_tier:`` in
frontmatter, ``specs doctor`` correctly rejects them, memory writes are phase-locked
outside DEFINITION/CLOSURE, and neither ``doctor --fix`` nor ``specs upgrade`` repaired
the key — a governance deadlock that blocked the consumer's release preflight entirely.

The migration is the legal repair path (CLI-owned, any phase): strip the top-level
``agent_tier`` key from every ``specs/memory/**/*.md`` frontmatter block, byte-preserving
everything else. Fixture = a REAL sample-consumer atom pulled from the reporting remote
(real-consumer-artifact law).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.agent_tier_frontmatter import (
    migrate_agent_tier_frontmatter,
)
from dadaia_workspace.features.migrate.registry import REGISTRY, latest_version

_REAL_ATOM = Path(__file__).parents[3] / "fixtures" / "memory-agent-tier" / "s3-delivery.md"


def _specs(tmp_path: Path, *atoms: tuple[str, str]) -> Path:
    specs = tmp_path / "specs"
    memory = specs / "memory"
    (memory / "product").mkdir(parents=True)
    for rel, body in atoms:
        target = memory / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return specs


def test_strips_agent_tier_from_real_consumer_atom(tmp_path: Path) -> None:
    """The REAL sample-consumer atom: ``agent_tier: self-pull`` is removed; every other
    byte of frontmatter and body is preserved."""
    original = _REAL_ATOM.read_text(encoding="utf-8")
    assert "agent_tier:" in original  # fixture sanity
    specs = _specs(tmp_path, ("product/s3-delivery.md", original))

    result = migrate_agent_tier_frontmatter(specs, dry_run=False)

    migrated = (specs / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8")
    assert "agent_tier" not in migrated
    # Byte-preservation: removing exactly the agent_tier line reproduces the original.
    expected = "\n".join(
        line for line in original.splitlines() if not line.startswith("agent_tier:")
    )
    if original.endswith("\n"):
        expected += "\n"
    assert migrated == expected
    assert len(result.moved) == 1


def test_unterminated_frontmatter_completes_linearly(tmp_path: Path) -> None:
    """v0.1.73 FR4 (bug ``migrate-agent-tier-frontmatter-redos-on-unterminated-block``,
    security review of v0.1.72): a malformed atom — opening ``---`` fence + a long
    blank-line run + NO closing fence — must complete in linear time. The DOTALL
    ``.*?`` frontmatter regex backtracked super-linearly (~34s at 50k newlines)."""
    import time

    malformed = "---\n" + "\n" * 50_000  # no closing fence
    specs = _specs(tmp_path, ("malformed.md", malformed))

    start = time.monotonic()
    result = migrate_agent_tier_frontmatter(specs, dry_run=False)
    elapsed = time.monotonic() - start

    assert elapsed < 2.0, f"frontmatter scan took {elapsed:.1f}s — super-linear backtracking"
    assert result.moved == []  # malformed file untouched
    assert (specs / "memory" / "malformed.md").read_text(encoding="utf-8") == malformed


def test_dry_run_idempotent_no_frontmatter_missing_dir_and_registered(tmp_path: Path) -> None:
    real_body = _REAL_ATOM.read_text(encoding="utf-8")

    # dry-run plans but writes nothing.
    dry_specs = _specs(tmp_path / "dry", ("product/s3-delivery.md", real_body))
    dry_result = migrate_agent_tier_frontmatter(dry_specs, dry_run=True)
    assert (dry_specs / "memory" / "product" / "s3-delivery.md").read_text(
        encoding="utf-8"
    ) == real_body
    assert dry_result.dry_run is True
    assert len(dry_result.moved) == 1  # planned

    # second run is idempotent (no-op).
    idem_specs = _specs(tmp_path / "idem", ("product/s3-delivery.md", real_body))
    migrate_agent_tier_frontmatter(idem_specs, dry_run=False)
    after_first = (idem_specs / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8")
    second = migrate_agent_tier_frontmatter(idem_specs, dry_run=False)
    assert (idem_specs / "memory" / "product" / "s3-delivery.md").read_text(
        encoding="utf-8"
    ) == after_first
    assert second.moved == []

    # a file with no frontmatter at all is skipped, untouched.
    no_fm_body = "> AGENTS doc, no frontmatter.\n\nagent_tier mentioned in prose only.\n"
    no_fm_specs = _specs(tmp_path / "no-fm", ("AGENTS.md", no_fm_body))
    no_fm_result = migrate_agent_tier_frontmatter(no_fm_specs, dry_run=False)
    assert (no_fm_specs / "memory" / "AGENTS.md").read_text(encoding="utf-8") == no_fm_body
    assert no_fm_result.moved == []

    # a missing memory/ dir degrades gracefully.
    empty_specs = tmp_path / "empty" / "specs"
    empty_specs.mkdir(parents=True)
    empty_result = migrate_agent_tier_frontmatter(empty_specs, dry_run=False)
    assert empty_result.moved == []
    assert empty_result.skipped  # notes nothing-to-migrate

    # the step is registered in the chain 2→3 so `specs upgrade` walks consumers to it.
    step = next((s for s in REGISTRY if s.key == "agent-tier-frontmatter"), None)
    assert step is not None, "agent-tier-frontmatter step not registered"
    assert (step.from_version, step.to_version) == (2, 3)
    assert latest_version() >= 3  # v0.1.73 added bugs-single-file (3→4)


def _deny_access_to(monkeypatch: pytest.MonkeyPatch, atom: Path) -> None:
    """Pin the read-only decision at the ``os.access`` seam — never a real chmod, which
    cannot distinguish "denied" from "root bypasses it" (the bug's own point)."""
    real_access = os.access

    def fake_access(path: object, mode: int, **kwargs: object) -> bool:
        if Path(str(path)) == atom:
            return False
        return real_access(path, mode, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "dadaia_workspace.features.migrate.agent_tier_frontmatter.os.access", fake_access
    )


def test_read_only_atom_needing_no_change_stays_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Intent: CONTRACT (bug read-only-atom-honouring-is-advisory-and-root-bypasses-it).
    Size: SMALL.

    DECIDED (T-044-39): the read-only check runs AFTER the no-change determination, so a
    read-only atom that needs no rewrite produces no note at all — matching every other
    no-op atom instead of the noise it used to emit because the check preceded the read.
    """
    body = "---\nslug: a\n---\nbody text, no agent_tier key.\n"
    specs = _specs(tmp_path, ("a.md", body))
    atom = specs / "memory" / "a.md"
    _deny_access_to(monkeypatch, atom)

    result = migrate_agent_tier_frontmatter(specs, dry_run=False)

    assert result.moved == []
    # No PER-ATOM note — the tree-level "nothing to migrate" summary is the only entry,
    # the same summary every completely no-op run produces.
    assert result.skipped == ["no memory atom carries agent_tier — nothing to migrate."]
    assert atom.read_text(encoding="utf-8") == body


def test_read_only_atom_needing_change_is_skipped_with_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Companion pin: a read-only atom that DOES carry ``agent_tier`` still produces the
    documented refusal note and is left untouched — the guard stays best-effort (it
    cannot close the root-bypass case, per the bug's own notes) but honours the common
    case instead of staying silent about a change it is refusing to make."""
    body = "---\nslug: a\nagent_tier: self-pull\n---\nbody text.\n"
    specs = _specs(tmp_path, ("a.md", body))
    atom = specs / "memory" / "a.md"
    _deny_access_to(monkeypatch, atom)

    result = migrate_agent_tier_frontmatter(specs, dry_run=False)

    assert result.moved == []
    assert result.skipped == [
        "a.md: read-only — skipped.",
        "no memory atom carries agent_tier — nothing to migrate.",
    ]
    assert atom.read_text(encoding="utf-8") == body  # untouched
