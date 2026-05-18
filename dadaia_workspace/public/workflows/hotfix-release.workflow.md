---
name: hotfix-release
description: "Hotfix release lifecycle. qa-engineer or operator files a candidate in specs/backlog/candidates.md `## Hotfixes pendentes`; project-manager promotes it to a PATCH release (v<M>.<m>.<patch+1>) and dispatches product-engineer for SPEC entry; implementer applies the fix; qa-engineer validates with smoke; product-engineer closes. Memory updates are optional — required only if the fix changes operator-visible product behavior."
version: 0.2.0
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
    default: software-engineer
    description: Which engineer applies the fix. One of frontend-engineer, backend-engineer, software-engineer, game-developer.
stages:
  - id: file_hotfix_candidate
    agent: qa-engineer
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-hotfix-candidate.html"
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
    expected_output:
      path: ".dadaia/reports/{context}/project-manager/{run_ts}-hotfix-promote.html"
      must_include: ["PATCH version assigned", "ACTIVE.md updated"]
    inputs:
      - kind: stage_output
        from: stages.file_hotfix_candidate.output
        as: candidate_report

  - id: spec_entry
    agent: product-engineer
    needs: [promote_to_release]
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
    expected_output:
      path: ".dadaia/reports/{context}/{implementer_agent}/{run_ts}-hotfix-implementation.html"
      must_include: ["Smoke test", "All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.spec_entry.output
        as: hotfix_spec

  - id: close_with_smoke
    agent: qa-engineer
    needs: [apply_fix]
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-hotfix-smoke.html"
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
   --patches <affected_release> --severity <severity>`, and updates
   `specs/releases/ACTIVE.md`.
3. **spec_entry** — `product-engineer` authors the formal `SPEC.md` for the
   new hotfix release using the promote report as input.
4. **apply_fix** — the chosen implementer reserves a task in
   `specs/releases/<version_id>/TASKS.md` (marker `[-]`), applies the minimum
   change, runs the local smoke test, commits, marks `[x]`.
5. **close_with_smoke** — `qa-engineer` validates with a post-deploy smoke
   evidence-triple (description, command, evidence). Gated by operator-approval.
6. **closure_write** — `product-engineer` writes `CLOSURE.md`. After approval:
   `git mv` to `specs/_archive/releases/` and reset `ACTIVE.md`.

When to use `bug-fix-fastlane` instead:

- Fix does NOT touch `specs/memory/product/*.html`
- No release versioning needed (no PATCH bump)
- Operator decides the fix is too small to warrant a release

Fastlane vs. hotfix-release is a routing decision documented in the fastlane
workflow header (D10 in sdd-hotfix-track-v1 SPEC).
