"""Merged PreToolUse gate: root-whitelist -> venv-guard -> SDD gate, first-block-wins.

Reads the stdin envelope once; a policy that raises is treated as ALLOW (fail-open).
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from dadaia_workspace.hooks import _common, root_whitelist, sdd_gate, venv_guard

#: Ordered PreToolUse policies. First block wins; allow requires all.
_POLICIES: tuple[Callable[[dict[str, object]], str | None], ...] = (
    root_whitelist.evaluate_payload,
    venv_guard.evaluate_payload,
    sdd_gate.evaluate_payload,
)


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Run every PreToolUse policy in order; return the first block reason, else ``None``.

    Each policy is fail-open: a policy that raises is caught and treated as ALLOW so a
    single faulty policy can never deadlock the harness.
    """
    for policy in _POLICIES:
        try:
            block = policy(payload)
        except Exception:  # noqa: BLE001 — fail-open: a policy crash must never block
            block = None
        if block is not None:
            return block
    return None


def main() -> int:
    """Run the merged PreToolUse gate. Returns 0 always (block via the stdout envelope)."""
    reason = evaluate_payload(_common.claude_payload(_common.read_stdin_json()))
    if reason is not None:
        _common.emit_block(reason)
    else:
        _common.emit_allow()
    return 0


if __name__ == "__main__":
    sys.exit(main())
