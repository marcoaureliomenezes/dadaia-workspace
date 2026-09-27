"""Intent: CONTRACT — sa-gate-blind-on-cursor-copilot-devin (0.5.0 WP-12, AC1.4, ADR 0054).

#B1: per harness, the native pre-tool payload for ``pip install requests`` gets the Claude
payload's verdict (deny) through the rendered wrapper. #B2: an allowed call prints no
explicit allow — the harness's own approval prompt stays in force.
Payload shapes are the vendor-documented ones cited in the bug record: Cursor
``beforeShellExecution`` ``{command}``, Copilot ``preToolUse`` ``{toolName, toolArgs}``
(toolArgs a JSON string). #B3: Devin, whose blocking file shape is not vendor-verified,
registers no gate event and declares every gated action ungated (ADR 0054).
Size: MEDIUM — runs the real generated ``sh`` wrapper (justified: the translation lives
in the wrapper, the seam the bug names).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    HOOK_DIALECTS,
    hook_wrapper_contents,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_PIP = "pip install requests"
_CASES = {
    "cursor": (
        {"hook_event_name": "beforeShellExecution", "command": _PIP, "cwd": "."},
        {"hook_event_name": "beforeShellExecution", "command": "ls -la", "cwd": "."},
        lambda out: out["permission"],
    ),
    "copilot": (
        {"toolName": "bash", "toolArgs": json.dumps({"command": _PIP})},
        {"toolName": "bash", "toolArgs": json.dumps({"command": "ls -la"})},
        lambda out: out["permissionDecision"],
    ),
}


def _gate(tmp_path: Path, harness: str, payload: dict[str, object]) -> str:
    bin_dir = tmp_path / ".dadaia" / ".venv" / "bin"
    hooks = tmp_path / ".dadaia" / "hooks"
    if not bin_dir.exists():
        bin_dir.mkdir(parents=True)
        (bin_dir / "python").symlink_to(sys.executable)
        hooks.mkdir(parents=True)
    wrapper = hooks / f"{harness}-pre-gate"
    wrapper.write_text(hook_wrapper_contents(HARNESS_RECORDS[harness])[wrapper.name])
    proc = subprocess.run(
        ["sh", str(wrapper)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
        check=True,
    )
    return proc.stdout.strip()


@pytest.mark.parametrize("harness", sorted(_CASES))
def test_b1_native_payload_gets_the_claude_verdict(tmp_path: Path, harness: str) -> None:
    deny_payload, _, decision = _CASES[harness]
    assert decision(json.loads(_gate(tmp_path, harness, deny_payload))) == "deny"


@pytest.mark.parametrize("harness", ["cursor", "copilot"])
def test_b2_an_allowed_call_prints_no_explicit_allow(tmp_path: Path, harness: str) -> None:
    _, allow_payload, _ = _CASES[harness]
    assert _gate(tmp_path, harness, allow_payload) == ""


def test_b3_devin_declares_its_gate_not_enforced() -> None:
    dialect = HOOK_DIALECTS[HARNESS_RECORDS["devin"].hooks]
    assert dialect.ungated == ("shell", "file-write")
    assert "devin-pre-gate" not in hook_wrapper_contents(HARNESS_RECORDS["devin"])
