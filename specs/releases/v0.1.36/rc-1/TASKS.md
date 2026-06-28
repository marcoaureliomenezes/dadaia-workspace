# TASKS: v0.1.36 rc-1 - PI Layer-2 Release-Definition Ship Gate

**Status:** Aprovado
**Release ID:** v0.1.36
**Segment:** rc-1
**Owner:** product-engineer
**Created:** 2026-06-28

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 - Run deterministic rc validation gates

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** none
- **Acceptance:** Ruff, focused pytest, specs doctor, public doctor, and repo hygiene scan pass with zero errors.

### T2 - Verify alpha live PI evidence is sufficient for rc ship

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.1.36/rc-1/CLOSURE.md`
- **Acceptance:** rc closure references the alpha live PI command/create/review evidence and does not require another expensive live PI run.

### T3 - Close rc-1

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.1.36/rc-1/CLOSURE.md`, `specs/releases/ACTIVE.md`
- **Acceptance:** `rc-1/CLOSURE.md` exists, all rc tasks are `[x] DONE`, and `ACTIVE.md` phase is `CLOSURE`.
