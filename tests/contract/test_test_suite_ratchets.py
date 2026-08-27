"""Intent: CONTRACT — 0.5.0 A22.10

The five test-suite ratchets (**V26**–**V30**), pinned in **one** file per T-050-18A
(release 0.5.0, `specs/releases/0.5.0/SPEC.md` A22.10 / FR22; measurement baselines:
`specs/releases/0.5.0/reviews/test-minimization-literature.md` Part 3, T-050-03's
capture at `.dadaia/tmp/software-engineer/20260827/T-050-03-baselines.md`). Same
measure-then-pin-then-ratchet law `test_module_size_ceiling.py` and
`test_import_linter_ignore_cap.py` already use: pin the number measured *now*,
lowering (or, for V27, raising) a pin in a later commit is welcome, growing one
past its ratchet direction without a same-commit justification is not.

**The A18.3 boundary, stated once so nobody re-litigates it.** These five properties
are *test-suite ratchets* — they measure the suite itself, run inside the existing
`pytest` job, and add zero new CLI surface, zero new doctor code and zero new hook
exit. A18.3's "zero new checks" governs *product* checks; it does not reach a
contract test that fails when the suite it measures regresses. A22.6's "zero new
blocking exits" is unaffected for the same reason: a red contract test failing the
suite is what every contract test in this repository already does.

Five properties, one function each (no new tier, no new CLI leaf, no new doctor
code):

* **V26** — private-symbol imports. Count of `from dadaia_workspace... import
  _name` statements in `tests/**`, AST-exact (not grep — a single-line grep
  undercounts multi-line `import (...)` continuations, which is exactly how the
  SPEC's own quoted "~24" baseline was produced). A statement is excluded only
  when one of its own source lines carries the inline
  ``# allow-private-import: <reason>`` marker — a documented-contract exception,
  one entry per import statement, never a blanket file-level exemption. Ratchet:
  DOWN ONLY. Target: 0.
* **V27** — `Intent:` header coverage. Every `tests/**/test_*.py`'s *module*
  docstring (not just any matching line in the file body) should carry an
  `Intent: <KIND> — <ref>` header (`tests/AGENTS.md` "Intent taxonomy",
  `dadaia-test-stewardship` §A). Ratchet: UP ONLY. Target: every file.
* **V28** — SCAFFOLD expiry. Every `Intent: SCAFFOLD` header must carry an
  `expires: <M.m.p>` field, and the named release must not already be archived.
  The archive-membership check is an **exact** directory-name match against
  `specs/_archive/releases/<M.m.p>` — no `v`-prefix normalization. This workspace
  carries legacy `vM.m.p`-named archives from a numbering track that predates the
  Gitflow-v2 no-`v`-prefix canon (`DADAIA.md` §4); normalizing the two forms
  together would make a *coincidental* legacy archive name (for example the
  pre-existing `specs/_archive/releases/v0.6.0`, unrelated to the yet-unshipped
  `0.6.0` this repo's own SCAFFOLD tests expire against) falsely retire a live
  SCAFFOLD. The canon-named exact match is the only form V28 checks.
* **V29** — one number per parameter. `dadaia-test-stewardship/PARAMETERS.md` is
  the LARGE-cap's one canonical, literal home; every other scanned doctrine file
  either references it or carries no numeric statement of its own. Baseline (fold
  3, `qa-engineer` amendment 7): three homes, `PARAMETERS.md` = 30,
  `tests/AGENTS.md` = 30, `specs/memory/QUALITY.md` = 100. T-050-18A repoints
  `tests/AGENTS.md` (this task's own write set); `specs/memory/QUALITY.md`'s
  competing 100 is T-050-29's — recorded here as the residual, ratcheted DOWN
  ONLY toward its eventual target of 0 competing homes.
* **V30** — pyramid shape. Per-tier shares computed from one `--collect-only`
  run, bucketed by the same `tests/<tier>/` directory layout `tests/conftest.py`
  already auto-marks by (SMALL = `unit` + `contract`, MEDIUM = `integration`,
  LARGE = `e2e`). **Reported, not gated** — a drift beyond the literature's
  SMALL >= 75 % / MEDIUM <= 20 % / LARGE <= 5 % (+/-5pp tolerance) targets is a
  finding for the closure size accounting (A22.10), never a pytest failure here.

Every property below is proven twice: once against the real repository (the
pinned ratchet), and once against a small in-memory mutation fixture — a clean
input the checker accepts and a deliberately violating input the same checker
function flags — so a reviewer can see the detector actually detects, not merely
that today's repository happens to be clean.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_DIR = _REPO_ROOT / "tests"

# ---------------------------------------------------------------------------
# V26 — private-symbol imports
# ---------------------------------------------------------------------------

_ALLOWLIST_MARKER = "# allow-private-import:"

# RECORDED CEILING (ratchet DOWN ONLY) — measured 2026-08-27 on this HEAD, after
# T-050-18 (FR9) deleted the one hook-de-slop private import that dropped the
# T-050-03 pre-T-050-18 AST-exact count from 59/53. Lowering these after a further
# clean-up is welcome (re-pin in the same commit as the deletion). Raising either
# number requires a same-commit justification — a newly-added private-symbol
# import is a newly-frozen Hyrum's-Law liability (test-minimization-literature.md
# §1.6, Part 3.1).
_V26_STATEMENT_CEILING = 60
_V26_FILE_CEILING = 54


def _private_symbol_import_statements(
    source: str, *, filename: str = "<fixture>"
) -> list[tuple[int, tuple[str, ...]]]:
    """Return ``(lineno, private_names)`` for every ``from dadaia_workspace...
    import _name[, ...]`` statement in *source*, skipping any statement that
    carries the ``# allow-private-import: <reason>`` marker on one of its own
    source lines (single- or multi-line import alike)."""
    tree = ast.parse(source, filename=filename)
    lines = source.splitlines()
    hits: list[tuple[int, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("dadaia_workspace")
        ):
            continue
        private_names = tuple(
            alias.name
            for alias in node.names
            if alias.name.startswith("_") and not alias.name.startswith("__")
        )
        if not private_names:
            continue
        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        span = lines[node.lineno - 1 : end]
        if any(_ALLOWLIST_MARKER in line for line in span):
            continue
        hits.append((node.lineno, private_names))
    return hits


def test_v26_private_symbol_import_ratchet_pins_the_hyrums_law_liability() -> None:
    """V26 (A22.10) — pins the AST-exact private-symbol-import count at **60
    statements / 54 files**, measured on this HEAD (post-T-050-18; supersedes the
    SPEC's quoted pre-measurement ~24, itself a single-line-grep undercount per
    T-050-03's capture). Ratchet DOWN ONLY; target 0."""
    total_statements = 0
    files_with_hits: set[Path] = set()
    for path in sorted(_TESTS_DIR.rglob("*.py")):
        hits = _private_symbol_import_statements(
            path.read_text(encoding="utf-8"), filename=str(path)
        )
        if hits:
            files_with_hits.add(path)
            total_statements += len(hits)

    assert total_statements <= _V26_STATEMENT_CEILING, (
        f"private-symbol import statements grew to {total_statements} "
        f"(ceiling {_V26_STATEMENT_CEILING}). Each is a Hyrum's-Law liability — a "
        "test pinning a private helper freezes it. Add a documented-contract "
        "`# allow-private-import: <reason>` marker only for a genuine exception, "
        "otherwise remove the import, and lower the ceiling in the same commit "
        "when the count drops."
    )
    assert len(files_with_hits) <= _V26_FILE_CEILING, (
        f"private-symbol-importing files grew to {len(files_with_hits)} "
        f"(ceiling {_V26_FILE_CEILING})."
    )

    # Mutation fixture — proves the counter both detects a violation and honours
    # a documented allowlist entry.
    clean = "from dadaia_workspace.core import public_thing\n"
    assert _private_symbol_import_statements(clean) == []

    violating = "from dadaia_workspace.core import _private_thing\n"
    assert len(_private_symbol_import_statements(violating)) == 1

    allowlisted = (
        "from dadaia_workspace.core import (\n"
        "    _private_thing,  # allow-private-import: documented contract reason\n"
        ")\n"
    )
    assert _private_symbol_import_statements(allowlisted) == []


# ---------------------------------------------------------------------------
# V27 — `Intent:` header coverage
# ---------------------------------------------------------------------------

_INTENT_HEADER_RE = re.compile(r"(?m)^\s*Intent:\s*\S")

# RECORDED FLOOR (ratchet UP ONLY) — measured 2026-08-27 on this HEAD: 108 of
# tests/**/test_*.py declare an `Intent:` header in their module docstring.
# Raising this after a curation sweep declares more headers is the point; a drop
# below the floor means a previously-declared file lost its header.
_V27_INTENT_DECLARED_FLOOR = 108


def _declares_intent(source: str, *, filename: str = "<fixture>") -> bool:
    """True if *source*'s module docstring carries an `Intent: <KIND> — <ref>`
    header line (`tests/AGENTS.md` "Intent taxonomy")."""
    tree = ast.parse(source, filename=filename)
    docstring = ast.get_docstring(tree) or ""
    return bool(_INTENT_HEADER_RE.search(docstring))


def test_v27_intent_header_coverage_ratchet() -> None:
    """V27 (A22.10) — pins `Intent:` module-docstring coverage at **>= 108**
    declared files out of `tests/**/test_*.py` (T-050-03 baseline 94/396; this
    re-measure on the current HEAD is higher — later tasks already declared more).
    Ratchet UP ONLY; target is every collected test file."""
    test_files = sorted(_TESTS_DIR.glob("**/test_*.py"))
    declared_count = sum(
        1
        for path in test_files
        if _declares_intent(path.read_text(encoding="utf-8"), filename=str(path))
    )

    assert declared_count >= _V27_INTENT_DECLARED_FLOOR, (
        f"declared `Intent:` headers dropped to {declared_count} "
        f"(floor {_V27_INTENT_DECLARED_FLOOR} of {len(test_files)} test files). "
        "An undeclared test is SCAFFOLD by the taxonomy's own default (DADAIA.md "
        "§7) — a drop below the floor means a previously-declared header was "
        "lost, not merely that the sweep has not reached a new file yet."
    )

    # Mutation fixture — proves the checker distinguishes a declared header from
    # an undeclared docstring.
    declared = '"""Intent: CONTRACT — T-000\n\nBody text.\n"""\nX = 1\n'
    assert _declares_intent(declared) is True

    undeclared = '"""Just a docstring, no header."""\nX = 1\n'
    assert _declares_intent(undeclared) is False


# ---------------------------------------------------------------------------
# V28 — SCAFFOLD carries `expires:`; a SCAFFOLD naming an archived release is RED
# ---------------------------------------------------------------------------

_SCAFFOLD_HEADER_RE = re.compile(r"(?m)^\s*Intent:\s*SCAFFOLD\b(?P<rest>.*)$")
_EXPIRES_RE = re.compile(r"expires:\s*([0-9]+(?:\.[0-9]+){1,3})")


def _scaffold_expiry_violation(
    source: str, *, archive_releases_dir: Path, filename: str = "<fixture>"
) -> str | None:
    """``None`` if *source* carries no `Intent: SCAFFOLD` header, or a violation
    message if it does and either (a) no `expires: <M.m.p>` is declared, or (b)
    *archive_releases_dir* / that exact version string already exists (canon-named
    exact match only — see the module docstring's V28 paragraph on why no
    `v`-prefix normalization is applied)."""
    tree = ast.parse(source, filename=filename)
    docstring = ast.get_docstring(tree) or ""
    header = _SCAFFOLD_HEADER_RE.search(docstring)
    if not header:
        return None
    expires = _EXPIRES_RE.search(header.group("rest")) or _EXPIRES_RE.search(docstring)
    if not expires:
        return "Intent: SCAFFOLD with no `expires: <M.m.p>` field"
    version = expires.group(1)
    if (archive_releases_dir / version).exists():
        return (
            f"Intent: SCAFFOLD `expires: {version}` names a release already archived "
            f"at {archive_releases_dir / version} — renew by an explicit qa-engineer "
            "verdict, never by silence"
        )
    return None


def test_v28_scaffold_expiry_goes_red_against_an_archived_release(tmp_path: Path) -> None:
    """V28 (A22.10) — every `Intent: SCAFFOLD` test in the real repo carries
    `expires: <M.m.p>` and names a release not yet archived (pinned: zero
    violations now — covers T-050-09's `migrate_v5_provenance_scaffold.py`,
    `expires: 0.6.0`, checked against the exact-name-match archive listing)."""
    archive_releases_dir = _REPO_ROOT / "specs" / "_archive" / "releases"
    violations = []
    for path in sorted(_TESTS_DIR.glob("**/test_*.py")):
        violation = _scaffold_expiry_violation(
            path.read_text(encoding="utf-8"),
            archive_releases_dir=archive_releases_dir,
            filename=str(path),
        )
        if violation:
            violations.append(f"{path}: {violation}")

    assert not violations, (
        "SCAFFOLD expiry violation(s) — renew by an explicit qa-engineer verdict, "
        "never by silence:\n" + "\n".join(violations)
    )

    # Mutation fixtures — prove the checker flags a missing `expires:`, flags an
    # already-archived release (exact-name match), and clears a not-yet-archived one.
    missing_expiry = '"""Intent: SCAFFOLD — T-999 — no expiry declared."""\n'
    assert _scaffold_expiry_violation(missing_expiry, archive_releases_dir=tmp_path) is not None

    (tmp_path / "9.9.9").mkdir()
    already_archived = '"""Intent: SCAFFOLD — T-999 — expires: 9.9.9."""\n'
    assert _scaffold_expiry_violation(already_archived, archive_releases_dir=tmp_path) is not None

    not_yet_archived = '"""Intent: SCAFFOLD — T-999 — expires: 8.8.8."""\n'
    assert _scaffold_expiry_violation(not_yet_archived, archive_releases_dir=tmp_path) is None


# ---------------------------------------------------------------------------
# V29 — one number per parameter (the LARGE cap)
# ---------------------------------------------------------------------------

_V29_PARAMETERS_MD = (
    _REPO_ROOT
    / "dadaia_workspace"
    / "public"
    / "skills"
    / "dadaia-test-stewardship"
    / "PARAMETERS.md"
)
_V29_TESTS_AGENTS_MD = _REPO_ROOT / "tests" / "AGENTS.md"
_V29_QUALITY_MD = _REPO_ROOT / "specs" / "memory" / "QUALITY.md"

# Each pattern extracts the numeric value a doctrine file states as *its own*
# LARGE-cap/census literal — never a value merely quoted while referencing
# PARAMETERS.md. One regex per file's actual, specific sentence shape (not a
# loose keyword scan — a loose scan false-positives on unrelated `LARGE`+digit
# sentences, e.g. tests/AGENTS.md's own "LARGE (e2e) | ... | 120 s" timeout row).
_PARAMETERS_MD_OWN_VALUE_RE = re.compile(r"\|\s*LARGE \(E2E\) cap\s*\|\s*(\d+)")
_TESTS_AGENTS_MD_OWN_VALUE_RE = re.compile(r"LARGE cap for this repo:\s*\*\*(\d+)\*\*")
_QUALITY_MD_OWN_VALUE_RE = re.compile(r"census is \*\*(\d+)\*\*")

# RECORDED CEILING (ratchet DOWN ONLY) — measured 2026-08-27, immediately after
# this task repoints tests/AGENTS.md: one competing home remains
# (specs/memory/QUALITY.md's 100), T-050-29's to delete. Target: 0.
_V29_COMPETING_HOME_CEILING = 1


def _own_declared_value(text: str, pattern: re.Pattern[str]) -> int | None:
    match = pattern.search(text)
    return int(match.group(1)) if match else None


def test_v29_one_number_per_parameter_for_the_large_cap() -> None:
    """V29 (A22.10) — `PARAMETERS.md` stays the LARGE cap's one literal source
    (pinned: 30); `tests/AGENTS.md` carries no numeric cap of its own (this task's
    own write-set achievement — repoints it to a reference); the residual
    competing home (`specs/memory/QUALITY.md`'s 100, T-050-29's to remove) is
    pinned at **1**, ratchet DOWN ONLY, target 0."""
    canonical = _own_declared_value(
        _V29_PARAMETERS_MD.read_text(encoding="utf-8"), _PARAMETERS_MD_OWN_VALUE_RE
    )
    assert canonical == 30, (
        "PARAMETERS.md must remain the LARGE-cap's own literal source; expected 30, "
        f"found {canonical!r} — this pin is stale if the number moved."
    )

    tests_agents_own = _own_declared_value(
        _V29_TESTS_AGENTS_MD.read_text(encoding="utf-8"), _TESTS_AGENTS_MD_OWN_VALUE_RE
    )
    assert tests_agents_own is None, (
        "tests/AGENTS.md must carry NO numeric LARGE cap of its own (T-050-18A "
        f"repointed it to reference PARAMETERS.md); found {tests_agents_own!r} — "
        "someone reintroduced the competing statement."
    )

    quality_md_own = _own_declared_value(
        _V29_QUALITY_MD.read_text(encoding="utf-8"), _QUALITY_MD_OWN_VALUE_RE
    )
    competing_homes = [
        name
        for name, value in (
            ("tests/AGENTS.md", tests_agents_own),
            ("specs/memory/QUALITY.md", quality_md_own),
        )
        if value is not None
    ]
    assert len(competing_homes) <= _V29_COMPETING_HOME_CEILING, (
        f"{len(competing_homes)} non-canonical doctrine file(s) declare their own "
        f"LARGE-cap number: {competing_homes} (ceiling {_V29_COMPETING_HOME_CEILING}, "
        "ratchet DOWN ONLY). specs/memory/QUALITY.md's remaining 100 is T-050-29's to "
        "delete (see TASKS.md T-050-18A's preconditions/description)."
    )

    # Mutation fixture — the exact regex that now finds nothing in tests/AGENTS.md
    # must still fire on the sentence it used to contain, proving a reintroduced
    # numeric cap (e.g. a revert of this task's edit) would be caught.
    reverted_sentence = "... LARGE cap for this repo: **30**, declared and measured as a WARN ..."
    assert _own_declared_value(reverted_sentence, _TESTS_AGENTS_MD_OWN_VALUE_RE) == 30


# ---------------------------------------------------------------------------
# V30 — pyramid shape, reported (not gated)
# ---------------------------------------------------------------------------

# tier -> (comparison, target_pct); comparison "min" reads as actual >= target,
# "max" reads as actual <= target (test-minimization-literature.md Part 3 rule 9;
# Google SWE book ch.11's ~80/15/5 mix).
_PYRAMID_TARGETS: dict[str, tuple[str, float]] = {
    "small": ("min", 75.0),
    "medium": ("max", 20.0),
    "large": ("max", 5.0),
}
_PYRAMID_DRIFT_TOLERANCE_PP = 5.0


def _pyramid_shares(tier_counts: dict[str, int]) -> dict[str, float]:
    total = sum(tier_counts.values())
    assert total > 0, "cannot compute pyramid shares of an empty collection"
    return {tier: (count / total) * 100.0 for tier, count in tier_counts.items()}


def _pyramid_drift_findings(
    shares: dict[str, float], *, tolerance_pp: float = _PYRAMID_DRIFT_TOLERANCE_PP
) -> list[str]:
    """Informational only (V30 is REPORTED, not gated) — a finding here is a
    closure-time observation (A22.10), never a reason this function's caller
    should fail."""
    findings = []
    for tier, (comparison, target) in _PYRAMID_TARGETS.items():
        actual = shares.get(tier, 0.0)
        if comparison == "min" and actual < target - tolerance_pp:
            findings.append(
                f"{tier}: {actual:.1f}% below target >= {target:.0f}% "
                f"(tolerance {tolerance_pp:.0f}pp)"
            )
        elif comparison == "max" and actual > target + tolerance_pp:
            findings.append(
                f"{tier}: {actual:.1f}% above target <= {target:.0f}% "
                f"(tolerance {tolerance_pp:.0f}pp)"
            )
    return findings


def _collect_tier_counts() -> dict[str, int]:
    """One `--collect-only` run (V30's own requirement: "same --collect-only
    run"), bucketed by the `tests/<tier>/` directory each item's nodeid falls
    under — the same directory layout `tests/conftest.py` already auto-marks by,
    so no second, marker-filtered subprocess per tier is needed."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=25,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    counts: dict[str, int] = {"unit": 0, "integration": 0, "contract": 0, "e2e": 0}
    for line in proc.stdout.splitlines():
        if not line.startswith("tests/") or "::" not in line:
            continue
        tier = line.split("/", 2)[1]
        if tier in counts:
            counts[tier] += 1
    return counts


def test_v30_pyramid_shape_reported_from_collect_only() -> None:
    """V30 (A22.10) — per-tier shares computed from one `--collect-only` run,
    folded to SMALL (`unit` + `contract`) / MEDIUM (`integration`) / LARGE
    (`e2e`) and reported against the literature's 75/20/5 targets. **Reported,
    not gated**: this test never fails on the real repository's shape — only the
    mutation fixture below proves the underlying finding-detector actually
    detects a drift when one exists."""
    tier_counts = _collect_tier_counts()
    total_collected = sum(tier_counts.values())
    assert total_collected > 0, "pytest --collect-only returned zero test items"

    folded = {
        "small": tier_counts["unit"] + tier_counts["contract"],
        "medium": tier_counts["integration"],
        "large": tier_counts["e2e"],
    }
    shares = _pyramid_shares(folded)
    findings = _pyramid_drift_findings(shares)
    print(
        f"V30 pyramid (reported, not gated) — collected {total_collected}: "
        f"small {shares['small']:.1f}% · medium {shares['medium']:.1f}% · "
        f"large {shares['large']:.1f}% — findings: {findings or 'none'}"
    )
    # Reported, not gated — `findings` is not asserted empty here; a drift is a
    # closure-time finding (A22.10), not a push-blocking failure.
    assert isinstance(findings, list)

    # Mutation fixture — proves the drift-finding function detects a violation
    # when actually given one, even though the real measurement above never
    # gates on it.
    skewed = _pyramid_shares({"small": 40, "medium": 20, "large": 40})
    skewed_findings = _pyramid_drift_findings(skewed)
    assert skewed_findings, "the drift-finding detector failed to flag a skewed pyramid"
