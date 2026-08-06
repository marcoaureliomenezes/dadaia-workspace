"""Derive the implement step's write scope from the reserved TASKS.md task (FR3, v0.1.68).

``pipeline-does-not-derive-write-scope-from-tasks``: the SDD task file already declares
the legal implementation surface once, in its ``Write set:`` bullet, but the pipeline's
``implement`` step ignored it — the operator had to hand-copy every task's write set via
``--write-scope`` on every invocation. :func:`write_scope_from_tasks` resolves the
release's active (``[-]``) task and parses its declared ``Write set:`` globs so
``pipeline.py`` can union them into the implement step's ``allowed_paths`` automatically.
``--write-scope`` remains an additive escape hatch, never a requirement.

Deterministic grammar (SPEC FR3.1 / architect F3; v0.1.71 FR1 — real consumer grammar):

Two task grammars occur in real repos and BOTH are supported:

- **Internal grammar** (this library's own releases): a ``### … `[-]``` H3 heading with
  the marker inline, and a bold ``- **Write set:**`` key.
- **Consumer grammar** (e.g. sample-consumer): a **bold** ``**T-3.1 — …**`` task heading
  whose active marker lives in a **fenced block** ```` ```\n[-] T-3.1\n``` ```` elsewhere
  in the file, and a **plain** ``- Write set:`` key.

Common rules:

- **Reserved task:** the single task whose marker is ``[-]`` (inline in an H3 heading OR a
  standalone ``[-] T-x`` marker line). If NOT exactly one ``[-]`` exists across the whole
  file (zero, or multiple), return ``()`` — never guess.
- **Write-set line:** the ``Write set:`` bullet (bold or plain key) within that task's
  block, up to the next bullet / heading / blank line; a multi-line continuation is joined
  into one logical line before extraction.
- **Glob extraction:** every backtick-delimited span that is *path-shaped* (contains ``/``
  or a filename extension), AFTER masking out every parenthetical annotation — per path,
  wherever it occurs (``(new)``, ``(reuse — no change)``, ``(`func` only)``). Annotations
  are NOT terminators, so per-path parentheticals never truncate the remaining paths, and
  a backtick token inside a parenthetical is never captured as a path.
- ``none`` (case-insensitive, the whole Write-set value) ⇒ ``()``.
- Absent ``TASKS.md`` / no ``releases/`` dir ⇒ ``()`` — never crashes the pipeline over a
  purely additive-optional derivation.
"""

from __future__ import annotations

import re
from pathlib import Path

# An H3 task heading (internal grammar). The inline marker, if present, is any single
# ``[ x-]`` bracket in the heading (with or without surrounding backticks): both
# ``### T-1 — … `[-]``` and ``### [-] T-1 — …`` are recognized.
_H3_HEADING_RE = re.compile(r"^###\s+\S")
# A bold task heading (consumer grammar): ``**T-3.1 — …**`` — the closing ``**`` need not
# be at end-of-line (a trailing ``(HOP-…)`` annotation may follow outside the bold span).
_BOLD_HEADING_RE = re.compile(r"^\*\*\s*(?P<id>T-[0-9][0-9A-Za-z.\-]*)\b.*?\*\*")
# A standalone marker line (consumer grammar), e.g. inside a fenced block: ``[-] T-3.1``.
_STANDALONE_MARKER_RE = re.compile(r"^\[(?P<marker>[ x-])\]\s+(?P<id>T-[0-9][0-9A-Za-z.\-]*)\s*$")
# Any ``[ x-]`` marker bracket appearing inline in a heading (optional backticks).
_INLINE_MARKER_RE = re.compile(r"`?\[(?P<marker>[ x-])\]`?")
# Any markdown heading (``#``..``######``) — a block boundary regardless of task-ness.
_ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
# A checklist-bullet task heading (the engine's OWN release_definition ``tasks_create``
# output — bug write-scope-parser-blind-to-own-tasks-create-checklist-grammar):
# ``- [-] **T-MB-01 — title**`` at column 0, marker inline, sub-bullets indented below.
_CHECKLIST_HEADING_RE = re.compile(r"^-\s+\[(?P<marker>[ x-])\]\s+\S")

_BULLET_RE = re.compile(
    r"^-\s+(?:\*\*(?P<bkey>[^*]+):\*\*|(?P<pkey>[A-Za-z][\w ]*?):)\s*(?P<rest>.*)$"
)
_BACKTICK_SPAN_RE = re.compile(r"`([^`]+)`")
_PARENTHETICAL_RE = re.compile(r"\([^()]*\)")

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


