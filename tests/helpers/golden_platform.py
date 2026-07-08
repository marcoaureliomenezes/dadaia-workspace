"""Shared platform-invariance normalization layer for byte-golden capture (v0.1.64 FR1).

One module, one truth: every byte-golden test normalizes its capture through these
pure functions so a new golden is cross-platform-stable **by construction** instead of
re-discovering the leak classes below file by file. Consolidates the local helper
copies that previously lived in 13 test files (5 golden-trio sites + 8 ``_norm_stderr``
sites) byte-identically — adoption changed **zero** golden bytes (v0.1.64 AC-1).

Leak-class taxonomy (why each function exists)
----------------------------------------------
The classes were paid for in blood during the v0.1.58 three-round CI golden saga
(commits ``60f42904``, ``c02e74f6``, ``1dadfafe`` — three consecutive GHA-only golden
failures after two local-green runs):

1. **host-state** — output depends on state the host happens to carry, not on the
   projection behaviour under test. Example: ``privacy_check`` walks up from cwd for an
   operator denylist, so a developer workspace emits the bare ``[ok] public-privacy``
   marker while a fresh CI checkout emits the ``(baseline structural scan, no operator
   denylist)`` variant. → :func:`norm_path_line` canonicalizes both to the bare marker;
   :func:`is_env_doctor_line` excludes live source-repo ``git-dirty`` lines entirely.
2. **iteration-order** — directory-iteration order differs across OSes (Windows yielded
   ``pi/extensions/*`` before ``pi/SYSTEM.md`` where Linux sorted the reverse) and is
   not a product contract. → :func:`sort_line_lists` locks the exact MULTISET of lines
   per key (order-insensitive, count-preserving).
3. **OS-phrase** — probes that EXECUTE something report the host OS's wording (POSIX
   ``exited 127 ... missing executable``; Windows ``[WinError 193]``). The invariant is
   *that the probe errored for that wrapper*, not the OS's words. →
   :func:`canon_env_line` (the D-CX-9 wrapper regex).
4. **path-version** — absolute fixture roots and ``os.sep`` leak machine identity into
   plain-text and JSON-escaped output. → :func:`norm_path_line` /
   :func:`norm_panel_body` scrub the workspace root to ``<WS>`` and canonicalize
   separators (the v0.1.55 platform-invariant law).
5. **clock** — ``datetime.now`` timestamps differ per run. → :func:`norm_panel_body`
   replaces every ISO-8601 timestamp with ``<TS>``.
6. **Rich-width** — Typer/Rich renders usage errors with ANSI colour + a box wrapped at
   an env-dependent terminal width, splitting asserted substrings across borders on CI
   while staying plain locally (the v0.1.57 QA-atom law). → :func:`norm_stderr`.

Regen discipline: :func:`assert_golden` regenerates a golden ONLY under its update env
flag (default ``UPDATE_INSTALL_GOLDENS``). A byte diff without that flag is a behaviour
regression — fix the consumer, never the golden.

Pure functions, stdlib-only (``re``/``json``/``os``/``pathlib`` + ``pytest.skip`` for
the deliberate-regen path). No fixtures live here.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

__all__ = [
    "assert_golden",
    "canon_env_line",
    "is_env_doctor_line",
    "norm_panel_body",
    "norm_path_line",
    "norm_stderr",
    "sort_line_lists",
]

# Any ISO-8601 timestamp (with or without fractional seconds / offset / Z).
_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")

# The D-CX-9 probe EXECUTES the codex hook wrapper, so its error text is OS-phrased.
_DCX9_WRAPPER_RE = re.compile(
    r"^\[error\] codex hook wrapper .*? (\.dadaia/hooks/\S+?):.*\(D-CX-9\)$"
)

# ANSI colour escapes emitted by Rich when it detects (or is forced into) a colour tty.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# The narrow Rich box-glyph set replaced character-by-character (the 7-site variant).
_BOX_CHARS = "│╭╮╰╯─"

# The wide glyph range (box-drawing block + smart quotes) replaced by regex (the
# ``test_lifecycle_policy_cli`` variant).
_WIDE_GLYPH_RE = re.compile(r"[─-╿‘’“”]")


def norm_path_line(line: str, ws: Path) -> str:
    """Normalize a plain-text install/doctor line (leak classes 1 + 4).

    Strips the fixture workspace root to ``<WS>`` (both ``as_posix`` and native-``str``
    forms), canonicalizes ``os.sep`` to ``/``, and canonicalizes the HOST-dependent
    public-privacy ok-marker: ``privacy_check`` resolves the operator denylist by
    walking up from cwd, so a workspace with ``.dadaia/states/privacy_denylist.json``
    emits the bare marker while a fresh checkout (CI) emits the "(baseline structural
    scan, no operator denylist)" variant. Both normalize to the bare marker — same
    rationale as the git-dirty exclusion in :func:`is_env_doctor_line`.
    """
    out = line.replace(ws.as_posix(), "<WS>").replace(str(ws), "<WS>")
    out = out.replace(
        "[ok] public-privacy (baseline structural scan, no operator denylist)",
        "[ok] public-privacy",
    )
    return out.replace("\\", "/")


def norm_panel_body(body: bytes, ws: Path) -> str:
    """Normalize a panel JSON body (leak classes 4 + 5).

    Strips the fixture root in plain, posix, and JSON-escaped forms to ``<WS>`` and
    replaces every ISO-8601 timestamp with ``<TS>`` (panel endpoints stamp
    ``generated_at`` with ``datetime.now``).
    """
    text = body.decode("utf-8")
    ws_escaped = json.dumps(str(ws))[1:-1]
    text = text.replace(ws.as_posix(), "<WS>").replace(ws_escaped, "<WS>").replace(str(ws), "<WS>")
    return _TS_RE.sub("<TS>", text)


def is_env_doctor_line(line: str) -> bool:
    """True for a doctor line whose content is environmental, not behaviour (leak class 1).

    The doctor ``git-dirty`` lines reference the LIVE source-repo working tree (not the
    fixture) and vary between capture and replay — exclude them from goldens.
    """
    return "git-dirty" in line


def canon_env_line(line: str) -> str:
    """Canonicalize OS-dependent doctor probe text (leak class 3 — the D-CX-9 wrapper).

    The D-CX-9 probe EXECUTES the codex hook wrapper, so its error text is the host
    OS's phrasing (POSIX: "exited 127 ... missing executable .../python"; Windows:
    "launch failed ... [WinError 193] ..."). The invariant is that the probe errored
    for that wrapper — not the OS's words. Keep the wrapper path, canonicalize the
    reason.
    """
    return _DCX9_WRAPPER_RE.sub(r"[error] codex hook wrapper probe failed \1 (D-CX-9)", line)


def sort_line_lists(obj: object) -> object:
    """Sort every list-of-strings in the captured object (leak class 2 — dir order).

    Directory-iteration order differs across OSes and is not a product contract. The
    golden locks the exact MULTISET of lines per key — order-insensitive,
    count-preserving. String lines are additionally canonicalized for OS-dependent
    probe text (:func:`canon_env_line`).
    """
    if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
        return sorted(canon_env_line(x) for x in obj)
    if isinstance(obj, dict):
        return {k: sort_line_lists(v) for k, v in obj.items()}
    return obj


def assert_golden(
    path: Path,
    obj: object,
    what: str,
    *,
    update_env: str | None = "UPDATE_INSTALL_GOLDENS",
    message: str | None = None,
) -> None:
    """Compare ``obj`` against the committed golden at ``path`` (regen discipline).

    Both sides pass through :func:`sort_line_lists`; serialization is
    ``json.dumps(..., indent=2, ensure_ascii=False, sort_keys=True)`` + trailing
    newline. When the ``update_env`` env var is set, the golden is regenerated and the
    test skips — deliberate, reviewed regens only. Pass ``update_env=None`` for a
    reproduction site that must NEVER regenerate the golden it borrows (e.g. the e2e
    reproduction of an integration-owned golden). ``message`` overrides the default
    divergence message; ``what`` always names the golden.
    """
    current_obj = sort_line_lists(obj)
    current = json.dumps(current_obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if update_env is not None and os.environ.get(update_env):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(current, encoding="utf-8")
        pytest.skip(f"regenerated {what} golden ({update_env} set)")
    golden = (
        json.dumps(
            sort_line_lists(json.loads(path.read_text(encoding="utf-8"))),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )
    assert current == golden, message or (
        f"{what} diverged from the committed golden — the change altered observable "
        "behaviour. Fix the consumer, never the golden."
    )


def norm_stderr(output: str, *, wide_glyphs: bool = False) -> str:
    """Width-independent normalization of Typer/Rich error output (leak class 6).

    On CI Rich renders the usage error with ANSI colour + a box wrapped at an
    env-dependent width, splitting asserted substrings across borders; locally
    (non-tty) it stays plain. Strip ANSI + box glyphs, collapse whitespace so a
    substring assert holds on any terminal width (the v0.1.57 QA-atom law).

    ``wide_glyphs=False`` (default) reproduces the 7-site character-set variant:
    replace ``│╭╮╰╯─`` with spaces, then ``re.sub(r"\\s+", " ", ...)`` (edge whitespace
    collapses to a single space, not stripped). ``wide_glyphs=True`` reproduces the
    ``test_lifecycle_policy_cli`` variant: replace the whole box-drawing block plus
    smart quotes by regex, then ``" ".join(text.split())`` (stripped).
    """
    text = _ANSI_RE.sub("", output)
    if wide_glyphs:
        text = _WIDE_GLYPH_RE.sub(" ", text)
        return " ".join(text.split())
    text = "".join(" " if ch in _BOX_CHARS else ch for ch in text)
    return re.sub(r"\s+", " ", text)
