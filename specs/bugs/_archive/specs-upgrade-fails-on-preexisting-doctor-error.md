---
name: specs-upgrade-fails-on-preexisting-doctor-error
status: Closed
severity: MEDIUM
reported: 2026-06-09
surface: dadaia specs upgrade (cli/commands/specs.py upgrade())
session_id: null
resolved_in: 0.1.7 (rc-4, T-017-33)
---

**Resolution (0.1.7 rc-4, T-017-33):** `upgrade()` snapshots doctor errors BEFORE the migration and only `[fail]`+advise-restore on errors the migration NEWLY introduced; pre-existing unrelated errors → `[warn]` + exit 0 (migration kept). `specs.py:upgrade`.


**Symptom:** `dadaia specs upgrade` runs the migration successfully (pattern
version 0 → 1, backup taken, files moved), then runs `SpecsDoctor.check()`,
finds a doctor ERROR that **pre-existed the upgrade and was not caused by it**,
declares `[fail] doctor reports 1 error(s) after upgrade`, advises
`Restore from: <backup>`, and exits non-zero.

**Repro:**
```
# A tree at version 0 that already has a pre-existing tree ERROR
# (e.g. a missing canonical memory atom: SPEC-DOC-002 quality-assurance.md):
dadaia specs upgrade --specs-dir <repo>/specs --yes
# -> [upgrade] 0 → 1   (migration succeeds, backup written)
# -> [fail] doctor reports 1 error(s) after upgrade. Restore from: <backup>
# -> exit 1
# The SAME error is present in the backup (pre-upgrade), proving the upgrade did
# not introduce it:
dadaia specs doctor --specs-dir <repo>/specs_bkp/0→1-<UTC>   # also 1 error
```

**Expected:** The upgrade should distinguish errors **introduced by the
migration** from **pre-existing, unrelated** errors. A successful migration whose
only post-doctor errors already existed pre-upgrade must NOT be reported as an
upgrade failure, and must NOT advise restoring (restoring reverts a good
migration to version 0 while keeping the very same error). At minimum: diff the
pre-upgrade vs post-upgrade doctor error sets; only `[fail]` + advise-restore on
**newly introduced** errors; for pre-existing errors, succeed with a `[warn]`
that the tree still has unrelated issues to fix separately.

**Impact:** Non-zero exit breaks any automation chaining on upgrade success even
though the migration worked; the "Restore from backup" advice is actively
harmful (would discard the successful version bump). Surfaced while preparing the
rand-engine spec-context for SDD compliance.

**Notes:** The migration itself is correct and idempotent; this is purely the
post-upgrade verification/exit-code/advice logic in `upgrade()`
(`cli/commands/specs.py`). Related reporting confusion tracked in
[[specs-doctor-dual-error-counter-confusing-output]].
