# Job 10 — Reconciliation: memory, derived docs, closure ledgers, the rollout list (FR10)

**Status:** Draft

Wave 4, waits on Jobs 1–9. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- Runs in the old-layout `reconcile` tree (rc-16 is built in the old layout). RC-FLOW step 4 order: `release.py phase CLOSURE`, `release.py drift` and the memory pass (shape 9, `dd-product-engineer`), derived docs, generated catalog, `measured_by` repairs, dispositions, measurements. Memory paths are closure procedure and appear in no `W:` (the check refuses them); T1 carries the memory pass in its outcome.
- **Memory pass (AC10.1).** `sdd/worktrees.md` rewritten whole (defect B: the line 'No cap bounds…' is already true in code); `sdd/release-lifecycle.md:36` and the one-clause fix of `:27` ('the newest `until` HEAD reaches opens the window', bug-window finding 3); `sdd/backlog-ledger.md:20`; `platform/workspace-doctor.md`, `platform/context-management.md`; `agents/*`; `philosophy/spec-context-project.md:24`; `product/index.md:66`; `ARCHITECTURE.md:195-200,253-260` and `QUALITY.md:43,49` (scaffold key `tests/tmp/job-<n>/`); the generated catalog and ADR block. Onboarding atoms tell `specs init` cutting the branch and the lane.
- **Derived docs (AC10.2).** Hierarchy words and the onboarding story: `docs/quickstart.md` and the byte-equal `tests/fixtures/quickstart.md` (guard `workspace-quickstart-fixture`), `docs/getting-started.md`, `docs/index.md`, `docs/positioning.md`, `CONTEXT.md`, `README.md`.
- **Closure (AC10.3).** Exit `worktree-hierarchy` and resolve the two Origin bugs (`bugs.py resolve` with fix sha and `caused_by`); `measured_by` repairs; the ADR proposal (supersedes 0191 and 0125; amends 0120 by text) is accepted only by the operator (`specs/ADRs/AGENTS.md` §2); `verdict.py stats 0.5.0-rc16` and `bugs.py archive`; the `memory` milestone through `release.py memory`.
- **Rollout list (AC10.4; the main thread's acts after the Reconciliation merge, not job tasks; no migration code).** The cleanup 'Agente arruma, sem perda' (empty dirs and branches with no own commit deleted; a tree with own work turned into tag `archive/wt/<name>` before removal) already ran BEFORE Job 5's merge (PLAN merge order); here, in order: (1) `public install` on this instance, then `doctor --fix` and `doctor`; (2) `ci install-hook --force` per repo; (3) `certify` green. From Job 5's merge until step 2 job branches are local-only and `feature/0.5.0` pushes continue.
- ADD justification against net lines: PLAN §6.

Tasks: 2 (0 jr, 1 sr, 1 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T2 after T1.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J10.T1 | pe | AC10.1, AC10.2 | `docs/index.md`, `docs/quickstart.md`, `docs/getting-started.md`, `docs/positioning.md`, `CONTEXT.md`, `README.md`, `tests/fixtures/quickstart.md` | memory pass per the intro (paths outside `W:` by the check's rule) and the derived docs, in this order; `memory.py check`, `memory.py drift` and `dadaia doctor` clean |
| J10.T2 | sr | AC10.3, AC10.4 | `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl`, `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl`, `specs/releases/0.5.0/_RELEASE.json` | dispositions, resolutions, archive, `stats` readout in the closure summary, and the rollout list in the summary's `carried`/notes; after T1 |
