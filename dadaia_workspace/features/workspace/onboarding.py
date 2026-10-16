"""The onboarding step list — the one next-step derivation.

``STEPS`` is ordered: ``context`` (no ALIVE context), ``bind`` (a resolvable session is
unbound), ``constitution`` (frontmatter unparseable), ``specs`` (3a),
``first-pass`` (3b), ``publish`` (3c). Every predicate reads real state — files, git,
the session registry — never a stamp, and no network. One context is judged: the focus,
else the only one in *trees* (every ALIVE name -> its ``specs/`` dir; the caller's read).
``doctor``, ``init``, ``context create`` and SessionStart all print :meth:`Step.text`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dadaia_workspace.core import platform, workspace_layout
from dadaia_workspace.core.cli_line import cli_words, fix_line, spell_fix
from dadaia_workspace.core.fixed_sections import strip_fixed_sections
from dadaia_workspace.core.gitflow import SeveralWorkBranches, constitution_problem
from dadaia_workspace.core.specs_version import state
from dadaia_workspace.core.template_history import was_shipped
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

CODE = "ONBOARDING"
Kind = Literal["command", "agent"]
_STUBS = ("ARCHITECTURE.md", "QUALITY.md")


@dataclass(frozen=True)
class Step:
    """One pending onboarding step: its id, kind, why it is pending and its one fix line."""

    id: str
    kind: Kind
    reason: str
    command: str

    def text(self) -> str:
        return f"Next ({self.kind} step {self.id}): {self.reason}\n{spell_fix(self.command)}"


@dataclass(frozen=True)
class _Ctx:
    root: Path
    name: str
    specs: Path
    bound: bool | None


def specs_ready(specs_dir: Path) -> bool:
    return state(specs_dir)[0] == "canonical"


def _constitution_reason(c: _Ctx) -> str | None:
    problem = constitution_problem(c.specs)
    return problem[0] if problem else None


def _unbound(c: _Ctx) -> str | None:
    return "this session has no context binding" if c.bound is False else None


def _first_pass(c: _Ctx) -> list[str]:
    templates = workspace_layout.public_scripts_dir().parent / "templates"
    pending = []
    for name in _STUBS:
        path = c.specs / "memory" / name
        text = platform.read_text(path) if path.is_file() else ""
        if not text or was_shipped(
            strip_fixed_sections(text), f"scaffold/memory/{name}", templates
        ):
            pending.append(str(path))
    try:
        catalog = json.loads(platform.read_text(c.specs / "memory" / "product" / "catalog.json"))
        atoms = bool(catalog.get("features"))
    except (OSError, ValueError, AttributeError, platform.Undecodable):
        atoms = False
    return pending if atoms else [*pending, f"{c.specs / 'memory' / 'product'} (no atom)"]


def _first_pass_fix(c: _Ctx) -> str:
    """The first-pass act; with several work branches it leads with the refusal's own fix."""
    repo, lead = c.specs.parent, ""
    try:
        version = GitSubprocessClient().work_version(repo)
    except SeveralWorkBranches as several:
        version, lead = several.keep, several.fix.removeprefix("Agent action: ") + ", then "
    lane = platform.inline(
        *cli_words(c.root, "worktree", "new", repo.name, f"{version}/wt-backlog-first-pass")
    )
    return (
        f"Agent action: {lead}open the lane {lane}"
        f", then run the dd-audit-project first pass in it — {', '.join(_first_pass(c))}"
    )


_Pending = Callable[[_Ctx], str | None]
#: (id, kind, pending -> reason | None, fix). The ``context`` step is derived in
#: :func:`next_step` — it is the one step with no context to judge.
STEPS: tuple[tuple[str, Kind, _Pending, Callable[[_Ctx], str]], ...] = (
    ("bind", "command", _unbound, lambda c: fix_line(c.root, "context", "bind", c.name)),
    (
        "constitution",
        "agent",
        _constitution_reason,
        lambda c: str(state(c.specs)[1]),
    ),
    (
        "specs",
        "command",
        lambda c: None if specs_ready(c.specs) else f"'{c.name}' specs tree is {state(c.specs)[0]}",
        lambda c: str(state(c.specs, root=c.root, context=c.name)[1]),
    ),
    (
        "first-pass",
        "agent",
        lambda c: f"'{c.name}' memory holds no audited content" if _first_pass(c) else None,
        _first_pass_fix,
    ),
    (
        "publish",
        "command",
        lambda c: (
            None
            if GitSubprocessClient().published(c.specs.parent)
            else f"'{c.name}' specs are on no remote branch"
        ),
        lambda c: fix_line(c.root, "context", "baseline", c.name),
    ),
)
STEP_IDS = ("context", *(step[0] for step in STEPS))


def next_step(
    root: Path, trees: Mapping[str, Path], focus: str | None = None, bound: bool | None = None
) -> Step | None:
    """The judged context's first pending step, or ``None``; *bound* is
    whether the caller's session is bound (``None``: no identity, so no ``bind`` step)."""
    if not trees:
        create = (
            f"Agent action: run {platform.inline(*cli_words(root, 'context', 'create'))} with a context name "
            "and --main-repo set to the main repo's clone URL"
        )
        return Step("context", "command", "no ALIVE Spec Context — create one", create)
    if focus is None and len(trees) == 1:
        focus = next(iter(trees))
    if focus is None or focus not in trees:
        return None
    c = _Ctx(root, focus, trees[focus], bound)
    for step_id, kind, pending, fix in STEPS:
        if (reason := pending(c)) is not None:
            return Step(step_id, kind, reason, fix(c))
    return None
