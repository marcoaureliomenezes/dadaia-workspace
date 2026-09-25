"""Repository self-scan sentinel — the push publishes, so the scan is full everywhere.

Intent: SENTINEL — the shipped denylist scan over this repository's own tracked tree
(SPEC v0.4.7 FR7; SPEC v0.4.2 FR9 A9.1-A9.3)

This repository is PUBLIC (MIT, published to GitHub and PyPI), so every pushed blob is
published and the full layer set — operator denylist, structural baseline, secret
shapes — applies to every tracked path without exception. That is the
one scope decision, and it lives in the production push gate.

**v0.4.7 FR7 — the tolerated-pairs baseline is gone.** From v0.11.0 to v0.4.6 this
module carried ``_TESTS_SCOPE_BASELINE``: a hand-kept list of ``(path, pattern id)``
rows naming every deliberate, pattern-shaped fixture literal under ``tests/**`` (23
rows at its death). That list was a SECOND scope decision, edited on every fixture
added, moved, renamed or deleted — and the measured cause of a 26-bug loop in which
every single fix was one more literal, baseline or regex edit. It is deleted, at its
root: no tracked fixture file carries a literal any pattern matches any more. A test
that merely needs a home path, an address or a mailbox writes a value the baseline
already excludes by design (``/home/user``, RFC 5737 ranges, ``@example.invalid``); a
test that must prove the scanner FIRES on a realistic shape composes it at run time
through :mod:`tests.helpers.privacy_fixtures`, so the shape exists only in memory.

The assertion is therefore a plain ZERO over the whole tracked tree
(:func:`test_no_denylist_hit_anywhere_in_the_tracked_tree`) — no tolerated rows, no
shrink-only bookkeeping, no path predicate. A new matching literal anywhere fails this
test, and the fix is always the same: make the value synthetic where it is written.

``specs/audits/_archive/**`` stays excluded, and that is NOT a tolerance: a blob
already published there is exempt from the real push gate by construction (a rename
reuses the blob sha, so an archived file is never a NEW object of a future push
range), so scanning it here would fail forever for content the real gate never
re-flags. SPEC v0.4.2 FR9/GRILL P14 narrows even that: an archive-prefixed path whose
blob sha is absent from ``HEAD^``'s tree — genuinely new content authored straight
into the archive — is added BACK into scope. ``HEAD^`` unavailable (a shallow clone or
the initial commit) degrades to no add-back, never a failure. See
:func:`_archive_paths_new_at_head` and the three ``tmp_path`` fixtures below.

The operator's own private denylist is excluded: it is operator-private and varies by
machine, so a test depending on it would not be deterministic.

Measured: ~950 tracked files, well under 5 MB, read through ONE ``git ls-files``
subprocess plus in-process file reads — far inside the integration tier's 60 s budget.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.models.git_scan import ScannedObject
from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects
from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns
from tests.helpers.privacy_fixtures import macos_home_path
from tests.helpers.scan_population import assert_populated

# v0.11.0 entry #29: matches the six sibling integration modules that also drive real
# subprocess/filesystem work (e.g. test_git_object_reader.py) — carrying BOTH marks
# keeps this sentinel collected under `-m integration`, `-m slow` and
# `-m "not quarantine"` (A3.5), not just the slow selector alone.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="reads ~990 tracked files through a real git subprocess"),
]

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCAN_SCOPE = ("dadaia_workspace", "specs", "tests", ".github", "docs")
_EXTRA_PATHS = ("pyproject.toml", "README.md", "CHANGELOG.md")
_EXCLUDED_PREFIXES = ("specs/audits/_archive/",)
_TIMEOUT_S = 60


def _tracked_paths(
    repo: Path, scope: tuple[str, ...], *, excluded_prefixes: tuple[str, ...]
) -> list[str]:
    """Every file tracked at HEAD/the index under *scope* — never an untracked file
    (e.g. an in-progress draft document not yet committed) — excluding FROZEN/
    dispositioned archive trees, **except** an archive-prefixed path whose blob is new
    at HEAD (SPEC v0.4.2 FR9/GRILL P14 — see :func:`_archive_paths_new_at_head` and the
    module docstring)."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "-s", "--", *scope],
        cwd=repo,
        capture_output=True,
        timeout=_TIMEOUT_S,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    raw = result.stdout.decode("utf-8", errors="replace")
    entries = [e for e in raw.split("\0") if e]
    # each entry is "<mode> <sha> <stage>\t<path>" (git ls-files -s output shape).
    blob_sha_by_path: dict[str, str] = {}
    for entry in entries:
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) >= 2 and path:
            blob_sha_by_path[path] = parts[1]

    all_paths = list(blob_sha_by_path)
    kept = [p for p in all_paths if not p.startswith(excluded_prefixes)]
    archived = [p for p in all_paths if p.startswith(excluded_prefixes)]
    kept.extend(_archive_paths_new_at_head(repo, archived, blob_sha_by_path))
    return kept


