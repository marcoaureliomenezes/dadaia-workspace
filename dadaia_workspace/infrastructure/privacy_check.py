"""Privacy denylist constants, loader, and public-asset privacy check.

Extracted from ``public_assets.py`` to keep that module under 600 lines.
All names remain importable from ``dadaia_workspace.infrastructure.public_assets``
via its re-export block.

Fail-closed posture (R7b / sec F-2): when the operator-private denylist is
absent (fresh clone, CI, pip install) the check is **never** a no-op. A
versioned, in-package *baseline structural scan* runs instead, flagging IP
literals, internal hostnames, ``/home/<user>`` paths, emails, and secret-looking
tokens in the public/ asset payload. Operator denylist terms, when present, are
merged additively on top of the baseline.
"""

from __future__ import annotations

import importlib.resources
import json
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

_PUBLIC_ASSET_IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_PUBLIC_ASSET_IGNORED_SUFFIXES = {".pyc", ".pyo"}
_PUBLIC_PRIVACY_TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".j2",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
# Operator-private privacy terms are NEVER hardcoded in this published library
# (dev-guardrail rule #4: no consumer-specific data in shipped source). Each
# workspace supplies its own terms via a runtime file kept OUT of the package:
#   1. $DADAIA_PRIVACY_DENYLIST            (path to a JSON file), or
#   2. <workspace_root>/.dadaia/states/privacy_denylist.json
#      where workspace_root is resolved by walking up from cwd looking for the
#      .dadaia/states/spec_contexts.json sentinel (via resolve_workspace_root).
# Format: [["term", "reason"], ...] or {"term": "reason", ...}.
# Absent -> the baseline structural scan (below) runs instead; the check is
# never a no-op (fail-closed).
_PRIVACY_DENYLIST_ENV = "DADAIA_PRIVACY_DENYLIST"
_PRIVACY_DENYLIST_REL = Path(".dadaia") / "states" / "privacy_denylist.json"

# Packaged, versioned baseline of STRUCTURAL patterns. Shipped inside the wheel
# so the check is fail-closed even with no operator denylist. Operator terms are
# additive on top of these.
_PRIVACY_BASELINE_PKG = "dadaia_workspace.infrastructure.data"
_PRIVACY_BASELINE_FILE = "privacy_baseline.json"

_OK_MARKER = DoctorLine(DoctorStatus.OK, "public-privacy")
# Distinct ok line so an operator can tell which mode actually ran.
_BASELINE_OK_MARKER = DoctorLine(
    DoctorStatus.OK, "public-privacy (baseline structural scan, no operator denylist)"
)


@dataclass(frozen=True)
class _BaselinePattern:
    """A compiled structural pattern from the packaged baseline."""

    id: str
    regex: re.Pattern[str]
    reason: str
    exclude: re.Pattern[str] | None


@lru_cache(maxsize=1)
def _load_privacy_baseline() -> tuple[_BaselinePattern, ...]:
    """Load and compile the packaged baseline structural patterns.

    The baseline ships inside the wheel under
    ``dadaia_workspace/infrastructure/data/privacy_baseline.json`` (versioned,
    documented ``_header``). A malformed or absent file yields an empty tuple —
    but the file is part of the distribution, so this is a defensive fallback,
    not the normal absent-operator-denylist path.
    """
    try:
        resource = importlib.resources.files(_PRIVACY_BASELINE_PKG) / _PRIVACY_BASELINE_FILE
        raw = json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, ValueError, ModuleNotFoundError):
        return ()
    patterns: list[_BaselinePattern] = []
    for entry in raw.get("patterns", []):
        if not isinstance(entry, dict):
            continue
        pattern_id = str(entry.get("id", ""))
        regex_src = entry.get("regex")
        if not isinstance(regex_src, str) or not regex_src:
            continue
        exclude_src = entry.get("exclude_regex")
        try:
            compiled = re.compile(regex_src)
            exclude = (
                re.compile(exclude_src) if isinstance(exclude_src, str) and exclude_src else None
            )
        except re.error:
            continue
        patterns.append(
            _BaselinePattern(
                id=pattern_id,
                regex=compiled,
                reason=str(entry.get("reason", "structural privacy match")),
                exclude=exclude,
            )
        )
    return tuple(patterns)


