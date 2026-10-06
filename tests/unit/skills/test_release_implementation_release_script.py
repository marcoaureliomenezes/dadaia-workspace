"""dd-release-implementation/scripts/release.py owns _RELEASE.json,
the candidate trio and releases_histo.jsonl (0.4.7 c7 T-047-66: the release ledger verbs
move into a stdlib skill script). Size: SMALL.

The script reads its two schemas from ``scripts/schemas/`` BESIDE itself — copies
`public stage` makes — so every test stages the folder exactly as stage does.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import ANY

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import load_owner
from tests.helpers.release_state import PLAN
from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-release-implementation" / "scripts"
_SCHEMAS = (
    _PUBLIC / "schemas" / "releases" / "release-state-v1.schema.json",
    _PUBLIC / "schemas" / "histo" / "histo-record-v1.schema.json",
)
_TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")
_TS = "2026-09-22T00:00:00Z"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: release.py with both schema copies beside it, and the spec
    navigator's scripts projected as its sibling skill (the drift decider it imports)."""
    for skill in ("dd-spec-navigator", "dd-gitflow-default"):  # the siblings it imports
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    return (
        stage_skill_scripts(
            "dd-release-implementation",
            tmp_path / "skills" / "dd-release-implementation" / "scripts",
        )
        / "release.py"
    )


