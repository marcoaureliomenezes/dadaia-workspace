# Job 8 — dd-grill-me complete, name kept: stage references, artifact-first report, three triggers (FR1)

**Status:** Draft

Wave 2, after Job 2: FR2's schema change lands before the adr reference cites `options` (SPEC delivery constraint). REBUILD of the skill (PLAN §1 row 1): the skill keeps the name `dd-grill-me`; `SKILL.md` keeps the common core, the four stage references carry what differs, `EMISSION-FORMAT.md` is deleted (the artifact-first rule with the CSS fallback replaces report mode), `PROBLEM-TAXONOMY.md` stays.

- Shipped text names no ADR number and no library path (FR4); the adr reference cites the law's threshold and `options` by name, never by number.
- AC1.3's check is `grep -rn 'whole frontier\|grill-<slug>.md' dadaia_workspace/public` returning nothing; the commit body quotes it with its count.
- Test-side first: T1. Then T2 (the core), T3, T4, T5, T6 in parallel; all `W:` are disjoint.
- The skill is standalone (`standalone_skills` in `behavior-map.json`): `references/` and the CSS file name no workspace-only path. Check the standalone-skill and projection tests on the first RED run.
- No-test tasks name the reviewer's source sweep as their check; net lines cannot shrink (the operator ordered the behaviour), and the commit body of T3 says so.
- Pre-review checklist: no code; the sweep lines of AC1.3 with counts; no cross-component import or cycle; net lines cannot shrink (stated above).

Tasks: 6 (2 jr, 4 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J8.T1 | sr | AC1.4 | `tests/infrastructure/test_public_assets__grill_references.py` | RED, integration: after `public stage`/`public install` the projected `dd-grill-me` holds `references/backlog.md`, `references/release.md`, `references/adr.md`, `references/plan.md` and `scripts/report.css`. New file, owner `test_public_assets__grill_references.py` |
| J8.T2 | sr | AC1.1, AC1.2, AC1.3, AC1.4 | `dadaia_workspace/public/skills/dd-grill-me/SKILL.md`, `dadaia_workspace/public/skills/dd-grill-me/EMISSION-FORMAT.md` | REBUILD the core: one question at a time, three closed options with trade-offs, one recommended, free text through the tool's open answer; each stage names its reference; the harness artifact first, else an HTML report styled by `scripts/report.css`; every answer lands in a durable record in the same turn (entry description, ADR `options` and `ruling.words`, or SPEC), the handoff stays ephemeral; delete `EMISSION-FORMAT.md`. No test; reviewer sweep: a grep of `dadaia_workspace/public` for `EMISSION-FORMAT` and for `whole frontier` returns nothing |
| J8.T3 | sr | AC1.1 | `dadaia_workspace/public/skills/dd-grill-me/references/backlog.md`, `dadaia_workspace/public/skills/dd-grill-me/references/release.md` | the backlog reference (is it a decision at all: problem measured, feature or bug, scope) and the release reference (before the SPEC). No test; reviewer source sweep |
| J8.T4 | sr | AC1.1 | `dadaia_workspace/public/skills/dd-grill-me/references/adr.md`, `dadaia_workspace/public/skills/dd-grill-me/references/plan.md` | the adr reference (the three-leg threshold and the question bank: reversibility, decision drivers, a quality-attribute scenario whose response measure becomes `measured_by`, the surface's bug history, ownership and coupling, reuse, failure and rollback, cost, security, what it lets us delete, the accepted drawback, open issues; the record carries `options` and self-contained `ruling.words`) and the plan reference (does the PLAN contradict an accepted ADR, or carry a technical decision past the threshold). No test; reviewer source sweep. After Job 3 |
| J8.T5 | jr | AC1.4 | `dadaia_workspace/public/skills/dd-grill-me/scripts/report.css` | one CSS file for the HTML fallback report: plain tables, readable on a white page, no external font or script. Owner T1 |
| J8.T6 | jr | AC1.2 | `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-release-definition/SKILL.md` | three trigger lines: before `backlog.py new`; in §3 before the SPEC or any ADR; after the PLAN for a technical decision past the threshold only. No test; reviewer sweep: each of the two skills names `dd-grill-me` and its reference once |
