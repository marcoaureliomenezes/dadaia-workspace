#!/usr/bin/env python3
"""`worktree.py merge|clean`: end one canonical worktree — land it on its parent's branch after
its gate, or drop an empty one — never with `--force` or `-D`, re-runnable after a stop. A task
lands after test separation, unreviewed; a main tree, a rc (plus, in the main repo, the ledger checks) and a hotfix
after their review and the job gate; a backlog tree lands `specs/` after its review and the ledger
checks alone (an associated repo holds no `specs/`, so those checks skip). The job gate is the repo's declared `verify:` line, run as one argv list."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from functools import partial
from pathlib import Path

import _worktree_names as names
from _handoffs import REVIEWER, reviewer_records
from _platform import act, command, git_inline, git_line, inline, run, venv_dir, venv_tool
from _refusal import relay, without_fix
from _worktree_git import (
    cli,
    cli_words,
    diff_sha256,
    dirty,
    drop_argv,
    flow_for,
    git,
    not_a_name,
    ours,
    reattach,
    scrubbed_env,
    workspace_of,
)
from _worktree_names import LAUNCH, NAME_RE, Refusal, base_of, branch, kind_of, locate, tree_path

#: The ledger and release checks a `backlog` or `rc` merge runs, in this order.
_LEDGERS = (Path("dd-bug-resolution/scripts/bugs.py"), Path("dd-backlog-definition/scripts/backlog.py"),
            Path("dd-release-implementation/scripts/release.py"))  # fmt: skip
#: The skills folder of the instance this script runs from, the fallback when a tree carries no ledger script.
_INSTANCE_SKILLS = Path(__file__).resolve().parent.parent.parent


def _target(root: Path, path: str) -> tuple[Path, Path, str, str]:
    """(repo, tree, name, base branch) of `worktrees/<repo>/<name>`; the tree may be gone. Only a
    base that is the work branch reads the gitflow."""
    tree = Path(path).resolve()
    rel = tree.relative_to(root).as_posix() if tree.is_relative_to(root) else ""
    repo_name, name, tail = locate(rel) or ("", None, ())
    if tail or not repo_name:
        raise Refusal(f"{path} is not a worktrees/<repo>/<name> path", command(*LAUNCH, "list"))
    if name is None or not NAME_RE.match(name):
        raise not_a_name(name or rel.split("/", 2)[-1])
    repo = root / "repos" / repo_name
    work = "" if kind_of(name) in ("task", "main") else flow_for(root, repo)["work"]
    return repo, tree, name, base_of(name, work)  # type: ignore[return-value]


def _refuse_dirty(tree: Path) -> None:
    if dirty(tree):
        raise Refusal(
            f"{tree} has uncommitted changes",
            act(
                "agent",
                f"stage the paths `{git_inline(tree, 'status', '--short')}` lists and commit them"
                f" in their commit shape (`{git_inline(tree, 'commit')}`) or remove them (`{git_inline(tree, 'clean', '-fd')}`"
                f" and `{git_inline(tree, 'restore', '-SW', '.')}`) — never a stash every worktree shares",
            ),
        )


def _precious(tree: Path) -> list[str]:
    """The ignored files of *tree* that are not disposable: a tool cache directory or a `*.pyc` is."""
    listing = git(tree, "status", "--porcelain", "-z", "--ignored=matching")
    ignored = [  # -z: a name with a blank arrives verbatim, never C-quoted; matching: one entry per directory
        line[3:].rstrip("/") for line in listing.split("\0") if line.startswith("!! ")
    ]
    return [
        p
        for p in ignored
        if not (p.endswith(".pyc") or any("cache" in part for part in Path(p).parts))
    ]


def _kept(tree: Path, verb: str, keep: list[str], drop: bool) -> list[str]:
    """The ignored files to copy into the repo; refuses while one is neither kept nor dropped."""
    precious = _precious(tree)
    left = [p for p in precious if p not in keep]
    if left and not drop:
        go = partial(inline, *LAUNCH, verb, str(tree))
        offer = f"keep them with `{go('--keep', *precious)}` or discard them with `{go('--drop')}`"
        raise Refusal(f"ignored files would be lost: {', '.join(left)}", act("agent", offer))  # fmt: skip
    return [p for p in precious if p in keep]


def _remove(repo: Path, tree: Path, onto: str, name: str, kept: list[str]) -> None:
    """Copy *kept* into the checkout of *onto* (of *repo*) and drop the tree (an absent one is pruned), its branch (on
    the remote too, when it was pushed) and the folder it leaves empty."""
    if not (drops := drop_argv(into := _parent(repo, onto), branch(name), onto)):
        raise Refusal(f"{branch(name)} is unmerged into {onto}", reattach(repo, tree, name))
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
    git(into, "worktree", *(("remove", str(tree)) if tree.exists() else ("prune",)))
    for argv in drops:
        git(into, *argv)
    _rmdir(tree, name)


def _rmdir(tree: Path, name: str) -> None:
    """Drop the folders *tree* leaves empty, its level folders cascading outward; a folder holding
    anything beyond its level file stops the cascade; an empty one is dropped too."""
    home = tree.parents[name.count("/")]
    for folder, _ in reversed(names.level_folders(home, name)):
        if folder.is_dir():
            if any(folder.iterdir()) and not names.is_bare_level(home, folder):
                return
            (folder / names.LEVEL_FILE).unlink(missing_ok=True)
            folder.rmdir()


def _undo(tree: Path, work: str, rel: str) -> str:
    """The one act putting *rel* back to the work branch's version, absent included."""
    return act("agent", f"revert {rel} to {work} in one commit — "
               f"`{git_inline(tree, 'restore', '-s', work, '-SW', '--', rel)}` and `{git_inline(tree, 'commit')}`")  # fmt: skip


