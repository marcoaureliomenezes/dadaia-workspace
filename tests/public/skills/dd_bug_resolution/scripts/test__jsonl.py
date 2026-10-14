"""A kernel file that is not UTF-8 and is not git-tracked in a user's workspace gets the fix
that clears it, never `git checkout`. Size: MEDIUM — the kernel runs as a child process over a
tmp copy.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_KERNEL = (
    Path(__file__).resolve().parents[5] / "dadaia_workspace/public/skills/dd-bug-resolution/scripts"
)
_PROBE = "import sys; sys.path.insert(0, sys.argv[1]); import _ledger, _refusal\n"


def _run(
    tmp_path: Path, body: str, env: dict[str, str] | None = None, damage: str = "", home: str = ""
) -> subprocess.CompletedProcess[str]:
    """*body* run over a tmp copy of the kernel under *home*, whose file *damage* first holds
    bytes that are not UTF-8."""
    kernel = tmp_path / home / "dd-bug-resolution" / "scripts"
    shutil.copytree(_KERNEL, kernel, ignore=shutil.ignore_patterns("__pycache__"))
    if damage:
        (kernel / damage).write_bytes(b"\xff\xfe")
    return subprocess.run(
        [sys.executable, "-c", _PROBE + body, str(kernel)],
        capture_output=True, check=False, text=True, env=env,
    )  # fmt: skip


def test_a_schema_that_is_not_utf8_is_reinstalled_not_restored_from_git(tmp_path: Path) -> None:
    body = (
        "try:\n    _ledger.load_schema('bug-record-v1')\n"
        "except _refusal.Refusal as refusal:\n    print(refusal.fix)\n"
    )
    done = _run(tmp_path, body, damage="schemas/bug-record-v1.schema.json")

    assert (
        done.stdout
        == "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument\n"
    )


def test_a_schema_of_the_installed_package_is_reinstalled_by_init(tmp_path: Path) -> None:
    body = (
        "try:\n    _ledger.load_schema('bug-record-v1')\n"
        "except _refusal.Refusal as refusal:\n    print(refusal.fix)\n"
    )
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    done = _run(tmp_path, body, damage="schemas/bug-record-v1.schema.json",
                home=".dadaia/.venv/lib/site-packages/dadaia_workspace/public/skills")  # fmt: skip

    assert done.stdout == f"uvx dadaia-workspace init {tmp_path.resolve()}\n"


def test_a_denylist_that_is_not_utf8_is_rewritten_not_restored_from_git(tmp_path: Path) -> None:
    denylist = tmp_path / "denylist.json"
    denylist.write_bytes(b"\xff\xfe")
    done = _run(tmp_path, "_ledger.terms(None)\n", {"DADAIA_PRIVACY_DENYLIST": str(denylist)})

    assert done.returncode == 1
    assert done.stderr == (
        f"[error] privacy denylist {denylist} is not one JSON object\n"
        f"fix: Agent action: rewrite {denylist} as one JSON object mapping each term to "
        "its reason\n"
    )
