"""Memory validator (v0.1.55 FR1): memory-atom files, atomicity, CAT-1, LINT-1.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the memory-markdown-source
invariants: required atoms present with a heading (SPEC-DOC-002/002L), no changelog/history
headings (SPEC-DOC-008), catalog↔atom sync (CAT-1), and the LINT-1 memory-atom lint. LINT-1
imports ``features.specs.memory_lint`` directly (v0.4.3 T-043-20/FR16 — no subprocess, no
dependency on the projected ``public/scripts/lint-memory-atoms.py`` copy existing or being
current). Leaf-only: imports the shared leaves + core, never a sibling validator.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from dadaia_workspace.core.protocols.process_runner import ProcessRunner
from dadaia_workspace.core.specs_repair import (  # noqa: F401
    has_unfilled_angle_placeholders,
    is_placeholder_atom,
    remove_placeholder_atoms,
)
from dadaia_workspace.features.specs import memory_lint
from dadaia_workspace.features.specs.doctor_types import (
    Severity,
    SpecsDoctorIssue,
    _MemoryMdSummary,
)

FORBIDDEN_MEMORY_H2_RE = re.compile(r"^(Changelog|History|Hist[óo]rico|Versions?)\b", re.IGNORECASE)
# Top-level memory files (.md canonical source).
TOPLEVEL_MEMORY_FILES = ("architecture.md", "tech-stack.md", "quality-assurance.md")
# Product memory is a folder catalog: index.md is required + 0..N feature .md atoms.
PRODUCT_INDEX_REL = "product/index.md"

# ---------------------------------------------------------------------------
# Markdown memory atom helpers
# ---------------------------------------------------------------------------

_MD_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Any ATX heading (H1-H6): satisfies the "has a heading" requirement.
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_MD_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MD_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _parse_memory_md(path: Path) -> _MemoryMdSummary:
    """Extract the facts the doctor needs from a memory .md atom."""
    content = path.read_text(encoding="utf-8")

    # Extract frontmatter if present
    fm: dict | None = None  # type: ignore[type-arg]
    body = content
    m = _MD_FRONTMATTER_RE.match(content)
    if m:
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            fm = None
        body = content[m.end() :]

    # First H1 heading text (used for heading_text field; may be empty).
    h1_match = _MD_H1_RE.search(body)
    heading_text = h1_match.group(1).strip() if h1_match else ""
    # has_heading is True if the body contains ANY ATX heading (H1–H6), including
    # atoms that only have ## / ### level headings and no H1.
    has_heading = bool(_MD_HEADING_RE.search(body))

    # Check ## headings for forbidden patterns
    forbidden_h2: list[str] = []
    for h2_match in _MD_H2_RE.finditer(body):
        text = h2_match.group(1).strip()
        if text and FORBIDDEN_MEMORY_H2_RE.search(text):
            forbidden_h2.append(text)

    return _MemoryMdSummary(
        has_heading=has_heading,
        heading_text=heading_text,
        forbidden_h2=forbidden_h2,
        frontmatter=fm,
        body=body,
    )


def _iter_memory_md_files(mem_dir: Path) -> list[Path]:
    """All memory .md atom files that should be checked for atomicity.

    Includes the top-level singles (architecture.md, tech-stack.md) and every
    *.md under product/ except index.md (the catalog folder).
    """
    out: list[Path] = []
    for name in TOPLEVEL_MEMORY_FILES:
        p = mem_dir / name
        if p.exists():
            out.append(p)
    product_dir = mem_dir / "product"
    if product_dir.is_dir():
        # Recurse into thematic subdirs (v0.1.9 product/ tree).
        for p in sorted(product_dir.glob("**/*.md")):
            if p.name == "index.md":
                continue
            out.append(p)
    return out


class MemoryValidator:
    """Memory-atom files, atomicity, CAT-1 catalog sync, and LINT-1 lint."""

    def __init__(self, specs_dir: Path, process_runner: ProcessRunner | None = None) -> None:
        self.specs_dir = specs_dir
        # v0.4.3 T-043-20/FR16: LINT-1 no longer shells out (memory_lint is imported
        # directly, below), so process_runner is UNUSED here now. The parameter is
        # kept — never removed — purely for SpecsDoctor.__init__'s call-site
        # compatibility (`MemoryValidator(self.specs_dir, self._process_runner)`,
        # doctor.py:100, outside this task's write set); a future cleanup pass may
        # retire the parameter from SpecsDoctor itself once nothing threads it here.
        self._process_runner: ProcessRunner | None = process_runner

    def check_placeholder_atoms(self) -> list[SpecsDoctorIssue]:
        """MEM-PLACEHOLDER-1: unfilled placeholder atoms under ``specs/memory/**``.

        Old scaffolds shipped a raw ``feature.md`` template (``SLUG_PLACEHOLDER`` and
        friends) that no verb could remediate (bug
        scaffold-repair-cannot-remediate-invalid-placeholder-atom). The issue is
        ``fixable=True``: the fix removes the template artifact — never real content
        (exact-token detection).
        """
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"
        if not mem_dir.is_dir():
            return issues
        for path in sorted(mem_dir.rglob("*.md")):
            if is_placeholder_atom(path):
                issues.append(
                    SpecsDoctorIssue(
                        code="MEM-PLACEHOLDER-1",
                        severity=Severity.ERROR,
                        description=(
                            f"{path.relative_to(self.specs_dir)} is an unfilled placeholder "
                            "atom (template markers never replaced) — remove it or fill it "
                            "with real content (`dadaia specs doctor --fix` removes it)"
                        ),
                        path=str(path),
                        fixable=True,
                    )
                )
        return issues

    def check_tests_agents_placeholder(self) -> list[SpecsDoctorIssue]:
        """AGENTS-PLACEHOLDER-1: an installed ``tests/AGENTS.md`` still carries an
        unfilled ``<TOKEN>`` placeholder (FR8, idea
        ``tests-agents-md-placeholder-doctor-warning``).

        Reuses the MEM-PLACEHOLDER-1 validator shape (same family, WARN not ERROR since
        no verb can auto-fill project-specific numbers). Runs ONLY against the
        **installed** consumer copy at ``<repo-root>/tests/AGENTS.md`` —
        ``specs_dir.parent`` is the repo-root idiom this module's ``REPO-DADAIA-1``
        sibling already uses — never against the canonical template
        (``dadaia_workspace/public/templates/tests-AGENTS.md``), which legitimately
        ships placeholders for the operator to fill in. Silent when the file is absent
        (its presence is not this check's concern) or already filled.
        """
        installed = self.specs_dir.parent / "tests" / "AGENTS.md"
        if not installed.is_file():
            return []
        if not has_unfilled_angle_placeholders(installed):
            return []
        return [
            SpecsDoctorIssue(
                code="AGENTS-PLACEHOLDER-1",
                severity=Severity.WARNING,
                description=(
                    f"{installed} still carries an unfilled `<TOKEN>` placeholder — "
                    "replace every project-specific value before relying on it (see "
                    "the file's own banner)."
                ),
                path=str(installed),
            )
        ]

    def fix_placeholder_atom(self, issue: SpecsDoctorIssue) -> None:
        """Remove an unfilled placeholder atom — re-verified before any delete."""
        if not issue.path:
            return
        path = Path(issue.path)
        if is_placeholder_atom(path):
            path.unlink()

    def check_memory_files(self) -> list[SpecsDoctorIssue]:
        """Check #2: required memory .md atoms exist with non-empty heading.

        Canonical source format is .md (memory-markdown-source-v1).
        Stray .html files are flagged as legacy (SPEC-DOC-002L).
        The product.html-at-root legacy error is retained for historical compat.
        """
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"

        # Required top-level singles
        required: list[tuple[str, Path]] = [
            (name, mem_dir / name) for name in TOPLEVEL_MEMORY_FILES
        ]
        # Required folder catalog entry
        required.append((PRODUCT_INDEX_REL, mem_dir / PRODUCT_INDEX_REL))

        # Plus any optional feature .md atoms that DO exist — they must parse too
        product_dir = mem_dir / "product"
        feature_files: list[tuple[str, Path]] = []
        if product_dir.is_dir():
            feature_files = [
                (f"product/{p.relative_to(product_dir)}", p)
                for p in sorted(product_dir.rglob("*.md"))
                if p.name != "index.md"
            ]

        for rel, p in required + feature_files:
            if not p.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} is missing — memory must be Markdown (.md)",
                        path=str(p),
                    )
                )
                continue
            try:
                summary = _parse_memory_md(p)
            except Exception as e:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} is not parseable: {e}",
                        path=str(p),
                    )
                )
                continue
            if not summary.has_heading:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} has no non-empty heading",
                        path=str(p),
                    )
                )

        # Legacy product.html at memory/ root (pre-folder-catalog) is still an error
        legacy_product = mem_dir / "product.html"
        if legacy_product.exists():
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-002L",
                    severity=Severity.ERROR,
                    description=(
                        "memory/product.html is legacy — product memory is now a folder "
                        "catalog. Move to _archive/legacy-memory/<timestamp>/ and create "
                        "memory/product/index.md + memory/product/<feature>.md files."
                    ),
                    path=str(legacy_product),
                )
            )

        # Flag any stray .html files in memory/ root or product/ as legacy.
        # AGENTS.md is a directory contract, not a memory atom — exempt it.
        # .html files are never written at runtime (D-4); any that appear are stale.
        if mem_dir.exists():
            for stray in mem_dir.glob("*.html"):
                if stray.name == "product.html":
                    continue  # already reported above
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002L",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{stray.name} is a stray HTML file — "
                            "memory atoms must be .md (memory-markdown-source-v1, D-4). "
                            "Remove the .html file; the canonical source is the .md atom."
                        ),
                        path=str(stray),
                    )
                )
            if product_dir.is_dir():
                for stray in product_dir.glob("*.html"):
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-002L",
                            severity=Severity.ERROR,
                            description=(
                                f"memory/product/{stray.name} is a stray HTML file — "
                                "memory atoms must be .md (D-4). Remove the .html file."
                            ),
                            path=str(stray),
                        )
                    )

            # Orphaned .md files at root (no known canonical role) — flag as legacy.
            # AGENTS.md is exempt. TOPLEVEL_MEMORY_FILES (.md) are canonical. index.md in
            # product/ is the generated TOC.  Everything else is flagged.
            _canonical_root_md = {Path(f).name for f in TOPLEVEL_MEMORY_FILES}
            for legacy in mem_dir.glob("*.md"):
                if legacy.name == "AGENTS.md":
                    continue
                if legacy.name in _canonical_root_md:
                    continue
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002L",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{legacy.name} is not a canonical memory atom. "
                            "Move to _archive/legacy-memory/<timestamp>/ if historical."
                        ),
                        path=str(legacy),
                    )
                )

        return issues

    def check_memory_atomicity(self) -> list[SpecsDoctorIssue]:
        """Check #8: no forbidden changelog/history ## headings in memory .md bodies.

        memory-markdown-source-v1: .md is now the canonical source.  We grep the
        Markdown body directly — no YAML escape hatch, no STRUCT bypass.
        Forbidden headings: ## Changelog, ## History, ## Histórico, ## Versions.
        """
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"

        for p in _iter_memory_md_files(mem_dir):
            try:
                summary = _parse_memory_md(p)
            except Exception:
                continue
            rel = p.relative_to(mem_dir).as_posix()
            for label in summary.forbidden_h2:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-008",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{rel} has forbidden heading: ## {label!r} — "
                            "memory atoms must be atomic, not changelogs"
                        ),
                        path=str(p),
                    )
                )
        return issues

    def check_lint1_memory_atoms(self) -> list[SpecsDoctorIssue]:
        """LINT-1: lint every memory atom under specs/memory/ via ``memory_lint``.

        ERROR on frontmatter/schema violations + forbidden headings.
        WARNING on unknown (non-allowlisted) headings.

        v0.4.3 T-043-20/FR16: ``memory_lint`` is imported directly — no subprocess,
        no dependency on the projected ``public/scripts/lint-memory-atoms.py`` copy
        existing, being current, or matching this package's version at all.
        """
        mem_dir = self.specs_dir / "memory"
        if not mem_dir.is_dir():
            return []
        try:
            schema = memory_lint.load_frontmatter_schema()
        except FileNotFoundError as exc:
            return [
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.WARNING,
                    description=f"LINT-1: {exc}",
                    path=str(mem_dir),
                )
            ]

        results = memory_lint.lint_directory(mem_dir, schema)
        if not results:
            return []

        error_lines: list[str] = []
        warn_lines: list[str] = []
        for result in results:
            for err in result.errors:
                error_lines.append(f"  [{result.path}] ERROR: {err}")
            for warn in result.warnings:
                warn_lines.append(f"  [{result.path}] WARN: {warn}")

        issues: list[SpecsDoctorIssue] = []
        if error_lines:
            issues.append(
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.ERROR,
                    description=(
                        "LINT-1: memory atom lint found frontmatter/schema violations "
                        "or forbidden headings:\n" + "\n".join(error_lines)
                    ),
                    path=str(mem_dir),
                )
            )
        elif warn_lines:
            issues.append(
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.WARNING,
                    description=("LINT-1: memory atom lint warnings:\n" + "\n".join(warn_lines)),
                    path=str(mem_dir),
                )
            )
        return issues

    def check_cat1_catalog_sync(self) -> list[SpecsDoctorIssue]:
        """CAT-1: catalog.json must stay in sync with *.md feature atom files.

        memory-markdown-source-v1: .md is canonical source; .html is retired.

        Logic:
        1. Enumerate ``memory/product/*.md`` excluding ``index.md`` → ``md_slugs``.
        2. If ``catalog.json`` is absent and md_slugs is non-empty → one WARNING.
        3. If ``catalog.json`` is present → parse ``features[].slug``:
           - One WARNING per slug in catalog that has no corresponding .md on disk.
           - One WARNING per .md on disk whose slug is not in the catalog.
        4. Severity is always WARNING (never ERROR) — catalog may simply need regeneration.
        """
        import json as _json

        issues: list[SpecsDoctorIssue] = []
        product_dir = self.specs_dir / "memory" / "product"
        catalog_path = product_dir / "catalog.json"

        if not product_dir.is_dir():
            return issues

        # Collect slugs from .md feature atoms (excluding index.md), recursing into subdirs
        md_slugs: set[str] = {p.stem for p in product_dir.rglob("*.md") if p.name != "index.md"}

        if not catalog_path.exists():
            if md_slugs:
                issues.append(
                    SpecsDoctorIssue(
                        code="CAT-1",
                        severity=Severity.WARNING,
                        description=(
                            f"catalog.json absent; {len(md_slugs)} feature .md atom"
                            f"{'s' if len(md_slugs) != 1 else ''} present; "
                            "run `dadaia memory catalog generate` to create it."
                        ),
                        path=str(catalog_path),
                    )
                )
            return issues

        # catalog.json exists — compare slug sets
        try:
            data = _json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_slugs: set[str] = {
                str(entry.get("slug", ""))
                for entry in data.get("features", [])
                if entry.get("slug")
            }
        except Exception as exc:
            issues.append(
                SpecsDoctorIssue(
                    code="CAT-1",
                    severity=Severity.WARNING,
                    description=f"catalog.json is not valid JSON: {exc}",
                    path=str(catalog_path),
                )
            )
            return issues

        # Slugs in catalog but no .md on disk
        for slug in sorted(catalog_slugs - md_slugs):
            issues.append(
                SpecsDoctorIssue(
                    code="CAT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"catalog.json lists slug '{slug}' but no corresponding "
                        f"'{slug}.md' exists in memory/product/. "
                        "Run `dadaia memory catalog generate` to resync."
                    ),
                    path=str(product_dir / f"{slug}.md"),
                )
            )

        # .md atoms on disk but not in catalog
        for slug in sorted(md_slugs - catalog_slugs):
            issues.append(
                SpecsDoctorIssue(
                    code="CAT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"'{slug}.md' exists in memory/product/ but is not listed in "
                        "catalog.json. "
                        "Run `dadaia memory catalog generate` to resync."
                    ),
                    path=str(product_dir / f"{slug}.md"),
                )
            )

        return issues
