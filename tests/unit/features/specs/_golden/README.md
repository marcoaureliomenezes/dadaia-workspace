# SpecsDoctor golden behavior lock (v0.1.55 FR1 / T-55-10, AC-2)

`fixture_specs/` is a fixed, committed `specs/`-shaped tree engineered to trigger **>=1 issue
from EACH of the six `SpecsDoctor` validator families** with the interleaved `check()` order
visible:

| Family | Triggered by |
|---|---|
| coherence | missing `constitution.md` → `SPEC-DOC-001`; unstamped pattern → `SPECS-VERSION` |
| memory | missing `memory/` atoms → `SPEC-DOC-002` |
| release | `ACTIVE.md` → missing `v9.9.9` dir → `SPEC-DOC-009`; non-SemVer `badname-release` (Created 2026-07-10) → `SPEC-DOC-016`/`SPEC-DOC-027` (date-gated) |
| closure_audit | loose `audits/bad-audit-name/` → `SPEC-DOC-030`/`SPEC-DOC-038`; missing `_archive/` → `SPEC-DOC-034` |
| governance | loose `backlog/candidates.md` (not `BACKLOG.md`/`README.md`) → `SPEC-DOC-035` (single-source invariant, SPEC v0.12.0 FR5) |
| structural | missing dirs/atoms → `TREE-3`/`TREE-4`/`TREE-5`/`TREE-5M` |

`doctor_golden_v0155.json` is the byte-identical capture (see `../test_doctor_golden.py`):
the CLI `--json` payload with every absolute path normalized to `<SPECS>` and the clock frozen
to 2026-07-15. The fixture deliberately has **no `memory/` dir**, so LINT-1 never shells out —
the capture is fully deterministic.

**Do not hand-edit the golden.** It is the behavior lock: a decomposition that changes the
observable output must fix the split, not the golden. Regenerate ONLY for an approved,
deliberate behavior change with:

```bash
UPDATE_DOCTOR_GOLDEN=1 pytest tests/unit/features/specs/test_doctor_golden.py
```
