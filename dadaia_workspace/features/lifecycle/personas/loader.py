"""Persona loader — the Layer-2 equivalent of a Claude sub-agent (AC-1).

A **persona** is the behavioral mandate behind a Layer-2 worker's ``role:`` token. At
Layer-1 (Claude) the sub-agent files under ``public/agents/<name>.md`` carry that mandate;
at Layer-2 (codex/pi) there is no sub-agent entity, so the persona library
(``public/personas/<role>.md``) supplies the same mandate in a harness-universal form.

This loader is the read+validate API the lifecycle engine uses to turn a ``role:`` string
into a validated :class:`Persona` (frontmatter metadata + markdown body). It is a semantic
twin of :class:`~dadaia_workspace.features.lifecycle.fragments.loader.FragmentLoader`,
parameterizing the shared
:class:`~dadaia_workspace.features.lifecycle._frontmatter_doc.FrontmatterDocLoader` base
with the persona schema.

It enforces three guarantees:

1. **Metadata validation** — every persona carries the 5 required frontmatter keys
   (``id``, ``role``, ``summary``, ``source_agent``, ``harness_universal``) with the
   correct types. Malformed metadata raises :class:`PersonaValidationError`.

2. **Harness-universal token lint** — a persona body that names a harness-specific
   tool/command token (e.g. ``read tool``, ``codex exec``, ``.claude/``) is rejected; a
   persona must read identically to any Layer-2 worker.

3. **Dangling-reference guard** — :meth:`PersonaLoader.validate_all` asserts each
   persona's ``source_agent`` navigational pointer resolves to an existing
   ``public/agents/<role>.md`` file. (This catches a missing/renamed sub-agent file; it
   does NOT detect content divergence between the two hand-authored mandates — that
   alignment is hand-authored discipline, recorded as risk R2.)

``project-manager`` deliberately has **no** persona atom — it is the Layer-1 orchestrator,
not a Layer-2 worker persona (D-1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.features.lifecycle._frontmatter_doc import (
    FrontmatterDocLoader,
    forbidden_token_in,
)

__all__ = [
    "Persona",
    "PersonaError",
    "PersonaLoader",
    "PersonaNotFoundError",
    "PersonaValidationError",
    "forbidden_token_in",
    "list_personas",
    "load_persona",
    "resolve_persona_for_role",
    "validate_all",
]

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PersonaError(DadaiaError):
    """Base error for the lifecycle persona loader."""


class PersonaNotFoundError(PersonaError):
    """Raised when a requested persona role / path cannot be resolved."""


class PersonaValidationError(PersonaError):
    """Raised when a persona's metadata is malformed, its body fails the lint, or its
    ``source_agent`` pointer is dangling."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STUB_NAME = "_README.md"

#: The 5 required persona frontmatter keys (SPEC AC-1), in declaration order.
_REQUIRED_KEYS: tuple[str, ...] = (
    "id",
    "role",
    "summary",
    "source_agent",
    "harness_universal",
)

#: Keys whose value must be a non-empty ``str``. ``harness_universal`` is a boolean and is
#: validated separately in :meth:`PersonaLoader._load_path`.
_STR_KEYS = frozenset({"id", "role", "summary", "source_agent"})


@dataclass(frozen=True)
class Persona:
    """A loaded, validated persona — a harness-universal Layer-2 role mandate."""

    id: str
    role: str
    summary: str
    source_agent: str
    harness_universal: bool
    body: str
    path: Path


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _default_root() -> Path:
    """Resolve the packaged persona root inside the wheel/source tree.

    ``loader.py`` lives at ``features/lifecycle/personas/loader.py``; the persona source
    lives at ``public/personas/`` — a sibling of ``public/lifecycle_fragments/`` under the
    package root.
    """
    package_root = Path(__file__).resolve().parents[3]
    return package_root / "public" / "personas"


