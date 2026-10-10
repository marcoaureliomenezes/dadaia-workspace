# Job 4 — law and skill text (FR5, AC2.4, AC6.1)

**Status:** Draft

Wave 3. Waits on Job 2 and on the operator's acceptance of ADR 0240 (the main thread writes `accepted`, `ruling` and `amends: "0022"` with the memory hunks the ADR names; no engineer writes them). Text edits delete or correct before they add; no mechanism is added. The AC5.2 rule (one REJECTED verdict on a `jr` task re-dispatches it to `dd-sw-engineer-sr`) is stated once, in `dd-manager-orchestration`, and the other skills point to it. Sources are exactly the AC6.1 set plus the two PLAN notes (`bugs.py:117` and the `shipped-hashes.json` re-record).

- All tasks have disjoint `W:`; at most 5 open at once. Projections change only by `public stage` and `public install` after the merge.
- Commit bodies carry `git grep -c 'dd-software-engineer'` for the touched files (target 0) and the AUTHORING contract check for every skill and persona-adjacent file.

Tasks: 7 (3 sr, 4 jr).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J4.T1 | sr | AC2.4 | `dadaia_workspace/public/data/AGENTS.md` | root map: §2 names five roles with their owners (sr: as-is review, PLAN, job files, new behaviour; jr: tasks stated by AC and `W:`; researcher: read-only findings), the ADR line no longer says "Three roles, no fourth", §6 reads "dispatching the five roles" |
| J4.T2 | jr | AC2.4, AC2.5 | `dadaia_workspace/public/data/CONTEXT-MAP.md`, `dadaia_workspace/public/data/fixed/slop-tests.md`, `dadaia_workspace/public/templates/specs-AGENTS.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/templates/shipped-hashes.json` | doc sync: the personas table lists five surfaces; the pruning line and the artifact-authority row name `dd-sw-engineer-sr`; the releases law §3 names the `who` column; `shipped-hashes.json` appends the new digest of each edited template, last in the task |
| J4.T3 | sr | AC2.4, AC5.2 | `dadaia_workspace/public/skills/dd-manager-orchestration/SKILL.md` | five-role dispatch; research goes to `dd-researcher` in place of `Explore` and `general-purpose`; engineer dispatch follows the task's `who:`; the AC5.2 escalation rule, stated once; the decision-authority table names the sr persona |
| J4.T4 | sr | AC5.1 | `dadaia_workspace/public/skills/dd-release-definition/SKILL.md` | §5 adds the `who` column (`sr` or `jr`) to the task table and its example, with the shape rule (jr: outcome fully stated by AC and `W:`; sr: new behaviour, design choice, root cause, RED test of a new contract, PLAN, job files, as-is review); §2 and the lead line name the sr persona |
| J4.T5 | jr | AC5.3 | `dadaia_workspace/public/skills/dd-code-review/SKILL.md` | one line in the Spec axis: the `define`-tree reviewer judges the job-file `who` column against the shape rule in `dd-release-definition` §5 |
| J4.T6 | jr | AC2.5 | `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`, `dadaia_workspace/public/schemas/handoff-v1.schema.json` | rename: the implementer line in both skills, the `reported_by` default string and the schema's example agent name become `dd-sw-engineer-sr` (`dd-release-implementation` points to the manager skill for dispatch and does not restate it) |
| J4.T7 | jr | AC1.2 | `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CONTEXT-ENGINEERING.md` | the registry-tier table names the four alias tiers (`fable`, `opus`, `sonnet`, `haiku`) with the same workload characters, and still tells the reader to take ids from the registry, never a hand copy |
