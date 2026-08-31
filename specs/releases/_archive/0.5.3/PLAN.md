# PLAN — Release 0.5.3

**Status:** Aprovado

- Sequence: folds (01-06) → extractions (07-09) → projection (10-11) → residue (12-13) → container (14) → bug (15) → SpecsTree+registry (16, design-it-twice-informed) → sweep/closure (17-18).
- Method per task: read the audit finding's evidence, write/adjust the RED or pinning test, apply the deletion-shaped diff, run the touched test modules, commit shape 6 (`type(T-053-NN): ...`).
- Integration gates: full pytest after T-053-06, after T-053-14, and at closure; mypy --strict + ruff at closure minimum.
- Ledger: picked bug resolved via `dadaia bugs resolve` inside its fix commit (shape 3).
- Backlog: 5 entries purged-on-pick at definition (CONSUMED provisional); terminal rewrite at closure sweep.
