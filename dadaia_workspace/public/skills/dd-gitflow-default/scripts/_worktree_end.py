#!/usr/bin/env python3
"""`worktree.py merge|clean`: end one canonical worktree — fast-forward it into the work
branch, or drop an empty one — never with `--force` or `-D`, re-runnable after a stop."""

from __future__ import annotations

import fnmatch
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

from _release_schema import MARK_RE, MARKS  # noqa: E402
from _worktree_git import cli, cli_line, flow_for, git, git_line, ours, quote, script  # noqa: E402
from _worktree_kinds import _NAME_RE, REPLAY, SCRIPT, Refusal, allows, kind_holding  # noqa: E402

REVIEWER = "dd-code-reviewer"


def _target(root: Path, path: str) -> tuple[Path, Path, str, str]:
    """(repo, tree, name, work branch) of `worktrees/<repo>/<name>`; the tree may be gone."""
    tree = Path(path).resolve()
    parts = (
        tree.relative_to(root / "worktrees").parts
        if tree.is_relative_to(root / "worktrees")
        else ()
    )
    match = _NAME_RE.match(parts[1]) if len(parts) == 2 else None
    if match is None:
        raise Refusal(
            f"{path} is not a worktrees/<repo>/<M.m.p><l>-<kind> path", f"{script(SCRIPT)} list"
        )
    repo = root / "repos" / parts[0]
    return repo, tree, parts[1], f"{flow_for(root, repo)['work']}{match['v']}"


def _refuse_dirty(tree: Path) -> None:
    if git(tree, "status", "--porcelain").strip():
        raise Refusal(
            f"{tree} has uncommitted changes",
            f"Operator action: commit them in the kind's commit shape (`{git_line(tree, 'add', '-A')}`"
            f" and `{git_line(tree, 'commit')}`) or remove them (`{git_line(tree, 'clean', '-fd')}`"
            f" and `{git_line(tree, 'restore', '-SW', '.')}`) — never a stash every worktree shares",
        )


def _kept(tree: Path, verb: str, keep: list[str], drop: bool) -> list[str]:
    """The ignored files to copy into the repo; refuses while one is neither kept nor dropped."""
    ignored = [  # -z: a name with a blank arrives verbatim, never C-quoted
        line[3:].rstrip("/")
        for line in git(tree, "status", "--porcelain", "-z", "--ignored").split("\0")
        if line.startswith("!! ")
    ]
    # disposable without asking (ADR 0130): a tool cache directory or a *.pyc
    precious = [
        p
        for p in ignored
        if not (p.endswith(".pyc") or any("cache" in part for part in Path(p).parts))
    ]
    left = [p for p in precious if p not in keep]
    if left and not drop:
        raise Refusal(
            f"ignored files would be lost: {', '.join(left)}",
            f"{script(SCRIPT)} {verb} {quote(str(tree))} --keep {' '.join(map(quote, precious))}",
        )
    return [p for p in precious if p in keep]


def _remove(repo: Path, tree: Path, name: str, kept: list[str]) -> None:
    for rel in kept:
        source, target = tree / rel, repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
    git(repo, "worktree", "unlock", str(tree), check=False)
    git(repo, "worktree", "remove", str(tree))
    git(repo, "branch", "-d", f"wt/{name}")


def _undo(tree: Path, work: str, rel: str) -> str:
    """The one act putting *rel* back to the work branch's version, absent included."""
    return (f"Operator action: revert {rel} to {work} in one commit — "
            f"`{git_line(tree, 'restore', '-s', work, '-SW', '--', rel)}` and `{git_line(tree, 'commit')}`")  # fmt: skip


def _check_allowed(tree: Path, work: str, name: str) -> None:
    kind = _NAME_RE.match(name)["k"]  # type: ignore[index]
    for rel in git(tree, "diff", "--name-only", f"{work}...HEAD").splitlines():
        if not allows(kind, rel):
            owner = kind_holding(rel)
            raise Refusal(
                f"{rel} is outside the {kind} allowed set"
                + (f"; it belongs in a {owner} worktree" if owner else ""),
                _undo(tree, work, rel),
            )


