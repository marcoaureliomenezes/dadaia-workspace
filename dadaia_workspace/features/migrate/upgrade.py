"""``dadaia specs upgrade`` orchestration (FR-S04 / FR-S05; simplified v0.5.1 T-051-16).

Sequence (v0.5.1 K10): resolve the current pattern version, then apply the registry's
one surviving rule (:func:`~dadaia_workspace.features.migrate.registry.check_upgradable`)
-- a tree below the one live hop raises
:class:`~dadaia_workspace.features.migrate.registry.UpgradeRefused` without touching the
filesystem; a tree at 6 walks the 6 -> 7 hop (:func:`fold_tech_stack`) and is re-stamped;
a tree already at canonical is a no-op except for the
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
from dadaia_workspace.core.fixed_sections import (
    FIXED_SECTIONS,
    extract_fixed_section,
    render_fixed_section,
)
from dadaia_workspace.core.frontmatter import FRONTMATTER_RE
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
    #: ``memory/TECHSTACK.md`` folded into ``ARCHITECTURE.md``'s ``## Tech Stack``
    #: section and deleted by the 6 -> 7 hop (planned-only when ``dry_run``).
    tech_stack_folded: list[Path] = field(default_factory=list)
    #: Files whose fixed law section was inserted or refreshed from the library
    #: fragment (planned-only when ``dry_run``).
    fixed_restored: list[Path] = field(default_factory=list)


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
        folded = plan_tech_stack_fold(specs_dir)
        fixed = plan_fixed_sections(specs_dir)
    else:
        removed = remove_placeholder_atoms(specs_dir) + remove_empty_ideas_dir(specs_dir)
        restated = rewrite_status_tokens(specs_dir)
        folded = fold_tech_stack(specs_dir)
        fixed = restore_fixed_sections(specs_dir)
        if current < goal:
            _version.write_pattern_version(specs_dir, goal)
    return UpgradeResult(
        from_version=current,
        to_version=goal,
        dry_run=dry_run,
        no_op=current >= goal and not (removed or restated or folded or fixed),
        placeholder_removed=removed,
        status_rewritten=restated,
        tech_stack_folded=folded,
        fixed_restored=fixed,
    )


#: The library's fixed-law fragments, shipped beside this package (``public/data/fixed``).
_FIXED_FRAGMENTS = Path(__file__).resolve().parents[2] / "public" / "data" / "fixed"


def _fixed_renders(specs_dir: Path) -> list[tuple[Path, str]]:
    """Every present fixed-section file whose block is missing or stale, with its render."""
    renders: list[tuple[Path, str]] = []
    for rel, section_id in FIXED_SECTIONS:
        path = specs_dir / rel
        if not path.is_file():
            continue
        fragment = (_FIXED_FRAGMENTS / f"{section_id}.md").read_text(encoding="utf-8")
        text = path.read_text(encoding="utf-8")
        if extract_fixed_section(text, section_id) != fragment:
            renders.append((path, render_fixed_section(text, section_id, fragment)))
    return renders


def plan_fixed_sections(specs_dir: Path) -> list[Path]:
    """Files whose fixed law section the upgrade would insert or refresh."""
    return [path for path, _ in _fixed_renders(specs_dir)]


def restore_fixed_sections(specs_dir: Path) -> list[Path]:
    """Insert or refresh every fixed law section — the part of canon v7 a v6 tree lacks."""
    renders = _fixed_renders(specs_dir)
    for path, text in renders:
        path.write_text(text, encoding="utf-8")
    return [path for path, _ in renders]


#: The section ``TECHSTACK.md``'s body becomes, appended at the END of ``ARCHITECTURE.md``
#: so the canonical file's existing sections keep their order and their anchors.
_TECH_STACK_HEADING = "## Tech Stack"

#: A tree whose canonical memory still carries the retired two-tier shape. The fold is a
#: text append, and appending a section to a document organised as Part 1 / Part 2 would
#: put it outside both parts — silent corruption. Such a tree is left byte-identical and
#: the doctor names it (TREE-5's canonical-law comparator and the memory shape rules).
_RETIRED_PART_HEADING = "## Part 1 — Principles"


def plan_tech_stack_fold(specs_dir: Path) -> list[Path]:
    """``memory/TECHSTACK.md``, when it exists and ``ARCHITECTURE.md`` can absorb it."""
    tech = specs_dir / "memory" / "TECHSTACK.md"
    architecture = specs_dir / "memory" / "ARCHITECTURE.md"
    if not (tech.is_file() and architecture.is_file()):
        return []
    if _RETIRED_PART_HEADING in architecture.read_text(encoding="utf-8"):
        return []
    return [tech]


def fold_tech_stack(specs_dir: Path) -> list[Path]:
    """Append ``TECHSTACK.md``'s body under ``## Tech Stack`` at the end of
    ``ARCHITECTURE.md``, then delete the file — the 6 -> 7 hop (memory canon v7).

    The body is everything after the document's own H1/frontmatter title block, taken
    verbatim: the hop moves a consumer's authored text, it never rewrites it.
    """
    planned = plan_tech_stack_fold(specs_dir)
    for tech in planned:
        architecture = tech.parent / "ARCHITECTURE.md"
        body = _tech_stack_body(tech.read_text(encoding="utf-8"))
        existing = architecture.read_text(encoding="utf-8").rstrip("\n")
        architecture.write_text(
            f"{existing}\n\n{_TECH_STACK_HEADING}\n\n{body}\n", encoding="utf-8"
        )
        tech.unlink()
    return planned


def _tech_stack_body(text: str) -> str:
    """*text* minus its YAML frontmatter and its leading ``# `` title line."""
    fm = FRONTMATTER_RE.match(text)
    remainder = text[fm.end() :] if fm else text
    lines = remainder.splitlines()
    while lines and (not lines[0].strip() or lines[0].startswith("# ")):
        lines.pop(0)
    return "\n".join(lines).strip()


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
