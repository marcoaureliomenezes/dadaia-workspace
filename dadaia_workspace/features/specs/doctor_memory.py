"""Memory validator: required atoms (SPEC-DOC-002), placeholders, fixed law sections,
LINT-1 atom lint, MEM-DRIFT-1 package map vs live tree, MEM-DRIFT-2 citations.
Leaf-only: imports the shared leaves + core, never a sibling validator."""

from __future__ import annotations

import re
import sys
from collections.abc import Collection
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import materialize_line, shell_line
from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.features.specs import citations, memory_canon, memory_lint
from dadaia_workspace.features.specs.canon import default_public_dir, is_canon_path
from dadaia_workspace.features.specs.doctor_types import Severity, finding_path, specs_finding

TOPLEVEL_MEMORY_FILES = memory_canon.MEMORY_TOPLEVEL_FILES
PRODUCT_INDEX_REL = "product/index.md"
_PKG = "dadaia-workspace"  # a missing library fragment is repaired by reinstalling it
_PLACEHOLDER_TOKENS = ("SLUG_PLACEHOLDER", "TITLE_PLACEHOLDER", "RELEASE_PLACEHOLDER")
# An unfilled token is a tight code span around the token alone; a longer span only illustrates.
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
# Matched by shape, never by the package count: the count changes only at closure.
_FEATURES_PKG_MAP_HEADING_RE = re.compile(
    r"^### `dadaia_workspace/features` — package map \(\d+ packages\)\s*$", re.MULTILINE
)
_MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_PKGS_NODE_RE = re.compile(r'pkgs\["([^"]*)"\]')


def _read_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""  # never flag, never delete on uncertainty


def is_placeholder_atom(path: Path) -> bool:
    """True when *path* is an unfilled placeholder memory atom (template artifact)."""
    return any(token in _read_or_empty(path) for token in _PLACEHOLDER_TOKENS)


def _has_heading(path: Path) -> bool:
    """An ATX heading in the atom's body — its whole text when the frontmatter does not parse."""
    content = path.read_text(encoding="utf-8")
    fm, body, _problem = memory_canon.parse_atom(content)
    return bool(_MD_HEADING_RE.search(body if fm is not None else content))


def _mermaid_block_after_heading(text: str, heading_end: int) -> str | None:
    """The first ```mermaid block before the next H2/H3 heading."""
    next_heading = re.search(r"\n#{2,3}\s", text[heading_end:])
    section = text[heading_end : heading_end + next_heading.start() if next_heading else None]
    block_match = _MERMAID_BLOCK_RE.search(section)
    return block_match.group(1) if block_match else None


def _live_feature_package_names() -> set[str]:
    # The namespace package's empty __init__ loads no sibling: no cross-feature edge.
    import importlib
    import pkgutil

    pkg = importlib.import_module("dadaia_workspace.features")
    return {name for _finder, name, ispkg in pkgutil.iter_modules(pkg.__path__) if ispkg}


