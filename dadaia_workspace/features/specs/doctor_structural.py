"""Structural validator: TREE-3..8 spec-tree invariants (required memory atoms, required
dirs, AGENTS.md drift, canon placement) and their auto-fixes.
Leaf-only: imports the shared leaves, never a sibling validator."""

from __future__ import annotations

import hashlib
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import mkdir_line, shell_line
from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.template_history import was_shipped
from dadaia_workspace.core.workspace_layout import (
    SCOPED_LAW_AREAS,
    render_registry_tables,
    render_workspace_cli,
)
from dadaia_workspace.features.specs import memory_canon
from dadaia_workspace.features.specs.canon import (
    CANON_ROOT_MEMBERS,
    REQUIRED_ROOT_DIRS,
    is_canon_path,
    scaffold_entry,
)
from dadaia_workspace.features.specs.doctor_types import Severity, finding_path, specs_finding

_TREE3_MEMORY_FILES: tuple[str, ...] = memory_canon.MEMORY_REQUIRED_FILES


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StructuralValidator:
    def __init__(
        self,
        specs_dir: Path,
        scaffold_dir: Path | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self._scaffold_dir = scaffold_dir
        self._templates_dir = templates_dir

    def check_tree3_memory_md(self) -> list[SectionFinding]:
        """TREE-3: a required memory atom is missing; ``--fix`` seeds it from its template."""
        return [
            specs_finding(
                "TREE-3",
                Severity.ERROR,
                f"memory/{rel_path} is missing — required memory .md atom.",
                str(self.specs_dir / "memory" / rel_path),
                fixable=True,
            )
            for rel_path in _TREE3_MEMORY_FILES
            if not (self.specs_dir / "memory" / rel_path).exists()
        ]

    def fix_tree3(self, issue: SectionFinding) -> None:
        scaffold_entry(
            self.specs_dir, Path(str(finding_path(issue))).relative_to(self.specs_dir).as_posix()
        )

    def check_tree4_required_dirs(self) -> list[SectionFinding]:
        """TREE-4: a ``REQUIRED_ROOT_DIRS`` area is missing; fixable when its scaffold
        AGENTS.md is at hand."""
        issues: list[SectionFinding] = []
        for dirname in REQUIRED_ROOT_DIRS:
            target = self.specs_dir / dirname
            if target.exists():
                continue
            fixable = (
                self._scaffold_dir is not None
                and (self._scaffold_dir / dirname / "AGENTS.md").exists()
            )
            remedy = (
                "Auto-fix available (run doctor --fix)."
                if fixable
                else "No scaffold source available — create manually."
            )
            issues.append(
                specs_finding(
                    "TREE-4",
                    Severity.WARNING,
                    f"specs/{dirname}/ is missing — required spec tree directory. {remedy}",
                    str(target),
                    fixable=fixable,
                    fix="" if fixable else mkdir_line(target),
                )
            )
        return issues

    def fix_tree4(self, issue: SectionFinding) -> None:
        """Create the missing directory with its scaffold AGENTS.md (no .gitkeep)."""
        assert issue.code == "TREE-4"
        target = Path(str(finding_path(issue)))
        target.mkdir(parents=True, exist_ok=True)
        src = self._scaffold_dir / target.name / "AGENTS.md" if self._scaffold_dir else None
        agents_md = target / "AGENTS.md"
        if not agents_md.exists():
            atomic_write(agents_md, src.read_text(encoding="utf-8") if src and src.exists() else "")

    def _tree5_targets(self) -> list[tuple[Path, Path, str]]:
        """The CLOSED set of law files: (projection, canonical source, shipped asset name)."""
        assert self._templates_dir is not None
        targets = [
            (
                self.specs_dir / "AGENTS.md",
                self._templates_dir / "specs-AGENTS.md",
                "specs-AGENTS.md",
            )
        ]
        if self._scaffold_dir is not None:
            targets += [
                (
                    self.specs_dir / area / "AGENTS.md",
                    self._scaffold_dir / area / "AGENTS.md",
                    f"scaffold/{area}/AGENTS.md",
                )
                for area in SCOPED_LAW_AREAS
            ]
        return targets

    def check_tree5_agents_md(self) -> list[SectionFinding]:
        """TREE-5: a projected law file is missing (fixable: lossless) or differs from its
        canonical source (fixable only when its bytes are a version we shipped)."""
        agents_md = self.specs_dir / "AGENTS.md"
        if self._templates_dir is None:
            return [] if agents_md.exists() else [self._tree5_missing(agents_md, False)]
        issues: list[SectionFinding] = []
        for dst, canonical_path, asset_name in self._tree5_targets():
            if not canonical_path.exists():
                if dst == agents_md and not dst.exists():
                    issues.append(self._tree5_missing(dst, False))
                continue
            issues += self._tree5_check(dst, canonical_path, asset_name)
        return issues

    def _tree5_check(self, dst: Path, canonical_path: Path, asset: str) -> list[SectionFinding]:
        """ONE comparison rule for every TREE-5 target (root and scoped alike)."""
        assert self._templates_dir is not None
        if not dst.exists():
            return [self._tree5_missing(dst, True)]
        label = f"specs/{dst.relative_to(self.specs_dir).as_posix()}"
        canonical_text = render_registry_tables(canonical_path.read_text(encoding="utf-8"))
        current_text = dst.read_text(encoding="utf-8")
        canonical_hash = _sha(canonical_text)
        current_hash = _sha(render_workspace_cli(current_text))
        if canonical_hash == current_hash:
            return []
        # A symlinked projection is never repaired (the write would leave the tree): never fixable.
        if was_shipped(current_text, asset, self._templates_dir) and not dst.is_symlink():
            return [
                specs_finding(
                    "TREE-5",
                    Severity.WARNING,
                    f"{label} is a superseded version of the canonical template (current "
                    f"sha256:{current_hash[:12]}… is a previously shipped release; canonical "
                    f"sha256:{canonical_hash[:12]}…). It carries no operator customisation, "
                    "so it can be refreshed losslessly.",
                    str(dst),
                    fixable=True,
                )
            ]
        return [
            specs_finding(
                "TREE-5",
                Severity.WARNING,
                f"copy-drift: {label} matches neither its canonical source nor any version "
                f"this project shipped (current sha256:{current_hash[:12]}… vs canonical "
                f"sha256:{canonical_hash[:12]}…). Review the diff and merge any upstream "
                "changes manually — auto-overwrite is disabled to protect operator "
                "customisations.",
                str(dst),
                fix=shell_line("git", "diff", "--no-index", "--", str(canonical_path), str(dst)),
            )
        ]

    def _tree5_missing(self, dst: Path, fixable: bool) -> SectionFinding:
        label = f"specs/{dst.relative_to(self.specs_dir).as_posix()}"
        return specs_finding(
            "TREE-5",
            Severity.WARNING,
            f"{label} is missing — expected the shipped law contract.",
            str(dst),
            fixable=fixable,
        )

    def fix_tree5(self, issue: SectionFinding) -> None:
        """Write a missing law file, or refresh a superseded one. The issue path selects a
        member of the closed target set, never a destination (CWE-73); ``was_shipped`` is
        re-verified so operator content is never overwritten."""
        if self._templates_dir is None:
            return
        named = finding_path(issue)
        issue_path = Path(named).resolve() if named else None
        for dst, canonical_path, asset_name in self._tree5_targets():
            if issue_path is not None and dst.resolve() != issue_path:
                continue
            if not canonical_path.exists():
                continue
            if dst.exists() and not was_shipped(
                dst.read_text(encoding="utf-8"), asset_name, self._templates_dir
            ):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            law = render_registry_tables(canonical_path.read_text(encoding="utf-8"))
            atomic_write(dst, law, preserve_mode=True)
            return

    def check_tree8_canon_root(self) -> list[SectionFinding]:
        """TREE-8: a root entry outside ``CANON_ROOT_MEMBERS`` (flagged once, whole), or a
        file inside a canon area failing ``is_canon_path`` — the pre-push gate's predicate.
        Never fixable: it may be operator content."""
        if not self.specs_dir.is_dir():
            return []
        strays = [e for e in sorted(self.specs_dir.iterdir()) if e.name not in CANON_ROOT_MEMBERS]
        nested = [
            e
            for e in sorted(self.specs_dir.rglob("*"))
            if not e.is_dir()
            and e.relative_to(self.specs_dir).parts[0] in CANON_ROOT_MEMBERS
            and not is_canon_path(e.relative_to(self.specs_dir).as_posix())
        ]
        return [self._tree8_issue(entry) for entry in strays + nested]

    def _tree8_issue(self, entry: Path) -> SectionFinding:
        rel = entry.relative_to(self.specs_dir).as_posix()
        return specs_finding(
            "TREE-8",
            Severity.ERROR,
            f"specs/{rel} is not part of the v6 canon (specs/AGENTS.md) — either a stray root "
            "entry (not one of backlog/, bugs/, memory/, releases/, audits/, ADRs/, "
            "constitution.md, AGENTS.md) or a file nested inside a canon area whose shape does "
            "not match that area's canon (a dotfile, a loose per-entry file, a markdown ADR, "
            "an old reviews/ file, …) — a directory is kept by its AGENTS.md, never a "
            "placeholder. Never auto-fixed — it may be real content; move/rename it into the "
            "canon shape, or delete it, by hand (TREE-8).",
            str(entry),
            fix=f"Operator action: move {entry} into its canon shape, or out of specs/",
        )
