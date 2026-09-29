"""``dadaia specs upgrade`` orchestration (FR-S04 / FR-S05; simplified v0.5.1 T-051-16).

Sequence: read the tree through ``specs_version.state`` -- an absent, malformed or
foreign tree raises :class:`UpgradeRefused` carrying that state's fix, without touching
the filesystem; an upgradable tree walks the hops (:func:`fold_tech_stack`, the doctor's repair set) and is re-stamped;
a tree already at canonical is a no-op except for the empty ``_ideas/`` removal.
Every other repair is the doctor's (``specs upgrade`` runs its repair set, WP-14).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core import specs_version as _version
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.frontmatter import FRONTMATTER_RE
from dadaia_workspace.core.gitflow import merge_frontmatter
from dadaia_workspace.core.spec_status import APPROVED, DRAFT, IN_REVIEW


class UpgradeRefused(Exception):
    """The tree cannot be upgraded; nothing was written."""


@dataclass
class UpgradeResult:
    """Outcome of an upgrade run."""

    #: True when the constitution was (or, dry-run, would be) re-stamped to ``to_version``.
    stamped: bool
    to_version: int
    dry_run: bool
    no_op: bool = False
    #: Empty ``releases/_ideas/`` dirs removed (planned-only when ``dry_run``).
    ideas_removed: list[Path] = field(default_factory=list)
    #: Live-release trio documents whose retired Portuguese status token was rewritten
    #: to the English vocabulary (planned-only when ``dry_run``).
    status_rewritten: list[Path] = field(default_factory=list)
    #: ``memory/TECHSTACK.md`` folded into ``ARCHITECTURE.md``'s ``## Tech Stack``
    #: section and deleted by the 6 -> 7 hop (planned-only when ``dry_run``).
    tech_stack_folded: list[Path] = field(default_factory=list)


def upgrade(
    specs_dir: Path, *, remove: Callable[[Path], object], dry_run: bool = False
) -> UpgradeResult:
    """Upgrade ``specs/`` to :data:`CANONICAL_SPECS_VERSION`, the one target. Every
    delete goes through *remove* — the caller's one guarded deleter (``sweep.remove``).

    Raises :class:`UpgradeRefused`, before any write, for a tree ``state`` does not call
    upgradable or canonical, or one still organised two-tier (ADR 0082).
    """
    kind, fix = _version.state(specs_dir)
    if kind not in ("upgradable", "canonical"):
        raise UpgradeRefused(f"specs tree {specs_dir} is {kind}; nothing written.\nfix: {fix}")
    goal = _version.CANONICAL_SPECS_VERSION
    architecture = specs_dir / "memory" / "ARCHITECTURE.md"
    if architecture.is_file() and _RETIRED_PART_HEADING in architecture.read_text("utf-8"):
        raise UpgradeRefused(
            f"{architecture} is two-tier ({_RETIRED_PART_HEADING!r}): nowhere safe to fold "
            "into. Rewrite it as ## Principles / ## Tech Stack / ## Structure, then re-run."
        )

    if dry_run:
        removed = plan_empty_ideas_dir(specs_dir)
        restated = plan_status_token_rewrites(specs_dir)
        folded = plan_tech_stack_fold(specs_dir)
    else:
        removed = remove_empty_ideas_dir(specs_dir, remove)
        restated = rewrite_status_tokens(specs_dir)
        folded = fold_tech_stack(specs_dir, remove)
        if kind == "upgradable":
            merge_frontmatter(specs_dir, specs_pattern_version=goal)
    return UpgradeResult(
        stamped=kind == "upgradable",
        to_version=goal,
        dry_run=dry_run,
        no_op=kind == "canonical" and not (removed or restated or folded),
        ideas_removed=removed,
        status_rewritten=restated,
        tech_stack_folded=folded,
    )


#: The section ``TECHSTACK.md``'s body becomes, appended at the END of ``ARCHITECTURE.md``
#: so the canonical file's existing sections keep their order and their anchors.
_TECH_STACK_HEADING = "## Tech Stack"

#: The retired two-tier shape: a fold appended to it lands outside both parts, so
#: :func:`upgrade` refuses the tree whole (ADR 0082).
_RETIRED_PART_HEADING = "## Part 1 — Principles"


def plan_tech_stack_fold(specs_dir: Path) -> list[Path]:
    """``memory/TECHSTACK.md``, when it exists and ``ARCHITECTURE.md`` can absorb it."""
    tech = specs_dir / "memory" / "TECHSTACK.md"
    architecture = specs_dir / "memory" / "ARCHITECTURE.md"
    return [tech] if tech.is_file() and architecture.is_file() else []


def fold_tech_stack(specs_dir: Path, remove: Callable[[Path], object]) -> list[Path]:
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
        atomic_write(architecture, f"{existing}\n\n{_TECH_STACK_HEADING}\n\n{body}\n")
        remove(tech)
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


def remove_empty_ideas_dir(specs_dir: Path, remove: Callable[[Path], object]) -> list[Path]:
    planned = plan_empty_ideas_dir(specs_dir)
    for ideas in planned:
        remove(ideas)
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


def _live_trio_documents(specs_dir: Path) -> list[Path]:
    """Every document of every LIVE release (the rewrite touches only a ``**Status:**``
    line). ``releases/_archive/`` is published history: excluded by path, never by
    token, so an archived tree keeps reading as it shipped."""
    releases = specs_dir / "releases"
    live = releases.glob("*/**/*.md")
    return sorted(p for p in live if "_archive" not in p.relative_to(releases).parts)


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
        atomic_write(path, _rewrite_status_line(text))
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
