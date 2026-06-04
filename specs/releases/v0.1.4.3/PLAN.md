# PLAN: v0.1.4.3 - handoff-directory-contract

**Status:** Aprovado
**Release ID:** v0.1.4.3
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Strategy

Keep human report storage and machine handoff storage separate. Update the
runtime contract first, then update code paths and tests that discover or
validate handoff JSON.

## 2. Design

### Runtime layout

Path | Purpose
---|---
`.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html` | Human-readable report
`.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json` | Machine-readable handoff
`.dadaia/handoff/AGENTS.md` | Scoped contract for writing and reading handoffs

### Handoff file rule

The handoff JSON continues to use the current schema. Its `artifact.path`
points to the report or other artifact being handed off. For report handoffs,
that value is normally a workspace-relative `.dadaia/reports/...` path.

### Validation rule

`dadaia reports validate --all` uses `.dadaia/handoff/` as the default discovery
root. Explicit file or directory paths remain honored for backward
compatibility.

Hash verification resolves workspace-relative artifact paths from the workspace
root, not from the handoff file directory.

## 3. Execution Order

```text
T-HANDOFF-01 -> T-HANDOFF-02 -> T-HANDOFF-03 -> T-HANDOFF-04
```

## 4. Validation

Run:

```bash
poetry run python -m pytest -q -p no:cacheprovider tests/unit/test_handoff_models.py tests/unit/test_reports_validation_service.py
poetry run python -m pytest -q -p no:cacheprovider tests/contract/test_handoff_schema_contract.py tests/contract/cli/test_cli_reports.py
poetry run python -m pytest -q -p no:cacheprovider tests/unit/infrastructure/test_public_assets.py
```
