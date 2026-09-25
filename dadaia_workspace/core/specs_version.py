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

import json
import re
from pathlib import Path

from dadaia_workspace.core.frontmatter import (
    FRONTMATTER_RE,
    Frontmatter,
    FrontmatterError,
    parse,
)
from dadaia_workspace.core.gitflow import DEFAULT, Gitflow, from_mapping

#: Single source of truth for the current canonical specs-pattern version.
#: Bump this when a new migration step is added to the registry (see ``registry.py``).
#: v3 = agent-tier-frontmatter (v0.1.72 FR1); v4 = bugs-single-file (v0.1.73 FR1 —
#: the operator's ONE-append-only-ledger contract); v5 = specs-canon-v6's tree shape
#: (T-050-05); v6 = this stamp, T-050-06A — the version number itself, deferred by
#: T-050-05 because RELEASE_SEMVER_RE's axis flip (below) is this task's write set;
#: v7 = memory canon v7 — ``memory/TECHSTACK.md`` left the canon and its body became
#: ``ARCHITECTURE.md``'s ``## Tech Stack`` section, which ``features/migrate`` folds.
CANONICAL_SPECS_VERSION = 7

#: The oldest stamp the one live upgrade hop starts from — and so the oldest a tree may
#: carry and still be a dadaia tree (SPEC 0.4.8 D7, D9); anything older is foreign.
OLDEST_UPGRADABLE_VERSION = 6

#: Version assigned to a tree with no stamp (pre-framework flat layout).
UNSTAMPED_VERSION = 0

#: Single source of truth for the release-directory SemVer form (v0.1.53 FR3, flipped
#: to canon v6 / two-axis form at T-050-06A, SPEC FR1 boundary 2a / AS-13). This is the
#: ONE compiled home for the pattern — previously triplicated in
#: ``features/specs/scaffolder.py``, ``features/specs/doctor.py``, and the retired
#: ``features/spec_artifacts/new_artifacts.py`` (its ``release_new`` now lives in
#: ``features/specs/canon.py``, v0.5.1 K4). Every consumer imports THIS object; the
#: agreement contract ``tests/contract/test_release_semver_canon.py`` locks the identity
#: (same compiled object everywhere) and forbids any re-introduced ``re.compile`` copy.
#:
#: Two axes, ONE compiled object (AS-13): the current, LIVE axis is bare
#: ``MAJOR.MINOR.PATCH`` (canon v6 moved live/archived release ids off the ``v`` prefix);
#: the retired axis (every id shipped before v0.5.0's canon move) is ``vMAJOR.MINOR.PATCH``
#: and stays matched here ONLY so an existing archived directory still resolves for
#: read-only lookups (doctor naming checks). The ``v``
#: prefix is therefore OPTIONAL in this object, but ``is_release_semver()`` below narrows
#: to the bare, current-axis form ONLY — nothing may *mint* a new ``v``-prefixed id. Both
#: axes keep the optional ``-suffix`` segment (rc/canary/hotfix flows are legitimate
#: release identities on either axis).
RELEASE_SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+(-[0-9A-Za-z][0-9A-Za-z.]*)?$")

#: The bare release-id pattern FRAGMENT (no anchors, no ``v`` prefix), mechanically
#: derived from :data:`RELEASE_SEMVER_RE` — never a second hand-typed copy (F004,
#: 20260830 audit). The one composable source for path regexes embedding a release id
#: (``features/specs/canon.py``'s TREE-8 canon entries).
#: The suffix group stays CAPTURING in the compiled pattern but is neutralized here so
#: embedding the fragment never shifts a consumer regex's group indices.
RELEASE_ID_FRAGMENT: str = (
    RELEASE_SEMVER_RE.pattern.removeprefix("^v?").removesuffix("$").replace("(-", "(?:-")
)


