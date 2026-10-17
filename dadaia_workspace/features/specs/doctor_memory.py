"""Memory validator: required atoms (SPEC-DOC-002), placeholders, fixed law sections,
LINT-1 atom lint, MEM-DRIFT-1 package map vs live tree, MEM-DRIFT-2 citations.
Leaf-only: imports the shared leaves + core, never a sibling validator."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection
from contextlib import suppress
from functools import partial
from pathlib import Path

from dadaia_workspace.core import platform
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import materialize_line, reinstall_fix
from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.features.specs import citations, doctor_adr, memory_canon, memory_lint
from dadaia_workspace.features.specs.canon import default_public_dir, is_canon_path
from dadaia_workspace.features.specs.doctor_types import Severity, finding_path, specs_finding

TOPLEVEL_MEMORY_FILES = memory_canon.MEMORY_TOPLEVEL_FILES
PRODUCT_INDEX_REL = "product/index.md"
_ADR_LIST = "adr-list"  # the ledger-rendered block of memory/ARCHITECTURE.md
_PLACEHOLDER_TOKENS = ("SLUG_PLACEHOLDER", "TITLE_PLACEHOLDER", "RELEASE_PLACEHOLDER")
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
# Matched by shape, never by the package count: the count changes only at closure.
_FEATURES_PKG_MAP_HEADING_RE = re.compile(
    r"^### `dadaia_workspace/features` — package map \(\d+ packages\)\s*$", re.MULTILINE
)
_MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_PKGS_NODE_RE = re.compile(r'pkgs\["([^"]*)"\]')


def _read_or_empty(path: Path) -> str:
    try:
        return platform.read_text(path)
    except OSError:
        return ""  # never flag, never delete on uncertainty


def _token_fields(path: Path) -> list[str]:
    """The frontmatter fields of *path* whose value is a template token; a mention in prose or
    a fixed section, and a top-level canon file, hold none."""
    if path.name in TOPLEVEL_MEMORY_FILES:
        return []
    fm, _body, _problem = memory_canon.parse_atom(_read_or_empty(path))
    return [key for key, value in (fm or {}).items() if value in _PLACEHOLDER_TOKENS]


def is_placeholder_atom(path: Path) -> bool:
    """True when *path* is an atom whose slug and title are both unfilled template tokens;
    a mention in prose or a fixed section, and a top-level canon file, never is."""
    return {"slug", "title"} <= set(_token_fields(path))


def _has_heading(path: Path) -> bool:
    """An ATX heading in the atom's body — its whole text when the frontmatter does not parse."""
    content = platform.read_text(path)
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
        """MEM-PLACEHOLDER-1: atoms with a template token field; report only, never fixed."""
        mem_dir = self.specs_dir / "memory"
        if not mem_dir.is_dir():
            return []
        return [
            specs_finding(
                "MEM-PLACEHOLDER-1",
                Severity.ERROR,
                f"{path.relative_to(self.specs_dir).as_posix()} keeps a template token in {fields}",
                str(path),
                fix=(
                    "Agent action: fill or delete the atom"
                    if is_placeholder_atom(path)
                    else f"Agent action: replace the token in {fields} of {path}"
                ),
            )
            for path in sorted(mem_dir.rglob("*.md"))
            if (fields := ", ".join(_token_fields(path)))
        ]

    def _fixed_blocks(
        self, public_dir: Path | None
    ) -> list[tuple[str, str, Callable[[], str], bool]]:
        """``(rel, id, render, optional)`` per fixed block: the library fragments, then the
        ARCHITECTURE.md ADR list rendered from the ledger, judged only where its markers are."""
        fragments_dir = public_dir if public_dir is not None else default_public_dir()
        blocks = [
            (rel, sid, partial(memory_canon.read_fixed_fragment, fragments_dir, sid), False)
            for rel, sid in memory_canon.FIXED_SECTIONS
        ]
        adr = partial(doctor_adr.adr_list_block, self.specs_dir)
        return [*blocks, ("memory/ARCHITECTURE.md", _ADR_LIST, adr, True)]

    def check_fixed_sections(self, public_dir: Path | None) -> list[SectionFinding]:
        """FIXED-1: a fixed block is missing; FIXED-2: its body is not the fragment or the
        ledger render, which is unfixable while an accepted `measured_by` resolves to nothing."""
        issues: list[SectionFinding] = []
        for rel, section_id, render, optional in self._fixed_blocks(public_dir):
            path = self.specs_dir / rel
            if not path.is_file():
                continue
            body = memory_canon.extract_fixed_section(platform.read_text(path), section_id)
            if body is None and optional:
                continue
            try:
                fragment = render()
            except FileNotFoundError as gone:
                issues.append(
                    specs_finding(
                        "FIXED-1",
                        Severity.ERROR,
                        f"{rel}: library fragment `{section_id}` is missing: {gone.filename}",
                        str(path),
                        fix=reinstall_fix(self.specs_dir),
                    )
                )
                continue
            except ValueError as refusal:
                message = f"{rel}: fixed law section `{section_id}` refused: {refusal}"
                issues.append(
                    specs_finding(
                        "FIXED-2",
                        Severity.ERROR,
                        message,
                        str(path),
                        fixable=False,
                        fix=str(refusal),
                    )
                )
                continue
            if body == fragment:
                continue
            source = "the ADR ledger" if optional else "the library fragment"
            state = "is missing" if body is None else f"differs from {source}"
            # The one writer refuses a link (CWE-59): a link is materialized first, never fixable.
            issues.append(
                specs_finding(
                    "FIXED-1" if body is None else "FIXED-2",
                    Severity.ERROR,
                    f"{rel}: fixed law section `{section_id}` {state}",
                    str(path),
                    fixable=not platform.is_link(path),
                    fix=materialize_line(path, path.resolve()) if platform.is_link(path) else "",
                )
            )
        return issues

    def fix_fixed_section(self, issue: SectionFinding, public_dir: Path | None) -> None:
        """Insert or refresh every renderable fixed block of the file named by *issue*; a
        block whose source refuses is left as it is."""
        named = finding_path(issue)
        if not named:
            return
        path = Path(named)
        rel = path.relative_to(self.specs_dir).as_posix()
        text = platform.read_text(path)
        for block_rel, section_id, render, optional in self._fixed_blocks(public_dir):
            if block_rel != rel or (
                optional and memory_canon.extract_fixed_section(text, section_id) is None
            ):
                continue
            with suppress(FileNotFoundError, ValueError):
                text = memory_canon.render_fixed_section(text, section_id, render())
        atomic_write(path, text)

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
            except (OSError, ValueError) as e:
                problem, fix = f"is not parseable: {e}", f"repair {p}"
            issues.append(
                specs_finding(
                    "SPEC-DOC-002",
                    Severity.ERROR,
                    f"memory/{rel} {problem}",
                    str(p),
                    fix=f"Agent action: {fix}",
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
                fix=f"Agent action: correct {result.path} ({err})",
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
        text = platform.read_text(architecture_md)
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
