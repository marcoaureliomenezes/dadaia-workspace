# TASKS — Release 0.5.3

**Status:** Aprovado

## alpha-1 (folds)

- [x] T-053-01 — Invocation adoption in hooks/container (F003) (write set: dadaia_workspace/hooks/, dadaia_workspace/container.py, dadaia_workspace/core/invocation.py, tests)
- [x] T-053-02 — Phase vocabulary one home (F007) (write set: dadaia_workspace/core/, dadaia_workspace/features/specs/doctor_release.py, dadaia_workspace/features/spec_context/gate_policy.py, tests)
- [x] T-053-03 — Release-identity fold (F004) (write set: dadaia_workspace/core/specs_version.py, dadaia_workspace/features/specs/canon.py, doctor_release.py, scaffolder.py, doctor_common.py, tests)
- [x] T-053-04 — Collapse doctor rule pairs (F005) (write set: dadaia_workspace/features/specs/doctor_structural.py, doctor_release.py, tests)
- [-] T-053-05 — Memory-canon fact folds (F011) (write set: dadaia_workspace/features/specs/doctor_memory.py, memory_lint.py, canon.py, catalog.py, tests)
- [ ] T-053-06 — One registry accessor (F008) (write set: dadaia_workspace/core/, dadaia_workspace/hooks/ctx_inject.py, tests)

## alpha-2 (extractions + projection)

- [ ] T-053-07 — decide_injection extraction (F009) (write set: dadaia_workspace/hooks/ctx_inject.py, dadaia_workspace/features/spec_context/, tests)
- [ ] T-053-08 — SessionBinding deep module (F002) (write set: dadaia_workspace/core/session_store.py or new core module, dadaia_workspace/cli/commands/context.py, dadaia_workspace/features/spec_context/doctor.py, gate_policy.py, tests)
- [ ] T-053-09 — service.py scope extraction (F013) (write set: dadaia_workspace/features/spec_context/service.py, dadaia_workspace/infrastructure/privacy_check.py, tests)
- [ ] T-053-10 — Projection single decider (F006) (write set: dadaia_workspace/infrastructure/projection_rules.py, codex_doctor.py, workspace_guardrail.py, public_assets.py, tests)
- [ ] T-053-11 — codex_doctor relocation + dead code (F014) (write set: dadaia_workspace/infrastructure/, tests)

## alpha-3 (residue + container + bug)

- [ ] T-053-12 — Honesty residue (F015/F016) (write set: dadaia_workspace/cli/commands/ci.py, dadaia_workspace/infrastructure/python_env.py, dadaia_workspace/core/handoff_index.py, tests)
- [ ] T-053-13 — Bug component vocabulary (F017) (write set: dadaia_workspace/features/bugs/, dadaia_workspace/cli/commands/bugs.py, tests)
- [ ] T-053-14 — Container dissolution (F001) (write set: dadaia_workspace/container.py, dadaia_workspace/features/panel/, dadaia_workspace/cli/, dadaia_workspace/core/protocols/, dadaia_workspace/infrastructure/process_ancestry_adapter.py, tests)
- [ ] T-053-15 — Scoped-law shipped-hashes coverage + repair (picked bug) (write set: dadaia_workspace/features/specs/template_history.py, doctor_structural.py, features/migrate/upgrade.py, public/templates/shipped-hashes.json, specs/releases/AGENTS.md, specs/audits/AGENTS.md, tests)

## alpha-4 (the deep model)

- [ ] T-053-16 — SpecsTree parsed model + rule registry (F010/F012) (write set: dadaia_workspace/features/specs/, dadaia_workspace/cli/commands/specs.py, tests)

## closure

- [ ] T-053-17 — Disposition sweep + audit archive (write set: specs/audits/**)
- [ ] T-053-18 — Memory update + CONTEXT.md + closure + CHANGELOG + pyproject (write set: specs/memory/, CONTEXT.md, specs/releases/0.5.3/RELEASE.json, CHANGELOG.md, pyproject.toml)
