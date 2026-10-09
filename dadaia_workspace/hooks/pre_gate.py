"""Merged PreToolUse gate: root-whitelist -> SDD gate, first block wins; a
policy that raises is treated as ALLOW (fail-open)."""

from __future__ import annotations

import sys
from collections.abc import Callable

from dadaia_workspace.hooks import _common, root_whitelist, sdd_gate

_POLICIES: tuple[Callable[[dict[str, object]], str | None], ...] = (
    root_whitelist.evaluate_payload,
    sdd_gate.evaluate_payload,
)


def evaluate_payload(payload: dict[str, object]) -> str | None:
    for policy in _POLICIES:
        try:
            block = policy(payload)
        except Exception:  # noqa: BLE001 — fail-open: a policy crash must never block
            block = None
        if block is not None:
            return block
    return None


def main() -> int:
    reason = evaluate_payload(_common.claude_payload(_common.read_stdin_json()))
    if reason is not None:
        _common.emit_block(reason)
    else:
        _common.emit_allow()
    return 0


if __name__ == "__main__":
    sys.exit(main())
