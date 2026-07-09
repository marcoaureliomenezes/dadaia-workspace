"""Derive the implement step's write scope from the reserved TASKS.md task (FR3, v0.1.68).

``pipeline-does-not-derive-write-scope-from-tasks``: the SDD task file already declares
the legal implementation surface once, in its ``Write set:`` bullet, but the pipeline's
``implement`` step ignored it — the operator had to hand-copy every task's write set via
``--write-scope`` on every invocation. :func:`write_scope_from_tasks` resolves the
release's active (``[-]``) task and parses its declared ``Write set:`` globs so
``pipeline.py`` can union them into the implement step's ``allowed_paths`` automatically.
``--write-scope`` remains an additive escape hatch, never a requirement.

Deterministic grammar (SPEC FR3.1 / architect F3):

- **Reserved task:** the task whose marker is ``[-]``. If NOT exactly one ``[-]`` task
  exists across the whole file (zero, or multiple), return ``()`` — never guess.
- **Write-set line:** the ``Write set:`` bullet within that task's block, up to the next
  ``- **``/``###`` bullet or a blank line; a multi-line continuation is joined into one
  logical line before extraction.
- **Glob extraction:** backtick-delimited spans that are *path-shaped* (contain ``/`` or
  a filename extension) AND appear before the first ``(`` on the (joined) line. A
  trailing parenthetical annotation (e.g. ``(new, additive)``,
  ``(`run_implement_review_loop` only)``) is stripped, and any backticks inside it are
  never captured as paths.
- ``none`` (case-insensitive, the whole Write-set value) ⇒ ``()``.
- Absent ``TASKS.md`` / no ``releases/`` dir ⇒ ``()`` — never crashes the pipeline over a
  purely additive-optional derivation.
"""

from __future__ import annotations

import re
from pathlib import Path

_TASK_MARKER_RE = re.compile(r"^###\s.*`\[(?P<marker>[ x-])\]`\s*$")
_BULLET_RE = re.compile(r"^-\s+\*\*(?P<key>[^*]+):\*\*\s*(?P<rest>.*)$")
_NEXT_BLOCK_RE = re.compile(r"^(-\s+\*\*|###)")
_BACKTICK_SPAN_RE = re.compile(r"`([^`]+)`")

_WRITE_SET_KEY = "write set"


def write_scope_from_tasks(specs_dir: Path, release_id: str) -> tuple[str, ...]:
    """Resolve the reserved task's declared ``Write set:`` globs, or ``()``.

    Reads ``<specs_dir>/releases/<release_id>/TASKS.md``. Never raises: any structural
    absence (missing releases dir, missing TASKS.md, no/multiple reserved tasks, an
    unparseable Write-set line) degrades to ``()`` rather than propagating — this
    derivation is additive-optional, never a hard dependency of the pipeline.
    """
    tasks_path = specs_dir / "releases" / release_id / "TASKS.md"
    if not tasks_path.is_file():
        return ()
    text = tasks_path.read_text(encoding="utf-8")
    block = _reserved_task_block(text)
    if block is None:
        return ()
    write_set_line = _write_set_line(block)
    if write_set_line is None:
        return ()
    return _extract_globs(write_set_line)


def _reserved_task_block(text: str) -> str | None:
    """Return the body lines of the single ``[-]`` task's block, or ``None``.

    A "block" is every line from a ``### ... `[-]``` heading up to (but excluding) the
    next ``### `` heading (or end of file). Returns ``None`` unless EXACTLY one task in
    the whole file carries the ``[-]`` marker.
    """
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = _TASK_MARKER_RE.match(line.rstrip())
        if match is not None:
            headings.append((idx, match.group("marker")))

    reserved = [idx for idx, marker in headings if marker == "-"]
    if len(reserved) != 1:
        return None

    start = reserved[0]
    heading_starts = sorted(idx for idx, _marker in headings)
    later = [idx for idx in heading_starts if idx > start]
    end = later[0] if later else len(lines)
    return "\n".join(lines[start + 1 : end])


def _write_set_line(block: str) -> str | None:
    """Extract the (possibly multi-line-joined) ``Write set:`` bullet value from *block*.

    Starts at the ``- **Write set:**`` bullet and joins subsequent lines until the next
    ``- **``/``###`` bullet or a blank line is reached.
    """
    lines = block.splitlines()
    start_idx: int | None = None
    first_rest = ""
    for idx, line in enumerate(lines):
        match = _BULLET_RE.match(line.strip())
        if match is not None and match.group("key").strip().lower() == _WRITE_SET_KEY:
            start_idx = idx
            first_rest = match.group("rest")
            break
    if start_idx is None:
        return None

    parts = [first_rest]
    for line in lines[start_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            break
        if _NEXT_BLOCK_RE.match(stripped):
            break
        parts.append(stripped)
    return " ".join(parts).strip()


def _extract_globs(write_set_line: str) -> tuple[str, ...]:
    """Apply the glob-extraction grammar to one joined ``Write set:`` value."""
    if write_set_line.strip().lower() == "none":
        return ()

    # Only consider content before the first '(' — a trailing parenthetical annotation
    # (and any backticks inside it) is never part of the glob list.
    head = write_set_line.split("(", 1)[0]

    globs: list[str] = []
    for span in _BACKTICK_SPAN_RE.findall(head):
        candidate = span.strip()
        if not candidate:
            continue
        if _is_path_shaped(candidate):
            globs.append(candidate)
    return tuple(globs)


def _is_path_shaped(candidate: str) -> bool:
    """A candidate is path-shaped iff it contains a ``/`` or a filename extension.

    A bare function/flag name like `` `some_func` `` or `` `--write-scope` `` has
    neither and is correctly rejected; a bare filename like `` `pyproject.toml` `` has
    an extension (dot with a non-empty stem and a non-empty, alphanumeric suffix) and
    is accepted.
    """
    if "/" in candidate:
        return True
    name, _dot, ext = candidate.rpartition(".")
    return bool(name) and bool(ext) and ext.isalnum()
