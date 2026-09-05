# HTML Report Format

Disclosed reference of [`SKILL.md`](SKILL.md), report mode only (operator asked, or
the next hop is human). Adapted from the reference corpus (`mattpocock/skills`,
`engineering/improve-codebase-architecture`), re-grounded on this workspace's report
law: a report is **self-contained** — inline `<style>`, inline SVG, zero external
scripts or stylesheets (`reports-AGENTS.md`; external assets only when committed
beside the report). Split any report over 30 KB behind an `index.html`
(`DADAIA.md` §5.4).

## Scaffold

One HTML file in the repo's reports home (`DADAIA.md` §5.2), everything inline:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review — {{context name}}</title>
    <style>
      /* One small hand-written layer. System font stack, one accent color,
         generous whitespace. Keep it under ~80 lines. */
      body { font: 15px/1.5 system-ui, sans-serif; margin: 0; background: #fafaf9; color: #0f172a; }
      main { max-width: 60rem; margin: 0 auto; padding: 3rem 1.5rem; }
      article { background: #fff; border: 1px solid #e7e5e4; border-radius: 8px; padding: 1.5rem; margin: 2rem 0; }
      .files { font-family: ui-monospace, monospace; font-size: 0.85rem; color: #57534e; }
      .badge { display: inline-block; border-radius: 4px; padding: 0.1rem 0.5rem; font-size: 0.8rem; font-weight: 600; }
      .strong { background: #d1fae5; color: #065f46; }
      .explore { background: #fef3c7; color: #92400e; }
      .spec { background: #e7e5e4; color: #44403c; }
      .diagrams { display: flex; gap: 1rem; flex-wrap: wrap; }
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
    </style>
  </head>
  <body>
    <main>
      <header>…</header>
      <section id="candidates">…</section>
      <section id="top-recommendation">…</section>
    </main>
  </body>
</html>
```

## Header

Context name, date, and a compact legend: solid box = module, dashed line = seam,
red arrow = leakage, thick dark box = deep module. No introduction paragraph —
straight into the candidates.

## Candidate card

The diagrams carry the weight. Prose is sparse, plain, and speaks the
`dd-codebase-design` vocabulary without ceremony. Each candidate is one `<article>`:

- **Title**: short, names the deepening (e.g. "Collapse the intake pipeline").
- **Badge row**: recommendation strength (`Strong` / `Worth exploring` /
  `Speculative`) plus the dependency-category tag.
- **Files**: monospaced list.
- **Before / After diagram**: the centrepiece — two columns, side by side.
- **Problem**: one sentence. What hurts.
- **Solution**: one sentence. What changes.
- **Wins**: bullets, ≤6 words each ("Tests hit one interface", "Delete 4 wrappers").
- **ADR callout** (if applicable): one line in an amber-tinted box.

No paragraphs of explanation — if the diagram needs a paragraph, redraw the diagram.

## Diagrams — hand-built inline SVG only

Draw every diagram as inline SVG (or bordered `<div>`s with absolutely-positioned
SVG arrows). No diagram library, no external script: the report renders identically
in the panel, a browser tab, or an offline copy, and carries no executable
dependency.

Patterns that work:

- **Call-flow / dependency graph**: boxes (`<rect>` + `<text>`) connected by
  `<line>`/`<path>` arrows; class `leak` colors a crossing edge red, class `seam`
  dashes a legitimate interface line.
- **Mass diagram (before/after)**: the "before" column as many small bordered
  boxes; the "after" column as ONE thick-bordered deep module with greyed-out
  internals — the visual weight IS the argument.
- **Sequence strip**: numbered arrows down a lane pair, "before: 6 round-trips;
  after: 1".

Vary the patterns between cards — a report where every diagram looks the same stops
being read.

## Top recommendation

End with one section: which candidate to tackle first and why, argued from the
cards, in the shared vocabulary. The handoff's `next_handoff` names the
`dd-grill-me` session as the next hop.
