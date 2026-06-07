# PLAN: v0.1.5 - bug-backlog-release-governance

**Status:** Aprovado
**Release ID:** v0.1.5
**Owner:** product-engineer
**Created:** 2026-06-04

---

## Approach

All AI-entity surfaces (agents, skills, rules) are **lib-originated**: edit source
under `dadaia_workspace/public/<type>/`, then propagate with
`dadaia public stage && dadaia public install --force --target all` and verify
`dadaia public doctor` exit 0. Production Python (pre-push gate, optional CLI)
edits run under the SDD gate (bound implementation session + `[-]` TASKS marker).

v0.1.5 is authored in the **flat** structure — the `alpha-N/rc-N` engine is v0.1.6,
so this release defines the model as **ADRs** but does not implement folder
mechanics. No changes to scaffolder, gate path-resolution, or `ACTIVE.md` schema.

Execution mode: **Direct** (single driver), per operator. Reviewers
(`qa-engineer`, `code-reviewer`, `security-reviewer`) are engaged per the new
cadence only at the rc-ship gate (this release ships when the operator elects).

## Work breakdown → task groups

**G1 — Governance docs (Theme A)**
- `dadaia-release-definition` skill (pick / bug-always-solved / subsumption /
  sanitize / mandatory-grill).
- `product-engineer.md` + `project-manager.md` persona edits.
- `project-orchestration` contract rewrite (segment/release cadence + branch
  model); define `bug-fix-fastlane` / `release-definition` playbook.
- `dadaia-grill-me` mandatory-trigger note.
- `release-governance.md` always-on rule.

**G2 — ADRs (Theme B)** — `adr/ADR-1..4.md`: alpha/rc model + ACTIVE schema-v2
sketch; hotfix unification (supersede `sdd-hotfix-track`); review cadence + branch
model; bug/backlog governance.

**G3 — Pre-push CI gate (Theme C / §3.4)**
- Script `public/scripts/pre-push-ci-gate.sh`: run `ruff format --check`,
  `ruff check`, `mypy --strict`, `pytest` (fast subset); non-zero → block push.
- Wire as a git `pre-push` hook on install (and/or `dadaia ci preflight` command).
- Honor the no-cache-in-repo rules (caches → /tmp).

**G4 — Memory (CLOSURE only)** — new atom `sdd-bug-backlog-governance`; update
release-lifecycle atom; annotate `sdd-hotfix-track` as superseded.

**G5 — Sanitization pass** — triage `specs/releases/v0.1.3` (stale Draft) and
any stale bugs/backlog per the new sanitize protocol (mark `deferred`/`rejected`).

## Sequencing

1. SPEC + PLAN + TASKS approved (operator).
2. G2 ADRs (design record) → G1 governance docs (consume ADR decisions).
3. G3 pre-push gate (independent; high value — lands early to protect later pushes).
4. G5 sanitization.
5. Propagate (`public stage/install/doctor`); full CI-equivalent suite green.
6. G4 memory at CLOSURE.
7. rc-ship gate: operator elects to ship → trio review → push `feature/0.1.5` + PR.

## Risks & mitigations

- **Persona projection gotcha** — `install` skips existing files; use `--force`;
  doctor exit 0 does NOT verify persona projection → verify `.claude/` + `.codex/`
  manually (memory: `project_public_install_agent_projection_gotcha`).
- **Contract rewrite breaks tests** — `project-orchestration` + persona wording is
  asserted by contract/e2e tests (e.g. review-gate contract). Update tests in the
  same task; run the full CI-equivalent suite before any push.
- **Scope creep into the engine** — keep alpha/rc strictly as ADRs; any code that
  touches scaffolder/gate/ACTIVE schema is out of scope → v0.1.6.
- **Gate friction for release-less fixes** — surfaced in v0.1.4; note as a v0.1.6
  backlog item (no clean SDD path for hygiene fixes when ACTIVE=none).

## Validation strategy

- Per the pre-push principle: `ruff format --check`, `ruff check`,
  `mypy --strict`, `pytest` (incl. e2e) all green **locally before any push**.
- `dadaia public doctor` exit 0; `dadaia specs doctor` 0 ERROR.
- Manual persona-projection check in `.claude/agents/` + `.codex/agents/`.
- Demonstrate the pre-push gate blocking a deliberately-failing check.
