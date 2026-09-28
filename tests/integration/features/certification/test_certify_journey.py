"""`certify` over a real journey: its `dadaia` and `git` children run for real.

Intent: CONTRACT — sa-reconcile-certify-skip-the-workspace-walk (T-050-50), and 0.4.7
FR4/T-047-16 (certify shells only verbs, flags and positionals the real CLI has: every
such check PASSes). Size: MEDIUM — only `init` (a venv build) and the harness binaries
get a stand-in answer.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.certification.service import certify
from dadaia_workspace.infrastructure.certification_process import (
    CertificationProcessResult,
    SubprocessCertificationProcess,
)


class _Children(SubprocessCertificationProcess):
    """`init` lays a bare workspace plus operator slop; `dadaia` and `git` run for real;
    any other binary answers nothing."""

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
            root = Path(argv[4])
            (root / ".dadaia" / "states").mkdir(parents=True)
            (root / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}')
            tools = root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
            tools.mkdir(parents=True)
            (tools / f"dadaia{PLATFORM.venv_exe_suffix}").write_text(
                "#!/bin/sh\ncat >/dev/null\n"
            )  # drains the pre-push pipe
            (tools / f"dadaia{PLATFORM.venv_exe_suffix}").chmod(0o755)
            (root / ".dadaia" / "nonsense").mkdir()
            (root / "notes.txt").write_text("operator notes", encoding="utf-8")
            return CertificationProcessResult(0, "", "")
        return super().run(argv, cwd=cwd, env=env, timeout=timeout)


@pytest.mark.slow(reason="a real certify journey: about a dozen dadaia children")
def test_certify_fails_naming_the_sandbox_slop(tmp_path: Path) -> None:
    """sa-reconcile-certify-skip-the-workspace-walk#B1: a certify sandbox seeded with
    `.dadaia/nonsense/` and a root `notes.txt` — the workspace section is judged and the
    result fails naming WS-dadaia-slop and WS-root-slop."""
    result = certify(tmp_path, _Children()).to_dict()

    checks = {c["name"]: c for c in result["checks"] if not c["name"].endswith("-probe")}
    failed = {name for name, c in checks.items() if c["status"] != "PASS"}
    assert result["ok"] is False
    assert failed == {"specs-scaffold-and-doctor", "context-specs-doctor"}, [
        checks[n]["detail"][-600:] for n in failed
    ]
    for name in failed:
        assert {"WS-dadaia-slop", "WS-root-slop"} <= set(checks[name]["detail"].split())