def _run(script: Path, *argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


def _state(release_id: str, **over: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema": "release-state-v1",
        "release": release_id,
        "phase": "DEFINITION",
        "defined": None,
        "implemented": None,
        "shipped": None,
        "log": [],
    }
    document.update(over)
    return document


def _release(
    specs: Path, release_id: str, *, tasks: str = "- [x] T-1 — done\n", **over: object
) -> Path:
    """One live release directory: its state document and candidate 1's trio in `rc-1/`."""
    release_dir = specs / "releases" / release_id
    (release_dir / "rc-1").mkdir(parents=True, exist_ok=True)
    for name in _TRIO:
        body = {"TASKS.md": tasks, "PLAN.md": PLAN}.get(
            name, "**Origin:** operator-demand\n\n## Bug window review\n"
        )
        release_dir.joinpath("rc-1", name).write_text(
            f"# {name}\n\n**Status:** Approved\n\n{body}", encoding="utf-8"
        )
    release_dir.joinpath("_RELEASE.json").write_text(
        json.dumps(_state(release_id, **over), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release_dir


def _specs(root: Path) -> Path:
    specs = root / "specs"
    (specs / "releases" / "_archive").mkdir(parents=True, exist_ok=True)
    (specs / "releases" / "_archive" / "releases_histo.jsonl").write_text("", encoding="utf-8")
    return specs


def _read(path: Path) -> dict[str, object]:
    document: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return document


def _tree_hash(root: Path) -> list[tuple[str, str]]:
    """Every file under *root* as (relative posix path, sha256) — the transaction probe."""
    return sorted(
        (
            p.relative_to(root).as_posix(),
            hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in root.rglob("*")
        if p.is_file()
    )


# ── new ───────────────────────────────────────────────────────────────────────


def test_new_writes_the_spec_stub_and_the_state_in_one_act(script: Path, tmp_path: Path) -> None:
    """A U+2028 inside a bug record is text, not a line break (release-new-crashes-on-a-
    unicode-line-separator-in-the-bug-ledger): the bugs: origin seeds the SPEC from it."""
    specs = _specs(tmp_path)
    bug = {"id": "ls-probe", "title": "t\u2028x", "repro": "r"}
    (specs / "bugs").mkdir()
    (specs / "bugs/BUGS.jsonl").write_text(json.dumps(bug, ensure_ascii=False) + "\n", "utf-8")
    result = _run(script, "new", "0.6.0", "--specs", str(specs), "--origin", "bugs:ls-probe")
    assert result.returncode == 0, result.stderr
    release_dir = specs / "releases" / "0.6.0"
    spec_md = (release_dir / "rc-1/SPEC.md").read_text(encoding="utf-8")
    assert "**Status:** Draft" in spec_md and "### FR1 — t\u2028x" in spec_md
    assert sorted(p.name for p in release_dir.iterdir()) == ["_RELEASE.json", "rc-1"]
    state = _read(release_dir / "_RELEASE.json")
    assert state["schema"] == "release-state-v1"
    assert state["phase"] == "DEFINITION"
    assert state["release"] == "0.6.0"
    assert "rc" not in state


def test_new_refuses_a_second_live_release_with_one_fix_line(script: Path, tmp_path: Path) -> None:
    """ADR 0005: exactly one live release, ever. The refusal writes nothing."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    before = _tree_hash(specs)
    result = _run(script, "new", "0.6.0", "--specs", str(specs))
    assert result.returncode == 1
    assert "0.5.0" in result.stderr
    fixes = [line for line in result.stderr.splitlines() if line.startswith("fix: ")]
    assert len(fixes) == 1, result.stderr
    assert not (specs / "releases" / "0.6.0").exists()
    assert _tree_hash(specs) == before


def test_new_opens_the_rc_spec_with_the_bug_window_review(script: Path, tmp_path: Path) -> None:
    """AC5.6: `new` writes `## Bug window review` as the first SPEC heading."""
    specs = _specs(tmp_path)
    assert _run(script, "new", "9.9.9", "--specs", str(specs)).returncode == 0
    spec = (specs / "releases" / "9.9.9" / "rc-1" / "SPEC.md").read_text(encoding="utf-8")
    headings = [line for line in spec.splitlines() if line.startswith("## ")]
    assert headings[:1] == ["## Bug window review"]


# fmt: off
@pytest.mark.parametrize(("phase", "errors", "verdict"), [
    pytest.param("DEFINITION", [("releases/0.5.0/rc-1/SPEC.md", 1, True)], "error",
                 id="definition-refuses"),
    pytest.param("IMPLEMENTATION", [], "info", id="past-definition-informs"),
])
# fmt: on
def test_a_live_spec_without_the_bug_window_review(
    script: Path, tmp_path: Path, phase: str, errors: list[tuple[str, int, bool]], verdict: str
) -> None:
    """AC5.6, scoped as the Origin check is: a live SPEC lacking the heading is an error with
    one fix while its candidate is in DEFINITION (where `new` writes it); past it, info."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase=phase, tasks="- [ ] T-1 — open\n")
    spec_md = specs / "releases" / "0.5.0" / "rc-1" / "SPEC.md"
    spec_md.write_text(spec_md.read_text(encoding="utf-8").replace("## Bug window review\n", ""))
    found = _run(script, "check", "--json", "--specs", str(specs))
    listed = _run(script, "check", "--specs", str(specs))
    assert found.returncode == (1 if errors else 0), found.stdout
    assert [(f["path"], f["line"], bool(f["fix"])) for f in json.loads(found.stdout)] == errors
    assert f"{verdict} releases/0.5.0/rc-1/SPEC.md:1 " in listed.stdout


def test_a_verb_with_no_live_release_hands_new_to_the_operator(
    script: Path, tmp_path: Path
) -> None:
    """ADR 0158: with no live release the one fix is the operator's `new`, version unchosen."""
    specs = _specs(tmp_path)
    result = _run(script, "phase", "IMPLEMENTATION", "--sha", "abc1234", "--specs", str(specs))
    py = Path(sys.executable).as_posix()
    assert result.returncode == 1
    assert result.stderr.splitlines()[-1] == (
        f"fix: Operator action: run `{py} {script.as_posix()} new --specs {specs.as_posix()}` "
        "with the release version you choose"
    )


def test_new_births_the_stacked_candidate_on_a_closed_live_release(
    script: Path, tmp_path: Path
) -> None:
    """ADR 0150: `new <id>` on the live release in CLOSURE births `rc-<N+1>/` on a SPEC
    stub, never touches the closed `rc-<N>/`, resets phase to DEFINITION and leaves the
    milestones standing (`phase IMPLEMENTATION` restamps `defined`)."""
    specs = _specs(tmp_path)
    release_dir = _release(
        specs,
        "0.5.0",
        phase="CLOSURE",
        defined={"sha": "aaaaaaa", "ts": "2026-01-01T00:00:00Z"},
        implemented={"sha": "beef123", "ts": "2026-01-02T00:00:00Z"},
    )
    closed = _tree_hash(release_dir / "rc-1")
    result = _run(script, "new", "0.5.0", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    assert "**Status:** Draft" in (release_dir / "rc-2/SPEC.md").read_text(encoding="utf-8")
    assert sorted(p.name for p in (release_dir / "rc-2").iterdir()) == ["SPEC.md"]
    assert _tree_hash(release_dir / "rc-1") == closed
    state = _read(release_dir / "_RELEASE.json")
    assert state["phase"] == "DEFINITION"
    assert state["defined"] == {"sha": "aaaaaaa", "ts": "2026-01-01T00:00:00Z"}
    assert state["implemented"] == {"sha": "beef123", "ts": "2026-01-02T00:00:00Z"}
    notes = [entry["text"] for entry in state["log"]]
    assert notes == ["Candidate born on 0.5.0 (prior candidate closed at beef123)"]


def test_new_refuses_the_same_id_while_its_candidate_is_open(script: Path, tmp_path: Path) -> None:
    """sa-promote-has-no-verb#B25-8: a candidate is stacked only on a CLOSURE state: mid-IMPLEMENTATION the live trio
    is still being worked, and the refusal names the phase verb that unblocks it."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    before = _tree_hash(specs)
    result = _run(script, "new", "0.5.0", "--specs", str(specs))
    assert result.returncode == 1
    assert "IMPLEMENTATION" in result.stderr
    fixes = [line for line in result.stderr.splitlines() if line.startswith("fix: ")]
    assert len(fixes) == 1 and "phase CLOSURE" in fixes[0], result.stderr
    assert _tree_hash(specs) == before


def test_new_refuses_a_non_semver_id(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    assert _run(script, "new", "v0.6.0", "--specs", str(specs)).returncode == 1


# ── phase ─────────────────────────────────────────────────────────────────────


def test_phase_implementation_stamps_defined(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    result = _run(script, "phase", "IMPLEMENTATION", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    state = _read(specs / "releases" / "0.5.0" / "_RELEASE.json")
    assert state["phase"] == "IMPLEMENTATION"
    assert isinstance(state["defined"], dict)
    assert state["defined"]["sha"] == "abc1234"


def test_phase_closure_stamps_the_implemented_milestone(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    result = _run(script, "phase", "CLOSURE", "--sha", "beef123", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    state = _read(specs / "releases" / "0.5.0" / "_RELEASE.json")
    assert state["phase"] == "CLOSURE"
    assert state["implemented"] == {"sha": "beef123", "ts": state["implemented"]["ts"]}
    # AC3.14 (F061): the slot holds the live candidate's stamp; the log keeps every one.
    assert state["log"][-1] == {"ts": ANY, "agent": "release.py", "kind": "milestone",
                                "candidate": "rc-1", "milestone": "implemented",
                                "sha": "beef123", "text": ANY}  # fmt: skip


def test_phase_implementation_refuses_an_unapproved_trio(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    release_dir = _release(specs, "0.5.0")
    (release_dir / "rc-1/PLAN.md").write_text("# PLAN\n\n**Status:** Draft\n", encoding="utf-8")
    result = _run(script, "phase", "IMPLEMENTATION", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 1
    assert "PLAN.md" in result.stderr


def test_phase_refuses_a_malformed_sha(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    assert (
        _run(script, "phase", "IMPLEMENTATION", "--sha", "zz", "--specs", str(specs)).returncode
        == 1
    )


# ── check ─────────────────────────────────────────────────────────────────────


def test_check_is_clean_on_a_valid_tree(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    result = _run(script, "check", "--specs", str(specs))
    assert result.returncode == 0, result.stdout


def test_writes_reads_rc6_t_050_117_to_its_ten_paths(script: Path) -> None:
    """AC3.3: a backticked path inside parentheses is named, not written. The line is
    rc-6 TASKS.md's T-050-117 verbatim (commit a386efc7), inlined: `ship` archives rc-6."""
    sys.path.insert(0, str(script.parent))  # the staged copy: no bytecode beside the source
    from _release_schema import MARK_RE, writes

    line = '- [x] **T-050-117 — PROTECTED floor in code; the protected section.** `W:` `core/workspace_layout.py`, `f/spec_context/gate_policy.py`, `hooks/sdd_gate.py`, `f/spec_context/doctor.py`, `CONTEXT.md`, `tests/unit/features/spec_context/test_gate_policy.py`, `tests/unit/hooks/test_pre_gate.py`, `tests/unit/core/test_workspace_layout_zones.py`, `tests/unit/hooks/test_sdd_gate.py`, `tests/integration/scripts/test_run_mutation_baseline_wiring.py` (:65 reads `classify_path(...)[0]`), (:83 B39-7 unledgered row drops root `AGENTS.md`, now floor) (the grammar owner, :97,104 rewritten to the triple; `doctor.py:299` follows the triple)'  # fmt: skip
    assert writes("`W:` `a.py` ) `b.py`") == ["a.py", "b.py"]  # a stray `)` drops nothing
    assert [m[0] for m in MARK_RE.finditer("-\n\n- [ ]**T-1**")] == ["- [ ]**T-1**"]
    assert writes(line) == [
        "core/workspace_layout.py", "f/spec_context/gate_policy.py", "hooks/sdd_gate.py",
        "f/spec_context/doctor.py", "CONTEXT.md", "tests/unit/features/spec_context/test_gate_policy.py",
        "tests/unit/hooks/test_pre_gate.py", "tests/unit/core/test_workspace_layout_zones.py",
        "tests/unit/hooks/test_sdd_gate.py", "tests/integration/scripts/test_run_mutation_baseline_wiring.py",
    ]  # fmt: skip


def test_tasks_without_a_memory_write_set_are_silent(script: Path, tmp_path: Path) -> None:
    """Re-homed from the doctor's SPEC-DOC-047 (memory is closure procedure, never a task):
    `specs/memory` in prose or in a source file name is not a `W:` naming the memory tree."""
    specs = _specs(tmp_path)
    tasks = "- [ ] **T-1** specs/memory in prose `W:` `f/specs/memory_lint.py`\n"
    _release(specs, "0.5.0", phase="IMPLEMENTATION", tasks=tasks)
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_a_source_file_named_memory_is_not_a_memory_write_set(script: Path, tmp_path: Path) -> None:
    """Re-homed SPEC-DOC-047: a `W:` naming `specs/memory` is a finding naming its task;
    `memory_lint.py` beside it is not (bug spec-doc-047-matches-specs-memory-as-a-substring)."""
    specs = _specs(tmp_path)
    tasks = "- [ ] **T-1** `W:` `f/specs/memory_lint.py`\n- [ ] **T-2** `W:` `specs/memory/x.md`\n"
    _release(specs, "0.5.0", phase="IMPLEMENTATION", tasks=tasks)
    result = _run(script, "check", "--specs", str(specs))
    assert result.returncode == 1
    assert "T-2" in result.stdout and "T-1" not in result.stdout, result.stdout


@pytest.mark.parametrize(
    ("tasks", "log", "needle"),
    [
        ("- [x] **T-1** done\n", [], "T-1"),
        ("- [-] **T-1** reserved\n", [], "T-1"),
        ("- [ ] **T-1** `W:` `specs/memory/x.md`\n", [], "specs/memory"),
        ("- [ ] **T-1** open\n", [("new", "note"), ("x", "dispositions")], "dispositions"),
        ("- [ ] **T-1** open\n", [("x", "dispositions"), ("new", "note")], None),
    ],
)
def test_check_judges_a_definition_release(
    script: Path, tmp_path: Path, tasks: str, log: list[tuple[str, str]], needle: str | None
) -> None:
    """AC3.4 (release-check-accepts-done-tasks-in-definition): a marker past `[ ]`, a `W:`
    naming specs/memory (refused where it is born, memory-gate-requires-closure-phase-
    that-spec-doc-024-forbids-before-last-task) or a closure entry after the candidate's
    birth note is a finding under DEFINITION; a stacked candidate's inherited closure
    entries, logged before its birth, are not."""
    specs = _specs(tmp_path)
    entries = [{"ts": _TS, "agent": f"release.py {a}", "kind": k, "text": k} for a, k in log]
    _release(specs, "0.5.0", tasks=tasks, log=entries)
    result = _run(script, "check", "--specs", str(specs))
    if needle:
        assert result.returncode == 1 and needle in result.stdout, result.stdout
    else:
        assert result.returncode == 0, result.stdout


def test_a_definition_finding_stamps_the_commit_that_touched_the_trio(
    script: Path, tmp_path: Path
) -> None:
    """AC3.4 review M3: `defined` is the trio's last commit, never HEAD — implementation
    commits after it stay inside the memory window `defined.sha` opens."""
    root, specs, _ = _memory_repo(tmp_path, script)
    trio = _git(root, "log", "-1", "--format=%h", "--", "specs/releases/0.5.0/rc-1/SPEC.md")
    _release(specs, "0.5.0")  # DEFINITION, `[x]` T-1; the trio's bytes unchanged
    (root / "dadaia_workspace/features/alpha/core.py").write_text("x = 3\n", encoding="utf-8")
    _git(root, "commit", "-qam", "implementation after the trio")
    fixes = [
        f["fix"] for f in json.loads(_run(script, "check", "--json", "--specs", str(specs)).stdout)
    ]
    assert fixes and all(f" --sha {trio} " in f for f in fixes), (trio, fixes)


def test_check_reports_a_schema_violation_and_emits_json(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    release_dir = _release(specs, "0.5.0")
    release_dir.joinpath("_RELEASE.json").write_text(
        json.dumps({"schema": "release-state-v1", "release": "0.5.0"}) + "\n", encoding="utf-8"
    )
    result = _run(script, "check", "--specs", str(specs), "--json")
    assert result.returncode == 1
    findings = json.loads(result.stdout)
    assert findings and all(f["code"] == "LEDGER-RELEASE-SCHEMA" for f in findings)


def test_check_reports_a_histo_record_that_is_not_valid_json(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    (specs / "releases" / "_archive" / "releases_histo.jsonl").write_text("{\n", encoding="utf-8")
    assert _run(script, "check", "--specs", str(specs)).returncode == 1


def test_check_reports_out_of_order_log_timestamps(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(
        specs,
        "0.5.0",
        phase="IMPLEMENTATION",
        log=[
            {"ts": "2026-02-01T00:00:00Z", "agent": "a", "kind": "note", "text": "later"},
            {"ts": "2026-01-01T00:00:00Z", "agent": "a", "kind": "note", "text": "earlier"},
        ],
    )
    result = _run(script, "check", "--specs", str(specs))
    assert result.returncode == 1
    assert "precedes" in result.stdout


def test_check_finds_the_specs_tree_by_walking_up_from_cwd(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    (tmp_path / ".git").mkdir()
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert _run(script, "check", cwd=nested).returncode == 0


# ── every refusal carries exactly one runnable `fix:` ─────────────────────────


def _in_phase(root: Path, script: Path, phase: str) -> Path:
    """A tree whose next verb runs: DEFINITION open, IMPLEMENTATION done, CLOSURE reconciled."""
    if phase == "CLOSURE":
        return _reconciled_closure(root, script)
    specs = _specs(root)
    _release(
        specs, "0.5.0", phase=phase, tasks=f"- [{' ' if phase == 'DEFINITION' else 'x'}] T-1\n"
    )
    return specs


@pytest.mark.parametrize(
    ("phase", "argv"),
    [
        ("DEFINITION", ("phase", "IMPLEMENTATION", "--sha", "nope")),
        ("DEFINITION", ("phase", "CLOSURE", "--sha", "abc1234")),
        ("IMPLEMENTATION", ("phase", "IMPLEMENTATION", "--sha", "abc1234")),
        ("CLOSURE", ("phase", "DEFINITION", "--sha", "abc1234")),
        ("CLOSURE", ("phase", "ARCHIVED", "--sha", "abc1234")),
        ("DEFINITION", ("ship", "--sha", "abc1234", "--pr", "7")),
        ("IMPLEMENTATION", ("ship", "--sha", "abc1234", "--pr", "7")),
        ("CLOSURE", ("ship", "--sha", "abc1234", "--pr", "zero")),
    ],
)
def test_every_refusal_carries_one_fix_that_is_not_itself_refused(
    script: Path, tmp_path: Path, phase: str, argv: tuple[str, ...]
) -> None:
    """sa-promote-has-no-verb#B25-7 and sa-promote-has-no-verb#B25-3: a refusal exits 1, writes nothing, prints
    one `fix:` — and that fix, run as printed in the same state, is not refused;
    ledger-fix-lines-drop-specs: under a spaced specs path too."""
    specs = _in_phase(tmp_path / "a b", script, phase)
    before = _tree_hash(specs)
    result = _run(script, *argv, "--specs", str(specs))
    assert result.returncode == 1, result.stdout
    assert _tree_hash(specs) == before
    fixes = [
        line.removeprefix("fix: ")
        for line in result.stderr.splitlines()
        if line.startswith("fix: ")
    ]
    assert len(fixes) == 1, result.stderr
    # T-050-149 (AC4.4): no `<n>` — the PR number is the operator's act, supplied as it says.
    act = re.fullmatch(
        r"Operator action: run `(.+)` with --pr set to the promote PR's .+", fixes[0]
    )
    command = f"{act[1]} --pr 7" if act else fixes[0]
    assert "<" not in fixes[0] and (act is not None) == (phase == "CLOSURE"), fixes[0]
    command = command.replace("$(git rev-parse --short HEAD)", "abc1234")
    done = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
    assert done.returncode == 0, (command, done.stderr)


# ── memory ────────────────────────────────────────────────────────────────────


_ATOM = "---\nslug: {0}\ntitle: {0}\ntldr: {0}\nsummary: {0}\ntags: [{0}]\nsources:\n  - dadaia_workspace/features/{0}/**\n---\n\n# {0}\n"


def _git(root: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _memory_repo(tmp_path: Path, script: Path) -> tuple[Path, Path, str]:
    """A git repo whose one atom `alpha` covers `features/alpha`, committed at *base*;
    the live release is in CLOSURE with `defined.sha` = base, and the code moved since."""
    root = tmp_path / "repo"
    specs = _specs(root)
    code = root / "dadaia_workspace" / "features" / "alpha" / "core.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")
    atom = specs / "memory" / "product" / "platform" / "alpha.md"
    atom.parent.mkdir(parents=True)
    atom.write_text(_ATOM.format("alpha"), encoding="utf-8")
    navigator = script.parents[2] / "dd-spec-navigator" / "scripts" / "memory.py"
    _run(navigator, "catalog", "generate", "--specs", str(specs))
    _git(root.parent, "init", "-q", root.name)
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    base = _git(root, "rev-parse", "HEAD")
    _release(specs, "0.5.0", phase="CLOSURE", defined={"sha": base, "ts": _TS},
             implemented={"sha": base, "ts": _TS})  # fmt: skip
    code.write_text("x = 2\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "code moved")
    return root, specs, base


def _reconciled_closure(tmp_path: Path, script: Path) -> Path:
    """`_memory_repo` with its one atom rewritten and the `memory` entry recorded: ready."""
    root, specs, _ = _memory_repo(tmp_path, script)
    atom = specs / "memory" / "product" / "platform" / "alpha.md"
    atom.write_text(_ATOM.format("alpha") + "rewritten\n", encoding="utf-8")
    _git(root, "commit", "-qam", "atom reconciled")
    assert _memory(script, root, specs, changed="alpha").returncode == 0
    return specs


def _memory(script: Path, root: Path, specs: Path, **lists: str):
    argv = [f"--{name}={value}" for name, value in lists.items()]
    return _run(script, "memory", *argv, "--specs", str(specs), cwd=root)


def _log(specs: Path) -> list[dict[str, object]]:
    return _read(specs / "releases" / "0.5.0" / "_RELEASE.json")["log"]  # type: ignore[return-value]


def test_memory_derives_its_window_and_records_since_and_until(
    script: Path, tmp_path: Path
) -> None:
    root, specs, base = _memory_repo(tmp_path, script)
    (specs / "memory" / "product" / "platform" / "alpha.md").write_text(
        _ATOM.format("alpha") + "rewritten\n", encoding="utf-8"
    )
    _git(root, "commit", "-qam", "atom reconciled")

    result = _memory(script, root, specs, reviewed="", changed="alpha")

    assert result.returncode == 0, result.stderr
    entry = _log(specs)[-1]
    assert entry["kind"] == "memory"
    assert entry["since"] == base
    assert entry["until"] == _git(root, "rev-parse", "HEAD")
    assert entry["reviewed"] == [] and entry["changed"] == ["alpha"]
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_a_memory_rerun_over_the_same_window_appends_nothing(script: Path, tmp_path: Path) -> None:
    specs = _reconciled_closure(tmp_path, script)
    root = specs.parent
    before = [json.dumps(e, sort_keys=True) for e in _log(specs) if e["kind"] == "memory"]

    result = _memory(script, root, specs, changed="alpha")

    assert result.returncode == 0, result.stderr
    after = [json.dumps(e, sort_keys=True) for e in _log(specs) if e["kind"] == "memory"]
    assert after == before


def test_the_first_memory_run_at_the_definition_sha_records_its_entry(
    script: Path, tmp_path: Path
) -> None:
    """J2.S6.T5 (review F9): with HEAD at defined.sha and no memory entry yet, the run is
    the first reconciliation, never "already reconciled": it records since == until."""
    root, specs, _ = _memory_repo(tmp_path, script)
    head = _git(root, "rev-parse", "HEAD")
    _release(specs, "0.5.0", phase="CLOSURE", defined={"sha": head, "ts": _TS},
             implemented={"sha": head, "ts": _TS})  # fmt: skip

    result = _memory(script, root, specs, reviewed="", changed="")

    assert result.returncode == 0, result.stderr
    entries = [e for e in _log(specs) if e["kind"] == "memory"]
    assert [(e["since"], e["until"]) for e in entries] == [(head, head)]


def test_memory_takes_no_caller_chosen_window_or_worklist(script: Path, tmp_path: Path) -> None:
    """H1: `--since`/`--worklist` were the caller choosing an empty window; they are gone."""
    root, specs, base = _memory_repo(tmp_path, script)
    for flag in (["--since", base], ["--worklist", str(tmp_path / "empty.json")]):
        result = _run(script, "memory", *flag, "--reviewed=alpha", "--specs", str(specs), cwd=root)
        assert result.returncode == 2, flag
    assert _log(specs) == []


def test_memory_refuses_an_empty_closure_over_a_moved_window(script: Path, tmp_path: Path) -> None:
    """H1: the code moved since defined.sha, so the derived worklist names `alpha` — a
    closure dispositioning nothing is refused."""
    root, specs, _ = _memory_repo(tmp_path, script)

    result = _memory(script, root, specs, reviewed="", changed="")

    assert result.returncode == 1
    assert "'alpha'" in result.stderr
    assert _log(specs) == []


def test_memory_refuses_a_slug_outside_the_worklist(script: Path, tmp_path: Path) -> None:
    root, specs, _ = _memory_repo(tmp_path, script)

    result = _memory(script, root, specs, reviewed="alpha", changed="ghost")

    assert result.returncode == 1
    assert "'ghost' is not in the window's worklist" in result.stderr
    assert _log(specs) == []


def test_memory_refuses_a_changed_slug_whose_atom_never_moved(script: Path, tmp_path: Path) -> None:
    """A `changed` atom git says did not move over since..HEAD changed nothing."""
    root, specs, _ = _memory_repo(tmp_path, script)

    result = _memory(script, root, specs, reviewed="", changed="alpha")

    assert result.returncode == 1
    assert "did not move" in result.stderr
    assert _log(specs) == []


def test_memory_opens_the_next_window_at_the_previous_until(script: Path, tmp_path: Path) -> None:
    """The second reconciliation starts where the first closed: with no code moved since,
    its worklist is empty and the empty entry is accepted."""
    root, specs, _ = _memory_repo(tmp_path, script)
    assert _memory(script, root, specs, reviewed="alpha", changed="").returncode == 0
    _git(root, "commit", "-qam", "memory entry")  # the state file is tracked
    until = _log(specs)[-1]["until"]

    result = _memory(script, root, specs, reviewed="", changed="")

    assert result.returncode == 0, result.stderr
    assert _log(specs)[-1]["since"] == until


def test_a_rerun_after_the_second_reconciliation_appends_nothing(
    script: Path, tmp_path: Path
) -> None:
    """J2.S6.T5: the no-op reads the LAST memory record's until, not the first one's."""
    root, specs, _ = _memory_repo(tmp_path, script)
    assert _memory(script, root, specs, reviewed="alpha", changed="").returncode == 0
    _git(root, "commit", "-qam", "memory entry")
    assert _memory(script, root, specs, reviewed="", changed="").returncode == 0

    result = _memory(script, root, specs, reviewed="", changed="")

    assert result.returncode == 0, result.stderr
    assert len([e for e in _log(specs) if e["kind"] == "memory"]) == 2


def test_memory_refuses_any_phase_but_closure(script: Path, tmp_path: Path) -> None:
    root, specs, _ = _memory_repo(tmp_path, script)
    state = specs / "releases" / "0.5.0" / "_RELEASE.json"
    document = _read(state)
    document["phase"] = "IMPLEMENTATION"
    state.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    result = _memory(script, root, specs, reviewed="alpha", changed="")

    assert result.returncode == 1
    assert "CLOSURE" in result.stderr


def _hand_append(specs: Path, **entry: object) -> None:
    """A `kind: memory` entry written by hand, bypassing the verb's refusals."""
    state = specs / "releases" / "0.5.0" / "_RELEASE.json"
    document = _read(state)
    document["log"] = [{"ts": _TS, "agent": "hand", "kind": "memory", "text": "hand", **entry}]
    state.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def test_check_refuses_a_hand_appended_entry_that_worked_nothing(
    script: Path, tmp_path: Path
) -> None:
    """A6: check re-runs the one decider over the entry's own [since, until] — an empty
    disposition over a window where `alpha` moved is not a reconciliation record."""
    root, specs, base = _memory_repo(tmp_path, script)
    _hand_append(specs, since=base, until=_git(root, "rev-parse", "HEAD"), reviewed=[], changed=[])

    result = _run(script, "check", "--specs", str(specs), cwd=root)

    assert result.returncode == 1
    assert "'alpha' is in neither --reviewed nor --changed" in result.stdout


def test_check_refuses_code_that_moved_after_the_entry(script: Path, tmp_path: Path) -> None:
    """A9: a source commit after the entry's `until` leaves memory unreconciled — check
    names the atom whose sources moved."""
    root, specs, base = _memory_repo(tmp_path, script)
    until = _git(root, "rev-parse", "HEAD")
    _hand_append(specs, since=base, until=until, reviewed=["alpha"], changed=[])
    assert _run(script, "check", "--specs", str(specs), cwd=root).returncode == 0
    (root / "dadaia_workspace" / "features" / "alpha" / "core.py").write_text("x = 3\n", "utf-8")
    _git(root, "commit", "-qam", "code moved after the entry")

    result = _run(script, "check", "--specs", str(specs), cwd=root)

    assert result.returncode == 1
    assert "'alpha'" in result.stdout and until[:12] in result.stdout


# ── ship ──────────────────────────────────────────────────────────────────────


def test_ship_refuses_what_check_refuses_and_touches_nothing(script: Path, tmp_path: Path) -> None:
    """AC3.4, the bug's repro (release-ship-accepts-what-release-check-refuses): a CLOSURE
    with no memory entry — `ship` exits 1 with `check`'s message and fix, nothing written."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="CLOSURE")
    before = _tree_hash(specs)
    checked = json.loads(_run(script, "check", "--json", "--specs", str(specs)).stdout)[0]
    result = _run(script, "ship", "--sha", "beef123", "--pr", "261", "--specs", str(specs))
    assert result.returncode == 1
    assert checked["message"] in result.stderr
    assert [x for x in result.stderr.splitlines() if x.startswith("fix: ")] == [
        f"fix: {checked['fix']}"
    ]
    assert _tree_hash(specs) == before
    _release(specs, "0.5.0", phase="BOGUS")  # review L1: an invalid phase refuses, no KeyError
    bogus = _run(script, "ship", "--sha", "beef123", "--pr", "261", "--specs", str(specs))
    assert bogus.returncode == 1 and "Traceback" not in bogus.stderr, bogus.stderr


def test_ship_records_the_promote_and_new_births_the_next(script: Path, tmp_path: Path) -> None:
    """sa-promote-has-no-verb#B25-1, sa-promote-has-no-verb#B25-2,
    sa-promote-has-no-verb#B25-4: a reconciled CLOSURE ships by verb; ADR 0152 (1): the
    folder moves to `_archive/<v>/`; AC3.14 (F059): `shipped` is the one sha/PR field,
    an archived state without a hex `shipped.sha` and int `shipped.pr` is a finding, a
    truncated one a finding with a fix and no traceback; the histo `summary` null."""
    specs = _reconciled_closure(tmp_path, script)
    result = _run(script, "ship", "--sha", "beef123", "--pr", "261", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    archived = specs / "releases/_archive/0.5.0"
    assert not (specs / "releases/0.5.0").exists() and (archived / "rc-1/TASKS.md").is_file()
    assert _read(archived / "_RELEASE.json")["shipped"] == {"sha": "beef123", "pr": 261, "ts": ANY}
    records = load_owner("dd-bug-resolution", "_ledger").records(
        specs / "releases/_archive/releases_histo.jsonl"
    )
    assert [(r["id"], r["disposition"], r["summary"]) for r in records] == [
        ("0.5.0", "delivered", None)
    ]
    assert _run(script, "new", "0.5.1", "--specs", str(specs)).returncode == 0
    assert _run(script, "check", "--specs", str(specs)).returncode == 0
    state = _read(archived / "_RELEASE.json")
    (archived / "_RELEASE.json").write_text(json.dumps({**state, "shipped": None}), "utf-8")
    assert "no shipped" in _run(script, "check", "--specs", str(specs)).stdout
    (archived / "_RELEASE.json").write_text('{"schema": ', "utf-8")  # truncated
    truncated = _run(script, "check", "--json", "--specs", str(specs))
    assert truncated.returncode == 1 and "Traceback" not in truncated.stderr
    assert json.loads(truncated.stdout)[0]["path"] == "releases/_archive/0.5.0/_RELEASE.json"
    schema = json.loads(_SCHEMAS[0].read_text("utf-8"))
    assert schema["properties"]["phase"]["enum"] == ["DEFINITION", "IMPLEMENTATION", "CLOSURE"]
