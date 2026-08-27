"""FR9 — hooks de-slopped to the publication boundary (v0.5.0 D9).

Three EXECUTED-PATH fixtures, at CONTRACT tier, that replace the two files this FR
deletes: ``tests/integration/test_precommit_backlog_scoping.py`` (imported
``_run_backlog_doctor_gate`` directly — the symbol this FR deletes, so the import
would fail) and its LARGE-tier e2e companion
``tests/e2e/features/test_backlog_precommit.py`` (its entire premise — pre-commit
*blocking* a bad stage — is deleted by this FR; rewriting either would be a
change-detector test of the new advisory behaviour, the class
``dadaia-test-stewardship`` §B prohibits). Verdict: `qa-engineer`, SPEC FR9 "Tests:"
line / A9.3 — both files DELETE, replaced here.

Each test below drives the REAL shipped shell script through ``bash`` (never asserts
on the script's *text* — SPEC A9.1/A9.2 both say "the executed path, not the script's
text"):

* :func:`test_pre_commit_exits_0_on_a_staged_set_backlog_doctor_would_reject` — A9.1:
  ``pre-commit-presence-gate.sh`` exits 0 on a staged set the (now-deleted) backlog
  doctor block would have rejected.
* :func:`test_failing_preflight_no_longer_blocks_the_push` — A9.2 companion: a
  simulated failing ``ci preflight`` no longer blocks a push through
  ``pre-push-ci-gate.sh``, because the hook no longer invokes that verb at all.
* :func:`test_unresolvable_runner_still_refuses_the_push` — A9.2: with no resolvable
  dadaia runner anywhere, ``pre-push-ci-gate.sh`` REFUSES the push (exit 1), never
  silently skips it — the fail-closed publication boundary the pre-commit hook does
  NOT share (pre-commit is advisory-only, D9).

The other two refusals A9.2 names — an invalid branch name and a denylist hit — are
already proven at the real CLI boundary by
``tests/e2e/test_push_gate_check.py::test_develop_push_is_blocked_naming_the_pr_path``
and ``tests/e2e/test_push_denylist_journey.py::
test_planted_term_refused_then_clean_push_after_amend`` respectively; this module adds
no duplicate coverage of those two.

Intent: CONTRACT — v0.5.0 A9.1, A9.2, A9.3
Owner: software-engineer
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(
        sys.platform != "linux",
        reason="pre-commit-presence-gate.sh / pre-push-ci-gate.sh are bash contracts (Linux only)",
    ),
]

_SCRIPTS_DIR = Path(dadaia_workspace.__file__).parent / "public" / "scripts"
_PRE_COMMIT_SCRIPT = _SCRIPTS_DIR / "pre-commit-presence-gate.sh"
_PRE_PUSH_SCRIPT = _SCRIPTS_DIR / "pre-push-ci-gate.sh"

_BASH = shutil.which("bash") or "/usr/bin/bash"
_DEADLINE = 30.0
_ZERO = "0" * 40

#: bug self-scan-baseline-drift-t05018-hooks-publication-boundary-fixture: the
#: prior email-shaped placeholder used a real ccTLD, never one of
#: privacy_baseline.json's RFC-2606-reserved-domain exclusions
#: (.invalid/.test/.example/.localhost) -- one placeholder, reused at both synthetic
#: git-identity call sites in this module, rather than two independently-typed
#: literals drifting apart again.
_SYNTHETIC_GIT_EMAIL = "test@example.invalid"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_dadaia_forwarder(path: Path) -> None:
    """A `dadaia` stub that forwards every verb into the REAL CLI through THIS
    interpreter — same technique as tests/e2e/test_push_denylist_journey.py."""
    _write_executable(
        path,
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'exec "{sys.executable}" -m dadaia_workspace.cli.main "$@"\n',
    )


def _init_context_repo(workspace: Path, slug: str) -> Path:
    """A real git repo at <workspace>/repos/<slug>, laid out as a Spec Context repo
    (the shape `dadaia ci pre-commit-check` resolves the workspace + specs/ against)."""
    (workspace / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    repo = workspace / "repos" / slug
    (repo / "specs" / "backlog").mkdir(parents=True)
    (repo / "specs" / "memory" / "product").mkdir(parents=True)
    (repo / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (repo / "dadaia_workspace").mkdir()
    (repo / "dadaia_workspace" / "m.py").write_text("class Widget:\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", _SYNTHETIC_GIT_EMAIL], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo


def _plant_backlog_doctor_violation(repo: Path) -> None:
    """A BL-SCHEMA violation (an unresolved subject symbol) — the exact shape the
    deleted integration test used to prove the (now-removed) blocking gate against."""
    (repo / "specs" / "backlog" / "BACKLOG.md").write_text(
        "## ACTIVE\n\n"
        "### bad-item\n"
        "- **Title:** Bad\n"
        "- **Opened:** 2026-08-15\n"
        "- **Status:** candidate\n"
        "- **Description:** references a phantom symbol.\n"
        "- **Provenance:** operator request\n"
        "- **Intents:**\n```yaml\n"
        "- subject:\n    kind: code\n    ref: dadaia_workspace/m.py#Ghost\n  change: x\n"
        "```\n\n"
        "## LEDGER\n",
        encoding="utf-8",
    )


def _hook_env(workspace: Path, *, dadaia_bin: Path | None = None) -> dict[str, str]:
    """A harness-FREE env mirroring the real installed hook's child env."""
    env = dict(os.environ)
    for bad in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID", "DADAIA_MODE"):
        env.pop(bad, None)
    env["WORKSPACE_ROOT"] = str(workspace)
    env.pop("DADAIA_SESSION_ID", None)
    if dadaia_bin is not None:
        env["DADAIA_BIN"] = str(dadaia_bin)
    else:
        env.pop("DADAIA_BIN", None)
    return env


