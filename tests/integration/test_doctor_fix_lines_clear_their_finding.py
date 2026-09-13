"""Intent: CONTRACT — 0.4.7 FR2 (T-047-14): a doctor fix line CLEARS its own finding.

``tests/contract/test_every_block_carries_a_fix.py`` proves the fix line is one
executable command that the gate lets through. That grammar says nothing about what the
command DOES: ``rm -rf specs/audits/<audit>`` is one executable command, passes the
gate, and destroys the record the finding exists to protect. This module closes the gap
by EXECUTING each fix line against a tree where the finding was planted, and re-running
the very rule that emitted it.

Two verdicts, one per rule class:

* a rule that carries ``fix_help`` — the command runs (``bash -c``, cwd = the fixture)
  and the rule must then emit nothing;
* a rule that carries none — its remedy is judgment (split a PLAN, migrate a deprecated
  layout), so every finding it emits must be WARNING: a warning never exits 1, so the
  operator is informed, never stalled.

The registry below is the census: a rule with no plant is skipped with the reason it
cannot be exercised here, and the census test pins that every rule is accounted for.

size: MEDIUM.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.doctor_rules import Rule
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue
from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES
from tests.fixtures.harness_env import session_home

from ..unit.features.specs.test_doctor import _make_clean_specs_tree

_RELEASE = "1.2.3"
_VENV_DADAIA = ".dadaia/.venv/bin/dadaia"
#: The fix line names the venv binary by its workspace-relative path; the fixture tree is
#: not a workspace, so it is resolved to the venv running this suite — the SAME binary.
_THIS_VENV_DADAIA = str(Path(sys.executable).parent / "dadaia")


@dataclass(frozen=True)
class Plant:
    """How to make one rule fire, and how to fill its fix line's ``<placeholders>``."""

    plant: Callable[[Path], None]
    substitutions: dict[str, str] = field(default_factory=dict)


def _plant_missing_memory_document(root: Path) -> None:
    (root / "specs" / "memory" / "QUALITY.md").unlink()


def _plant_status_line_gone(root: Path) -> None:
    spec = root / "specs" / "releases" / _RELEASE / "SPEC.md"
    spec.write_text("# Spec\n\n> **Created:** 2026-04-01\n\nContent.\n", encoding="utf-8")


def _plant_oversized_plan(root: Path) -> None:
    plan = root / "specs" / "releases" / _RELEASE / "PLAN.md"
    body = "\n".join(f"- line {i}" for i in range(400))
    plan.write_text(f"# Plan\n\n> **Status:** Aprovado\n\n{body}\n", encoding="utf-8")


def _plant_changelog_heading(root: Path) -> None:
    atom = root / "specs" / "memory" / "product" / "testarea" / "feature-a.md"
    atom.write_text(
        atom.read_text(encoding="utf-8") + "\n## Changelog\n\n- 1.0.0 born\n", encoding="utf-8"
    )


def _plant_tests_agents_placeholder(root: Path) -> None:
    tests_dir = root / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "AGENTS.md").write_text(
        "# Test Rules\n\nThe LARGE cap is `<LARGE_CAP>`.\n", encoding="utf-8"
    )


def _plant_root_spec_md(root: Path) -> None:
    (root / "specs" / "SPEC.md").write_text("# Deprecated root spec\n", encoding="utf-8")