def _check_specs_only(tree: Path, work: str) -> None:
    """A backlog tree lands `specs/` and the repo's `AGENTS.md` alone: its merge runs no test."""
    for rel in git(tree, "diff", "--name-only", f"{work}...HEAD").splitlines():
        if rel != "AGENTS.md" and not rel.startswith("specs/"):
            raise Refusal(f"{rel} is code; a backlog tree lands specs/ and AGENTS.md only — "
                          "code lands through a job", _undo(tree, work, rel))  # fmt: skip


def _check_ancestor(root: Path, tree: Path, work: str) -> None:
    """*work* must be an ancestor of HEAD: `merge` lands HEAD as it is, never rebased."""
    try:
        git(tree, "merge-base", "--is-ancestor", work, "HEAD")
    except RuntimeError as error:
        raise Refusal(
            f"{work} moved past this branch's base",
            command(*cli_words(root, "worktree", "sync", str(tree))),
        ) from error


def _workspace(tree: Path) -> Path:
    """The workspace owning *tree*; none owns it is a refusal."""
    if (root := workspace_of(tree)) is None:
        raise Refusal(
            f"no workspace owns {tree}", act("agent", "run this merge inside its workspace")
        )
    return root


def _land_line(tree: Path, work: str, text: str) -> str:
    """The one act that lands a repo-law line: a backlog lane carries it onto the work branch (its
    merge still runs the verdict and the ledger checks), then the tree owning *work* syncs."""
    root = _workspace(tree)
    owner = tree
    if work.startswith("wt/"):
        owner = _into(root / "repos" / tree.relative_to(tree_path(root, "")).parts[0], work)
    sync = inline(*cli_words(root, "worktree", "sync", str(owner)))
    return act("agent", f"{text} through a wt-backlog lane, then `{sync}`")