def _bare(line: str) -> str:
    return MARK_RE.sub(r"\1 \3", line)


def _rank(line: str) -> int:
    return MARKS.index(m[2]) if (m := MARK_RE.match(line)) else -1


def _replayed(tree: Path, rel: str) -> list[str] | None:
    """The work side of *rel* with each marker the worktree flipped carried onto its one
    equal line at the most advanced state (` ` < `-` < `x`, ADR 0111); ``None`` when the
    worktree changed more than markers, a stage is missing, or a line has no unique match."""
    try:
        base, work, mine = (git(tree, "show", f":{n}:{rel}").splitlines() for n in "123")
    except RuntimeError:  # modify/delete or add/add
        return None
    bare = [_bare(line) for line in work]
    if [_bare(line) for line in base] != [_bare(line) for line in mine]:
        return None
    for old, new in zip(base, mine, strict=True):
        if old != new:
            if bare.count(_bare(new)) != 1:
                return None
            i = bare.index(_bare(new))
            work[i] = max(work[i], new, key=_rank)
    return work


def _rebase(tree: Path, work: str) -> None:
    """Rebase onto *work*: a conflict in TASKS markers alone replays; anything else, a JSONL
    ledger included, aborts and refuses — re-run the ledger's writer on the rebased tree.
    A branch already holding *work* (a merge of it included) fast-forwards as it is."""
    if git(tree, "rev-list", "--count", f"HEAD..{work}").strip() == "0":
        return
    step: tuple[str, ...] = ("rebase", "-q", work)
    while True:
        try:
            git(tree, *step)
            return
        except RuntimeError as error:
            rels = git(tree, "diff", "--name-only", "--diff-filter=U").split()
            replayed = {r: _replayed(tree, r) for r in rels if fnmatch.fnmatch(r, REPLAY)}
            replay = {r: lines for r, lines in replayed.items() if lines is not None}
            if not rels or len(replay) < len(rels):
                git(tree, "rebase", "--abort", check=False)
                raise Refusal(
                    f"rebase onto {work} conflicts: {error}",
                    git_line(tree, "rebase", work),
                ) from error
        for rel, lines in replay.items():
            (tree / rel).write_text("\n".join(lines) + "\n", encoding="utf-8")
            git(tree, "add", rel)
        step = ("-c", "core.editor=true", "rebase", "--continue")


def _series(tree: Path, work: str, tip: str) -> list[tuple[str, str]]:
    """(patch-id, full message) per commit of *work*..*tip*, oldest first, keyed by commit id:
    an empty commit has no patch-id (""); a changed one without a patch-id never matches."""
    rng = f"{work}..{tip}"
    patch = git(tree, "log", "-p", "--no-color", "--no-ext-diff", "--format=commit %H", rng)
    pids = git(tree, "patch-id", "--stable", input=patch).split()
    ids = dict(zip(pids[1::2], pids[::2], strict=True))
    changed = set(git(tree, "log", "--format=%H", rng, "--", ".").split())
    logs = git(tree, "log", "--reverse", "--no-show-signature", "--format=%H%n%B%x00", rng)
    return [
        (ids.get(c, f"unmatched {c}" if c in changed else ""), msg)
        for c, _, msg in (x.lstrip("\n").partition("\n") for x in logs.split("\0")[:-1])
    ]


