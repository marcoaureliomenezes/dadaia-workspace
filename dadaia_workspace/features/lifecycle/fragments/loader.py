"""Lifecycle fragment loader — load + validate the WS-3 fragment library.

Fragments ship in the wheel under ``dadaia_workspace/public/lifecycle_fragments/``
(ADR-D / OQ-1) and are projected + manifest-tracked by ``public install``. This
module is the read+validate API the lifecycle engine uses to turn a fragment id into
a validated ``Fragment`` (frontmatter metadata + markdown body).

It enforces two guarantees:

1. **Metadata validation** — every fragment carries the 8 required frontmatter keys
   (``id``, ``role``, ``workflow``, ``step``, ``static_inputs``, ``dynamic_inputs``,
   ``output_schema``, ``max_context_policy``) with the correct types. Malformed
   metadata raises :class:`FragmentValidationError` with a precise message.

2. **Harness-universal token lint (SECONDARY guarantee).** A fragment body that names
   a harness-specific tool/command token (e.g. ``read tool``, ``codex exec``,
   ``pi --mode``, ``.claude/``) is rejected — a fragment must read identically to any
   Layer-2 worker. The PRIMARY harness-universal guarantee is the behavioral
   dual-parser output-schema parity test (see ``tests/.../test_fragment_output_parity``).

``_README.md`` files are workflow-directory stubs with no frontmatter; they are not
fragments and are skipped by discovery and validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from dadaia_workspace.core.exceptions import DadaiaError

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class FragmentError(DadaiaError):
    """Base error for the lifecycle fragment loader."""


class FragmentNotFoundError(FragmentError):
    """Raised when a requested fragment id / path cannot be resolved."""


class FragmentValidationError(FragmentError):
    """Raised when a fragment's metadata is malformed or its body fails the lint."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FRONTMATTER_DELIM = "---"
_STUB_NAME = "_README.md"

#: The 8 required frontmatter keys (SPEC WS-3 / epic §5), in declaration order.
_REQUIRED_KEYS: tuple[str, ...] = (
    "id",
    "role",
    "workflow",
    "step",
    "static_inputs",
    "dynamic_inputs",
    "output_schema",
    "max_context_policy",
)

#: Keys whose value must be a non-empty ``str``.
_STR_KEYS = frozenset({"id", "role", "workflow", "step", "output_schema", "max_context_policy"})

#: Keys whose value must be a ``list`` of ``str``.
_LIST_KEYS = frozenset({"static_inputs", "dynamic_inputs"})

#: Case-insensitive harness-specific tokens forbidden in a universal fragment body.
#: Each entry is a literal substring matched case-insensitively against the body.
_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "read tool",
    "write tool",
    "edit tool",
    "bash tool",
    "codex exec",
    "pi --mode",
    "pi --model",
    "claude code",
    "claude-code",
    ".claude/",
    ".codex/",
    ".opencode/",
    "--output-last-message",
    "message_end",
    "apply_patch",
    "--ignore-user-config",
)


@dataclass(frozen=True)
class Fragment:
    """A loaded, validated lifecycle fragment."""

    id: str
    role: str
    workflow: str
    step: str
    static_inputs: tuple[str, ...]
    dynamic_inputs: tuple[str, ...]
    output_schema: str
    max_context_policy: str
    body: str
    path: Path


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _default_root() -> Path:
    """Resolve the packaged fragment root inside the wheel/source tree.

    ``loader.py`` lives at ``features/lifecycle/fragments/loader.py``; the fragment
    source lives at ``public/lifecycle_fragments/`` — both under the package root.
    """
    package_root = Path(__file__).resolve().parents[3]
    return package_root / "public" / "lifecycle_fragments"


