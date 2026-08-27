"""Specs-pattern versioning (FR-S01 / FR-S02).

A Spec Context Project's ``specs/`` tree conforms to a *pattern version* — the
canonical structural layout the workspace expects. The library carries the single
source of truth (:data:`CANONICAL_SPECS_VERSION`); each project records its own
version in the ``specs_pattern_version`` field of ``specs/constitution.md``'s YAML
frontmatter.

Absent-stamp semantics: a constitution with no frontmatter (or no
``specs_pattern_version`` key) is treated as **version 0** — pre-framework, the flat
layout that predates the tree-v2 migration. Doctor warns and recommends
``dadaia specs upgrade``.
"""

from __future__ import annotations

import re
from pathlib import Path

#: Single source of truth for the current canonical specs-pattern version.
#: Bump this when a new migration step is added to the registry (see ``registry.py``).
#: v3 = agent-tier-frontmatter (v0.1.72 FR1); v4 = bugs-single-file (v0.1.73 FR1 —
#: the operator's ONE-append-only-ledger contract); v5 = specs-canon-v6's tree shape
#: (T-050-05); v6 = this stamp, T-050-06A — the version number itself, deferred by
#: T-050-05 because RELEASE_SEMVER_RE's axis flip (below) is this task's write set.
CANONICAL_SPECS_VERSION = 6

#: Version assigned to a tree with no stamp (pre-framework flat layout).
UNSTAMPED_VERSION = 0

#: Single source of truth for the release-directory SemVer form (v0.1.53 FR3, flipped
#: to canon v6 / two-axis form at T-050-06A, SPEC FR1 boundary 2a / AS-13). This is the
#: ONE compiled home for the pattern — previously triplicated in
#: ``features/specs/scaffolder.py``, ``features/specs/doctor.py``, and
#: ``features/spec_artifacts/new_artifacts.py``. Every consumer imports THIS object; the
#: agreement contract ``tests/contract/test_release_semver_canon.py`` locks the identity
#: (same compiled object everywhere) and forbids any re-introduced ``re.compile`` copy.
#:
#: Two axes, ONE compiled object (AS-13): the current, LIVE axis is bare
#: ``MAJOR.MINOR.PATCH`` (canon v6 moved live/archived release ids off the ``v`` prefix);
#: the retired axis (every id shipped before v0.5.0's canon move) is ``vMAJOR.MINOR.PATCH``
#: and stays matched here ONLY so an existing archived directory still resolves for
#: read-only lookups (doctor naming checks, the CI verdict-evidence gate). The ``v``
#: prefix is therefore OPTIONAL in this object, but ``is_release_semver()`` below narrows
#: to the bare, current-axis form ONLY — nothing may *mint* a new ``v``-prefixed id. Both
#: axes keep the optional ``-suffix`` segment (rc/canary/hotfix flows are legitimate
#: release identities on either axis).
RELEASE_SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+(-[0-9A-Za-z][0-9A-Za-z.]*)?$")