def _archive_paths_new_at_head(
    repo: Path, archived_paths: list[str], blob_sha_by_path: dict[str, str]
) -> list[str]:
    """SPEC v0.4.2 FR9/GRILL P14: an archive-prefixed path is added back into the scan
    **iff** its blob sha is absent from ``HEAD^``'s tree — genuinely new content
    authored straight into the archive, never a rename/relocation of a blob that
    already existed (a ``git mv`` republishes the same sha and stays excluded — the
    FROZEN<->scan invariant, A9.2). ``HEAD^`` unavailable (a shallow clone or the
    initial commit) degrades to no add-back — exactly today's behaviour (A9.3), never a
    failure. One additional subprocess (``git ls-tree -r HEAD^``), only when there is at
    least one archived path to weigh."""
    if not archived_paths:
        return []
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--full-tree", "HEAD^"],
        cwd=repo,
        capture_output=True,
        timeout=_TIMEOUT_S,
    )
    if result.returncode != 0:
        return []
    parent_blob_shas: set[str] = set()
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        meta, _, _path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            parent_blob_shas.add(parts[2])
    return [p for p in archived_paths if blob_sha_by_path.get(p) not in parent_blob_shas]


def _scan_object_for(repo: Path, rel_path: str) -> ScannedObject:
    """Read *rel_path* off disk (one filesystem read, never a per-file subprocess —
    the very antipattern this remediation removed from the production adapter)."""
    try:
        raw = (repo / rel_path).read_bytes()
    except OSError:
        return ScannedObject(path=rel_path, sha=rel_path, text="", decodable=False)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ScannedObject(path=rel_path, sha=rel_path, text="", decodable=False)
    return ScannedObject(path=rel_path, sha=rel_path, text=text, decodable=True)


def test_no_denylist_hit_anywhere_in_the_tracked_tree() -> None:
    """v0.4.7 FR7: the shipped baseline layer, run over EVERY tracked
    path of this repository, report ZERO hits — no tolerated-pairs list, no per-path
    exception. A commit that publishes a matching literal anywhere (production,
    specs, tests, workflows, docs or the packaging metadata) fails HERE, before the
    push gate refuses it for real, and is fixed where the value is written."""
    paths = _tracked_paths(
        _REPO_ROOT, _SCAN_SCOPE + _EXTRA_PATHS, excluded_prefixes=_EXCLUDED_PREFIXES
    )
    # v0.4.5 FR5 (scan-test-vacuity-guard): `pyproject.toml` is unconditionally
    # in-scope (_EXTRA_PATHS) and pins that `git ls-files` walked the real repo root.
    assert_populated(paths, sentinel="pyproject.toml")

    objects = [_scan_object_for(_REPO_ROOT, path) for path in paths]
    baseline_patterns = load_baseline_patterns()

    outcome = scan_objects(objects, terms=(), patterns=baseline_patterns)

    if outcome.hits:
        offenders = "\n".join(
            f"  {hit.path}:{hit.line} — masked '{hit.masked_term}' ({hit.source_layer})"
            for hit in outcome.hits[:10]
        )
        pytest.fail(
            f"{len(outcome.hits)} tracked file(s) would be refused by the push-range "
            "denylist scan. This repository is public: fix the literal where it is "
            "written (a value the baseline already excludes, or a shape composed at "
            "run time via tests.helpers.privacy_fixtures) — there is no tolerated-pairs "
            f"baseline to add it to:\n{offenders}"
        )