class PersonaLoader(FrontmatterDocLoader):
    """Load + validate personas from the projected/packaged location."""

    _NOUN = "persona"
    _NOUN_PLURAL = "personas"
    _ERROR = PersonaValidationError
    _REQUIRED_KEYS = _REQUIRED_KEYS
    _STR_KEYS = _STR_KEYS
    _LIST_KEYS = frozenset()

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else _default_root()

    @property
    def root(self) -> Path:
        return self._root

    # -- discovery -------------------------------------------------------

    def _iter_persona_paths(self) -> list[Path]:
        if not self._root.exists():
            raise PersonaNotFoundError(f"Persona root not found: {self._root}")
        return [path for path in sorted(self._root.rglob("*.md")) if path.name != _STUB_NAME]

    def list_personas(self) -> list[Persona]:
        """Load every persona under the root."""
        return [self._load_path(path) for path in self._iter_persona_paths()]

    # -- loading ---------------------------------------------------------

    def load_persona(self, role: str) -> Persona:
        """Load the persona for *role* by its filename stem (``<root>/<role>.md``)."""
        path = self._root / f"{role}.md"
        if not path.exists():
            raise PersonaNotFoundError(f"No persona for role '{role}' under {self._root}")
        return self._load_path(path)

    def load_optional(self, role: str) -> Persona | None:
        """Load the persona for *role*, or ``None`` when no atom exists for it.

        ``role == "shared"`` and any role with no persona atom resolve to ``None`` — the
        non-raising resolution the injection seam uses so a shared / unmapped step simply
        carries no persona block (additive-optional, never a placeholder).
        """
        if not role or role == "shared":
            return None
        path = self._root / f"{role}.md"
        if not path.exists():
            return None
        return self._load_path(path)

    def validate_all(self) -> list[Persona]:
        """Load + validate every persona AND assert each ``source_agent`` resolves.

        The dangling-reference guard: each persona's ``source_agent`` pointer
        (``agents/<role>.md``) must resolve to an existing file under the sibling
        ``public/agents/`` directory. A dangling pointer raises
        :class:`PersonaValidationError`.
        """
        personas = self.list_personas()
        for persona in personas:
            agent_path = self._root.parent / persona.source_agent
            if not agent_path.exists():
                raise PersonaValidationError(
                    f"{persona.path}: source_agent '{persona.source_agent}' is dangling — "
                    f"no such agent file at {agent_path}"
                )
        return personas

    # -- parse + validate ------------------------------------------------

    def _load_path(self, path: Path) -> Persona:
        text = path.read_text(encoding="utf-8")
        meta, body = self._split_frontmatter(text, path)
        self._validate_metadata(meta, path)
        self._lint_body(body, path)
        harness_universal = meta["harness_universal"]
        if not isinstance(harness_universal, bool):
            raise PersonaValidationError(
                f"{path}: persona metadata key 'harness_universal' must be a boolean, "
                f"got {type(harness_universal).__name__}"
            )
        return Persona(
            id=str(meta["id"]),
            role=str(meta["role"]),
            summary=str(meta["summary"]),
            source_agent=str(meta["source_agent"]),
            harness_universal=harness_universal,
            body=body,
            path=path,
        )


# Module-level convenience: a default loader bound to the packaged persona root.
_DEFAULT_LOADER = PersonaLoader()


def resolve_persona_for_role(role: str, loader: PersonaLoader | None = None) -> str | None:
    """Resolve a step's ``role`` token to its Layer-2 persona mandate(s) (v0.1.44 / AC-2).

    This is the SINGLE source of role→persona resolution shared by every prompt-assembly
    surface — the :class:`~dadaia_workspace.features.lifecycle.pipeline.LifecyclePipeline`,
    each fragment workflow body (release_definition / audit / backlog_definition),
    and the implementation pipeline — so every model-driven step prompt
    on every verb carries the persona body as its operative role directive (W1-3).

    ``role`` is comma-split (a multi-role step such as ``plan_review`` names
    ``"qa-engineer, software-architect"``); each named role is resolved through
    :meth:`PersonaLoader.load_optional`. ``role == "shared"`` and any role with no persona
    atom (e.g. ``python``, ``project-manager``) resolve to ``None`` for that name — no
    persona block, no crash. The result is:

    * ``None`` when no named role resolves to a persona (a ``shared`` / unmapped step —
      keeping the persona-less envelope byte-identical);
    * the single mandate body when exactly one role resolves;
    * each resolving role's mandate, delimited by a ``### Persona — <name>`` header, when
      several do (the multi-role set carries every named persona's mandate).

    ``loader`` is injectable for tests; ``None`` uses the packaged default loader.
    """
    active = loader if loader is not None else _DEFAULT_LOADER
    resolved: list[tuple[str, str]] = []
    for name in (part.strip() for part in role.split(",")):
        persona = active.load_optional(name)
        if persona is not None:
            resolved.append((name, persona.body))
    if not resolved:
        return None
    if len(resolved) == 1:
        return resolved[0][1]
    return "\n\n".join(f"### Persona — {name}\n{body}" for name, body in resolved)


def load_persona(role: str) -> Persona:
    """Load a single persona from the default (packaged) persona root."""
    return _DEFAULT_LOADER.load_persona(role)


def list_personas() -> list[Persona]:
    """List personas from the default (packaged) persona root."""
    return _DEFAULT_LOADER.list_personas()


def validate_all() -> list[Persona]:
    """Validate every persona under the default (packaged) persona root."""
    return _DEFAULT_LOADER.validate_all()
