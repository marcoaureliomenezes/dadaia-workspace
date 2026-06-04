# Closure: Release — v0.1.4.3

> **Status:** Aprovado
> **Release ID:** v0.1.4.3
> **Owner:** product-engineer
> **Closed:** 2026-06-04

## Summary

This release establishes `.dadaia/handoff/<context>/` as the canonical home for
machine-readable agent handoffs. Human reports remain under
`.dadaia/reports/<context>/<agent>/`, while downstream agents, validation tools,
`reports next`, and review gates consume handoff JSON from the new context-scoped
handoff root.

The release also hardens validation and closure gates: handoff validation now
includes bounded artifact hash checks, panel report links remain report-relative,
and the QA/security verdict gate rejects stale, wrong-agent, same-file, or wrong
release handoffs.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-HANDOFF-01 | Add canonical `.dadaia/handoff/AGENTS.md` public projection. | `cd36043` |
| T-HANDOFF-02 | Update public agentic instructions to emit handoffs under `.dadaia/handoff/<context>/`. | `b7b944e` |
| T-HANDOFF-03 | Update validation discovery, hash resolution, and verdict search defaults. | `18fc771` |
| T-HANDOFF-04 | Verify and harden panel, reports-next, hash validation, and review gates. | `b707951` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Handoff model and validation service | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/test_handoff_models.py tests/unit/test_reports_validation_service.py` | ```text
15 passed in 1.10s
``` |
| Handoff schema and CLI validation contracts | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/test_handoff_schema_contract.py tests/contract/cli/test_cli_reports.py` | ```text
13 passed in 5.06s
``` |
| Public asset projection contracts | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/infrastructure/test_public_assets.py` | ```text
195 passed in 2.78s
``` |
| Panel report/handoff linkage | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/features/panel/test_api_contract.py` | ```text
11 passed in 1.47s
``` |
| Expanded regression suite after review fixes | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/test_reports_validation_service.py tests/contract/test_handoff_schema_contract.py tests/contract/cli/test_cli_reports.py tests/unit/features/panel/test_api_contract.py tests/integration/test_cli_reports_next.py` | ```text
42 passed in 4.57s
``` |
| Verdict gate smoke for matching, same-file, wrong-agent, and stale-release handoffs | `HANDOFF_DIR=<tmp> RELEASE_ID=v0.1.4.3 CONTEXT=dadaia-workspace bash scripts/check-verdict.sh` | ```text
matching handoffs passed; same-file, wrong-agent, and stale-release handoffs rejected
``` |
| Required reviewer gate | QA, code-reviewer, and security-reviewer read-only re-reviews against `bbe196c` | ```text
qa-engineer: APPROVE
code-reviewer: APPROVE
security-reviewer: APPROVE
``` |

## Drifts

### panel-and-reports-next-canonical-root

**Description:** The original plan focused on validation discovery and public
instructions. Review found that `dadaia panel` and `dadaia reports next` also
depended on report-adjacent handoffs.

**Resolution:** Panel now reads handoffs from `.dadaia/handoff/`, returns
report-relative paths for serve/delete routes, and deletes matching handoffs by
`artifact.path`. `reports next` now scans `.dadaia/handoff/<context>/` by
`agent` and `release_id`.

**Memory updates:** `specs/memory/product/agent-comms.md`.

### security-gate-hardening

**Description:** Security review identified that artifact hash resolution and
the QA/security verdict gate needed stronger boundaries than the initial plan
spelled out.

**Resolution:** `artifact.path` rejects absolute paths and parent traversal;
hash resolution is workspace-bounded; hash mismatch/missing artifacts invalidate
handoffs when `artifact.path` is present. The verdict gate requires distinct
QA/security files with matching `agent`, `release_id`, optional `context`, and
`APPROVED` verdict.

**Memory updates:** `specs/memory/product/agent-comms.md`.

## Memory updates

- `specs/memory/product/agent-comms.md` — updated current handoff truth:
  canonical `.dadaia/handoff/<context>/` root, bounded hash validation, panel
  and reports-next consumers, and QA/security verdict-gate semantics.
- `specs/memory/product/public-asset-distribution.md` — updated scoped AGENTS
  list to include `.dadaia/handoff/AGENTS.md` separately from reports.
- `specs/memory/product/index.md` — no change: catalog entry already points to
  `agent-comms` and did not need new feature registration.
- `specs/memory/architecture.md` — no change: release did not alter architecture
  boundaries or dependencies.
- `specs/memory/tech-stack.md` — no change: release added no runtime dependency.

## Backlog returns

None.

## Archive decision

**MOVE** — release directory will be moved to
`specs/_archive/releases/v0.1.4.3/`. `ACTIVE.md` will be updated to
`release: none` / `phase: none`.