class MemoryValidator:
    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir

    def check_placeholder_atoms(self) -> list[SectionFinding]:
        """MEM-PLACEHOLDER-1: unfilled placeholder atoms; fixable by removing them."""
        mem_dir = self.specs_dir / "memory"
        if not mem_dir.is_dir():
            return []
        return [
            specs_finding(
                "MEM-PLACEHOLDER-1",
                Severity.ERROR,
                f"{path.relative_to(self.specs_dir).as_posix()} is an unfilled placeholder atom (template "
                "markers never replaced) — remove it or fill it with real content",
                str(path),
                fixable=True,
            )
            for path in sorted(mem_dir.rglob("*.md"))
            if is_placeholder_atom(path)
        ]

    def fix_placeholder_atom(self, issue: SectionFinding) -> None:
        """Remove an unfilled placeholder atom — re-verified before any delete."""
        named = finding_path(issue)
        if named and is_placeholder_atom(Path(named)):
            Path(named).unlink()

    def check_fixed_sections(self, public_dir: Path | None) -> list[SectionFinding]:
        """FIXED-1: a fixed law block is missing; FIXED-2: its body is not the fragment."""
        fragments_dir = public_dir if public_dir is not None else default_public_dir()
        issues: list[SectionFinding] = []
        for rel, section_id in memory_canon.FIXED_SECTIONS:
            path = self.specs_dir / rel
            if not path.is_file():
                continue
            try:
                fragment = memory_canon.read_fixed_fragment(fragments_dir, section_id)
            except FileNotFoundError:
                issues.append(
                    specs_finding(
                        "FIXED-1",
                        Severity.ERROR,
                        f"{rel}: library fragment `{section_id}` is missing: {fragments_dir}",
                        str(path),
                        fix=shell_line(sys.executable, "-m", "pip", "install", "-U", _PKG),
                    )
                )
                continue
            body = memory_canon.extract_fixed_section(path.read_text(encoding="utf-8"), section_id)
            if body == fragment:
                continue
            state = "is missing" if body is None else "differs from the library fragment"
            # The one writer refuses a link (CWE-59): a link is materialized first, never fixable.
            issues.append(
                specs_finding(
                    "FIXED-1" if body is None else "FIXED-2",
                    Severity.ERROR,
                    f"{rel}: fixed law section `{section_id}` {state}",
                    str(path),
                    fixable=not path.is_symlink(),
                    fix=materialize_line(path, path.resolve()) if path.is_symlink() else "",
                )
            )
        return issues

    def fix_fixed_section(self, issue: SectionFinding, public_dir: Path | None) -> None:
        """Insert or refresh the fixed law block of the file named by *issue*."""
        named = finding_path(issue)
        if not named:
            return
        fragments_dir = public_dir if public_dir is not None else default_public_dir()
        path = Path(named)
        section_id = memory_canon.FIXED_SECTION_BY_PATH[path.relative_to(self.specs_dir).as_posix()]
        fragment = memory_canon.read_fixed_fragment(fragments_dir, section_id)
        text = path.read_text(encoding="utf-8")
        atomic_write(path, memory_canon.render_fixed_section(text, section_id, fragment))

    def check_memory_files(self) -> list[SectionFinding]:
        """SPEC-DOC-002: every present required/feature atom parses and has a heading.
        A missing atom is TREE-3's; a stray file is TREE-8's."""
        mem_dir = self.specs_dir / "memory"
        product_dir = mem_dir / "product"
        rels = [*TOPLEVEL_MEMORY_FILES, PRODUCT_INDEX_REL]
        if product_dir.is_dir():
            rels += [
                f"product/{p.relative_to(product_dir).as_posix()}"
                for p in sorted(product_dir.rglob("*.md"))
                if p.name != "index.md"
            ]
        issues: list[SectionFinding] = []
        for rel in rels:
            p = mem_dir / rel
            if not p.exists():
                continue
            try:
                if _has_heading(p):
                    continue
                problem, fix = "has no non-empty heading", f"give {p} a `#` heading"
            except Exception as e:
                problem, fix = f"is not parseable: {e}", f"repair {p}"
            issues.append(
                specs_finding(
                    "SPEC-DOC-002",
                    Severity.ERROR,
                    f"memory/{rel} {problem}",
                    str(p),
                    fix=f"Operator action: {fix}",
                )
            )
        return issues

    def check_lint1_memory_atoms(self) -> list[SectionFinding]:
        """LINT-1: one ERROR per ``memory_lint`` error of a canon memory atom."""
        mem_dir = self.specs_dir / "memory"
        if not mem_dir.is_dir():
            return []
        try:
            schema = memory_lint.load_frontmatter_schema()
        except FileNotFoundError as exc:
            return [specs_finding("LINT-1", Severity.WARNING, f"LINT-1: {exc}", str(mem_dir))]
        return [
            specs_finding(
                "LINT-1",
                Severity.ERROR,
                err,
                str(result.path),
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
    ) -> list[SectionFinding]:
        """MEM-DRIFT-2: every ``dadaia <verb>`` and repo path an atom cites still exists.
        WARNING: memory drift is a closure finding, never a mid-task red."""
        return [
            specs_finding(
                "MEM-DRIFT-2",
                Severity.WARNING,
                f"memory atom cites what no longer exists: {violation} "
                "(memory drift — correct the atom at closure).",
                str(path),
            )
            for path, violation in citations.memory_citation_violations(
                self.specs_dir / "memory", repo_root=repo_root, command_paths=command_paths
            )
        ]

    def check_mem_drift1_features_package_map(self) -> list[SectionFinding]:
        """MEM-DRIFT-1: one WARNING per stale or missing node of ARCHITECTURE.md's features
        package map vs the live tree; silent when the map is absent."""
        architecture_md = self.specs_dir / "memory" / "ARCHITECTURE.md"
        if not architecture_md.is_file():
            return []
        text = architecture_md.read_text(encoding="utf-8")
        heading = _FEATURES_PKG_MAP_HEADING_RE.search(text)
        mermaid = _mermaid_block_after_heading(text, heading.end()) if heading else None
        pkgs_match = _PKGS_NODE_RE.search(mermaid) if mermaid is not None else None
        if pkgs_match is None:
            return []
        declared = {tok.strip() for tok in pkgs_match.group(1).split("·") if tok.strip()}
        live = _live_feature_package_names()
        stale = "ARCHITECTURE.md features package map names '{}' but dadaia_workspace/features"
        stale += " has no such live package — update the diagram (memory drift)."
        missing = "dadaia_workspace/features/{} is a live package not named in ARCHITECTURE.md's"
        missing += " features package map — update the diagram (memory drift)."
        return [
            specs_finding("MEM-DRIFT-1", Severity.WARNING, tpl.format(name), str(architecture_md))
            for names, tpl in ((declared - live, stale), (live - declared, missing))
            for name in sorted(names)
        ]
