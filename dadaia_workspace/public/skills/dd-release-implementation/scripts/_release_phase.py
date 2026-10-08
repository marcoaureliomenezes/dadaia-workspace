#!/usr/bin/env python3
"""`release.py phase` — the two in-candidate transitions a release walks.

`phase` is the ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5): the phase
and its milestone move in one act, so they cannot disagree.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_schema import (  # noqa: E402
    APPROVED,
    CANDIDATE_DOCS,
    SHA_RE,
    STATE,
    current_job_writes,
    current_plan_jobs,
    extract_status,
    job_errors,
    plan_errors,
    utc_now,
)
from _release_store import SCRIPT, Live, Refusal, State, commit, live_release  # noqa: E402
from _specs import choice  # noqa: E402

#: DEFINITION is `new`'s; each later phase has one predecessor (out-of-order = re-run).
PREDECESSOR = {"IMPLEMENTATION": "DEFINITION", "CLOSURE": "IMPLEMENTATION"}


def _refuse_unapproved_docs(live: Live) -> Path:
    """A candidate enters IMPLEMENTATION only with SPEC and PLAN `Approved`; returns the
    candidate folder that holds them (no folder yet: `rc-1/` is where they belong)."""
    candidate = live.candidate or live.release_dir / "rc-1"
    for name in CANDIDATE_DOCS:
        document = candidate / name
        if not document.is_file():
            raise Refusal(
                f"release {live.release_id} has no {document.relative_to(live.release_dir).as_posix()}",
                f"Operator action: write {document.resolve()} carrying '**Status:** {APPROVED}'",
            )
        status = extract_status(document.read_text(encoding="utf-8"))
        if status != APPROVED:
            raise Refusal(
                f"{document.relative_to(live.release_dir).as_posix()} of release {live.release_id} "
                f"carries status {status!r} — SPEC and PLAN "
                f"must both be '**Status:** {APPROVED}' to enter IMPLEMENTATION",
                f"Operator action: set '**Status:** {APPROVED}' in {document.resolve()}",
            )
    return candidate


def _refuse_open_worktrees(specs: Path) -> None:
    """ADR 0128 (4): a candidate closes with every `wt/*` of its repo merged or cleaned — read
    from the owner's rows (imported, ADR 0135), sparing the tree closure runs from."""
    from _ledger import workspace_of

    root = workspace_of(specs)
    if root is None:  # no workspace holds this tree: there is no worktree to wait for
        return
    sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts"))
    import _worktree_git as worktree_git  # the worktrees' owner, read-only (ADR 0135)
    from _worktree_names import Refusal as WorktreeRefusal

    top = worktree_git.git(specs, "rev-parse", "--path-format=absolute", "--show-toplevel",
                           "--git-common-dir", check=False).split() or ["", ""]  # fmt: skip
    try:
        found = worktree_git.rows(root)
    except WorktreeRefusal as error:
        raise Refusal(f"worktree rows unreadable: {error}", error.fix) from error
    repo = Path(top[1]).parent.name
    held = [r for r in found if r["repo"] == repo and r["exit"]
            and Path(str(r["path"])).resolve() != Path(top[0]).resolve()]  # fmt: skip
    if held:
        raise Refusal(f"repos/{repo} still holds {len(held)} open wt/* worktree(s) — a "
                      "candidate closes with every one merged", str(held[0]["exit"]))  # fmt: skip


#: The one verb that moves each phase forward — every refusal's fix names it, so a fix
#: never names a verb that refuses in the same state.
NEXT = {"DEFINITION": "phase IMPLEMENTATION", "IMPLEMENTATION": "phase CLOSURE", "CLOSURE": "ship"}
#: `ship`'s one optional value no code knows: the promote PR's number, when the host has one.
SHIP_PR = "with --pr set to the promote PR's number, when the host has one"
#: What the operator supplies to each NEXT verb that the code cannot fill (ADR 0158).
SUPPLY = {"CLOSURE": SHIP_PR}


