"""The project gitflow (ADRs 0037, 0046): three fixed roles, free names.

A value only — the constitution frontmatter holds it (``core/specs_version.read_gitflow``),
the pre-push gate and ``specs init`` consume it. This is the one place a branch name is
mapped to a role; no other module matches branch names.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

__all__ = ["DEFAULT", "Gitflow", "Role", "from_mapping"]

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
    return Gitflow(str(names["principal"]), str(names["integration"]), str(names["work"]))
