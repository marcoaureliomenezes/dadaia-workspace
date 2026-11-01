"""The onboarding step list — the one next-step derivation.

``STEPS`` is ordered: ``context`` (no ALIVE context), ``bind`` (a resolvable session is
unbound), ``constitution`` (frontmatter unparseable), ``specs`` (3a),
``first-pass`` (3b), ``publish`` (3c). Every predicate reads real state — files, git,
the session registry — never a stamp, and no network. One context is judged: the focus,
else the only one in *trees* (every ALIVE name -> its ``specs/`` dir; the caller's read).
``doctor``, ``init``, ``context create`` and SessionStart all print :meth:`Step.text`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core import platform, workspace_layout
from dadaia_workspace.core.cli_line import cli_words, fix_line, spell_fix
from dadaia_workspace.core.fixed_sections import strip_fixed_sections
from dadaia_workspace.core.gitflow import SeveralWorkBranches, constitution_problem
from dadaia_workspace.core.platform import act
from dadaia_workspace.core.specs_version import state
from dadaia_workspace.core.template_history import was_shipped
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.ledger_scripts import load_owner

CODE = "ONBOARDING"
_INDEX = "product/index.md"
_STUBS = ("ARCHITECTURE.md", "QUALITY.md", _INDEX)


@dataclass(frozen=True)
class Step:
    """One pending onboarding step: its id, kind, why it is pending and its one fix line."""

    id: str
    kind: str
    reason: str
    command: str

    def text(self) -> str:
        return f"Next ({self.kind} step {self.id}): {self.reason}\n{spell_fix(self.command)}"


def _step(step_id: str, reason: str, fix: str) -> Step:
    """The step whose kind is its fix line's: an act's own kind, else a command."""
    return Step(step_id, platform.act_kind(fix) or "command", reason, fix)


@dataclass(frozen=True)
class _Ctx:
    root: Path
    name: str
    specs: Path
    bound: bool | None
    refusal: tuple[str, str] | None = None


def specs_ready(specs_dir: Path) -> bool:
    return state(specs_dir)[0] == "canonical"


def _constitution_reason(c: _Ctx) -> str | None:
    problem = constitution_problem(c.specs)
    return problem[0] if problem else None


def _unbound(c: _Ctx) -> str | None:
    why = c.refusal[0] if c.refusal else "this session has no context binding"
    return why if c.bound is False else None


def _first_pass(c: _Ctx) -> list[str]:
    templates = workspace_layout.public_scripts_dir().parent / "templates"
    catalog = load_owner("dd-spec-navigator", "_memory_catalog")
    pending = []
    for name in _STUBS:
        path = c.specs / "memory" / name
        text = platform.read_text(path) if path.is_file() else ""
        if text and name == _INDEX:
            text = catalog.render(c.specs, {})  # the generated section set aside
        if not text or was_shipped(
            strip_fixed_sections(text), f"scaffold/memory/{name}", templates
        ):
            pending.append(str(path))
    drift = load_owner("dd-bug-resolution", "_memory_drift")
    try:
        atoms = bool(drift.atoms(c.specs))
    except drift.Refusal:
        atoms = False
    return pending if atoms else [*pending, f"{c.specs / 'memory' / 'product'} (no atom)"]


def _first_pass_fix(c: _Ctx) -> str:
    """The first-pass act; with several work branches, that refusal's own fix."""
    repo = c.specs.parent
    try:
        version = GitSubprocessClient().work_version(repo)
    except SeveralWorkBranches as several:
        return several.fix
    lane = platform.inline(
        *cli_words(c.root, "worktree", "new", repo.name, f"{version}/wt-backlog-first-pass")
    )
    return act(
        "agent",
        f"open the lane {lane}, then run the dd-audit-project first pass in it — {', '.join(_first_pass(c))}",
    )


_Pending = Callable[[_Ctx], str | None]
#: (id, pending -> reason | None, fix). The ``context`` step is derived in
#: :func:`next_step` — it is the one step with no context to judge.
STEPS: tuple[tuple[str, _Pending, Callable[[_Ctx], str]], ...] = (
    (
        "bind",
        _unbound,
        lambda c: c.refusal[1] if c.refusal else fix_line(c.root, "context", "bind", c.name),
    ),
    (
        "constitution",
        _constitution_reason,
        lambda c: str(state(c.specs)[1]),
    ),
    (
        "specs",
        lambda c: None if specs_ready(c.specs) else f"'{c.name}' specs tree is {state(c.specs)[0]}",
        lambda c: str(state(c.specs, root=c.root, context=c.name)[1]),
    ),
    (
        "first-pass",
        lambda c: f"'{c.name}' memory holds no audited content" if _first_pass(c) else None,
        _first_pass_fix,
    ),
    (
        "publish",
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
    root: Path,
    trees: Mapping[str, Path],
    focus: str | None = None,
    bound: bool | None = None,
    refusal: tuple[str, str] | None = None,
) -> Step | None:
    """The judged context's first pending step, or ``None``; *bound* is
    whether the caller's session is bound (``None``: no identity, so no ``bind`` step) and
    *refusal* the ``(message, fix)`` a pending ``bind`` prints instead of ``context bind`` (a
    refused bind); a step's kind follows its fix line."""
    if not trees:
        create = act(
            "agent",
            f"run {platform.inline(*cli_words(root, 'context', 'create'))} with a context name "
            "and --main-repo set to the main repo's clone URL",
        )
        return _step("context", "no ALIVE Spec Context — create one", create)
    if focus is None and len(trees) == 1:
        focus = next(iter(trees))
    if focus is None or focus not in trees:
        return None
    c = _Ctx(root, focus, trees[focus], bound, refusal)
    for step_id, pending, fix in STEPS:
        if (reason := pending(c)) is not None:
            return _step(step_id, reason, fix(c))
    return None
