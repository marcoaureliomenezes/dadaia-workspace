---
name: deprecation-strips-and-doctor-cleanup
status: candidate
opened: 2026-07-10
owner: project-manager (curates)
priority: P3
source: "consolidation 2026-07-10 (operator-ratified): merges `dispatch-band-legacy-fallback-removal` (v0.1.64 closure return, date-gated) + `specs-doctor-partial-archive-invariant` (v0.1.61 closure return, audit G-23) into one low-risk cleanup entry"
absorbs:
  - backlog: dispatch-band-legacy-fallback-removal (superseded)
  - backlog: specs-doctor-partial-archive-invariant (superseded)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/agents/reader.py#_raw_to_dto" }
    change: "strip the v0.1.64 rename's tolerate window — **eligible from 2026-08-01** (deprecation-expiry law; one consumer re-projection window since every `dadaia public install` post-v0.1.64 projects `dispatch_band:` bodies). Remove the silent legacy `tier:` frontmatter fallback (the second read `band_raw = raw.get('tier')`, reader.py:173 — re-verified present 2026-07-10), drop `tier` from _ALLOWED_FIELDS (an unknown `tier:` then gets the standard unknown-field drop warning; band defaults to 3 with the missing-band warning), delete the deprecated module-level alias `MissingTierError = MissingDispatchBandError` (reader.py:109) and its features/agents/__init__.py re-export, and flip the AC-6 fallback test from proving silent tolerance to proving the legacy key is unknown. The dispatch_band-preferred path, the contract test's pinned model/effort map, and the registry `Tier` (model-cost axis, unrelated) are untouched."
  - subject: { kind: code, ref: "dadaia_workspace/features/specs/doctor_release.py#ReleaseValidator" }
    change: "add the specs-doctor WARNING invariant flagging PARTIAL archived release dirs: a specs/_archive/releases/<id>/ directory containing none of SPEC.md/PLAN.md/TASKS.md/CLOSURE.md is residue masquerading as an archived release (the v0.1.41 case held only GRILL.md + OQ-DECISIONS.md and sat undetected until the 2026-07-06 audit; v0.1.61 fixed the instance, deferred the invariant per ADR-5). The check honors the SPEC-DOC-027 legacy-name allowlist, tolerates segmented layouts (<id>/<segment>/), suggests relocation to specs/_archive/wip-abandoned/<id>/ with a README breadcrumb (the G-23 remediation precedent), and stays WARNING so historical trees never hard-fail doctor."
---

# BACKLOG — Deprecation strips & doctor cleanup (P3)

**Priority: P3 (LOW, low-risk, bounded).** Two small disjoint cleanups consolidated into
one tight entry so debt actually dies instead of lingering as micro-items:

1. **Dated strip** of the v0.1.64 `tier:` → `dispatch_band:` tolerate window
   (fallback read + allowlist entry + `MissingTierError` alias + test inversion).
   **Ship constraint: on/after 2026-08-01.**
2. **Doctor coverage gap** (audit G-23): the WARNING invariant for artifact-empty
   `_archive/releases/<id>/` dirs.

**Note:** `platform-seam-todo-retirement` was previously grouped with the dispatch-band
strip; it now rides inside the P0 `lock-lease-session-identity-kernel` entry (same
`locking.py` surface, one frozen-suite adjudication) — it is NOT part of this entry.
