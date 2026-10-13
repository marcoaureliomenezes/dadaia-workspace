"""A doctor fix line CLEARS its own finding.

``tests/core/test_cli_line__every_block_carries_a_fix.py`` proves the fix line is one
executable command that the gate lets through. That grammar says nothing about what the
command DOES: ``rm -rf specs/audits/<audit>`` is one executable command, passes the
gate, and destroys the record the finding exists to protect. This module closes the gap
by EXECUTING each fix line against a tree where the finding was planted, and re-running
the very rule that emitted it.

Every planted finding's description also passes the dead-verb scanner
(``features.specs.citations``) — bug doctor-messages-cite-dead-verbs.

Two verdicts, one per rule class:

* a rule that carries ``fix_help`` — the command runs (``bash -c``, cwd = the fixture)
  and the rule must then emit nothing;
* a rule that carries none — its remedy is judgment, so every finding it emits must be
  WARNING: a warning never exits 1, so the operator is informed, never stalled.

The registry below is the census: a rule with no plant is skipped with the reason it
cannot be exercised here, and the census test pins that every rule is accounted for.

size: MEDIUM.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands.doctor import (
    _build_specs_doctor,
    _ledgers_section,
    _specs_section,
)
from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.doctor_rules import Rule, SectionFinding, rule_fix, run_section
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.core.workspace_layout import LEVEL1_SEEDS, occupied, provisioned_zones
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.specs.citations import dead_verb_citations
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.features.backlog.test_doctor import _SOURCE, _active_entry
from tests.features.specs.test_doctor import _make_clean_specs_tree
from tests.fixtures.harness_env import run_bash, suite_env
from tests.fixtures.stores import context_store
from tests.helpers import worktree_ws

_RELEASE = "1.2.3"


@dataclass(frozen=True)
class Plant:
    """How to make one rule fire, and how to fill its fix line's ``<placeholders>``."""

    plant: Callable[[Path], None]
    substitutions: dict[str, str] = field(default_factory=dict)


def _plant_missing_memory_document(root: Path) -> None:
    (root / "specs" / "memory" / "QUALITY.md").unlink()


def _plant_headingless_memory_document(root: Path) -> None:
    quality = root / "specs" / "memory" / "QUALITY.md"
    quality.write_text("---\nslug: quality\n---\n\nno heading here\n", encoding="utf-8")


def _plant_nothing(root: Path) -> None:
    """The fixture already carries it (no audits/, bugs/ dirs; no backlog/_archive/)."""


def _plant_placeholder_atom(root: Path) -> None:
    atom = root / "specs" / "memory" / "product" / "testarea" / "raw.md"
    atom.write_text("---\nslug: SLUG_PLACEHOLDER\n---\n# TITLE_PLACEHOLDER\n", encoding="utf-8")


def _plant_missing_root_agents(root: Path) -> None:
    (root / "specs" / "AGENTS.md").unlink(missing_ok=True)


def _plant_fixed_block_gone(root: Path) -> None:
    """A memory document whose fixed law block was deleted by hand."""
    quality = root / "specs" / "memory" / "QUALITY.md"
    text = quality.read_text(encoding="utf-8")
    head, _, rest = text.partition("<!-- dadaia:fixed slop-tests -->")
    quality.write_text(head + rest.partition("<!-- /dadaia:fixed slop-tests -->\n")[2])


def _plant_fixed_block_drifted(root: Path) -> None:
    """A memory document whose fixed law block was edited by hand."""
    quality = root / "specs" / "memory" / "QUALITY.md"
    text = quality.read_text(encoding="utf-8")
    quality.write_text(
        text.replace(
            "<!-- dadaia:fixed slop-tests -->\n", "<!-- dadaia:fixed slop-tests -->\n- edited\n"
        )
    )


