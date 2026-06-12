# PLAN: v0.1.8 — Coordinator + Sub-Agent Architecture, Roster 15→9, Persona Tailoring

**Status:** Em revisão
**Release ID:** v0.1.8 (milestone of v0.2.0)
**Owner:** product-engineer
**Created:** 2026-06-06

---

## Strategy

This milestone is entirely AI-entity craft — no Python code, no test changes, no schema
migrations. The only artifacts it touches are `dadaia_workspace/public/agents/*.md`,
`dadaia_workspace/public/skills/` (5 deletions), `dadaia_workspace/public/rules/plugin-scope.md`,
and `specs/bugs/` (two annotations). Execution is owned by `ai-engineer`.

Order rationale:
1. Author new `software-engineer` first (T-018-01) so the old implementer deletions
   (T-018-02) never leave a gap — the gate must not see a missing implementer persona.
2. Delete old implementers (T-018-02) only after `software-engineer` is confirmed present.
3. Plugin stubs + skill removals (T-018-03) happen after deletions so references can be
   cleaned atomically.
4. Coordinator deepening (T-018-04) against the frozen constitution (v0.1.7 prereq).
5. Gate persona sharpening + software-architect (T-018-05) after coordinators, since
   qa/sec/code-reviewer personas reference the gate sequence the coordinators define.
6. Bug annotations (T-018-06) — small change, no dependency on persona content.
7. Propagation (T-018-07) — last, after all persona edits are committed.
8. qa-engineer gate (T-018-08).
9. Operator in-workspace validation + push (T-018-09).

---

## File map

### New files

| File | Owner | Purpose |
|------|-------|---------|
| `dadaia_workspace/public/agents/software-engineer.md` | ai-engineer | Generic implementer absorbing python/node/backend; MUTATING/PM-sub-agent |

### Modified files — coordinator personas (deep rewrites)

| File | Owner | Change summary |
|------|-------|----------------|
| `dadaia_workspace/public/agents/project-manager.md` | ai-engineer | Confirm model=`claude-opus-4-8`; add lease-coordinator + A-2 sub-agent model; add §1 position; update dispatch table (remove python/node/backend refs + researcher + stale Tier-1 workflow names); harden review-gate hard rule |
| `dadaia_workspace/public/agents/product-engineer.md` | ai-engineer | Add §1 position + MUTATING/PM-sub-agent; update memory write to DEFINITION+CLOSURE; update Phase 7 implementer list; update "What I don't do" table; remove stale agent refs |
| `dadaia_workspace/public/agents/project-auditor.md` | ai-engineer | Add §1 position (ADDITIVE/peer/no-lease); make dispatch authority explicit; add scoring model inline; remove researcher header ref; remove deleted agent names from dispatch list |
| `dadaia_workspace/public/agents/ai-engineer.md` | ai-engineer | Add §1 position (MUTATING/PM-sub-agent during releases); update scope section (remove old implementer refs); update collaboration section; update write-permissions table |

### Modified files — gate personas + architect (targeted additions)

| File | Owner | Change summary |
|------|-------|----------------|
| `dadaia_workspace/public/agents/qa-engineer.md` | ai-engineer | Add §1 position (ADDITIVE/gate-pre-commit/no-lease); add `activity_class`, `lease_relationship`, `gate_role` |
| `dadaia_workspace/public/agents/security-reviewer.md` | ai-engineer | Add §1 position (ADDITIVE/gate-pre-push/no-lease); add `activity_class`, `lease_relationship`, `gate_role` |
| `dadaia_workspace/public/agents/code-reviewer.md` | ai-engineer | Add §1 position (ADDITIVE/gate-pre-PR/no-lease); add `activity_class`, `lease_relationship`, `gate_role` |
| `dadaia_workspace/public/agents/software-architect.md` | ai-engineer | Add §1 position (ADDITIVE/feeds-SPEC-PLAN); strip `architect-code-audit` + `architect-design-patterns` skill refs; strip researcher dispatch ref |

### Plugin stubs (rewrites to thin stubs)

| File | Owner | Change summary |
|------|-------|----------------|
| `dadaia_workspace/public/agents/frontend-engineer.md` | ai-engineer | Replace full persona with plugin stub: `[PLUGIN REQUIRED] frontend-engineer` + install pointer |
| `dadaia_workspace/public/agents/design-specialist.md` | ai-engineer | Replace full persona with plugin stub: `[PLUGIN REQUIRED] design-specialist` + install pointer |
| `dadaia_workspace/public/agents/devops-engineer.md` | ai-engineer | Replace full persona with plugin stub: `[PLUGIN REQUIRED] devops-engineer` + install pointer; strip dangling skill refs |

