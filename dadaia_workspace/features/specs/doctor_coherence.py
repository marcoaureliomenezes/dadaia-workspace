"""Constitution and pattern-version coherence checks for SpecsDoctor."""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

# SPEC-DOC-037 (v0.1.47 W1-9 / WS-E): the constitution must not re-encode a mutable
# runtime-kind roster. It states the runtime-kind invariant and cites ``[[tech-stack]]`` as
# the roster single-source. Any standalone ``AgentRuntimeKind`` member token (the distinctive
# ALL-CAPS enum identifiers) enumerated in ``specs/constitution.md`` is an ERROR — this is the
# recurrence guard behind the v0.1.47 constitution rewrite. The tokens are word-bounded and
# uppercase, so lowercase English prose ("fake") never matches; ``{claude, codex, pi}`` (the
# Layer model set W2 keeps) is deliberately NOT matched — only runtime-kind ENUM members are.
_CONSTITUTION_RUNTIME_KIND_RE = re.compile(
    r"\b(FAKE|CODEX_EXEC|CLAUDE_SDK|PI_HEADLESS|OPENCODE_RUN)\b"
)

# SPEC-DOC-028: path-like backtick references in constitution.md.
_CONSTITUTION_REF_RE = re.compile(
    r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|md|sh|json|toml|txt|cfg|yml|yaml))`"
)


class CoherenceValidator:
    """Constitution and pattern-version coherence."""

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir
        self.repo_root = repo_root

    def check_constitution(self) -> list[SpecsDoctorIssue]:
        path = self.specs_dir / "constitution.md"
        if not path.exists():
            return [
                SpecsDoctorIssue(
                    code="SPEC-DOC-001",
                    severity=Severity.ERROR,
                    description="specs/constitution.md is missing",
                    path=str(path),
                )
            ]
        return []

    def check_specs_pattern_version(self) -> list[SpecsDoctorIssue]:
        """WARN-only: the tree's ``specs_pattern_version`` is below the canonical
        version the library ships. Recommends ``dadaia specs upgrade`` (FR-S05)."""
        from dadaia_workspace.core import specs_version as _ver

        current = _ver.read_pattern_version(self.specs_dir)
        if current >= _ver.CANONICAL_SPECS_VERSION:
            return []
        return [
            SpecsDoctorIssue(
                code="SPECS-VERSION",
                severity=Severity.WARNING,
                description=(
                    # The remedy carries the tree it was produced for. `specs upgrade`
                    # has no --context option, so the bare line acted on the BOUND
                    # context — doing nothing when unbound, and silently upgrading a
                    # different repo when bound elsewhere. An upgrade rewrites artifacts
                    # and re-stamps the constitution, so aiming it at the wrong tree is
                    # worse than the staleness it was meant to fix.
                    f"specs_pattern_version is {current}, below the canonical "
                    f"{_ver.CANONICAL_SPECS_VERSION}. "
                    f"Run: dadaia specs upgrade --specs-dir {self.specs_dir}"
                ),
                path=str(self.specs_dir / "constitution.md"),
            )
        ]

    def check_constitution_file_refs(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-028: every path-like backtick reference in constitution.md to a
        repo file should resolve.

        Resolution is relative to ``repo_root``; without it the check is a no-op
        (the doctor is otherwise a pure specs_dir-scoped module). References that
        are clearly not repo paths (bare filenames, glob-only, or generic tokens
        like ``<id>``) are skipped — only refs containing a ``/`` separator OR a
        recognised root-level filename are resolved, to avoid false positives on
        illustrative inline names.
        """
        if self.repo_root is None:
            return []
        constitution = self.specs_dir / "constitution.md"
        if not constitution.exists():
            return []
        text = constitution.read_text(encoding="utf-8")
        issues: list[SpecsDoctorIssue] = []
        seen: set[str] = set()
        for m in _CONSTITUTION_REF_RE.finditer(text):
            ref = m.group(1)
            if ref in seen:
                continue
            seen.add(ref)
            # Only resolve refs that look like a real repo path: they must contain a
            # directory separator (e.g. ``docs/01_medium_codex.md``,
            # ``specs/memory/architecture.md``). Bare filenames (``AGENTS.md``,
            # ``CLAUDE.md``, ``SPEC.md``) are contract tokens that appear in many
            # locations and are intentionally not resolved here.
            if "/" not in ref:
                continue
            if (self.repo_root / ref).exists():
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-028",
                    severity=Severity.WARNING,
                    description=(
                        f"constitution.md references '{ref}' but it does not resolve "
                        f"against the repo root ({self.repo_root}). Point it at a real "
                        f"path or delete the line — find it with:  grep -n {ref!r} "
                        f"{constitution}   (SPEC-DOC-028)."
                    ),
                    path=str(constitution),
                )
            )
        return issues

    def check_constitution_no_runtime_enum(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-037 (v0.1.47 W1-9 / WS-E): constitution must not enumerate runtime kinds.

        The constitution states the runtime-kind INVARIANT and cites ``[[tech-stack]]`` (the
        roster single-source) instead of re-encoding a mutable ``AgentRuntimeKind`` roster.
        Any standalone enum-member token (FAKE / CODEX_EXEC / CLAUDE_SDK / PI_HEADLESS /
        OPENCODE_RUN, matched word-bounded + uppercase per :data:`_CONSTITUTION_RUNTIME_KIND_RE`)
        in ``specs/constitution.md`` is an ERROR — the recurrence guard behind the constitution
        rewrite. The Layer model set ``{claude, codex, pi}`` is not a runtime-kind enumeration
        and is deliberately not matched. Absent constitution → no-op (SPEC-DOC-001 owns that).
        """
        path = self.specs_dir / "constitution.md"
        if not path.exists():
            return []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return []
        found = sorted({m.group(1) for m in _CONSTITUTION_RUNTIME_KIND_RE.finditer(text)})
        if not found:
            return []
        tokens = ", ".join(found)
        return [
            SpecsDoctorIssue(
                code="SPEC-DOC-037",
                severity=Severity.ERROR,
                description=(
                    f"constitution.md enumerates AgentRuntimeKind member/harness-roster "
                    f"token(s) ({tokens}). The constitution must state the runtime-kind "
                    "invariant and cite [[tech-stack]] as the roster single-source, never "
                    "enumerate concrete runtime kinds (SPEC-DOC-037, ERROR)."
                ),
                path=str(path),
            )
        ]
