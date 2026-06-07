# PLAN — v0.2.2 Full Codex Compatibility

**Status:** Aprovado
**Release:** v0.2.2

---

## Strategy

Implement the release in seven focused tasks so each layer is independently reviewable:

1. Fix Codex transform/model projection.
2. Generate official Codex `.rules` command policy.
3. Add Codex custom-agent config mapping.
4. Update public AI surface wording for Codex subagents and harness-neutral protocol references.
5. Expand public doctor semantic checks and tests.
6. Stage/install projections and eliminate runtime drift.
7. Update memory and close/archive the release.

## Validation Matrix

| Area | Validation |
|---|---|
| Transformer | Unit/golden tests for model mapping and skill-name preservation |
| Codex TOML | Parse generated TOML; verify skill references resolve |
| Codex Rules | Verify `.codex/rules/*.rules` generated and Markdown protocols do not masquerade as executable command policy |
| Hooks | Verify generated hook commands point to existing scripts and `ctx-inject.sh` Codex JSON mode works |
| Public doctor | `dadaia public doctor` catches semantic drift |
| Projection sync | `dadaia public stage && dadaia public install --target all && dadaia public doctor` |
| SDD | `DADAIA_CONTEXT=dadaia-workspace dadaia specs doctor` |

## Risk Controls

- Keep provider/auth/telemetry out of project-local `.codex/config.toml`.
- Do not edit generated runtime projections directly; edit source and re-run public stage/install.
- Keep workflow files reference-only unless and until an executor exists.
- Do not mark tasks done until validation evidence exists.

## Rollout

1. Work on branch `feature/0.2.2-codex-compatibility`.
2. Commit task reservation.
3. Implement and test.
4. Stage/install runtime projections.
5. Close release and archive.
6. Push branch and open PR.
7. Do not merge.
