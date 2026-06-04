# TASKS: v0.1.4.1 — agent-architecture-hardening

**Status:** Aprovado
**Release ID:** v0.1.4.1
**Owner:** product-engineer
**Created:** 2026-06-03

---

## Execution order

Maximum one `[-]` at a time unless disjoint write sets are declared.

**Disjoint-parallel authorized:** T-HARD-01 (sdd-spec-gate.sh) ∥ T-HARD-02 (public/ docs) — non-overlapping write sets.

```
T-HARD-00 → T-HARD-01 → T-HARD-02 → T-HARD-03 → T-HARD-04
                      → T-HARD-05 → T-HARD-06 → T-HARD-11
```

---

## Tasks

### T-HARD-00 — Merge hardening/panel-auth-review branch

- **Status:** [x]
- **Owner:** devops-engineer
- **Target files:** git history (merge commit only)
- **Preconditions:** none
- **Done criterion:** `git log --oneline | head -3` shows the merge commit;
  `poetry run pytest -q -m "unit and not slow" tests/unit` exits 0 with no
  regressions.

Merge `hardening/panel-auth-review` (commit `58aff97`) into main. Resolve any
conflicts. Do not modify the branch content — merge as-is. Covers F-01/02/04
(panel bearer-auth), F-03 (scaffolder SandboxedEnvironment), F-05 (git clone
URL guard).

---

### T-HARD-01 — Fix sdd-spec-gate.sh context-resolution chain

- **Status:** [x]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
- **Preconditions:** T-HARD-00 done
- **Done criterion:** Gate resolves `PRIMARY_SPECS` via the 4-step chain
  (DADAIA_CONTEXT → spec_contexts.json ALIVE → session file → fail-open).
  When `primary_context.json` is absent and `DADAIA_CONTEXT` is unset, the
  gate falls back to `spec_contexts.json` rather than silently no-oping. Gate
  unit tests pass.

Replace the `PRIMARY_SLUG` / `PRIMARY_SPECS` resolution block (currently reads
only `primary_context.json`) with the correct 4-step chain described in PLAN
§5 "Gate fix". Keep `DADAIA_CONTEXT` as priority 1 (already correct). Add
steps 2-3 as described. Ensure RULE A, RULE B, RULE C, and RULE E tests still
pass after the change.

---

### T-HARD-02 — Purge dadaia context activate and primary_context.json refs

- **Status:** [x]
- **Owner:** ai-engineer
- **Target files:**
  - `dadaia_workspace/public/skills/dadaia-workspace-spec-navigator.md`
  - `dadaia_workspace/public/skills/dadaia-step0-memory-bootstrap.md`
  - `dadaia_workspace/public/skills/dadaia-task-manager.md`
  - `dadaia_workspace/public/rules/workspace-protocol.md`
  - `dadaia_workspace/public/data/AGENTS.md`
- **Preconditions:** T-HARD-01 done
- **Done criterion:** `grep -r "primary_context.json\|context activate" dadaia_workspace/public/`
  returns zero matches in the five target files.

In each file, replace `primary_context.json` references with the correct lookup
against `spec_contexts.json` (ALIVE+primary entry). Replace
`dadaia context activate <name>` with `dadaia context bind <name>` or the
correct v2 verb. Keep the rest of each file's content intact.

---

### T-HARD-03 — Fix dadaia-handoff-emitter skill schema drift

- **Status:** [ ]
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/skills/dadaia-handoff-emitter.md`
- **Preconditions:** T-HARD-02 done (sequential ownership; disjoint write set)
- **Done criterion:** The skill contains no `sha256:` prefix instruction.
  All example JSON in the skill shows a bare 64-hex hash. The guardrail line
  "Never omit the sha256: prefix" is absent.

Edit the skill file per PLAN §5 "Handoff skill fix". The schema at
`dadaia_workspace/public/schemas/handoff-v1.schema.json` is the authority
(pattern `^[a-f0-9]{64}$`). The skill must match it.

---

### T-HARD-04 — Fix broken refs, language uniformity, scope blocks

- **Status:** [ ]
- **Owner:** ai-engineer
- **Target files:**
  - `dadaia_workspace/public/agents/project-auditor.md`
  - `dadaia_workspace/public/agents/design-specialist.md`
- **Preconditions:** T-HARD-03 done (sequential ownership; disjoint write set)
- **Done criterion:**
  - `project-auditor.md` skills list does not reference `dadaia-workspace-spec-reviewer`
    or `drift-detection`.
  - Both files contain no Portuguese-language headings or prose blocks.
  - `project-auditor.md` embedded scope rule (the `# project-auditor-scope`
    block) is rendered in English.

Fix broken skill references in `project-auditor.md` frontmatter. Convert all
Portuguese-language embedded scope/rule blocks in both files to English.
See AC-CONS-1 and PLAN §5 "Language uniformity".

---

### T-HARD-05 — Gate RULE F tmp fast-allow and one-[-]-per-owner warn

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
- **Preconditions:** T-HARD-04 done (different file from T-HARD-04; may overlap
  in time with T-HARD-04 if TASKS.md is amended to declare disjoint write sets)
- **Done criterion:** RULE F exists in the gate before the IS_PROD block.
  A tmp path write exits 0 immediately. A TASKS.md with two or more `[-]`
  markers without `parallel_tasks:` header emits a WARN line to the gate log.

Implement RULE F and the one-[-]-warn as specified in PLAN §5.

---

### T-HARD-06 — De-bloat: write_allowlist tightening and consumer path removal

- **Status:** [ ]
- **Owner:** ai-engineer
- **Target files:**
  - `dadaia_workspace/public/agents/devops-engineer.md`
  - `dadaia_workspace/public/agents/ai-engineer.md`
  - Any other `public/agents/` or `public/rules/` file found to contain
    consumer-specific paths or names
- **Preconditions:** T-HARD-05 done
- **Done criterion:**
  - `devops-engineer.md` write_allowlist: `dadaia_workspace/**` replaced by
    `dadaia_workspace/public/**`.
  - `ai-engineer.md` write_allowlist: contains `dadaia_workspace/public/**`
    and no raw Python source paths.
  - `grep -r "openclaw\|hermes\|burrinhos\|dd-chain\|bothub" dadaia_workspace/public/`
    returns zero matches.

Tighten write allowlists per AC-CONS-3. Remove any consumer-specific project
names, hostnames, or private paths from `public/` assets per Constitution §2.

---

### T-HARD-11 — Propagate asset chain and verify all ACs

- **Status:** [ ]
- **Owner:** devops-engineer
- **Target files:** `.dadaia/agentic/` (staging), `.claude/`, `.codex/`,
  `.opencode/`, `.agents/` (projections — generated, not committed in lib)
- **Preconditions:** T-HARD-00 through T-HARD-06 all `[x]`
- **Done criterion:** All AC-* criteria from SPEC §10 pass. Specifically:
  - `dadaia public stage` exits 0
  - `dadaia public install --target all --force` exits 0
  - `dadaia public doctor` exits 0 (no drift)
  - `dadaia specs doctor` exits 0 (no SDD violations)
  - `poetry run pytest -q -m "unit and not slow" tests/unit` exits 0
  - Schema round-trip check (AC-HANDOFF-02) exits 0

Run the validation plan from PLAN §6 in full. Record each command's exit code
as evidence in CLOSURE.
