# PLAN: v0.1.5 rc-1 — session-semaphore + agent-specialization

**Status:** Aprovado
**Release ID:** v0.1.5
**Segment:** rc-1
**Owner:** product-engineer
**Created:** 2026-06-05

---

## Approach

This segment runs on `feature/0.1.5` (existing branch, 24 commits ahead of main,
unpushed). All lib-originated AI-entity files (agents, skills, rules, hooks) are
edited at source under `dadaia_workspace/public/<type>/`, then propagated with
`dadaia public stage && dadaia public install --force --target all` and verified
with `dadaia public doctor` exit 0. Python source changes (R1 gate/session/CLI)
run under the SDD gate (bound session + `[-]` TASKS marker).

Implementation order is FIXED per the grill session: R1 → D5 → R3 → R4 → D4.
R1 must be complete before R3/R4 are dispatched (R3 personas encode the semaphore
flow; D5 gate shares the gate surface with R1).

## Work breakdown

### G1 — R1: Session semaphore + env-free binding + 3 lock fixes

**Owner surface:** Python (gate scripts, session model, CLI) + DevOps (hooks).
**Files in scope:**
- `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
- `dadaia_workspace/public/scripts/sdd-post-gate.sh`
- `dadaia_workspace/public/scripts/ctx-inject.sh`
- `dadaia_workspace/core/models/spec_context.py` (or equivalent session model)
- `dadaia_workspace/features/specs/` — session/lock logic
- `dadaia_workspace/cli/context.py` — `bind` command
- `dadaia_workspace/features/specs/` — doctor invariant additions

**Design direction:**
1. `ctx-inject.sh` writes a runtime→session pointer file at session start
   (e.g. `.dadaia/sessions/runtime/<pid>.ptr` → `session_id`); cleans up on end.
2. RULE E in `sdd-spec-gate.sh` resolves session by: env var → runtime ptr file
   → deny (no rebind required).
3. Per-context semaphore: `.dadaia/states/ctx_locks/<context>.lock` with `owner`,
   `phase`, `release`, `write_set`, `acquired_at`, `ttl`, `heartbeat`. One holder
   max per context for implement+review; read/spec are never blocked.
4. `sdd-post-gate.sh` heartbeat renews both session file and lock.
5. Lock glob narrowed to exact `${CONTEXT_SLUG}__${ACTIVE_RELEASE}.json`.
6. `CONTEXT_SLUG` sanitized (strip non-alphanumeric except `-_`) before path use.
7. Doctor adds orphan/stale/duplicate lock invariants.

**Test plan:** unit tests for session resolution (env, ptr-file, deny paths);
lock acquire/renew/release; sanitization; glob narrowing; E2E concurrent-session
test (two writers, one blocked).

### G2 — D5: Backlog-ownership rule + hard gate

**Owner surface:** AI-entity (rule) + gate hook.
**Files in scope:**
- `dadaia_workspace/public/rules/backlog-ownership.md` (new)
- Gate hook wiring for the backlog write-block (mirrors memory-atomicity gate)

**Design direction:** New always-on rule declares ownership. A PreToolUse hook
(analogous to the memory-atomicity hook) intercepts Write/Edit calls targeting
`specs/backlog/**` and blocks unless the calling agent is `project-manager`.

**Test plan:** Verify gate blocks a simulated non-PM write to `specs/backlog/`;
verify PM write passes; `dadaia public doctor` exit 0.

### G3 — R3: Four dadaia-agent specialization (strategy-first)

**Owner surface:** AI-entity (personas, skills, rules). Python: zero.
**Files in scope (source):**
- `dadaia_workspace/public/agents/product-engineer.md`
- `dadaia_workspace/public/agents/project-manager.md`
- `dadaia_workspace/public/agents/project-auditor.md`
- `dadaia_workspace/public/agents/ai-engineer.md`
- New skill files as determined by the strategy document
- New or updated rule files as determined by the strategy document

**Required first step:** ai-engineer produces a strategy document (report) covering
the questions in SPEC §3/R3 before any persona file is touched. PM accepts strategy
before dispatch continues.

**D4 is folded here:** `model: claude-opus-4-8` in `project-manager.md` source,
verified in `.claude/agents/` + `.codex/agents/` projections.

**Validation:** `dadaia public doctor` exit 0; manual projection check; anti-slop
review (no giant prompts, no redundancy with referenced skills/rules).

### G4 — R4: Generic-agent audit

**Owner surface:** Read-only audit; no writes to agent/skill files.
**Scope:** all agents except product-engineer, project-manager, project-auditor,
ai-engineer.
**Output:** scored audit report with cited findings (file:line, severity).
**No persona or skill file is modified in R4.** Trims are R4b (future release).

### G5 — Pre-push CI gate (inherited from v0.1.5 flat release, must hold)

The pre-push CI gate delivered in v0.1.5 (T-GOV-05) remains mandatory for all
pushes on this segment. Before any push:
```bash
dadaia ci preflight   # or: ruff format --check && ruff check && mypy dadaia_workspace && pytest -p no:cacheprovider
```
All checks must pass locally. Never push red.

## Sequencing

```
1. G1 (R1) — gate/session/CLI Python + hooks
       ↓ complete
2. G2 (D5) — backlog ownership rule + gate (hot gate surface)
       ↓ complete
3. G3 (R3) — ai-engineer strategy document → PM accept → persona edits + D4
       ↓ complete
4. G4 (R4) — generic-agent audit (read-only)
       ↓ complete
5. G5 — propagate all asset changes: dadaia public stage && install --force --target all && doctor
6. Pre-push CI suite green
7. rc-1 ship gate: qa-engineer + code-reviewer + security-reviewer all APPROVE
8. Push feature/0.1.5 → PR → merge → CLOSURE → tag v0.1.5 → publish
9. Propagate to live instance: dadaia public stage && install --force --target all && doctor exit 0
```

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| R1 scope creep into session-model redesign | Design direction in SPEC is prescriptive; architect only what the acceptance criteria require |
| D5 hook conflicts with existing gate hooks | Mirror the memory-atomicity gate exactly; test isolation |
| R3 anti-slop violation (giant prompts) | Strategy document reviewed by PM before any edit; reviewer checklist per SPEC |
| R4 audit scope too wide | Limit to non-dadaia agents; audit-only (no edits); time-box per task |
| D4 projection miss | Verify `.claude/` + `.codex/` projections manually post-install |
| Push before gate green | Pre-push CI gate blocks; never skip with `--no-verify` |

## Validation strategy

- R1: unit + E2E concurrent-session test; gate functions without env export.
- D5: gate blocks non-PM write; PM write passes.
- R3: `dadaia public doctor` exit 0; manual projection check; anti-slop review.
- D4: model field verified in source + both projections.
- R4: audit report complete with cited findings.
- All: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` green before push.
- Ship gate: trio review (QA + code + security) all APPROVE.
