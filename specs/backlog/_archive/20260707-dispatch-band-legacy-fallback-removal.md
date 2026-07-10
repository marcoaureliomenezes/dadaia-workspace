---
name: dispatch-band-legacy-fallback-removal
status: superseded
superseded_by: deprecation-strips-and-doctor-cleanup (consolidation 2026-07-10)
opened: 2026-07-07
owner: project-manager (curates)
source: v0.1.64 closure backlog return (FR5/ADR-4 tolerate-then-strip window — deprecation-expiry law)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/agents/reader.py#_raw_to_dto" }
    change: "strip the v0.1.64 rename's tolerate window: remove the silent legacy `tier:` frontmatter fallback in `_raw_to_dto` (the second read `band_raw = raw.get('tier')`), drop the `tier` key from the `_ALLOWED_FIELDS` allowlist, delete the deprecated module-level alias `MissingTierError = MissingDispatchBandError` and its `features/agents/__init__.py` re-export, and flip the reader fallback test from proving silent tolerance to proving the legacy key is now unknown (dropped with the standard unknown-field warning; band defaults to 3). Eligible for strip from 2026-08-01 — consumer workspaces need one re-projection window (`dadaia public install`) so stale `.claude/agents/*.md` projections carrying `tier:` are gone before the fallback dies."
---

# BACKLOG — Strip the legacy `tier:` reader fallback + `MissingTierError` alias

**Priority:** LOW. v0.1.64 renamed the numeric agent-frontmatter key `tier:` →
`dispatch_band:` across the 12 shipped bodies + parser/model/renderer/tests
(tolerate-then-strip per the v0.1.53 `agent_tier` precedent, SPEC §9 ADR-4). The tolerate
half is deliberate, bounded debt in `features/agents/reader.py`:

- `_raw_to_dto` reads `dispatch_band` first and falls back **silently** to the legacy
  `tier` key (source: `band_raw = raw.get('tier')` — silent so a consumer workspace's
  stale projection does not warn-spam);
- `_ALLOWED_FIELDS` carries BOTH keys for the window;
- the module-level alias `MissingTierError = MissingDispatchBandError` (+ the
  `features/agents/__init__.py` re-export of both names) keeps old imports working.

This item is the dated strip. **Expiry:** eligible from **2026-08-01** (deprecation-expiry
law — one consumer re-projection window; every `dadaia public install` since v0.1.64
projects `dispatch_band:` bodies). Strip = remove the fallback read, drop `tier` from the
allowlist (an unknown `tier:` then gets the standard unknown-field drop warning and the
band defaults to 3 with the missing-band warning), delete the alias + re-export, and
invert the AC-6 fallback test. The `dispatch_band`-preferred path, the contract test's
pinned model/effort map, and the registry `Tier` (model-cost axis — unrelated, keeps its
name) are untouched.
