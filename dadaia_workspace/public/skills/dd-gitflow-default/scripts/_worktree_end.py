#!/usr/bin/env python3
"""`worktree.py merge|clean`: end one canonical worktree — land it on the work branch after
its gate, or drop an empty one — never with `--force` or `-D`, re-runnable after a
stop. A job lands after its review and the job gate (its tasks and stages ran their own
`scripts/ci.py task|stage` inside its one tree); a `define` or `backlog` tree lands `specs/`
after its review and the ledger checks alone."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from _worktree_git import (
    _env,
    cli,
    cli_line,
    flow_for,
    git,
    git_line,
    ours,
    quote,
    script,
    work_version,
)
from _worktree_names import NAME_RE, SCRIPT, Refusal, branch, locate, non_code

REVIEWER = "dd-code-reviewer"
#: A CI-matrix run as a verdict names it: its GitHub Actions run URL.
_RUN_RE = re.compile(r"/actions/runs/\d+")
#: The ledger, trio and release checks a `define` or `backlog` merge runs, in this order.
_LEDGERS = (("dd-bug-resolution", "bugs.py"), ("dd-backlog-definition", "backlog.py"),
            ("dd-release-implementation", "release.py"))  # fmt: skip


def _target(root: Path, path: str) -> tuple[Path, Path, str, str]:
    """(repo, tree, name, work branch) of `worktrees/<repo>/<name>`; the tree may be gone."""
    tree = Path(path).resolve()
    rel = tree.relative_to(root).as_posix() if tree.is_relative_to(root) else ""
    repo_name, name, tail = locate(rel) or ("", None, ())
    if name is None or tail or not NAME_RE.match(name):
        raise Refusal(f"{path} is not a worktrees/<repo>/<name> path", f"{script(SCRIPT)} list")
    repo = root / "repos" / repo_name
    flow, version = flow_for(root, repo), NAME_RE.match(name)["v"]  # type: ignore[index]
    return repo, tree, name, flow["work"] + (version or work_version(repo, flow))


def _refuse_dirty(tree: Path) -> None:
    if git(tree, "status", "--porcelain").strip():
        raise Refusal(
            f"{tree} has uncommitted changes",
            f"Operator action: commit them in their commit shape (`{git_line(tree, 'add', '-A')}`"
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


def _remove(into: Path, tree: Path, name: str, kept: list[str]) -> None:
    """Copy *kept* into the repo *into* and drop the tree and its branch."""
    for rel in kept:
        source, target = tree / rel, into / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
    git(into, "worktree", "unlock", str(tree), check=False)
    git(into, "worktree", "remove", str(tree))
    git(into, "branch", "-d", branch(name))


def _undo(tree: Path, work: str, rel: str) -> str:
    """The one act putting *rel* back to the work branch's version, absent included."""
    return (f"Operator action: revert {rel} to {work} in one commit — "
            f"`{git_line(tree, 'restore', '-s', work, '-SW', '--', rel)}` and `{git_line(tree, 'commit')}`")  # fmt: skip


def _check_specs_only(tree: Path, work: str) -> None:
    """A `define` or `backlog` tree lands `specs/` alone: its merge runs no test."""
    for rel in git(tree, "diff", "--name-only", f"{work}...HEAD").splitlines():
        if not rel.startswith("specs/"):
            raise Refusal(f"{rel} is code; a define or backlog tree lands specs/ only — "
                          "code lands through a job", _undo(tree, work, rel))  # fmt: skip


def _check_ancestor(tree: Path, work: str) -> None:
    """*work* must be an ancestor of HEAD: `merge` lands HEAD as it is, never rebased."""
    try:
        git(tree, "merge-base", "--is-ancestor", work, "HEAD")
    except RuntimeError as error:
        raise Refusal(
            f"{work} moved past this branch's base", git_line(tree, "rebase", work)
        ) from error


def _python(root: Path) -> Path:
    found = [p for p in (root / ".dadaia/.venv/bin/python", root / ".dadaia/.venv/Scripts/python.exe")
             if p.exists()]  # fmt: skip
    if not found:
        raise Refusal(
            "no workspace venv",
            " ".join(map(quote, ("uvx", "dadaia-workspace", "init", str(root)))),
        )
    return found[0]


def _gate(root: Path, tree: Path, *argv: str) -> None:
    """One gate level: `scripts/ci.py <level> [files]` of the HEAD being landed, run
    as one argv list (never a shell) in *tree* by the workspace venv; its output, on stdout
    alone, is the evidence; stdin is closed: a gate reading it never blocks merge."""
    ci = tree / "scripts" / "ci.py"
    if not ci.is_file():
        raise Refusal(f"{tree} has no scripts/ci.py",
                      f"Operator action: add scripts/ci.py with its task, stage and job levels to repos/"
                      f"{tree.parents[2].name}")  # fmt: skip
    command = [str(_python(root)), str(ci), *argv]
    done = subprocess.run(command, cwd=tree, env=_env(), stdin=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)  # fmt: skip
    if done.returncode:
        line = " ".join(map(quote, command))
        raise Refusal(f"scripts/ci.py {argv[0]} exited {done.returncode}",
                      f"Operator action: make `{line}` exit 0 in {tree} and commit the fix in this worktree")  # fmt: skip


