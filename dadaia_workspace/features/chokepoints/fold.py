"""The push gate's remedy: re-commit the unpublished range of HEAD over what the gate listed."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dadaia_workspace.core import platform
from dadaia_workspace.core.exceptions import DadaiaError, GitSyncError
from dadaia_workspace.core.models.git_scan import ZERO_SHA
from dadaia_workspace.core.platform import act
from dadaia_workspace.features.chokepoints.branch_policy import Decision
from dadaia_workspace.features.chokepoints.push_gate import ObjectSource


def rewrite_unpublished(
    repo: Path,
    oldest: str,
    message: str | None,
    *,
    git: Any,
    reader: ObjectSource,
    decide: Callable[[Path, str], Decision],
) -> None:
    """Re-commit HEAD's unpublished range from *oldest* as one commit (two when RED `test(` commits
    and others mix), holding the tracked tree and every folded message. Runs only over edits or
    deletions of the paths ``decide(repo, held)`` lists; *message* is the subject and replaces just
    the messages the decision lists. Raises DadaiaError, changing nothing, when it cannot."""
    tip = git.git(repo, "rev-parse", "HEAD")
    try:
        sha = git.git(repo, "rev-parse", "--verify", f"{oldest}^{{commit}}")
    except GitSyncError:
        sha = oldest
    branch = git.current_branch(repo) or "HEAD"
    held = git.git(repo, "for-each-ref", "--format=%(objectname)", f"refs/remotes/origin/{branch}")
    decision = decide(repo, held or ZERO_SHA)
    changed = git.git(repo, "diff", "--name-status", "--no-renames", "-z", tip).split("\0")
    stray = sorted(
        p
        for st, p in zip(changed[::2], changed[1::2], strict=False)
        if st not in ("M", "D") or p not in decision.listed
    )
    if sha not in reader.unpublished(repo, tip):
        raise DadaiaError(
            f"cannot rewrite {oldest}: origin already holds it, or it is not in HEAD's history",
            act(
                "agent",
                "pass the oldest commit origin does not hold, as the push gate's fix line names it",
            ),
        )
    if not decision.listed:
        raise DadaiaError(
            "the push gate lists no denylist or canon finding in HEAD's unpublished range",
            act(
                "agent",
                "land the change through a worktree; this remedy answers a push gate refusal only",
            ),
        )
    if stray:
        raise DadaiaError(
            f"the working tree changes paths the gate did not list: {', '.join(stray)}",
            act("agent", "revert or unstage every path the gate did not list, and add no path"),
        )
    _fold(repo, sha, tip, decision, message, git)


def _fold(
    repo: Path, sha: str, tip: str, decision: Decision, message: str | None, git: Any
) -> None:
    """Re-commit *sha*..*tip* as a test commit of the paths RED `test(` commits touch, then the
    rest, or as one. *message* heads every commit holding a listed message, else the last. All is
    settled in a temporary index before the one ref move."""
    log = git.git(repo, "log", "--reverse", "--format=%H%x00%B%x1e", tip, "--not", f"{sha}^@")
    folded = [e.strip().partition("\0")[::2] for e in log.split("\x1e") if e.strip()]
    replaced = set(decision.messages) if message else set()
    every, red = {c for c, _ in folded}, {c for c, m in folded if m.startswith("test(")}
    try:
        parent = git.git(repo, "rev-parse", "--verify", f"{sha}^")
    except GitSyncError:
        parent = ""

    def names(*args: str) -> set[str]:
        return set(filter(None, git.git(repo, *args, "-z").split("\0")))

    with tempfile.TemporaryDirectory(prefix="fold-") as scratch:
        env = {"GIT_INDEX_FILE": str(Path(scratch) / "index")}
        git.git(repo, "read-tree", tip, env=env)
        git.git(repo, "add", "-u", env=env)
        final = git.git(repo, "write-tree", env=env)
        groups: list[tuple[set[str] | None, set[str]]] = [(None, every)]
        if parent and red and red != every:
            reds = set().union(*(names("diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", c) for c in red))  # fmt: skip
            net = names("diff", "--name-only", "--no-renames", parent, tip)
            groups = [(reds & net, red), (None, every - red)]
        heads = [bool(replaced & cs) for _, cs in groups]
        heads[-1] |= not any(heads)
        texts = [
            "\n\n".join(
                [message or "" if h else "", *(m for c, m in folded if c in cs - replaced)]
            ).strip()  # fmt: skip
            for (_, cs), h in zip(groups, heads, strict=True)
        ]
        if not all(texts):
            raise DadaiaError(
                f"a folded commit would carry no message ({sha[:12]}..{tip[:12]})",
                act(
                    "agent",
                    f"re-commit the range by hand with a message: `{platform.inline('git', '-C', str(repo), 'reset', '--soft', sha)}`, then commit it",  # fmt: skip
                ),
            )
        head = parent
        for (paths, _), text in zip(groups, texts, strict=True):
            tree = final
            if paths is not None:
                git.git(repo, "read-tree", parent, env=env)
                kept = git.git(repo, "ls-tree", "-rz", final, "--", *sorted(paths), env={"GIT_LITERAL_PATHSPECS": "1"})  # fmt: skip
                rows = {e.partition("\t")[2]: e.partition("\t")[0].split() for e in kept.split("\0") if e}  # fmt: skip
                entries = [f"{rows[p][0]} {rows[p][2]}\t{p}" if p in rows else f"0 {ZERO_SHA}\t{p}" for p in sorted(paths)]  # fmt: skip
                git.git(repo, "update-index", "-z", "--index-info", stdin="\0".join(entries) + "\0", env=env)  # fmt: skip
                tree = git.git(repo, "write-tree", env=env)
            head = git.git(repo, "commit-tree", tree, *(["-p", head] if head else []), "-m", text)
        git.git(repo, "update-ref", "HEAD", head, tip)
    git.git(repo, "reset", "-q")
