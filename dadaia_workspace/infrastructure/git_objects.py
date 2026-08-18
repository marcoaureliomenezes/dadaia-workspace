"""GitSubprocessObjectReader — the ``GitObjectReader`` adapter for the push-range scan.

Implements ``core.protocols.git_object_reader.GitObjectReader`` over ``git rev-list
--objects`` + ``git cat-file`` (SPEC v0.9.0 FR1). Kept in a sibling file to
``git_subprocess.py`` rather than grown inside it — the two modules serve different
concerns (workspace-management git operations vs. the push-range object reader) and
``git_subprocess.py`` is already close to the size that would warrant a split
(PLAN v0.9.0 §2).

Every subprocess invocation in this module — including the batch calls that need
``input=`` — is routed through :func:`_run` so a timeout or a missing ``git`` executable
always surfaces as :class:`GitObjectReadError` (SPEC v0.9.0 FR6 row 2 / the port's own
contract, ``core/protocols/git_object_reader.py``: "Any git failure raises
GitObjectReadError rather than returning a partial/empty result") — never a raw,
unhandled exception at the push boundary (code-reviewer MEDIUM finding).
"""

from __future__ import annotations

import contextlib
import queue
import re
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

from dadaia_workspace.core.protocols.git_object_reader import (
    ZERO_SHA,
    GitObjectReadError,
    ScannedObject,
)

_TIMEOUT_S = 30

#: FR7/A7.4 (v0.11.0) — the same sha-shape check the service layer's
#: ``parse_push_stdin`` applies (40-char SHA-1 or 64-char SHA-256 hex). Re-checked here
#: as a second, independent layer: this adapter must never interpolate an
#: option-shaped string into a git argv, regardless of what already validated the
#: caller's input (CWE-88).
_SHA_SHAPE_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")

#: SPEC v0.9.0 R3 — a per-blob size guard so one pathological blob cannot dominate the
#: scan's wall clock or memory: a blob at or under this cap is read and decoded; a blob
#: over it is never fetched at all and is reported ``decodable=False`` (counted the same
#: way an undecodable binary blob is, FR6 row 3).
_MAX_BLOB_BYTES = 5 * 1024 * 1024  # 5 MB

#: SPEC v0.11.0 FR9/ADR D8 — the ``git cat-file --batch`` conversation is chunked so the
#: peak resident set is bounded by a CONSTANT (``chunk_size x cap``) rather than growing
#: with the size of the pushed range. 500 is the code-reviewer's suggested size and the
#: PLAN's recorded default (PLAN §5) — a measured rationale, not a tunable a test may
#: depend on the exact value of. FR2's prior-side lookup (T-110-09) rides the SAME chunk
#: loop, doubling the bound to ``chunk_size x cap x 2`` rather than adding a second,
#: unbounded pass.
_BATCH_CHUNK_SIZE = 500

#: v0.4.3 T-043-15/FR11 — synthetic, non-path labels for a commit/tag BODY object
#: (never a real repo-relative path — there is nothing to key an amnesty lookup on).
_COMMIT_BODY_PATH = "(commit message)"
_TAG_BODY_PATH = "(tag message)"


