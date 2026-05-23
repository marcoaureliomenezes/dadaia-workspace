---
name: hotfix-release
description: "Hotfix release lifecycle. qa-engineer or operator files a candidate in specs/backlog/candidates.md `## Hotfixes pendentes`; project-manager promotes it to a PATCH release (v<M>.<m>.<patch+1>) and dispatches product-engineer for SPEC entry; the chosen implementer applies the fix; qa-engineer validates with smoke; product-engineer closes. Implementer slot is selected from {software-engineer-python, software-engineer-node, data-engineer, data-analyst, ai-engineer, frontend-engineer, backend-engineer, devops-engineer, game-developer, game-designer, game-tester} based on the file paths the fix touches. Memory updates are optional — required only if the fix changes operator-visible product behavior."
version: 0.3.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context (workspace or repo slug).
  affected_release:
    type: string
    required: true
    description: "Most recent feature release id whose PATCH digit is incremented (e.g. v1.1.0 produces v1.1.1)."
  severity:
    type: string
    required: true
    description: One of LOW, MEDIUM, HIGH, CRITICAL.
  implementer_agent:
    type: string
    required: false
    default: software-engineer-python
    description: "Which engineer applies the fix. Selected by project-manager (or operator) from the path → agent triage table in the workflow body. Allowed values: software-engineer-python, software-engineer-node, data-engineer, data-analyst, ai-engineer, frontend-engineer, backend-engineer, devops-engineer, game-developer, game-designer, game-tester."