def set_phase(specs: Path, phase: str, sha: str) -> tuple[str, str]:
    """Move the live release to *phase* and stamp its milestone."""
    if not SHA_RE.match(sha):
        raise Refusal(
            f"--sha {sha!r} is not a 7-40 character lowercase hex commit sha",
            f"{SCRIPT} phase {phase} --sha $(git rev-parse --short HEAD)",
        )
    live = live_release(specs)
    current = str(live.state.get("phase"))
    if PREDECESSOR.get(phase) != current:
        refusal = Refusal(
            f"release {live.release_id} is in phase {current!r} — `phase` writes "
            "IMPLEMENTATION after DEFINITION and CLOSURE after IMPLEMENTATION, once each",
            f"{SCRIPT} {NEXT.get(current, 'check')} --sha {sha}",
        )
        raise choice(refusal, SUPPLY.get(current, ""))
    ts, candidate = utc_now(), live.candidate
    if phase == "IMPLEMENTATION":
        candidate = _refuse_unapproved_docs(live)
        plan = (candidate / "PLAN.md").resolve()
        text = plan.read_text(encoding="utf-8")
        planned, errors = current_plan_jobs(text)
        if errors:
            raise Refusal(errors[0], f"Operator action: correct the as-is review and DAG in {plan}")
        if planned is None and (errors := plan_errors(text)):
            raise Refusal(errors[0], f"Operator action: correct the as-is review and DAG in {plan}")
        authorities: dict[str, set[str]] = {}
        for job in sorted(candidate.glob("tasks/*.md")):
            job_text = job.read_text(encoding="utf-8")
            if errors := job_errors(job_text, f"tasks/{job.name}"):
                raise Refusal(errors[0], f"Operator action: correct {job.resolve()} "
                              "(dd-release-definition §5)")  # fmt: skip
            writes, _ = current_job_writes(job_text, f"tasks/{job.name}")
            if writes is not None:
                number = job.stem.removeprefix("job")
                if not number.isdigit() or number.startswith("0"):
                    raise Refusal(
                        f"current task authority {job.name} is not named job<n>.md",
                        f"Operator action: rename {job.resolve()} to its canonical job<n>.md name",
                    )
                authorities[f"Job {int(number)}"] = writes
        if planned is not None:
            implementation = {job: row for job, row in planned.items() if job != "Reconciliation"}
            if set(implementation) != set(authorities):
                raise Refusal(
                    "PLAN.md DAG jobs do not equal the current tasks/job<n>.md authorities",
                    f"Operator action: make every current job appear exactly once in {plan}",
                )
            for plan_job, (_, planned_writes) in implementation.items():
                if planned_writes != authorities[plan_job]:
                    raise Refusal(
                        f"PLAN.md DAG {plan_job} `W:` is not its exact task-file union",
                        f"Operator action: set {plan_job}'s exact `W:` in {plan} from tasks/job{plan_job.split()[-1]}.md",
                    )
            if errors := plan_errors(text):
                raise Refusal(
                    errors[0], f"Operator action: correct the as-is review and DAG in {plan}"
                )
    else:
        _refuse_open_worktrees(specs.resolve())

    milestone = "defined" if phase == "IMPLEMENTATION" else "implemented"
    rc = {"candidate": candidate.name} if candidate else {}

    def apply(state: State) -> State:
        # The slot is the live candidate's stamp; the `milestone` entry is its history (F061).
        state[milestone] = {"sha": sha, "ts": ts}
        state.setdefault("log", []).append({
            "ts": ts, "agent": "release.py", "kind": "milestone", **rc,
            "milestone": milestone, "sha": sha,
            "text": f"Candidate {milestone} at {sha}; phase {phase}."})  # fmt: skip
        state["phase"] = phase
        return state

    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}", apply)
    return live.release_id, ts
