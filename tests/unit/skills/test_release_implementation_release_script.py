"""Intent: CONTRACT — dd-release-implementation/scripts/release.py owns _RELEASE.json,
the candidate trio and releases_histo.jsonl (0.4.7 c7 T-047-66: the release ledger verbs
move into a stdlib skill script). Size: SMALL.

The script reads its two schemas from ``scripts/schemas/`` BESIDE itself — copies
`public stage` makes — so every test stages the folder exactly as stage does.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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
    staged = tmp_path / "skills" / "dd-release-implementation" / "scripts"
    (staged / "schemas").mkdir(parents=True)
    shutil.copytree(_PUBLIC / "skills" / "dd-spec-navigator" / "scripts",
                    tmp_path / "skills" / "dd-spec-navigator" / "scripts")  # fmt: skip
    for module in sorted(_SCRIPTS.glob("*.py")):
        shutil.copy2(module, staged / module.name)
    for schema in _SCHEMAS:
        shutil.copy2(schema, staged / "schemas" / schema.name)
    return staged / "release.py"


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
    """One live release directory with its trio and its state document."""
    release_dir = specs / "releases" / release_id
    release_dir.mkdir(parents=True, exist_ok=True)
    for name in _TRIO:
        body = tasks if name == "TASKS.md" else ""
        release_dir.joinpath(name).write_text(
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
    specs = _specs(tmp_path)
    result = _run(script, "new", "0.6.0", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    release_dir = specs / "releases" / "0.6.0"
    assert "**Status:** Draft" in (release_dir / "SPEC.md").read_text(encoding="utf-8")
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


def test_new_births_the_stacked_candidate_on_a_closed_live_release(
    script: Path, tmp_path: Path
) -> None:
    """The law's stacked candidate: `new <id>` on the live release in CLOSURE rewrites
    SPEC.md, deletes the closed PLAN/TASKS, resets phase to DEFINITION and leaves the
    milestones standing (`phase IMPLEMENTATION` restamps `defined`)."""
    specs = _specs(tmp_path)
    release_dir = _release(
        specs,
        "0.5.0",
        phase="CLOSURE",
        defined={"sha": "aaaaaaa", "ts": "2026-01-01T00:00:00Z"},
        implemented={"sha": "beef123", "ts": "2026-01-02T00:00:00Z"},
    )
    result = _run(script, "new", "0.5.0", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    assert "**Status:** Draft" in (release_dir / "SPEC.md").read_text(encoding="utf-8")
    assert not (release_dir / "PLAN.md").exists()
    assert not (release_dir / "TASKS.md").exists()
    state = _read(release_dir / "_RELEASE.json")
    assert state["phase"] == "DEFINITION"
    assert state["defined"] == {"sha": "aaaaaaa", "ts": "2026-01-01T00:00:00Z"}
    assert state["implemented"] == {"sha": "beef123", "ts": "2026-01-02T00:00:00Z"}
    notes = [entry["text"] for entry in state["log"]]
    assert notes == ["Candidate born on 0.5.0 (prior candidate closed at beef123)"]


def test_new_refuses_the_same_id_while_its_candidate_is_open(script: Path, tmp_path: Path) -> None:
    """A candidate is stacked only on a CLOSURE state: mid-IMPLEMENTATION the live trio
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


def test_phase_closure_records_the_merged_release_pr(script: Path, tmp_path: Path) -> None:
    """T-047-90: the number `archive --pr <n>` carried moves to the one living verb.
    Promote leaves a number in the log, not a moved directory."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    result = _run(
        script, "phase", "CLOSURE", "--sha", "beef123", "--pr", "261", "--specs", str(specs)
    )
    assert result.returncode == 0, result.stderr
    state = _read(specs / "releases" / "0.5.0" / "_RELEASE.json")
    notes = [entry["text"] for entry in state["log"] if entry["kind"] == "note"]
    assert any("#261" in text for text in notes), notes


def test_phase_closure_without_a_pr_is_still_accepted(script: Path, tmp_path: Path) -> None:
    """`--pr` is optional: a candidate that closes without promoting names no PR."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    result = _run(script, "phase", "CLOSURE", "--sha", "beef123", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    state = _read(specs / "releases" / "0.5.0" / "_RELEASE.json")
    notes = [entry["text"] for entry in state["log"] if entry["kind"] == "note"]
    assert not any("#" in text for text in notes), notes


def test_phase_refuses_a_non_numeric_pr(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    result = _run(
        script, "phase", "CLOSURE", "--sha", "beef123", "--pr", "zero", "--specs", str(specs)
    )
    assert result.returncode != 0


def test_phase_refuses_an_out_of_order_transition(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    result = _run(script, "phase", "CLOSURE", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 1
    assert "fix: " in result.stderr
    assert _read(specs / "releases" / "0.5.0" / "_RELEASE.json")["phase"] == "DEFINITION"


def test_phase_implementation_refuses_an_unapproved_trio(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    release_dir = _release(specs, "0.5.0")
    (release_dir / "PLAN.md").write_text("# PLAN.md\n\n**Status:** Draft\n", encoding="utf-8")
    result = _run(script, "phase", "IMPLEMENTATION", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 1
    assert "PLAN.md" in result.stderr


def test_phase_closure_refuses_an_open_task(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION", tasks="- [ ] T-1 — open\n")
    result = _run(script, "phase", "CLOSURE", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 1
    assert "T-1" in result.stderr


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


def test_check_reports_a_live_directory_carrying_the_archived_phase(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="ARCHIVED")
    result = _run(script, "check", "--specs", str(specs))
    assert result.returncode == 1
    assert "LEDGER-RELEASE-SCHEMA error" in result.stdout


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


@pytest.mark.parametrize(
    ("name", "argv"),
    [
        ("bad-sha", ("phase", "IMPLEMENTATION", "--sha", "nope")),
        ("out-of-order", ("phase", "CLOSURE", "--sha", "abc1234")),
        ("unknown-phase", ("phase", "DEFINITION", "--sha", "abc1234")),
        ("second-live", ("new", "0.6.0")),
    ],
)
def test_every_refusal_carries_exactly_one_runnable_fix(
    script: Path, tmp_path: Path, name: str, argv: tuple[str, ...]
) -> None:
    """The block contract the retired CLI verbs used to carry (`test_every_block_carries
    _a_fix.py`): one `fix:` line, naming one executable command, on every refusal."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="DEFINITION")
    result = _run(script, *argv, "--specs", str(specs))
    assert result.returncode == 1, result.stdout
    fixes = [line for line in result.stderr.splitlines() if line.startswith("fix: ")]
    assert len(fixes) == 1, f"{name}: {result.stderr}"
    assert fixes[0].removeprefix("fix: ").strip(), name


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


def test_memory_refuses_any_phase_but_closure(script: Path, tmp_path: Path) -> None:
    root, specs, _ = _memory_repo(tmp_path, script)
    state = specs / "releases" / "0.5.0" / "_RELEASE.json"
    document = _read(state)
    document["phase"] = "IMPLEMENTATION"
    state.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    result = _memory(script, root, specs, reviewed="alpha", changed="")

    assert result.returncode == 1
    assert "CLOSURE" in result.stderr