def _plant_gitflow_gone(root: Path) -> None:
    """A current dadaia tree whose constitution frontmatter has no gitflow block."""
    constitution = root / "specs" / "constitution.md"
    constitution.write_text(
        f"---\nspecs_pattern_version: {CANONICAL_SPECS_VERSION}\n---\n"
        + constitution.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def _plant_status_line_gone(root: Path) -> None:
    """sa-status-line-has-two-parsers#B26-3 a 173-line TASKS.md, lowercase token on line 3;
    sa-status-line-has-two-parsers#B26-4 a SPEC.md with no status line — both fire."""
    release = root / "specs" / "releases" / _RELEASE / "rc-1"
    (release / "SPEC.md").write_text("# Spec\n\nContent.\n", encoding="utf-8")
    (release / "TASKS.md").write_text("# Tasks\n\n**Status:** approved\n" + "- t\n" * 170)


def _plant_changelog_heading(root: Path) -> None:
    atom = root / "specs" / "memory" / "product" / "testarea" / "feature-a.md"
    atom.write_text(
        atom.read_text(encoding="utf-8") + "\n## Changelog\n\n- 1.0.0 born\n", encoding="utf-8"
    )


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


def _plant_legacy_state_name(root: Path) -> None:
    """ADR 0007: the legacy state-file name, renamed by `doctor --fix`."""
    state = root / "specs" / "releases" / _RELEASE / "_RELEASE.json"
    state.rename(state.with_name("RELEASE.json"))


def _plant_stray_dotfile(root: Path) -> None:
    # Untracked and with no canon home — the case a ``git mv`` fix line could not serve
    # (bug tree8-fix-line-not-runnable-for-every-case).
    (root / "specs" / ".DS_Store").write_bytes(b"\x00")


def _plant_orphan_wt(root: Path) -> None:
    """An unmerged orphan: `wt/0.5.0-rc1/j1` carries a task merge and has no tree."""
    repo, tree = root / "repos/r", root / "worktrees/r/0.5.0-rc1/j1"
    task = root / "worktrees/r/0.5.0-rc1/j1--t1"
    worktree_ws.git(repo, "checkout", "-q", "feature/0.5.0")
    worktree_ws.git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0-rc1/j1", str(tree))
    worktree_ws.git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0-rc1/j1--t1", str(task))
    worktree_ws.commit(task, "src/a.py")
    worktree_ws.git(tree, "merge", "-q", "--ff-only", "wt/0.5.0-rc1/j1--t1")
    worktree_ws.git(repo, "worktree", "remove", str(task))
    worktree_ws.git(repo, "branch", "-q", "-D", "wt/0.5.0-rc1/j1--t1")
    worktree_ws.git(repo, "worktree", "remove", str(tree))


#: code -> how to make it fire. The eight remedies the 0.4.7 candidate-2 review named,
#: plus the memory-document pair they share a shape with.
PLANTS: dict[str, Plant] = {
    # sa-unfixable-doctor-findings-say-doctor-fix#S2 — the doctor's own repairs, run as
    # printed (`doctor --fix --specs-dir <specs>`).
    "TREE-4": Plant(_plant_nothing),
    # AC1.10: the workspace section's WORKTREE rule, proven by its own test below.
    "WORKTREE": Plant(_plant_orphan_wt),
    "TREE-5": Plant(_plant_missing_root_agents),
    "SPEC-DOC-034": Plant(_plant_nothing),
    "MEM-PLACEHOLDER-1": Plant(_plant_placeholder_atom),
    "FIXED-1": Plant(_plant_fixed_block_gone),
    "FIXED-2": Plant(_plant_fixed_block_drifted),
    "GITFLOW-1": Plant(_plant_gitflow_gone, {"<specs>": "specs"}),
    "TREE-3": Plant(_plant_missing_memory_document),
    "SPEC-DOC-046": Plant(_plant_legacy_state_name),
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env=suite_env(
            {}, root, overrides={"PATH": "/usr/bin:/bin", "GIT_CONFIG_GLOBAL": "/dev/null"}
        ),
    )


@pytest.fixture(scope="module")
def clean_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A git-backed fixture tree, built once per module: a fix line may legitimately be a
    `git rm`/`git mv`."""
    root = tmp_path_factory.mktemp("clean")
    _make_clean_specs_tree(root, _RELEASE)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")
    return root


@pytest.fixture
def repo(tmp_path: Path, clean_repo: Path) -> Path:
    """This test's own copy of the clean tree — every plant and fix mutates it."""
    shutil.copytree(clean_repo, tmp_path, symlinks=True, dirs_exist_ok=True)
    return tmp_path


def _doctor(root: Path) -> SpecsDoctor:
    """The specs doctor the CLI builds for *root* (templates, public tree, repo root)."""
    doctor = _build_specs_doctor(root / "specs", None)
    assert doctor is not None
    return doctor


def _run_rule(root: Path, rule: Rule[SpecsDoctor]) -> list[SectionFinding]:
    return rule.run(_doctor(root))


def _resolve(fix: str, plant: Plant) -> str:
    command = fix
    for token, value in plant.substitutions.items():
        command = command.replace(token, value)
    assert "<" not in command, f"unsubstituted placeholder left in:\n{command}"
    return command


_PLANTED_RULES: list[tuple[str, Rule[SpecsDoctor]]] = [
    (code, rule) for rule in SPECS_RULES for code in rule.codes if code in PLANTS
]


@pytest.mark.parametrize(("code", "rule"), _PLANTED_RULES, ids=[code for code, _ in _PLANTED_RULES])
def test_the_fix_line_clears_the_finding_it_was_stamped_on(
    code: str, rule: Rule[SpecsDoctor], repo: Path
) -> None:
    """Plant the finding, run the rule's OWN fix line, and the rule falls silent."""
    root = repo
    plant = PLANTS[code]
    plant.plant(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture")

    before = _run_rule(root, rule)
    assert before, f"{code}: the fixture did not make the rule fire"
    whole_before = _whole(root)
    if code == "TREE-3":  # sa-missing-memory-file-reported-twice: one finding for one fact
        assert [f[0] for f in whole_before if "memory/QUALITY.md" in f[1]] == ["TREE-3"]
    dead = [
        v
        for issue in before
        for line in issue.message.splitlines()
        for v in dead_verb_citations(f"`{line}`", rel=code, command_paths=command_paths())
    ]
    assert not dead, f"{code}: the finding cites a verb that does not exist: {dead}"

    if rule.fix_help is None:
        assert all(issue.verdict == "warning" for issue in before), (
            f"{code} carries no fix line, so it must never exit 1 — "
            f"got {[i.verdict for i in before]}"
        )
        return

    # sa-unfixable-doctor-findings-say-doctor-fix#S2: run the fix PRINTED on the finding
    # (its own, or the rule's default stamped by the doctor), never the rule default blind.
    # The fixture is no workspace: the fix names the CLI of the venv running this suite.
    (printed, *_) = run_section("specs", [rule], _doctor(root), None, root / "specs").findings
    # sa-unfixable-doctor-findings-say-doctor-fix#S1: no `<…>` survives into a printed fix.
    assert not re.search(r"<[^<>]+>", printed.fix), f"{code}: placeholder in {printed.fix}"
    command = _resolve(printed.fix, plant)
    done = run_bash(command, cwd=root, check=False)
    # `doctor --fix` exits 1 while the fixture's unrelated findings remain; the judge is
    # sa-unfixable-doctor-findings-say-doctor-fix#S2: re-run the WHOLE doctor — this
    # finding (its message) is gone and the fix created no new error elsewhere.
    after = _whole(root)
    assert (code, printed.message, printed.error) not in after, (
        f"{code}: survives\n{command}\n{done.stderr}"
    )
    new_errors = {f for f in after - whole_before if f[2]}
    assert not new_errors, f"{code}: the fix created {new_errors}"


def test_spec_doc_046_never_clobbers_a_canonical_state_file(repo: Path) -> None:
    """ADR 0007: with both names on disk SPEC-DOC-046 is silent, and a fix stamped before
    `_RELEASE.json` appeared re-checks and renames nothing."""
    release = repo / "specs" / "releases" / _RELEASE
    _plant_legacy_state_name(repo)
    doctor = _doctor(repo)
    [stale] = [i for i in doctor.check() if i.code == "SPEC-DOC-046"]
    (release / "_RELEASE.json").write_text("{}", encoding="utf-8")
    assert [i for i in doctor.check() if i.code == "SPEC-DOC-046"] == []
    doctor.fix([stale])
    assert (release / "RELEASE.json").is_file()
    assert (release / "_RELEASE.json").read_text(encoding="utf-8") == "{}"


def _whole(root: Path) -> set[tuple[str, str, bool]]:
    """Every finding of the whole specs section: (code, message, error-class)."""
    report = _specs_section(_doctor(root), None)
    return {(f.code, f.message, f.error) for f in report.findings}


def _iter_fix_helps() -> list[tuple[str, Any]]:
    return [("/".join(r.codes), rule_fix(r, Path()) or None) for r in SPECS_RULES]


#: a bare ``rm`` invocation with a recursive flag, at the head of the line or of any
#: segment of a chain. ``git rm -r`` is deliberately NOT matched: it stages a removal
#: that git history still holds.
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


#: sa-unfixable-doctor-findings-say-doctor-fix#S1 — `report-only` codes: WARNING-only by
#: construction, and no fix line (their remedy is the operator's judgment).
REPORT_ONLY: dict[str, Callable[[Path], None]] = {
    "SPEC-DOC-030": lambda r: (r / "specs" / "audits" / "Bad_Name").mkdir(parents=True),
    "MEM-DRIFT-1": lambda r: _append(
        r / "specs" / "memory" / "ARCHITECTURE.md",
        "\n### `dadaia_workspace/features` — package map (1 packages)\n\n"
        '```mermaid\nflowchart LR\n  pkgs["ghostpkg"]\n```\n',
    ),
    "MEM-DRIFT-2": lambda r: _append(
        r / "specs" / "memory" / "QUALITY.md", "\nRun `dadaia no-such-verb`.\n"
    ),
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


#: sa-unfixable-doctor-findings-say-doctor-fix#S1 — error findings no command can repair
#: (the remedy is the operator's content): each carries an `Operator action:` naming its file.
OPERATOR_ACTION: dict[str, Callable[[Path], None]] = {
    "SPEC-DOC-002": _plant_headingless_memory_document,
    "SPEC-DOC-004": _plant_status_line_gone,
    "TREE-8": _plant_stray_dotfile,
    "LINT-1": lambda r: _write(r / "specs" / "memory" / "product" / "testarea" / "x.md", "# X\n"),
    "SPEC-DOC-001": lambda r: (r / "specs" / "constitution.md").unlink(),
    "SPEC-DOC-026": lambda r: _write(r / f"specs/releases/_archive/{_RELEASE}/SPEC.md", "# S\n"),
    "ADR-SUPERSEDED-CITATION": lambda r: (
        _write(r / "specs/ADRs/decisions.jsonl", '{"id": "0001", "status": "superseded"}\n'),
        _append(r / "specs/memory/QUALITY.md", "\nADR: 0001\n"),
    ),
    "BL-SCHEMA": lambda r: _write(r / "specs/backlog/BACKLOG.json", json.dumps({"schema": "backlog-v1", "active": [
        _active_entry("xx", "x", "candidate", ref="pkg/m.py#Ghost", change="x")]})),
    "BL-CONFLICT": lambda r: (
        _write(r / "pkg/m.py", _SOURCE),
        _write(r / "specs/backlog/BACKLOG.json", json.dumps({"schema": "backlog-v1", "active": [
            _active_entry(t, t, "candidate", ref="pkg/m.py#Widget", change=t) for t in ("dd", "ee")]})),
    ),
}  # fmt: skip


@pytest.mark.parametrize("code", sorted(OPERATOR_ACTION))
def test_an_operator_action_names_the_file_to_change(code: str, repo: Path) -> None:
    """sa-unfixable-doctor-findings-say-doctor-fix#S1: an unfixable error's fix is one
    `Operator action:` line naming the finding's own file — never a placeholder."""
    root = repo
    OPERATOR_ACTION[code](root)
    ledgers = _ledgers_section(None, root / "specs")
    found = [f for f in (*_specs_section(_doctor(root), None).findings, *ledgers.findings) if f.code == code]  # fmt: skip
    assert found, f"{code}: the fixture did not make the rule fire"
    for finding in found:
        assert finding.fix.startswith("Operator action: "), finding.fix
        assert str(repo) in finding.fix and not re.search(r"<[^<>]+>", finding.fix)


def test_an_untraced_origin_id_is_cleared_by_its_printed_fix(repo: Path) -> None:
    """AC3.2 (review F4; SPEC-DOC-048's row re-homed): after the sweep, a carried entry with
    no exit is an error on the real Origin line; its printed fix writes the pointer back."""
    specs = repo / "specs"
    _write(specs / "backlog/BACKLOG.json", json.dumps(
        {"schema": "backlog-v1", "active": [_active_entry("carried", "c", "candidate")]}))  # fmt: skip
    spec = specs / "releases" / _RELEASE / "rc-1" / "SPEC.md"
    spec.write_text(spec.read_text("utf-8").replace("operator-demand", "backlog:carried"), "utf-8")

    def origin_errors() -> list[SectionFinding]:
        found = _ledgers_section(None, specs).findings
        rows = [f for f in found if "Origin" in f.message]
        assert all(f.error for f in rows), rows  # a listing row never reaches the doctor
        return rows

    assert origin_errors() == []  # before the sweep the carried id is only listed
    state = specs / "releases" / _RELEASE / "_RELEASE.json"
    sweep = {"ts": "2026-01-01T00:00:00Z", "agent": "a", "kind": "dispositions", "text": "t"}
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "log": [sweep]}))

    [before] = origin_errors()
    assert before.message.startswith(f"releases/{_RELEASE}/rc-1/SPEC.md:5 "), before.message
    run_bash(before.fix, cwd=repo, check=True)
    assert origin_errors() == []


