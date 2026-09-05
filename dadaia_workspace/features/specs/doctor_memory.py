"""Memory validator (v0.1.55 FR1): memory-atom files, atomicity, CAT-1, LINT-1, MEM-DRIFT-1.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the memory-markdown-source
invariants: required atoms present with a heading (SPEC-DOC-002/002L), no changelog/history
headings (SPEC-DOC-008), catalog↔atom sync (CAT-1), the LINT-1 memory-atom lint, and (v0.5.1
T-051-22 rework) MEM-DRIFT-1's features-package-map-vs-live-tree WARNING. LINT-1 imports
``features.specs.memory_lint`` directly (v0.4.3 T-043-20/FR16 — no subprocess, no dependency
on the projected ``public/scripts/lint-memory-atoms.py`` copy existing or being current).
Leaf-only: imports the shared leaves + core, never a sibling validator.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core import frontmatter as _fm
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.specs_repair import (  # noqa: F401
    has_unfilled_angle_placeholders,
    is_placeholder_atom,
    remove_placeholder_atoms,
)
from dadaia_workspace.features.specs import memory_canon, memory_lint
from dadaia_workspace.features.specs.canon import default_public_dir
from dadaia_workspace.features.specs.doctor_types import (
    Severity,
    SpecsDoctorIssue,
    _MemoryMdSummary,
)

# ONE home for memory-canon facts (F011): features.specs.memory_canon.
FORBIDDEN_MEMORY_H2_RE = memory_canon.FORBIDDEN_MEMORY_HEADING_RE
TOPLEVEL_MEMORY_FILES = memory_canon.MEMORY_TOPLEVEL_FILES
# Product memory is a folder catalog: index.md is required + 0..N feature .md atoms.
PRODUCT_INDEX_REL = "product/index.md"

# ---------------------------------------------------------------------------
# Markdown memory atom helpers
# ---------------------------------------------------------------------------

# Any ATX heading (H1-H6): satisfies the "has a heading" requirement.
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_MD_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MD_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = memory_canon.WIKILINK_RE


def _parse_memory_md(path: Path) -> _MemoryMdSummary:
    """Extract the facts the doctor needs from a memory .md atom."""
    content = path.read_text(encoding="utf-8")

    # Extract frontmatter if present — tolerant: any parse failure (no delimiter,
    # invalid YAML, non-mapping block) degrades to "no frontmatter" rather than
    # raising, same as the pre-consolidation behaviour.
    fm: dict | None = None  # type: ignore[type-arg]
    body = content
    parsed = _fm.parse(content)
    if isinstance(parsed, _fm.Frontmatter):
        fm = parsed.data
        body = parsed.body

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


# ---------------------------------------------------------------------------
# MEM-DRIFT-1: features package-map mermaid block vs the live tree
# ---------------------------------------------------------------------------
#
# Relocated (v0.5.1 T-051-22 rework) from the deleted push-gated contract test
# ``tests/contract/test_architecture_diagrams_current.py`` (removed at 5e0719af, bug
# ``push-gate-test-pins-memory-package-count-that-only-closure-may-change``) per
# qa-engineer's 2026-08-29 deletion-verdict handoff: the diagram-vs-code correspondence
# guard is real and must survive, but never on a push-gated tier — every future package
# add/delete during IMPLEMENTATION would go red before the next CLOSURE gets to update
# memory. See ``check_mem_drift1_features_package_map`` below for the WARNING itself.

# ARCHITECTURE.md's "features package map" H3 heading — matched by SHAPE, not by the
# parenthetical package count. The deleted test's package-COUNT assertion is the part the
# bug diagnosed as structurally wrong and is DROPPED here entirely; never reintroduce it.
_FEATURES_PKG_MAP_HEADING_RE = re.compile(
    r"^### `dadaia_workspace/features` — package map \(\d+ packages\)\s*$", re.MULTILINE
)
_MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
# The single `pkgs["a · b · c"]` flowchart node inside that heading's mermaid block — the
# ONLY line this rule reads. The sibling `subs[...]` node (reports submodules) is out of
# scope: MEM-DRIFT-1 covers feature PACKAGE names only.
_PKGS_NODE_RE = re.compile(r'pkgs\["([^"]*)"\]')


def _mermaid_block_after_heading(text: str, heading_end: int) -> str | None:
    """The sole fenced ```mermaid block in the section starting at *heading_end* (up to
    the next H2/H3 heading, or end of file). Mirrors the deleted contract test's helper."""
    next_heading = re.search(r"\n#{2,3}\s", text[heading_end:])
    section = (
        text[heading_end : heading_end + next_heading.start()]
        if next_heading
        else text[heading_end:]
    )
    block_match = _MERMAID_BLOCK_RE.search(section)
    return block_match.group(1) if block_match else None


def _live_feature_package_names() -> set[str]:
    """The live ``dadaia_workspace/features/<pkg>`` package names.

    Introspects the SAME installed ``dadaia_workspace.features`` namespace this module
    itself lives under — never a hardcoded name list (the deleted contract test's own
    technique, preserved). ``dadaia_workspace.features`` is the package NAMESPACE, not a
    sibling feature: the `features-no-cross-feature` independence contract's ``modules =``
    list names only the sub-packages (``features.panel``, …, never bare ``features``
    itself), and this module's own empty ``__init__.py`` means importing it loads no
    sibling code — so this import carries no cross-feature edge (verified live by
    `lint-imports --config setup.cfg --no-cache`, which this module's own contract gates).
    Falls back to a filesystem walk from this module's own path — never a subprocess,
    never a hardcoded list — if that ever stops holding.
    """
    try:
        import importlib
        import pkgutil

        pkg = importlib.import_module("dadaia_workspace.features")
        return {name for _finder, name, ispkg in pkgutil.iter_modules(pkg.__path__) if ispkg}
    except ImportError:
        features_dir = Path(__file__).resolve().parents[1]
        return {
            child.name
            for child in features_dir.iterdir()
            if child.is_dir() and (child / "__init__.py").is_file()
        }


def _iter_memory_md_files(mem_dir: Path) -> list[Path]:
    """All memory .md atom files that should be checked for atomicity.

    Includes the top-level singles (ARCHITECTURE.md, TECHSTACK.md, QUALITY.md) and every
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

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir

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

    def check_fixed_sections(self, public_dir: Path | None) -> list[SpecsDoctorIssue]:
        """FIXED-1: a fixed law block is missing; FIXED-2: its body is not the fragment."""
        fragments_dir = public_dir if public_dir is not None else default_public_dir()
        issues: list[SpecsDoctorIssue] = []
        for rel, section_id in memory_canon.FIXED_SECTIONS:
            path = self.specs_dir / rel
            if not path.is_file():
                continue
            try:
                fragment = memory_canon.read_fixed_fragment(fragments_dir, section_id)
            except FileNotFoundError:
                issues.append(
                    SpecsDoctorIssue(
                        code="FIXED-1",
                        severity=Severity.ERROR,
                        description=(
                            f"{rel}: library fragment `{section_id}` is missing under "
                            f"{fragments_dir} — reinstall the library"
                        ),
                        path=str(path),
                        fixable=False,
                    )
                )
                continue
            body = memory_canon.extract_fixed_section(path.read_text(encoding="utf-8"), section_id)
            if body == fragment:
                continue
            state = "is missing" if body is None else "differs from the library fragment"
            issues.append(
                SpecsDoctorIssue(
                    code="FIXED-1" if body is None else "FIXED-2",
                    severity=Severity.ERROR,
                    description=(
                        f"{rel}: fixed law section `{section_id}` {state} — "
                        "`dadaia specs doctor --fix` inserts or refreshes it"
                    ),
                    path=str(path),
                    fixable=True,
                )
            )
        return issues

    def fix_fixed_section(self, issue: SpecsDoctorIssue, public_dir: Path | None) -> None:
        """Insert or refresh the fixed law block of the file named by *issue*."""
        if not issue.path:
            return
        fragments_dir = public_dir if public_dir is not None else default_public_dir()
        path = Path(issue.path)
        section_id = memory_canon.FIXED_SECTION_BY_PATH[path.relative_to(self.specs_dir).as_posix()]
        fragment = memory_canon.read_fixed_fragment(fragments_dir, section_id)
        rendered = memory_canon.render_fixed_section(
            path.read_text(encoding="utf-8"), section_id, fragment
        )
        atomic_write(path, rendered)

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
            #
            # v6 canon (FR1/A1.5/A1.6, T-050-06): the top-level trio's PRE-migration
            # lowercase names (architecture.md, tech-stack.md, quality-assurance.md) are
            # recognized here too, so a consumer tree `specs upgrade` has not yet
            # hand-renamed (the rename is a by-hand recipe step, never automated) is not
            # mistaken for a genuinely stray/orphaned file — SPEC-DOC-002/TREE-3 already
            # correctly report the RENAMED file as missing; SPEC-DOC-002L's job is orphan
            # detection, not a second "please rename" signal.
            _RETIRED_TOPLEVEL_MEMORY_NAMES = frozenset(
                {"architecture.md", "tech-stack.md", "quality-assurance.md"}
            )
            _canonical_root_md = {Path(f).name for f in TOPLEVEL_MEMORY_FILES}
            for legacy in mem_dir.glob("*.md"):
                if legacy.name == "AGENTS.md":
                    continue
                if legacy.name in _canonical_root_md:
                    continue
                if legacy.name in _RETIRED_TOPLEVEL_MEMORY_NAMES:
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

        ERROR on frontmatter/schema violations, forbidden (changelog/history)
        headings, duplicate headings, and unresolved wikilinks. A heading vocabulary
        is prose policy, not a lint (v0.5.0) — no WARNING severity path exists here
        any more.

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

    def check_mem_drift1_features_package_map(self) -> list[SpecsDoctorIssue]:
        """MEM-DRIFT-1: the features package-map mermaid diagram matches the live tree.

        One WARNING per stale node (a package the diagram names that no longer exists)
        and one WARNING per missing node (a live package the diagram never names).
        Severity is always WARNING — never ERROR, never blocking push/CI (same class as
        SPECS-VERSION/SPEC-DOC-030) — this is a continuous memory-drift signal, not a
        structural invariant. See the module-level docstring above
        ``_FEATURES_PKG_MAP_HEADING_RE`` for the relocation history.

        Silent (returns ``[]``) when ``ARCHITECTURE.md`` is absent, the features
        package-map heading is absent, or its mermaid block / ``pkgs[...]`` node is
        absent — this rule only fires when there is something concrete to compare;
        SPEC-DOC-002/TREE-3 already own "the atom itself is missing".
        """
        architecture_md = self.specs_dir / "memory" / "ARCHITECTURE.md"
        if not architecture_md.is_file():
            return []
        text = architecture_md.read_text(encoding="utf-8")
        heading_match = _FEATURES_PKG_MAP_HEADING_RE.search(text)
        if heading_match is None:
            return []
        mermaid = _mermaid_block_after_heading(text, heading_match.end())
        if mermaid is None:
            return []
        pkgs_match = _PKGS_NODE_RE.search(mermaid)
        if pkgs_match is None:
            return []
        declared = {tok.strip() for tok in pkgs_match.group(1).split("·") if tok.strip()}
        live = _live_feature_package_names()

        issues: list[SpecsDoctorIssue] = []
        for stale in sorted(declared - live):
            issues.append(
                SpecsDoctorIssue(
                    code="MEM-DRIFT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"ARCHITECTURE.md features package map names '{stale}' but "
                        "dadaia_workspace/features has no such live package — update "
                        "the diagram (memory drift)."
                    ),
                    path=str(architecture_md),
                )
            )
        for missing in sorted(live - declared):
            issues.append(
                SpecsDoctorIssue(
                    code="MEM-DRIFT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"dadaia_workspace/features/{missing} is a live package not named "
                        "in ARCHITECTURE.md's features package map — update the diagram "
                        "(memory drift)."
                    ),
                    path=str(architecture_md),
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
