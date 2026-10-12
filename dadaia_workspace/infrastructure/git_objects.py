"""GitSubprocessObjectReader — the sole adapter for the push-range object scan (no
``GitObjectReader`` port: one adapter, no swap seam).

Reads over ``git rev-list --objects`` + ``git cat-file``. Every subprocess invocation
here — including the batch calls that need ``input=`` — is routed through :func:`_run`,
so a timeout or a missing ``git`` executable always surfaces as
:class:`GitObjectReadError`, never a raw exception at the push boundary.

**One exclusion formula for every push.** :func:`_base_exclusions` returns one exclusion
set for every call: ``--remotes=origin`` unconditionally, plus ``remote_sha`` when it resolves.
Every range and base derivation in this module consumes that same set.
"""

from __future__ import annotations

import contextlib
import subprocess
from collections.abc import Iterator
from pathlib import Path

from dadaia_workspace.core.models.git_scan import (
    SHA_SHAPE_RE,
    ZERO_SHA,
    GitObjectReadError,
    GitRunError,
    ScannedObject,
)
from dadaia_workspace.core.redaction import PUBLISHED, publication_boundaries

_TIMEOUT_S = 30

#: Re-checks the sha shape of ``parse_push_stdin`` (40-char SHA-1 or 64-char SHA-256 hex)
#: as an independent layer: this adapter never interpolates an option-shaped string into a
#: git argv, whatever validated the caller's input (CWE-88).

#: Per-blob size guard, so one pathological blob cannot dominate the scan's wall clock or
#: memory: a blob at or under this cap is read and decoded; a blob over it is never fetched
#: and is reported ``decodable=False``, counted like an undecodable binary blob.
_MAX_BLOB_BYTES = 5 * 1024 * 1024  # 5 MB

#: The ``git cat-file --batch`` conversation is chunked so the peak resident set is bounded
#: by a constant (``chunk_size x cap``) rather than growing with the pushed range. The
#: prior-side lookup rides the same chunk loop, doubling the bound to ``chunk_size x cap x 2``.
_BATCH_CHUNK_SIZE = 500

#: Synthetic, non-path labels for a commit or tag body object: there is no repo-relative
#: path to key a lookup on.
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
    except OSError as exc:  # no git on PATH, or a cwd that is not a directory (WinError 267)
        raise GitRunError(f"git could not run in {cwd}: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitRunError(f"git command timed out: {' '.join(args)}") from exc


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _lines(raw: bytes) -> list[str]:
    """Non-empty lines of git output, split on ``\n`` only (a path may hold U+2028)."""
    return [line for line in _decode(raw).split("\n") if line]


def _is_resolvable_commit(repo: Path, sha: str) -> bool:
    """True when *sha* resolves to a commit object reachable locally.

    *sha* is shape-checked against :data:`SHA_SHAPE_RE` before it is interpolated into the
    ``git cat-file -e <sha>^{commit}`` argv: an option-shaped value (e.g.
    ``--upload-pack=...``) is rejected, never interpolated (CWE-88). Used by
    :func:`_base_exclusions` to decide whether *remote_sha* is an extra ``--not`` target.
    """
    if not sha or sha == ZERO_SHA or not SHA_SHAPE_RE.match(sha):
        return False
    result = _run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], repo)
    return result.returncode == 0


def _base_exclusions(repo: Path, remote_sha: str) -> list[str]:
    """The ``--not`` exclusion targets shared by every range and base derivation below.

    ``--remotes=origin`` (every locally known ``origin`` remote-tracking ref, never another
    remote's) is always present. *remote_sha* is added first when it resolves to a local
    commit (:func:`_is_resolvable_commit`); a brand-new ref's all-zero *remote_sha* never
    resolves. Every caller gets this same set.
    """
    exclusions = [PUBLISHED]
    if _is_resolvable_commit(repo, remote_sha):
        exclusions.insert(0, remote_sha)
    return exclusions


def _rev_list_candidates(
    repo: Path, local_sha: str, exclusions: list[str]
) -> list[tuple[str, str]]:
    """Return ``(sha, path)`` pairs for every object with a path newly reachable from
    *local_sha* — blobs AND trees (type filtering happens separately, in
    :func:`_blob_info`) — after subtracting *exclusions* (:func:`_base_exclusions`).

    The argv ends with a ``--`` end-of-options marker after the revision arguments
    (CWE-88/CWE-20).
    """
    args = ["git", "rev-list", "--objects", local_sha, "--not", *exclusions, "--"]
    result = _run(args, repo)
    if result.returncode != 0:
        raise GitObjectReadError(f"git rev-list --objects failed: {_decode(result.stderr).strip()}")
    entries: list[tuple[str, str]] = []
    for raw_line in _lines(result.stdout):
        sha, _, path = raw_line.partition(" ")
        if path:
            entries.append((sha, path))
    return entries


