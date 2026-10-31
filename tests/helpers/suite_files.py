"""The one suite enumerator: git-tracked paths, so a scratch file another process leaves
in the checkout is never read."""

from pathlib import Path

from tests.helpers.oslib import run


def tracked(root: Path, *spec: str) -> list[Path]:
    """Sorted absolute paths of the files git tracks under *spec* in the repo at *root*."""
    out = run(["git", "-C", str(root), "ls-files", "-z", "--", *spec], check=True).stdout
    return sorted(root / p for p in out.split("\0") if p)