def test_a_judgment_only_rule_never_makes_the_run_exit_1(repo: Path) -> None:
    """The exit-code half of the contract: every judgment-only rule fires at once and
    contributes NO error-class finding and NO fix line, so it stalls nobody
    (sa-unfixable-doctor-findings-say-doctor-fix#S1 — the `report-only` proof).
    sa-memory-atom-has-two-grammars#B29-6: a history heading planted beside them is
    reported once, by LINT-1 — CAT-1 and SPEC-DOC-008 do not exist."""
    root = repo
    _plant_changelog_heading(root)
    for plant in REPORT_ONLY.values():
        plant(root)

    report = _specs_section(_doctor(root), Path())
    fired = {f.code for f in report.printable}
    assert set(REPORT_ONLY) <= fired, fired
    assert not {"CAT-1", "SPEC-DOC-008", "SPEC-DOC-010"} & fired, fired
    history = [f for f in report.findings if "Changelog" in f.message]
    assert [(f.code, f.error) for f in history] == [("LINT-1", True)], history
    judged = [f for f in report.findings if f.code in REPORT_ONLY]
    assert [(f.code, f.error, f.fix) for f in judged if f.error or f.fix] == []


# ── T-050-09: TREE-5 remedies are honest (AC2.3, AC2.4) ─────────────────────────