def _range_commit_shas(repo: Path, local_sha: str, exclusions: list[str]) -> list[str]:
    """Return every COMMIT sha in the range (never ``--objects`` — commits only), the
    SAME range shape :func:`_rev_list_candidates` walks (the SAME *exclusions*,
    :func:`_base_exclusions`), reused here so the two callers agree on what "the
    range" means without either re-deriving it."""
    args = ["git", "rev-list", local_sha, "--not", *exclusions, "--"]
    result = _run(args, repo)
    if result.returncode != 0:
        raise GitObjectReadError(f"git rev-list failed: {_decode(result.stderr).strip()}")
    return _lines(result.stdout)


def _publication_boundaries(repo: Path, local_sha: str, exclusions: list[str]) -> tuple[str, ...]:
    """The prior-text anchor(s), from
    :func:`~dadaia_workspace.core.redaction.publication_boundaries`, over the same
    *exclusions* (:func:`_base_exclusions`) the range walk uses."""

    def git(args: list[str]) -> list[str]:
        result = _run(["git", *args], repo)
        if result.returncode != 0:
            raise GitObjectReadError(
                f"git rev-list --boundary failed: {_decode(result.stderr).strip()}"
            )
        return _lines(result.stdout)

    return publication_boundaries(git, local_sha, exclusions)


def _is_annotated_tag(repo: Path, sha: str) -> bool:
    """True iff *sha* names an annotated tag object.

    A lightweight tag is not an object at all — its ref points directly at a commit, so
    ``local_sha`` would already BE that commit sha and this correctly returns False (no
    separate tag body exists to scan). Shape-checked BEFORE interpolation into the
    ``git cat-file -t`` argv, mirroring :func:`_is_resolvable_commit` (CWE-88).
    """
    if not sha or sha == ZERO_SHA or not SHA_SHAPE_RE.match(sha):
        return False
    result = _run(["git", "cat-file", "-t", sha], repo)
    return result.returncode == 0 and _decode(result.stdout).strip() == "tag"


def _split_object_body(raw: bytes) -> bytes:
    """Return *raw*'s message BODY only — everything after the first blank-line
    header/body separator of a raw commit or annotated-tag object.

    A commit object is ``tree/parent/author/committer[/gpgsig]`` header lines, a blank
    line, then the free-form message; an annotated tag object is
    ``object/type/tag/tagger`` header lines, a blank line, then the free-form message.
    Both shapes share the SAME blank-line boundary, so one splitter serves both. A
    ``gpgsig`` header's own body is multi-line but every continuation line is prefixed
    with a single space (never blank), so the FIRST ``b"\\n\\n"`` is always the true
    header/body boundary — the ``author``/``committer``/``tagger`` header lines (and any
    ``gpgsig``) are structurally excluded from the returned body, never scanned.
    Returns ``b""`` (never raises) for a malformed object with no blank-line boundary at
    all — an honest empty message, not a fabricated one.
    """
    idx = raw.find(b"\n\n")
    if idx == -1:
        return b""
    return raw[idx + 2 :]


#: The exact folded header key a merge of a signed tag embeds (CWE-184; see
#: :func:`_mergetag_bodies`).
_MERGETAG_PREFIX = b"mergetag "


