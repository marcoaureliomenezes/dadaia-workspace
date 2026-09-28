"""Memory validator: atom files, LINT-1, MEM-DRIFT-1, MEM-DRIFT-2.
Single-responsibility sibling of the SpecsDoctor coordinator. Owns the memory-markdown-source
invariants: required atoms present with a heading (SPEC-DOC-002), the LINT-1 memory-atom
lint (the one home of the forbidden-heading rule; the generated pair is LEDGER-MEMORY's), and (v0.5.1
T-051-22 rework) MEM-DRIFT-1's features-package-map-vs-live-tree WARNING and (0.4.7 FR2)
MEM-DRIFT-2's memory-citation WARNING (finders: ``features.specs.citations``). LINT-1 imports
``features.specs.memory_lint`` directly.
Leaf-only: imports the shared leaves + core, never a sibling validator.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Collection
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import materialize_line, shell_line
from dadaia_workspace.features.specs import citations, memory_canon, memory_lint
from dadaia_workspace.features.specs.canon import default_public_dir, is_canon_path
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

# ONE home for memory-canon facts (F011): features.specs.memory_canon.
TOPLEVEL_MEMORY_FILES = memory_canon.MEMORY_TOPLEVEL_FILES
# Product memory is a folder catalog: index.md is required + 0..N feature .md atoms.
PRODUCT_INDEX_REL = "product/index.md"
_PKG = "dadaia-workspace"  # a missing library fragment is repaired by reinstalling it

#: Template tokens of the retired placeholder feature atom: an atom carrying one was never
#: filled (bug scaffold-repair-cannot-remediate-invalid-placeholder-atom); MEM-PLACEHOLDER-1
#: removes it.
_PLACEHOLDER_TOKENS = ("SLUG_PLACEHOLDER", "TITLE_PLACEHOLDER", "RELEASE_PLACEHOLDER")
#: FR8: an unfilled installed-file token is a tight code span around the token alone
#: (`` `<UNIT_TIMEOUT_S>` ``); a token illustrated inside a longer span is not one.
_ANGLE_PLACEHOLDER_RE = re.compile(r"`<[A-Z_]+>`")


def _read_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""  # never flag, never delete on uncertainty


def is_placeholder_atom(path: Path) -> bool:
    """True when *path* is an unfilled placeholder memory atom (template artifact)."""
    return any(token in _read_or_empty(path) for token in _PLACEHOLDER_TOKENS)


def has_unfilled_angle_placeholders(path: Path) -> bool:
    """True when *path* still carries an unfilled `` `<TOKEN>` `` placeholder (FR8)."""
    return bool(_ANGLE_PLACEHOLDER_RE.search(_read_or_empty(path)))


# ---------------------------------------------------------------------------
# Markdown memory atom helpers
# ---------------------------------------------------------------------------

# Any ATX heading (H1-H6): satisfies the "has a heading" requirement.
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)


def _has_heading(path: Path) -> bool:
    """True when the atom's body — its whole text when the frontmatter does not parse —
    carries an ATX heading."""
    content = path.read_text(encoding="utf-8")
    fm, body, _problem = memory_canon.parse_atom(content)
    return bool(_MD_HEADING_RE.search(body if fm is not None else content))


# ---------------------------------------------------------------------------
# MEM-DRIFT-1: features package-map mermaid block vs the live tree
# ---------------------------------------------------------------------------
#
# Relocated (v0.5.1 T-051-22) from a push-gated contract test (bug
# ``push-gate-test-pins-memory-package-count-that-only-closure-may-change``): the
# diagram-vs-code correspondence guard is real, but never on a push-gated tier — every future package
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
    itself lives under — never a hardcoded name list. That namespace is the package, not
    a sibling feature: the `features-no-cross-feature` contract's ``modules =`` list names
    only the sub-packages, and the namespace's own empty ``__init__.py`` loads no sibling
    code — so this import carries no cross-feature edge (gated live by `lint-imports`).
    """
    import importlib
    import pkgutil

    pkg = importlib.import_module("dadaia_workspace.features")
    return {name for _finder, name, ispkg in pkgutil.iter_modules(pkg.__path__) if ispkg}


