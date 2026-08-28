"""Bug ``specs-upgrade-emits-atoms-violating-frontmatter-schema`` (HIGH) — the canonical
upgrade chain must leave every memory atom valid against ``memory-frontmatter-v1``.

Intent: CONTRACT (bug specs-upgrade-emits-atoms-violating-frontmatter-schema). Size: SMALL.

``memory-frontmatter-v1`` is closed (``additionalProperties: false``) and the migrate
feature exists precisely because *a schema-drop MUST ship its migration*
(``agent_tier_frontmatter`` docstring, v0.1.72 FR1). ``token_estimate`` was dropped from
that schema with no migration, so ``dadaia specs upgrade`` rewrote consumer atoms, then
failed its own post-upgrade doctor with LINT-1 ``Additional properties are not allowed
('token_estimate' was unexpected)`` and told the operator to restore from backup —
reproduced on two independent consumer trees, plus a third from a preserved backup.

Fixture = the REAL sample-consumer atom already vetted into this repo, which carries both
retired keys (``agent_tier: self-pull`` and ``token_estimate: 650``) exactly as consumer
trees in the field do (real-consumer-artifact law).

The assertion is schema-driven on purpose: it fails for ANY retired key the chain forgets
to strip, so the next schema-drop cannot silently reopen this bug.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml

from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.features.migrate.registry import REGISTRY, latest_version, run_chain
from dadaia_workspace.features.migrate.retired_frontmatter_keys import (
    migrate_retired_frontmatter_keys,
)
from dadaia_workspace.features.specs.memory_lint import load_frontmatter_schema

_REAL_ATOM = Path(__file__).parents[3] / "fixtures" / "memory-agent-tier" / "s3-delivery.md"


def _frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    assert lines[0].strip() == "---", "atom has no leading frontmatter fence"
    close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    loaded = yaml.safe_load("\n".join(lines[1:close]))
    assert isinstance(loaded, dict)
    return loaded


def _tree_with_real_atom(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "memory" / "product" / "s3-delivery.md").write_text(
        _REAL_ATOM.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return specs


def test_canonical_chain_leaves_real_atom_schema_valid(tmp_path: Path) -> None:
    """Walking an unstamped tree to the canonical version must produce atoms the shipped
    schema accepts — the exact post-upgrade check ``specs upgrade`` runs itself."""
    original = _REAL_ATOM.read_text(encoding="utf-8")
    assert "agent_tier:" in original and "token_estimate:" in original  # fixture sanity

    specs = _tree_with_real_atom(tmp_path)
    run_chain(specs, 0, CANONICAL_SPECS_VERSION)

    migrated = (specs / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8")
    jsonschema.validate(instance=_frontmatter(migrated), schema=load_frontmatter_schema())


def test_chain_reaches_the_registered_latest_version() -> None:
    """The canonical version must be reachable — a step added without bumping the
    constant (or the reverse) leaves consumer trees unable to converge."""
    assert latest_version() == CANONICAL_SPECS_VERSION


def test_strips_only_retired_keys_and_preserves_every_other_byte(tmp_path: Path) -> None:
    """Byte-preservation: removing exactly the retired key lines reproduces the original."""
    original = _REAL_ATOM.read_text(encoding="utf-8")
    specs = _tree_with_real_atom(tmp_path)

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    migrated = (specs / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8")
    retired = ("agent_tier:", "token_estimate:")
    expected = "\n".join(line for line in original.splitlines() if not line.startswith(retired))
    if original.endswith("\n"):
        expected += "\n"
    assert migrated == expected
    assert len(result.moved) == 1


def test_dry_run_idempotent_and_degrades_gracefully(tmp_path: Path) -> None:
    """dry-run plans without writing, a second run is a no-op, and a tree with no
    memory/ directory is reported rather than crashed on."""
    body = _REAL_ATOM.read_text(encoding="utf-8")

    dry = _tree_with_real_atom(tmp_path / "dry")
    dry_result = migrate_retired_frontmatter_keys(dry, dry_run=True)
    assert (dry / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8") == body
    assert dry_result.dry_run is True and len(dry_result.moved) == 1

    idem = _tree_with_real_atom(tmp_path / "idem")
    migrate_retired_frontmatter_keys(idem, dry_run=False)
    after_first = (idem / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8")
    second = migrate_retired_frontmatter_keys(idem, dry_run=False)
    assert (idem / "memory" / "product" / "s3-delivery.md").read_text(
        encoding="utf-8"
    ) == after_first
    assert second.moved == []
    assert second.skipped  # notes nothing-to-migrate

    empty = tmp_path / "empty" / "specs"
    empty.mkdir(parents=True)
    empty_result = migrate_retired_frontmatter_keys(empty, dry_run=False)
    assert empty_result.moved == [] and empty_result.skipped


def test_registered_after_the_agent_tier_step(tmp_path: Path) -> None:
    """Wiring: the step closes the chain at 4→5 so trees already past the agent_tier
    step are repaired too — the case that made this bug reachable in the field."""
    step = next((s for s in REGISTRY if s.key == "retired-frontmatter-keys"), None)
    assert step is not None, "retired-frontmatter-keys step not registered"
    assert (step.from_version, step.to_version) == (4, 5)

    specs = _tree_with_real_atom(tmp_path)
    run_chain(specs, 4, CANONICAL_SPECS_VERSION)  # a tree ALREADY at the old canonical
    migrated = (specs / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8")
    jsonschema.validate(instance=_frontmatter(migrated), schema=load_frontmatter_schema())


def _tree_with_atom(tmp_path: Path, body: str) -> tuple[Path, Path]:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    atom = specs / "memory" / "a.md"
    atom.write_text(body, encoding="utf-8")
    return specs, atom


def _deny_access_to(monkeypatch: pytest.MonkeyPatch, atom: Path) -> None:
    """Pin the read-only decision at the ``os.access`` seam — never a real chmod, which
    cannot distinguish "denied" from "root bypasses it" (the bug's own point)."""
    real_access = os.access

    def fake_access(path: object, mode: int, **kwargs: object) -> bool:
        if Path(str(path)) == atom:
            return False
        return real_access(path, mode, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "dadaia_workspace.features.migrate.retired_frontmatter_keys.os.access", fake_access
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
    body = "---\nslug: a\n---\nbody text, no retired key.\n"
    specs, atom = _tree_with_atom(tmp_path, body)
    _deny_access_to(monkeypatch, atom)

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert result.moved == []
    # No PER-ATOM note — the tree-level "nothing to do" summary is the only entry, the
    # same summary every completely no-op run produces (test_dry_run_idempotent_...).
    assert result.skipped == ["no memory atom carries a retired frontmatter key — nothing to do."]
    assert atom.read_text(encoding="utf-8") == body


def test_read_only_atom_needing_change_is_skipped_with_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Companion pin: a read-only atom that DOES need a rewrite still produces the
    documented refusal note and is left untouched — the guard stays best-effort (it
    cannot close the root-bypass case, per the bug's own notes) but honours the common
    case instead of staying silent about a change it is refusing to make."""
    body = "---\nslug: a\ntoken_estimate: 650\n---\nbody text.\n"
    specs, atom = _tree_with_atom(tmp_path, body)
    _deny_access_to(monkeypatch, atom)

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert result.moved == []
    assert result.skipped == [
        "a.md: read-only — skipped.",
        "no memory atom carries a retired frontmatter key — nothing to do.",
    ]
    assert atom.read_text(encoding="utf-8") == body  # untouched
