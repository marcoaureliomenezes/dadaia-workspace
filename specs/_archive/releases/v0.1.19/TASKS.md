# TASKS: v0.1.19 — Drift Elimination, Memory Diagrams, PI E2E Parity, User README

**Status:** Aprovado
**Release ID:** v0.1.19

Markers: `[ ]` open · `[-]` reserved · `[x]` done. Reserve before writing.

## DEFINITION — memory (write set: specs/memory/**, specs/releases/v0.1.19/**)

- [x] T-19-01 — Author SPEC.md / PLAN.md / TASKS.md (Status: Aprovado).
- [x] T-19-02 — MD-1/MD-3: `tech-stack.md` purge fable-5 two-tier table → single
  opus-4-8 tier; document reserved unused `claude-fable-5`/`deep` registry entry.
- [x] T-19-03 — MD-2/MD-4/MD-5 + DG-3: refresh `agent-orchestration.md` (gate
  scope honest, 8 rules, PI in dispatch honesty, agent-topology diagram, re-date).
- [x] T-19-04 — MD-6/MD-7: `multi-platform-parity.md` tldr/summary include PI;
  OpenCode→Python hook (not shell). MD-8: `product-vision.md` five runtime kinds.
  MD-9: `architecture.md` orchestrate retained-inert note.
- [x] T-19-05 — DG-1: `lifecycle-foundation.md` two-layer + pipeline-ladder diagram.
- [x] T-19-06 — DG-2: `architecture.md` two-layer agentic model diagram.
- [x] T-19-07 — DG-6: `quality-assurance.md` test-pyramid + CI-jobs diagram.
- [x] T-19-08 — DG-4/DG-5: `tech-stack.md` ring-dependency diagram; ensure
  `specs-doctor.md` has an invariant-flow diagram.
- [x] T-19-09 — Regenerate `catalog.json` + `index.md` (`dadaia memory catalog
  generate`).

## IMPLEMENTATION — code/tests/docs (write set: dadaia_workspace/**, tests/**, README.md, specs/constitution.md)

- [x] T-19-10 — PKG-1: `pyproject.toml` description includes PI.
- [x] T-19-11 — ARCH-NIT-1: `_GitDiffPort.diff_name_only` param `cwd`→`path`.
- [x] T-19-12 — QA-1: factory test `build_agent_runtime(PI_HEADLESS)`→adapter.
- [x] T-19-13 — QA-2: Layer-2 CLI e2e `--harness pi` with injected fake stream.
- [x] T-19-14 — QA-3: Layer-1 projection via real CLI `public install --target pi`.
- [x] T-19-15 — QA-4: Layer-1 governance-content assertion on projected `.pi/`.
- [x] T-19-16 — CONST-1: constitution §11 tense fix.
- [x] T-19-17 — F: full README rewrite (4 harnesses incl PI, two layers,
  workflows, lifecycle phases, current CLI surface).

## CLOSURE

- [x] T-19-18 — preflight green + `poetry build` wheel; review ladder (QA +
  code-review + security) APPROVED on closing tip.
- [x] T-19-19 — CLOSURE.md, archive release, regenerate catalog, auto-memory
  update; gated push + PR update + CI watched green; fresh drift re-audit = zero.
