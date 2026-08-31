# TASKS — Release 0.5.3

**Status:** Aprovado

## alpha-1 (folds)

- [x] T-053-01 — Invocation adoption in hooks/container (F003) (write set: dadaia_workspace/hooks/, dadaia_workspace/container.py, dadaia_workspace/core/invocation.py, tests)
- [x] T-053-02 — Phase vocabulary one home (F007) (write set: dadaia_workspace/core/, dadaia_workspace/features/specs/doctor_release.py, dadaia_workspace/features/spec_context/gate_policy.py, tests)
- [x] T-053-03 — Release-identity fold (F004) (write set: dadaia_workspace/core/specs_version.py, dadaia_workspace/features/specs/canon.py, doctor_release.py, scaffolder.py, doctor_common.py, tests)
- [x] T-053-04 — Collapse doctor rule pairs (F005) (write set: dadaia_workspace/features/specs/doctor_structural.py, doctor_release.py, tests)
- [x] T-053-05 — Memory-canon fact folds (F011) (write set: dadaia_workspace/features/specs/doctor_memory.py, memory_lint.py, canon.py, catalog.py, tests)
- [x] T-053-06 — One registry accessor (F008) (write set: dadaia_workspace/core/, dadaia_workspace/hooks/ctx_inject.py, tests)

## alpha-2 (extractions + projection)

- [x] T-053-07 — decide_injection extraction (F009) (write set: dadaia_workspace/hooks/ctx_inject.py, dadaia_workspace/features/spec_context/, tests)
- [x] T-053-08 — SessionBinding deep module (F002) (write set: dadaia_workspace/core/session_store.py or new core module, dadaia_workspace/cli/commands/context.py, dadaia_workspace/features/spec_context/doctor.py, gate_policy.py, tests)
- [x] T-053-09 — service.py scope extraction (F013) (write set: dadaia_workspace/features/spec_context/service.py, dadaia_workspace/infrastructure/privacy_check.py, tests)
- [x] T-053-10 — Projection single decider (F006) (write set: dadaia_workspace/infrastructure/projection_rules.py, codex_doctor.py, workspace_guardrail.py, public_assets.py, tests)
- [x] T-053-11 — codex_doctor relocation + dead code (F014) (write set: dadaia_workspace/infrastructure/, tests)

## alpha-3 (residue + container + bug)

- [x] T-053-12 — Honesty residue (F015/F016) (write set: dadaia_workspace/cli/commands/ci.py, dadaia_workspace/infrastructure/python_env.py, dadaia_workspace/core/handoff_index.py, tests)
- [x] T-053-13 — Bug component vocabulary (F017) (write set: dadaia_workspace/features/bugs/, dadaia_workspace/cli/commands/bugs.py, tests)
- [x] T-053-14 — Container dissolution (F001) (write set: dadaia_workspace/container.py, dadaia_workspace/features/panel/, dadaia_workspace/cli/, dadaia_workspace/core/protocols/, dadaia_workspace/infrastructure/process_ancestry_adapter.py, tests)
- [x] T-053-15 — Scoped-law shipped-hashes coverage + repair (picked bug) (write set: dadaia_workspace/features/specs/template_history.py, doctor_structural.py, features/migrate/upgrade.py, public/templates/shipped-hashes.json, specs/releases/AGENTS.md, specs/audits/AGENTS.md, tests)

## alpha-4 (the deep model)

- [x] T-053-16 — SpecsTree parsed model + rule registry (F010/F012) (write set: dadaia_workspace/features/specs/, dadaia_workspace/cli/commands/specs.py, tests)

## closure

- [x] T-053-17 — Disposition sweep + audit archive (write set: specs/audits/**)
- [x] T-053-18 — Memory update + CONTEXT.md + closure + CHANGELOG + pyproject (write set: specs/memory/, CONTEXT.md, specs/releases/0.5.3/RELEASE.json, CHANGELOG.md, pyproject.toml)

## alpha-5 (AI-surface backlog consumption — extension, operator order 2026-08-31)

- [x] T-053-19 — dadaia-codebase-design skill + architect-core-workflow fuse (write set: dadaia_workspace/public/skills/dadaia-codebase-design/, dadaia_workspace/public/skills/architect-core-workflow/ (delete), dadaia_workspace/public/agents/, dadaia_workspace/public/entities/behavior-map.json)
- [x] T-053-20 — dd-architecture-survey skill (write set: dadaia_workspace/public/skills/dd-architecture-survey/, dadaia_workspace/public/entities/behavior-map.json)
- [-] T-053-21 — dd-code-review skill + persona thinning (write set: dadaia_workspace/public/skills/dd-code-review/, dadaia_workspace/public/agents/code-reviewer.md, dadaia_workspace/public/entities/behavior-map.json)
- [ ] T-053-22 — dadaia-glossary skill + CONTEXT.md homonyms (write set: dadaia_workspace/public/skills/dadaia-glossary/, CONTEXT.md, dadaia_workspace/public/entities/behavior-map.json)
- [ ] T-053-23 — tracer-bullets section in dd-release-definition (write set: dadaia_workspace/public/skills/dd-release-definition/SKILL.md, dadaia_workspace/public/entities/behavior-map.json)
- [ ] T-053-24 — CLI help architecture + derived digest + session injection (write set: dadaia_workspace/cli/, dadaia_workspace/hooks/ctx_inject.py, dadaia_workspace/features/spec_context/injection_policy.py, dadaia_workspace/infrastructure/runtime_config.py, dadaia_workspace/features/, tests)
- [ ] T-053-25 — nine-skill execution: Update×5 + Merge×3 (write set: dadaia_workspace/public/skills/, dadaia_workspace/public/agents/, dadaia_workspace/public/entities/behavior-map.json)
- [ ] T-053-26 — extension closure: histo terminal rewrite, memory/CHANGELOG addenda, re-close (write set: specs/, CHANGELOG.md, CONTEXT.md)