def _run(
    args: list[str], cwd: Path, *, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run a git subcommand, capturing raw bytes (never ``text=True`` — decoding is the
    caller's job, and content bytes may not be valid UTF-8 at all).

    ``input_bytes``, when given, is piped to stdin — the shape the batch commands need
    (``git cat-file --batch[-check]`` reads one object id per line from stdin). Every
    call site in this module goes through here so a timeout or missing-``git`` failure
    is always converted to the typed :class:`GitObjectReadError`, never left to escape
    as a raw ``subprocess`` exception.
    """
    try:
        return subprocess.run(
            args, cwd=cwd, input=input_bytes, capture_output=True, timeout=_TIMEOUT_S
        )
    except FileNotFoundError as exc:
        raise GitObjectReadError(f"git is not available on PATH: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitObjectReadError(f"git command timed out: {' '.join(args)}") from exc


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _is_resolvable_commit(repo: Path, sha: str) -> bool:
    """True when *sha* resolves to a commit object reachable locally (FR1 row 1/2).

    v0.11.0 FR7/A7.4: *sha* is shape-checked against :data:`_SHA_SHAPE_RE` BEFORE it is
    ever interpolated into the ``git cat-file -e <sha>^{commit}`` argv — an
    option-shaped value (e.g. ``--upload-pack=...``) is rejected here, never
    interpolated, and the caller treats it as unresolvable (falls back to the
    ``--not --remotes`` range shape) rather than spawning git with that string
    embedded (CWE-88).
    """
    if not sha or sha == ZERO_SHA or not _SHA_SHAPE_RE.match(sha):
        return False
    result = _run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], repo)
    return result.returncode == 0


def _rev_list_candidates(repo: Path, local_sha: str, base: str | None) -> list[tuple[str, str]]:
    """Return ``(sha, path)`` pairs for every object with a path in the FR1 range —
    blobs AND trees (type filtering happens separately, in :func:`_blob_info`).

    *base* is the ALREADY-RESOLVED base (SPEC v0.11.0 FR2 — ``None`` means the
    fallback shape): resolution happens ONCE, in :meth:`GitSubprocessObjectReader.new_objects`,
    and is reused here AND for the prior-side lookup, rather than being re-derived.

    v0.11.0 FR7/A7.4: the argv carries a trailing ``--`` end-of-options marker after
    the revision arguments on both range shapes, closing the git argv interpolation
    site (CWE-88/CWE-20).
    """
    if base is not None:
        args = ["git", "rev-list", "--objects", local_sha, "--not", base, "--"]
    else:
        args = ["git", "rev-list", "--objects", local_sha, "--not", "--remotes", "--"]
    result = _run(args, repo)
    if result.returncode != 0:
        raise GitObjectReadError(f"git rev-list --objects failed: {_decode(result.stderr).strip()}")
    entries: list[tuple[str, str]] = []
    for raw_line in _decode(result.stdout).splitlines():
        if not raw_line:
            continue
        sha, _, path = raw_line.partition(" ")
        if path:
            entries.append((sha, path))
    return entries


def _range_commit_shas(repo: Path, local_sha: str, base: str | None) -> list[str]:
    """Return every COMMIT sha in the FR1 range (never ``--objects`` — commits only),
    the SAME range shape :func:`_rev_list_candidates` walks, reused here so the two
    callers agree on what "the range" means without either re-deriving it.

    Commit count is bounded by the number of commits actually being pushed (an
    ordinary push is a handful; this module's own ``commits_in_range`` metric on this
    repository's v0.4.2 delta was 34) — orders of magnitude fewer than the object count
    the SAME range's ``--objects`` walk produces, which is what keeps
    :func:`_multi_path_shas`'s per-commit ``git ls-tree`` loop below affordable.
    """
    if base is not None:
        args = ["git", "rev-list", local_sha, "--not", base, "--"]
    else:
        args = ["git", "rev-list", local_sha, "--not", "--remotes", "--"]
    result = _run(args, repo)
    if result.returncode != 0:
        raise GitObjectReadError(f"git rev-list failed: {_decode(result.stderr).strip()}")
    return [line for line in _decode(result.stdout).splitlines() if line]


def _is_annotated_tag(repo: Path, sha: str) -> bool:
    """True iff *sha* names an ANNOTATED tag object (v0.4.3 T-043-15/FR11/A11.3).

    A lightweight tag is not an object at all — its ref points directly at a commit, so
    ``local_sha`` would already BE that commit sha and this correctly returns False (no
    separate tag body exists to scan). Shape-checked BEFORE interpolation into the
    ``git cat-file -t`` argv, mirroring :func:`_is_resolvable_commit` (CWE-88).
    """
    if not sha or sha == ZERO_SHA or not _SHA_SHAPE_RE.match(sha):
        return False
    result = _run(["git", "cat-file", "-t", sha], repo)
    return result.returncode == 0 and _decode(result.stdout).strip() == "tag"


def _split_object_body(raw: bytes) -> bytes:
    """Return *raw*'s message BODY only — everything after the first blank-line
    header/body separator of a raw commit or annotated-tag object (v0.4.3
    T-043-15/FR11/A11.6).

    A commit object is ``tree/parent/author/committer[/gpgsig]`` header lines, a blank
    line, then the free-form message; an annotated tag object is
    ``object/type/tag/tagger`` header lines, a blank line, then the free-form message.
    Both shapes share the SAME blank-line boundary, so one splitter serves both. A
    ``gpgsig`` header's own body is multi-line but every continuation line is prefixed
    with a single space (never blank), so the FIRST ``b"\\n\\n"`` is always the true
    header/body boundary — the ``author``/``committer``/``tagger`` header lines (and any
    ``gpgsig``) are structurally excluded from the returned body, never scanned (A11.6).
    Returns ``b""`` (never raises) for a malformed object with no blank-line boundary at
    all — an honest empty message, not a fabricated one.
    """
    idx = raw.find(b"\n\n")
    if idx == -1:
        return b""
    return raw[idx + 2 :]


#: v0.4.3 T-043-23 security-review rework (FR11 LOW, CWE-184) — the exact folded
#: header key a merge-of-a-signed-tag embeds (see :func:`_mergetag_bodies`).
_MERGETAG_PREFIX = b"mergetag "


def _unfold_mergetag_blocks(raw: bytes) -> list[bytes]:
    """Extract and unfold every ``mergetag `` header block from *raw*'s HEADER region
    (everything before the first blank-line body separator) — v0.4.3 T-043-23
    security-review rework, FR11 LOW residual (CWE-184, handoff
    2026-08-17T173112Z-security-reviewer-v0.4.3-alpha-2-delta).

    Merging a GPG-signed annotated tag embeds the WHOLE tag object — its own
    ``object``/``type``/``tag``/``tagger`` header lines AND its own free-form message
    body — into the outer commit's header as a ``mergetag <object-sha>`` line followed
    by CONTINUATION lines, each prefixed with exactly one space (the identical
    RFC-2822-style folding ``gpgsig`` already uses, per :func:`_split_object_body`'s
    own docstring) — entirely inside the region ``_split_object_body`` excludes from
    scanning, so a secret published ONLY inside a merged tag's own message never
    reached the matcher.

    Returns one UNFOLDED block per ``mergetag `` line found (leading continuation
    space stripped from every line, ``mergetag `` prefix stripped from the first) —
    each block carries the identical header-lines/blank-line/body shape a standalone
    tag object does, ready for :func:`_split_object_body` to split again. Empty when
    *raw* embeds no mergetag block (the ordinary case).
    """
    header_region = raw.split(b"\n\n", 1)[0]
    lines = header_region.split(b"\n")
    blocks: list[bytes] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(_MERGETAG_PREFIX):
            unfolded = [line[len(_MERGETAG_PREFIX) :]]
            i += 1
            while i < len(lines) and lines[i].startswith(b" "):
                unfolded.append(lines[i][1:])  # strip the single folding space
                i += 1
            blocks.append(b"\n".join(unfolded))
            continue
        i += 1
    return blocks


def _mergetag_bodies(raw: bytes) -> bytes:
    """The scannable MESSAGE-BODY text of every mergetag-embedded tag in *raw*,
    joined with a newline — reuses :func:`_split_object_body`'s own header/body split
    on each unfolded block (an embedded tag carries the identical shape a standalone
    tag object does), so the embedded tag's OWN header lines (its ``tagger``, etc.)
    stay excluded from the scanned text exactly like the outer commit's headers
    already are (A11.6). Returns ``b""`` when *raw* embeds no mergetag block."""
    return b"\n".join(_split_object_body(block) for block in _unfold_mergetag_blocks(raw))


def _read_object_bodies(
    repo: Path, shas: list[str], *, kind: str, path_label: str
) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per sha in *shas*, scanning ONLY the message
    BODY of each commit/tag object (v0.4.3 T-043-15/FR11).

    Reuses the exact SAME primitives the blob content read already uses: a batched
    ``git cat-file --batch`` conversation, chunked to :data:`_BATCH_CHUNK_SIZE` (FR9's
    bounded-memory property extends unchanged to this population), routed through
    :func:`_run` so a timeout or missing ``git`` always raises the typed
    :class:`GitObjectReadError` (A11.4 — no silent skip, matching the blob path
    exactly). ``prior_text`` is never set (stays ``None``): a commit/tag object carries
    no real path to key a prior-text amnesty lookup on, so every hit here is
    unconditionally fail-closed (A11.7) — never a special case in the matcher, which
    already treats ``prior_text=None`` as "never suppress".
    """
    for start in range(0, len(shas), _BATCH_CHUNK_SIZE):
        chunk = shas[start : start + _BATCH_CHUNK_SIZE]
        stdin_payload = ("\n".join(chunk) + "\n").encode("utf-8")
        result = _run(["git", "cat-file", "--batch"], repo, input_bytes=stdin_payload)
        if result.returncode != 0:
            raise GitObjectReadError(
                f"git cat-file --batch failed reading {kind} bodies: "
                f"{_decode(result.stderr).strip()}"
            )
        out = result.stdout
        pos = 0
        for sha in chunk:
            try:
                newline_idx = out.index(b"\n", pos)
                header = out[pos:newline_idx].decode("utf-8", errors="replace")
                pos = newline_idx + 1
                parts = header.split()
                if len(parts) != 3:
                    raise ValueError(f"unexpected header shape {header!r}")
                obj_sha, _obj_type, size_str = parts
                content_size = int(size_str)
            except ValueError as exc:
                raise GitObjectReadError(
                    f"git cat-file --batch stream desynchronised reading {kind} body "
                    f"at {sha}: {exc}"
                ) from exc
            content = out[pos : pos + content_size]
            pos += content_size + 1  # skip the trailing newline after the content block
            body = _split_object_body(content)
            # v0.4.3 T-043-23 security-review rework (FR11): a merge-of-a-signed-tag
            # embeds the WHOLE tag object in the HEADER region _split_object_body
            # excludes — fold any mergetag-embedded tag message body in alongside the
            # commit's own message so BOTH reach the matcher on this SAME object.
            mergetag_body = _mergetag_bodies(content)
            if mergetag_body:
                body = body + b"\n" + mergetag_body if body else mergetag_body
            try:
                text = body.decode("utf-8")
            except UnicodeDecodeError:
                yield ScannedObject(
                    path=path_label, sha=obj_sha, text="", decodable=False, kind=kind
                )
                continue
            yield ScannedObject(path=path_label, sha=obj_sha, text=text, decodable=True, kind=kind)


def _multi_path_shas(
    repo: Path, local_sha: str, base: str | None, candidate_shas: set[str]
) -> set[str]:
    """The subset of *candidate_shas* reachable at MORE THAN ONE distinct path ANYWHERE
    in the pushed RANGE (SPEC v0.4.2 FR7/A7.1/GRILL P10, ADR R1, D4; CR-3 remediation —
    v0.4.2 code-review MEDIUM, operator ruling: SPEC wins over the cheaper tip-tree-only
    form the release originally shipped).

    ``git rev-list --objects`` (:func:`_rev_list_candidates`) cannot answer this
    question by itself: git's own object walk visits each OBJECT once and reports only
    the first tree ENTRY that references it, so a blob reachable at two paths in the
    same tree is reported at only one of them regardless — the very thing that made
    :func:`_blob_info`'s "first-seen path wins" choice tree-order-dependent in the
    first place (GRILL P10), one layer further up than that function's own docstring
    suggests. ``git ls-tree -r``, by contrast, enumerates every tree ENTRY (not every
    distinct object) of the ONE commit it is pointed at, so a blob at two paths within
    that commit's tree shows up twice — the primitive this detection actually needs.

    CR-3: FR7/A7.1 say "reachable at more than one path in the RANGE", not only the
    pushed tip's tree — a blob may be multi-pathed in an INTERMEDIATE commit (e.g. a
    transient copy that is removed again before the tip) and single-pathed, or absent,
    at the tip; the pre-remediation tip-tree-only call could not see that and silently
    granted amnesty. The fix widens the enumeration to EVERY commit in the range
    (:func:`_range_commit_shas`), unions each commit's ``(sha -> paths)`` mapping, and
    flags a candidate multi-path the moment its UNIONED path set exceeds one entry —
    tree-order-independent within each commit (unchanged from the pre-fix single-tree
    call) AND commit-order-independent across the range (the new property).

    **Bounded-cost note.** This costs one ``git ls-tree -r`` subprocess call PER COMMIT
    in the range (never per object), each proportional to that commit's tree size — see
    :func:`_range_commit_shas`'s docstring for why that count stays small for an
    ordinary push. A pathological range with very many commits (e.g. a first push of an
    entire deep history in the ``--not --remotes`` fallback shape) pays proportionally
    more calls; nothing here silently degrades to a partial scan in that case (a fail-
    open amnesty is a worse outcome than a slower push). If this ever becomes a
    measured bottleneck, the calls can be CHUNKED (batched in groups via a single
    ``git cat-file --batch`` conversation over ``<commit>^{tree}`` objects, mirroring
    the FR9 chunking this module already applies to blob content) rather than the
    current one-call-per-commit form — deferred until real cost data justifies it.
    """
    if not candidate_shas:
        return set()
    # local_sha is always included even when the range walk would already report it
    # (the ordinary case) — a defensive guarantee that the tip's own tree is NEVER
    # skipped, matching the pre-fix call's coverage exactly as a floor.
    commit_shas = {local_sha, *_range_commit_shas(repo, local_sha, base)}
    paths_by_sha: dict[str, set[str]] = {}
    for commit_sha in commit_shas:
        result = _run(["git", "ls-tree", "-r", "--full-tree", commit_sha, "--"], repo)
        if result.returncode != 0:
            raise GitObjectReadError(f"git ls-tree -r failed: {_decode(result.stderr).strip()}")
        for line in _decode(result.stdout).splitlines():
            meta, _, path = line.partition("\t")
            parts = meta.split()
            if len(parts) != 3 or parts[1] != "blob":
                continue
            sha = parts[2]
            if sha not in candidate_shas:
                continue
            paths_by_sha.setdefault(sha, set()).add(path)
    return {sha for sha, paths in paths_by_sha.items() if len(paths) > 1}


def _blob_info(repo: Path, candidates: list[tuple[str, str]]) -> dict[str, tuple[str, int]]:
    """Return ``{sha: (first-seen path, size)}`` restricted to the candidates that are
    blobs.

    ``git rev-list --objects`` also emits trees with a path (directory names) — this
    filters those out, and reads each blob's size in the same pass, via a single
    batched ``git cat-file --batch-check`` call rather than one subprocess per
    candidate. The size is what lets :func:`_read_blobs` apply the oversized-blob guard
    (R3) BEFORE ever fetching an oversized blob's content.

    SPEC v0.4.2 FR8(3)/GRILL P12: a row that is NOT the documented 3-field
    ``<sha> <type> <size>`` shape, or whose size field is non-numeric, RAISES the typed
    error naming the row — every ``candidates`` entry is a sha :func:`_rev_list_candidates`
    already confirmed reachable, so an unparseable response row here is a real
    read-desync, never an ordinary outcome to silently drop (which would silently
    shrink the scanned set with no signal anywhere). A ``blob``-type filter MISS (the
    row parses fine but names a tree) stays the ordinary, expected, silent skip it
    always was — that is not a parse failure.
    """
    if not candidates:
        return {}
    stdin_payload = ("\n".join(sha for sha, _ in candidates) + "\n").encode("utf-8")
    result = _run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        repo,
        input_bytes=stdin_payload,
    )
    if result.returncode != 0:
        raise GitObjectReadError(
            f"git cat-file --batch-check failed: {_decode(result.stderr).strip()}"
        )
    blob_sizes: dict[str, int] = {}
    for line in _decode(result.stdout).splitlines():
        parts = line.split()
        if len(parts) != 3:
            raise GitObjectReadError(f"git cat-file --batch-check: unexpected row shape {line!r}")
        if parts[1] != "blob":
            continue  # an ordinary, expected filtered outcome (a tree) — never an error.
        sha, size_str = parts[0], parts[2]
        try:
            blob_sizes[sha] = int(size_str)
        except ValueError:
            raise GitObjectReadError(
                f"git cat-file --batch-check: non-numeric size in row {line!r}"
            ) from None
    info: dict[str, tuple[str, int]] = {}
    for sha, path in candidates:
        if sha in blob_sizes and sha not in info:
            info[sha] = (path, blob_sizes[sha])
    return info


def _resolve_prior_texts(repo: Path, base: str, paths: list[str]) -> dict[str, str]:
    """Resolve the published prior text of every DISTINCT path in *paths*, at *base*
    (SPEC v0.11.0 FR2, rides the SAME chunk this is called from).

    Two batched calls, on the SAME shape the content read already uses:

    1. ``git cat-file --batch-check`` fed ``<base>:<path>`` lines — this both filters
       non-existent paths (git answers ``<spec> missing``) and supplies the size, so
       the cap is applied BEFORE any prior content is fetched. ``--batch-check``
       preserves stdin ORDER in its output (one line per input line), which is how
       each output line is correlated back to its requesting path — the returned
       ``%(objectname)`` is the PRIOR BLOB's sha, not the ``<base>:<path>`` spec, so
       content-based correlation is not available here (unlike :func:`_blob_info`,
       which correlates by the requested blob sha itself).
    2. ``git cat-file --batch`` for the under-cap survivors — full content, never
       truncated (already filtered to under-cap sizes).

    A path missing from the returned dict has NO prior content — never mapped to an
    empty string, which would silently amnesty nothing but would also hide the
    distinction (over-cap / undecodable / genuinely absent) from a future reader.

    SPEC v0.4.2 FR8(3)/GRILL P12: the documented ``<spec> missing`` row (git's own
    shape for "this path does not exist at this base") stays an ORDINARY absence,
    exactly as before — a genuinely new path is the common case, not a failure. Any
    OTHER row shape that is not the documented 3-field ``<sha> <type> <size>``
    blob/tree response, or whose size field is non-numeric, RAISES the typed error
    instead of silently falling into the same "absence" bucket — an unparseable row
    here is a real read-desync (git answering something git-only ever answers on
    internal inconsistency), never routine "this path never existed."

    CR-1 (v0.4.2 code review HIGH, regression vs 741f2294): a *missing* row is git
    ECHOING THE WHOLE ``<base>:<path>`` INPUT back, followed by `` missing`` — i.e.
    ``<base>:<path> missing``. A path with embedded spaces (routine on macOS/Windows,
    e.g. a screenshot filename) therefore does NOT split into a fixed 2-field row; a
    field-COUNT classifier misreads the extra fields as a desynchronised row and
    raises, blocking a legitimate push. The row is classified by SUFFIX instead —
    ``line.endswith(" missing")`` identifies the absence row for ANY path, regardless
    of how many spaces it contains — before ever looking at field count. This does not
    affect :func:`_blob_info`'s own ``--batch-check`` classifier: that call is fed
    SHAS, never paths, so its rows never carry a path's embedded whitespace and the
    field-count classifier there stays exact for its own input shape.
    """
    if not paths:
        return {}
    unique_paths = list(dict.fromkeys(paths))
    check_stdin = ("\n".join(f"{base}:{path}" for path in unique_paths) + "\n").encode("utf-8")
    check_result = _run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        repo,
        input_bytes=check_stdin,
    )
    if check_result.returncode != 0:
        raise GitObjectReadError(
            "git cat-file --batch-check failed resolving prior content: "
            f"{_decode(check_result.stderr).strip()}"
        )
    check_lines = _decode(check_result.stdout).splitlines()
    if len(check_lines) != len(unique_paths):
        raise GitObjectReadError(
            "git cat-file --batch-check desynchronised resolving prior content "
            f"(expected {len(unique_paths)} line(s), got {len(check_lines)})"
        )

    under_cap: dict[str, int] = {}
    for path, line in zip(unique_paths, check_lines, strict=True):
        # CR-1: classify the documented "<base>:<path> missing" absence row by SUFFIX,
        # not by field count — git echoes the WHOLE input line, so a path with one or
        # more embedded spaces (e.g. "docs/my other file.md") never has a fixed field
        # count. Checked BEFORE any `line.split()` field-count reasoning below.
        if line.endswith(" missing"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise GitObjectReadError(
                "git cat-file --batch-check: unexpected row shape resolving prior content",
                path=path,
            )
        _sha, obj_type, size_str = parts
        # code-reviewer LOW finding (v0.11.0 pre-PR review): a path that was a
        # DIRECTORY at the base resolves to its TREE object, not a blob — only
        # objecttype "blob" may ever supply prior text; anything else (tree, or any
        # future object kind) is treated exactly like a missing path, never fetched.
        if obj_type != "blob":
            continue
        try:
            size = int(size_str)
        except ValueError:
            raise GitObjectReadError(
                "git cat-file --batch-check: non-numeric size resolving prior content",
                path=path,
            ) from None
        if size <= _MAX_BLOB_BYTES:
            under_cap[path] = size

    if not under_cap:
        return {}

    fetch_paths = list(under_cap)
    fetch_stdin = ("\n".join(f"{base}:{path}" for path in fetch_paths) + "\n").encode("utf-8")
    batch_result = _run(["git", "cat-file", "--batch"], repo, input_bytes=fetch_stdin)
    if batch_result.returncode != 0:
        raise GitObjectReadError(
            "git cat-file --batch failed resolving prior content: "
            f"{_decode(batch_result.stderr).strip()}"
        )

    out = batch_result.stdout
    pos = 0
    prior_texts: dict[str, str] = {}
    for path in fetch_paths:
        try:
            newline_idx = out.index(b"\n", pos)
            header = out[pos:newline_idx].decode("utf-8", errors="replace")
            pos = newline_idx + 1
            parts = header.split()
            if len(parts) != 3:
                raise ValueError(f"unexpected header shape {header!r}")
            _obj_sha, _obj_type, size_str = parts
            content_size = int(size_str)
        except ValueError as exc:
            # v0.4.2 FR4/GRILL P9: the offending PATH is a structured field, never
            # embedded in the message string — the single render boundary
            # (features.chokepoints.service) masks it before it reaches any
            # operator-facing string. `exc` (the ValueError) still names the parse
            # detail (an internal shape description, never a path) in the message.
            raise GitObjectReadError(
                f"git cat-file --batch stream desynchronised resolving prior content: {exc}",
                path=path,
            ) from exc
        content = out[pos : pos + content_size]
        pos += content_size + 1  # skip the trailing newline after the content block
        # Undecodable prior blob -> absence, never a partial/garbled string.
        with contextlib.suppress(UnicodeDecodeError):
            prior_texts[path] = content.decode("utf-8")
    return prior_texts


def _read_blob_chunk(
    repo: Path,
    chunk_shas: list[str],
    blob_info: dict[str, tuple[str, int]],
    prior_texts: dict[str, str],
    multi_path_shas: set[str],
) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per blob in *chunk_shas*, via a SINGLE batched
    ``git cat-file --batch`` conversation scoped to just this chunk.

    v0.11.0 FR8/A8.1-A8.2: the header-parse pair (the newline lookup and the size-field
    conversion) is wrapped so a truncated stream or a non-numeric size field surfaces as
    the module's typed :class:`GitObjectReadError` instead of a raw ``ValueError``
    escaping past the module's contract. A desynchronised header shape (``len(parts) !=
    3``) raises the SAME typed error rather than yielding a fabricated
    ``decodable=False`` object and continuing: after a desync, ``pos`` points into
    content bytes and every later header parse is garbage — a stream of fabricated
    objects silently counted as binary skips. A gate that has lost sync with git's
    stream aborts; it does not invent.

    v0.11.0 FR2: *prior_texts* (already resolved for this chunk's distinct paths, or
    empty in the fallback shape) supplies each yielded object's ``prior_text`` — a
    lookup miss maps to the explicit absence ``None``, never an empty string.

    SPEC v0.4.2 FR7/GRILL P10/ADR R1/D4: a sha in *multi_path_shas* — reachable at more
    than one path in this range — ALWAYS gets ``prior_text=None``, fail-closed,
    regardless of what :func:`_resolve_prior_texts` resolved for its (arbitrarily
    "first-seen") reporting path. The matcher itself is untouched: this is the ONLY
    place the multi-path decision is made.
    """
    stdin_payload = ("\n".join(chunk_shas) + "\n").encode("utf-8")
    result = _run(["git", "cat-file", "--batch"], repo, input_bytes=stdin_payload)
    if result.returncode != 0:
        raise GitObjectReadError(f"git cat-file --batch failed: {_decode(result.stderr).strip()}")

    out = result.stdout
    pos = 0
    for sha in chunk_shas:
        path, size = blob_info[sha]
        try:
            newline_idx = out.index(b"\n", pos)
            header = out[pos:newline_idx].decode("utf-8", errors="replace")
            pos = newline_idx + 1
            parts = header.split()
            if len(parts) != 3:
                raise ValueError(f"unexpected header shape {header!r}")
            obj_sha, _obj_type, size_str = parts
            content_size = int(size_str)
        except ValueError as exc:
            raise GitObjectReadError(
                f"git cat-file --batch stream desynchronised at object {sha}: {exc}"
            ) from exc
        content = out[pos : pos + content_size]
        pos += content_size + 1  # skip the trailing newline after the content block
        prior_text = None if sha in multi_path_shas else prior_texts.get(path)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            yield ScannedObject(
                path=path, sha=obj_sha, text="", decodable=False, prior_text=prior_text
            )
            continue
        yield ScannedObject(
            path=path, sha=obj_sha, text=text, decodable=True, prior_text=prior_text
        )


def _read_oversized_blob_prefix(repo: Path, sha: str) -> bytes:
    """Read at most :data:`_MAX_BLOB_BYTES` of *sha*'s content through a SEPARATE,
    bounded per-object stream, then close it early (SPEC v0.11.0 FR4/ADR D2-a).

    This call deliberately does NOT go through :func:`_run`: closing the pipe before
    git has finished writing makes a non-zero exit / broken-pipe outcome EXPECTED on
    THIS call only, and ``_run``'s contract is to convert every subprocess failure into
    :class:`GitObjectReadError` — which would misreport this intentional early close as
    a git failure. git genuinely never produces the remainder once the pipe is closed,
    so v0.9.0's R3 "never fetched" property holds for the truncated tail exactly as
    before; only the DECISION of what to do with the (now non-empty) prefix changed.

    A missing ``git`` executable, or the read exceeding :data:`_TIMEOUT_S` with no
    prefix delivered, still raises :class:`GitObjectReadError` — the bound is on the
    NORMAL, expected-success path only, not on genuine git/environment failure.

    SPEC v0.4.2 FR8(1)/GRILL P11/A8.1-A8.2: *after* the early-close ``wait()``, the
    process's own exit status is inspected — a nonexistent oid or a non-blob object
    (e.g. a tree sha) makes ``git cat-file blob`` fail immediately and deliver ZERO
    bytes on stdout; pre-fix, that 0-byte outcome was indistinguishable from "genuinely
    empty content" and was reported as a successfully (if trivially) scanned prefix. A
    process that FAILED (``returncode not in (0,)``) and delivered FEWER than the cap's
    worth of bytes now raises. A full-cap read keeps swallowing the terminate/EPIPE
    outcome unconditionally (A8.2) — our own early close intentionally makes git exit
    non-zero on the SUCCESS path too, so a full cap's worth of bytes never triggers
    this check regardless of the exit status.
    """
    try:
        proc = subprocess.Popen(  # noqa: S603 — fixed argv, no shell
            ["git", "cat-file", "blob", sha],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise GitObjectReadError(f"git is not available on PATH: {exc}") from exc

    result_q: queue.Queue[bytes | Exception] = queue.Queue(maxsize=1)

    def _reader() -> None:
        try:
            assert proc.stdout is not None
            result_q.put(proc.stdout.read(_MAX_BLOB_BYTES))
        except Exception as exc:  # noqa: BLE001 — surfaced via the queue, never re-raised bare
            result_q.put(exc)

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()
    try:
        outcome: bytes | Exception | None
        try:
            outcome = result_q.get(timeout=_TIMEOUT_S)
        except queue.Empty:
            outcome = None
    finally:
        # Close the read end and terminate now — this is the deliberate EARLY CLOSE:
        # git will see EPIPE/SIGPIPE on its next write and exit non-zero, which is
        # EXPECTED here and is never inspected or converted into an error.
        if proc.stdout is not None:
            proc.stdout.close()
        proc.terminate()
        try:
            proc.wait(timeout=_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    if outcome is None:
        raise GitObjectReadError(f"git cat-file blob timed out reading oversized object {sha}")
    if isinstance(outcome, Exception):
        raise GitObjectReadError(
            f"git cat-file blob failed reading oversized object {sha}: {outcome}"
        ) from outcome
    if len(outcome) < _MAX_BLOB_BYTES and proc.returncode not in (0,):
        raise GitObjectReadError(
            f"git cat-file blob failed reading oversized object {sha} "
            f"(exit {proc.returncode}, {len(outcome)} byte(s) delivered before failure)"
        )
    return outcome


def _read_oversized_blob(repo: Path, sha: str, path: str, size: int) -> ScannedObject:
    """Build the :class:`ScannedObject` for one oversized blob (SPEC v0.11.0 FR4).

    The scanned prefix is decoded ``errors="strict"`` (PLAN §5): a truncation that
    happens to land mid-multi-byte-character is honestly reported as undecodable
    (A4.6) rather than silently repaired — the matcher then falls back to the SAME
    binary skip class as any other undecodable blob (denylist_scan.scan_objects).
    """
    prefix = _read_oversized_blob_prefix(repo, sha)
    try:
        text = prefix.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return ScannedObject(
            path=path,
            sha=sha,
            text="",
            decodable=False,
            oversized=True,
            size_bytes=size,
            scanned_bytes=len(prefix),
        )
    return ScannedObject(
        path=path,
        sha=sha,
        text=text,
        decodable=True,
        oversized=True,
        size_bytes=size,
        scanned_bytes=len(prefix),
    )


def _read_blobs(
    repo: Path,
    blob_info: dict[str, tuple[str, int]],
    base: str | None,
    multi_path_shas: set[str],
) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per blob in *blob_info*.

    Content is read via batched ``git cat-file --batch`` conversations, chunked to
    :data:`_BATCH_CHUNK_SIZE` blobs per call (SPEC v0.11.0 FR9/ADR D8) — one subprocess
    per CHUNK, not one per blob (code-reviewer MEDIUM finding; mirrors the batching
    pattern :func:`_blob_info` already uses) and NOT one whole-range subprocess whose
    output buffer grows unbounded with the range size. A blob over
    :data:`_MAX_BLOB_BYTES` is EXCLUDED from every batch conversation entirely — the
    single-conversation win is preserved for the under-cap population — and is instead
    read through :func:`_read_oversized_blob`'s separate, bounded per-object stream
    (SPEC v0.11.0 FR4, supersedes the v0.9.0 total-blind-spot skip): its first cap
    bytes are scanned and it is reported ``decodable=True``/``oversized=True`` when
    that prefix is valid UTF-8, or ``decodable=False``/``oversized=True`` otherwise
    (A4.6) — the remainder past the cap is genuinely never fetched either way.

    v0.11.0 FR2/ADR D8: with *base* resolved, each CHUNK's prior-side lookup
    (:func:`_resolve_prior_texts`) rides the SAME loop as the content read — two extra
    batched calls per chunk, never per blob — so the peak resident set stays
    ``chunk_size x cap x 2`` rather than growing with the range. An oversized CURRENT
    object never carries prior text (the prior-side lookup rides the chunk loop only).
    """
    fetch_shas = [sha for sha, (_, size) in blob_info.items() if size <= _MAX_BLOB_BYTES]
    oversized_shas = [sha for sha, (_, size) in blob_info.items() if size > _MAX_BLOB_BYTES]

    for sha in oversized_shas:
        path, size = blob_info[sha]
        yield _read_oversized_blob(repo, sha, path, size)

    for start in range(0, len(fetch_shas), _BATCH_CHUNK_SIZE):
        chunk = fetch_shas[start : start + _BATCH_CHUNK_SIZE]
        prior_texts: dict[str, str] = {}
        if base is not None:
            chunk_paths = [blob_info[sha][0] for sha in chunk]
            prior_texts = _resolve_prior_texts(repo, base, chunk_paths)
        yield from _read_blob_chunk(repo, chunk, blob_info, prior_texts, multi_path_shas)


class GitSubprocessObjectReader:
    """Subprocess-backed ``GitObjectReader`` (SPEC v0.9.0 FR1/FR7 injected port)."""

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterator[ScannedObject]:
        if not local_sha or local_sha == ZERO_SHA:
            return
        # code-reviewer LOW finding (v0.11.0 pre-PR review): the module's stated
        # second-layer argv defence (module docstring above) must also cover
        # `local_sha` — the SAME shape check `_is_resolvable_commit` already applies to
        # `remote_sha`, here applied BEFORE `local_sha` ever reaches
        # `_rev_list_candidates`'s `git rev-list` argv (CWE-88). An option-shaped value
        # is rejected as a read failure rather than ever being interpolated.
        if not _SHA_SHAPE_RE.match(local_sha):
            raise GitObjectReadError(f"local_sha is not a valid sha shape: {local_sha!r}")
        # v0.11.0 FR2/ADR D7: base resolved ONCE per call — reused for the FR1 range
        # shape (_rev_list_candidates) AND the prior-side lookup (_read_blobs), rather
        # than re-derived. Unresolvable/zero remote_sha -> no base -> no object in this
        # call carries prior content (the fallback shape stays byte-identical to
        # v0.9.0).
        base = remote_sha if _is_resolvable_commit(repo, remote_sha) else None
        candidates = _rev_list_candidates(repo, local_sha, base)
        blob_info = _blob_info(repo, candidates)
        multi_path_shas = _multi_path_shas(repo, local_sha, base, set(blob_info))
        yield from _read_blobs(repo, blob_info, base, multi_path_shas)
        # v0.4.3 T-043-15/FR11: the range's commit message BODIES (never their
        # author/committer headers, A11.6) — the SAME range :func:`_range_commit_shas`
        # already walks for the multi-path detection above, re-derived here rather than
        # threaded through (keeps this call's own signature and every existing caller
        # of the functions above untouched). `prior_text` is never set for these (A11.7,
        # fail-closed by construction — see `_read_object_bodies`).
        commit_shas = _range_commit_shas(repo, local_sha, base)
        yield from _read_object_bodies(
            repo, commit_shas, kind="commit", path_label=_COMMIT_BODY_PATH
        )
        # A11.3: a tag-ref push additionally yields the annotated tag's OWN body — a
        # lightweight tag has no such object (local_sha already names the commit
        # directly), so `_is_annotated_tag` correctly yields nothing for it.
        if _is_annotated_tag(repo, local_sha):
            yield from _read_object_bodies(repo, [local_sha], kind="tag", path_label=_TAG_BODY_PATH)
