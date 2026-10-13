# Job 2 — the reconcile tree's writes have their shape, and closure readouts live in the summary (FR1)

**Status:** Draft

Wave 1. Shipped law only, no code and no test: two commit-shape rows and three texts that place a closure readout in a PLAN or SPEC. None of the four files is canon-fingerprinted (the fingerprint covers `public/scaffold/*/AGENTS.md`, `templates/specs-AGENTS.md`, `data/fixed` and `FIXED_SECTIONS`), so no pin moves here. `specs/AGENTS.md` §4 keeps "read-only after its closure" and gains no exception (Q4 option B, agent default).

- **Seams closed.**
  - §3a today bundles three ADR writes in rows 2 and 3. After the edit: the backlog entry or exit row names `backlog/<slug>`, `reconcile`; the ADR proposal row names `backlog/<slug>`, `define` and no other tree; the in-place `measured_by` repair becomes its own row 2 line naming `define`, `reconcile` (message `chore(adrs): repair …`); the acceptance row is unchanged. Rows 4 and 8 and every other row stay byte-identical.
  - The readouts clause: `RC-FLOW.md` step 4 says the rc's independent measurement, `verdict.py stats` and the goal readouts are recorded only in the `summary` entry and that a closed SPEC and PLAN are not written; `RELEASE-EVENTS.md` adds `readouts: …` to the `summary` completion criterion; the PLAN skeleton of `dd-release-definition` §2 says a PLAN holds no closure readout. `release.py check` reads `delivered`, `carried` and `backlog exits` only, so no code follows.
  - Public law names no ADR number, bug id or task id (the public-source hygiene row): the new text states the rule, not its history.
- **Consumers.** `git grep -nE 'shape [0-9]+' -- dadaia_workspace/public` lists the citing texts; no row number moves because the split rows keep `2`.
- Both tasks have disjoint `W:` and run in parallel.
- Commit bodies carry `git grep -n -i 'readout' -- dadaia_workspace/public` (the hits before and after, each reading named).
- Pre-review checklist: one home per rule (the §3a row, the summary entry); sweep line above; net law lines ≤ 0 except the split row.

Tasks: 2 (2 jr, 0 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J2.T1 | jr | AC1.1 | `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` | §3a as the intro says; no test, reviewer sweep: `git diff` touches only the row 2 lines, and `reconcile` appears in exactly the backlog entry or exit row and the repair row among row 2 lines |
| J2.T2 | jr | AC1.2 | `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`, `dadaia_workspace/public/skills/dd-release-definition/SKILL.md` | the readouts clause in step 4, the `summary` row and the PLAN skeleton as the intro says. No test, reviewer sweep with the `readout` grep |
