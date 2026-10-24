"""Exit 0 when the named env secret is non-empty (and parses as JSON for codex); otherwise
print one ::error:: line naming the harness, the secret's name and the reseed doc. Never
prints a value."""

import json
import os
import sys


def _valid(harness, value):
    if not value:
        return False
    if harness != "codex":
        return True
    try:
        json.loads(value)
    except ValueError:
        return False
    return True


def main(harness, name):
    if _valid(harness, os.environ.get(name, "")):
        return 0
    print(f"::error::{harness} secret {name} is empty or invalid; see evals/RESEED.md")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
