"""The onboarding step list (ADRs 0033, 0034, 0038, 0042-0044) — the ONE next-step derivation.

``STEPS`` is ordered: ``context`` (no ALIVE context), ``bind`` (a resolvable session is
unbound), ``specs`` (3a), ``first-pass`` (3b), ``publish`` (3c). Every predicate reads
real state — files, git, the session registry — never a stamp, and no network. The next
step is the focus context's first pending one, else the first pending across *trees*
(every ALIVE context name -> its ``specs/`` dir; the registry read is the caller's).
``doctor``, ``init``, ``context create`` and SessionStart all print :meth:`Step.text`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from dadaia_workspace.core import session_store, workspace_layout
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.fixed_sections import strip_fixed_sections
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION, read_pattern_version
from dadaia_workspace.core.template_history import was_shipped
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

CODE = "ONBOARDING"
Kind = Literal["command", "agent"]
_SKILL = Path(".agents", "skills", "dd-audit-project", "SKILL.md")
_STUBS = ("ARCHITECTURE.md", "QUALITY.md")


@dataclass(frozen=True)
class Step:
    """One pending onboarding step: its id, kind, why it is pending and its one fix line."""

    id: str
    kind: Kind
    reason: str
    command: str

    def text(self) -> str:
        return f"Next ({self.kind} step {self.id}): {self.reason}\nfix: {self.command}"


@dataclass(frozen=True)
class _Ctx:
    root: Path
    name: str
    specs: Path
    session: str | None


def specs_ready(specs_dir: Path) -> bool:
    """True once ``specs init`` has run: the tree is stamped at the canonical version."""
    return specs_dir.is_dir() and read_pattern_version(specs_dir) >= CANONICAL_SPECS_VERSION


def _unbound(c: _Ctx) -> str | None:
    record = session_store.live_session(c.root, c.session) if c.session else None
    if c.session is None or (record is not None and record.get("context")):
        return None
    return "this session has no context binding"


def _first_pass(c: _Ctx) -> list[str]:
    templates = workspace_layout.public_scripts_dir().parent / "templates"
    pending = []
    for name in _STUBS:
        path = c.specs / "memory" / name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not text or was_shipped(
            strip_fixed_sections(text), f"scaffold/memory/{name}", templates
        ):
            pending.append(str(path))
    try:
        catalog = json.loads((c.specs / "memory" / "product" / "catalog.json").read_text("utf-8"))
        atoms = bool(catalog.get("features"))
    except (OSError, ValueError, AttributeError):
        atoms = False
    return pending if atoms else [*pending, "specs/memory/product/ (no atom)"]


def _specs_fix(c: _Ctx) -> str:
    flow = replace(DEFAULT, principal=GitSubprocessClient().default_branch(c.specs.parent))
    flags = ("--principal", flow.principal, "--integration", flow.integration)
    return fix_line(
        c.root, "specs", "init", "--context", c.name, *flags, "--work-prefix", flow.work_prefix
    )


_Pending = Callable[[_Ctx], str | None]
#: (id, kind, pending -> reason | None, fix). The ``context`` step is derived in
#: :func:`next_step` — it is the one step with no context to judge.
STEPS: tuple[tuple[str, Kind, _Pending, Callable[[_Ctx], str]], ...] = (
    ("bind", "command", _unbound, lambda c: fix_line(c.root, "context", "bind", c.name)),
    (
        "specs",
        "command",
        lambda c: None if specs_ready(c.specs) else f"'{c.name}' carries no current specs tree",
        _specs_fix,
    ),
    (
        "first-pass",
        "agent",
        lambda c: f"'{c.name}' memory holds no audited content" if _first_pass(c) else None,
        lambda c: f"{c.root / _SKILL} §first pass — pending: {', '.join(_first_pass(c))}",
    ),
    (
        "publish",
        "command",
        lambda c: (
            None
            if GitSubprocessClient().published(c.specs.parent, "specs/constitution.md")
            else f"'{c.name}' specs are on no remote branch"
        ),
        lambda c: fix_line(c.root, "context", "baseline", c.name),
    ),
)
STEP_IDS = ("context", *(step[0] for step in STEPS))


def next_step(
    root: Path, trees: Mapping[str, Path], focus: str | None = None, session: str | None = None
) -> Step | None:
    """The first pending step — *focus* first, then every context in *trees*; *session* is
    the caller's resolvable session id (``None``: no identity, so no ``bind`` step)."""
    if not trees:
        create = fix_line(root, "context", "create", "<name>", "--main-repo", "<clone-url>")
        return Step("context", "command", "no ALIVE Spec Context — create one", create)
    names = [focus] if focus is not None and focus in trees else []
    for name in [*names, *trees]:
        c = _Ctx(root, name, trees[name], session)
        for step_id, kind, pending, fix in STEPS:
            if (reason := pending(c)) is not None:
                return Step(step_id, kind, reason, fix(c))
    return None