def write_scope_from_release_tasks(specs_dir: Path, release_id: str) -> tuple[str, ...]:
    """Return the stable union of write sets for every incomplete release task.

    ``implementation_reviews`` is a release-scoped workflow: its implementation worker
    executes the approved task set in dependency order before the release-wide reviews
    and closure. Open and reserved tasks therefore contribute scope; completed tasks do
    not. The narrower :func:`write_scope_from_tasks` remains available for task-scoped
    callers that require exactly one reservation.
    """
    tasks_path = specs_dir / "releases" / release_id / "TASKS.md"
    if not tasks_path.is_file():
        return ()
    globs: list[str] = []
    seen: set[str] = set()

    def _add(path: str) -> None:
        if path not in seen:
            seen.add(path)
            globs.append(path)

    for block in _incomplete_task_blocks(tasks_path.read_text(encoding="utf-8")):
        value = _write_set_line(block)
        if value is None:
            continue
        for path in _extract_globs(value):
            _add(path)
            # Bug implementation-write-scope-omits-declared-python-module-entrypoint:
            # a write set naming FILES denied creating sibling files the contract
            # itself requires (src/<pkg>/__main__.py next to src/<pkg>/cli.py). A file
            # path also contributes its parent-directory glob — the declared zone is
            # the directory, not the single filename; explicit globs pass unchanged.
            if "*" not in path and "/" in path and "." in path.rsplit("/", 1)[-1]:
                parent, filename = path.rsplit("/", 1)
                parent_glob = parent + "/**"
                # NEVER emit a repo-wide (repos/<slug>/**) or workspace-wide glob —
                # the prompt-scope security guard forbids them (they would grant
                # specs/ writes; bug implementation-prompt-scope-rejects-repo-glob).
                segments = parent.split("/")
                repo_wide = parent == "" or (len(segments) == 2 and segments[0] == "repos")
                if not repo_wide:
                    _add(parent_glob)
                elif "." in filename:
                    # Root-level file: allow same-extension siblings only.
                    _add(f"{parent}/*.{filename.rsplit('.', 1)[-1]}")
    return tuple(globs)


def _incomplete_task_blocks(text: str) -> tuple[str, ...]:
    """Extract body blocks for ``[ ]`` and ``[-]`` tasks in every supported grammar."""
    lines = text.splitlines()
    boundaries: list[int] = []
    task_markers: dict[int, str] = {}
    bold_ids: dict[str, int] = {}
    standalone_markers: dict[str, str] = {}

    for idx, raw in enumerate(lines):
        line = raw.rstrip()
        standalone = _STANDALONE_MARKER_RE.match(line.strip())
        if standalone is not None:
            standalone_markers[standalone.group("id")] = standalone.group("marker")
        checklist = _CHECKLIST_HEADING_RE.match(line)
        if checklist is not None:
            boundaries.append(idx)
            task_markers[idx] = checklist.group("marker")
            continue
        if _H3_HEADING_RE.match(line):
            boundaries.append(idx)
            markers = _INLINE_MARKER_RE.findall(line)
            if len(markers) == 1:
                task_markers[idx] = markers[0]
            continue
        if _ANY_HEADING_RE.match(line):
            boundaries.append(idx)
            continue
        bold = _BOLD_HEADING_RE.match(line)
        if bold is not None:
            boundaries.append(idx)
            bold_ids[bold.group("id")] = idx

    for task_id, marker in standalone_markers.items():
        bold_idx = bold_ids.get(task_id)
        if bold_idx is not None:
            task_markers[bold_idx] = marker

    ordered = sorted(set(boundaries))
    blocks: list[str] = []
    for start, marker in sorted(task_markers.items()):
        if marker == "x":
            continue
        end = next((idx for idx in ordered if idx > start), len(lines))
        blocks.append("\n".join(lines[start + 1 : end]))
    return tuple(blocks)