def _ledgers(tree: Path) -> None:
    """A `define` or `backlog` merge's whole gate: each ledger script's `check` on the tree."""
    skills = Path(__file__).resolve().parents[2]
    for skill, name in _LEDGERS:
        command = [sys.executable, str(skills / skill / "scripts" / name),
                   "check", "--specs", str(tree / "specs")]  # fmt: skip
        done = subprocess.run(command, cwd=tree, env=_env(), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True)  # fmt: skip
        if done.returncode:
            print(done.stdout, done.stderr, sep="", end="")
            raise Refusal(f"{name} check failed on {tree / 'specs'}",
                          f"Operator action: fix the findings above in {tree} and commit them")  # fmt: skip


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


def _check_approved(root: Path, tree: Path, work: str, name: str, run: bool) -> None:
    """The newest dd-code-reviewer handoffs naming a candidate sha decide: each must be a valid
    APPROVED (ADR 0110). A candidate is a sha X of this branch's reflog whose (patch-id, message)
    series over *work*..X equals HEAD's, in order (ADR 0168); X == HEAD is the degenerate case;
    the reflog's base (series []) matches only an empty branch. Newest is the schema-required
    `produced_at`, across every candidate (a newer verdict on a carried-over sha overrules an
    older one on HEAD); the file name never orders. A missing, unparseable or offset-less
    `produced_at` ranks newest and refuses; handoffs tied on the newest moment all decide, and
    the fix names the first in path order that is not a valid APPROVED. An unreadable file
    names no sha and is skipped. With *run* (a job), the deciding verdict also names the job's
    CI-matrix run."""
    head = git(tree, "rev-parse", "HEAD").strip()
    mine = _series(tree, work, head)
    reflog = {head, *git(tree, "reflog", "--format=%H", branch(name), check=False).split()}
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
        if named and (not run or _RUN_RE.search(json.dumps(data))):
            return
        if named:
            raise Refusal(
                f"the APPROVED verdict {path} names no CI-matrix run of HEAD {head}",
                f"Operator action: push {branch(name)}, wait for its CI run to pass, and have "
                f"{REVIEWER}'s verdict name that run's actions/runs URL",
            )
        path = "--all"
    raise Refusal(
        f"the newest {REVIEWER} handoff naming HEAD {head} or a sha of its patch and message"
        " series is not a valid APPROVED (the file comes from the reviewer's verdict)",
        cli_line(root, "reports", "validate", path),
    )


def merge(root: Path, path: str, keep: list[str], drop: bool) -> str:
    repo, tree, name, onto = _target(root, path)
    ref = branch(name)
    if not tree.exists():  # removed by an earlier run or by hand: only the branch may be left
        git(repo, "worktree", "unlock", str(tree), check=False)
        git(repo, "worktree", "prune")
        if git(repo, "branch", "--list", ref).strip():
            try:
                git(repo, "branch", "-d", ref)
            except RuntimeError as error:
                raise Refusal(
                    f"{ref} is unmerged: {error}",
                    git_line(repo, "worktree", "add", str(tree), ref),
                ) from error
        return f"{ref} merged into {onto}"
    _refuse_dirty(tree)
    code = not non_code(name)
    if not code:
        _check_specs_only(tree, onto)
    _check_ancestor(tree, onto)
    _check_approved(root, tree, onto, name, run=code)
    _gate(root, tree, "job") if code else _ledgers(tree)
    kept = _kept(tree, "merge", keep, drop)
    if git(repo, "branch", "--show-current").strip() != onto:
        raise Refusal(f"repos/{repo.name} is not on {onto}", git_line(repo, "switch", onto))
    try:
        git(repo, "merge", "-q", "--ff-only", ref)
    except RuntimeError as error:
        _check_ancestor(tree, onto)  # moved while merge ran; else a stray the operator owns
        fix = f"Operator action: commit or remove the paths above in {repo}"
        raise Refusal(f"fast-forward failed: {error}", fix) from error
    _remove(repo, tree, name, kept)
    return f"{ref} merged into {onto}"


def clean(root: Path, path: str, keep: list[str], drop: bool) -> str:
    repo, tree, name, onto = _target(root, path)
    if not any(Path(row["path"]).resolve() == tree for row in ours(repo)):
        raise Refusal(f"{tree} is not a dadaia:-locked worktree", f"{script(SCRIPT)} list")
    ahead = int(git(repo, "rev-list", "--count", f"{onto}..{branch(name)}"))
    if ahead:
        raise Refusal(
            f"{branch(name)} holds {ahead} unmerged commit(s)",
            f"{script(SCRIPT)} merge {quote(str(tree))}",
        )
    _refuse_dirty(tree)
    _remove(repo, tree, name, _kept(tree, "clean", keep, drop))
    return f"cleaned {tree}"
