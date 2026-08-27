"""Repository self-scan regression (code-reviewer MEDIUM finding, v0.9.0 pre-PR review).

Intent: SENTINEL — denylist-scan self-consistency over this repo's own tracked content
(SPEC v0.9.0 FR3/FR5/FR6; SPEC v0.11.0 FR3, A3.1-A3.6; SPEC v0.4.2 FR9, A9.1-A9.4)

The CRITICAL finding this test exists to catch: the push-range denylist scan THIS
release ships refused THIS repository's own release-closing commits, because published
content (``pyproject.toml``'s author email, ``specs/memory/architecture.md``'s quoted
synthetic git identity) already carried a baseline match. Every previous "scan is clean"
verification was a one-off manual run recorded in prose (CLOSURE ``## Drifts``, ALPHA-1-QA
V7) — nothing in the suite failed when a commit reintroduced matching content, which is
exactly what happened three commits after the v0.9.0 remediation landed.

This runs the SAME shipped baseline patterns plus the foreign-slug layer the push gate
uses, over this repository's own HEAD **tracked** tree (``git ls-files`` — never the
working tree's untracked scratch, so an in-progress draft document correctly never
appears here before it is committed).

**v0.11.0 FR3 — the scope now includes ``tests/**`` behind a SHRINK-ONLY baseline.**
The v0.9.0 sentinel excluded ``tests/**`` entirely (~30 deliberate synthetic fixture
literals it could not distinguish from a genuine new leak). That gap is closed here,
not by whitelisting the directory again but by naming EVERY surviving fixture literal
explicitly, as a literal, enumerated ``(path, pattern id)`` baseline
(:data:`_TESTS_SCOPE_BASELINE`) measured directly against this commit — 29 rows at
authoring time (14 ``home-abs-path``, 9 ``email-address``, 5 ``ipv4-literal``, 1
``secret-token``), matching the SPEC v0.11.0 §1 census exactly. Shrunk to 28 rows (13
``home-abs-path``) at v0.12.0 T-120-03: ``tests/unit/test_backlog_ledger_writer.py``
was deleted as a recorded supersession (its subject, ``ledger_writer.py``, retired by
FR4) and its row removed per this test's own shrink-only contract. Shrunk to 27 rows
at v0.5.0 T-050-08: ``tests/unit/features/bugs/test_jsonl_bug_store.py`` was deleted
(its subject, ``JsonlBugStore``, retired by FR2) and its row removed. Shrunk to 25 rows
at v0.5.0 T-050-18 (FR9, hooks de-slop): ``tests/integration/
test_precommit_backlog_scoping.py`` (imported ``_run_backlog_doctor_gate``, the symbol
this FR deletes) and ``tests/e2e/features/test_backlog_precommit.py`` (its entire
premise — pre-commit *blocking* a bad stage — this FR deletes) were both DELETED under
a recorded ``qa-engineer`` verdict, replaced by three CONTRACT-tier fixtures in
``tests/contract/test_hooks_publication_boundary.py`` — their two ``email-address``
rows removed. Two properties make the baseline honest, asserted in the two directions
below:

1. **No hit outside the baseline** (:func:`test_no_hit_outside_the_shrink_only_baseline`)
   — a NEW matching literal anywhere in the scanned scope (``dadaia_workspace/`` and
   ``specs/`` still at a strict ZERO; ``tests/**`` at exactly the 29 baseline rows and
   nothing more) fails this test.
2. **Every baseline row still produces a hit**
   (:func:`test_every_baseline_row_still_produces_a_hit`) — shrink-only. A row whose
   file has been cleaned fails THIS test until the row is deleted, so the count can
   only go DOWN, turning the 29-blocker figure from review-pinned prose into
   test-pinned fact.

**This baseline is NOT the forbidden FR10 amnesty list (grill P7).** It is a TEST
ASSERTION baseline, read only by this test module. The production matcher
(``features/chokepoints/denylist_scan.py``) and the adapter
(``infrastructure/git_objects.py``) never import or read it — FR1's amnesty (T-110-10)
derives suppression entirely from a scanned object's OWN published prior git content,
never from any list. A4.1's source-scan contract test
(``test_denylist_scan.py::test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source``)
stays unmodified and green, proving the production module carries no such construct.

**Why the ``dadaia_workspace``/``specs`` classes still resolve rather than joining the
baseline.** One class was resolved as part of the v0.9.0 remediation (live,
actively-edited, non-archived source — the same character as the CRITICAL finding
itself, discovered only because this test exists):

* ``dadaia_workspace/features/telemetry/aggregator/runtimes.py`` and
  ``infrastructure/runtime_config.py`` false-positived ``internal-hostname`` on the
  stdlib ``Path.home()`` idiom — fixed at the root with a narrow baseline carve-out
  (``privacy_baseline.json`` v4), proven by
  ``test_baseline_excludes_the_stdlib_pathlib_home_method_call``.

``specs/_archive/**`` and ``specs/audits/_archive/**`` stay excluded — FROZEN/
dispositioned archives. A tainted blob already published there is exempt from the real
push gate by construction (the FROZEN<->scan invariant, ``sdd-gate-v3`` memory atom: a
rename reuses the blob, so an archived file is never a NEW object of a future push
range). Scanning them here would fail this sentinel forever for content the real gate
will never re-flag.

**SPEC v0.4.2 FR9/GRILL P14 — the exclusion is no longer wholesale.** A path under an
archive prefix is added BACK into scan scope iff its blob sha is absent from ``HEAD^``'s
tree — i.e. genuinely new content authored straight into the archive (a CLOSURE or QA
document written directly there), never a rename/relocation of a blob that already
existed (a ``git mv`` republishes the same sha and stays excluded, preserving the
FROZEN<->scan invariant exactly as before this FR — R5's guard). ``HEAD^`` unavailable
(a shallow clone or the initial commit) degrades to no add-back, i.e. exactly today's
behaviour, never a failure. See :func:`_archive_paths_new_at_head` and the three
dedicated fixtures below (A9.1-A9.3), each driving a throwaway ``tmp_path`` repo rather
than this repository's own HEAD. A9.4: this FR leaves :data:`_TESTS_SCOPE_BASELINE`
untouched — the two positive fixtures compose their ``users-abs-path`` literal at
runtime (:func:`_archive_fixture_literal`) precisely so it never appears contiguously in
this module's own tracked source.

So the scope asserted here is ``dadaia_workspace/`` + ``specs/`` (excluding both archive
trees) + ``tests/`` + ``pyproject.toml`` — every tracked file, with ``tests/**`` alone
carrying the shrink-only baseline exception (29 rows at authoring time, 28 after
v0.12.0 T-120-03, 27 after v0.5.0 T-050-08). Measured at the time this test was written:
~990 files / well under 5 MB, read through ONE ``git ls-files`` subprocess call plus
in-process file reads (no per-file subprocess) — well under a second, far inside the
integration tier's 60 s budget.

**Foreign-slug layer, and why it always runs with an EMPTY slug set here.** The real CLI
derives foreign slugs from `<workspace>/repos/` at push time — deliberately NOT
reproduced here: doing so would make this test's outcome depend on which sibling repos
happen to be checked out in the surrounding workspace on whichever machine runs it (this
repo's own tracked content already collides, as a whole word, with at least one
operator-local sibling repo slug seen while writing this test — a real but
environment-specific fact, not a defect in THIS repo). A test whose pass/fail depends on
an uncontrolled environment fact is not deterministic (tests/AGENTS.md admission filter).
The layer still runs — ``scan_objects`` still receives and processes ``slugs`` — exactly
as it would for this repo checked out standalone with no outer ``repos/`` directory (a
from-scratch clone or a bare CI checkout), which is the one deterministic case. Slug
word-boundary matching itself is proven correct elsewhere (A3.2/A3.3 in
``test_denylist_scan.py``). This is ALSO SPEC v0.11.0 A3.1's "deterministic empty
foreign-slug set... unchanged" — the widened FR5 registry-derived layer (T-110-13) does
not touch this test.

The operator's own private denylist is intentionally NOT included either, for the same
reason: it is operator-private by design and varies by machine.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.git_object_reader import ScannedObject
from dadaia_workspace.features.chokepoints.denylist_scan import Hit, scan_objects
from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns
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
_SCAN_SCOPE = ("dadaia_workspace", "specs", "tests")
_EXTRA_PATHS = ("pyproject.toml",)
_EXCLUDED_PREFIXES = ("specs/_archive/", "specs/audits/_archive/")
_TIMEOUT_S = 60

#: Deterministic by design — see the module docstring's "Foreign-slug layer" section.
_NO_FOREIGN_SLUGS: tuple[str, ...] = ()

#: SPEC v0.11.0 FR3 — the shrink-only ``tests/**`` baseline (A3.2). Measured directly
#: against this commit via a one-off enumeration run
#: (``.dadaia/tmp/software-engineer/20260815/t-110-12-baseline-enumeration.txt``); every
#: row here is a pre-existing, deliberate synthetic-but-pattern-shaped fixture literal
#: (fake IPv4s, ``t@example.com``-style addresses, ``/home/...`` fixture paths, a
#: fixture-shaped token) that predates T-110-12 — NOT a scan suppression list (see the
#: module docstring). 27 rows (shrunk from 29 at v0.12.0 T-120-03 — the
#: ``test_backlog_ledger_writer.py`` row removed with its file, a recorded
#: supersession): 13 ``home-abs-path``, 9 ``email-address``, 5 ``ipv4-literal``,
#: 1 ``secret-token``. The v0.11.0 §1 census (29/14) is the authoring-time baseline.
#:
#: Shrunk to 25 rows at v0.5.0 T-050-18 (FR9, hooks de-slop): both
#: ``tests/integration/test_precommit_backlog_scoping.py`` and ``tests/e2e/features/
#: test_backlog_precommit.py`` were DELETED (their ``email-address`` rows removed with
#: them) — 13 ``home-abs-path``, 7 ``email-address``, 4 ``ipv4-literal``,
#: 1 ``secret-token``.
#:
#: SPEC v0.4.2 FR10/GRILL P15/D9 — +2 rows at T-042-11 (30 total): the baseline v5
#: cross-platform home-path patterns (``users-abs-path``, ``windows-users-path``) each
#: brought their OWN dedicated fixture file
#: (``tests/fixtures/privacy_baseline/{macos,windows}_home_path.txt``, synthetic
#: ``zz-fixture-user`` literal) — not an existing test module, because
#: ``denylist_scan.scan_objects`` reports at most ONE hit per scanned object (FR5's
#: one-line-per-offending-object shape), so a literal added anywhere in an
#: already-hit-bearing module (e.g. this file's existing ``ipv4-literal``/
#: ``email-address`` rows) would be silently masked by that earlier hit and never
#: individually provable here.
#:
#: Bug ``push-gate-refuses-its-own-privacy-baseline-fixtures`` (HIGH, found running the
#: real chokepoint for the v0.4.2 ship review) — -2 rows, back to 28 total: those two
#: dedicated fixture files were NEW blobs at NEW paths on first publication, so the
#: prior-published-term amnesty granted them nothing and the real push-range denylist
#: scan refused them, even though this shrink-only baseline correctly tolerated them.
#: Root-cause fix: both files are retired; ``tests/unit/test_public_assets.py`` now
#: composes the same two literals (and the CR-2 prose form) at RUNTIME via
#: ``_macos_home_path_fixture``/``_windows_home_path_fixture``, the same technique this
#: module's own :func:`_archive_fixture_literal` already uses — never contiguous in
#: tracked source, so there is no longer a row for either file here.
_TESTS_SCOPE_BASELINE: tuple[tuple[str, str], ...] = (
    ("tests/e2e/test_pre_commit_presence_gate.py", "email-address"),
    ("tests/fixtures/telemetry/sample_session_basic.jsonl", "home-abs-path"),
    ("tests/fixtures/telemetry/sample_session_malformed_mid.jsonl", "home-abs-path"),
    ("tests/fixtures/telemetry/sample_session_truncated.jsonl", "home-abs-path"),
    ("tests/integration/infrastructure/test_git_subprocess.py", "email-address"),
    ("tests/integration/test_context_alive_scaffold_commit.py", "email-address"),
    ("tests/integration/test_dead_review_gate.py", "email-address"),
    ("tests/integration/test_git_subprocess.py", "email-address"),
    ("tests/integration/test_public_assets.py", "ipv4-literal"),
    ("tests/integration/test_telemetry_end_to_end_aggregation.py", "home-abs-path"),
    ("tests/unit/features/migrate/test_bugs_jsonl.py", "home-abs-path"),
    ("tests/unit/features/panel/test_no_auth_contract.py", "ipv4-literal"),
    ("tests/unit/features/server_registry/test_scan.py", "ipv4-literal"),
    ("tests/unit/features/telemetry/test_allowlist.py", "home-abs-path"),
    ("tests/unit/features/telemetry/test_dao.py", "home-abs-path"),
    ("tests/unit/features/telemetry/test_reader_claude.py", "home-abs-path"),
    ("tests/unit/features/telemetry/test_reader_codex.py", "home-abs-path"),
    ("tests/unit/features/telemetry/test_reader_kimi.py", "home-abs-path"),
    ("tests/unit/hooks/test_venv_guard.py", "home-abs-path"),
    ("tests/unit/infrastructure/test_git_subprocess_diff.py", "email-address"),
    ("tests/unit/infrastructure/test_git_subprocess_unit.py", "email-address"),
    ("tests/unit/infrastructure/test_runtime_config_kimi.py", "home-abs-path"),
    ("tests/unit/test_backlog_models.py", "home-abs-path"),
    ("tests/unit/test_public_assets.py", "ipv4-literal"),
    ("tests/unit/test_spec_context_service.py", "secret-token"),
)


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


def _pattern_id(hit: Hit) -> str:
    """Extract the baseline pattern id from a ``Hit.source_layer`` string shaped like
    ``"baseline pattern '<id>'"`` (the foreign-slug/operator-term layers never fire
    here — ``_NO_FOREIGN_SLUGS`` and no operator terms are passed)."""
    layer = hit.source_layer
    prefix, suffix = "baseline pattern '", "'"
    if layer.startswith(prefix) and layer.endswith(suffix):
        return layer[len(prefix) : -len(suffix)]
    return layer


def test_no_hit_outside_the_shrink_only_baseline() -> None:
    """SPEC v0.11.0 A3.3: the shipped baseline + foreign-slug layers, run over this
    repo's own tracked content (``dadaia_workspace/`` + ``specs/`` + ``tests/`` +
    ``pyproject.toml``), must report NO hit outside :data:`_TESTS_SCOPE_BASELINE` — a
    future commit that republishes a matching literal anywhere in
    ``dadaia_workspace/``/``specs/`` (still a strict zero), or introduces a NEW
    fixture literal under ``tests/**`` not already on the baseline, fails THIS test
    instead of only being caught by a manual pre-PR diff review."""
    paths = _tracked_paths(
        _REPO_ROOT, _SCAN_SCOPE + _EXTRA_PATHS, excluded_prefixes=_EXCLUDED_PREFIXES
    )
    # v0.4.5 FR5 (scan-test-vacuity-guard): the non-empty half already existed; this
    # task adds the sentinel half — `pyproject.toml` is unconditionally in-scope
    # (_EXTRA_PATHS) and pins that `git ls-files` actually walked the real repo root.
    assert_populated(paths, sentinel="pyproject.toml")

    objects = [_scan_object_for(_REPO_ROOT, path) for path in paths]
    baseline_patterns = load_baseline_patterns()

    outcome = scan_objects(objects, terms=(), patterns=baseline_patterns, slugs=_NO_FOREIGN_SLUGS)

    baseline_set = set(_TESTS_SCOPE_BASELINE)
    unexpected = [hit for hit in outcome.hits if (hit.path, _pattern_id(hit)) not in baseline_set]
    if unexpected:
        offenders = "\n".join(
            f"  {hit.path}:{hit.line} — masked '{hit.masked_term}' ({hit.source_layer})"
            for hit in unexpected[:10]
        )
        pytest.fail(
            f"{len(unexpected)} tracked file(s) under {_SCAN_SCOPE + _EXTRA_PATHS} would be "
            "refused by the push-range denylist scan and are NOT on the shrink-only "
            "tests/** baseline (dadaia_workspace/specs must stay at a strict zero; a "
            "genuinely new tests/** literal must be fixed at the root, never added to "
            f"the baseline):\n{offenders}"
        )


def test_every_baseline_row_still_produces_a_hit() -> None:
    """SPEC v0.11.0 A3.4: shrink-only. A baseline row whose file has been cleaned
    fails THIS test until the row is DELETED from :data:`_TESTS_SCOPE_BASELINE` — the
    count can only go down, turning the 29-blocker figure into test-pinned fact rather
    than review-pinned prose that silently rots."""
    objects = [_scan_object_for(_REPO_ROOT, path) for path, _pid in _TESTS_SCOPE_BASELINE]
    baseline_patterns = load_baseline_patterns()

    outcome = scan_objects(objects, terms=(), patterns=baseline_patterns, slugs=_NO_FOREIGN_SLUGS)

    observed = {(hit.path, _pattern_id(hit)) for hit in outcome.hits}
    stale = [row for row in _TESTS_SCOPE_BASELINE if row not in observed]
    if stale:
        rows = "\n".join(f"  {path} ({pattern_id})" for path, pattern_id in stale)
        pytest.fail(
            f"{len(stale)} baseline row(s) no longer produce a hit — the underlying "
            "file has been cleaned. DELETE these rows from _TESTS_SCOPE_BASELINE (the "
            f"count only ever shrinks):\n{rows}"
        )


# --- SPEC v0.4.2 FR9/GRILL P14 — archive-authored blobs (A9.1-A9.4) -------------------
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


def _archive_fixture_literal() -> str:
    """A ``users-abs-path`` baseline match, composed at runtime so THIS module's own
    tracked source never contains the substring contiguously — writing it inline would
    make :func:`test_no_hit_outside_the_shrink_only_baseline` see a NEW hit in this very
    file and force a ``_TESTS_SCOPE_BASELINE`` row, which A9.4 says this FR must not
    add. The composed text lands only inside an ephemeral ``tmp_path`` repo, never
    committed here."""
    return "/Users/" + "zz-fixture-user" + "/notes"


def test_archive_authored_blob_is_scanned_and_fails(tmp_path: Path) -> None:
    """A9.1: a file AUTHORED directly under ``specs/_archive/`` (a genuinely new blob,
    never published before) carrying a baseline-matching literal is scanned — and
    fails — rather than hidden by the wholesale archive exclusion."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README.md").write_text("clean\n", encoding="utf-8")
    _commit(repo, "c1 — a real HEAD^")

    archive_dir = repo / "specs" / "_archive"
    archive_dir.mkdir(parents=True)
    (archive_dir / "CLOSURE.md").write_text(
        f"backed up under {_archive_fixture_literal()}\n", encoding="utf-8"
    )
    _commit(repo, "c2 — author a CLOSURE straight into the archive")

    paths = _tracked_paths(repo, ("specs",), excluded_prefixes=_EXCLUDED_PREFIXES)
    assert "specs/_archive/CLOSURE.md" in paths, (
        "a genuinely new archive-authored blob must be added back into scan scope"
    )

    objects = [_scan_object_for(repo, path) for path in paths]
    baseline_patterns = load_baseline_patterns()
    outcome = scan_objects(objects, terms=(), patterns=baseline_patterns, slugs=_NO_FOREIGN_SLUGS)
    assert any(hit.path == "specs/_archive/CLOSURE.md" for hit in outcome.hits), (
        "the archive-authored blob's baseline-matching literal must surface as a hit"
    )


def test_archive_rename_of_an_existing_blob_stays_excluded(tmp_path: Path) -> None:
    """A9.2: a ``git mv`` of an EXISTING published file into ``specs/_archive/``
    republishes the SAME blob sha (no new object) — it must stay excluded, preserving
    the FROZEN<->scan invariant (R5's guard against A9.1's "new" reading being too
    loose)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "specs").mkdir()
    (repo / "specs" / "old-doc.md").write_text(
        f"backed up under {_archive_fixture_literal()}\n", encoding="utf-8"
    )
    _commit(repo, "c1 — publish the doc outside the archive")

    (repo / "specs" / "_archive").mkdir()
    _git(["mv", "specs/old-doc.md", "specs/_archive/old-doc.md"], repo)
    _commit(repo, "c2 — relocate into the archive via git mv")

    paths = _tracked_paths(repo, ("specs",), excluded_prefixes=_EXCLUDED_PREFIXES)
    assert "specs/_archive/old-doc.md" not in paths, (
        "a renamed/relocated blob that already existed must stay excluded"
    )


def test_missing_head_parent_degrades_to_prior_behaviour(tmp_path: Path) -> None:
    """A9.3: with no ``HEAD^`` (the initial commit — a shallow clone degrades
    identically), the sentinel behaves exactly as before this FR: archive paths stay
    excluded, and resolving the scope never raises."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "specs" / "_archive").mkdir(parents=True)
    (repo / "specs" / "_archive" / "CLOSURE.md").write_text(
        f"backed up under {_archive_fixture_literal()}\n", encoding="utf-8"
    )
    _commit(repo, "c1 — the initial commit, no parent")

    paths = _tracked_paths(repo, ("specs",), excluded_prefixes=_EXCLUDED_PREFIXES)
    assert "specs/_archive/CLOSURE.md" not in paths