stages:
  - id: file_hotfix_candidate
    agent: qa-engineer
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-hotfix-candidate.handoff.json"
      must_include: ["Affected release", "Suggested PATCH"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.affected_release"
        as: affected_release
      - kind: workflow_input
        from: "$.inputs.severity"
        as: severity

  - id: promote_to_release
    agent: project-manager
    needs: [file_hotfix_candidate]
    consumes:
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-hotfix-candidate.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/project-manager/{run_ts}-hotfix-promote.handoff.json"
      must_include: ["PATCH version assigned", "ACTIVE.md updated"]
    inputs:
      - kind: stage_output
        from: stages.file_hotfix_candidate.output
        as: candidate_report

  - id: spec_entry
    agent: product-engineer
    needs: [promote_to_release]
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-hotfix-promote.handoff.json"
    expected_output:
      path: "specs/releases/{run_version_id}/SPEC.md"
      must_include: ["Patches release", "Incident summary"]
    inputs:
      - kind: stage_output
        from: stages.promote_to_release.output
        as: promote_report

  - id: apply_fix
    agent: "{{implementer_agent}}"
    needs: [spec_entry]
    consumes:
      - "specs/releases/{run_version_id}/SPEC.md"
    expected_output:
      path: ".dadaia/reports/{context}/{implementer_agent}/{run_ts}-hotfix-implementation.handoff.json"
      must_include: ["Smoke test", "All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.spec_entry.output
        as: hotfix_spec

  - id: close_with_smoke
    agent: qa-engineer
    needs: [apply_fix]
    consumes:
      - ".dadaia/reports/{context}/{implementer_agent}/{run_ts}-hotfix-implementation.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-hotfix-smoke.handoff.json"
      must_include: ["Validations", "post-deploy smoke"]
    inputs:
      - kind: stage_output
        from: stages.apply_fix.output
        as: implementation_report
    gate:
      kind: operator-approval
      prompt: "Approve hotfix smoke evidence before product-engineer writes CLOSURE?"

  - id: closure_write
    agent: product-engineer
    needs: [close_with_smoke]
    consumes:
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-hotfix-smoke.handoff.json"
    expected_output:
      path: "specs/releases/{run_version_id}/CLOSURE.md"
      must_include: ["Validations", "post-deploy smoke"]
    inputs:
      - kind: stage_output
        from: stages.close_with_smoke.output
        as: smoke_report

exit_criteria:
  - all_stages: completed
---

# hotfix-release

Lifecycle for a hotfix release (PATCH bump on the most recent feature release).
Per `sdd-hotfix-track-v1` SPEC (D2/D3/D4): hotfix MUST come through backlog;
folder name is `v<MAJOR>.<MINOR>.<PATCH>` with PATCH≥1; status ladder is the
canonical `Draft → Em revisão → Aprovado` (no hotfix-specific ladder).

The 6 stages map to the SDD hotfix flow (v0.2.0: PM + PE separation):

1. **file_hotfix_candidate** — `qa-engineer` (or operator manually) files a
   stub HTML report describing the incident: failing scenario, affected
   release, suggested PATCH bump, severity. A bullet must also be appended to
   `specs/backlog/candidates.md` under `## Hotfixes pendentes` (audited by
   `dadaia specs doctor` SPEC-DOC-012 extended).
2. **promote_to_release** — `project-manager` assigns the next PATCH version
   (e.g. v1.1.0 → v1.1.1), moves the backlog bullet to `## Histórico`,
   scaffolds the release via `dadaia specs hotfix open <version-id>
   --patches <affected_release> --severity <severity>`, updates
   `specs/releases/ACTIVE.md`, **and triages the implementer slot** by
   inspecting the file paths the fix will touch and matching them against the
   path → agent table below. The chosen agent name is passed to the
   `apply_fix` stage via the `implementer_agent` workflow input.
3. **spec_entry** — `product-engineer` authors the formal `SPEC.md` for the
   new hotfix release using the promote report as input.
4. **apply_fix** — the chosen implementer reserves a task in
   `specs/releases/<version_id>/TASKS.md` (marker `[-]`), applies the minimum
   change, runs the local smoke test, commits, marks `[x]`.
5. **close_with_smoke** — `qa-engineer` validates with a post-deploy smoke
   evidence-triple (description, command, evidence). Gated by operator-approval.
6. **closure_write** — `product-engineer` writes `CLOSURE.md`. After approval:
   `git mv` to `specs/_archive/releases/` and reset `ACTIVE.md`.

## Triage — pick the implementer

The `apply_fix` stage instantiates exactly one of the eleven leaf implementer agents.
Selection is driven by the file paths the hotfix touches. project-manager runs the
triage during `promote_to_release` and records the chosen agent in the promote report so
the dispatch in `apply_fix` is unambiguous.

| Path family the fix touches | Implementer dispatched |
|---|---|
| `*.py`, `pyproject.toml`, `poetry.lock`, Python scripts, `dadaia_workspace/{features,infrastructure,cli,core}/**` | `software-engineer-python` |
| Node server-side (`package.json` without browser bundler, CLIs, agent runtimes, `*.mjs`, server-side `*.ts`/`*.js`) | `software-engineer-node` |
| `*.sql`, `**/databricks/**`, `**/dabs/**` excluding `**/dabs/dashboards/**`, `**/notebooks/**`, `**/pipelines/**` | `data-engineer` |
| `**/dashboards/**`, `**/genie/**`, `**/bi/**`, `**/dabs/dashboards/**` | `data-analyst` |
| `dadaia_workspace/public/{skills,rules,workflows,commands,agents,hooks}/**` (AI-entity surface) | `ai-engineer` |
| `*.tsx`, `*.jsx`, browser-targeted `*.ts`/`*.js`, `*.css`, `*.html`, `*/frontend/`, `*/client/`, `*/web/`, `*/ui/` | `frontend-engineer` |
| `*.go`, `go.mod`, `go.sum`, production DB integrations (non data-pipeline) | `backend-engineer` |
| `.github/workflows/*.yml`, CI/CD config, Docker base-image bumps that change pipeline shape | `devops-engineer` |
| `repos/redacted-slug/**` — gameplay logic, mechanics, IA, physics | `game-developer` |
| `repos/redacted-slug/**` — assets, materials, maps, audio | `game-designer` |
| `repos/redacted-slug/**` — engine test automation + evidence reports | `game-tester` |

Triage rules:

1. **Exactly one path family touched → single implementer**. Standard hotfix flow.
2. **Two or more path families touched → reconsider scope**. A multi-surface fix usually
   indicates the operator should open a regular feature release (use
   `cross-cutting-feature` workflow) rather than a hotfix. If the operator confirms
   single-release urgency, project-manager dispatches the implementers sequentially —
   never in parallel inside a hotfix, because the smoke evidence must remain coherent.
3. **Game subdomain conflicts** — when a hotfix touches `repos/redacted-slug/**` and spans
   logic + assets, the three game agents triage among themselves per
   `game-agents-coordination` rule; one of them owns the `apply_fix` stage and the
   others are consulted via report.
4. **Default** — if the path family is ambiguous, project-manager defaults to
   `software-engineer-python` (the workflow input default) and documents the choice in
   the promote report. The operator may override before `apply_fix` starts.

## When to use `bug-fix-fastlane` instead

- Fix does NOT touch `specs/memory/product/*.html`
- No release versioning needed (no PATCH bump)
- Operator decides the fix is too small to warrant a release

Fastlane vs. hotfix-release is a routing decision documented in the fastlane
workflow header (D10 in sdd-hotfix-track-v1 SPEC).
