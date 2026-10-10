# Job 6 — Reconciliation

**Status:** Draft

Wave 5, last: one tree (`0.5.0-rc13/reconcile`), cut once Jobs 1–5 have merged. Order: `release.py phase CLOSURE --sha <sha>` first, then `release.py drift` and the memory pass (`MEMORY-UPDATE.md`), then derived docs, the generated catalog, the `measured_by` repair, the backlog exit and the measurements. T2 is dispatched to `dd-product-engineer` (the memory pass is its role); its `who` is `sr` because the column admits only the two engineer tiers.

ADD justification (net lines ≤ 0 for production code): production code shrank across Jobs 1–3 (the registry, overrides, Fable guard, `parse()`, the Codex id rewrite and two doctor checks leave; `TIER_CODEX`, two options and one `save` call enter). The ADD is AI-entity files, three personas for the one deleted (about +150 lines), and the new alias-contract, template-table and selector tests. T1 records the measured diff (`git diff --shortstat <base>...HEAD -- dadaia_workspace` and `-- tests`) beside this statement.

- Exit: the sweep lines from the PLAN, `public stage`, `public install` and `public doctor` clean on this instance, `dadaia doctor` clean. The instance reflects the library only through those verbs, never by hand.

Tasks: 4 (1 sr, 3 jr).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J6.T1 | jr | AC1.5, AC2.5, AC6.1 | `specs/releases/0.5.0/rc-13/PLAN.md`, `specs/releases/0.5.0/rc-13/tasks/job6.md` | measurement: record the sweep lines (`git grep -c 'dd-software-engineer'`, the claude-id grep with target 0, `git grep -n 'dd-software-engineer' -- dadaia_workspace tests` printing nothing), the kept-class figure with each remaining file classified, the net-lines diff and the AC6.1 source sweep (every changed source is in the set) |
| J6.T2 | sr | AC2.4, AC3.1, AC4.1 | `specs/memory/product/agents/agent-orchestration.md`, `specs/memory/product/agents/agentic-entities.md`, `specs/memory/product/distribution/public-asset-distribution.md`, `specs/memory/product/platform/workspace-init.md`, `specs/memory/product/catalog.json`, `specs/memory/product/index.md` | memory pass (`dd-product-engineer`): the roster of five, the alias table, `--template` on `public install` and `init`, and the removed overrides in the four atoms; `memory.py catalog generate` re-records `catalog.json` and `index.md`; `release.py drift` is empty |
| J6.T3 | jr | AC2.5, AC6.1 | `docs/bug-loop.md`, `specs/AGENTS.md`, `specs/releases/AGENTS.md`, `specs/memory/QUALITY.md` | derived law and docs: `specs upgrade` refreshes `specs/AGENTS.md`, `specs/releases/AGENTS.md` and the fixed `QUALITY.md` section from the shipped sources; `docs/bug-loop.md` names `dd-sw-engineer-sr` |
| J6.T4 | jr | AC1.1, AC2.1 | `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl`, `specs/ADRs/decisions.jsonl`, `specs/releases/0.5.0/_RELEASE.json` | closure ledgers: `backlog.py exit` for `subagent-model-tiers`, the ADR 0240 `measured_by` repair in place (shape 2), the `_RELEASE.json` memory milestone through `release.py memory` |
