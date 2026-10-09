#!/usr/bin/env python3
"""`worktree.py merge|clean`: end one canonical worktree — land it on the branch it
was cut from after its gate, or drop an empty one — never with `--force` or `-D`,
re-runnable after a stop. A task lands on its job branch after test separation, unreviewed; a
job lands on the work branch after its review and the job gate; a `define` or `backlog` tree
lands `specs/` after its review and the ledger checks alone. The job gate is the repo's own
declared `verify:` line, run as one argv list."""

from __future__ import annotations

import fnmatch
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from _worktree_git import (
    _env,
    cli,
    cli_line,
    diff_sha256,
    flow_for,
    git,
    git_line,
    ours,
    quote,
    recorded_base,
    script,
    work_version,
    workspace_of,
)
from _worktree_names import NAME_RE, SCRIPT, Refusal, branch, locate, non_code, plain

REVIEWER = "dd-code-reviewer"
#: The ledger, trio and release checks a `define` or `backlog` merge runs, in this order.
_LEDGERS = (("dd-bug-resolution", "bugs.py"), ("dd-backlog-definition", "backlog.py"),
            ("dd-release-implementation", "release.py"))  # fmt: skip


def _target(root: Path, path: str) -> tuple[Path, Path, str, str]:
    """(repo, tree, name, base branch) of `worktrees/<repo>/<name>`; the tree may be gone."""
    tree = Path(path).resolve()
    rel = tree.relative_to(root).as_posix() if tree.is_relative_to(root) else ""
    repo_name, name, tail = locate(rel) or ("", None, ())
    if name is None or tail or not NAME_RE.match(name):
        raise Refusal(f"{path} is not a worktrees/<repo>/<name> path", f"{script(SCRIPT)} list")
    repo = root / "repos" / repo_name
    flow, version = flow_for(root, repo), NAME_RE.match(name)["v"]  # type: ignore[index]
    work = flow["work"] + (version or work_version(repo, flow)) if not plain(name) else ""
    return repo, tree, name, recorded_base(repo, name, work)


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
    """Copy *kept* into the repo *into* and drop the tree, its branch (on the remote too, when it
    was pushed) and the rc folder it leaves empty."""
    for rel in kept:
        source, target = tree / rel, into / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
    held = f"refs/heads/{branch(name)}"  # its upstream remote, when it has one that still holds it
    fields = git(
        into, "for-each-ref", "--format=%(upstream:remotename) %(upstream:track)", held
    ).split()
    if fields and "[gone]" not in fields:
        try:
            git(into, "push", "-q", fields[0], "--delete", branch(name))
        except RuntimeError as error:
            raise Refusal(
                f"{branch(name)} is still on {fields[0]}: {error}",
                git_line(into, "push", fields[0], "--delete", branch(name)),
            ) from error
    git(into, "worktree", "unlock", str(tree), check=False)
    git(into, "worktree", "remove", str(tree))
    git(into, "branch", "-d", branch(name))
    _rmdir(tree)


def _rmdir(tree: Path) -> None:
    """Drop the rc folder *tree* leaves empty; a folder still holding another tree stays."""
    if tree.parent.is_dir() and not any(tree.parent.iterdir()):
        tree.parent.rmdir()


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


def _declared(tree: Path, work: str, key: str) -> str:
    """The value of the `<key>` line *work*'s tracked `AGENTS.md` declares (a leading UTF-8 BOM is
    ignored), `""` when absent."""
    shown = git(tree, "show", f"{work}:AGENTS.md", check=False)
    lines = shown.removeprefix("\ufeff").splitlines()
    return next((ln.removeprefix(key).strip() for ln in lines if ln.startswith(key)), "")


def _gate(tree: Path, work: str, *, required: bool = True) -> None:
    """Run *work*'s tracked `verify:` once; a plain tree may omit the declaration."""
    key = "verify:"
    declared = _declared(tree, work, key)
    root = workspace_of(tree)
    if root is None:
        raise Refusal(
            f"no workspace owns {tree}", "Operator action: run this merge inside its workspace"
        )
    repo_name = tree.relative_to(root / "worktrees").parts[0]
    agents = root / "repos" / repo_name / "AGENTS.md"
    if not declared:
        if not required:
            return
        raise Refusal(f"this repo declares no {key} command",
                      f"Operator action: add this repo's job gate as a {key} line to {agents} and commit it on {work}")  # fmt: skip
    venv = [root / ".dadaia/.venv" / d for d in ("bin", "Scripts")]  # the workspace's
    env = _env() | {"PATH": os.pathsep.join([*map(str, venv), os.environ.get("PATH", "")])}
    try:
        command = shlex.split(declared)
        done = subprocess.run(command, cwd=tree, env=env, stdin=subprocess.DEVNULL,
                              stderr=subprocess.STDOUT)  # fmt: skip
    except (OSError, ValueError) as error:
        raise Refusal(f"{key} {declared!r} cannot start: {error}",
                      f"Operator action: make the {key} line of {agents} on {work} one argv list that starts:"
                      " it runs without a shell — no VAR=value prefix, no sh -c") from error  # fmt: skip
    if done.returncode:
        line = " ".join(map(quote, command))
        raise Refusal(f"{key} exited {done.returncode}",
                      f"Operator action: make `{line}` exit 0 in {tree} and commit the fix in this worktree")  # fmt: skip


