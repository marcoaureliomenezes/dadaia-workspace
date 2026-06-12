---
name: release-ship
description: project-manager dispatches the deterministic deploy sequence AFTER electing to ship an rc-N. Covers only the no-judgment gate-and-publish steps; the ship decision itself lives in PM's persona. Honesty note in body — Claude Code and Codex do not auto-load workflow files at runtime.
version: 0.1.0
schema_version: "1"
trigger: operator-elects-to-ship
owner: project-manager
activity_class: MUTATING
lifecycle_phase: Closure
inputs:
  version:
    type: string
    required: true
    description: Target release version M.m.p (the rc being shipped).
  context:
    type: string
    required: true
    description: Active spec context name for the release.
stages:
  - id: verify_ship_trio
    agent: project-manager
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-project-manager-ship-preconditions.handoff.json"
      must_include: ["qa APPROVED", "security APPROVED", "code-review APPROVED", "pytest", "dadaia ci preflight"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.version"
        as: version
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
  - id: deploy
    agent: project-manager
    needs: [verify_ship_trio]
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-project-manager-deploy.handoff.json"
      must_include: ["merge", "tag", "poetry publish", "smoke test"]
    inputs:
      - kind: stage_output
        from: stages.verify_ship_trio.output
        as: preconditions
exit_criteria:
  - all_stages: completed
---

# release-ship

The deterministic deploy gate sequence for shipping an rc-N segment. `project-manager`
runs this **only after it has decided to ship** — the ship decision is a judgment call
that lives in the PM persona, not in this file. This workflow encodes the no-judgment
mechanical sequence that follows that decision.

Cites constitution §1 matrix: **activity class MUTATING, lifecycle phase Closure** (§7
phase 8). The deploy mutates `main`, the tag namespace, and the published package — a
single MUTATING actor under the PM-held release lease (§8/§9).

> **Honesty note.** This is a dispatch-reference document. Claude Code and Codex workflow
> Markdown does not auto-execute at runtime (constitution §4). This file is read by an
> agent only when `project-manager` explicitly loads it as context. It is not a Claude Code
> or Codex runtime primitive. In Codex, fan-out requires an explicit subagent delegation
> request or a future real executor; this file alone never spawns agents.

## When to use

After the operator elects to ship at the end of an rc-N segment and the ship-trio gate
(qa → security → code-review) has all returned `APPROVED` for the rc commit.

## Steps (deterministic deploy sequence)

1. **Precondition — ship-trio approved.** All three review handoffs are present with
   `verdict: APPROVED` for the rc commit: `qa-engineer`, `security-reviewer`,
   `code-reviewer`. If any is missing or non-APPROVED, terminate and delegate to PM.
2. **Precondition — tests green on rc commit.** `pytest -p no:cacheprovider` passes on
   the rc commit. If red, terminate and delegate to PM.
3. **CI preflight.** `dadaia ci preflight` (ruff format --check, ruff check, mypy
   --strict, pytest) exits 0. If non-zero, terminate and delegate to PM.
4. **Merge.** Merge `feature/<version>` → `main` with `--no-ff` (preserve history).
5. **Tag.** `git tag v<M>.<m>.<p> <merge-commit-sha>`.
6. **Publish.** `poetry publish --build`.
7. **Smoke test.** In a clean venv: `pip install dadaia==<version>` and confirm
   `dadaia --version` matches `<version>`.

## Judgment delegation

This workflow encodes no decision about **whether** to ship — that judgment lives in the
PM persona. On any precondition failure (steps 1–3) or any judgment fork, the workflow
**terminates** and delegates back to `project-manager` with the specific failure detail
(which precondition failed, which command exited non-zero, which handoff was missing or
non-APPROVED). PM decides the next action; the workflow never improvises.

## Output

A deploy handoff under `.dadaia/handoff/<context>/` recording the merge SHA, the tag, the
publish result, and the smoke-test outcome. On termination, a precondition-failure handoff
recording exactly which gate blocked.
