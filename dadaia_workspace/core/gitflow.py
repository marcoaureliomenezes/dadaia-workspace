"""The project gitflow: three fixed roles, free names, held in the constitution frontmatter.
The one place a branch name is mapped to a role, and the one frontmatter writer."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.frontmatter import FrontmatterError, parse, split
from dadaia_workspace.core.skill_owner import load_owner

__all__ = [
    "DEFAULT",
    "candidate_dir",
    "candidate_number",
    "Gitflow",
    "Role",
    "constitution_error",
    "constitution_path",
    "constitution_text",
    "from_mapping",
    "merge_frontmatter",
    "live_release_id",
    "next_candidate",
    "read_gitflow",
    "resolve_live_candidate",
    "work_branch",
]

Role = Literal["principal", "integration", "work"]

_grammar = load_owner("dd-bug-resolution", "_grammar")
_VERSION_RE = _grammar.SEMVER_RE
candidate_number = _grammar.candidate_number
candidate_dir = _grammar.candidate_dir
# git check-ref-format's refusals, for one branch name (a prefix may end in "/").
_BAD_REF_RE = re.compile(r"[\x00-\x20\x7f~^:?*\[\\]|\.\.|//|@\{|^[/.]|\.$|\.lock(/|$)|/\.|^@$")


@dataclass(frozen=True, slots=True)
class Gitflow:
    principal: str
    integration: str
    work_prefix: str

    @property
    def work_pattern(self) -> str:
        return f"{self.work_prefix}<M.m.p>"

    def role_of(self, branch: str) -> Role | None:
        """``principal`` | ``integration`` | ``work`` (``<prefix><M.m.p>``) | ``None``."""
        if branch == self.principal:
            return "principal"
        if branch == self.integration:
            return "integration"
        version = branch.removeprefix(self.work_prefix)
        if version != branch and _VERSION_RE.fullmatch(version):
            return "work"
        return None


DEFAULT = Gitflow(principal="main", integration="develop", work_prefix="feature/")


def next_candidate(release_dir: Path) -> Path:
    """The ``rc-<N+1>/`` a new candidate is born in — `_release_schema`'s rule."""
    schema = load_owner("dd-release-implementation", "_release_schema")
    return Path(schema.next_candidate(release_dir, None))


def live_release_id(specs_dir: Path) -> str | None:
    """The id of the ONE live release, ``None`` with none or several."""
    live = _grammar.live_ids(specs_dir)
    return live[0] if len(live) == 1 else None


def resolve_live_candidate(specs_dir: Path) -> Path | None:
    """The live release's highest-numbered ``rc-<N>/`` (ADR 0150) — `_release_store`'s
    `candidate_dir` rule; ``None`` with no live release or no candidate folder."""
    release_id = live_release_id(specs_dir)
    return candidate_dir(specs_dir / "releases" / release_id) if release_id else None


def work_branch(specs_dir: Path, flow: Gitflow) -> str:
    """``<work><live release id>``, else ``<work>0.1.0``."""
    return f"{flow.work_prefix}{live_release_id(specs_dir) or '0.1.0'}"


def from_mapping(block: object) -> Gitflow:
    """Validate the frontmatter ``gitflow:`` mapping; ``ValueError`` names what is wrong."""
    if not isinstance(block, Mapping):
        raise ValueError("gitflow must be a mapping {principal, integration, work}")
    names = {key: block.get(key) for key in ("principal", "integration", "work")}
    for key, name in names.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"gitflow.{key} must be a non-empty string")
        if _BAD_REF_RE.search(name.removesuffix("/") if key == "work" else name):
            raise ValueError(f"gitflow.{key} {name!r} is not a valid git branch name")
    if names["principal"] == names["integration"]:
        raise ValueError("gitflow.principal and gitflow.integration must differ")
    if any(f"{names['work']}0".startswith(f"{names[k]}/") for k in ("principal", "integration")):
        raise ValueError(f"gitflow.work {names['work']!r} nests under a role branch name")
    return Gitflow(str(names["principal"]), str(names["integration"]), str(names["work"]))


def constitution_path(specs_dir: Path) -> Path:
    return specs_dir / "constitution.md"


def specs_tree_exists(specs_dir: Path) -> bool:
    return specs_dir.exists()


def constitution_text(specs_dir: Path) -> str:
    constitution = constitution_path(specs_dir)
    return constitution.read_text(encoding="utf-8") if constitution.is_file() else ""


def _gitflow_block(text: str) -> tuple[Gitflow | None, str | None]:
    """(valid block, None); (None, why the frontmatter or block is malformed); (None, None)
    when the constitution, its frontmatter or the block is absent."""
    fm = parse(text)
    if isinstance(fm, FrontmatterError):
        return None, None if fm.kind == "missing_delimiter" else fm.message
    if "gitflow" not in fm.data:
        return None, None
    try:
        return from_mapping(fm.data["gitflow"]), None
    except ValueError as exc:
        return None, str(exc)


def constitution_error(specs_dir: Path, text: str | None = None) -> str | None:
    """Why the constitution's frontmatter (of *text* when given) cannot be trusted."""
    reason = _gitflow_block(constitution_text(specs_dir) if text is None else text)[1]
    return reason and f"{constitution_path(specs_dir)}: {reason}"


def read_gitflow(specs_dir: Path, text: str | None = None) -> tuple[Gitflow, str | None]:
    """The ``gitflow:`` block of *text* (else the file); absent or malformed ⇒ ``DEFAULT``
    plus the warning to show, never a block."""
    flow, reason = _gitflow_block(constitution_text(specs_dir) if text is None else text)
    if flow is not None:
        return flow, None
    return DEFAULT, (
        f"{constitution_path(specs_dir)}: {reason or 'no gitflow block'} — using the default "
        f"gitflow (principal {DEFAULT.principal}, integration {DEFAULT.integration}, "
        f"work {DEFAULT.work_prefix}<M.m.p>)"
    )


def merge_frontmatter(
    specs_dir: Path,
    *,
    specs_pattern_version: int | None = None,
    gitflow: Gitflow | None = None,
) -> None:
    """Write the given keys into the constitution frontmatter (replaced in place, else
    appended; no block ⇒ one prepended); every other line stays identical."""
    names = gitflow and (gitflow.principal, gitflow.integration, gitflow.work_prefix)
    values = {
        "specs_pattern_version": specs_pattern_version,
        "gitflow": names and dict(zip(("principal", "integration", "work"), names, strict=True)),
    }
    updates = {k: json.dumps(v) for k, v in values.items() if v is not None}  # JSON is YAML
    constitution = constitution_path(specs_dir)
    text = constitution.read_text(encoding="utf-8") if constitution.exists() else ""
    parts = split(text)
    lines = parts[0].split("\n") if parts else []
    kept: list[str] = []
    skipping = False
    for line in lines:
        if skipping and (line[:1] in (" ", "\t", "-") or not line.strip()):
            continue
        key = line.split(":", 1)[0]
        skipping = ":" in line and key in updates
        kept.append(f"{key}: {updates.pop(key)}" if skipping else line)
    kept.extend(f"{key}: {value}" for key, value in updates.items())
    constitution.write_text(
        "---\n" + "\n".join(kept) + "\n---\n" + (parts[1] if parts else text), encoding="utf-8"
    )
