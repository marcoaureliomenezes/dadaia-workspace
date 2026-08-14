"""Repository self-scan regression (code-reviewer MEDIUM finding, v0.9.0 pre-PR review).

Intent: SENTINEL — denylist-scan self-consistency over this repo's own tracked content

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
appears here before it is committed), and asserts zero hits.

**Scope, and why it is bounded rather than the whole tree.** A first full-tree pass
(``dadaia_workspace/`` + ``specs/`` + ``tests/`` + ``pyproject.toml``, every tracked file)
found 46 hits, not 0 — this is the exact "50 latent blockers" wider probe the
code-reviewer already named in the CRITICAL finding. One class was resolved as part of
THIS remediation (live, actively-edited, non-archived source — the same character as the
CRITICAL finding itself, discovered only because this test exists):

* ``dadaia_workspace/features/telemetry/aggregator/runtimes.py`` and
  ``infrastructure/runtime_config.py`` false-positived ``internal-hostname`` on the
  stdlib ``Path.home()`` idiom — fixed at the root with a narrow baseline carve-out
  (``privacy_baseline.json`` v4), proven by
  ``test_baseline_excludes_the_stdlib_pathlib_home_method_call``.

The remainder is excluded from THIS test's scope, per the operator's ratified v0.9.0
pre-PR decision ("keep whole-blob matching; prior-published-term amnesty goes to
backlog, not you") — these are pre-existing, out-of-scope-for-this-remediation classes,
not new regressions this session introduced or is authorized to bulk-fix:

* ``specs/_archive/**`` and ``specs/audits/_archive/**`` — FROZEN/dispositioned archives.
  A tainted blob already published there is exempt from the real push gate by
  construction (the FROZEN<->scan invariant, ``sdd-gate-v3`` memory atom: a rename
  reuses the blob, so an archived file is never a NEW object of a future push range).
  Scanning them here would fail this sentinel forever for content the real gate will
  never re-flag.
* ``tests/**`` — carries ~30 additional hits, all deliberate synthetic-but-pattern-
  shaped fixture literals (fake IPv4s, ``t@example.com``-style addresses, ``/home/...``
  fixture paths) that predate this session. A systematic pass to make every test
  fixture baseline-clean (or to redesign matching itself, e.g. diff-scoped rather than
  whole-blob) is exactly the "prior-published-term amnesty" backlog item the operator
  named, not a change this remediation session is authorized to make.

So the scope actually asserted here is ``dadaia_workspace/`` + ``specs/`` (excluding both
archive trees) + ``pyproject.toml`` — every file in that scope that is NOT historically
FROZEN/dispositioned or deliberate test fixture data. Measured at the time this test was
written: ~513 files / well under 5 MB, read through ONE ``git ls-files`` subprocess call
plus in-process file reads (no per-file subprocess) — well under a second, far inside the
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
``test_denylist_scan.py``).

The operator's own private denylist is intentionally NOT included either, for the same
reason: it is operator-private by design and varies by machine.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.git_object_reader import ScannedObject
from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects
from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

pytestmark = pytest.mark.slow(reason="reads ~500 tracked files through a real git subprocess")

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCAN_SCOPE = ("dadaia_workspace", "specs")
_EXTRA_PATHS = ("pyproject.toml",)
_EXCLUDED_PREFIXES = ("specs/_archive/", "specs/audits/_archive/")
_TIMEOUT_S = 60

#: Deterministic by design — see the module docstring's "Foreign-slug layer" section.
_NO_FOREIGN_SLUGS: tuple[str, ...] = ()


def _tracked_paths(
    repo: Path, scope: tuple[str, ...], *, excluded_prefixes: tuple[str, ...]
) -> list[str]:
    """Every file tracked at HEAD/the index under *scope* — never an untracked file
    (e.g. an in-progress draft document not yet committed) — excluding FROZEN/
    dispositioned archive trees (see the module docstring)."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", *scope],
        cwd=repo,
        capture_output=True,
        timeout=_TIMEOUT_S,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    raw = result.stdout.decode("utf-8", errors="replace")
    all_paths = [p for p in raw.split("\0") if p]
    return [p for p in all_paths if not p.startswith(excluded_prefixes)]


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


def test_this_repos_own_tracked_tree_scans_clean() -> None:
    """The single regression that would have caught the v0.9.0 pre-PR CRITICAL finding:
    the shipped baseline + foreign-slug layers, run over this repo's own tracked
    content, must report zero hits. A future commit that republishes a matching literal
    fails THIS test instead of only being caught by a manual pre-PR diff review."""
    paths = _tracked_paths(
        _REPO_ROOT, _SCAN_SCOPE + _EXTRA_PATHS, excluded_prefixes=_EXCLUDED_PREFIXES
    )
    assert paths, "scope must resolve at least one tracked file — an empty scan proves nothing"

    objects = [_scan_object_for(_REPO_ROOT, path) for path in paths]
    baseline = load_baseline_patterns()

    outcome = scan_objects(objects, terms=(), patterns=baseline, slugs=_NO_FOREIGN_SLUGS)

    if outcome.hits:
        offenders = "\n".join(
            f"  {hit.path}:{hit.line} — masked '{hit.masked_term}' ({hit.source_layer})"
            for hit in outcome.hits[:10]
        )
        pytest.fail(
            f"{len(outcome.hits)} tracked file(s) under {_SCAN_SCOPE + _EXTRA_PATHS} would "
            f"be refused by the push-range denylist scan:\n{offenders}"
        )
