---
name: specs-doctor-dual-error-counter-confusing-output
status: Closed
severity: LOW
reported: 2026-06-09
surface: dadaia specs doctor (features/specs/doctor.py + memory lint output)
session_id: null
resolved_in: 0.1.7 (rc-4, T-017-33)
---

**Resolution (0.1.7 rc-4, T-017-33):** the `doctor` CLI now prints one authoritative final verdict line (`[ok|fail] overall: N error(s)…`), and the embedded memory-lint `Summary:` line is stripped from the LINT-1 issue text so the last output line never contradicts the real result. `specs.py:doctor`, `doctor.py:_check_lint1_memory_atoms`.


**Symptom:** A single `dadaia specs doctor --specs-dir <repo>/specs` run prints
two unreconciled "error" counters:
- Header (tree doctor): `[fail] <specs> — 1 error(s), 6 warning(s):` followed by
  the `[ERR ] SPEC-DOC-002 …` detail.
- Trailing line (memory-atom lint): `Summary: 11 OK, 1 WARN-only, 0 ERROR`.

A reader who trusts the **trailing** `Summary: … 0 ERROR` concludes the tree is
clean, when the tree doctor above actually reported 1 ERROR. The two counters
come from different subsystems (tree-structure doctor vs `lint-memory-atoms`) and
are never reconciled into one overall verdict.

**Repro:**
```
dadaia specs doctor --specs-dir <repo>/specs
# Header: [fail] … 1 error(s), 6 warning(s)
# Footer: Summary: 11 OK, 1 WARN-only, 0 ERROR   <- refers only to memory atoms
```

**Expected:** One authoritative overall verdict. Either (a) print a final
combined summary that sums tree + memory errors and reflects the true exit
status, or (b) clearly label the memory-lint summary as scoped to memory atoms
(e.g. `Memory atoms: 11 OK, 0 ERROR`) so it is not mistaken for the overall
result. The last line of output should never say `0 ERROR` when the run failed
with a tree error.

**Impact:** Confusing/contradictory output; risk of a non-compliant tree being
read as compliant. Low severity (no wrong action by the tool itself).

**Notes:** Surfaced while bringing rand-engine to SDD compliance. Related to
[[specs-upgrade-fails-on-preexisting-doctor-error]] (the upgrade trusts the tree
doctor's error count, which is the correct one — the trailing memory summary is
the misleading surface).
