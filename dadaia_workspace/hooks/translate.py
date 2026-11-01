"""Remap the pre-gate's deny envelope (JSON on STDIN) into the shape one harness reads.

``translate <exit_code>`` writes the reason to stderr and exits with that code;
``translate <decision_key> <reason_key>`` prints ``{decision_key: "deny", reason_key: reason}``.
Only a deny is answered: anything else, unparsable input included, is silence and exit 0.
"""

from __future__ import annotations

import json
import sys


def main(words: list[str], stdin: bytes) -> int:
    try:
        out = json.loads(stdin).get("hookSpecificOutput", {})
        if out.get("permissionDecision") != "deny":
            return 0
        reason = out.get("permissionDecisionReason", "")
    except (ValueError, AttributeError):
        return 0
    if len(words) == 1:
        from dadaia_workspace.core import platform

        platform.use_utf8_stdio()
        sys.stderr.write(f"{reason}\n")
        return int(words[0])
    print(json.dumps({words[0]: "deny", words[1]: reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdin.buffer.read()))
