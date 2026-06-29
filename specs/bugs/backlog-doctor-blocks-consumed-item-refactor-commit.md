---
name: backlog-doctor-blocks-consumed-item-refactor-commit
status: Closed
severity: MEDIUM
reported: 2026-06-27
surface: pre-commit backlog doctor (BL-SCHEMA) / features.backlog.subject_registry
session_id: null
---

**Symptom:** During v0.1.30 Wave A (a SPEC-approved refactor that consumes the backlog
item `shared-headless-adapter-base`), the pre-commit hook BLOCKED the implementation
commit with:

```
[pre-commit] BLOCKED: backlog doctor found 1 error(s):
  BL-SCHEMA [shared-headless-adapter-base] subject ref
  'dadaia_workspace/infrastructure/pi_runtime.py#_SECRET_NAME_PARTS' (kind=code)
  resolves to no known anchor; add it as an alias in the operator alias map, or
  correct the ref.
```

The backlog item's `intents[].subject.ref` anchors deliberately point at the
*pre-refactor* code locations (where the duplication lived). The whole purpose of the
release is to MOVE those anchors (hoist `_SECRET_NAME_PARTS` etc. into a shared base).
The moment the refactor lands, the consumed item's anchors necessarily go stale — yet
the per-commit BL-SCHEMA gate fires and blocks the very commit that implements the
consumed item.

**Repro:**
1. Have a backlog item whose `subject.ref` anchors point at code symbols.
2. Land a refactor (authorized by a release that `**Consumes:**` that item) which moves
   those symbols to a new module.
3. `git commit` the refactor → pre-commit backlog doctor blocks on BL-SCHEMA
   (anchor no longer resolves).

**Expected:** A refactor that consumes a backlog item should not be blocked by the
consumed item's now-stale anchors. The item's disposition (anchors updated / flipped to
DELIVERED) happens at CLOSURE, but the per-commit gate enforces anchor resolution during
implementation. Either the gate should treat a `**Consumes:**`-declared item as exempt
during its consuming release's IMPLEMENTATION phase, or the operator alias map should be
the documented escape hatch (the block message mentions it but there is no smooth flow).

**Workaround used:** updated the three `subject.ref` anchors in
`specs/backlog/shared-headless-adapter-base.md` to the new shared-base home
(`headless_adapter_base.py#_SECRET_NAME_PARTS` / `#ChangedPathsMixin` /
`#SubprocessAdapterMixin`) so the anchors resolve again. This is a PM-curated file
edited by the implementer purely to unblock — flagged in the Wave A handoff.

**Notes:** Self-hosting dadaia-workspace source repo, branch feature/v0.1.30. The
backlog file is ADDITIVE class so editing it was permitted by the SDD gate; the friction
is the per-commit BL-SCHEMA enforcement colliding with the consume-on-release lifecycle.

## Resolution

Closed in v0.1.40 alpha-1 T5. `backlog doctor` now reads the active release
`**Consumes:**` declaration during IMPLEMENTATION/CLOSURE and exempts those consumed
slugs from unresolved subject-anchor BL-SCHEMA findings. Malformed intents, missing
intents, duplicate/conflict checks, and non-consumed stale anchors remain enforced.
