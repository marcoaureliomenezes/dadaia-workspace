"""`certify` over a real journey: its `dadaia` and `git` children run for real.

T-050-50; 0.4.7 FR4/T-047-16 (every verb certify shells exists: its
check PASSes). Size: MEDIUM — only `init` (a venv build) and harness binaries are faked.
"""

from __future__ import annotations

import os
import site
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from dadaia_workspace.features.certification.service import certify
from dadaia_workspace.infrastructure.certification_process import (
    CertificationProcessResult,
    SubprocessCertificationProcess,
)
from tests.fixtures.stores import own_venv_python, own_venv_workspace


class _Children(SubprocessCertificationProcess):
    """`init` lays a workspace plus slop; `dadaia` runs on *python*, `git` for real."""

    def __init__(self, python: Path) -> None:
        self._python = str(python)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CertificationProcessResult:
        if argv[0] not in ("git", sys.executable):
            return CertificationProcessResult(1, "", "not exercised")
        if list(argv[3:4]) == ["init"]:
            (own_venv_workspace(Path(argv[4])) / ".dadaia" / "nonsense").mkdir()
            (Path(argv[4]) / "notes.txt").write_text("operator notes", encoding="utf-8")
            return CertificationProcessResult(0, "", "")
        path = os.pathsep.join([str((env or {}).get("PYTHONPATH")), *site.getsitepackages()])
        argv = [self._python if argv[0] == sys.executable else argv[0], *argv[1:]]
        return super().run(argv, cwd=cwd, env={**(env or {}), "PYTHONPATH": path}, timeout=timeout)


@pytest.mark.slow(reason="a real certify journey: about a dozen dadaia children")
def test_certify_fails_naming_the_sandbox_slop(tmp_path: Path) -> None:
    """sa-reconcile-certify-skip-the-workspace-walk#B1: a certify sandbox seeded with
    `.dadaia/nonsense/` and a root `notes.txt` — the workspace section is judged and the
    result fails naming WS-dadaia-slop and WS-root-slop. sa-certify-children-resolve-the-
    live-workspace: run from a "live" workspace owning the children's venv, every child
    acts on the sandbox only — the live registry is byte-identical, no session is left."""
    live = own_venv_workspace(tmp_path / "live")
    result = certify(live, _Children(own_venv_python(live))).to_dict()

    assert (live / ".dadaia" / "states" / "spec_contexts.json").read_bytes() == b'{"contexts": []}'
    assert sorted(p.name for p in (live / ".dadaia").iterdir()) == [".venv", "states", "tmp"]
    checks = {c["name"]: c for c in result["checks"] if not c["name"].endswith("-probe")}
    failed = {name for name, c in checks.items() if c["status"] != "PASS"}
    assert result["ok"] is False
    assert failed == {"specs-scaffold-and-doctor", "context-specs-doctor"}, checks
    for name in failed:
        assert {"WS-dadaia-slop", "WS-root-slop"} <= set(checks[name]["detail"].split())
