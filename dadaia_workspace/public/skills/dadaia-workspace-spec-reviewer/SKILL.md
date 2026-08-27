---
name: dadaia-workspace-spec-reviewer
description: "Use when: reviewing or refining dadaia-workspace specs before implementation or before declaring a refinement pass complete. Audits memory Markdown atomicity, the RELEASE.jsonl phase fold, status canonicity, the RELEASE.jsonl closure-note records, external image references, and the 300-line PLAN policy. Loads canonical owner docs first, detects duplicated ownership, and routes unresolved gaps to the PM's operator-gated intake report."
---

# dadaia-workspace-spec-reviewer

## Goal

Run a disciplined consistency review over the relevant spec set before implementation or
before declaring a refinement pass complete. Enforce the release lifecycle (SPEC → PLAN →
TASKS → CLOSURE) and the atomic memory contract.

## Review workflow

1. Load `<specs-dir>/constitution.md`.
2. Load atomic memory (Markdown): `memory/ARCHITECTURE.md`, `memory/product/catalog.json`
   when present, `memory/product/index.md`, and `memory/TECHSTACK.md`.
   Load feature atoms under `memory/product/` on demand.
3. Fold `<specs-dir>/releases/<release-id>/RELEASE.jsonl` (last `phase` record wins)
   and resolve the active release id (`ACTIVE.md` retired at T-050-21A — the SDD gate
   reads this same fold directly, no mirror to cross-check).
4. Load active release artifacts: `SPEC.md`, `PLAN.md`, `TASKS.md`, and, if phase ∈
   {CLOSURE, ARCHIVED}, the `RELEASE.jsonl` closure `note` records (`CLOSURE.md`
   retired T-050-21 — until T-050-25A, a minimal freeform `CLOSURE.md` may still exist
   for SPEC-DOC-006 compatibility only).
5. Load `specs/backlog/BACKLOG.md` (`ACTIVE` section) if present — the single-source
   backlog (`dd-backlog-definition`).
6. Compare the spec set across these dimensions:
   - **Memory atomicity** — no `Changelog|History|Histórico|Versions?` sections; no
     narrative of past versions; product described as it is *now*. Applies to every
     Markdown atom under `memory/` and `memory/product/`.
   - **Product memory catalog** — `memory/product/` is a folder; `index.md` exists and
     links every production feature atom in daily-relevance order. `catalog.json`, when
     present, must match the Markdown frontmatter.
   - **Feature atom structure** — each `memory/product/<area>/<slug>.md` contains the required
     feature sections: `Purpose`, `Usage flow`, `Typical trigger`, `Differentiator`,
     `Runtime state touched`, and `Dependencies` (English canon, `.heading-allowlist`).
     Missing any of these is a finding.
   - **No external image references** — the v6 canon root carries no `assets/` member;
     a diagram belongs in-doc as a fenced Mermaid block (`ARCHITECTURE.md`'s own
     `## Architecture Diagrams` section is the pattern), never an `<img>` reference to
     an external file.
   - **Mermaid syntax** — fenced Mermaid blocks must be syntactically readable by the
     target renderer.
   - **Status canonicity** — every SPEC/PLAN/TASKS uses `**Status:** Draft|Em revisão|Aprovado`
     exactly. No `[x] Approved`, `Accepted`, `Implementado`, `Completed`, `Source of Truth`.
   - **Phase consistency** — the RELEASE.jsonl fold's phase matches the artifacts that
     exist (e.g. phase = TASKS implies PLAN is Aprovado).
   - **PLAN ≤ 300 lines** — warning for releases created before 2026-05-17, error after.
   - **Closure narrative completeness** — every `RELEASE.jsonl` `note` record class
     `dd-release-implement`'s `RELEASE-EVENTS.md` names is present once the release
     reaches CLOSURE (summary, size accounting, drifts, artifact-GC, test
     dispositions); a `closure-summary`/`closure-drift`/etc. `note` missing at CLOSURE
     phase is a finding, dispositions/record-only-observations/intake-candidates are
     verified against their native homes (ledgers, reviewer handoffs, PM intake) per
     that file's conversion table, never a restated CLOSURE table.
   - **No closed release outside archive** — once a release ships its `phase: ARCHIVED`
     record and is moved, it must live under `_archive/releases/<id>/` only.
   - **No live PLAN/TASKS outside releases** — except legacy `features/*/` during the
     migration window.
   - **`_archive/` not used as a gate** — no SPEC outside `_archive/` references an
     archived release as the source of authority.
   - **Traceability** — every approved requirement maps into PLAN strategy and at least
     one TASKS entry.
7. Report findings ordered by severity.
8. If unresolved issues remain, list them for the PM's operator-facing intake report —
   never append them to the backlog directly (`dd-backlog-definition` §5).

## Output rules

- Findings first.
- No implementation suggestions that bypass unresolved spec conflicts.
- Prefer owner-document fixes over derived-document patches.
- If no blocking issues remain, say so explicitly.
- For each finding cite the path + (when applicable) the HTML attribute or markdown
  marker that triggered it.

## Segments (ADR-1/ADR-5)

Segmented releases (ADR-1/ADR-5) place SPEC/PLAN/TASKS under `releases/<release-id>/<segment>/` (`alpha-N`/`rc-N`) — `RELEASE.jsonl` stays one file per release, its `phase`/`note` records carrying `data.segment`. When reviewing, resolve the active segment from the fold's `data.segment` and audit that segment's artifacts; flat releases keep `releases/<release-id>/`.
