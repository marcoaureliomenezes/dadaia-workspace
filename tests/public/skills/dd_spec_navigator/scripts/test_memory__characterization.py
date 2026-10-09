"""Characterization net for the three public memory seams owned by CP1."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM
from tests.fixtures.harness_env import suite_env
from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.slow(reason="runs the public scripts over a real Git repository")

_ATOM = """\
---
slug: alpha
title: Alpha
tldr: Alpha feature.
summary: Catalog fixture.
tags: [one, two]
sources:
  - src/alpha/**
---

# Alpha

Tracks [[beta]].
"""
_NOW = "2026-01-01T00:00:00Z"
_CATALOG_POSIX = b"""{
  "generated_at": "2026-01-01T00:00:00Z",
  "features": [
    {
      "rank": 1,
      "slug": "alpha",
      "title": "Alpha",
      "area": "platform",
      "tldr": "Alpha feature.",
      "summary": "Catalog fixture.",
      "path": "specs/memory/product/platform/alpha.md",
      "tags": [
        "one",
        "two"
      ],
      "token_estimate": 5,
      "depends_on": [
        "beta"
      ],
      "sources": [
        "src/alpha/**"
      ]
    }
  ]
}
"""
_CATALOG_WINDOWS = (
    b"{\r\n"
    b'  "generated_at": "2026-01-01T00:00:00Z",\r\n'
    b'  "features": [\r\n'
    b"    {\r\n"
    b'      "rank": 1,\r\n'
    b'      "slug": "alpha",\r\n'
    b'      "title": "Alpha",\r\n'
    b'      "area": "platform",\r\n'
    b'      "tldr": "Alpha feature.",\r\n'
    b'      "summary": "Catalog fixture.",\r\n'
    b'      "path": "specs/memory/product/platform/alpha.md",\r\n'
    b'      "tags": [\r\n'
    b'        "one",\r\n'
    b'        "two"\r\n'
    b"      ],\r\n"
    b'      "token_estimate": 5,\r\n'
    b'      "depends_on": [\r\n'
    b'        "beta"\r\n'
    b"      ],\r\n"
    b'      "sources": [\r\n'
    b'        "src/alpha/**"\r\n'
    b"      ]\r\n"
    b"    }\r\n"
    b"  ]\r\n"
    b"}\r\n"
)
_INDEX_POSIX = b"""# Memory Catalog

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `memory.py catalog generate`; other
> sections of this file are preserved verbatim.

## Feature catalog

### platform

| slug | title | tldr |
|------|-------|------|
| `alpha` | Alpha | Alpha feature. |
"""
_INDEX_WINDOWS = (
    b"# Memory Catalog\r\n"
    b"\r\n"
    b"> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.\r\n"
    b"> The catalog section below is refreshed by `memory.py catalog generate`; other\r\n"
    b"> sections of this file are preserved verbatim.\r\n"
    b"\r\n"
    b"## Feature catalog\r\n"
    b"\r\n"
    b"### platform\r\n"
    b"\r\n"
    b"| slug | title | tldr |\r\n"
    b"|------|-------|------|\r\n"
    b"| `alpha` | Alpha | Alpha feature. |\r\n"
)


def _run(
    script: Path, repo: Path, *args: str, fixed_clock: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(script), *args]
    if fixed_clock:
        bootstrap = (
            "import sys\nfrom datetime import datetime\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path(sys.argv.pop(1))))\n"
            "import memory\n"
            "class Clock:\n"
            " @staticmethod\n"
            f" def now(tz): return datetime.fromisoformat({_NOW!r}.replace('Z', '+00:00'))\n"
            "memory.cat.datetime = Clock\n"
            "raise SystemExit(memory.main(sys.argv[1:]))"
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


def test_catalog_generate_and_drift_pin_exit_output_and_artifacts(tmp_path: Path) -> None:
    script = (
        stage_skill_scripts("dd-spec-navigator", tmp_path / "skills/dd-spec-navigator/scripts")
        / "memory.py"
    )
    repo = tmp_path / "repo"
    product = repo / "specs/memory/product"
    atom = product / "platform/alpha.md"
    atom.parent.mkdir(parents=True)
    atom.write_text(_ATOM, encoding="utf-8")
    stale_catalog = b'{"generated_at":"2000-01-01T00:00:00Z","features":[]}\n'
    stale_index = b"# stale catalog fixture\n"
    (product / "catalog.json").write_bytes(stale_catalog)
    (product / "index.md").write_bytes(stale_index)
    expected_catalog = _CATALOG_WINDOWS if PLATFORM.windows else _CATALOG_POSIX
    expected_index = _INDEX_WINDOWS if PLATFORM.windows else _INDEX_POSIX
    assert stale_catalog != expected_catalog
    assert stale_index != expected_index
    source = repo / "src/alpha/core.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    _git(repo.parent, "init", "-q", str(repo))

    generated = _run(
        script,
        repo,
        "catalog",
        "generate",
        "--specs",
        str(repo / "specs"),
        fixed_clock=True,
    )

    assert (generated.returncode, generated.stdout, generated.stderr) == (
        0,
        "[ok] memory/product/catalog.json and memory/product/index.md written (1 feature)\n",
        "",
    )
    assert (product / "catalog.json").read_bytes() == expected_catalog
    assert (product / "index.md").read_bytes() == expected_index

    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    source.write_text("value = 2\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "change alpha")

    drifted = _run(
        script,
        repo,
        "drift",
        "--since",
        base,
        "--json",
        "--specs",
        str(repo / "specs"),
    )

    assert (drifted.returncode, drifted.stderr) == (1, "")
    assert json.loads(drifted.stdout) == {
        "since": base,
        "atoms": [
            {
                "slug": "alpha",
                "path": "specs/memory/product/platform/alpha.md",
                "matched": ["src/alpha/core.py"],
            }
        ],
        "uncovered": [],
    }