def _unfold_mergetag_blocks(raw: bytes) -> list[bytes]:
    """Extract and unfold every ``mergetag `` header block from *raw*'s HEADER region
    (everything before the first blank-line body separator).

    Merging a GPG-signed annotated tag embeds the whole tag object into the outer commit's
    header as a ``mergetag <object-sha>`` line followed by continuation lines, each prefixed
    with exactly one space (the folding ``gpgsig`` uses, see :func:`_split_object_body`).
    That region is excluded from scanning, so the embedded tag's own message is taken here.

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
    """The scannable message-body text of every mergetag-embedded tag in *raw*, joined
    with a newline. Each unfolded block is split by :func:`_split_object_body`, so the
    embedded tag's own header lines stay out of the scanned text. Returns ``b""`` when
    *raw* embeds no mergetag block."""
    return b"\n".join(_split_object_body(block) for block in _unfold_mergetag_blocks(raw))


def _read_object_bodies(
    repo: Path, shas: list[str], *, kind: str, path_label: str
) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per sha in *shas*, scanning ONLY the message
    BODY of each commit/tag object.

    A batched ``git cat-file --batch`` conversation, chunked to :data:`_BATCH_CHUNK_SIZE`,
    routed through :func:`_run` so a timeout or missing ``git`` raises
    :class:`GitObjectReadError`, never a silent skip. ``prior_text`` is never set (stays
    ``None``): a commit/tag object carries no real path to key a prior-text lookup on, so
    every hit here is fail-closed, and the matcher treats ``prior_text=None`` as "never
    suppress".
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
            # A merged signed tag embeds its whole tag object in the header region that
            # _split_object_body excludes: fold its message body in beside the commit's own.
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
    repo: Path, local_sha: str, exclusions: list[str], candidate_shas: set[str]
) -> set[str]:
    """The subset of *candidate_shas* reachable at more than one distinct path anywhere in
    the pushed range.

    ``git rev-list --objects`` (:func:`_rev_list_candidates`) reports each object once, at
    the first tree entry that references it, so it cannot see a second path. ``git ls-tree
    -r`` enumerates every tree entry of one commit, so a blob at two paths within that
    commit's tree shows up twice.

    Every commit in the range is enumerated (:func:`_range_commit_shas`), since a blob may be
    multi-pathed in an intermediate commit and single-pathed, or absent, at the tip. Each
    commit's ``(sha -> paths)`` mapping is unioned, and a candidate is multi-path once its
    unioned path set exceeds one entry, independent of commit order.

    **Bounded cost.** One ``git ls-tree -r`` subprocess runs per commit in the range, never
    per object, each proportional to that commit's tree size. A range with very many commits
    pays proportionally more calls; nothing here silently degrades to a partial scan.
    """
    if not candidate_shas:
        return set()
    # local_sha is always included, even when the range walk already reports it: the tip's
    # own tree is never skipped.
    commit_shas = {local_sha, *_range_commit_shas(repo, local_sha, exclusions)}
    paths_by_sha: dict[str, set[str]] = {}
    for commit_sha in commit_shas:
        result = _run(["git", "ls-tree", "-r", "--full-tree", commit_sha, "--"], repo)
        if result.returncode != 0:
            raise GitObjectReadError(f"git ls-tree -r failed: {_decode(result.stderr).strip()}")
        for line in _lines(result.stdout):
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
    before ever fetching an oversized blob's content.

    A row that is not the 3-field ``<sha> <type> <size>`` shape, or whose size is non-numeric,
    raises the typed error naming the row: every candidate is a sha already confirmed
    reachable, so an unparseable row is a read desync, never silently dropped. A row naming a
    tree is a filtered skip, not a parse failure.
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
    for line in _lines(result.stdout):
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


def _resolve_prior_texts_at_base(repo: Path, base: str, paths: list[str]) -> dict[str, str]:
    """Resolve the published prior text of every distinct path in *paths*, at one *base*.

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

    A ``<base>:<path> missing`` row is an ordinary absence. The row is classified by its
    suffix, not its field count: git echoes the whole input, and a path may hold spaces.
    Any other row that is not the 3-field ``<sha> <type> <size>`` shape, or whose size is
    non-numeric, raises. :func:`_blob_info` keeps the field-count rule, since its input is
    shas, never paths.
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
    check_lines = _lines(check_result.stdout)
    if len(check_lines) != len(unique_paths):
        raise GitObjectReadError(
            "git cat-file --batch-check desynchronised resolving prior content "
            f"(expected {len(unique_paths)} line(s), got {len(check_lines)})"
        )

    under_cap: dict[str, int] = {}
    for path, line in zip(unique_paths, check_lines, strict=True):
        # The "<base>:<path> missing" absence row is classified by suffix, not field count:
        # git echoes the whole input line, so a path with embedded spaces has no fixed count.
        if line.endswith(" missing"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise GitObjectReadError(
                "git cat-file --batch-check: unexpected row shape resolving prior content",
                path=path,
            )
        _sha, obj_type, size_str = parts
        # A path that was a directory at the base resolves to a tree object, not a blob: only
        # objecttype "blob" may supply prior text. Anything else is treated like a missing
        # path, never fetched.
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
            # The offending PATH is a structured field, never embedded in the message: the
            # render boundary (features.chokepoints.push_gate) masks it. `exc` names only the
            # parse detail, never a path.
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


def _resolve_prior_texts(repo: Path, bases: tuple[str, ...], paths: list[str]) -> dict[str, str]:
    """Resolve the published prior text of every distinct path in *paths* across all of
    *bases* (:func:`_publication_boundaries`).

    Tries *bases* in order: each pass resolves :func:`_resolve_prior_texts_at_base` for
    whichever paths the previous passes left unresolved, and stops once every path has an
    answer or every base has been tried. With exactly one boundary, the common case, this is
    a single pass. A path absent at every base stays absent from the returned dict, never a
    synthesized empty string.
    """
    if not paths or not bases:
        return {}
    remaining = list(dict.fromkeys(paths))
    resolved: dict[str, str] = {}
    for base in bases:
        if not remaining:
            break
        found = _resolve_prior_texts_at_base(repo, base, remaining)
        resolved.update(found)
        remaining = [path for path in remaining if path not in found]
    return resolved


def _read_blob_chunk(
    repo: Path,
    chunk_shas: list[str],
    blob_info: dict[str, tuple[str, int]],
    prior_texts: dict[str, str],
    multi_path_shas: set[str],
) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per blob in *chunk_shas*, via a SINGLE batched
    ``git cat-file --batch`` conversation scoped to just this chunk.

    The header-parse pair (the newline lookup and the size-field conversion) surfaces a
    truncated stream or a non-numeric size as :class:`GitObjectReadError`, never a raw
    ``ValueError``. A desynchronised header (``len(parts) != 3``) raises the same error
    rather than yielding a fabricated ``decodable=False`` object: after a desync every later
    header parse is garbage, so the gate aborts rather than invents.

    *prior_texts* (already resolved for this chunk's distinct paths, or empty in the fallback
    shape) supplies each yielded object's ``prior_text``: a lookup miss maps to the explicit
    absence ``None``, never an empty string.

    A sha in *multi_path_shas*, reachable at more than one path in this range, always gets
    ``prior_text=None``, fail-closed, whatever :func:`_resolve_prior_texts` resolved for its
    arbitrary first-seen path. This is the only place the multi-path decision is made.
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
    """At most :data:`_MAX_BLOB_BYTES` of *sha*'s content: leaving the ``with`` closes the
    pipe early, git dies on SIGPIPE and the tail is never fetched. A short read from a failed
    git (unknown oid, a tree) raises :class:`GitObjectReadError`."""
    try:
        proc = subprocess.Popen(  # noqa: S603 — fixed argv, no shell
            ["git", "cat-file", "blob", sha],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:  # same conversion as ``_run``
        raise GitObjectReadError(f"git could not run in {repo}: {exc}") from exc
    with proc:
        prefix = proc.stdout.read(_MAX_BLOB_BYTES) if proc.stdout else b""
    if len(prefix) < _MAX_BLOB_BYTES and proc.returncode != 0:
        raise GitObjectReadError(
            f"git cat-file blob failed reading oversized object {sha} "
            f"(exit {proc.returncode}, {len(prefix)} byte(s) delivered before failure)"
        )
    return prefix


def _read_oversized_blob(repo: Path, sha: str, path: str, size: int) -> ScannedObject:
    """Build the :class:`ScannedObject` for one oversized blob.

    The scanned prefix is decoded ``errors="strict"``: a truncation that lands mid-character
    is reported as undecodable rather than silently repaired, and the matcher falls back to
    the binary skip class like any other undecodable blob (denylist_scan.scan_objects).
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
    bases: tuple[str, ...],
    multi_path_shas: set[str],
) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per blob in *blob_info*.

    Content is read through batched ``git cat-file --batch`` conversations, chunked to
    :data:`_BATCH_CHUNK_SIZE` blobs per call: one subprocess per chunk, never one for the
    whole range. A blob over :data:`_MAX_BLOB_BYTES` is excluded from every batch and read
    through :func:`_read_oversized_blob`'s bounded per-object stream: its first cap bytes are
    scanned and it is reported ``decodable=True``/``oversized=True`` when that prefix is valid
    UTF-8, or ``decodable=False``/``oversized=True`` otherwise. The remainder past the cap is
    never fetched either way.

    With *bases* non-empty, each chunk's prior-side lookup (:func:`_resolve_prior_texts`)
    rides the same loop as the content read, normally two extra batched calls per chunk and
    never per blob, so the peak resident set stays ``chunk_size x cap x 2`` rather than
    growing with the range. An oversized current object never carries prior text: the
    prior-side lookup rides the chunk loop only.
    """
    fetch_shas = [sha for sha, (_, size) in blob_info.items() if size <= _MAX_BLOB_BYTES]
    oversized_shas = [sha for sha, (_, size) in blob_info.items() if size > _MAX_BLOB_BYTES]

    for sha in oversized_shas:
        path, size = blob_info[sha]
        yield _read_oversized_blob(repo, sha, path, size)

    for start in range(0, len(fetch_shas), _BATCH_CHUNK_SIZE):
        chunk = fetch_shas[start : start + _BATCH_CHUNK_SIZE]
        prior_texts: dict[str, str] = {}
        if bases:
            chunk_paths = [blob_info[sha][0] for sha in chunk]
            prior_texts = _resolve_prior_texts(repo, bases, chunk_paths)
        yield from _read_blob_chunk(repo, chunk, blob_info, prior_texts, multi_path_shas)


def unpublished(repo: Path, rev: str) -> list[str]:
    """The commits of *rev* origin does not hold, newest first — the ONE "already
    published" rule (:func:`_base_exclusions`) the push gate and ``unpushed`` share."""
    return _range_commit_shas(repo, rev, _base_exclusions(repo, ZERO_SHA))


class GitSubprocessObjectReader:
    """Subprocess-backed push-range object reader: the sole adapter, with no
    ``GitObjectReader`` port."""

    def unpublished(self, repo: Path, sha: str) -> list[str]:
        """:func:`unpublished` for the gate, failing closed: an unreadable *sha* is
        itself unpublished — never a birth, never an empty range."""
        try:
            return unpublished(repo, sha) if SHA_SHAPE_RE.match(sha) else [sha]
        except GitObjectReadError:
            return [sha]

    def remote_branch(self, repo: Path, branch: str) -> bool:
        """``refs/remotes/origin/<branch>`` exists locally (offline)."""
        ref = f"refs/remotes/origin/{branch}"
        return _run(["git", "rev-parse", "-q", "--verify", ref], repo).returncode == 0

    def netted_specs(self, repo: Path, local_sha: str, remote_sha: str) -> list[str]:
        """The ``specs/`` paths the push nets in. Netted in = present at the tip and
        different from every publication boundary; an empty range nets nothing; a range
        with no boundary (bootstrap) nets the tip's whole ``specs/``. A force-push
        re-judges paths carried from the overwritten tip (it is no boundary)."""
        if not SHA_SHAPE_RE.match(local_sha) or local_sha == ZERO_SHA:
            return []
        exclusions = _base_exclusions(repo, remote_sha)
        if not _range_commit_shas(repo, local_sha, exclusions):
            return []
        bases = _publication_boundaries(repo, local_sha, exclusions)
        runs = [["diff", "--name-only", "--no-renames", "--diff-filter=AM", b] for b in bases]
        netted: set[str] | None = None
        for run in runs or [["ls-tree", "-r", "--name-only"]]:
            result = _run(["git", *run, local_sha, "--", "specs/"], repo)
            if result.returncode != 0:
                raise GitObjectReadError(f"git {run[0]} failed: {_decode(result.stderr).strip()}")
            paths = set(_lines(result.stdout))
            netted = paths if netted is None else netted & paths
        return sorted(netted or ())

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterator[ScannedObject]:
        if not local_sha or local_sha == ZERO_SHA:
            return
        # The shape check of `_is_resolvable_commit`, applied to `local_sha` before it reaches
        # `_rev_list_candidates`'s `git rev-list` argv (CWE-88): an option-shaped value is
        # rejected as a read failure, never interpolated.
        if not SHA_SHAPE_RE.match(local_sha):
            raise GitObjectReadError(f"local_sha is not a valid sha shape: {local_sha!r}")
        # Exclusions are resolved once per call (_base_exclusions: always `--remotes=origin`,
        # plus a resolvable remote_sha) and reused for the range walk and the prior-text
        # anchors (_publication_boundaries, _read_blobs). One formula, whether remote_sha is a
        # real tip or the all-zero sentinel.
        exclusions = _base_exclusions(repo, remote_sha)
        candidates = _rev_list_candidates(repo, local_sha, exclusions)
        blob_info = _blob_info(repo, candidates)
        bases = _publication_boundaries(repo, local_sha, exclusions)
        multi_path_shas = _multi_path_shas(repo, local_sha, exclusions, set(blob_info))
        yield from _read_blobs(repo, blob_info, bases, multi_path_shas)
        # The range's commit message BODIES, never their author or committer headers: the same
        # range :func:`_range_commit_shas` walks above. `prior_text` is never set for these
        # (fail-closed by construction, see `_read_object_bodies`).
        commit_shas = _range_commit_shas(repo, local_sha, exclusions)
        yield from _read_object_bodies(
            repo, commit_shas, kind="commit", path_label=_COMMIT_BODY_PATH
        )
        # A tag-ref push also yields the annotated tag's own body. A lightweight tag has no such
        # object (local_sha already names the commit), so `_is_annotated_tag` yields nothing.
        if _is_annotated_tag(repo, local_sha):
            yield from _read_object_bodies(repo, [local_sha], kind="tag", path_label=_TAG_BODY_PATH)