def _check_approved(root: Path, tree: Path, work: str, name: str) -> None:
    """The newest dd-code-reviewer handoffs naming a candidate sha decide: each must be a valid
    APPROVED (ADR 0110). A candidate is a sha X of this branch's reflog whose (patch-id, message)
    series over *work*..X equals HEAD's, in order (ADR 0168); X == HEAD is the degenerate case;
    the reflog's base (series []) matches only an empty branch. Newest is the schema-required
    `produced_at`, across every candidate (a newer verdict on a carried-over sha overrules an
    older one on HEAD); the file name never orders. A missing, unparseable or offset-less
    `produced_at` ranks newest and refuses; handoffs tied on the newest moment all decide, and
    the fix names the first in path order that is not a valid APPROVED. An unreadable file
    names no sha and is skipped."""
    head = git(tree, "rev-parse", "HEAD").strip()
    mine = _series(tree, work, head)
    reflog = {head, *git(tree, "reflog", "--format=%H", f"wt/{name}", check=False).split()}
    shas = {x for x in reflog if x == head or _series(tree, work, x) == mine}
    named = []
    for handoff in (root / ".dadaia" / "handoff").glob("*/*.handoff.json"):
        try:
            data = json.loads(handoff.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (
            isinstance(data, dict)
            and data.get("agent") == REVIEWER
            and any(sha in str(data.get("scope")) for sha in shas)
        ):
            try:
                at = datetime.fromisoformat(str(data.get("produced_at")))
                moment = at.timestamp() if at.tzinfo else None
            except ValueError:
                moment = None
            named.append((moment is None, moment or 0.0, str(handoff), data))
    top = max((row[:2] for row in named), default=None)
    for unparsed, _, path, data in sorted(row for row in named if row[:2] == top):
        if (
            unparsed
            or data.get("verdict") != "APPROVED"
            or cli(root, "reports", "validate", path).returncode
        ):
            break
    else:
        if named:
            return
        path = "--all"
    raise Refusal(
        f"the newest {REVIEWER} handoff naming HEAD {head} or a sha of its patch and message"
        " series is not a valid APPROVED (the file comes from the reviewer's verdict)",
        cli_line(root, "reports", "validate", path),
    )


def merge(root: Path, path: str, keep: list[str], drop: bool) -> str:
    repo, tree, name, work = _target(root, path)
    branch = f"wt/{name}"
    if not tree.exists():  # removed by an earlier run or by hand: only the branch may be left
        git(repo, "worktree", "unlock", str(tree), check=False)
        git(repo, "worktree", "prune")
        if git(repo, "branch", "--list", branch).strip():
            try:
                git(repo, "branch", "-d", branch)
            except RuntimeError as error:
                raise Refusal(
                    f"{branch} is unmerged: {error}",
                    git_line(repo, "worktree", "add", str(tree), branch),
                ) from error
        return f"{branch} merged into {work}"
    _refuse_dirty(tree)
    _check_allowed(tree, work, name)
    _rebase(tree, work)
    _check_approved(root, tree, work, name)
    kept = _kept(tree, "merge", keep, drop)
    if git(repo, "branch", "--show-current").strip() != work:
        raise Refusal(f"repos/{repo.name} is not on {work}", git_line(repo, "switch", work))
    try:
        git(repo, "merge", "-q", "--ff-only", branch)
    except RuntimeError as error:
        try:  # the work branch did not move: a stray change the operator owns blocks
            git(repo, "merge-base", "--is-ancestor", work, branch)
            fix = f"Operator action: commit or remove the paths above in {repo}"
        except RuntimeError:  # the work branch moved since the rebase
            fix = f"{script(SCRIPT)} merge {quote(str(tree))}"
        raise Refusal(f"fast-forward failed: {error}", fix) from error
    _remove(repo, tree, name, kept)
    return f"{branch} merged into {work}"


def clean(root: Path, path: str, keep: list[str], drop: bool) -> str:
    repo, tree, name, work = _target(root, path)
    if not any(Path(row["path"]).resolve() == tree for row in ours(repo)):
        raise Refusal(f"{tree} is not a dadaia:-locked worktree", f"{script(SCRIPT)} list")
    ahead = int(git(repo, "rev-list", "--count", f"{work}..wt/{name}"))
    if ahead:
        raise Refusal(
            f"wt/{name} holds {ahead} unmerged commit(s)",
            f"{script(SCRIPT)} merge {quote(str(tree))}",
        )
    _refuse_dirty(tree)
    _remove(repo, tree, name, _kept(tree, "clean", keep, drop))
    return f"cleaned {tree}"
