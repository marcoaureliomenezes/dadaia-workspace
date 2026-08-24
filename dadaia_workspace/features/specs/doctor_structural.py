"""Structural validator (v0.1.55 FR1): TREE-1..7 spec-tree invariants + TREE-4/TREE-5M.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the ``spec-context-tree-v2``
structural invariants (foundation/root-spec deprecation, required memory atoms, required dirs,
AGENTS.md drift, active-release artifacts, bug session_id) and the TREE-4 auto-fix. Leaf-only:
imports the shared leaves, never a sibling validator.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

from dadaia_workspace.features.specs.doctor_common import read_active_md
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue
from dadaia_workspace.features.specs.template_history import was_shipped

# TREE-3: memory .md files that must exist.  No Jinja templates — .md is canonical source.
_TREE3_MEMORY_FILES: tuple[str, ...] = (
    "architecture.md",
    "tech-stack.md",
    "quality-assurance.md",
    "product/index.md",
)

# TREE-4: directories that must exist.
_TREE4_REQUIRED_DIRS = ("audits", "backlog", "bugs", "releases")

# TREE-6: mandatory artifacts per phase bucket.
_TREE6_IMPL_ARTIFACTS = ("SPEC.md", "PLAN.md", "TASKS.md")

# Migration hint printed loudly for TREE-1 and TREE-2 (regardless of --fix).
_TREE_MIGRATION_HINT = (
    "[TREE MIGRATION REQUIRED] Run: dadaia migrate tree-v2\n"
    "  This command moves deprecated content to releases/legacy/ "
    "without destroying SDD-approved artifacts."
)


class StructuralValidator:
    """TREE-1..7 + TREE-5M structural invariants for the spec tree."""

    def __init__(
        self,
        specs_dir: Path,
        scaffold_dir: Path | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self._scaffold_dir = scaffold_dir
        self._templates_dir = templates_dir

    def check_tree1_foundation(self) -> list[SpecsDoctorIssue]:
        """TREE-1: specs/foundation/ must NOT exist (deprecated layout).

        Warn-only (fixable=False).  A loud migration hint pointing to
        ``dadaia migrate tree-v2`` is emitted regardless of the --fix flag.
        Auto-moving is intentionally blocked: foundation/ may hold SDD-approved
        content and reclassification requires operator consent.
        """
        foundation = self.specs_dir / "foundation"
        if not foundation.exists():
            return []
        return [
            SpecsDoctorIssue(
                code="TREE-1",
                severity=Severity.WARNING,
                description=(
                    "specs/foundation/ exists — this is the deprecated layout. "
                    f"{_TREE_MIGRATION_HINT}"
                ),
                path=str(foundation),
                fixable=False,
            )
        ]

    def check_tree2_root_spec_md(self) -> list[SpecsDoctorIssue]:
        """TREE-2: specs/SPEC.md at the tree root must NOT exist (deprecated).

        Warn-only (fixable=False).  A loud migration hint pointing to
        ``dadaia migrate tree-v2`` is emitted regardless of the --fix flag.
        Auto-moving is intentionally blocked: root SPEC.md may hold
        SDD-approved content that requires operator consent to reclassify.
        """
        root_spec = self.specs_dir / "SPEC.md"
        if not root_spec.exists():
            return []
        return [
            SpecsDoctorIssue(
                code="TREE-2",
                severity=Severity.WARNING,
                description=(
                    "specs/SPEC.md exists at the tree root — this is the deprecated layout. "
                    f"{_TREE_MIGRATION_HINT}"
                ),
                path=str(root_spec),
                fixable=False,
            )
        ]

    def check_tree3_memory_md(self) -> list[SpecsDoctorIssue]:
        """TREE-3: required memory .md atom files must exist.

        Checks: memory/architecture.md, memory/tech-stack.md,
        memory/quality-assurance.md, memory/product/index.md.

        .md is the canonical source (memory-markdown-source-v1 / D-4).
        No auto-fix: .md atoms are operator-authored, not generated from templates.
        """
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"
        for rel_path in _TREE3_MEMORY_FILES:
            target = mem_dir / rel_path
            if target.exists():
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="TREE-3",
                    severity=Severity.WARNING,
                    description=(
                        f"memory/{rel_path} is missing — required memory .md atom. "
                        "Create it using `dadaia memory product add` or the born-markdown scaffold."
                    ),
                    path=str(target),
                    fixable=False,
                )
            )
        return issues

    def check_tree4_required_dirs(self) -> list[SpecsDoctorIssue]:
        """TREE-4: backlog/, bugs/, and releases/ must exist under specs/.

        When a directory is absent the issue is emitted as fixable=True.
        The fix creates the dir, writes README.md (content copied from the
        canonical scaffold source), and touches .gitkeep — matching the exact
        output of ``scaffold()``.
        """
        issues: list[SpecsDoctorIssue] = []
        for dirname in _TREE4_REQUIRED_DIRS:
            target = self.specs_dir / dirname
            if target.exists():
                continue
            fixable = (
                self._scaffold_dir is not None
                and (self._scaffold_dir / dirname / "README.md").exists()
            )
            issues.append(
                SpecsDoctorIssue(
                    code="TREE-4",
                    severity=Severity.WARNING,
                    description=(
                        f"specs/{dirname}/ is missing — required spec tree directory. "
                        + (
                            "Auto-fix available (run doctor --fix)."
                            if fixable
                            else "No scaffold source available — create manually."
                        )
                    ),
                    path=str(target),
                    fixable=fixable,
                )
            )
        return issues

    def check_repo_dadaia1(self) -> list[SpecsDoctorIssue]:
        """REPO-DADAIA-1: a ``.dadaia/`` directory INSIDE the context repo (v0.1.73 FR6,
        bug ``stray-dadaia-tmp-inside-repo``).

        ``.dadaia/`` is workspace-level ONLY — an in-repo copy corrupts workspace-vs-repo
        boundary detection (root AGENTS.md repo-cleanliness law). Fixable (removed by
        ``--fix``) only when it carries NO ``states/`` — a stray tmp landing zone; a
        ``.dadaia/`` WITH ``states/`` demands operator judgment and is never auto-removed.
        """
        stray = self.specs_dir.parent / ".dadaia"
        if not stray.is_dir():
            return []
        has_states = (stray / "states").exists()
        return [
            SpecsDoctorIssue(
                code="REPO-DADAIA-1",
                severity=Severity.WARNING,
                description=(
                    ".dadaia/ exists INSIDE the repo — it is workspace-level only "
                    "(corrupts workspace-vs-repo boundary detection). "
                    + (
                        "Contains states/ — resolve manually (never auto-removed)."
                        if has_states
                        else "Stray tmp landing zone — `dadaia specs doctor --fix` removes it."
                    )
                ),
                path=str(stray),
                fixable=not has_states,
            )
        ]

    def fix_repo_dadaia1(self, issue: SpecsDoctorIssue) -> None:
        """Remove a stray in-repo ``.dadaia/`` (only ever called for fixable issues —
        the check marks a states/-bearing dir non-fixable)."""
        assert issue.code == "REPO-DADAIA-1"
        stray = Path(issue.path)  # type: ignore[arg-type]
        if (stray / "states").exists():  # belt-and-suspenders: never remove state
            return
        shutil.rmtree(stray, ignore_errors=True)

    def fix_tree4(self, issue: SpecsDoctorIssue) -> None:
        """Create the missing directory with README.md and .gitkeep."""
        assert issue.code == "TREE-4"
        target = Path(issue.path)  # type: ignore[arg-type]
        dirname = target.name
        target.mkdir(parents=True, exist_ok=True)
        # README.md — copy from scaffold source
        readme_content = ""
        if self._scaffold_dir is not None:
            src_readme = self._scaffold_dir / dirname / "README.md"
            if src_readme.exists():
                readme_content = src_readme.read_text(encoding="utf-8")
        readme = target / "README.md"
        if not readme.exists():
            readme.write_text(readme_content, encoding="utf-8")
        # .gitkeep
        gitkeep = target / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    def check_tree5_agents_md(self) -> list[SpecsDoctorIssue]:
        """TREE-5: specs/AGENTS.md must exist and its content must match the canonical template.

        Absent file → WARNING (fixable=False; cannot auto-create because the file
        is intended for operator customisation).
        Hash drift → WARNING (fixable=False; silent overwrite would destroy
        operator customisation — user must merge manually).

        When no templates_dir is available, hash comparison is skipped and
        only presence is checked.
        """
        agents_md = self.specs_dir / "AGENTS.md"
        if not agents_md.exists():
            return [
                SpecsDoctorIssue(
                    code="TREE-5",
                    severity=Severity.WARNING,
                    description=(
                        "specs/AGENTS.md is missing — expected SDD workflow contract. "
                        "Create it from the canonical template "
                        "(dadaia_workspace/public/templates/specs-AGENTS.md) "
                        "or run `dadaia specs init` to scaffold it."
                    ),
                    path=str(agents_md),
                    fixable=False,
                )
            ]

        # Hash comparison against canonical template
        if self._templates_dir is None:
            return []
        canonical_path = self._templates_dir / "specs-AGENTS.md"
        if not canonical_path.exists():
            return []
        canonical_text = canonical_path.read_text(encoding="utf-8")
        current_text = agents_md.read_text(encoding="utf-8")
        canonical_hash = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
        current_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
        if canonical_hash == current_hash:
            return []
        # A file whose bytes we published earlier carries no operator customisation, so
        # refreshing it is lossless (bug
        # upgrade-never-refreshes-uncustomised-scoped-law-projection). Anything else may
        # hold operator content and stays warn-only.
        # A symlinked projection is never repaired (the write would land outside the
        # tree), so it must not be advertised as fixable either — reporting a fix that
        # never happens is its own defect (CWE-393).
        if was_shipped(current_text, "specs-AGENTS.md", self._templates_dir) and not (
            agents_md.is_symlink()
        ):
            return [
                SpecsDoctorIssue(
                    code="TREE-5",
                    severity=Severity.WARNING,
                    description=(
                        f"specs/AGENTS.md is a superseded version of the canonical "
                        f"template (current sha256:{current_hash[:12]}… is a previously "
                        f"shipped release; canonical sha256:{canonical_hash[:12]}…). "
                        "It carries no operator customisation, so it can be refreshed "
                        "losslessly — run `dadaia specs doctor --fix`."
                    ),
                    path=str(agents_md),
                    fixable=True,
                )
            ]
        return [
            SpecsDoctorIssue(
                code="TREE-5",
                severity=Severity.WARNING,
                description=(
                    f"specs/AGENTS.md has drifted from canonical template "
                    f"(current sha256:{current_hash[:12]}… vs "
                    f"canonical sha256:{canonical_hash[:12]}…). "
                    "Review the diff and merge any upstream changes manually — "
                    "auto-overwrite is disabled to protect operator customisations. "
                    "Canonical template: dadaia_workspace/public/templates/specs-AGENTS.md"
                ),
                path=str(agents_md),
                fixable=False,
            )
        ]

    def fix_tree5(self, issue: SpecsDoctorIssue) -> None:
        """Refresh a superseded projection from the canonical template.

        Only ever reached for issues this validator marked ``fixable`` — i.e. the on-disk
        bytes are a version we shipped ourselves. Re-verified here so a future caller
        cannot turn the repair into an overwrite of operator content.
        """
        if self._templates_dir is None:
            return
        # The repair target is derived, never taken from the issue: an externally supplied
        # path would let a caller aim the write anywhere (CWE-73). A link is refused
        # outright so the canonical text cannot be written through it to a file outside
        # the tree (CWE-59).
        agents_md = self.specs_dir / "AGENTS.md"
        if agents_md.is_symlink():
            return
        canonical_path = self._templates_dir / "specs-AGENTS.md"
        if not canonical_path.exists() or not agents_md.exists():
            return
        current_text = agents_md.read_text(encoding="utf-8")
        if not was_shipped(current_text, "specs-AGENTS.md", self._templates_dir):
            return
        _write_text_atomic(agents_md, canonical_path.read_text(encoding="utf-8"))

    def check_memory_agents_md(self) -> list[SpecsDoctorIssue]:
        """Check: specs/memory/AGENTS.md must exist (WARNING only).

        The specs-tree copy is NOT a projection target: `dadaia public install`
        only scaffolds it when the file is missing and never updates an existing
        copy (bug specs-doctor-tree5m-remediation-wrong). The real repair is to
        create/edit specs/memory/AGENTS.md directly, restoring content from the
        canonical source dadaia_workspace/public/data/memory-AGENTS.md and
        keeping the data/ + scaffold/ source copies in sync. Absence is expected
        on fresh scaffolds and early in the lifecycle, so it is flagged as WARN
        (never ERROR) and does NOT cause doctor to exit non-zero.
        """
        memory_agents_md = self.specs_dir / "memory" / "AGENTS.md"
        if memory_agents_md.exists():
            return []
        return [
            SpecsDoctorIssue(
                code="TREE-5M",
                severity=Severity.WARNING,
                description=(
                    "specs/memory/AGENTS.md is missing — expected memory ownership contract. "
                    "Restore it by copying the canonical source "
                    "dadaia_workspace/public/data/memory-AGENTS.md into specs/memory/AGENTS.md "
                    "(edit the specs-tree copy directly and keep both source copies — "
                    "public/data/ and public/scaffold/memory/ — in sync). "
                    "Note: `dadaia public install` does NOT project this file; it only "
                    "scaffolds it when missing and never updates an existing copy."
                ),
                path=str(memory_agents_md),
                fixable=False,
            )
        ]

    def check_tree6_release_artifacts(self) -> list[SpecsDoctorIssue]:
        """TREE-6: for the ACTIVE release, mandatory SDD artifacts must exist for its phase.

        Rule: if the active release exists and its phase is IMPLEMENTATION or CLOSURE,
        then SPEC.md, PLAN.md, and TASKS.md must all be present in the release directory.
        Any missing file is an ERROR (no auto-fix — creating an empty PLAN.md would
        constitute an unapproved artifact; human review is required).

        Inactive / non-active releases are not checked here (SPEC-DOC-004 already
        checks the active release's artifact statuses; we only add the TREE-6
        structural check for the IMPLEMENTATION/CLOSURE gates).

        Note: this invariant applies to the ACTIVE release only.  The broader
        per-release artifact check (SPEC-DOC-004) covers Status: field validation.
        """
        issues: list[SpecsDoctorIssue] = []
        active_path = self.specs_dir / "releases" / "ACTIVE.md"
        release, segment, phase, err = read_active_md(active_path)
        if err or not release or release == "none":
            return issues
        if phase not in ("IMPLEMENTATION", "CLOSURE"):
            return issues
        rdir = self.specs_dir / "releases" / release
        if segment:  # schema v2: artifacts live in the active segment dir
            rdir = rdir / segment
        if not rdir.exists():
            # v0.4.3 T-043-22 [Arm-B rider] bug specs-doctor-segment-router-silent-skip:
            # a live segment: pointer at a missing segment directory used to `return
            # issues` here silently, UNCONDITIONALLY. SPEC-DOC-009 (check_active_md,
            # doctor_release.py) only validates the RELEASE directory
            # (releases/<release>/) — it NEVER checks the segment SUBdirectory
            # (releases/<release>/<segment>/), so a segmented ACTIVE.md pointing at a
            # missing segment dir was invisible to every downstream check (this one AND
            # SPEC-DOC-004 in doctor_release.py). Scoped to `segment` truthy only: the
            # FLAT-release case (no segment:) is genuinely, correctly covered already
            # by check 9's own release-dir check (rdir IS the release dir there) —
            # firing here too would duplicate that finding.
            if segment:
                issues.append(
                    SpecsDoctorIssue(
                        code="TREE-6",
                        severity=Severity.ERROR,
                        description=(
                            f"Active release '{release}' (phase={phase}) segment="
                            f"'{segment}' but no directory at {rdir} — the segment "
                            "directory itself is missing; SPEC-DOC-009 validates "
                            "only the release directory, never the segment "
                            "subdirectory."
                        ),
                        path=str(rdir),
                        fixable=False,
                    )
                )
            return issues
        for fname in _TREE6_IMPL_ARTIFACTS:
            fpath = rdir / fname
            if not fpath.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="TREE-6",
                        severity=Severity.ERROR,
                        description=(
                            f"Active release '{release}' (phase={phase}) is missing "
                            f"mandatory SDD artifact: {fname}. "
                            "Create the artifact via the SDD lifecycle (product-engineer) — "
                            "do NOT create an empty placeholder."
                        ),
                        path=str(fpath),
                        fixable=False,
                    )
                )
        return issues

    def check_tree7_bug_session_id(self) -> list[SpecsDoctorIssue]:
        """TREE-7: every bugs/<slug>.md must have a session_id frontmatter field.

        Expected frontmatter format (YAML-like leading lines):
            session_id: <value>   OR   session_id: null

        Missing field → ERROR (no auto-fix — injecting a session_id would
        falsify authorship; human review is required).

        If bugs/ does not exist, this check is a no-op.
        """
        issues: list[SpecsDoctorIssue] = []
        bugs_dir = self.specs_dir / "bugs"
        if not bugs_dir.exists():
            return issues
        for bug_file in sorted(bugs_dir.glob("*.md")):
            # Skip README.md and other non-bug files
            if bug_file.name in ("README.md",):
                continue
            text = bug_file.read_text(encoding="utf-8")
            has_session_id = bool(re.search(r"^session_id\s*:", text, re.MULTILINE))
            if not has_session_id:
                issues.append(
                    SpecsDoctorIssue(
                        code="TREE-7",
                        severity=Severity.ERROR,
                        description=(
                            f"bugs/{bug_file.name} is missing the required 'session_id:' "
                            "frontmatter field. "
                            "Add 'session_id: null' if the session is unknown. "
                            "Do NOT inject a fabricated session ID."
                        ),
                        path=str(bug_file),
                        fixable=False,
                    )
                )
        return issues


def _write_text_atomic(path: Path, text: str) -> None:
    """Write *text* to *path* by atomic replacement, never THROUGH the existing file.

    Feature-local by architecture: features are mutually independent, may not import
    infrastructure, and core/ file I/O is a closed ratchet.

    A hard link is not a symlink and a checked-then-opened path is a TOCTOU window
    (CWE-59/CWE-367), so refusing links alone cannot keep a write inside the tree.
    Rendering to a temp file in the same directory and ``os.replace``-ing it rebinds the
    name instead of writing through whatever it points at, and the swap is atomic.

    ``newline=""`` disables universal-newline translation, so the bytes on disk are exactly
    ``text.encode("utf-8")`` — without it Windows text mode rewrites LF to CRLF and the
    byte-preserving guarantee dies on that platform (the same reason
    ``public_assets_common`` passes it, FR-RC2-2).

    ``mkstemp`` creates the temp file 0600 and ``os.replace`` carries that mode onto the
    target, which would silently narrow a 0644 atom in a shared or CI-checked-out tree
    (CWE-732 in the fail-safe direction, invisible to git). The original mode is copied
    back before the swap.
    """
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        with contextlib.suppress(OSError):
            shutil.copymode(path, tmp_path)  # keep the target's mode, not mkstemp's 0600
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
