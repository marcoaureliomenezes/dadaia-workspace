"""The project gitflow (ADRs 0037, 0046): three fixed roles, free names.

The constitution frontmatter holds it: :func:`read_gitflow` reads it back and
:func:`merge_frontmatter` is the one frontmatter writer; the pre-push gate and ``specs init``
consume it. This is the one place a branch name is
mapped to a role; no other module matches branch names.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.frontmatter import FRONTMATTER_RE, FrontmatterError, parse

__all__ = [
    "DEFAULT",
    "Gitflow",
    "Role",
    "constitution_error",
    "constitution_path",
    "constitution_text",
    "from_mapping",
    "merge_frontmatter",
    "read_gitflow",
]

Role = Literal["principal", "integration", "work"]

_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
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


def constitution_error(specs_dir: Path) -> str | None:
    """Why an existing constitution's frontmatter cannot be trusted (ADR 0047): its YAML
    does not parse, or its ``gitflow:`` block does not validate; ``None`` otherwise."""
    reason = _gitflow_block(constitution_text(specs_dir))[1]
    return reason and f"{constitution_path(specs_dir)}: {reason}"


def read_gitflow(specs_dir: Path, text: str | None = None) -> tuple[Gitflow, str | None]:
    """The constitution's ``gitflow:`` block — of *text* when given (a committed copy,
    ADR 0048), else of the file; absent or malformed ⇒ ``DEFAULT`` plus the warning to
    show (ADR 0037: never a block)."""
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
    """Write the given keys into the constitution frontmatter, one line each.

    The one writer for both keys: a written key's top-level line (and its indented or
    ``-`` continuation lines) is replaced in place, a new key is appended to the block,
    and every other line — plus the body — stays byte-identical. No block ⇒ one is
    prepended.
    """
    names = gitflow and (gitflow.principal, gitflow.integration, gitflow.work_prefix)
    values = {
        "specs_pattern_version": specs_pattern_version,
        "gitflow": names and dict(zip(("principal", "integration", "work"), names, strict=True)),
    }
    updates = {k: json.dumps(v) for k, v in values.items() if v is not None}  # JSON is YAML
    constitution = constitution_path(specs_dir)
    text = constitution.read_text(encoding="utf-8") if constitution.exists() else ""
    match = FRONTMATTER_RE.match(text)
    lines = match.group(1).split("\n") if match else []
    kept: list[str] = []
    skipping = False
    for line in lines:
        if skipping and (line[:1] in (" ", "\t", "-") or not line.strip()):
            continue
        key = line.split(":", 1)[0]
        skipping = ":" in line and key in updates
        kept.append(f"{key}: {updates.pop(key)}" if skipping else line)
    kept.extend(f"{key}: {value}" for key, value in updates.items())
    body = text[match.end() :] if match else text
    closing = text[match.start(0) : match.end()].rsplit("\n---", 1)[1] if match else "\n"
    constitution.write_text("---\n" + "\n".join(kept) + "\n---" + closing + body, encoding="utf-8")