def _is_test_path(path: str, declared: str) -> bool:
    """Whether *path* is a declared test glob, or a built-in fallback when none is declared."""
    if declared:
        try:
            return any(fnmatch.fnmatchcase(path, glob) for glob in shlex.split(declared))
        except ValueError:
            return False
    name = Path(path).name
    return (
        path.startswith("tests/")
        or name.startswith("test_")
        or fnmatch.fnmatchcase(name, "*_test.*")
        or fnmatch.fnmatchcase(name, "*.spec.*")
    )


def _refuse_implementation_tests(tree: Path, onto: str, law: str) -> None:
    """Keep RED test commits separate from every non-test implementation commit."""
    declared = _declared(tree, law, "tests:")
    commits = git(tree, "rev-list", "--reverse", f"{onto}..HEAD").split()
    for commit in commits:
        subject = git(tree, "show", "-s", "--format=%s", commit).strip()
        if subject.startswith("test("):
            continue
        paths = git(tree, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).split()
        if test := next((path for path in paths if _is_test_path(path, declared)), None):
            raise Refusal(
                f"implementation commit {commit[:12]} touches test path {test}",
                f"Operator action: move {test} to the separate RED test dispatch and keep this implementation commit source-only",
            )


def _open_tasks(repo: Path, name: str) -> None:
    """A stage closes, and a job lands, only with none of its task worktrees open."""
    for row in ours(repo):
        if row["name"].startswith(f"{name}--"):
            raise Refusal(f"task worktree {row['path']} of {branch(name)} is open",
                          f"{script(SCRIPT)} merge {quote(row['path'])}")  # fmt: skip


