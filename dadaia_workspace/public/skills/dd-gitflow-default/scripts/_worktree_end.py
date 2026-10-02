#!/usr/bin/env python3
"""`worktree.py merge|clean`: end one canonical worktree — fast-forward it into the work
branch, or drop an empty one — never with `--force` or `-D`, re-runnable after a stop."""

from __future__ import annotations

import fnmatch
import json
import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

from _release_schema import MARK_RE, MARKS  # noqa: E402
from _worktree_git import cli, cli_line, flow_for, git, ours, quote, script  # noqa: E402
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
            f"git -C {quote(str(tree))} stash push --include-untracked",
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
    return (f"Operator action: revert {rel} to {work} in one commit — `git -C {quote(str(tree))} restore "
            f"-s {work} -SW -- {quote(rel)}` and `git -C {quote(str(tree))} commit`")  # fmt: skip


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
    """Rebase onto *work*: JSONL ledgers union (the `new` attributes); a conflict in TASKS
    markers alone replays; anything else aborts and refuses."""
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
                    f"git -C {quote(str(tree))} rebase {work}",
                ) from error
        for rel, lines in replay.items():
            (tree / rel).write_text("\n".join(lines) + "\n", encoding="utf-8")
            git(tree, "add", rel)
        step = ("-c", "core.editor=true", "rebase", "--continue")


def _check_approved(root: Path, sha: str) -> None:
    """An APPROVED dd-code-reviewer handoff names *sha* in its scope and validates (ADR 0110)."""
    named = []
    for handoff in sorted((root / ".dadaia" / "handoff").glob("*/*.handoff.json")):
        try:
            data = json.loads(handoff.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (
            isinstance(data, dict)
            and data.get("agent") == REVIEWER
            and sha in str(data.get("scope"))
        ):
            named.append(handoff)
            if (
                data.get("verdict") == "APPROVED"
                and cli(root, "reports", "validate", str(handoff)).returncode == 0
            ):
                return
    fix = cli_line(root, "reports", "validate", str(named[-1]) if named else "--all")
    raise Refusal(
        f"no valid APPROVED {REVIEWER} handoff names HEAD {sha} in its scope"
        " (the file comes from the reviewer's verdict)",
        fix,
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
                    f"git -C {quote(str(repo))} worktree add {quote(str(tree))} {branch}",
                ) from error
        return f"{branch} merged into {work}"
    _refuse_dirty(tree)
    _check_allowed(tree, work, name)
    _rebase(tree, work)
    _check_approved(root, git(tree, "rev-parse", "HEAD").strip())
    kept = _kept(tree, "merge", keep, drop)
    if git(repo, "branch", "--show-current").strip() != work:
        raise Refusal(
            f"repos/{repo.name} is not on {work}", f"git -C {quote(str(repo))} switch {work}"
        )
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
