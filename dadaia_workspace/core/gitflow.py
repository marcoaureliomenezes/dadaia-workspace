"""The project gitflow: three fixed roles, free names, held in the constitution frontmatter.
The one place a branch name is mapped to a role, and the one frontmatter writer."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dadaia_workspace.core import platform
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.frontmatter import FrontmatterError, parse, split
from dadaia_workspace.core.platform import act
from dadaia_workspace.core.skill_owner import load_owner

__all__ = [
    "DEFAULT",
    "candidate_dir",
    "candidate_number",
    "Gitflow",
    "Role",
    "SeveralWorkBranches",
    "constitution_problem",
    "constitution_path",
    "constitution_text",
    "from_mapping",
    "merge_frontmatter",
    "live_release_id",
    "origin_work_branch",
    "next_candidate",
    "read_gitflow",
    "resolve_live_candidate",
    "work_branch",
]

Role = Literal["principal", "integration", "work"]

_grammar = load_owner("dd-bug-resolution", "_grammar")
_key_spans = load_owner("dd-bug-resolution", "_frontmatter").key_spans
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
    live: str | None
    try:
        live = _grammar.sole_live(specs_dir)
    except load_owner("dd-bug-resolution", "_refusal").Refusal:
        live = None
    return live


def resolve_live_candidate(specs_dir: Path) -> Path | None:
    """The live release's candidate folder: `_release_schema.current_candidate` over the state
    `_release_store.read_state` reads; ``None`` with no live release or an unreadable state."""
    release_id = live_release_id(specs_dir)
    if release_id is None:
        return None
    release_dir = specs_dir / "releases" / release_id
    try:
        state = load_owner("dd-release-implementation", "_release_store").read_state(
            release_dir / _grammar.STATE
        )
    except load_owner("dd-bug-resolution", "_refusal").Refusal:
        return None
    candidate: Path | None = load_owner(
        "dd-release-implementation", "_release_schema"
    ).current_candidate(release_dir, state)
    return candidate


_git = load_owner("dd-gitflow-default", "_worktree_git")


class SeveralWorkBranches(DadaiaError):
    """Several local work branches; *keep* is the version the rule keeps, *text* the unlabeled act."""

    def __init__(self, message: str, text: str, keep: str) -> None:
        super().__init__(message, act("agent", text))
        self.keep = keep


def work_branch(repo: Path, flow: Gitflow, main: str) -> str:
    """The repo's work branch by the skill's one rule (``work_version``); with none, the name to
    create (``next_version``); several raise ``SeveralWorkBranches``, which carries the skill's
    text. *main* is the main repo's slug."""
    rule = {"work": flow.work_prefix, "integration": flow.integration, "main": main}
    if _git.work_versions(repo, rule):
        try:
            return str(flow.work_prefix + _git.work_version(repo, rule))
        except _git.SeveralWork as several:
            raise SeveralWorkBranches(several.args[0], several.text, several.keep) from several
    return str(flow.work_prefix + _git.next_version(repo, rule))


def origin_work_branch(repo: Path, flow: Gitflow) -> str | None:
    """The highest work branch origin holds (remote-tracking refs, offline), ``None`` with none."""
    rule, origin = {"work": flow.work_prefix}, "refs/remotes/origin"
    versions = _git.work_versions(repo, rule, origin)
    return (
        flow.work_prefix + _git.several_work(repo, rule, versions, origin)[0] if versions else None
    )


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


def specs_path_kind(specs_dir: Path) -> Literal["tree", "file", "absent"]:
    """What the path is: a directory, anything else that exists, or nothing (a dangling symlink)."""
    return "tree" if specs_dir.is_dir() else "file" if specs_dir.exists() else "absent"


def constitution_text(specs_dir: Path) -> str:
    constitution = constitution_path(specs_dir)
    return platform.read_text(constitution) if constitution.is_file() else ""


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


def constitution_problem(specs_dir: Path, text: str | None = None) -> tuple[str, str] | None:
    """``(cause, act)`` when the constitution (of *text* when given) cannot be trusted: the act
    re-encodes a file that is not UTF-8, else repairs the YAML frontmatter."""
    try:
        reason = _gitflow_block(constitution_text(specs_dir) if text is None else text)[1]
    except platform.Undecodable as bad:
        return f"{bad.path}: is not valid UTF-8", str(bad.fix)
    if not reason:
        return None
    cause = f"{constitution_path(specs_dir)}: {reason}"
    return cause, act("agent", f"repair the YAML frontmatter of {cause}")


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
    text = platform.read_text(constitution) if constitution.exists() else ""
    parts = split(text)
    kept: list[str] = []
    for key, lines in _key_spans(parts[0]) if parts else []:
        if key in updates:
            kept.append(f"{key}: {updates.pop(key)}")
        else:
            kept.extend(lines)
    kept.extend(f"{key}: {value}" for key, value in updates.items())
    platform.write_text(
        constitution, "---\n" + "\n".join(kept) + "\n---\n" + (parts[1] if parts else text)
    )
