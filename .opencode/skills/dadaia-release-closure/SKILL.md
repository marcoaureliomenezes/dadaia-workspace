---
name: dadaia-release-closure
description: "Use when: closing a release that has all TASKS marked [x] DONE. Defines the CLOSURE.md template, the memory HTML update protocol, the evidence-triple validation format, and the move-to-archive command. Only product-engineer in CLOSURE phase invokes this skill — gate enforces that memory writes only happen here."
applyTo: "specs/releases/*/CLOSURE.md"
---

# dadaia-release-closure

## When to invoke

After every task in `specs/releases/<release-id>/TASKS.md` is marked `[x] DONE` and
implementation is verified. Set `specs/releases/ACTIVE.md` phase to `CLOSURE` **before**
writing CLOSURE.md or memory HTML — gate v3 only allows memory writes in this phase.

## CLOSURE.md template

```markdown
# Closure: Release — <release-id>

> **Status:** Aprovado
> **Release ID:** <release-id>
> **Owner:** product-engineer
> **Closed:** <YYYY-MM-DD>

## Summary

<1–3 paragraphs describing what shipped, from the product owner's perspective. No
implementation detail.>

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-X.Y | <one-liner> | `<sha>` |
| ...   | ...         | ...    |

## Validations

Each validation is a triple: description, command, evidence. Evidence MUST be one of:
commit SHA, stdout snippet (in fenced code), or path to a report HTML under
`.dadaia/reports/<context>/`.

| Description | Command | Evidence |
|-------------|---------|----------|
| <what was validated> | `<command>` | `<sha\|snippet\|path>` |
| ...                  | ...         | ...                  |

## Drifts

For every place where reality diverged from PLAN.md during implementation, document it:

### <slug-of-drift>

**Description:** What happened? Why did the plan need to bend?

**Resolution:** How was it resolved? What was the trade-off?

**Memory updates:** Which `specs/memory/*.html` files needed adjustment because of this
drift?

### <another-drift>

...

## Memory updates

Explicit list of memory files written during this CLOSURE phase. If a memory file was not
updated, state the reason here (e.g. "memory/tech-stack.html: no change — release did not
touch dependencies").

- `specs/memory/product/index.html` — <one-liner of what changed in the catalog>
- `specs/memory/product/<slug>.html` — <one-liner per feature page updated>
- `specs/memory/architecture.html` — <one-liner>
- `specs/memory/tech-stack.html` — <one-liner or "no change: reason">

## Backlog returns

Items discovered during implementation that did not fit this release's scope. Each goes
to either `specs/backlog/ideas.md` (informal) or `specs/backlog/candidates.md` (formal
candidate for next planning round).

- `backlog/candidates.md` ← <candidate>
- `backlog/ideas.md` ← <idea>

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/<release-id>/` via
`git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.

(Alternative: `KEEP` — leave the release in `specs/releases/` only if explicitly justified
by the operator. Should be rare.)
```

## Memory HTML update protocol

1. **Verify gate phase.** Confirm `specs/releases/ACTIVE.md` phase = `CLOSURE`. Otherwise
   the gate will block writes to `specs/memory/*.html`.

2. **Archive legacy memory.** If markdown `specs/memory/*.md` still exists from a previous
   model, move to `specs/_archive/legacy-memory/<UTC-timestamp>/` (one-time, then never
   again). Markdown is not accepted in `specs/memory/`.

3. **Render from canonical templates.** Source templates live in
   `dadaia_workspace/public/templates/`:
   - `memory-product.html.j2`
   - `memory-architecture.html.j2`
   - `memory-tech-stack.html.j2`

   Render each template into the corresponding `specs/memory/<name>.html` with the
   release's deltas applied. Memory describes the product **as it is now** — not what
   changed. The change history lives in this CLOSURE.md and the archived release dir.

4. **Diagrams.** Use Mermaid embedded inside the HTML:
   ```html
   <pre class="mermaid">
   flowchart LR
     A --> B
   </pre>
   ```
   For screenshots, place PNGs under `specs/assets/<scope>/<id>.png` and reference via
   `<img src="../assets/<scope>/<id>.png" alt="<text>">`.

5. **Forbidden in memory HTML:**
   - `<h2>Changelog</h2>`, `<h2>History</h2>`, `<h2>Histórico</h2>`, `<h2>Versions</h2>`
   - `<section class="changelog">` and similar
   - Narrative of past versions ("we used to use X, now we use Y")

   If the operator asks for history, point to CLOSURE.md or `_archive/`.

6. **Validate** with `dadaia specs doctor` before moving to archive. Doctor checks
   atomicity, broken `<img>` references, and Mermaid script presence.

## Move-to-archive command

After CLOSURE.md is written, memory is updated, and `dadaia specs doctor` reports green:

```bash
git mv specs/releases/<release-id> specs/_archive/releases/<release-id>
# Edit specs/releases/ACTIVE.md to point at the next release or `release: none`
```

The git history preserves the release's evolution; archive is the human-browsable
snapshot.

## Out of scope for this skill

- Writing source code, tests, or pipelines (other agents).
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Editing memory outside CLOSURE phase (gate-blocked).
- Re-opening an archived release. Once archived, a new release supersedes it.
