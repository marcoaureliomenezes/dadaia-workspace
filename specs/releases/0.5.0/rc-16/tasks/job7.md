# Job 7 — Law, skills, agents, templates describe the hierarchy (FR7)

**Status:** Draft

Wave 3, waits on Job 5. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- Text only, no `.py`. Law text for behaviour not yet built would drift, so it follows Job 5 (agent default, unruled). Every AI-entity change follows `dd-ai-eng-knowhow` AUTHORING and passes the reviewer's AI-surface lens; `public doctor` must print `[ok] public-privacy`; an edited `SKILL.md` stays under the SKILL-MD-LENGTH limit.
- Sweep after every task: `grep -n '<job>--\|/define\|/reconcile\|plain\|wt/hotfix/\|wt/backlog/\|worktree\.py' <the task's files>` = 0, except the runner's own mention. `WT` means `dadaia worktree …` everywhere. Shape 9's 'first-pass plain tree' becomes the `wt-backlog-first-pass` lane (Job 9) in `dd-gitflow-default/SKILL.md:67` and map §7 3b (`data/AGENTS.md`).
- `specs/releases/AGENTS.md` and `specs/bugs/AGENTS.md` in the repo are mirrors of the scaffold sources named below; the Reconciliation refreshes them (`specs upgrade`). `test_gate_policy__law_states_what_the_code_does.py` stays green.
- Law, not behaviour: no test except the guards. The `worktrees-AGENTS.md` statement shrinks (39 lines now, at most 34 after).

Tasks: 4 (3 jr, 1 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T1–T4 have disjoint `W:` and run together.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J7.T1 | sr | AC7.1 | `dadaia_workspace/public/data/worktrees-AGENTS.md` | the hierarchy, leaf names, three merges, lanes, `sync`, the hook, the cutover; in fewer lines than today. No test: law text; guards + `public doctor` + the reviewer's AI-surface lens |
| J7.T2 | jr | AC7.2 | `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md` | §2a/§3a/§2 step 11/§5, `RC-FLOW` define and reconcile as `wt-rc` commits, shape 9 and 10 trees; old grammar words gone; sweep = 0 |
| J7.T3 | jr | AC7.3 | `dadaia_workspace/public/skills/dd-manager-orchestration/SKILL.md`, `dadaia_workspace/public/skills/dd-release-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-registration/SKILL.md`, `dadaia_workspace/public/skills/dd-code-review/SKILL.md`, `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-SPECS.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CODEX.md` | old tree names and `worktree.py` become the hierarchy and `dadaia worktree`; sweep = 0 |
| J7.T4 | jr | AC7.4 | `dadaia_workspace/public/agents/dd-code-reviewer.md`, `dadaia_workspace/public/agents/dd-sw-engineer-sr.md`, `dadaia_workspace/public/agents/dd-sw-engineer-jr.md`, `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/data/handoff-AGENTS.md`, `dadaia_workspace/public/data/dadaia-AGENTS.md`, `dadaia_workspace/public/data/CONTEXT-MAP.md`, `dadaia_workspace/public/scaffold/bugs/AGENTS.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/schemas/handoff-v1.schema.json` | agents, projected map sources, scaffold laws (`releases` define tree → `wt-rc`; `bugs` §2 hotfix text), template, schema descriptions; sweep = 0 |