class FragmentLoader:
    """Load + validate fragments from the projected/packaged location."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else _default_root()

    @property
    def root(self) -> Path:
        return self._root

    # -- discovery -------------------------------------------------------

    def _iter_fragment_paths(self, workflow: str | None = None) -> list[Path]:
        if not self._root.exists():
            raise FragmentNotFoundError(f"Fragment root not found: {self._root}")
        paths: list[Path] = []
        for path in sorted(self._root.rglob("*.md")):
            if path.name == _STUB_NAME:
                continue
            if workflow is not None and path.parent.name != workflow:
                continue
            paths.append(path)
        return paths

    def list_fragments(self, workflow: str | None = None) -> list[Fragment]:
        """Load every fragment (optionally filtered to one *workflow* directory)."""
        return [self._load_path(path) for path in self._iter_fragment_paths(workflow)]

    def list_workflow_dirs(self) -> list[str]:
        """Return the names of every workflow directory under the fragment root."""
        if not self._root.exists():
            raise FragmentNotFoundError(f"Fragment root not found: {self._root}")
        return sorted(p.name for p in self._root.iterdir() if p.is_dir())

    # -- loading ---------------------------------------------------------

    def load_fragment(self, id_or_path: str | Path) -> Fragment:
        """Load a single fragment by its ``id`` (``workflow.step``) or by file path."""
        candidate = Path(id_or_path)
        if candidate.suffix == ".md":
            resolved = candidate if candidate.is_absolute() else (self._root / candidate)
            if not resolved.exists():
                raise FragmentNotFoundError(f"Fragment file not found: {resolved}")
            return self._load_path(resolved)

        target = str(id_or_path)
        for path in self._iter_fragment_paths():
            fragment = self._load_path(path)
            if fragment.id == target:
                return fragment
        raise FragmentNotFoundError(f"No fragment with id '{target}' under {self._root}")

    def validate_all(self) -> list[Fragment]:
        """Load + validate every fragment; raise on the first malformed one."""
        return self.list_fragments()

    # -- parse + validate ------------------------------------------------

    def _load_path(self, path: Path) -> Fragment:
        text = path.read_text(encoding="utf-8")
        meta, body = self._split_frontmatter(text, path)
        self._validate_metadata(meta, path)
        self._lint_body(body, path)
        # _validate_metadata has proven the list keys are list[str].
        static_inputs = meta["static_inputs"]
        dynamic_inputs = meta["dynamic_inputs"]
        assert isinstance(static_inputs, list)
        assert isinstance(dynamic_inputs, list)
        return Fragment(
            id=str(meta["id"]),
            role=str(meta["role"]),
            workflow=str(meta["workflow"]),
            step=str(meta["step"]),
            static_inputs=tuple(str(item) for item in static_inputs),
            dynamic_inputs=tuple(str(item) for item in dynamic_inputs),
            output_schema=str(meta["output_schema"]),
            max_context_policy=str(meta["max_context_policy"]),
            body=body,
            path=path,
        )

    @staticmethod
    def _split_frontmatter(text: str, path: Path) -> tuple[dict[str, object], str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
            raise FragmentValidationError(
                f"{path}: fragment is missing the opening YAML frontmatter delimiter '---'"
            )
        buffer: list[str] = []
        body_start: int | None = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == _FRONTMATTER_DELIM:
                body_start = index + 1
                break
            buffer.append(line)
        if body_start is None:
            raise FragmentValidationError(
                f"{path}: fragment frontmatter is not closed by a second '---' line"
            )
        try:
            parsed = yaml.safe_load("\n".join(buffer))
        except yaml.YAMLError as exc:
            raise FragmentValidationError(f"{path}: invalid YAML frontmatter: {exc}") from exc
        if not isinstance(parsed, dict):
            raise FragmentValidationError(
                f"{path}: fragment frontmatter must be a YAML mapping, got {type(parsed).__name__}"
            )
        body = "\n".join(lines[body_start:]).strip()
        return parsed, body

    @staticmethod
    def _validate_metadata(meta: dict[str, object], path: Path) -> None:
        missing = [key for key in _REQUIRED_KEYS if key not in meta]
        if missing:
            raise FragmentValidationError(
                f"{path}: fragment metadata is missing required key(s): {', '.join(missing)}"
            )
        for key in _STR_KEYS:
            value = meta[key]
            if not isinstance(value, str) or not value.strip():
                raise FragmentValidationError(
                    f"{path}: fragment metadata key '{key}' must be a non-empty string, "
                    f"got {type(value).__name__}"
                )
        for key in _LIST_KEYS:
            value = meta[key]
            if not isinstance(value, list):
                raise FragmentValidationError(
                    f"{path}: fragment metadata key '{key}' must be a list, "
                    f"got {type(value).__name__}"
                )
            for item in value:
                if not isinstance(item, str):
                    raise FragmentValidationError(
                        f"{path}: fragment metadata key '{key}' must contain only strings, "
                        f"found {type(item).__name__}"
                    )

    @staticmethod
    def _lint_body(body: str, path: Path) -> None:
        haystack = body.lower()
        for token in _FORBIDDEN_TOKENS:
            if token in haystack:
                raise FragmentValidationError(
                    f"{path}: fragment body contains harness-specific token '{token}' — "
                    "fragments must read identically across PI, Codex, and Claude workers"
                )


# Module-level convenience: a default loader bound to the packaged fragment root.
_DEFAULT_LOADER = FragmentLoader()


def load_fragment(id_or_path: str | Path) -> Fragment:
    """Load a single fragment from the default (packaged) fragment root."""
    return _DEFAULT_LOADER.load_fragment(id_or_path)


def list_fragments(workflow: str | None = None) -> list[Fragment]:
    """List fragments from the default (packaged) fragment root."""
    return _DEFAULT_LOADER.list_fragments(workflow)


def validate_all() -> list[Fragment]:
    """Validate every fragment under the default (packaged) fragment root."""
    return _DEFAULT_LOADER.validate_all()


_HARNESS_TOKEN_RE = re.compile("|".join(re.escape(t) for t in _FORBIDDEN_TOKENS), re.IGNORECASE)


def forbidden_token_in(text: str) -> str | None:
    """Return the first forbidden harness-specific token found in *text*, else None."""
    match = _HARNESS_TOKEN_RE.search(text)
    return match.group(0) if match else None
