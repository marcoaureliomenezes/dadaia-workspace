# CLOSURE — v0.2.2 Full Codex Compatibility

**Status:** Aprovado
**Release:** v0.2.2
**Closed:** 2026-06-07

## Summary

v0.2.2 makes the Codex projection operational instead of approximate:

- Codex agent generation preserves real skill identifiers such as `ai-harness-claude-code`.
- Claude model identifiers are mapped only where they are model identifiers.
- Codex receives native custom-agent TOML with `sandbox_mode` and `model_reasoning_effort`.
- Codex receives native Starlark command policy in `.codex/rules/dadaia-command-policy.rules`.
- Markdown behavioral protocols are not installed as executable Codex Rules.
- `dadaia public doctor` detects fake/missing Codex skill references, stale Claude model/path leaks, bad rules shape, hook shape drift, and missing TOML boundary fields.
- Memory now records the invariant that Codex custom agents are real configured delegates while workflow Markdown does not auto-execute.

## Validations

| Check | Command | Result |
|---|---|---|
| Codex/public regression slice | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/unit/infrastructure/runtime_transforms/test_codex_transform.py repos/dadaia-workspace/tests/unit/infrastructure/test_public_assets.py repos/dadaia-workspace/tests/integration/test_public_assets.py repos/dadaia-workspace/tests/integration/features/public/test_doctor_codex_checks.py repos/dadaia-workspace/tests/contract/test_codex_reference_only_wording.py` | PASS — 257 passed |
| Live projection drift | `DADAIA_CONTEXT=dadaia-workspace .dadaia/.venv/bin/dadaia public stage && DADAIA_CONTEXT=dadaia-workspace .dadaia/.venv/bin/dadaia public install --target all --force && DADAIA_CONTEXT=dadaia-workspace .dadaia/.venv/bin/dadaia public doctor` | PASS — no missing/drift/error/leak; expected git-dirty warnings for this branch |
| Spec/memory gate | `DADAIA_CONTEXT=dadaia-workspace .dadaia/.venv/bin/dadaia specs doctor` | PASS — 0 errors; 9 pre-existing warning lines, reduced to 6 warn-only atoms after memory estimate fix |

## Drifts

No unresolved Codex projection drift remains. The instantiated workspace at
`/home/marco/workspace/dadaia/` was restaged and reinstalled from the library source, and
`dadaia public doctor` returned no missing, drift, error, or leak findings.

Known unrelated warnings remain in specs doctor for older archived release names and
pre-existing memory heading allowlist warnings.

## Memory updates

Updated current product truth:

- `specs/memory/product/agents/agent-orchestration.md`
- `specs/memory/product/agents/agent-sdd-alignment.md`
- `specs/memory/product/agents/ai-harness-codex.md`
- `specs/memory/product/platform/multi-platform-parity.md`
- `specs/memory/product/catalog.json`
- `specs/memory/product/index.md`

## Archive Notes

This release was intentionally not merged. The branch must be pushed and a PR opened for review.
