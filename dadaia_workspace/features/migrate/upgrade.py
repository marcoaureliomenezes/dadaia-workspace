"""``dadaia specs upgrade`` orchestration (FR-S04 / FR-S05; simplified v0.5.1 T-051-16).

Sequence (v0.5.1 K10): resolve the current pattern version, then apply the registry's
one surviving rule (:func:`~dadaia_workspace.features.migrate.registry.check_upgradable`)
-- ``current < goal`` raises :class:`~dadaia_workspace.features.migrate.registry.UpgradeRefused`
without touching the filesystem; ``current >= goal`` is a no-op except for the
unconditional template-artifact repair (bug
scaffold-repair-cannot-remediate-invalid-placeholder-atom), which runs regardless of
version since it is unrelated to the retired migration chain.

No backup is taken on either path: refusal never writes, and the no-op path's only
possible write (placeholder removal) was never backed up before this simplification
either.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core import specs_version as _version
from dadaia_workspace.core.spec_status import APPROVED, DRAFT, IN_REVIEW
from dadaia_workspace.core.specs_repair import remove_placeholder_atoms
from dadaia_workspace.features.migrate import registry as _registry


@dataclass
class UpgradeResult:
    """Outcome of an upgrade run."""

    from_version: int
    to_version: int
    dry_run: bool
    no_op: bool = False
    #: Placeholder atoms removed by the unconditional template-artifact repair
    #: (planned-only when ``dry_run``).
    placeholder_removed: list[Path] = field(default_factory=list)
    #: Live-release trio documents whose retired Portuguese status token was rewritten
    #: to the English vocabulary (planned-only when ``dry_run``).
    status_rewritten: list[Path] = field(default_factory=list)


def upgrade(
    specs_dir: Path,
    *,
    target: int | None = None,
    dry_run: bool = False,
) -> UpgradeResult:
    """Upgrade ``specs/`` from its stamped version to ``target`` (default: canonical).

    Raises :class:`~dadaia_workspace.features.migrate.registry.UpgradeRefused` when
    the tree sits below ``target`` — see that exception's message for the fix.
    """
    current = _version.read_pattern_version(specs_dir)
    goal = _version.CANONICAL_SPECS_VERSION if target is None else target

    _registry.check_upgradable(current, goal)

    if dry_run:
        removed = remove_placeholder_atoms(specs_dir, dry_run=True) + plan_empty_ideas_dir(
            specs_dir
        )
        restated = plan_status_token_rewrites(specs_dir)
    else:
        removed = remove_placeholder_atoms(specs_dir) + remove_empty_ideas_dir(specs_dir)
        restated = rewrite_status_tokens(specs_dir)
    return UpgradeResult(
        from_version=current,
        to_version=goal,
        dry_run=dry_run,
        no_op=not (removed or restated),
        placeholder_removed=removed,
        status_rewritten=restated,
    )


def plan_empty_ideas_dir(specs_dir: Path) -> list[Path]:
    """``specs/releases/_ideas/`` left the canon (0.4.7 c5, ADR 0019): a live tree whose
    ``_ideas/`` holds nothing but the scaffolded ``AGENTS.md`` is repaired losslessly."""
    ideas = specs_dir / "releases" / "_ideas"
    if not ideas.is_dir():
        return []
    entries = [p.name for p in ideas.iterdir()]
    return [ideas] if entries in ([], ["AGENTS.md"]) else []


def remove_empty_ideas_dir(specs_dir: Path) -> list[Path]:
    planned = plan_empty_ideas_dir(specs_dir)
    for ideas in planned:
        for child in ideas.iterdir():
            child.unlink()
        ideas.rmdir()
    return planned


#: The retired Portuguese status tokens mapped onto the one English vocabulary
#: (``core.spec_status``). A tree is migrated ONCE, here — nothing downstream
#: keeps a compatibility spelling, so the doctor keeps exactly one rule.
_RETIRED_STATUS_TOKENS = {
    "Aprovado": APPROVED,
    "Em revisão": IN_REVIEW,
    "Em revisao": IN_REVIEW,
    "Rascunho": DRAFT,
}
_TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")


def _live_trio_documents(specs_dir: Path) -> list[Path]:
    """Every trio document of every LIVE release — release root and its ``rc-N/``
    archives. ``releases/_archive/`` is published history: excluded by path, never by
    token, so an archived tree keeps reading as it shipped."""
    releases = specs_dir / "releases"
    return sorted(
        path
        for path in releases.glob("*/**/*.md")
        if path.name in _TRIO and "_archive" not in path.relative_to(releases).parts
    )


def plan_status_token_rewrites(specs_dir: Path) -> list[Path]:
    """Live trio documents still declaring a retired Portuguese status token."""
    planned: list[Path] = []
    for path in _live_trio_documents(specs_dir):
        text = path.read_text(encoding="utf-8")
        if _rewrite_status_line(text) != text:
            planned.append(path)
    return planned


def rewrite_status_tokens(specs_dir: Path) -> list[Path]:
    """Rewrite the planned set in place, returning what was rewritten."""
    rewritten = plan_status_token_rewrites(specs_dir)
    for path in rewritten:
        text = path.read_text(encoding="utf-8")
        path.write_text(_rewrite_status_line(text), encoding="utf-8")
    return rewritten


def _rewrite_status_line(text: str) -> str:
    """Translate the document's ``**Status:**`` declaration, and nothing else."""
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if "**Status:**" not in line:
            continue
        for retired, english in _RETIRED_STATUS_TOKENS.items():
            if retired in line:
                lines[index] = line.replace(retired, english)
                break
    return "".join(lines)
