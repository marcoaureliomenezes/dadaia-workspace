---
name: dadaia-workspace-spec-reviewer
description: "Use when: reviewing or refining dadaia-workspace specs before implementation or before declaring a refinement pass complete. Audits memory Markdown atomicity, ACTIVE.md, status canonicity, CLOSURE evidence triples, broken image references, and the 300-line PLAN policy. Loads canonical owner docs first, detects duplicated ownership, and records unresolved gaps in specs/backlog/candidates.md."
---

# dadaia-workspace-spec-reviewer

## Goal

Run a disciplined consistency review over the relevant spec set before implementation or
before declaring a refinement pass complete. Enforce the release lifecycle (SPEC → PLAN →
TASKS → CLOSURE) and the atomic memory contract.

## Review workflow

1. Load `<specs-dir>/constitution.md`.
2. Load atomic memory (Markdown): `memory/architecture.md`, `memory/product/catalog.json`
   when present, `memory/product/index.md`, and `memory/tech-stack.md`.
   Load feature atoms under `memory/product/` on demand.
3. Read `<specs-dir>/releases/ACTIVE.md` and resolve the active release id.
4. Load active release artifacts: `SPEC.md`, `PLAN.md`, `TASKS.md`, and `CLOSURE.md` if
   phase ∈ {CLOSURE, ARCHIVED}.
5. Load `specs/backlog/candidates.md`.
6. Load `report-specs-review.md` only if the operator explicitly asks for historical
   context.
7. Compare the spec set across these dimensions:
   - **Memory atomicity** — no `Changelog|History|Histórico|Versions?` sections; no
     narrative of past versions; product described as it is *now*. Applies to every
     Markdown atom under `memory/` and `memory/product/`.
   - **Product memory catalog** — `memory/product/` is a folder; `index.md` exists and
     links every production feature atom in daily-relevance order. `catalog.json`, when
     present, must match the Markdown frontmatter.
   - **Feature atom structure** — each `memory/product/<slug>.md` contains the required
     feature sections: `Propósito`, `Fluxo de uso`, `Trigger típico`, `Diferencial`,
     `Estado runtime tocado`, and `Dependências`. Missing any of these is a finding.
   - **Broken image references** — every image reference in any memory Markdown resolves
     to a real file under `specs/assets/…`.
   - **Mermaid syntax** — fenced Mermaid blocks must be syntactically readable by the
     target renderer.
   - **Status canonicity** — every SPEC/PLAN/TASKS uses `**Status:** Draft|Em revisão|Aprovado`
     exactly. No `[x] Approved`, `Accepted`, `Implementado`, `Completed`, `Source of Truth`.
   - **Phase consistency** — `ACTIVE.md` phase matches the artifacts that exist (e.g.
     phase = TASKS implies PLAN is Aprovado).
   - **PLAN ≤ 300 lines** — warning for releases created before 2026-05-17, error after.
   - **CLOSURE evidence triples** — every entry under `## Validations` has
     `{description, command, evidence}`; evidence is a commit SHA, a stdout snippet, or a
     report path.
   - **Drifts section** — `## Drifts` with `### <slug>` and `Description:` /
     `Resolution:` / `Memory updates:` fields.
   - **No closed release outside archive** — once a release has CLOSURE and is moved, it
     must live under `_archive/releases/<id>/` only.
   - **No live PLAN/TASKS outside releases** — except legacy `features/*/` during the
     migration window.
   - **`_archive/` not used as a gate** — no SPEC outside `_archive/` references an
     archived release as the source of authority.
   - **Traceability** — every approved requirement maps into PLAN strategy and at least
     one TASKS entry.
8. Report findings ordered by severity.
9. If unresolved issues remain, append to `specs/backlog/candidates.md` under `## Hotfixes pendentes`.

## Output rules

- Findings first.
- No implementation suggestions that bypass unresolved spec conflicts.
- Prefer owner-document fixes over derived-document patches.
- If no blocking issues remain, say so explicitly.
- For each finding cite the path + (when applicable) the HTML attribute or markdown
  marker that triggered it.