# --- SPEC v0.4.2 FR9/GRILL P14 — archive-authored blobs (A9.1-A9.3) -------------------
#
# These three tests drive a throwaway git repo under ``tmp_path`` (never this repo's own
# HEAD — the archive-authored/rename fixtures need a controlled, private history), the
# same pattern ``test_git_object_reader.py`` already establishes for the same reason.


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init"], path)
    _git(["config", "user.email", "t@example.com"], path)
    _git(["config", "user.name", "T"], path)


def _commit(path: Path, message: str) -> str:
    _git(["add", "-A"], path)
    _git(["commit", "-m", message], path)
    return _git(["rev-parse", "HEAD"], path).stdout.strip()


def test_archive_authored_blob_is_scanned_and_fails(tmp_path: Path) -> None:
    """A9.1: a file AUTHORED directly under ``specs/audits/_archive/`` (a genuinely
    new blob, never published before) carrying a baseline-matching literal is
    scanned — and fails — rather than hidden by the wholesale archive exclusion."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README.md").write_text("clean\n", encoding="utf-8")
    _commit(repo, "c1 — a real HEAD^")

    archive_dir = repo / "specs" / "audits" / "_archive"
    archive_dir.mkdir(parents=True)
    (archive_dir / "CLOSURE.md").write_text(
        f"backed up under {macos_home_path()}\n", encoding="utf-8"
    )
    _commit(repo, "c2 — author a CLOSURE straight into the archive")

    paths = _tracked_paths(repo, ("specs",), excluded_prefixes=_EXCLUDED_PREFIXES)
    assert "specs/audits/_archive/CLOSURE.md" in paths, (
        "a genuinely new archive-authored blob must be added back into scan scope"
    )

    objects = [_scan_object_for(repo, path) for path in paths]
    baseline_patterns = load_baseline_patterns()
    outcome = scan_objects(objects, terms=(), patterns=baseline_patterns)
    assert any(hit.path == "specs/audits/_archive/CLOSURE.md" for hit in outcome.hits), (
        "the archive-authored blob's baseline-matching literal must surface as a hit"
    )


def test_archive_rename_of_an_existing_blob_stays_excluded(tmp_path: Path) -> None:
    """A9.2: a ``git mv`` of an EXISTING published file into
    ``specs/audits/_archive/`` republishes the SAME blob sha (no new object) — it
    must stay excluded, preserving the FROZEN<->scan invariant (R5's guard against
    A9.1's "new" reading being too loose)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "specs").mkdir()
    (repo / "specs" / "old-doc.md").write_text(
        f"backed up under {macos_home_path()}\n", encoding="utf-8"
    )
    _commit(repo, "c1 — publish the doc outside the archive")

    (repo / "specs" / "audits" / "_archive").mkdir(parents=True)
    _git(["mv", "specs/old-doc.md", "specs/audits/_archive/old-doc.md"], repo)
    _commit(repo, "c2 — relocate into the archive via git mv")

    paths = _tracked_paths(repo, ("specs",), excluded_prefixes=_EXCLUDED_PREFIXES)
    assert "specs/audits/_archive/old-doc.md" not in paths, (
        "a renamed/relocated blob that already existed must stay excluded"
    )


def test_missing_head_parent_degrades_to_prior_behaviour(tmp_path: Path) -> None:
    """A9.3: with no ``HEAD^`` (the initial commit — a shallow clone degrades
    identically), the sentinel behaves exactly as before this FR: archive paths stay
    excluded, and resolving the scope never raises."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "specs" / "audits" / "_archive").mkdir(parents=True)
    (repo / "specs" / "audits" / "_archive" / "CLOSURE.md").write_text(
        f"backed up under {macos_home_path()}\n", encoding="utf-8"
    )
    _commit(repo, "c1 — the initial commit, no parent")

    paths = _tracked_paths(repo, ("specs",), excluded_prefixes=_EXCLUDED_PREFIXES)
    assert "specs/audits/_archive/CLOSURE.md" not in paths
