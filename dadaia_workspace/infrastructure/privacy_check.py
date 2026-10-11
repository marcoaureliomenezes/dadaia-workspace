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

from collections.abc import Callable, Iterable
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.core.redaction import (
    BaselinePattern,
    load_baseline,
    mask,
    privacy_matches,
)
from dadaia_workspace.core.workspace_resolver import own_workspace_root
from dadaia_workspace.infrastructure.ledger_scripts import load_owner

#: Directory names never walked when scanning public assets: Python's own bytecode cache
#: (0080). Never ``.dadaia`` — the staged assets this walk reads live inside it.
_PUBLIC_ASSET_IGNORED_DIRS = {"__pycache__"}
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
# Operator-private privacy terms are NEVER hardcoded in this published library; each
# workspace keeps them OUT of the package, read by :func:`load_privacy_terms`.

#: The published surface is English-only. These retired
#: Portuguese control terms are the adoption blocker this closed: a consumer
#: meets them on day 1, inside otherwise-English law. Scanned under ``public/`` only,
#: on the same walk as the privacy layers, because the failure mode is identical —
#: an authored asset leaking something that must never ship.
PORTUGUESE_CONTROL_TERMS: tuple[tuple[str, str], ...] = (
    ("Aprovado", "retired status token — use 'Approved'"),
    ("Em revisão", "retired status token — use 'In review'"),
    ("Em revisao", "retired status token — use 'In review'"),
    ("Rascunho", "retired status token — use 'Draft'"),
    ("Catálogo", "Portuguese heading — use 'catalog'"),
    ("APROVADA", "Portuguese verdict — use 'APPROVED'"),
    ("BLOQUEADA", "Portuguese verdict — use 'BLOCKED'"),
    ("em progresso", "Portuguese marker prose — use 'in progress'"),
)

_OK_MARKER = DoctorLine(DoctorStatus.OK, "public-privacy")
# Distinct ok line so an operator can tell which mode actually ran.
_BASELINE_OK_MARKER = DoctorLine(
    DoctorStatus.OK, "public-privacy (baseline structural scan, no operator denylist)"
)


_BaselinePattern = BaselinePattern


def _load_privacy_baseline() -> tuple[BaselinePattern, ...]:
    """The packaged baseline through its ONE parser, ``_privacy.load_baseline``."""
    return load_baseline()


def load_privacy_terms() -> tuple[tuple[str, str], ...]:
    """The operator denylist through its ONE loader and ONE root decision (ADR 0157):
    ``_ledger.terms`` rooted at ``_ledger.workspace_of`` the cwd (the ledger seam passes its
    ``--specs``), else the workspace owning this venv. ``$DADAIA_PRIVACY_DENYLIST`` loads
    even outside any workspace."""
    ledger = load_owner("dd-bug-resolution", "_ledger")
    return tuple(ledger.terms(ledger.workspace_of(Path.cwd()) or own_workspace_root()))


def load_baseline_patterns() -> tuple[_BaselinePattern, ...]:
    """Public accessor over the packaged structural baseline (SPEC v0.9.0 FR3, source 2).

    Same compiled patterns :func:`check_public_privacy` scans public assets with —
    reused, not forked, so the push-range scan and the public-privacy doctor check stay
    a single source of truth for what counts as a structural privacy match.
    """
    return _load_privacy_baseline()


def _check_baseline_exclude_rationale(
    baseline: Iterable[_BaselinePattern],
) -> list[DoctorLine]:
    """A12.1: every baseline pattern carrying an ``exclude_regex`` carve-out must
    document WHY via ``exclude_rationale`` — flags, by pattern id, any that don't.

    A pattern with NO carve-out (``exclude is None``) needs no rationale and is never
    flagged — this check is about carve-outs specifically, the exact thing the SPEC
    calls out as having grown "literal by literal" with no attached justification.
    Wired into :func:`check_public_privacy` so it runs on every ``dadaia public
    doctor`` invocation, on the SAME ``public-privacy`` doctor line the operator
    already reads — never a second, easy-to-miss check surface.
    """
    findings: list[DoctorLine] = []
    for pattern in baseline:
        if pattern.exclude is None:
            continue
        if pattern.exclude_rationale is None or not pattern.exclude_rationale.strip():
            findings.append(
                DoctorLine(
                    DoctorStatus.ERROR,
                    f"public-privacy: baseline pattern '{pattern.id}' has an "
                    "exclude_regex carve-out with no documented exclude_rationale "
                    "(v0.4.3 FR12/A12.1)",
                )
            )
    return findings


def check_public_privacy(
    public_dir: Path,
    iter_files_fn: Callable[[Path], Iterable[Path]],
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
    denylist = load_privacy_terms()
    try:
        baseline = _load_privacy_baseline()
    except load_owner("dd-bug-resolution", "_refusal").Refusal as refusal:
        return [DoctorLine(DoctorStatus.ERROR, f"public-privacy: {refusal}", refusal.fix)]
    baseline_only = not denylist
    root_agents = lib_root / "AGENTS.md"
    if root_agents.exists():
        roots.append(root_agents)

    findings: list[DoctorLine] = []
    findings.extend(_check_baseline_exclude_rationale(baseline))
    for root in roots:
        files: list[Path] = [root] if root.is_file() else list(iter_files_fn(root))
        for path in files:
            if path.suffix.lower() not in _PUBLIC_PRIVACY_TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = path.relative_to(lib_root) if path.is_relative_to(lib_root) else path
            lowered = text.lower()
            if path.is_relative_to(public_dir):
                for term, reason in PORTUGUESE_CONTROL_TERMS:
                    if term.lower() in lowered:
                        findings.append(
                            DoctorLine(
                                DoctorStatus.ERROR,
                                f"public-privacy:{rel.as_posix()}: contains '{term}' ({reason})",
                            )
                        )
            for value, source, reason in privacy_matches(text, denylist, baseline):
                kind = "contains" if source == "operator denylist" else "baseline match"
                findings.append(
                    DoctorLine(
                        DoctorStatus.ERROR,
                        f"public-privacy:{rel.as_posix()}: {kind} '{mask(value)}' ({reason})",
                    )
                )
    if findings:
        return findings
    return [_BASELINE_OK_MARKER if baseline_only else _OK_MARKER]