#: The exactly-two verdict-evidence root templates the CI security-verdict gate
#: (``.github/scripts/pr-verdict-check.sh``) resolves against (SPEC AS-15, T-050-06A
#: boundary 2). Each string carries ONE ``{glob}`` placeholder the caller substitutes
#: with either ``*`` (search every release, live and archived) or a narrowing value
#: already validated against :data:`RELEASE_SEMVER_RE`. Never
#: ``specs/releases/_ideas/`` — T-050-01 moves every verdict-bearing trio out of
#: ``_ideas/`` before any PR exists, and ``_ideas/`` stays deliberately MUTATING
#: (A6.3): a freely-writable directory is never a trust root of a required check.
#: The gate shells out to a bare ``python3 -c`` importing this module (stdlib-only —
#: ``re`` + ``pathlib``, no install step) to read this tuple and
#: :data:`RELEASE_SEMVER_RE`'s pattern; a derivation failure there is fail-closed
#: (SPEC §9.2 SEC-R2) — no fallback glob, ever.
VERDICT_EVIDENCE_ROOT_TEMPLATES: tuple[str, str] = (
    "specs/releases/{glob}/verdicts",
    "specs/releases/_archive/{glob}/verdicts",
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_STAMP_RE = re.compile(r"^specs_pattern_version:\s*(\d+)\s*$", re.MULTILINE)


def release_semver_ere_pattern() -> str:
    """Return :data:`RELEASE_SEMVER_RE`'s pattern translated to POSIX ERE syntax.

    ``.github/scripts/pr-verdict-check.sh`` validates an optional ``RELEASE_ID``
    narrowing value with bash's ``[[ value =~ pattern ]]`` — POSIX Extended Regular
    Expressions, a different dialect from Python's ``re``. ``\\d`` is the ONLY
    PCRE-only construct :data:`RELEASE_SEMVER_RE` uses (POSIX ERE has no digit-class
    shorthand; bash's regex engine treats a literal ``\\d`` as an escaped ``d``,
    silently rejecting every valid id — reproduced and fixed at T-050-06A). This is a
    MECHANICAL syntax translation of the one canon pattern, computed here so the gate
    reads a single derived value rather than a second, hand-typed copy; it is not a
    second definition of the release-id shape.
    """
    return RELEASE_SEMVER_RE.pattern.replace(r"\d", "[0-9]")


def is_release_semver(value: str) -> bool:
    """Return ``True`` when ``value`` is the CURRENT-axis release id: bare
    ``MAJOR.MINOR.PATCH`` (optional ``-suffix``), no ``v`` prefix.

    The single MINT predicate (AS-13/A1.10, T-050-06A): "is this string a value a NEW
    release/segment may be created under?" A ``v``-prefixed id matches the broader
    :data:`RELEASE_SEMVER_RE` (it must still resolve for archived-directory lookups) but
    is refused here — the retired axis is read-only, never mintable again. Used by
    ``dadaia release new`` (``new_artifacts.release_new``). Callers that also accept the
    legacy slug form compose this with their own slug check.
    """
    return RELEASE_SEMVER_RE.match(value) is not None and not value.startswith("v")


def _constitution_path(specs_dir: Path) -> Path:
    return specs_dir / "constitution.md"


def read_pattern_version(specs_dir: Path) -> int:
    """Return the ``specs_pattern_version`` stamped in the constitution.

    Returns :data:`UNSTAMPED_VERSION` (0) when the constitution is absent, has no
    YAML frontmatter, or the frontmatter omits the stamp.
    """
    constitution = _constitution_path(specs_dir)
    if not constitution.exists():
        return UNSTAMPED_VERSION
    text = constitution.read_text(encoding="utf-8")
    fm = _FRONTMATTER_RE.match(text)
    if fm is None:
        return UNSTAMPED_VERSION
    stamp = _STAMP_RE.search(fm.group(1))
    if stamp is None:
        return UNSTAMPED_VERSION
    return int(stamp.group(1))


def write_pattern_version(specs_dir: Path, version: int) -> None:
    """Stamp ``specs_pattern_version: <version>`` into the constitution frontmatter.

    Creates the YAML frontmatter block if absent; updates the stamp in place if the
    block already exists. Idempotent: re-stamping the same version is a no-op write.
    """
    constitution = _constitution_path(specs_dir)
    text = constitution.read_text(encoding="utf-8") if constitution.exists() else ""
    fm = _FRONTMATTER_RE.match(text)

    if fm is None:
        # No frontmatter: prepend a fresh block.
        new_text = f"---\nspecs_pattern_version: {version}\n---\n{text}"
        constitution.write_text(new_text, encoding="utf-8")
        return

    block = fm.group(1)
    if _STAMP_RE.search(block):
        new_block = _STAMP_RE.sub(f"specs_pattern_version: {version}", block)
    else:
        new_block = f"{block}\nspecs_pattern_version: {version}"
    new_text = f"---\n{new_block}\n---\n" + text[fm.end() :]
    constitution.write_text(new_text, encoding="utf-8")
