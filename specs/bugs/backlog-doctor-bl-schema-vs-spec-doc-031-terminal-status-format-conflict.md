---
name: backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict
status: Closed
severity: MEDIUM
reported: 2026-06-26
surface: features/backlog/doctor.py (BL-SCHEMA _KNOWN_STATUSES) vs features/specs/doctor.py (SPEC-DOC-031)
session_id: null
---

**Symptom:** A consumed/shipped backlog item cannot satisfy both backlog-status
checks at once. `backlog doctor` BL-SCHEMA validates `status.lower()` against a set
of **bare** tokens (`_KNOWN_STATUSES = {idea, candidate, picked, in-progress,
delivered, rejected, deferred, done, closed, open}`) and HARD-ERRORs anything else.
`specs doctor` SPEC-DOC-031 instead asks a consumed item to use a terminal token
**with a version suffix**: `DELIVERED — vX.Y.Z` (also SUPERSEDED/RESOLVED/CONSUMED).
Setting `status: DELIVERED — v0.1.26` (the SPEC-DOC-031 form) makes
`"delivered — v0.1.26"` ∉ `_KNOWN_STATUSES`, so BL-SCHEMA blocks the commit:

```
[pre-commit] BLOCKED: backlog doctor found 1 error(s):
  BL-SCHEMA [backlog-definition-workflow-dedup-conflict-control] invalid status 'DELIVERED — v0.1.26'
```

Conversely, the BL-SCHEMA-valid bare `delivered` leaves a SPEC-DOC-031 WARN (it
wants the version + evidence pointer). No single `status:` value satisfies both
enforcement points.

**Repro:**
1. Set a backlog item's `status: DELIVERED — v0.1.26`.
2. `git commit` anything → pre-commit `backlog doctor` BL-SCHEMA ERROR (blocks).
3. Set `status: delivered` → commit passes, but `dadaia specs doctor` emits
   SPEC-DOC-031 WARN asking for the `TOKEN — vX.Y.Z` form.

**Expected:** The two doctors should agree on the terminal-status vocabulary for a
consumed/shipped backlog item — one canonical format that passes BL-SCHEMA and
silences SPEC-DOC-031. Options: (a) BL-SCHEMA parses `TOKEN — vX.Y.Z` by splitting
on the em-dash and validating the leading token (accepting the version suffix); or
(b) SPEC-DOC-031 accepts a bare terminal token plus a separate `delivered_in:` /
evidence frontmatter field instead of demanding the suffix inside `status:`.

**Workaround applied (v0.1.26 closure):** set `status: delivered` + a separate
`delivered_in: v0.1.26` frontmatter field on the consumed epic. BL-SCHEMA passes;
SPEC-DOC-031 remains a non-blocking WARN (same advisory class already present on
~7 other archived-referenced candidate items).

**Notes:** Surfaced while closing release v0.1.26 (R2). The em-dash in the
SPEC-DOC-031 example token is `—` (U+2014). `_KNOWN_STATUSES` is documented as
"kept permissive" — the permissiveness should extend to the SPEC-DOC-031 terminal
form so the two checks are reconcilable.

## Resolution

Closed in v0.1.40 alpha-1 T5. `backlog doctor` now validates the leading lifecycle
token before a whitespace-delimited dash suffix, so `DELIVERED — vX.Y.Z` and
`DELIVERED - vX.Y.Z` satisfy BL-SCHEMA while preserving hyphenated bare tokens such as
`in-progress`. ADR-11 terminal tokens also participate in BL-STALE terminal handling.
