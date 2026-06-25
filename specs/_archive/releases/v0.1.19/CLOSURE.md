# Closure: Release — v0.1.19

> **Status:** Aprovado
> **Release ID:** v0.1.19
> **Owner:** product-engineer
> **Closed:** 2026-06-25

## Summary

v0.1.19 is the **drift-elimination + diagrams + PI-E2E-parity + user-README**
remediation release on top of v0.1.18 (PI fourth harness / two-layer model). It was
commissioned by an operator `/goal` for a full re-audit with a hard "no drift" mandate.

A four-lens audit (project-auditor + qa-engineer + security-reviewer +
software-architect) found the **implementation sound** — security
APPROVED-with-findings (no CRITICAL/HIGH/MED), architecture APPROVED ("zero
engine-spine changes" holds; PI is a true `CodexExecAdapter` twin), QA QUALIFIED-YES
(PI is the best-covered non-fake harness) — and a **concentrated documentation/memory
drift set** plus a badly stale user README and PI E2E gaps shared by all four
harnesses. This release closes every one of those.

What shipped:
- **Memory drift eliminated (MD-1..9 + the deeper pre-existing drift the code-review
  caught):** purged the fictional `claude-fable-5` two-tier model table in
  `tech-stack.md` (all 9 core agents are `claude-opus-4-8`; fable/deep is a reserved,
  unused registry entry) — this was a false fact injected into every session; corrected
  `agent-orchestration.md` (gate enforces path-class×lease×phase×mode, not
  write-allowlists; 8 rules not 5; PI added to dispatch honesty); `multi-platform-parity`
  tldr/summary include PI and OpenCode invokes the Python hook not shell scripts;
  `product-vision` five runtime kinds; `architecture` orchestrate retained-inert note;
  `specs-doctor` TREE-3 is WARNING/no-fix (not ERROR/auto-fix); `quality-assurance` CI
  is 10 quality + 4 governance jobs (not 7).
- **Six mermaid diagrams** added for human readability: the two-layer agentic model
  (`architecture`), the pipeline ladder (`lifecycle-foundation`), the 9-core agent
  topology (`agent-orchestration`), the dependency rings (`tech-stack`), the test
  pyramid + CI jobs (`quality-assurance`), and the invariant flow (`specs-doctor`).
- **Constitution §11** gate-ladder tense corrected (codified in v0.1.15, now in force).
- **Code:** `pyproject.toml` description includes PI; `_GitDiffPort.diff_name_only`
  param `cwd`→`path`; `init.py` docstring/output reflects all-runtime projection.
- **PI E2E parity at both layers (4 new tests):** factory `build_agent_runtime(kind)`
  → adapter parametrized over all five kinds + PI git-seam; Layer-2 CLI e2e
  `dadaia lifecycle pipeline --harness pi` (engine records `pi_headless`); Layer-1
  projection via the real CLI `dadaia public install --target pi`; Layer-1 `.pi/`
  governance-content assertion.
- **README** fully rewritten to the current architecture: four harnesses incl PI, the
  two agentic layers (with diagram), the workflow engine, the lifecycle phases, the
  real gate (merged Python `pre_gate` + git chokepoints, not the retired
  `sdd-spec-gate.sh`), and the real CLI surface.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-19-01 | Author SPEC/PLAN/TASKS (Status: Aprovado) | `4dfd80f` |
| T-19-02 | tech-stack.md purge fable-5 table → single opus-4-8 tier + reserved note | `4dfd80f` |
| T-19-03 | agent-orchestration.md gate scope / 8 rules / PI dispatch + topology diagram | `4dfd80f` |
| T-19-04 | multi-platform-parity PI + Python-hook; product-vision 5 kinds; architecture orchestrate note | `4dfd80f` |
| T-19-05 | lifecycle-foundation pipeline-ladder diagram (DG-1) | `4dfd80f` |
| T-19-06 | architecture two-layer model diagram (DG-2) | `4dfd80f` |
| T-19-07 | quality-assurance test-pyramid + CI diagram (DG-6) | `4dfd80f` |
| T-19-08 | tech-stack ring-dependency diagram; specs-doctor invariant-flow diagram | `4dfd80f` |
| T-19-09 | Regenerate catalog.json + index.md | `4dfd80f` / `7c4b1a8` |
| T-19-10 | pyproject description includes PI | `4dfd80f` |
| T-19-11 | _GitDiffPort.diff_name_only param cwd→path | `4dfd80f` |
| T-19-12 | QA-1 factory wiring test (all kinds + PI git-seam) | `4dfd80f` |
| T-19-13 | QA-2 Layer-2 CLI e2e --harness pi | `4dfd80f` |
| T-19-14 | QA-3 Layer-1 projection via real CLI | `4dfd80f` |
| T-19-15 | QA-4 Layer-1 governance-content assertion | `4dfd80f` |
| T-19-16 | constitution §11 tense fix | `4dfd80f` |
| T-19-17 | README full rewrite | `4dfd80f` |
| (review-fix) | Code-review findings: TREE-3 + CI-jobs drift, README/init accuracy, test-fake params | `7c4b1a8` |
| T-19-18 | preflight green + wheel build + review ladder APPROVED | `<closure>` |
| T-19-19 | CLOSURE.md + archive + auto-memory + gated push + CI green + drift re-audit | `<closure>` |

## Acceptance criteria — met

1. `dadaia specs doctor` exit 0. ✅
2. `dadaia public doctor` exit 0 with `[ok] public-privacy` + `[ok] pi:`. ✅
3. `dadaia ci preflight` green (ruff format/check + mypy --strict + pytest 3359 passed). ✅
4. `python -m build --wheel` produced `dadaia_workspace-*.whl` (project compiles). ✅
5. Memory complete + representative + drift-free; 30 atoms lint-clean, zero token-drift;
   a fresh drift re-audit confirms zero unresolved drift. ✅
6. Targeted atoms carry well-designed mermaid diagrams; catalog.json/index.md regenerated. ✅
7. PI E2E parity at both layers; new tests QA-1..4 added and passing. ✅
8. README accurately describes the 4 harnesses, two layers, workflows, lifecycle phases,
   and CLI surface. ✅
9. Review ladder on the closing tip: qa-engineer APPROVED, code-reviewer APPROVED,
   security-reviewer APPROVED (push-gate verdict keyed to the pushed sha). ✅

## Reviews

- **qa-engineer:** APPROVED — 48 PI/lifecycle/public tests pass; PI E2E parity proven at
  both agentic layers; no slop; live seam correctly opt-in.
- **code-reviewer:** APPROVED — 7 findings (3 MEDIUM drift, 1 LOW, 1 INFO actionable, 2
  INFO verifications). All actionable findings fixed in `7c4b1a8`.
- **security-reviewer:** APPROVED — 0 CRITICAL/HIGH/MED; no secrets, no operator-local
  paths, no dependency delta; `[ok] public-privacy`; push-safe. Binding push-gate
  handoff re-keyed to the final pushed sha.

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Format + lint + strict-type + full tests | `dadaia ci preflight` | 4/4 PASS (ruff format --check; ruff check; mypy --strict; pytest 3359 passed, 11 skipped) |
| Memory atoms lint (frontmatter, headings, wikilinks, token drift) | `lint-memory-atoms.py` | 30 OK, 0 WARN, 0 ERROR |
| Public projection + privacy + PI target | `dadaia public doctor` | exit 0; `[ok] public-privacy`; `[ok] pi:` SYSTEM.md / settings.json / prompts |
| SDD structural health | `dadaia specs doctor` | exit 0 (after phase/marker coherence restored) |
| Project compiles (wheel) | `python -m build --wheel` | `dadaia_workspace-*.whl` produced |
| PI E2E (both layers) | `pytest` (QA-1..4) | factory all-kinds + git-seam; Layer-2 CLI `--harness pi`; Layer-1 real-CLI projection; Layer-1 governance content — all pass |
| QA gate | qa-engineer APPROVE | `.dadaia/handoff/dadaia-workspace/…-qa-engineer-v0119-*.json` |
| Code review | code-reviewer APPROVE (findings fixed in `7c4b1a8`) | `.dadaia/handoff/dadaia-workspace/…-code-reviewer-v0119-*.json` |
| Security verdict (push gate) | security-reviewer APPROVE | keyed to the final pushed sha (`metrics.commit_sha`) |
| Branch push + GitHub Actions CI | CI for the closing tip | watched to green |

## Drifts

### memory-and-doc-drift-eliminated

This release's purpose was to eliminate drift. Fixed: the fictional `claude-fable-5`
two-tier model table (injected into every session via `tech-stack.md`); the stale
`agent-orchestration` gate-scope / rule-count / PI omission; `multi-platform-parity` PI +
OpenCode-shell claims; `product-vision` runtime-kind count; the pre-existing
`specs-doctor` TREE-3 drift (WARNING/no-fix, not ERROR/auto-fix); and the pre-existing
`quality-assurance` "7 CI jobs" undercount (real: 10 quality + 4 governance). All
corrected; 30 atoms lint-clean with zero token-drift; a fresh project-auditor drift
re-audit confirms zero unresolved drift.

### self-induced-spec-doc-024-phase-incoherence

Flipping `ACTIVE.md` back to `DEFINITION` to apply the code-review memory fixes — while
TASKS.md was already `[x]`-majority — tripped SPEC-DOC-024 (the e2e specs-doctor-0-errors
gate). Resolution: advanced the phase to IMPLEMENTATION once memory work was complete;
specs doctor returned exit 0. The gate working as designed (phase/marker coherence), not
a product defect — no bug filed.

## Memory updates

Atoms updated (all lint-clean): `tech-stack.md` (MD-1/MD-3 model table + DG-4 ring
diagram), `architecture.md` (MD-9 + DG-2 two-layer diagram), `agent-orchestration.md`
(MD-2/4/5 + DG-3 topology), `multi-platform-parity.md` (MD-6/7), `product-vision.md`
(MD-8), `lifecycle-foundation.md` (DG-1 pipeline ladder), `quality-assurance.md` (DG-6
pyramid + CI-job fix), `specs-doctor.md` (DG-5 invariant flow + TREE-3 fix).
`catalog.json` + `index.md` regenerated. No atom created or deleted. The auto-memory
`project_pi_fourth_harness` atom carries the v0.1.19 milestone note.

## Dispositions / deferred (recorded, not silently dropped)

- WS-PI-4 (Ring-1 `.pi/extensions/` pre-disk gate), WS-PI-6 (telemetry), RPC/SDK
  transports — deferred (out of scope; tracked by EPIC `pi-agent-fourth-harness`).
- The reserved-but-unused `claude-fable-5`/`deep` registry tier — documented as reserved
  (not removed); code unchanged.
- The stale un-archived `specs/releases/v0.1.12` dir — flagged for PM/PE disposition;
  not touched by this release.
- `release new` SemVer/dots bug (`release-new-rejects-semver-but-doctor-requires-it`,
  Open) — release-tooling; this release sidestepped it by naming the dir `v0.1.19`.

## Notes

This is a documentation/memory/test/README fidelity release: no engine-spine refactor,
no new runtime transport, no harness behavior change, no dependency change. It hardens
fidelity on top of the already-shipped, already-reviewed v0.1.18 implementation.