def _checks(root: Path, tree: Path) -> Iterator[tuple[str, subprocess.CompletedProcess[str]]]:
    """Each ledger script's `check` on the tree, then the workspace doctor on its `specs/` — the
    check the work branch's gates run — fenced to the tree."""
    skills = Path(__file__).resolve().parents[2]
    for skill, name in _LEDGERS:
        command = [sys.executable, str(skills / skill / "scripts" / name),
                   "check", "--specs", str(tree / "specs")]  # fmt: skip
        yield name, subprocess.run(command, cwd=tree, env=_env(), stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")  # fmt: skip
    yield "dadaia doctor", cli(root, "doctor", "--specs-dir", str(tree / "specs"), tree=tree)


def _ledgers(root: Path, tree: Path) -> None:
    """A `define` or `backlog` merge's whole gate: the ledger checks and the doctor on the tree, a red one relaying its own first `fix:` line."""
    for name, done in _checks(root, tree):
        if done.returncode:
            print(out := done.stdout + done.stderr, end="")
            raise Refusal(f"{name} check failed on {tree / 'specs'}", next((ln[5:] for ln in out.splitlines() if ln.startswith("fix: ")), f"Operator action: fix the findings above in {tree} and commit them"))  # fmt: skip


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
    """The newest dd-code-reviewer handoffs whose `reviewed_sha` is a candidate sha decide: each must
    be a valid APPROVED whose `diff_sha256` is HEAD's, read from the handoff
    zone and from the reaper's hold of it. A candidate is a sha X of this branch's reflog whose (patch-id, message)
    series over *work*..X equals HEAD's, in order (ADR 0168); X == HEAD is the degenerate case;
    the reflog's base (series []) matches only an empty branch. Newest is the schema-required
    `produced_at`, across every candidate (a newer verdict on a carried-over sha overrules an
    older one on HEAD); the file name never orders. A missing, unparseable or offset-less
    `produced_at` ranks newest and refuses; handoffs tied on the newest moment all decide, and
    the fix names the first in path order that is not a valid APPROVED. An unreadable file
    names no sha and is skipped."""
    head = git(tree, "rev-parse", "HEAD").strip()
    mine = _series(tree, work, head)
    reflog = {head, *git(tree, "reflog", "--format=%H", branch(name), check=False).split()}
    shas = {x for x in reflog if x == head or _series(tree, work, x) == mine}
    named = []
    for handoff in [*root.glob(".dadaia/handoff/*/*.handoff.json"), *root.glob(".dadaia/reaped/*/.dadaia/handoff/*/*.handoff.json")]:  # fmt: skip
        try:
            data = json.loads(handoff.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (
            isinstance(data, dict)
            and data.get("agent") == REVIEWER
            and str(data.get("reviewed_sha")) in shas
        ):
            try:
                at = datetime.fromisoformat(str(data.get("produced_at")))
                moment = at.timestamp() if at.tzinfo else None
            except ValueError:
                moment = None
            named.append((moment is None, moment or 0.0, str(handoff), data))
    top = max((row[:2] for row in named), default=None)
    decided = sorted(row for row in named if row[:2] == top)
    invalid = next(
        (
            path
            for unparsed, _, path, data in decided
            if unparsed
            or data.get("verdict") != "APPROVED"
            or cli(root, "reports", "validate", path).returncode
        ),
        None,
    )
    if invalid or not decided:
        raise Refusal(
            f"the newest {REVIEWER} handoff naming HEAD {head} or a sha of its patch and message"
            " series is not a valid APPROVED (the file comes from the reviewer's verdict)",
            cli_line(root, "reports", "validate", invalid or "--all"),
        )
    want = diff_sha256(tree, work, head)
    if any(row[3].get("diff_sha256") != want for row in decided):
        raise Refusal(f"no {REVIEWER} verdict binds the diff {head} lands",
                      f"Operator action: dispatch {REVIEWER} on {tree} at HEAD {head}; its verdict.py run writes the verdict")  # fmt: skip


def digest(root: Path, path: str, sha: str) -> str:
    """The binding a verdict carries for *sha* of a worktree, as one JSON object."""
    _, tree, name, onto = _target(root, path)
    if git(tree, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}", check=False).strip() != sha:  # fmt: skip
        raise Refusal(f"{sha} is not a commit sha of {tree}", f"Operator action: pass a 40-hex commit of {tree}")  # fmt: skip
    scope = f"{branch(name)}@{git(tree, 'rev-parse', 'HEAD').strip()}"
    return json.dumps({"root": str(root), "scope": scope, "reviewed_sha": sha, "diff_sha256": diff_sha256(tree, onto, sha)})  # fmt: skip


def _into(repo: Path, onto: str) -> Path:
    """The checkout *onto* is checked out in: its job's tree for a job branch, else the repo."""
    name = onto.removeprefix("wt/")
    return repo.parents[1] / "worktrees" / repo.name / name if onto.startswith("wt/") else repo


def merge(root: Path, path: str, keep: list[str], drop: bool) -> str:
    repo, tree, name, onto = _target(root, path)
    into, ref = _into(repo, onto), branch(name)
    if not tree.exists():  # removed by an earlier run or by hand: only the branch may be left
        git(into, "worktree", "unlock", str(tree), check=False)
        git(into, "worktree", "prune")
        if git(into, "branch", "--list", ref).strip():
            try:
                git(into, "branch", "-d", ref)
            except RuntimeError as error:
                raise Refusal(
                    f"{ref} is unmerged: {error}",
                    git_line(repo, "worktree", "add", str(tree), ref),
                ) from error
        _rmdir(tree)
        return f"{ref} merged into {onto}"
    _refuse_dirty(tree)
    if into != repo:  # a task: hygiene and implementation/test separation, no gate or verdict
        _check_ancestor(tree, onto)
        _refuse_implementation_tests(tree, onto, _target(root, str(into))[3])
        _refuse_dirty(into)
    elif non_code(name):
        _check_specs_only(tree, onto)
        _check_ancestor(tree, onto)
        _check_approved(root, tree, onto, name)
        _ledgers(root, tree)
    elif plain(name):
        _check_ancestor(tree, onto)
        _check_approved(root, tree, onto, name)
        _gate(tree, onto, required=False)
    else:
        _open_tasks(repo, name)
        _check_ancestor(tree, onto)
        _check_approved(root, tree, onto, name)
        _gate(tree, onto)
    kept = _kept(tree, "merge", keep, drop)
    if git(into, "branch", "--show-current").strip() != onto:
        raise Refusal(f"{into} is not on {onto}", git_line(into, "switch", onto))
    try:
        git(into, "merge", "-q", "--ff-only", ref)
    except RuntimeError as error:
        _check_ancestor(tree, onto)  # moved while merge ran; else a stray the operator owns
        fix = f"Operator action: commit or remove the paths above in {into}"
        raise Refusal(f"fast-forward failed: {error}", fix) from error
    _remove(into, tree, name, kept)
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
    _remove(_into(repo, onto), tree, name, _kept(tree, "clean", keep, drop))
    return f"cleaned {tree}"
