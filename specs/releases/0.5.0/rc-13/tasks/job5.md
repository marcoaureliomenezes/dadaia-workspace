# Job 5 — Reconciliation

**Status:** Draft

Wave 5, last: one tree (`0.5.0-rc13/reconcile`), cut once Jobs 1–4 have merged. Order: `release.py phase CLOSURE --sha <sha>` first, then `release.py drift` and the memory pass (`MEMORY-UPDATE.md`), then derived docs, the generated catalog, the `measured_by` repair, the backlog exit and the measurements. T2 is the memory pass and belongs to `dd-product-engineer` (`pe`).

ADD justification (net lines ≤ 0 for production code): production code shrank across Job 1 (the registry, overrides, Fable guard, `parse()`, the Codex id rewrite and two doctor checks leave; `TIER_CODEX`, two options, one `save` call and one error field enter). The ADD is AI-entity files, three personas for the one deleted (about +150 lines), and the new alias-contract, template-table, selector and remedy tests. T1 records the measured diff (`git diff --shortstat <base>...HEAD -- dadaia_workspace` and `-- tests`) beside this statement.

- Exit: the sweep lines from the PLAN, `public stage`, `public install` and `public doctor` clean on this instance, `dadaia doctor` clean. The instance reflects the library only through those verbs, never by hand.
- AC4.6 instance step: the main thread runs `dadaia public install --template balanced` on this instance (the overlay is PROTECTED, so no engineer writes it; it drops the operator's two medium-effort overrides, which the operator is told), then `dadaia public doctor`, and T1 records `[ok] model-resolution: template balanced` as evidence.

Tasks: 4 (3 jr, 1 pe). `who` names the dispatched role (SPEC AC5.1).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J5.T1 | jr | AC1.5, AC2.5, AC4.6, AC6.1 | `specs/releases/0.5.0/rc-13/PLAN.md`, `specs/releases/0.5.0/rc-13/tasks/job5.md` | measurement and evidence: record the sweep lines (`git grep -c 'dd-software-engineer'`, the claude-id grep over `dadaia_workspace tests`, `git grep -n 'dd-software-engineer' -- dadaia_workspace tests` printing nothing), the kept-class figure with each remaining file classified, the net-lines diff, the AC6.1 source sweep (every changed source is in the set) and the AC4.6 `public doctor` line |
| J5.T2 | pe | AC2.4, AC3.1, AC4.1, AC6.2 | `specs/memory/product/agents/agent-orchestration.md`, `specs/memory/product/agents/agentic-entities.md`, `specs/memory/product/distribution/public-asset-distribution.md`, `specs/memory/product/platform/workspace-init.md`, `specs/memory/product/harness/harness-claude-code.md`, `specs/memory/product/harness/harness-codex.md`, `specs/memory/product/harness/harness-copilot.md`, `specs/memory/product/catalog.json`, `specs/memory/product/index.md` | memory pass (`dd-product-engineer`): the roster of five, the alias table, `--template` on `public install` and `init`, the removed overrides, and the "three dd- personas" summaries of the three harness atoms; `memory.py catalog generate` re-records `catalog.json` and `index.md`; `release.py drift` is empty |
| J5.T3 | jr | AC2.5, AC6.1 | `docs/bug-loop.md`, `specs/AGENTS.md`, `specs/memory/QUALITY.md` | derived law and docs: `specs upgrade` refreshes `specs/AGENTS.md` and the fixed `QUALITY.md` section from the shipped sources; `docs/bug-loop.md` names `dd-sw-engineer-sr` |
| J5.T4 | jr | AC1.1, AC2.1 | `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl`, `specs/ADRs/decisions.jsonl`, `specs/releases/0.5.0/_RELEASE.json` | closure ledgers: `backlog.py exit` for `subagent-model-tiers`, the ADR 0240 `measured_by` repair in place (shape 2), the `_RELEASE.json` memory milestone through `release.py memory` |
