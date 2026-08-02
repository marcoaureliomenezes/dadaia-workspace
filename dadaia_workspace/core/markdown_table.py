"""Read one Markdown table row into its cells.

Bug ``r24-live-definition-draft-fails-validation-table``: the validation dependency
table asks each workstream for its *direct validation command*, and the live worker
answered honestly with ``rg -n "a|b|c" README.md``. Splitting the row on every ``|``
shattered that one cell into three, the lint counted seven cells instead of five, and
reported "every row must contain all five non-empty cells" — a statement that was
false, since not one cell was empty. The worker rewrote the same correct table, got the
same false diagnostic, and the release deadlocked at ``definition_draft``.

A cell is therefore read with two pipes that do not delimit:

* ``\\|`` — the escape GFM itself defines;
* a pipe inside an inline code span.

The second is a deliberate reading, not an oversight. Strict GFM does split code spans
on pipes and asks authors to write ``\\|`` even inside backticks. That rule is not one
authors follow, and the column in question exists to hold shell commands, which contain
pipes. Enforcing it bought nothing and cost a release that could not be unblocked. A
code span is opaque here, which is the only reading under which the gate measures what
it says it measures.

An unterminated backtick run is not a code span at all — it is literal text — so the
scan falls back to escape-aware splitting rather than silently swallowing the rest of
the row into one cell.
"""

from __future__ import annotations

_BACKTICK = "`"
_PIPE = "|"


def _ends_with_delimiter(line: str) -> bool:
    """True when the final ``|`` closes the row rather than being escaped into it."""
    if not line.endswith(_PIPE):
        return False
    backslashes = len(line) - 1 - len(line[:-1].rstrip("\\"))
    return backslashes % 2 == 0


def _trim_delimiters(raw: str) -> str:
    line = raw.strip()
    if line.startswith(_PIPE):
        line = line[1:]
    if _ends_with_delimiter(line):
        line = line[:-1]
    return line


def _split_escaped_only(line: str) -> list[str]:
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line) and line[index + 1] == _PIPE:
            current.append(_PIPE)
            index += 2
            continue
        if char == _PIPE:
            cells.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current).strip())
    return cells


def split_row(raw: str) -> list[str]:
    """Split one table row into its cells, honouring escapes and inline code spans."""
    line = _trim_delimiters(raw)

    cells: list[str] = []
    current: list[str] = []
    fence = 0  # length of the open code-span backtick run; 0 when outside a span
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line) and line[index + 1] == _PIPE:
            current.append(_PIPE)
            index += 2
            continue
        if char == _BACKTICK:
            run = 0
            while index + run < len(line) and line[index + run] == _BACKTICK:
                run += 1
            if fence == 0:
                fence = run
            elif fence == run:
                fence = 0
            current.append(_BACKTICK * run)
            index += run
            continue
        if char == _PIPE and fence == 0:
            cells.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1

    if fence != 0:
        # The span never closed, so those backticks were literal text. Reading the rest
        # of the row as one cell would invent a merged cell nobody wrote.
        return _split_escaped_only(line)

    cells.append("".join(current).strip())
    return cells