def is_release_semver(value: str) -> bool:
    """Return ``True`` when ``value`` is the CURRENT-axis release id: bare
    ``MAJOR.MINOR.PATCH`` (optional ``-suffix``), no ``v`` prefix.

    The single MINT predicate (AS-13/A1.10, T-050-06A): "is this string a value a NEW
    release/segment may be created under?" A ``v``-prefixed id matches the broader
    :data:`RELEASE_SEMVER_RE` (it must still resolve for archived-directory lookups) but
    is refused here — the retired axis is read-only, never mintable again. Used by
    ``release.py new``. Callers that also accept the
    legacy slug form compose this with their own slug check.
    """
    return RELEASE_SEMVER_RE.match(value) is not None and not value.startswith("v")


def _constitution_path(specs_dir: Path) -> Path:
    return specs_dir / "constitution.md"


def _frontmatter(specs_dir: Path) -> Frontmatter | FrontmatterError:
    constitution = _constitution_path(specs_dir)
    if not constitution.is_file():
        return FrontmatterError(kind="missing_delimiter", message=f"{constitution} is absent")
    return parse(constitution.read_text(encoding="utf-8"))


def read_pattern_version(specs_dir: Path) -> int:
    """The constitution's ``specs_pattern_version``; :data:`UNSTAMPED_VERSION` (0) when
    the constitution, its frontmatter or the key is absent or unreadable."""
    fm = _frontmatter(specs_dir)
    value = fm.data.get("specs_pattern_version") if isinstance(fm, Frontmatter) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else UNSTAMPED_VERSION


def read_gitflow(specs_dir: Path) -> tuple[Gitflow, str | None]:
    """The constitution's ``gitflow:`` block; absent or malformed ⇒ ``DEFAULT`` plus the
    warning to show (ADR 0037: never a block)."""
    fm = _frontmatter(specs_dir)
    if not isinstance(fm, Frontmatter) or "gitflow" not in fm.data:
        reason = "no gitflow block"
    else:
        try:
            return from_mapping(fm.data["gitflow"]), None
        except ValueError as exc:
            reason = str(exc)
    return DEFAULT, (
        f"{_constitution_path(specs_dir)}: {reason} — using the default gitflow "
        f"(principal {DEFAULT.principal}, integration {DEFAULT.integration}, "
        f"work {DEFAULT.work_prefix}<M.m.p>)"
    )


_PLAIN_RE = re.compile(r"[A-Za-z0-9._/-]+")


def _scalar(value: str) -> str:
    return value if _PLAIN_RE.fullmatch(value) else json.dumps(value)


def _render(value: int | Gitflow) -> str:
    if isinstance(value, Gitflow):
        return (
            f"{{principal: {_scalar(value.principal)}, "
            f"integration: {_scalar(value.integration)}, work: {_scalar(value.work_prefix)}}}"
        )
    return str(value)


def merge_frontmatter(
    specs_dir: Path,
    *,
    specs_pattern_version: int | None = None,
    gitflow: Gitflow | None = None,
) -> None:
    """Write the given keys into the constitution frontmatter, one line each.

    The one writer for both keys: a written key's top-level line (and its indented or
    ``-`` continuation lines) is replaced in place, a new key is appended to the block,
    and every other line — plus the body — stays byte-identical. No block ⇒ one is
    prepended.
    """
    updates = {
        key: _render(value)
        for key, value in (("specs_pattern_version", specs_pattern_version), ("gitflow", gitflow))
        if value is not None
    }
    constitution = _constitution_path(specs_dir)
    text = constitution.read_text(encoding="utf-8") if constitution.exists() else ""
    match = FRONTMATTER_RE.match(text)
    lines = match.group(1).split("\n") if match else []
    kept: list[str] = []
    skipping = False
    for line in lines:
        if skipping and (line[:1] in (" ", "\t", "-") or not line.strip()):
            continue
        key = line.split(":", 1)[0]
        skipping = ":" in line and key in updates
        if skipping:
            kept.append(f"{key}: {updates.pop(key)}")
        else:
            kept.append(line)
    kept.extend(f"{key}: {value}" for key, value in updates.items())
    body = text[match.end() :] if match else text
    closing = text[match.start(0) : match.end()].rsplit("\n---", 1)[1] if match else "\n"
    constitution.write_text("---\n" + "\n".join(kept) + "\n---" + closing + body, encoding="utf-8")