def _reserved_task_block(text: str) -> str | None:
    """Return the body lines of the single ``[-]`` task's block, or ``None``.

    Handles both grammars (see module docstring). A "block" is every line from the
    reserved task's heading up to (but excluding) the next markdown/bold-task heading (or
    end of file). Returns ``None`` unless EXACTLY one task in the whole file carries the
    ``[-]`` marker — whether inline in an H3 heading or in a standalone ``[-] T-x`` line.
    """
    lines = text.splitlines()

    # All heading line indices (block boundaries) and, for bold headings, their task id.
    heading_idxs: list[int] = []
    bold_id_to_idx: dict[str, int] = {}
    # Reserved tasks found via an inline H3 marker: their heading line index.
    inline_reserved: list[int] = []

    for idx, raw in enumerate(lines):
        line = raw.rstrip()
        if _H3_HEADING_RE.match(line):
            heading_idxs.append(idx)
            markers = _INLINE_MARKER_RE.findall(line)
            # Exactly one marker bracket in the heading ⇒ that is the task's marker.
            if len(markers) == 1 and markers[0] == "-":
                inline_reserved.append(idx)
        elif _ANY_HEADING_RE.match(line):
            heading_idxs.append(idx)
        elif _CHECKLIST_HEADING_RE.match(line):
            # Checklist grammar: the column-0 ``- [m] …`` bullet is itself the task
            # heading (block boundary); its marker is inline. Indented sub-bullets
            # below it stay inside the block.
            checklist = _CHECKLIST_HEADING_RE.match(line)
            assert checklist is not None
            heading_idxs.append(idx)
            if checklist.group("marker") == "-":
                inline_reserved.append(idx)
        else:
            bold = _BOLD_HEADING_RE.match(line)
            if bold is not None:
                heading_idxs.append(idx)
                bold_id_to_idx.setdefault(bold.group("id"), idx)

    # Reserved tasks found via a standalone ``[-] T-x`` marker line (consumer grammar).
    standalone_reserved_ids = [
        m.group("id")
        for m in (_STANDALONE_MARKER_RE.match(raw.strip()) for raw in lines)
        if m is not None and m.group("marker") == "-"
    ]

    starts: list[int] = list(inline_reserved)
    for task_id in standalone_reserved_ids:
        heading_idx = bold_id_to_idx.get(task_id)
        if heading_idx is not None:
            starts.append(heading_idx)

    if len(starts) != 1:
        return None

    start = starts[0]
    later = [idx for idx in sorted(heading_idxs) if idx > start]
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
    key_indent = 0
    for idx, line in enumerate(lines):
        match = _BULLET_RE.match(line.strip())
        if match is None:
            continue
        key = match.group("bkey") or match.group("pkey") or ""
        if key.strip().lower() == _WRITE_SET_KEY:
            start_idx = idx
            first_rest = match.group("rest")
            key_indent = len(line) - len(line.lstrip())
            break
    if start_idx is None:
        # Third real grammar (bug write-scope-parser-rejects-own-tasks-grammar — the
        # engine's OWN tasks_create output): a standalone bold/plain ``Write set:``
        # paragraph followed by (blank line +) a bullet list of backticked paths.
        return _standalone_key_write_set(lines)

    parts = [first_rest]
    for line in lines[start_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            if any(part.strip() for part in parts):
                break
            continue
        indent = len(line) - len(line.lstrip())
        # Sibling bullets end the property. More-indented bullets are the generated
        # grammar's path list and belong to the Write set value.
        if stripped.startswith("- ") and indent <= key_indent:
            break
        if _ANY_HEADING_RE.match(stripped) or _BOLD_HEADING_RE.match(stripped):
            break
        parts.append(stripped)
    return " ".join(parts).strip()


def _extract_globs(write_set_line: str) -> tuple[str, ...]:
    """Apply the glob-extraction grammar to one joined ``Write set:`` value."""
    if write_set_line.strip().lower() == "none":
        return ()

    # Mask EVERY parenthetical annotation (and any backticks inside it) — per path,
    # wherever it occurs. A ``(new)`` / ``(reuse — no change)`` after path #1 must not
    # truncate the remaining paths (the old ``split('(', 1)[0]`` bug), and a ``(`func`
    # only)`` annotation must not surface ``func`` as a path.
    masked = _PARENTHETICAL_RE.sub(" ", write_set_line)

    globs: list[str] = []
    for span in _BACKTICK_SPAN_RE.findall(masked):
        candidate = span.strip()
        if not candidate:
            continue
        if _is_path_shaped(candidate) and _is_traversal_safe(candidate):
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


def _is_traversal_safe(candidate: str) -> bool:
    """v0.1.78 T-E / FR-E: reject at parse time a token that is absolute (leading ``/``),
    contains a ``..`` path segment, or contains a ``~``/``$`` token anywhere in the path.

    Defense-in-depth (absorbed backlog ``tasks-write-scope-traversal-hardening``): inert
    today because ``allowed_paths`` only feeds the ADVISORY scope check
    (``core/scope_match.py``), but the parser must not silently widen scope if matching
    ever gains real glob semantics. A rejected token maps to NO captured glob — this never
    raises (the derivation stays additive-optional / never-crash). ``~``/``$`` are checked
    per path segment (not just a leading anchor): a legitimate repo path never contains
    either, so ``foo/~/bar.py`` or ``foo/$USER/bar.py`` are rejected exactly like a
    leading ``~/secrets.env`` or ``$HOME/.ssh/id_rsa``.
    """
    if candidate.startswith("/"):
        return False
    if "$" in candidate:
        return False
    return not any(segment == ".." or segment.startswith("~") for segment in candidate.split("/"))


_STANDALONE_KEY_RE = re.compile(r"^(?:\*\*)?write set:(?:\*\*)?\s*$", re.IGNORECASE)


def _standalone_key_write_set(lines: list[str]) -> str | None:
    """Value of a standalone ``**Write set:**`` paragraph (third real grammar).

    The key sits on its own line; the value is the following bullet list (blank lines
    between key and list tolerated), joined into one logical line. Stops at the first
    non-bullet non-blank line after the list has started. Returns ``None`` when the key
    is absent or the list is empty.
    """
    key_idx: int | None = None
    for idx, line in enumerate(lines):
        if _STANDALONE_KEY_RE.match(line.strip()):
            key_idx = idx
            break
    if key_idx is None:
        return None
    parts: list[str] = []
    for line in lines[key_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            if parts:
                break
            continue
        if not stripped.startswith("- "):
            break
        parts.append(stripped[2:].strip())
    if not parts:
        return None
    return " ".join(parts).strip()
