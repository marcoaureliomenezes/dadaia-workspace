# specs/releases/ — Release Rules

Scope: this file governs only `specs/releases/`. Replaces the retired `releases/README.md` (v6 canon, FR1).

This directory contains all release directories for this Spec Context Project.

## 1. Structure

```
releases/
  AGENTS.md                  — this file
  <release-id>/               — bare SemVer (e.g. `0.6.0`), the current axis
    SPEC.md                  — release specification (Status: Draft → Aprovado)
    PLAN.md                  — implementation plan (added after SPEC is approved)
    TASKS.md                 — task checklist with [ ]/[-]/[x] markers
    RELEASE.json              — ONE mutable state document: phase/rc/defined/
                                implemented/shipped/audited + an append-only `log`
                                array (v0.5.x FR — the canonical release+phase record
                                and the closure narrative's home)
    verdicts/                — required-check evidence handoffs, deleted once consumed
  _ideas/<release-id>/        — pre-approval drafts; MUTATING, never a trust root
  _archive/releases_histo.jsonl — one summary record per archived release (no
                                per-release directory survives archiving)
```

## 2. Authoring rules

- Each live release directory is named with a bare SemVer id (`^\d+\.\d+\.\d+$`, e.g. `0.6.0`) — no `v`-prefixed id is minted.
- A legacy `v`-prefixed id resolves only in `_archive/releases_histo.jsonl` (read-only lookup) — no archived directory exists.
- Release directories are created with `dadaia release new <id>` — never manually, to keep canonical SPEC.md frontmatter.
- SDD lifecycle order: `SPEC.md` (Draft) -> operator approval -> `PLAN.md` -> `TASKS.md` -> implementation -> closure.
- Closure: memory update, closure narrative in `RELEASE.json`'s `log`, disposition sweep, artifact GC, archive.
- No separate `CLOSURE.md` — full arc: `dd-release-implement`'s `RC-FLOW.md`.
- Only one release may be in IMPLEMENTATION phase at a time.

## 3. The active release and its phase (RELEASE.json, D3/D7/D11)

- Canonical record: `RELEASE.json`. The active release's phase is its `phase` field — read directly, no fold.
- Retires the `RELEASE.jsonl` event stream (SPEC FR4-successor).
- Who sets which milestone, and the exact shape per field: `dd-release-implement`'s `RELEASE-EVENTS.md`.
- No dual-write, no mirror file (v0.5.0 FR4/T-050-21A, A4.1).
- The SDD gate resolves the active release directly: the ONE non-archived, non-`_ideas` directory with a `RELEASE.json`.
- When no such directory exists, there is no active release — honest absence, no placeholder file.

## 4. `_ideas/` and `_archive/`

- `_ideas/<release-id>/` holds a pre-approval Draft (SPEC, sometimes PLAN/TASKS) before the release opens.
- It stays MUTATING and is never an evidence root for any required check; carries no `RELEASE.json`.
- Its own scoped rule: `releases/_ideas/AGENTS.md`.
- `_archive/releases_histo.jsonl` is the ADDITIVE, append-only landing zone for a closed release.
- One summary record per release, appended at archive time; the release directory itself is deleted, never `git mv`'d.
- History survives in git and this record, never a second on-disk copy.
