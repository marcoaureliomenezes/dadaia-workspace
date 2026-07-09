"""v0.1.72 FR1 — ``agent-tier-frontmatter`` migration (bug
``memory-agent-tier-migration-deadlock``, CRITICAL).

``agent_tier`` was schema-dropped in v0.1.61 (``additionalProperties: false``) with NO
migration: consumer workspaces scaffolded earlier carry atoms with ``agent_tier:`` in
frontmatter, ``specs doctor`` correctly rejects them, memory writes are phase-locked
outside DEFINITION/CLOSURE, and neither ``doctor --fix`` nor ``specs upgrade`` repaired
the key — a governance deadlock that blocked the consumer's release preflight entirely.

The migration is the legal repair path (CLI-owned, any phase): strip the top-level
``agent_tier`` key from every ``specs/memory/**/*.md`` frontmatter block, byte-preserving
everything else. Fixture = a REAL dd-chain-capture atom pulled from the reporting remote
(real-consumer-artifact law).
"""

from __future__ import annotations

from pathlib import Path

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
    """The REAL dd-chain-capture atom: ``agent_tier: self-pull`` is removed; every other
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


def test_dry_run_plans_but_writes_nothing(tmp_path: Path) -> None:
    original = _REAL_ATOM.read_text(encoding="utf-8")
    specs = _specs(tmp_path, ("product/s3-delivery.md", original))

    result = migrate_agent_tier_frontmatter(specs, dry_run=True)

    assert (specs / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8") == original
    assert result.dry_run is True
    assert len(result.moved) == 1  # planned


def test_idempotent_second_run_is_noop(tmp_path: Path) -> None:
    specs = _specs(tmp_path, ("product/s3-delivery.md", _REAL_ATOM.read_text(encoding="utf-8")))
    migrate_agent_tier_frontmatter(specs, dry_run=False)
    after_first = (specs / "memory" / "product" / "s3-delivery.md").read_text(encoding="utf-8")

    result = migrate_agent_tier_frontmatter(specs, dry_run=False)

    assert (specs / "memory" / "product" / "s3-delivery.md").read_text(
        encoding="utf-8"
    ) == after_first
    assert result.moved == []


def test_agent_tier_only_in_frontmatter_is_touched_not_body(tmp_path: Path) -> None:
    """A body line mentioning ``agent_tier:`` (prose/docs) is NEVER touched — only the
    frontmatter block's top-level key is stripped."""
    body = (
        "---\n"
        "slug: doc-mention\n"
        "title: Doc\n"
        "agent_tier: self-pull\n"
        "---\n"
        "\n"
        "Frontmatter carries `name`, `agent_tier`, `token_estimate` historically.\n"
        "agent_tier: this-is-prose-not-frontmatter\n"
    )
    specs = _specs(tmp_path, ("doc-mention.md", body))

    migrate_agent_tier_frontmatter(specs, dry_run=False)

    migrated = (specs / "memory" / "doc-mention.md").read_text(encoding="utf-8")
    assert "agent_tier: self-pull" not in migrated
    assert "agent_tier: this-is-prose-not-frontmatter" in migrated
    assert "`agent_tier`" in migrated  # prose untouched


def test_file_without_frontmatter_is_skipped(tmp_path: Path) -> None:
    body = "> AGENTS doc, no frontmatter.\n\nagent_tier mentioned in prose only.\n"
    specs = _specs(tmp_path, ("AGENTS.md", body))

    result = migrate_agent_tier_frontmatter(specs, dry_run=False)

    assert (specs / "memory" / "AGENTS.md").read_text(encoding="utf-8") == body
    assert result.moved == []


def test_missing_memory_dir_is_graceful(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    result = migrate_agent_tier_frontmatter(specs, dry_run=False)
    assert result.moved == []
    assert result.skipped  # notes nothing-to-migrate


def test_registered_in_chain_v2_to_v3() -> None:
    """The step must be registered 2→3 so ``specs upgrade`` walks consumers to it."""
    step = next((s for s in REGISTRY if s.key == "agent-tier-frontmatter"), None)
    assert step is not None, "agent-tier-frontmatter step not registered"
    assert (step.from_version, step.to_version) == (2, 3)
    assert latest_version() >= 3  # v0.1.73 added bugs-single-file (3→4)


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
