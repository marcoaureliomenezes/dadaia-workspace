"""Characterization net for the three public ``release.py`` seams owned by CP3."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM
from tests.fixtures.harness_env import suite_env
from tests.helpers.release_state import PLAN
from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = [
    pytest.mark.medium,
    pytest.mark.slow(reason="runs three public-script subprocesses over a real Git fixture"),
]

_NOW = "2026-10-09T12:00:00Z"
_MILESTONE = "2026-10-09T10:00:00Z"
_SHIP_SHA = "beef123"


def _bytes(document: dict[str, object]) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            *args,
        ],
        cwd=repo,
        env=suite_env(os.environ, repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _run(
    script: Path, repo: Path, *args: str, fixed_clock: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(script), *args]
    if fixed_clock:
        bootstrap = (
            "import sys; from pathlib import Path; "
            "sys.path.insert(0, str(Path(sys.argv.pop(1)))); "
            "import release; "
            f"release.utc_now = lambda: {_NOW!r}; "
            "raise SystemExit(release.main(sys.argv[1:]))"
        )
        command = [sys.executable, "-c", bootstrap, str(script.parent), *args]
    return subprocess.run(
        command,
        cwd=repo,
        env=suite_env(os.environ, repo),
        capture_output=True,
        text=True,
        check=False,
    )


def test_drift_memory_and_ship_pin_outputs_and_release_bytes(tmp_path: Path) -> None:
    for skill in ("dd-spec-navigator", "dd-gitflow-default", "dd-bug-resolution"):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    script = (
        stage_skill_scripts(
            "dd-release-implementation",
            tmp_path / "skills/dd-release-implementation/scripts",
        )
        / "release.py"
    )
    repo = tmp_path / "repo"
    specs = repo / "specs"
    release_dir = specs / "releases/0.5.0"
    candidate = release_dir / "rc-1"
    candidate.mkdir(parents=True)
    (candidate / "SPEC.md").write_text(
        "# SPEC\n\n**Status:** Approved\n\n**Origin:** operator-demand\n\n## Bug window review\n",
        encoding="utf-8",
    )
    (candidate / "PLAN.md").write_text(
        f"# PLAN\n\n**Status:** Approved\n\n{PLAN}", encoding="utf-8"
    )
    archive = specs / "releases/_archive"
    archive.mkdir()
    history = archive / "releases_histo.jsonl"
    history.write_bytes(b"")
    atom = specs / "memory/product/platform/alpha.md"
    atom.parent.mkdir(parents=True)
    atom.write_text(
        "---\nslug: alpha\ntitle: Alpha\ntldr: Alpha\nsummary: Alpha\n"
        "tags: [alpha]\nsources:\n  - src/alpha/**\n---\n\n# Alpha\n",
        encoding="utf-8",
    )
    (specs / "memory/product/catalog.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-10-09T09:00:00Z",
                "features": [
                    {
                        "slug": "alpha",
                        "path": "specs/memory/product/platform/alpha.md",
                        "sources": ["src/alpha/**"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    source = repo / "src/alpha/core.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")

    initial = {
        "schema": "release-state-v1",
        "release": "0.5.0",
        "phase": "CLOSURE",
        "defined": {"sha": base, "ts": _MILESTONE},
        "implemented": {"sha": base, "ts": _MILESTONE},
        "shipped": None,
        "log": [],
    }
    state = release_dir / "_RELEASE.json"
    state.write_bytes(_bytes(initial))

    drift = _run(script, repo, "drift", "--json", "--specs", str(specs))
    drift_report = {"since": base, "atoms": [], "uncovered": []}
    assert (drift.returncode, drift.stdout, drift.stderr) == (
        0,
        json.dumps(drift_report, indent=2) + "\n",
        "",
    )
    assert state.read_bytes() == _bytes(initial)

    memory_entry = {
        "ts": _NOW,
        "agent": "release.py memory",
        "kind": "memory",
        "text": f"Memory reconciled over {base}..{base[:12]}: 0 reviewed, 0 changed.",
        "since": base,
        "until": base,
        "reviewed": [],
        "changed": [],
    }
    remembered = {**initial, "log": [memory_entry]}
    memory = _run(
        script,
        repo,
        "memory",
        "--reviewed=",
        "--changed=",
        "--specs",
        str(specs),
        fixed_clock=True,
    )
    assert (memory.returncode, memory.stdout, memory.stderr) == (
        0,
        f"[ok] release 0.5.0 log <- kind memory {base}..{base[:12]} ({_NOW})\n",
        "",
    )
    assert state.read_bytes() == _bytes(remembered)

    shipped = {
        **remembered,
        "shipped": {"sha": _SHIP_SHA, "pr": 42, "ts": _NOW},
    }
    ship = _run(
        script,
        repo,
        "ship",
        "--sha",
        _SHIP_SHA,
        "--pr",
        "42",
        "--specs",
        str(specs),
        fixed_clock=True,
    )
    assert (ship.returncode, ship.stdout, ship.stderr) == (
        0,
        f"[ok] release 0.5.0 shipped at {_SHIP_SHA} (PR #42)\n",
        "",
    )
    archived = archive / "0.5.0"
    assert not release_dir.exists()
    assert (archived / "_RELEASE.json").read_bytes() == _bytes(shipped)
    expected_history = (
        (
            b'{"id": "0.5.0", "ts": "2026-10-09T12:00:00Z", '
            b'"disposition": "delivered", "release": "0.5.0", "reason": null, '
            b'"entry": null, "summary": null}\r\n'
        )
        if PLATFORM.windows
        else (
            b'{"id": "0.5.0", "ts": "2026-10-09T12:00:00Z", '
            b'"disposition": "delivered", "release": "0.5.0", "reason": null, '
            b'"entry": null, "summary": null}\n'
        )
    )
    assert history.read_bytes() == expected_history
