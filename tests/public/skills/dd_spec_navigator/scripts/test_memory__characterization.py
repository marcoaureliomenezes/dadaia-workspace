"""Characterization net for the three public memory seams owned by CP1."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

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
_CATALOG = b"""{
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
_INDEX = b"""# Memory Catalog

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `memory.py catalog generate`; other
> sections of this file are preserved verbatim.

## Feature catalog

### platform

| slug | title | tldr |
|------|-------|------|
| `alpha` | Alpha | Alpha feature. |
"""


def _run(script: Path, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
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
    (product / "catalog.json").write_bytes(_CATALOG)
    source = repo / "src/alpha/core.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    _git(repo.parent, "init", "-q", str(repo))

    generated = _run(script, repo, "catalog", "generate", "--specs", str(repo / "specs"))

    assert (generated.returncode, generated.stdout, generated.stderr) == (
        0,
        "[ok] memory/product/catalog.json and memory/product/index.md written (1 feature)\n",
        "",
    )
    assert (product / "catalog.json").read_bytes() == _CATALOG
    assert (product / "index.md").read_bytes() == _INDEX

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
