# SPEC: Release v0.1.72 — Gate coherence: repair paths + preflight enforcement

**Status:** Aprovado
**Release ID:** v0.1.72
**Owner:** product-engineer

## Context

Six bugs reported from the operator's remote against `c33a07aa` (round 3), all in or
around the v0.1.69 preflight subsystem. Root architectural failure: **gates without
repair paths + an advisory gate the guarded verbs never enforced.** The real consumer
(dd-chain-capture v0.2.0, IMPLEMENTATION, everything mandated through `dadaia lifecycle`)
was fully deadlocked. Probes were validated on clean fixture workspaces, never against a
lived-in one (old atoms, real harness lease lineage, accumulated protected evidence).

## Functional Requirements

### FR1 — agent_tier migration (CRITICAL, `memory-agent-tier-migration-deadlock`)
The v0.1.61 schema-drop shipped with no migration; consumers carry atoms with
`agent_tier:` that `specs doctor` correctly rejects, memory writes are phase-locked, and
neither `doctor --fix` nor `specs upgrade` repaired the key.
- FR1.1 New migration step `agent-tier-frontmatter` (registry v2→3;
  `CANONICAL_SPECS_VERSION` = 3): strip the top-level `agent_tier` key (and indented
  continuations) from every `specs/memory/**/*.md` LEADING frontmatter block,
  byte-preserving everything else (no YAML round-trip). Prose mentions untouched.
  Idempotent; dry-run plans without writing.
- FR1.2 Law: a schema-drop MUST ship its migration.
- **Acceptance:** the real dd-chain-capture tree (8 affected atoms) upgrades v1→3 and
  `specs doctor` is clean; on the remote, `specs upgrade` unblocks preflight's
  specs-doctor gate. Real atom committed as fixture.

### FR2 — same-process lease adoption (HIGH, `rebind-does-not-adopt-same-process-lease`)
The lock record can name an old identity (dead session / hook-heartbeat harness id)
whose recorded pid is the live harness process — an ancestor of every CLI it spawns.
The preflight probe's forked identity check (`record sid != incumbent sid` ⇒ foreign)
contradicted acquire's rung-1 `.ptr` canon and blocked rebinds forever.
- FR2.1 `lease.holder_in_lineage(record, ancestry_pids)`: holder pid ∈ current process
  ancestry ⇒ own lineage (a process is never foreign to itself).
- FR2.2 `lease.adopt_if_own_lineage(...)`: bind eagerly rewrites a same-lineage record
  to the new session (same O_EXCL CAS; foreign records never touched).
- FR2.3 The preflight probe uses the same discrimination: own-lineage holder is NOT
  `live_foreign_holder`; a live NON-lineage holder still is.
- **Acceptance:** hermetic both-directions tests + remote replay (bind adopts; preflight
  lease gate passes).

### FR3 — hygiene gate excludes protected residuals (HIGH,
`hygiene-preflight-blocks-protected-residuals`)
`_check_hygiene` blocked on `cleanup_candidate_count > 0` while all candidates were
`protected: current_release_evidence` — which the cleaner refuses to delete.
- FR3.1 Block only when `cleanup_candidate_count - protected_residual_count > 0`.
- **Acceptance:** all-protected passes; one unprotected still blocks; remote replay.

### FR4 — live branch in `context show` (MEDIUM, `context-current-branch-stale-for-alive-repo`)
- FR4.1 For an ALIVE context with a repo on disk, `current_branch` reports the actual
  checked-out branch; the stored snapshot is exposed as `stored_branch` (restore
  metadata). Fallback to stored when the repo is absent; a git error never breaks show.
- **Acceptance:** stored=main vs live=feature/x reports feature/x; remote replay.

### FR5 — fake pipeline completes (HIGH, `fake-pipeline-blocks-missing-artifact-evidence`)
release-definition and implement-review had DRIVING fakes (APPROVED + artifact evidence);
pipeline used the bare fake — so the documented deterministic smoke path always blocked.
- FR5.1 `_pipeline_runtime_factory` (module seam, mirrors implement-review's) injected
  via `build_lifecycle_pipeline(runtime_factory=…)`.
- FR5.2 The v0.1.68 E2E asserted the BLOCKED outcome — inverted: the fake pipeline must
  COMPLETE (exit 0) with write-scope derivation still proven on the executed path.
- **Acceptance:** E2E completes; remote fake pipeline completes.

### FR6 — verbs enforce preflight (HIGH, `workflow-verbs-run-despite-blocked-preflight`)
`preflight` was wired to no verb — it reported "unsafe" while pipeline/implement-review
ran anyway.
- FR6.1 `pipeline` and `implement-review` run the same preflight gate BEFORE creating a
  lifecycle run; BLOCKED refuses with `preflight blocked: <reason>` (exit 3, no run).
- FR6.2 `--skip-preflight` is the explicit, visible operator override (human notice on
  non-JSON output; `--json` stream stays machine-pure). `--show-policy` is never gated.
- FR6.3 Stale `--write-scope` help ("parser out of scope") corrected to the v0.1.71 truth.
- **Acceptance:** E2E: unbound context ⇒ both verbs refuse, no run dir created; with the
  flag they proceed. Remote: blocked preflight refuses the verb.

## Non-goals
- Gating DEFINITION-phase verbs (release/backlog define) on the implementation-shaped
  preflight — a phase-aware preflight is follow-up work, routed to backlog.
- Migrating consumer `specs/memory/AGENTS.md` doc prose (WARN-only, not an ERROR).

## Red lines
- Real consumer artifacts as fixtures; remote replay of the FULL workflow chain before ship.
- RED-first executed-path tests; no workarounds; foreign leases never stolen.