def _doctor_json(specs: Path, *flags: str) -> list[dict[str, str]]:
    result = CliRunner().invoke(app, ["doctor", "--json", *flags, "--specs-dir", str(specs)])
    findings: list[dict[str, str]] = json.loads(result.output)["sections"]["specs"]["findings"]
    return findings


#: Literal lines of the rendered canon table and the registry placeholders (the law's own).
_AREA_HEADER = "| Area | Members |"
_ROOT_ROW = "| root | `AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/` |"
_PLACEHOLDERS = (
    "<!-- zones -->",
    "<!-- canon -->",
    "<!-- root -->",
    "<!-- specs-canon -->",
)


def test_doctor_fix_renders_a_raw_law_copy_and_clears_its_finding(repo: Path) -> None:
    """sa-specs-init-writes-unrendered-law#B38-3: a raw specs/AGENTS.md (the template an
    older `specs init` copied) is flagged by `dadaia doctor` as refreshable; `dadaia
    doctor --fix` renders it and the TREE-5 finding is gone."""
    specs = repo / "specs"
    public = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
    law = specs / "AGENTS.md"
    law.write_bytes((public / "templates" / "specs-AGENTS.md").read_bytes())

    def root_law_findings() -> list[str]:
        messages = [f["message"] for f in _doctor_json(specs) if f["code"] == "TREE-5"]
        return [m for m in messages if m.startswith("specs/AGENTS.md ")]

    before = root_law_findings()
    assert len(before) == 1 and "refreshed losslessly" in before[0], before

    _doctor_json(specs, "--fix")

    text = law.read_text(encoding="utf-8")
    assert _AREA_HEADER in text and _ROOT_ROW in text
    assert not [p for p in _PLACEHOLDERS if p in text]
    assert root_law_findings() == []