def _load_privacy_denylist() -> tuple[tuple[str, str], ...]:
    """Load operator-private privacy terms from outside the published package.

    Resolution order:
    1. ``$DADAIA_PRIVACY_DENYLIST`` environment variable — path to a JSON file.
    2. ``<workspace_root>/.dadaia/states/privacy_denylist.json`` where
       *workspace_root* is resolved by walking up from ``cwd`` looking for the
       ``.dadaia/states/spec_contexts.json`` sentinel. Returns ``()`` when no
       workspace root is found (e.g. pip-installed in site-packages without an
       active workspace) or the file is absent / unreadable / malformed.
    """
    candidates: list[Path] = []
    env_path = os.environ.get(_PRIVACY_DENYLIST_ENV)
    if env_path:
        candidates.append(Path(env_path))
    # Resolve workspace root via cwd-based walk-up; never fall back to the lib repo.
    try:
        workspace_root = resolve_workspace_root()
        candidates.append(workspace_root / _PRIVACY_DENYLIST_REL)
    except WorkspaceNotInitializedError:
        pass  # No workspace found — file-based fallback is simply unavailable.
    for source in candidates:
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        terms: list[tuple[str, str]] = []
        if isinstance(raw, dict):
            terms = [(str(key), str(value)) for key, value in raw.items()]
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    terms.append((str(item[0]), str(item[1])))
                elif isinstance(item, str):
                    terms.append((item, "private identifier"))
        if terms:
            return tuple(terms)
    return ()


def load_privacy_terms() -> tuple[tuple[str, str], ...]:
    """Public accessor over the operator denylist loader (SPEC v0.9.0 FR3, source 1).

    Reused by the push-range denylist scan (``features.chokepoints.denylist_scan``) so
    the CLI wires ONE operator term source, not a second denylist — same resolution
    order as :func:`check_public_privacy` (``$DADAIA_PRIVACY_DENYLIST``, then
    ``<workspace>/.dadaia/states/privacy_denylist.json``). Empty when neither resolves.
    """
    return _load_privacy_denylist()


def load_baseline_patterns() -> tuple[_BaselinePattern, ...]:
    """Public accessor over the packaged structural baseline (SPEC v0.9.0 FR3, source 2).

    Same compiled patterns :func:`check_public_privacy` scans public assets with —
    reused, not forked, so the push-range scan and the public-privacy doctor check stay
    a single source of truth for what counts as a structural privacy match.
    """
    return _load_privacy_baseline()


def _scan_text_for_baseline(
    text: str, patterns: Iterable[_BaselinePattern]
) -> list[tuple[str, str]]:
    """Return ``(matched_text, reason)`` pairs for baseline structural hits.

    Each match is filtered through the pattern's optional ``exclude`` regex so
    loopback / documentation IP ranges, example hostnames, and SHA-like tokens
    do not produce false positives.
    """
    hits: list[tuple[str, str]] = []
    for pattern in patterns:
        for match in pattern.regex.finditer(text):
            value = match.group(0)
            if pattern.exclude is not None and pattern.exclude.search(value):
                continue
            hits.append((value, pattern.reason))
    return hits


def check_public_privacy(
    public_dir: Path,
    iter_files_fn: Callable[[Path], Iterable[Path]],
    is_ignored_fn: Callable[[Path], bool],
) -> list[DoctorLine]:
    """Fail doctor if public distributed assets contain private identifiers.

    Two complementary layers, always at least one runs (fail-closed):

    * **Operator denylist** (additive, when present): literal-substring terms
      supplied by the workspace operator outside the package.
    * **Baseline structural scan** (always available, in-package): regex
      patterns for IP/hostname/path/email/secret literals.

    The emitted ``[ok]`` line distinguishes the absent-denylist baseline mode
    explicitly so an operator can confirm a real scan ran.
    """
    lib_root = public_dir.parent.parent
    roots: list[Path] = [public_dir]
    denylist = _load_privacy_denylist()
    baseline = _load_privacy_baseline()
    baseline_only = not denylist
    root_agents = lib_root / "AGENTS.md"
    if root_agents.exists():
        roots.append(root_agents)

    findings: list[DoctorLine] = []
    for root in roots:
        files: list[Path] = [root] if root.is_file() else list(iter_files_fn(root))
        for path in files:
            if is_ignored_fn(path):
                continue
            if path.suffix.lower() not in _PUBLIC_PRIVACY_TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = path.relative_to(lib_root) if path.is_relative_to(lib_root) else path
            lowered = text.lower()
            for term, reason in denylist:
                if term.lower() in lowered:
                    findings.append(
                        DoctorLine(
                            DoctorStatus.ERROR,
                            f"public-privacy:{rel.as_posix()}: contains '{term}' ({reason})",
                        )
                    )
            for value, reason in _scan_text_for_baseline(text, baseline):
                findings.append(
                    DoctorLine(
                        DoctorStatus.ERROR,
                        f"public-privacy:{rel.as_posix()}: baseline match '{value}' ({reason})",
                    )
                )
    if findings:
        return findings
    return [_BASELINE_OK_MARKER if baseline_only else _OK_MARKER]
