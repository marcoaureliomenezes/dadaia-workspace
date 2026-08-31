---
slug: specs-doctor
title: specs-doctor
category: product
tldr: Validates the v6 canon tree, memory drift and catalog integrity, _RELEASE.json, bug and backlog governance, and audit findings folded from JSONL.
summary: dadaia specs doctor coordinates structural, memory, release, closure/audit, governance and coherence validators over the v6 canon; it reports, never blocks, and fixes only deterministic state.
tags: [specs, doctor, validation, sdd]
---

## Validator families

- Specs doctor verifies that SDD artifacts are structurally and semantically coherent before release advancement or closure; it reports, and the enforcement lane is the gate ([[sdd-gate-v3]]).
- `features/specs/rules.py::RULES` is the one ordered registry: check order, fix dispatch and the `--fix` CLI help are three projections of the same table, never hand-kept copies.
- Each `check()` run builds a fresh `SpecsTree` snapshot (`features/specs/specs_tree.py`): the active release is parsed once per run; fixes mutate paths and the next run re-parses.
- `features/specs/canon.py`'s `CANON` table is the one definition of what a `specs/` tree may hold: `scaffold` renders it, `check_tree` checks it, and a scaffolded tree passes its own doctor by construction.
- `TREE-*` covers the canonical tree, required rule files and the absence of repo-local runtime or cache state.
- `TREE-8` is the v6 canon-root check over top-level membership under `specs/` — WARN-only, ignoring dotfiles.
- `TREE-5` covers the root `specs/AGENTS.md` AND every scoped scaffold law file (releases, releases/_ideas, backlog, bugs, audits, ADRs; memory excluded by single-ownership): a projection byte-identical to a shipped version (`shipped-hashes.json`, every historical scaffold version recorded) is refreshed losslessly by `--fix`; anything else stays warn-only.
- `SPEC-DOC-*` release checks cover the active release and phase, artifact presence and `**Status:** Aprovado`, task-marker coherence, naming (`SPEC-DOC-027`, the one naming rule — `SPEC-DOC-016` and `TREE-6` retired at 0.5.3: one rule, one implementation), unique ids, archive-shape and partial-archive-residue invariants, and release references.
- The live release and its phase are read from `_RELEASE.json` through one reader (legacy `RELEASE.json` read-side accepted; SPEC-DOC-046 offers the fixable rename); zero live release directories resolves cleanly to no active release; the segment lane is retired (0.4.6, ADR 0006).
- Memory checks cover Markdown, frontmatter and atomicity, forbidden history sections, Mermaid and image references, catalog/index agreement, and unfilled `<PLACEHOLDER>` tokens in atoms (ERROR) or an installed `tests/AGENTS.md` (WARN).
- `CAT-1` reconciles catalog entries against atom files by slug set, so which optional fields the persisted catalog carries is outside what it asserts ([[context-management]]).
- `MEM-DRIFT-1` compares `ARCHITECTURE.md`'s features package-map diagram against the live `dadaia_workspace/features` tree, one WARNING per stale or missing package and silence when the heading or its Mermaid block is absent.
- `SPEC-DOC-033` reads `BUGS.jsonl` only through the injected bug store, reporting each line that store cannot parse as one ERROR; it re-derives no field and raises no coherence WARNING.
- `SPEC-DOC-031` flags an active backlog item left non-terminal while an archived release asserts it was consumed, counting only an archived SPEC's `**Consumes:**` declaration with candidate slugs isolated as whole tokens.
- `SPEC-DOC-035` is the single-source invariant: any item file loose directly under `specs/backlog/`, other than `BACKLOG.json` and its scoped rule file, is drift; the entry schema belongs to `backlog doctor`'s BL-* codes.
- `SPEC-DOC-036` and `SPEC-DOC-038` fold `FINDINGS.jsonl`, never audit prose: an `open` finding in an archived audit is an ERROR, and a live audit whose findings are all terminal is an archive-due WARNING.
- `SPEC-DOC-030` checks the audit directory shape `<YYYYMMDD>-<slug>` (`core/workspace_layout.py::AUDIT_DIR_NAME_RE`, the fragment `canon.py` imports), and constitution checks cover required invariant references and `specs_pattern_version` 6.
- `SPEC-DOC-045` requires `pyproject.toml`'s `[tool.poetry].version` to equal the release id once the release is in `CLOSURE` or later; it is silent without a repo root, a pyproject or a live release.
- `SPECS-VERSION` names the fix for a pre-v6 stamp — migrate the tree and re-stamp `constitution.md`; `dadaia specs upgrade` refuses pre-v6 trees.
- `dadaia memory product add <slug> --area <area>` writes `product/<area>/<slug>.md`, validated by `canon.is_canon_path`, the same decider the doctor and the pre-push gate use.
- The split across doctors is by subject — `public doctor` carries the privacy-baseline carve-out rationale check, `dadaia doctor` owns workspace-state invariants ([[workspace-doctor]]), `backlog doctor` owns the backlog document model.
- `--recipe` renders ordered, copy-pasteable steps over the same finding objects `--json` emits, every step tracing to a finding id in that run.
- `--fix` regenerates deterministic catalog/tree artifacts and normalizes supported archive layout, inventing no approval, task completion, evidence, disposition or operator decision.

## Dependencies

[[sdd-bug-backlog-governance]], [[audits-canon]], [[workspace-doctor]], [[sdd-gate-v3]].