class MemoryValidator:
    """Memory-atom files and the LINT-1 lint."""

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
                            "with real content"
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
        ``specs_dir.parent`` is the repo-root idiom the workspace section's repo-tree walk
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
                            f"{rel}: library fragment `{section_id}` is missing: {fragments_dir}"
                        ),
                        path=str(path),
                        fixable=False,
                        fix=shell_line(sys.executable, "-m", "pip", "install", "-U", _PKG),
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
                    description=(f"{rel}: fixed law section `{section_id}` {state}"),
                    path=str(path),
                    # The one writer refuses a link (CWE-59), so a link is never advertised
                    # as fixable (CWE-393); its fix materializes the link first.
                    fixable=not path.is_symlink(),
                    fix=materialize_line(path, path.resolve()) if path.is_symlink() else "",
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

        A stray or legacy file is TREE-8's."""
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"

        required: list[tuple[str, Path]] = [
            (name, mem_dir / name) for name in TOPLEVEL_MEMORY_FILES
        ]
        required.append((PRODUCT_INDEX_REL, mem_dir / PRODUCT_INDEX_REL))

        product_dir = mem_dir / "product"
        feature_files: list[tuple[str, Path]] = []
        if product_dir.is_dir():
            feature_files = [
                (f"product/{p.relative_to(product_dir)}", p)
                for p in sorted(product_dir.rglob("*.md"))
                if p.name != "index.md"
            ]

        for rel, p in required + feature_files:
            if not p.exists():  # TREE-3 owns a missing atom (and seeds it)
                continue
            try:
                has_heading = _has_heading(p)
            except Exception as e:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} is not parseable: {e}",
                        path=str(p),
                        fix=f"Operator action: repair {p}",
                    )
                )
                continue
            if not has_heading:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} has no non-empty heading",
                        path=str(p),
                        fix=f"Operator action: give {p} a `#` heading",
                    )
                )

        return issues

    def check_lint1_memory_atoms(self) -> list[SpecsDoctorIssue]:
        """LINT-1: lint every memory atom under specs/memory/ via ``memory_lint``.

        ERROR on frontmatter/schema violations, forbidden (changelog/history)
        headings, duplicate headings, and unresolved wikilinks. A heading vocabulary
        is prose policy, not a lint (v0.5.0) — no WARNING severity path exists here
        any more.
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

        # One issue per error, naming its atom: the doctor prints one line per finding.
        return [
            SpecsDoctorIssue(
                code="LINT-1",
                severity=Severity.ERROR,
                description=err,
                path=str(result.path),
                fix=f"Operator action: correct {result.path} ({err})",
            )
            for result in memory_lint.lint_directory(mem_dir, schema)
            for err in result.errors
            if is_canon_path(result.path.relative_to(self.specs_dir).as_posix())
        ]

    def check_mem_drift2_citations(
        self,
        *,
        repo_root: Path | None,
        command_paths: Collection[tuple[str, ...]] | None,
    ) -> list[SpecsDoctorIssue]:
        """MEM-DRIFT-2: every ``dadaia <verb>`` and repo path a memory atom cites still
        exists — the SAME finders (``features.specs.citations``) the ``public/**``
        citation contract tests use, never a second rule. WARNING and unfixable, like
        MEM-DRIFT-1: memory drift is a closure finding (QUALITY.md), so a verb retired
        mid-implementation never reddens an unrelated task. *command_paths* is plain data
        from the CLI root.
        """
        return [
            SpecsDoctorIssue(
                code="MEM-DRIFT-2",
                severity=Severity.WARNING,
                description=(
                    f"memory atom cites what no longer exists: {violation} "
                    "(memory drift — correct the atom at closure)."
                ),
                path=str(path),
            )
            for path, violation in citations.memory_citation_violations(
                self.specs_dir / "memory", repo_root=repo_root, command_paths=command_paths
            )
        ]

    def check_mem_drift1_features_package_map(self) -> list[SpecsDoctorIssue]:
        """MEM-DRIFT-1: the features package-map mermaid diagram matches the live tree.

        One WARNING per stale node (a package the diagram names that no longer exists)
        and one WARNING per missing node (a live package the diagram never names).
        Severity is always WARNING — never ERROR, never blocking push/CI (same class as
        SPEC-DOC-030) — this is a continuous memory-drift signal, not a
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
