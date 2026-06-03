# TASKS: v0.1.3 - codex-runtime-readiness

**Status:** Draft
**Release ID:** v0.1.3
**Owner:** product-engineer
**Created:** 2026-06-02

---

## Execution order

Maximum one `[-]` at a time unless this file is amended with explicit disjoint write sets.

```text
T-CR-01 -> T-CR-02 -> T-CR-03 -> T-CR-04 -> T-CR-05 -> T-CR-06 -> T-CR-09 -> T-CR-10 -> T-CR-11 -> T-CR-07 -> T-CR-08
```

---

## Tasks

### T-CR-01 - Lock Codex activation contract

- **Status:** [ ]
- **Owner:** ai-engineer + software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/public_assets.py`, tests, docs as needed

Confirm whether workspace `.codex/config.toml` is consumed by Codex CLI or whether the
active config is user-level `~/.codex/config.toml`. Implement the chosen bridge or warning
mechanism. Add tests for the selected contract.

### T-CR-02 - Convert Codex/shared memory instructions from HTML to Markdown

- **Status:** [ ]
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/runtime/codex/**`, `dadaia_workspace/public/skills/**`, `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/templates/specs-AGENTS.md`, affected `dadaia_workspace/public/agents/*.md`

Replace stale `.html` memory paths with Markdown-source paths and `catalog.json`
semantics. Keep memory writes for actual `specs/memory/**` until CLOSURE.

### T-CR-03 - Make Codex-only skill discovery explicit

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/public_assets.py`, tests

Ensure generated Codex config exposes both shared skills and Codex-only adapters, or add a
test proving `.codex/skills` is always auto-discovered by the supported Codex version.

### T-CR-04 - Make Codex persona dispatch wording runtime-accurate

- **Status:** [ ]
- **Owner:** software-engineer-python + ai-engineer
- **Target files:** `dadaia_workspace/infrastructure/runtime_transforms/codex.py`, tests, affected agent docs if needed

Replace the vague "`subagent` dispatch" transform with Codex-native wording. Generated
PM/auditor personas must not instruct the model to call a literal unavailable tool.

### T-CR-05 - Exclude cache files from public asset traversal

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/public_assets.py`, tests

Ignore `__pycache__/` and `*.pyc` in stage/install/doctor traversal. Add regression tests
for manifest and doctor output.

### T-CR-06 - Reconcile Codex workflow policy

- **Status:** [ ]
- **Owner:** ai-engineer + software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/public_assets.py`, `dadaia_workspace/public/data/AGENTS.md`, memory at CLOSURE

Choose and implement one coherent policy for `.codex/workflows/`: absent/not-applicable or
installed/reference-only. Update doctor labels and docs accordingly.

### T-CR-07 - Propagate and run gates

- **Status:** [ ]
- **Owner:** devops-engineer
- **Target subsystem:** public asset projections

Run `dadaia public stage`, `dadaia public install --target all`, and `dadaia public doctor`.
Run focused tests and Python quality gates from PLAN.md.

### T-CR-09 - Add scoped AGENTS.md for dadaia runtime subtrees

- **Status:** [ ]
- **Owner:** ai-engineer + software-engineer-python
- **Target files:** `dadaia_workspace/public/data/*AGENTS.md`, `dadaia_workspace/infrastructure/public_assets.py`, tests

Install and doctor-track scoped AGENTS.md files for `.dadaia/`, `.dadaia/tmp/`,
and `.dadaia/states/`. Keep the root AGENTS.md short and make it route agents to
the nearest scoped rule file.

### T-CR-10 - Enforce Codex hook parity and Markdown-only memory gate

- **Status:** [ ]
- **Owner:** software-engineer-python + ai-engineer
- **Target files:** `dadaia_workspace/infrastructure/public_assets.py`, `dadaia_workspace/infrastructure/runtime_transforms/codex.py`, `dadaia_workspace/public/scripts/sdd-*.sh`, tests

Generate Codex `PreToolUse`, `PostToolUse`, and `UserPromptSubmit` hooks with broad
matchers. Ensure heartbeat is not limited to write-like tools. Hook scripts must prefer
workspace venv Python. Codex persona transforms must preserve hook semantics. The SDD gate
must block legacy memory `.html/.yaml/.yml` writes even in CLOSURE; Markdown atoms are the
only editable memory source.

### T-CR-11 - Enforce source-repo hygiene

- **Status:** [ ]
- **Owner:** software-engineer-python + devops-engineer
- **Target files:** `.gitignore`, `AGENTS.md`, `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/infrastructure/public_assets.py`, `tests/conftest.py`, `.github/workflows/ci.yml`, `scripts/**`, package/e2e config

Remove tracked root-local artefacts from the public source repo (`Makefile`,
`opencode.json`, root `playwright.config.ts`, stale investigation scripts). Add guards so
tests and CI fail if runtime projections or local harness files are created/tracked at the
repo root. Keep legitimate guard scripts only.

### T-CR-08 - QA Codex readiness gate

- **Status:** [ ]
- **Owner:** qa-engineer
- **Target subsystem:** Codex projection, specs doctor, public doctor

Verify SPEC.md acceptance criteria AC-1 through AC-10. Include evidence from `codex doctor`,
temporary Codex projection smoke, `public doctor`, `specs doctor`, and focused tests.