def _declared(tree: Path, work: str, key: str) -> str:
    """The value of the `<key>` line *work*'s tracked `AGENTS.md` declares (a leading UTF-8 BOM is
    ignored), `""` when absent."""
    shown = git(tree, "show", f"{work}:AGENTS.md", check=False)
    lines = shown.removeprefix("\ufeff").splitlines()
    return next((ln.removeprefix(key).strip() for ln in lines if ln.startswith(key)), "")


_WORD = re.compile(r"""(?:[^\s"']|"[^"]*"|'[^']*')+""")
_QUOTED = re.compile(r"""'([^']*)'|"([^"]*)\"""")


def _declared_argv(tree: Path, work: str, key: str) -> list[str]:
    """The words of the `<key>` line: split on whitespace, a quote groups a word, a backslash is
    literal, `;` and `$(...)` are plain words; `[]` when absent."""
    line = _declared(tree, work, key)
    if _WORD.sub("", line).strip():
        raise Refusal(f"the {key} line of {work} has an unclosed quote",
                      _land_line(tree, work, f"close the quote in the {key} line of AGENTS.md on {work}"))  # fmt: skip
    return [_QUOTED.sub(lambda m: m[1] if m[1] is not None else m[2], w) for w in _WORD.findall(line)]  # fmt: skip


def _gate(tree: Path, work: str) -> None:
    """Run *work*'s tracked `verify:` once."""
    key = "verify:"
    argv = _declared_argv(tree, work, key)
    root = _workspace(tree)
    if not argv:
        raise Refusal(f"this repo declares no {key} command",
                      _land_line(tree, work, f"add this repo's job gate as a {key} line of AGENTS.md on {work}"))  # fmt: skip
    env = scrubbed_env()
    env["PATH"] = os.pathsep.join([str(venv_tool(venv_dir(root), "python").parent), env.get("PATH", "")])  # fmt: skip
    try:
        done = subprocess.run(argv, cwd=tree, env=env, stdin=subprocess.DEVNULL,
                              stderr=subprocess.STDOUT)  # fmt: skip
    except OSError as error:
        raise Refusal(f"{key} {' '.join(argv)!r} cannot start: {error}",
                      _land_line(tree, work, f"make the {key} line of AGENTS.md on {work} one argv list that starts"
                                       " (no shell: no VAR=value prefix, no sh -c)")) from error  # fmt: skip
    if done.returncode:
        name = (locate(tree.relative_to(root).as_posix()) or ("", ""))[1]
        match kind_of(name or ""):
            case "main":
                tail = "commit the fix in a task of this job"
            case "rc":
                sync = inline(*cli_words(root, "worktree", "sync", str(tree)))
                tail = (
                    "commit the fix in this worktree when a reconcile commit is at fault or only this release's job code fails"
                    " (register that bug first, specs/bugs/AGENTS.md §2), or through a"
                    f" wt-hotfix lane when the work branch's verify: fails too, then `{sync}`"
                )
            case _:
                tail = "commit the fix in this worktree"
        raise Refusal(f"{key} exited {done.returncode}",
                      act("agent", f"make `{inline(*argv)}` exit 0 in {tree} and {tail}"))  # fmt: skip


def _is_test_path(path: str, globs: list[str]) -> bool:
    """Whether *path* is a declared test glob, or a built-in fallback when none is declared: under
    `tests/` or named like a test, never inside a dot-folder (`.github/`) of tooling."""
    if globs:
        return any(fnmatch.fnmatchcase(path, glob) for glob in globs)
    *folders, name = Path(path).parts
    return not any(f.startswith(".") for f in folders) and (
        path.startswith("tests/")
        or name.startswith("test_")
        or fnmatch.fnmatchcase(name, "*_test.*")
        or fnmatch.fnmatchcase(name, "*.spec.*")
    )


