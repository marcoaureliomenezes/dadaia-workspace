"""Typed harness identity registry — ``core/harness_registry.py``.

The **code embodiment** of the agent-runtime roster that ``specs/memory/tech-stack.md``
("Agent runtimes") documents as the single source of truth (SPEC-DOC-037). One
:class:`HarnessRecord` per harness is the whole registry: every other constant here
(:data:`L1_ENTRY_HARNESSES`, :data:`HARNESS_PROJECTION_DIRS`,
:data:`PROJECTION_TARGETS`) and every projection rule in
``infrastructure/projection_rules.py`` derives from it, so a harness fact is stated
once and a per-harness ``if`` has nowhere to live (0.4.7 FR2).

Layering: a pure ``core`` leaf — **stdlib only, no upward import** (import-linter clean).
Consumed downward by ``infrastructure`` / ``features`` / ``cli``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentTranscode(StrEnum):
    """How a harness consumes the ONE authored persona set under ``.agents/agents/``.

    ``NONE`` means it reads that tree natively and projects no view of its own.
    """

    NONE = "none"
    CLAUDE_MD_SYMLINK = "claude-md-symlink"
    CODEX_TOML = "codex-toml"
    CURSOR_MD = "cursor-md"
    DEVIN_MD = "devin-md"
    COPILOT_AGENT_MD = "copilot-agent-md"


class HookFormat(StrEnum):
    """The serialization format a harness's hook registration takes.

    A value names only the *format*: the behaviours themselves (root whitelist, venv
    guard, SDD gate, session-start reaper) are the workspace's, identical everywhere.
    """

    NONE = "none"
    CLAUDE_SETTINGS = "claude-settings"
    CODEX_HOOKS = "codex-hooks"
    KIMI_HOOKS = "kimi-hooks"
    CURSOR_HOOKS = "cursor-hooks"
    DEVIN_HOOKS = "devin-hooks"
    COPILOT_HOOKS = "copilot-hooks"


@dataclass(frozen=True)
class HarnessRecord:
    """Everything the workspace knows about one Layer-1 entry harness.

    Args:
        name: the harness id — the ``--harness`` value and the ``ProjectionRule.harness``
            tag.
        directory: the workspace directory it owns, or ``None`` when it owns none
            (``kimi-code`` reads the shared ``.agents/*`` tree and registers its hooks at
            the user level).
        agent_transcode: how it consumes the authored persona set.
        hooks: the format its hook registration serializes into.
    """

    name: str
    directory: str | None
    agent_transcode: AgentTranscode
    hooks: HookFormat


#: The registry. Insertion order IS the canonical order (``init --harness`` and the
#: projection loop both walk it).
HARNESS_RECORDS: dict[str, HarnessRecord] = {
    record.name: record
    for record in (
        HarnessRecord(
            name="claude",
            directory=".claude",
            agent_transcode=AgentTranscode.CLAUDE_MD_SYMLINK,
            hooks=HookFormat.CLAUDE_SETTINGS,
        ),
        HarnessRecord(
            name="codex",
            directory=".codex",
            agent_transcode=AgentTranscode.CODEX_TOML,
            hooks=HookFormat.CODEX_HOOKS,
        ),
        HarnessRecord(
            name="kimi-code",
            directory=None,
            agent_transcode=AgentTranscode.NONE,
            hooks=HookFormat.KIMI_HOOKS,
        ),
        HarnessRecord(
            name="cursor",
            directory=".cursor",
            agent_transcode=AgentTranscode.CURSOR_MD,
            hooks=HookFormat.CURSOR_HOOKS,
        ),
        HarnessRecord(
            name="devin",
            directory=".devin",
            agent_transcode=AgentTranscode.DEVIN_MD,
            hooks=HookFormat.DEVIN_HOOKS,
        ),
        HarnessRecord(
            name="copilot",
            directory=".github",
            agent_transcode=AgentTranscode.COPILOT_AGENT_MD,
            hooks=HookFormat.COPILOT_HOOKS,
        ),
    )
}

#: The Layer-1 entry-harness roster, in canonical order.
L1_ENTRY_HARNESSES: tuple[str, ...] = tuple(HARNESS_RECORDS)

#: The workspace directories each Layer-1 entry harness owns — a harness with no
#: ``directory`` owns an empty tuple.
HARNESS_PROJECTION_DIRS: dict[str, tuple[str, ...]] = {
    name: ((record.directory,) if record.directory is not None else ())
    for name, record in HARNESS_RECORDS.items()
}

#: The projectable install targets in canonical order: the shared ``agents`` authored
#: root plus one projection per Layer-1 entry harness.
PROJECTION_TARGETS: tuple[str, ...] = ("agents", *L1_ENTRY_HARNESSES)

_L1_SET: frozenset[str] = frozenset(L1_ENTRY_HARNESSES)


def parse_harness_name(value: str) -> str:
    """Parse a ``--harness`` selector into the ONE registered harness name it denotes.

    Exactly one record, always. The ``"all"`` meta-value and the comma-separated subset
    form were deleted with 0.4.7 FR2: a workspace is born with one harness and
    ``dadaia harness add`` is the only way a second one enters.

    Args:
        value: the raw selector, e.g. ``"claude"`` (case-insensitive, whitespace-tolerant).

    Returns:
        The canonical harness name.

    Raises:
        ValueError: if *value* is not a registered harness name. The message lists the
            registered names.
    """
    name = value.strip().lower()
    valid = ", ".join(L1_ENTRY_HARNESSES)
    if name not in _L1_SET:
        raise ValueError(f"unknown harness {value!r}; registered harnesses: {valid}")
    return name
