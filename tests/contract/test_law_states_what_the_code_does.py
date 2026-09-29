"""Intent: CONTRACT — sa-text-restates-rules-the-code-contradicts: a law or docstring
sentence that restates a rule states what the code does, or cites the code instead.
Size: SMALL — text reads, one AST walk and in-process gate calls.
"""

from __future__ import annotations

import ast
import configparser
import re
from pathlib import Path

import pytest

from dadaia_workspace.hooks import _common
from tests.contract.test_slop_ratchets import _V34_CEILINGS

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_PKG = _REPO / "dadaia_workspace"
_MAP = _PKG / "public" / "data" / "AGENTS.md"


def test_the_map_states_what_the_gate_judges() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.1 (first-token rows: unit test_venv_guard)
    and bug gate-law-claims-out-of-scope-writes-blocked-but-bash-is-never-judged: only file
    tools are judged as writes, never Bash, and NotebookEdit creates no root entry."""
    tools = ("Write", "Edit", "MultiEdit", "apply_patch")
    assert {*tools, "NotebookEdit", "write_file", "edit_file"} == _common.WRITE_TOOLS
    line = next(ln for ln in _MAP.read_text("utf-8").splitlines() if "One PreToolUse gate" in ln)
    assert "first token is `dadaia`, `pip`/`pip3` or `python -m dadaia_workspace`" in line
    assert "file-tool write (`" + "`, `".join(tools) + "`) creating a new" in line
    assert "a file-tool write (those or `NotebookEdit`) that is PROTECTED" in line
    assert "a Bash write (`sed -i`, `rm`, `mkdir`, a redirect) is never judged" in line


_SESSION_NAMES = ("DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID",
                  "CODEX_THREAD_ID", "session_id")  # fmt: skip


def test_no_docstring_restates_the_session_id_order() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.2: the precedence is
    resolve_session_id's alone; no other module spells a session-id chain."""
    chains = []
    for path in sorted(_PKG.rglob("*.py")):
        if path.name == "invocation.py" and path.parent.name == "core":
            continue
        for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
            if re.search(r"→|->", line) and sum(name in line for name in _SESSION_NAMES) >= 2:
                chains.append(f"{path.relative_to(_REPO)}:{number}")
    assert chains == []


def test_the_release_law_states_the_trio_byte_ceilings() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.3: the law states KiB with the byte
    counts the V34 ratchet enforces."""
    law = (_PKG / "public" / "scaffold" / "releases" / "AGENTS.md").read_text("utf-8")
    assert _V34_CEILINGS == {"SPEC.md": 24576, "TASKS.md": 12288}
    assert "SPEC.md fits 24 KiB (24576 bytes) and TASKS.md 12 KiB (12288 bytes)" in law


def test_the_bind_resolution_contract_covers_every_verb_module() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.4: every cli/commands/* module is a
    source of the bind-resolution-seam contract, so a direct core.invocation import in any
    verb (harness, reconcile, capabilities, certify included) breaks lint-imports."""
    config = configparser.ConfigParser()
    config.read(_REPO / "setup.cfg", encoding="utf-8")
    sources = config["importlinter:contract:bind-resolution-seam-is-a-single-home"]
    modules = sources["source_modules"].split()
    verbs = sorted((_PKG / "cli" / "commands").glob("[!_]*.py"))
    uncovered = [
        v.stem for v in verbs
        if not any(f"dadaia_workspace.cli.commands.{v.stem}".startswith(m) for m in modules)
    ]  # fmt: skip
    assert verbs and uncovered == []


def test_os_name_is_read_only_through_the_platform_seam() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.5: no `os.name` read in the package
    outside core/platform (python_env branches on PLATFORM). Stdlib skill scripts under
    public/ cannot import core and are out of this ratchet."""
    reads = [
        f"{path.relative_to(_REPO)}:{node.lineno}"
        for path in sorted(_PKG.rglob("*.py"))
        if "public" not in path.relative_to(_PKG).parts
        for node in ast.walk(ast.parse(path.read_text("utf-8")))
        if isinstance(node, ast.Attribute) and node.attr == "name"
        and isinstance(node.value, ast.Name) and node.value.id == "os"
    ]  # fmt: skip
    assert reads == []


def test_the_work_order_has_one_home_the_map() -> None:
    """sa-implementation-adds-before-it-deletes: the map §1 states the order once; no skill."""
    rule = "Every change minimizes code and tests: DELETE → REBUILD → UPDATE → KEEP → ADD last;"
    skills = [p.read_text("utf-8") for p in (_PKG / "public" / "skills").rglob("*.md")]
    assert _MAP.read_text("utf-8").count(rule) == 1 and not [
        t for t in skills if "REBUILD → UPDATE" in t
    ]