def _refuse_implementation_tests(tree: Path, onto: str, law: str) -> None:
    """Keep RED test commits separate from every non-test implementation commit."""
    declared = _declared_argv(tree, law, "tests:")
    commits = git(tree, "rev-list", "--reverse", f"{onto}..HEAD").split()
    for commit in commits:
        subject = git(tree, "show", "-s", "--format=%s", commit).strip()
        diff = git(tree, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", commit)
        paths = diff.split("\0")[:-1]
        if subject.startswith("test("):
            if source := next((path for path in paths if not _is_test_path(path, declared)), None):
                raise Refusal(
                    f"test commit {commit[:12]} touches source path {source}",
                    act(
                        "agent",
                        f"move {source} to the implementation task and keep this test commit tests-only",
                    ),
                )
            continue
        if test := next((path for path in paths if _is_test_path(path, declared)), None):
            raise Refusal(
                f"implementation commit {commit[:12]} touches test path {test}",
                act(
                    "agent",
                    f"move {test} to the separate RED test dispatch and keep this implementation commit source-only",
                ),
            )


def _open_children(repo: Path, name: str) -> None:
    """A rc or main tree lands only with none of the trees below its folder open."""
    folder = name.rpartition("/")[0] + "/"
    for row in ours(repo):
        if row["name"].startswith(folder) and row["name"] != name:
            raise Refusal(f"{kind_of(row['name'])} worktree {row['path']} of {branch(name)} is open",
                          command(*LAUNCH, "merge", row["path"]))  # fmt: skip


def _scaffold(tree: Path, name: str) -> None:
    """Refuses while any path under `tests/tmp/<job>/` is tracked; `<job>` is the job (a hotfix:
    the bug) of *name*, and only the index counts, never the directory on disk."""
    job = (m := NAME_RE.match(name))["job"] or m["bug"]  # type: ignore[index]
    folder = tree / "tests" / "tmp" / job
    if git(tree, "ls-files", "--", f"tests/tmp/{job}").strip():
        raise Refusal(
            f"{folder} exists: promote each test in it into its contract's home, or the operator orders its delete, before the job lands",  # fmt: skip
            act(
                "agent",
                f"promote each test in {folder} into its contract's home (a delete needs the operator's order), then commit the removal",
            ),
        )


def _tracked(tree: Path, rel: Path) -> list[Path]:
    """The copies of ledger script *rel* the tree tracks (its `verify:` ran them), else this instance's."""
    held = git(tree, "ls-files", "-z", "--", f"*/{rel.as_posix()}").split("\0")
    return [tree / h for h in held if h] or [_INSTANCE_SKILLS / rel]


def _ledgers(root: Path, repo: Path, tree: Path, scripts: Callable[[Path], list[Path]]) -> None:  # fmt: skip
    """`check` of each script *scripts* names per ledger, then the doctor; an associated repo has no `specs/`."""
    if flow_for(root, repo)["main"] != repo.name:
        return
    for script in [s for rel in _LEDGERS for s in scripts(rel)]:
        argv = [sys.executable, str(script), "check", "--specs", str(tree / "specs")]
        _relay(script.name, run(argv, cwd=tree, env=scrubbed_env(), stdin=subprocess.DEVNULL), tree)  # fmt: skip
    _relay("dadaia doctor", cli(root, "doctor", "--specs-dir", str(tree / "specs"), tree=tree), tree)  # fmt: skip


def _relay(name: str, done: subprocess.CompletedProcess[str], tree: Path) -> None:
    if done.returncode:
        print(without_fix(done.stdout + done.stderr), end="")
    relay(done, f"{name} check failed on {tree}", act("agent", f"fix the findings above in {tree} and commit them"))  # fmt: skip


def _refuse_denylisted(root: Path, tree: Path, onto: str) -> None:
    """Refuse a tree whose `onto..HEAD` carries a denylisted term: the pre-push content matcher."""
    _relay("the denylist scan", cli(root, "ci", "push-gate-check", "--onto", onto, tree=tree), tree)  # fmt: skip


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


def _moment(data: dict[str, object]) -> float | None:
    """The instant of a handoff's `produced_at`, `None` when missing, unparseable or offset-less."""
    try:
        at = datetime.fromisoformat(str(data.get("produced_at")))
    except ValueError:
        return None
    return at.timestamp() if at.tzinfo else None


def _reviews(root: Path, shas: set[str]) -> list[tuple[bool, float, str, dict[str, object]]]:
    """(unparsed, moment, path, data) of every verdict naming one of *shas*; an unreadable file
    names no sha and is skipped."""
    found = []
    for handoff, data in reviewer_records(root):
        if str(data.get("reviewed_sha")) in shas:
            moment = _moment(data)
            found.append((moment is None, moment or 0.0, str(handoff), data))
    return found


def _dispatch(tree: Path, at: str) -> str:
    return f"dispatch {REVIEWER} on {tree} at {at}; its verdict.py run writes the verdict"


def _check_approved(root: Path, tree: Path, work: str, name: str) -> None:
    """The newest reviewer handoffs naming a candidate sha decide: each must be a valid APPROVED
    whose `diff_sha256` is HEAD's. A candidate is HEAD or a sha of this branch's reflog whose
    (patch-id, message) series over *work* equals HEAD's; newest is `produced_at`, a missing or
    naive one ranks newest, and ties all decide."""
    head = git(tree, "rev-parse", "HEAD").strip()
    mine = _series(tree, work, head)
    reflog = {head, *git(tree, "reflog", "--format=%H", branch(name), check=False).split()}
    named = _reviews(root, {x for x in reflog if x == head or _series(tree, work, x) == mine})
    top = max((row[:2] for row in named), default=None)
    decided = sorted(row for row in named if row[:2] == top)
    invalid = next(
        (
            path
            for unparsed, _, path, _ in decided
            if unparsed
            or cli(
                root, "reports", "validate", path, "--reviewed-root", str(tree)
            ).returncode  # fmt: skip
        ),
        None,
    )
    said = f"the newest {REVIEWER} handoff naming HEAD {head} or a sha of its patch and message series is not a valid APPROVED (the file comes from the reviewer's verdict)"  # fmt: skip
    if invalid:
        raise Refusal(said, command(*cli_words(root, "reports", "validate", invalid, "--reviewed-root", str(tree))))  # fmt: skip
    if rejected := next((row[2] for row in decided if row[3].get("verdict") != "APPROVED"), None):
        rework = f"fix the findings of {rejected}, then {_dispatch(tree, 'its new HEAD')}"  # fmt: skip
        raise Refusal(said, act("agent", rework))
    dispatch = act("agent", _dispatch(tree, f"HEAD {head}"))
    if not decided:
        raise Refusal(said, dispatch)
    want = diff_sha256(tree, work, head)
    if any(row[3].get("diff_sha256") != want for row in decided):
        raise Refusal(f"no {REVIEWER} verdict binds the diff {head} lands", dispatch)


def digest(root: Path, path: str, sha: str) -> str:
    """The binding a verdict carries for *sha* of a worktree, as one JSON object."""
    _, tree, name, onto = _target(root, path)
    if git(tree, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}", check=False).strip() != sha:  # fmt: skip
        raise Refusal(f"{sha} is not a commit sha of {tree}", act("agent", f"pass a 40-hex commit of {tree}"))  # fmt: skip
    scope = f"{branch(name)}@{git(tree, 'rev-parse', 'HEAD').strip()}"
    return json.dumps({"root": str(root), "scope": scope, "reviewed_sha": sha, "diff_sha256": diff_sha256(tree, onto, sha)})  # fmt: skip


def _into(repo: Path, onto: str) -> Path:
    """The checkout *onto* is checked out in: its tree for a `wt/` branch, else the repo."""
    name = onto.removeprefix("wt/")
    return tree_path(repo.parents[1], repo.name, name) if onto.startswith("wt/") else repo


def _parent(repo: Path, onto: str) -> Path:
    """The checkout *onto* is checked out in; a Refusal when the parent's tree was removed by hand."""
    if not (into := _into(repo, onto)).exists():
        raise Refusal(f"{into} does not exist", reattach(repo, into, str(names.name_of(onto))))  # fmt: skip
    return into


def _kind_checks(root: Path, repo: Path, tree: Path, name: str, onto: str, into: Path) -> list[Callable[[], object]]:  # fmt: skip
    """The ordered checks a tree of this kind must pass to land, before `merge`'s ending checks."""
    ancestor = partial(_check_ancestor, root, tree, onto)
    verdict = partial(_check_approved, root, tree, onto, name)
    job_gate = partial(_gate, tree, onto)
    gate = [ancestor, verdict, job_gate]
    denylist = partial(_refuse_denylisted, root, tree, onto)
    children, scaffold = partial(_open_children, repo, name), partial(_scaffold, tree, name)
    ledgers, specs = partial(_ledgers, root, repo, tree), partial(_check_specs_only, tree, onto)
    tests = lambda: _refuse_implementation_tests(tree, onto, _target(root, str(into))[3])  # noqa: E731
    table: dict[str | None, list[Callable[[], object]]] = {
        "task": [ancestor, tests, denylist, partial(_refuse_dirty, into)],
        "main": [children, scaffold, *gate],
        "hotfix": [scaffold, ancestor, denylist, verdict, job_gate],
        "backlog": [specs, ancestor, denylist, verdict, partial(ledgers, lambda rel: [_INSTANCE_SKILLS / rel])],
        "rc": [children, *gate, partial(ledgers, partial(_tracked, tree))],
    }  # fmt: skip
    return [partial(_refuse_dirty, tree), *table[kind_of(name)]]


def _on_target(into: Path, onto: str) -> None:
    if git(into, "branch", "--show-current").strip() != onto:
        raise Refusal(f"{into} is not on {onto}", git_line(into, "switch", onto))


def merge(root: Path, path: str, keep: list[str], drop: bool) -> str:
    repo, tree, name, onto = _target(root, path)
    ref = branch(name)
    if not tree.exists() and not git(repo, "branch", "--list", ref).strip():
        _rmdir(tree, name)
        return f"{ref} merged into {onto}"
    into = _parent(repo, onto)
    if not tree.exists():  # only the branch is left
        _on_target(into, onto)
        _remove(repo, tree, onto, name, [])
        return f"{ref} merged into {onto}"
    for check in _kind_checks(root, repo, tree, name, onto, into):
        check()
    kept = _kept(tree, "merge", keep, drop)
    _on_target(into, onto)
    try:
        git(into, "merge", "-q", "--ff-only", ref)
    except RuntimeError as error:
        _check_ancestor(root, tree, onto)  # moved while merge ran; else a stray the operator owns
        fix = act("agent", f"commit or remove the paths above in {into}")
        raise Refusal(f"fast-forward failed: {error}", fix) from error
    _remove(repo, tree, onto, name, kept)
    return f"{ref} merged into {onto}"


def clean(root: Path, path: str, keep: list[str], drop: bool) -> str:
    repo, tree, name, onto = _target(root, path)
    if not any(Path(row["path"]).resolve() == tree for row in ours(repo)):
        raise Refusal(f"{tree} is not a worktree of ours", command(*LAUNCH, "list"))
    ahead = int(git(repo, "rev-list", "--count", f"{onto}..{branch(name)}"))
    if ahead:
        merge = inline(*LAUNCH, "merge", str(tree))
        raise Refusal(f"{branch(name)} holds {ahead} unmerged commit(s)",
                      act("agent", f"{_dispatch(tree, 'its HEAD')}, then run `{merge}`"))  # fmt: skip
    _refuse_dirty(tree)
    _remove(repo, tree, onto, name, _kept(tree, "clean", keep, drop))
    return f"cleaned {tree}"
