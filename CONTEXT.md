# dadaia-workspace

The library that scaffolds and governs a dadaia workspace. Each entry is a term and the words to avoid for it; every rule lives in the law file that owns it (the root `AGENTS.md` and its scoped files, `specs/constitution.md`).

## Workspace

**Workspace**:
The root tree that holds `.dadaia/`, `repos/` and every projection.
_Avoid_: root (bare), instance root, ws dir

**Repo**:
One checked-out repository under `repos/<repo_slug>/`.
_Avoid_: project, root

**Context**:
One `specs/` tree registered under a `context_name`. The model's window is "context window".
_Avoid_: spec context project, registry row, slug (for the name), context (bare) for the model's window

**Session**:
One harness process, identified by its `session_id`.
_Avoid_: sid ladder, CLI-minted session, thread id

**Bind**:
The session record naming the context a session works in.
_Avoid_: alive flag, lease, lock, bind mode, bind release

**Fix line**:
The one runnable line a finding, refusal or onboarding step prints after its `fix:` label.
_Avoid_: hint, remedy text

**Worktree**:
A canonical git worktree under `worktrees/<repo>/`; its rules are in `worktrees/AGENTS.md`.
_Avoid_: sandbox, harness worktree, plain, define or reconcile tree (retired)

## Enforcement

**Gate**:
The one PreToolUse chain that decides whether a harness write proceeds.
_Avoid_: hook (for the chain), guard (for the chain)

**Hook**:
A harness-invoked script, the transport that calls the gate.
_Avoid_: gate, chokepoint

**Chokepoint**:
A git hook or CI job that validates at the Publication boundary.
_Avoid_: hook, guard

**Publication boundary**:
The push, where a blob becomes public.
_Avoid_: release boundary, publish step, baseline (for a tolerated literal)

**Path class**:
The category a written path belongs to: ADDITIVE, MUTATING or PROTECTED.
_Avoid_: lane, MEMORY, LAW, UNGATED, FROZEN (retired classes)

**Scope**:
The repo set one Bind owns.
_Avoid_: ownership, lease, territory, allowlist (for the repo set)

**Zone**:
One top-level `.dadaia/` directory, a row of `DADAIA_ZONES` in `core/workspace_layout.py`.
_Avoid_: folder, area, lane, path class (the gate's category)

## Projection

**Asset**:
A library-owned file under `dadaia_workspace/public/`, the source of every projection.
_Avoid_: template (except for rendered scaffolds), public file

**Projection**:
An asset rendered for one harness into a runtime tree.
_Avoid_: install target, stage copy, agentic file

**Harness**:
An entry AI runtime with its own projection directory.
_Avoid_: target, runtime, agent-target, tool

**Drift**:
A projection whose bytes differ from its render. Memory drift is always written qualified.
_Avoid_: parity, mismatch, stale copy, drift (bare) for memory drift

## Specs

**Canon**:
The closed set of paths a `specs/` tree may contain.
_Avoid_: schema (for paths), layout, tree version

**Record**:
One JSONL line in a store: a bug, a backlog exit, a finding, a decision.
_Avoid_: event, entry, row

**Terminal**:
A record's final status, reached only through a transition.
_Avoid_: closed, dispositioned, done

**Release**:
The open-scope publication unit; its state is `_RELEASE.json`.
_Avoid_: "release" for one closed scope (that is a Candidate)

**Candidate**:
One closed-scope SDD cycle inside the live Release, in `specs/releases/<v>/rc-<N>/`.
_Avoid_: version (for the unit), sprint, "rc" as a branch name or a fixes-only round

**As-is review**:
The read-only reading of every unit a picked set touches, ending in the PLAN's one verdict per unit.
_Avoid_: audit (the three-pillar review), inventory, survey

**Memory drift**:
A product atom whose sources changed while the atom was not reconciled. Always qualified.
_Avoid_: stale memory, drift (bare)

**Bug window**:
The resolved fixes an rc's SPEC judges in its `## Bug window review`. It judges fixes and schedules no work.
_Avoid_: wave, pile, cause group (retired)

## Output and doctor

**Handoff**:
The machine-readable JSON completion record an agent emits under `.dadaia/handoff/`.
_Avoid_: sidecar, result file

**Doctor**:
`.dadaia/.venv/bin/dadaia doctor`, the one validator and reaper; `public doctor` is the only other, always qualified.
_Avoid_: specs doctor, backlog doctor (retired), checker, linter (for doctors), audit (for doctors)

## Work units and homonyms

**Authority**:
The one symbol, command or file answering a question; every other reader consults it.
_Avoid_: owner, source of truth (bare)

**Job**:
One measured feature in one `wt-main` worktree.
_Avoid_: CI job (a GitHub Actions job)

**Task**:
One exact `W:` set and AC; the unit of dispatch.
_Avoid_: ticket, story

**Quarantine**:
The pytest mark that parks a flaky test. A bug is never "quarantined".
_Avoid_: quarantine for any bug state

**Workflow**:
A GitHub Actions workflow file; the SDD sequence is "the flow".
_Avoid_: workflow for the flow or for the retired engine