### Deleted files

| File | Owner | Reason |
|------|-------|--------|
| `dadaia_workspace/public/agents/software-engineer-python.md` | ai-engineer | Merged into software-engineer |
| `dadaia_workspace/public/agents/software-engineer-node.md` | ai-engineer | Merged into software-engineer |
| `dadaia_workspace/public/agents/backend-engineer.md` | ai-engineer | Merged into software-engineer |
| `dadaia_workspace/public/agents/researcher.md` | ai-engineer | Removed from core; PM dispatches read-only exploration inline |

### Deleted skill files (5 frontend/design)

| File | Owner | Reason |
|------|-------|--------|
| `dadaia_workspace/public/skills/frontend-design/` (or equivalent) | ai-engineer | Moves to plugin |
| `dadaia_workspace/public/skills/frontend-implementation-quality/` | ai-engineer | Moves to plugin |
| `dadaia_workspace/public/skills/design-reference-research/` | ai-engineer | Moves to plugin |
| `dadaia_workspace/public/skills/design-report-quality-gate/` | ai-engineer | Moves to plugin |
| `dadaia_workspace/public/skills/ux-ui-review/` | ai-engineer | Moves to plugin |

> **Note:** Confirm exact skill directory names against `public/skills/` before deletion.
> Skill slugs in the grill report and SPEC are canonical; actual filesystem names may use
> different slug formats (verify with `ls dadaia_workspace/public/skills/`).

### Modified rule

| File | Owner | Change summary |
|------|-------|----------------|
| `dadaia_workspace/public/rules/plugin-scope.md` | ai-engineer | Name all 3 plugin agents; document `[PLUGIN REQUIRED]` response for core agents receiving plugin-scoped tasks |

### Bug annotations

| File | Owner | Change |
|------|-------|--------|
| `specs/bugs/agent-skill-surface-slop.md` | ai-engineer | Add `adopted: v0.2.0` to frontmatter |
| `specs/bugs/semaphore-no-liveness-reclaim.md` | ai-engineer | Add `superseded_by: v0.2.0/v0.1.6` to frontmatter |

---

## Persona authoring contract (for ai-engineer)

Every surviving core persona MUST have ALL of the following in YAML frontmatter (not
body-only — dadaia-doctor validates their presence in frontmatter; Claude Code runtime
ignores non-native frontmatter keys, so these are for tooling only):

```yaml
activity_class: <MUTATING|ADDITIVE>
lease_relationship: <holds/PM-sub-agent-no-independent-acquire/additive-no-lease>
gate_role: <coordinator|implementer|gate-pre-commit|gate-pre-push|gate-pre-PR|architecture-feed|none>
```

Each coordinator persona must also contain a prose `## §1 Lifecycle position` section
(1–3 sentences) stating:
- Which lifecycle phases the agent owns or gates
- Its lease relationship in plain English (not just YAML)
- How it is dispatched (operator-direct / PM dispatch / no dispatch)

**Anti-slop body budget (gate-checked in T-018-08):**
- No deepened persona body may restate a constitution §/skill protocol for >3 lines —
  cite by reference instead (e.g. A-2 → cite `project-orchestration`; grill-mandatory →
  cite `dadaia-grill-me`; gate sequence → cite constitution §11).
- PM persona body (Markdown body, excluding frontmatter) ≤ 120 lines.
- 'Cite the constitution, never duplicate it' is a gate-checked criterion in T-018-08,
  not advisory prose. qa-engineer must count lines and flag violations.

---

## Migration approach: projection after persona edits

Propagation is a single-command chain. It runs in T-018-07 after all persona files are
committed. ai-engineer executes (or requests PM to run via Bash):

```bash
dadaia public stage
dadaia public install --force --target all
dadaia public doctor
```

`--force` is needed here because:
- Plugin stubs replace full personas in-place (hash diverges from staging → force needed
  to clobber the projected full persona with the thin stub).
- Deleted files must be absent from all runtime projection trees.