def test_pre_commit_exits_0_on_a_staged_set_backlog_doctor_would_reject(
    tmp_path: Path,
) -> None:
    """A9.1: the real ``pre-commit-presence-gate.sh`` exits 0 on a staged set the
    (now-deleted) backlog doctor block would have rejected — advisory-only, always
    exit 0, never the script's text."""
    workspace = tmp_path
    repo = _init_context_repo(workspace, "demo-ctx")
    _plant_backlog_doctor_violation(repo)
    subprocess.run(["git", "add", "specs/backlog/BACKLOG.md"], cwd=repo, check=True)

    stub = workspace / "dadaia-stub.sh"
    _write_dadaia_forwarder(stub)

    result = subprocess.run(
        [_BASH, str(_PRE_COMMIT_SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=_hook_env(workspace, dadaia_bin=stub),
        timeout=_DEADLINE,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _write_preflight_fails_stub(path: Path) -> None:
    """``ci preflight`` fails loudly (exit 1); ``ci push-gate-check`` drains stdin and
    succeeds. If the hook still invoked ``ci preflight``, ``set -euo pipefail`` would
    abort the script on that failure — asserting the overall exit code proves,
    EXECUTED, that the hook no longer reaches that branch at all."""
    _write_executable(
        path,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [ "${1:-}" = "ci" ] && [ "${2:-}" = "preflight" ]; then\n'
        '    echo "[stub] simulated preflight FAILURE" >&2\n'
        "    exit 1\n"
        "fi\n"
        'if [ "${1:-}" = "ci" ] && [ "${2:-}" = "push-gate-check" ]; then\n'
        "    cat >/dev/null\n"
        "    exit 0\n"
        "fi\n"
        'echo "[stub] unexpected verb: $*" >&2\n'
        "exit 1\n",
    )


def test_failing_preflight_no_longer_blocks_the_push(tmp_path: Path) -> None:
    """A9.2 companion: a failing local ``ci preflight`` no longer blocks a push
    through ``pre-push-ci-gate.sh`` — the hook does not invoke that verb any more."""
    workspace = tmp_path
    repo = workspace / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    stub = workspace / "dadaia-stub.sh"
    _write_preflight_fails_stub(stub)

    stdin_text = f"refs/heads/feature/0.0.1 {'a' * 40} refs/heads/feature/0.0.1 {_ZERO}\n"
    result = subprocess.run(
        [_BASH, str(_PRE_PUSH_SCRIPT)],
        cwd=repo,
        input=stdin_text,
        capture_output=True,
        text=True,
        env=_hook_env(workspace, dadaia_bin=stub),
        timeout=_DEADLINE,
    )
    out = result.stdout + result.stderr
    assert result.returncode == 0, out
    assert "simulated preflight FAILURE" not in out, out


def test_unresolvable_runner_still_refuses_the_push(tmp_path: Path) -> None:
    """A9.2: with no ``$DADAIA_BIN``, no workspace venv, no poetry, and no repo-local
    venv, ``pre-push-ci-gate.sh`` REFUSES the push (exit 1) — never silently skipped.
    Pre-push keeps its fail-closed runner resolution; only pre-commit became
    unconditionally exit 0 (D9)."""
    workspace = tmp_path
    repo = workspace / "isolated-repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", _SYNTHETIC_GIT_EMAIL], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    # A fully controlled PATH with no poetry/dadaia reachable — same isolation
    # technique as tests/unit/public/test_pre_push_gate_venv_probe.py.
    env = {"PATH": "/usr/bin:/bin", "HOME": str(repo)}

    stdin_text = f"refs/heads/feature/0.0.1 {'a' * 40} refs/heads/feature/0.0.1 {_ZERO}\n"
    result = subprocess.run(
        [_BASH, str(_PRE_PUSH_SCRIPT)],
        cwd=repo,
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=_DEADLINE,
    )
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "could not locate the dadaia runner" in out, out
