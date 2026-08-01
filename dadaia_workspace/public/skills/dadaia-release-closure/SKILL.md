---
name: dadaia-release-closure
description: "Use when: closing a release that has all TASKS marked [x] DONE. Defines the CLOSURE.md template, the memory Markdown update protocol, the evidence-triple validation format, and the move-to-archive command. Only product-engineer invokes this skill, and only in the CLOSURE phase. (product-engineer also holds memory-write permission in the DEFINITION phase per constitution §13 — that authorization is separate from this closure skill.)"
applyTo: "specs/releases/*/CLOSURE.md"
---

# dadaia-release-closure

> **Not the lifecycle enforcement mechanism.** Ordered lifecycle execution (the closure
> sequence and its gates) is owned by the dadaia-workflows (`dadaia lifecycle`). This
> skill is reference / manual-operator guidance only.

## When to invoke

After every task in `specs/releases/<release-id>/TASKS.md` is marked `[x] DONE` and
implementation is verified. Set `specs/releases/ACTIVE.md` phase to `CLOSURE` **before**
writing CLOSURE.md or memory Markdown — gate v3 allows memory writes in the DEFINITION and CLOSURE phases (this skill operates in CLOSURE).

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

**Memory updates:** Which `specs/memory/*.md` files needed adjustment because of this
drift?

### <another-drift>

...

## Memory updates

Explicit list of memory files written during this CLOSURE phase. If a memory file was not
updated, state the reason here (e.g. "memory/tech-stack.md: no change — release did not
touch dependencies").

- `specs/memory/product/index.md` — <one-liner of what changed in the catalog>
- `specs/memory/product/<slug>.md` — <one-liner per feature page updated>
- `specs/memory/architecture.md` — <one-liner>
- `specs/memory/tech-stack.md` — <one-liner or "no change: reason">

### Writing a new memory atom

A shipped feature is recorded as an **atom** at `specs/memory/product/<area>/<slug>.md`.
**Prefer the generator** — `dadaia memory product add <slug> --specs-dir <specs-dir>` — then
edit the generated body. A malformed atom is rejected by `dadaia specs doctor` (frontmatter,
allowlisted headings, and the mandatory markdown heading are all validated), so if you write
the file by hand, copy this template verbatim and fill it:

```markdown
---
slug: <kebab-case-slug>
title: <Feature Title>
category: product
tldr: <one-line summary under 160 chars>
summary: <2-3 sentence description of the shipped capability>
tags:
  - <tag>
token_estimate: 0
last_updated: "<YYYY-MM-DD>"
release_origin: <release-id>
---

## Visão atômica

<what this feature does, grounded in the shipped behaviour>
```

An atom states what the product **is now** — never a changelog. History lives in
`_archive/` and `git log`.

## Dispositions

Disposition-sweep ledger (mandatory — see "Disposition sweep" below). One row per
backlog item and bug picked into (or superseded by) this release.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/<slug>.md` | bug | `Closed` | `<CLOSURE section \| commit sha>` |
| `specs/backlog/<slug>.md` | backlog | `DELIVERED — <release-id>` | `<CLOSURE section \| commit sha>` |
| ... | ... | ... | ... |

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

## Disposition sweep (mandatory)

Before archive, flip every backlog item and bug picked into (or superseded by) the
release to a terminal status token per the ADR-11 vocabulary, and record each flip as a
row in the CLOSURE `## Dispositions` table with an evidence pointer (CLOSURE section or
commit SHA). A release whose CLOSURE lacks the sweep is not closeable.

| Kind | Terminal tokens | Format |
|------|-----------------|--------|
| Bug (`specs/bugs/**`) | `Closed` | frontmatter `status: Closed`; add `superseded_by: <backlog-slug>` when a picked backlog item superseded the fix |
| Backlog (`specs/backlog/**`) | `DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`, `DEFERRED`, `REJECTED` | Status line, case-insensitive prefix match; suffix allowed, e.g. `DELIVERED — vX.Y.Z`, `SUPERSEDED — <slug>` |

Never-delete law (release-governance): a bug or backlog file is **never deleted** —
always marked with a terminal token and a reason. A bug is never silently dropped:
either it is fixed (`Closed`) or a superseding backlog item covers its acceptance
(`Closed` + `superseded_by: <slug>`). Stale or invalid items are dispositioned
`DEFERRED` or `REJECTED` with a reason, never removed.

`dadaia specs doctor` backstops the sweep: SPEC-DOC-031 WARNs on a backlog entry left
non-terminal (`OPEN`/`PICKED`/`CANDIDATE`) while referenced by an archived release;
SPEC-DOC-032 WARNs on a bug `status:` outside the {`Open`, `Closed`} canon.

## Memory Markdown update protocol

1. **Verify gate phase.** Confirm `specs/releases/ACTIVE.md` phase = `CLOSURE` (memory
   writes are also allowed in `DEFINITION`). Otherwise the gate will block writes to
   `specs/memory/*.md`.

2. **Do not author legacy HTML memory.** If legacy HTML memory exists, treat it as
   read-only migration input. New memory writes are Markdown atoms.

3. **Update Markdown atoms.** Apply the release's deltas to the corresponding
   `specs/memory/*.md` or `specs/memory/product/*.md` files. Memory describes the
   product **as it is now** — not what changed. The change history lives in this
   CLOSURE.md and the archived release dir.

4. **Diagrams.** Use fenced Mermaid blocks:
   ```mermaid
   flowchart LR
     A --> B
   </pre>
   ```
   For screenshots, place PNGs under `specs/assets/<scope>/<id>.png` and reference via
   `<img src="../assets/<scope>/<id>.png" alt="<text>">`.

5. **Forbidden in memory Markdown:**
   - `<h2>Changelog</h2>`, `<h2>History</h2>`, `<h2>Histórico</h2>`, `<h2>Versions</h2>`
   - `<section class="changelog">` and similar
   - Narrative of past versions ("we used to use X, now we use Y")

   If the operator asks for history, point to CLOSURE.md or `_archive/`.

6. **Validate** with `dadaia specs doctor` before moving to archive. Doctor checks
   atomicity, broken `<img>` references, and Mermaid script presence.

## Move-to-archive command

After CLOSURE.md is written, the disposition sweep is complete, memory is updated, and
`dadaia specs doctor` reports green:

```bash
git mv specs/releases/<release-id> specs/_archive/releases/<release-id>
# Edit specs/releases/ACTIVE.md to point at the next release or `release: none`
```

The git history preserves the release's evolution; archive is the human-browsable
snapshot.

## Out of scope for this skill

- Writing source code, tests, or pipelines (other agents).
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates via this skill happen in the CLOSURE phase only. (product-engineer
  may also write memory in the DEFINITION phase under a separate §13 authorization —
  that path is not this skill.) Memory edits by any other agent, or in any other phase,
  are gate-blocked.
- Re-opening an archived release. Once archived, a new release supersedes it.

## Segments (ADR-1/ADR-5)

When the active release carries a `segment:` in `ACTIVE.md` (schema v2), each segment closes independently: write `specs/releases/<release-id>/<segment>/CLOSURE.md` for that segment. Per ADR-3, qa-only gates an `alpha-N` (commit, no closure/ship), and the full trio + release CLOSURE + archive happen at the shipping `rc-N`. Flat releases are unchanged.