After doctor exits 0, verify:
```bash
ls .claude/agents/ | wc -l     # must equal 12 (9 core + 3 plugin stubs)
ls .codex/agents/ | wc -l      # same
ls .agents/ | wc -l            # same
```

---

## `agents.index.json` regenerated index (RULE D gate update)

The v0.1.6 gate uses a pre-compiled `agents.index.json` generated by `dadaia public
stage` from persona frontmatter. **Do NOT hand-author this file.** Location:
`.dadaia/agentic/agents.index.json` (NOT `public/scripts/`).

T-018-07 depends on v0.1.6 T-016-00 (the `agents.index.json` generator being in place).

T-018-07's job: re-run `dadaia public stage` and VERIFY the regenerated index reflects
the updated persona roster — deleted agent names absent, `software-engineer` present,
plugin stubs reflected with their `plugin: true` marker. The index maps EVERY agent to
its write_allowlist as declared in frontmatter; it is NOT a "mutating-only names" subset.
Who is MUTATING is answered by constitution §7, not by filtering this index.

Plugin stubs (`plugin: true` in frontmatter) carry no write_allowlist. They appear in
the index only to surface the `plugin: true` flag for tooling. They are not MUTATING
actors and are not in the core roster.

---

## In-workspace validation (operator drives)

After T-018-09, the operator runs a small end-to-end demand through PM on the live
instance:

1. Operator states a demand to PM.
2. PM runs `dadaia-grill-me` (confirms grill-mandatory works from the persona alone).
3. PM creates a backlog entry; dispatches PE.
4. PE authors a stub SPEC (need not be a real release spec — a scratch spec suffices).
5. PM dispatches software-engineer for a stub implementation task.
6. software-engineer flips `[ ]` → `[-]` and does minimal work.
7. PM routes through review gates (qa → security → code-reviewer).
8. Confirms: no lock friction, no spurious MUTATING block, no deadlock.
9. Confirms: `dadaia public doctor` exits 0; 9 agents enumerable.

This validation does not require a complete release cycle — it proves the coordinator
dispatch logic works and the lease flows correctly under the new topology.

---

## Technical risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `agents.index.json` not regenerated → gate uses stale roster | HIGH | T-018-07 re-runs `dadaia public stage` and verifies regenerated index at `.dadaia/agentic/agents.index.json`; depends on v0.1.6 T-016-00 generator being in place; qa-engineer confirms in T-018-08 |
| Plugin stub in a runtime that doesn't understand stub format → confusing error | MEDIUM | Stub format is just a thin markdown file; no runtime should break on it; doctor confirms |
| PM persona grows during deepening → context window tax | MEDIUM | Anti-slop constraint: PM body ≤ 120 lines; every addition must cite a skill/constitution section rather than restate inline; qa-engineer gate-checks line count and cite discipline in T-018-08 |
| Skill slot name mismatch (grill report slugs vs actual filesystem) | MEDIUM | ai-engineer confirms exact slugs before deletion via `ls public/skills/` |
| v0.1.7 constitution not yet committed when v0.1.8 starts | CRITICAL | Hard dependency — v0.1.7 operator sign-off is the gate to open v0.1.8 |

---

## Validation plan

| Check | Command | Expected result |
|-------|---------|-----------------|
| Persona count (core + stubs) | `ls dadaia_workspace/public/agents/ \| wc -l` | 12 (9 core personas + 3 plugin stubs) |
| Plugin stubs have `plugin: true` | `grep 'plugin: true' dadaia_workspace/public/agents/*.md \| wc -l` | 3 |
| All 4 deleted files absent | `ls dadaia_workspace/public/agents/ \| grep -E 'python\|node\|backend\|researcher'` | empty |
| All 9 core personas present | `ls dadaia_workspace/public/agents/` | list contains 9 core names |
| Each core persona has §1 fields in frontmatter | `grep -l 'activity_class' dadaia_workspace/public/agents/*.md \| wc -l` | 9 (stubs excluded) |
| `agents.index.json` location correct | `ls .dadaia/agentic/agents.index.json` | file exists |
| PM body line count | `wc -l dadaia_workspace/public/agents/project-manager.md` | body ≤ 120 lines (excluding frontmatter) |
| No dangling persona refs to deleted agents | `dadaia public doctor` D-OC-1 on personas | exit 0 |
| Runtime propagation | `dadaia public doctor` | exit 0 |
| Operator E2E | PM → grill → PE → SE → review gates | no friction observed |