def _plant_dispositioned_audit(root: Path) -> None:
    audit = root / "specs" / "audits" / "20260101-lifecycle"
    audit.mkdir(parents=True)
    (root / "specs" / "audits" / "_archive").mkdir(parents=True, exist_ok=True)
    (root / "specs" / "audits" / "_archive" / "audits_histo.jsonl").touch()
    (audit / "AUDIT.md").write_text("# Audit\n", encoding="utf-8")
    (audit / "FINDINGS.jsonl").write_text(
        json.dumps(
            {
                "id": "20260101-lifecycle-F001",
                "pillar": "specs",
                "severity": "LOW",
                "refs": ["specs/constitution.md"],
                "claim": "a claim",
                "evidence": "an evidence line",
                "disposition": "resolved",
                "release": _RELEASE,
                "reason": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _plant_archived_release_residue(root: Path) -> None:
    residue = root / "specs" / "_archive" / "releases" / "0.0.9"
    residue.mkdir(parents=True)
    (residue / "GRILL.md").write_text("# Grill notes\n", encoding="utf-8")


#: code -> how to make it fire. The eight remedies the 0.4.7 candidate-2 review named,
#: plus the memory-document pair they share a shape with.
PLANTS: dict[str, Plant] = {
    "SPEC-DOC-002": Plant(
        _plant_missing_memory_document, {"<document>": "QUALITY", "<title>": "Quality"}
    ),
    "SPEC-DOC-004": Plant(
        _plant_status_line_gone,
        {
            "<id>": _RELEASE,
            "<document>": "SPEC",
            "<Aprovado|Em revisão|Draft>": "Aprovado",
        },
    ),
    "SPEC-DOC-005": Plant(_plant_oversized_plan),
    "SPEC-DOC-010": Plant(_plant_changelog_heading),
    "AGENTS-PLACEHOLDER-1": Plant(_plant_tests_agents_placeholder),
    "TREE-2": Plant(_plant_root_spec_md),
    "TREE-3": Plant(
        _plant_missing_memory_document, {"<document>": "QUALITY", "<title>": "Quality"}
    ),
    "SPEC-DOC-038": Plant(
        _plant_dispositioned_audit,
        {
            "<audit>": "20260101-lifecycle",
            # The fixture tree is not a bound workspace, so the verb is told which
            # specs/ it acts on — the one argument a real invocation resolves itself.
            "<sha>": "abc1234 --specs-dir specs",
        },
    ),
    "SPEC-DOC-039": Plant(
        _plant_archived_release_residue,
        {"<release-id>": "0.0.9", "<why abandoned>": "abandoned: superseded by 0.1.0"},
    ),
}

_UNEXERCISED: dict[str, str] = {
    "SPEC-DOC-001": "the fix appends a constitution section header; the check reads the "
    "public fixed-section fragments, which a tmp tree does not carry",
    "MEM-PLACEHOLDER-1": "auto-fixed rule: `doctor --fix` runs its own fixer, covered by "
    "tests/unit/features/specs/test_doctor.py placeholder-atom cases",
    "SPEC-DOC-003/SPEC-DOC-009": "the fix is `git rm specs/ACTIVE.md` — a deprecated "
    "layout no longer scaffolded anywhere",
    "SPEC-DOC-007": "the orphan path is operator content; removing it is the operator's "
    "own call, not a fixture assertion",
    "TREE-1": "the fix is `specs upgrade`, a full scaffold run exercised by the specs "
    "upgrade integration suite",
    "RELEASE-TREE-HANDEDIT": "carries no fix line by design (0.4.7 FR6: re-running the "
    "verb and accepting the edit are both correct); the rule is exercised end to end by "
    "tests/integration/cli/test_doctor_hand_edit.py",
    "TREE-4": "auto-fixed rule (`fix_tree4`), covered by the structural doctor unit tests",
    "TREE-5": "auto-fixed rule (`fix_tree5`), covered by the structural doctor unit tests",
    "TREE-7": "the fix redacts a session id inside BUGS.jsonl; the value is per-record "
    "and redaction is covered by the redaction suite",
    "TREE-8": "auto-fixed rule (`fix_tree8`), covered by the structural doctor unit tests",
    "CAT-1": "the fix is `memory catalog generate`, exercised by the catalog CLI suite",
    "LINT-1": "the fix inserts one missing frontmatter field; which field is per-atom",
    "MEM-DRIFT-1": "the fix rewrites one ARCHITECTURE.md package line against the real "
    "package tree, which a tmp specs tree has none of",
    "MEM-DRIFT-2": "the fix rewrites one dead citation inside one memory atom against "
    "the live command tree and repo; both are the real repo's, which a tmp specs tree "
    "has none of (the rule itself: tests/unit/features/specs/test_doctor_memory_"
    "citations.py)",
    "FIXED-1/FIXED-2": "auto-fixed rule (`fix_fixed_section`), covered by "
    "tests/contract/test_fixed_sections_canon.py",
    "SPECS-VERSION": "the fix is `specs upgrade`, exercised by the specs upgrade suite",
    "SPEC-DOC-024": "the fix rewrites a phase marker to the _RELEASE.json phase; the "
    "value is per-document",
    "SPEC-DOC-026": "the fix renames one of two duplicate release dirs; which one is the "
    "operator's call",
    "SPEC-DOC-027": "the fix renames a non-canon release dir to its M.m.p form; the "
    "target name is judgment",
    "SPEC-DOC-028": "the fix deletes a dangling constitution reference line; the tmp "
    "constitution carries none of the public fragments",
    "SPEC-DOC-030": "the fix renames an audit dir to <YYYYMMDD>-<slug>; the date is judgment",
    "SPEC-DOC-033": "the fix is `bugs update`, exercised by the bugs CLI suite",
    "SPEC-DOC-034": "auto-fixed rule (`fix_archive_dir`), covered by the closure-audit "
    "doctor unit tests",
    "SPEC-DOC-035": "the fix is `backlog archive`, exercised by the backlog CLI suite",
    "SPEC-DOC-036": "the fix dispositions a finding inside an ARCHIVED audit dir; "
    "`dadaia audit disposition` acts on live audits only, and `dadaia audit close` is "
    "what stops an audit reaching _archive/ with an open finding at all",
    "SPEC-DOC-037": "the fix deletes a runtime-enum line from the constitution; the line "
    "is operator content",
    "SPEC-DOC-041": "the fix is `bugs archive`, exercised by the bugs CLI suite",
    "SPEC-DOC-044": "auto-fixed rule (`fix_stale_verdict`), covered by the verdict suite",
    "SPEC-DOC-045": "the fix rewrites pyproject.toml's version; a tmp specs tree has no pyproject",
    "SPEC-DOC-047": "the fix deletes a memory task line from TASKS.md; the line is "
    "operator content",
    "RELEASE-TREE-SCHEMA/RELEASE-TREE-PARSE/RELEASE-TREE-TS-ORDER/RELEASE-TREE-PHASE/"
    "RELEASE-TREE-ARCHIVED/RELEASE-TREE-TRIO/RELEASE-TREE-STATE-MISSING": "the fix "
    "rewrites one _RELEASE.json value; which value depends on which of the seven codes "
    "fired",
    "SPEC-DOC-046": "auto-fixed rule (`fix_release_state_filename`), covered by the "
    "release doctor unit tests",
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env={"HOME": str(root), "PATH": "/usr/bin:/bin", "GIT_CONFIG_GLOBAL": "/dev/null"},
    )


def _repo(tmp_path: Path) -> Path:
    """A git-backed fixture tree: a fix line may legitimately be a `git rm`/`git mv`."""
    _make_clean_specs_tree(tmp_path, _RELEASE)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _git(tmp_path, "config", "user.name", "fixture")
    return tmp_path


def _run_rule(root: Path, rule: Rule[SpecsDoctor, SpecsDoctorIssue]) -> list[SpecsDoctorIssue]:
    return rule.run(SpecsDoctor(root / "specs"))


def _resolve(fix: str, plant: Plant) -> str:
    command = fix
    for token, value in plant.substitutions.items():
        command = command.replace(token, value)
    assert "<" not in command, f"unsubstituted placeholder left in:\n{command}"
    return command


_PLANTED_RULES: list[tuple[str, Rule[SpecsDoctor, SpecsDoctorIssue]]] = [
    (code, rule) for rule in SPECS_RULES for code in rule.codes if code in PLANTS
]


@pytest.mark.parametrize(("code", "rule"), _PLANTED_RULES, ids=[code for code, _ in _PLANTED_RULES])
def test_the_fix_line_clears_the_finding_it_was_stamped_on(
    code: str, rule: Rule[SpecsDoctor, SpecsDoctorIssue], tmp_path: Path
) -> None:
    """Plant the finding, run the rule's OWN fix line, and the rule falls silent."""
    root = _repo(tmp_path)
    plant = PLANTS[code]
    plant.plant(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture")

    before = _run_rule(root, rule)
    assert before, f"{code}: the fixture did not make the rule fire"

    if rule.fix_help is None:
        assert all(issue.severity is Severity.WARNING for issue in before), (
            f"{code} carries no fix line, so it must never exit 1 — "
            f"got {[i.severity for i in before]}"
        )
        return

    command = _resolve(rule.fix_help, plant).replace(_VENV_DADAIA, _THIS_VENV_DADAIA)
    done = subprocess.run(
        ["bash", "-c", command],
        cwd=root,
        env={**os.environ, "HOME": str(session_home())},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, f"{code}: the fix line failed:\n{command}\n{done.stderr}"
    after = _run_rule(root, rule)
    assert not after, (
        f"{code}: the fix line ran but the finding survives — "
        f"{[i.description for i in after]}\n{command}"
    )


def test_spec_doc_039_relocates_the_residue_instead_of_destroying_it(tmp_path: Path) -> None:
    """The remedy the finding NAMES is the remedy its fix line RUNS.

    ``doctor_release.check_partial_archived_release_dirs`` tells the operator to
    relocate the residue to ``specs/_archive/wip-abandoned/<name>/`` with a README
    breadcrumb. A fix line that removes the directory answers a different question.
    """
    root = _repo(tmp_path)
    plant = PLANTS["SPEC-DOC-039"]
    plant.plant(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture")
    rule = next(r for r in SPECS_RULES if "SPEC-DOC-039" in r.codes)
    assert rule.fix_help is not None

    command = _resolve(rule.fix_help, plant).replace(_VENV_DADAIA, _THIS_VENV_DADAIA)
    done = subprocess.run(
        ["bash", "-c", command],
        cwd=root,
        env={**os.environ, "HOME": str(session_home())},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, f"{command}\n{done.stderr}"

    relocated = root / "specs" / "_archive" / "wip-abandoned" / "0.0.9"
    assert (relocated / "GRILL.md").read_text(encoding="utf-8") == "# Grill notes\n"
    assert "abandoned" in (relocated / "README.md").read_text(encoding="utf-8")
    assert not (root / "specs" / "_archive" / "releases" / "0.0.9").exists()


def test_every_specs_rule_is_either_exercised_or_listed_with_a_reason() -> None:
    """The census: no rule falls out of this module silently."""
    accounted: set[str] = set()
    missing: list[str] = []
    for rule in SPECS_RULES:
        key = "/".join(rule.codes)
        if any(code in PLANTS for code in rule.codes):
            accounted.add(key)
            continue
        if key in _UNEXERCISED:
            accounted.add(key)
            continue
        missing.append(key)
    assert not missing, f"doctor rules with neither a plant nor a skip reason: {missing}"
    stale = set(_UNEXERCISED) - accounted
    assert not stale, f"skip reasons for rules that no longer exist: {stale}"


def _iter_fix_helps() -> list[tuple[str, Any]]:
    return [("/".join(r.codes), r.fix_help) for r in SPECS_RULES]


#: a bare ``rm`` invocation with a recursive flag, at the head of the line or of any
#: segment of a chain. ``git rm -r`` is deliberately NOT matched: it stages a removal
#: that git history still holds, which is why SPEC-DOC-038 may end with one.
_BARE_RECURSIVE_RM = re.compile(r"(?:^|&&|;|\|)\s*rm\s+-[a-zA-Z]*r")


@pytest.mark.parametrize(("codes", "fix"), _iter_fix_helps(), ids=[c for c, _ in _iter_fix_helps()])
def test_no_fix_line_deletes_a_record_without_recording_it(codes: str, fix: str | None) -> None:
    """A bare recursive ``rm`` is never a fix: what the finding protects goes with it.

    The class, not the one line that was found: any ``rm -r``/``rm -rf``/``rm -fr``
    anywhere in the chain, not only as its opening token.
    """
    if fix is None:
        return
    assert not _BARE_RECURSIVE_RM.search(fix), (
        f"{codes}: a bare recursive `rm` destroys the subject instead of "
        "dispositioning it — chain the record step ahead of the removal, "
        "relocate instead of deleting, or drop the fix line"
    )


def test_a_judgment_only_rule_never_makes_the_run_exit_1(tmp_path: Path) -> None:
    """The exit-code half of the contract: the four judgment-only rules fire at once and
    contribute NO error-class finding, so dropping their fix lines stalls nobody.

    The one error left standing is LINT-1 on the same atom the atomicity rule warned
    about — the forbidden-heading invariant keeps its exit-1 home; only the duplicate
    finding that had no honest command became a warning."""
    from dadaia_workspace.cli.commands.doctor import _specs_section

    root = _repo(tmp_path)
    for code in ("SPEC-DOC-005", "SPEC-DOC-010", "TREE-2", "AGENTS-PLACEHOLDER-1"):
        PLANTS[code].plant(root)

    report = _specs_section(SpecsDoctor(root / "specs"))
    fired = {f.code for f in report.printable}
    assert {"SPEC-DOC-005", "SPEC-DOC-008", "TREE-2", "AGENTS-PLACEHOLDER-1"} <= fired, fired
    errors = {f.code for f in report.findings if f.error}
    assert errors == {"LINT-1"}, errors