def test_a_worktree_finding_is_cleared_by_its_merge_fix(tmp_path: Path) -> None:
    """AC1.10: an unmerged orphan wt/* carries the owner's `worktree.py merge`; its chain —
    merge refuses with the re-attach, the re-attached (unlocked) tree is still ours and
    `ready`, the reviewed merge lands — ends with no finding."""
    root = worktree_ws.make_workspace(tmp_path)
    PLANTS["WORKTREE"].plant(root)
    doctor = worktree_ws.registered_doctor(root)
    for _ in range(3):
        if not (found := doctor.check_worktrees("c")):
            break
        worktree_ws.approve(
            root, worktree_ws.git(root / "repos/r", "rev-parse", "wt/0.5.0-rc1/j1").strip()
        )
        command = found[0].fix
        done = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True)  # noqa: S602
        if done.returncode:
            (refix,) = worktree_ws.fixes(done)
            subprocess.run(refix.removeprefix("fix: "), shell=True, check=True, capture_output=True)  # noqa: S602
    assert doctor.check_worktrees("c") == []


def _plant_file(entry: Path, _outside: Path) -> None:
    entry.write_text("# mine\n", encoding="utf-8")


def _plant_link(entry: Path, outside: Path) -> None:
    entry.symlink_to(outside)


def _identity(entry: Path) -> tuple[int, str]:
    """lstat identity: the inode plus the link target or the content — never followed."""
    body = os.readlink(entry) if entry.is_symlink() else entry.read_text(encoding="utf-8")
    return entry.lstat().st_ino, body


@pytest.mark.parametrize(
    ("present", "plant"),
    [(".dadaiaignore", _plant_file), ("prompt.md", _plant_file), ("prompt.md", _plant_link)],
    ids=["dadaiaignore", "prompt", "dangling-link"],
)
def test_the_session_lane_re_creates_missing_core_and_rewrites_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    present: str,
    plant: Callable[[Path, Path], None],
) -> None:
    """AC2.4 (ADR 0096): the SessionStart lane re-creates a missing level-1
    entry (`.dadaiaignore`, `prompt.md`, every provisioned zone) and rewrites no present one —
    a dangling link is present, never written through."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside" / "pwned.md"
    outside.parent.mkdir()
    plant(tmp_path / present, outside)
    planted = _identity(tmp_path / present)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        container,
        "build_doctor_service",
        lambda root: DoctorService(
            context_store(root / ".dadaia/states"), GitSubprocessClient(), root
        ),
    )

    lane = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only", "--quiet"])

    assert lane.exit_code == 0, lane.output
    assert all(occupied(tmp_path / name) for name in LEVEL1_SEEDS) and not outside.exists()
    assert all((tmp_path / ".dadaia" / zone.name).is_dir() for zone in provisioned_zones())
    assert _identity(tmp_path / present) == planted
