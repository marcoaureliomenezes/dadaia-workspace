---
name: ux-ui-review
description: >
  Reference for design-specialist agent. WCAG 2.2 AA accessibility checklist,
  visual hierarchy heuristics, design-system conformance audit, reference-search
  whitelist (Dribbble, Mobbin, Figma Community, Refactoring UI, Apple HIG,
  Material 3), and design-spec output template.
applyTo: ".dadaia/reports/**"
---

# ux-ui-review — UX/UI Design Review Reference

## WCAG 2.2 AA Checklist

Score each criterion: PASS / FAIL / NA. Any FAIL on a criterion marked (AA) blocks
handoff to `frontend-engineer`. (AAA) criteria are advisory.

### Perceivable

| # | Criterion | Level | Signal to check |
|---|---|---|---|
| 1.1.1 | Non-text content has text alternative | AA | `<img alt="">` non-empty and descriptive; decorative images use `alt=""` + `role="presentation"` |
| 1.3.1 | Info and relationships conveyed in markup | AA | Headings in semantic order (h1 → h2 → h3); tables have `<th scope>`; lists use `<ul>`/`<ol>` |
| 1.3.3 | Sensory characteristics not sole instruction | AA | No "click the red button" without name/label |
| 1.3.4 | Orientation not locked | AA | Layout works in both portrait and landscape |
| 1.4.1 | Color not sole differentiator | AA | Error states use icon + text, not color alone |
| 1.4.3 | Text contrast ≥ 4.5:1 (normal) / 3:1 (large) | AA | Use browser DevTools or axe; large text ≥ 18pt or 14pt bold |
| 1.4.4 | Text resizes to 200% without content loss | AA | Zoom browser to 200%; no overflow or clipped text |
| 1.4.10 | Reflow at 320 CSS px width | AA | Horizontal scroll must not appear at 320px width |
| 1.4.11 | Non-text contrast ≥ 3:1 | AA | Button borders, focus indicators, input borders vs background |
| 1.4.12 | Text spacing overrides respected | AA | Apply: line-height 1.5, letter-spacing 0.12em, word-spacing 0.16em — no content lost |
| 1.4.13 | Content on hover/focus dismissible | AA | Tooltips / popovers closable without moving pointer |

### Operable

| # | Criterion | Level | Signal to check |
|---|---|---|---|
| 2.1.1 | All functionality keyboard accessible | AA | Tab through every interactive element; no keyboard trap |
| 2.1.2 | No keyboard trap | AA | Esc exits all modals/dialogs |
| 2.4.3 | Focus order logical | AA | Tab order matches visual reading order |
| 2.4.4 | Link purpose clear from context | AA | No bare "click here" links; `aria-label` on icon-only buttons |
| 2.4.7 | Focus visible | AA | `:focus-visible` style present and high-contrast (≥ 3:1 vs adjacent bg) |
| 2.4.11 | Focus not obscured (WCAG 2.2) | AA | Sticky headers/footers must not fully hide focused element |
| 2.5.3 | Label in name | AA | Button/link accessible name contains the visible text |
| 2.5.8 | Target size ≥ 24×24 CSS px (WCAG 2.2) | AA | Touch targets; inline links allowed if spacing ≥ 24px |

### Understandable

| # | Criterion | Level | Signal to check |
|---|---|---|---|
| 3.1.1 | Language of page declared | AA | `<html lang="pt-BR">` or `lang="en"` |
| 3.2.1 | No context change on focus | AA | Select/input focus does not submit or navigate |
| 3.3.1 | Error identification | AA | Error message identifies which field and describes the issue |
| 3.3.2 | Labels or instructions present | AA | All form fields have visible label or `aria-label` |

### Robust

| # | Criterion | Level | Signal to check |
|---|---|---|---|
| 4.1.2 | Name, role, value for all UI components | AA | Custom controls have `role`, `aria-label`, `aria-expanded` as appropriate |
| 4.1.3 | Status messages programmatically determinable | AA | Toast/alerts use `role="status"` or `aria-live="polite"` |

### Motion

| Check | Required |
|---|---|
| `prefers-reduced-motion` media query | All CSS transitions/animations gated behind `@media (prefers-reduced-motion: no-preference)` |
| Auto-playing animation ≤ 5 s or user-stoppable | Any animation > 5 s has a pause/stop control |

---

## Visual Hierarchy Heuristics

### Typographic Scale

Use a modular scale (ratio 1.25 or 1.333). Minimum recommended scale for web:

| Token name | Size | Use |
|---|---|---|
| `text-xs` | 12px | Labels, captions, legal |
| `text-sm` | 14px | Secondary body, metadata |
| `text-base` | 16px | Primary body copy |
| `text-lg` | 18px | Lead paragraphs |
| `text-xl` | 20px | Section subheadings |
| `text-2xl` | 24px | H3 |
| `text-3xl` | 30px | H2 |
| `text-4xl` | 36px | H1 |

Red flags: more than 6 distinct font sizes in a single view; font sizes not from
the defined scale; body copy smaller than 14px.

### Spacing Rhythm

Consistent spacing prevents visual noise. All spacing values should be multiples
of the base unit (4px or 8px). Check:
- Component internal padding uses 4px grid?
- Section gaps use 8px or 16px grid?
- No one-off values like `padding: 7px` or `margin: 13px`?

### Contrast and Emphasis

- One dominant element per section (primary CTA, hero heading).
- Secondary elements visually subordinate (reduced size, reduced contrast, or lighter weight).
- Decorative elements do not compete with content for attention.

### Proximity

Related elements are grouped closer together than unrelated elements. Check:
- Form label is closer to its input than to adjacent label.
- Card content grouped within card boundary; card margin separates from sibling cards.

### Alignment

- All text within a section shares a common left (or right) edge — no ragged alignment between adjacent elements.
- Icon + label pairs aligned on center axis.
- No "floating" elements that do not align with any other element in the layout.

---

## Design-System Conformance Audit

### Token Usage vs One-Off Values

```bash
# Find hard-coded hex colors in CSS/SCSS (should be token references)
grep -rn "#[0-9a-fA-F]\{3,6\}" src/ --include="*.css" --include="*.scss"

# Find hard-coded pixel sizes not from scale
grep -rn "[0-9]\+px" src/ --include="*.css" | grep -v "var(--"
```

Allowable exceptions: 1px borders, `0px`, `100%`, viewport units.

### Motion Adherence

Every animation must reference a duration and easing token:
```css
/* PASS */
transition: opacity var(--duration-fast) var(--ease-standard);

/* FAIL */
transition: opacity 150ms cubic-bezier(0.4, 0, 0.2, 1);
```

### Breakpoint Cascade

Declared breakpoints must be used consistently. Check:
- No magic-number media queries outside the declared breakpoint tokens.
- Mobile-first: base styles define mobile, `min-width` overrides for larger viewports.
- Content does not overflow or clip at any declared breakpoint.

---

## Reference-Search Whitelist

Use these sources only. Do not reference sources outside this whitelist without
explicit operator approval.

| Source | URL | When to Use |
|---|---|---|
| Dribbble | https://dribbble.com | Visual pattern inspiration; screenshot layout ideas |
| Mobbin | https://mobbin.com | Real-world mobile and web UX patterns; interaction flows |
| Figma Community | https://www.figma.com/community | Design system templates; component library references |
| Refactoring UI | https://www.refactoringui.com | Typography, spacing, and contrast principles; specific improvement tactics |
| Apple HIG | https://developer.apple.com/design/human-interface-guidelines/ | Platform conventions for iOS/macOS surfaces |
| Material 3 | https://m3.material.io | Google Design system tokens, motion specs, component states |

When referencing, always cite: source name + URL + section + what you are borrowing.

---

## Screenshot Annotation Template

When analyzing a screenshot, produce annotations in this format:

```
Screenshot: <path or URL>
Component: <name of component being reviewed>

Annotations:
[A1] <x,y region or element name> — <observation> — Severity: PASS/WARN/FAIL
[A2] <x,y region or element name> — <observation> — Severity: PASS/WARN/FAIL
...

Summary: N PASS, M WARN, P FAIL
```

Severity mapping for design annotations:
- FAIL: accessibility violation (WCAG AA breach) or design-system token violation.
- WARN: inconsistency or best-practice deviation that does not break WCAG.
- PASS: meets spec; document positive patterns explicitly.

---

## Output Template

Every UX/UI review report must include the following sections. Emit as HTML.

### Brief

```
Component / view under review: <name>
Review scope: <WCAG audit | hierarchy review | full design review>
Source: <PR, branch, Figma link, or screenshot path>
Date: <ISO 8601>
```

### Current State Evidence

List screenshots or code snippets that illustrate the current state. Never
include sensitive data. Reference by file path or URL.

### WCAG Findings

Table: Criterion | Level | Result | Evidence | Recommendation.
List only criteria that FAIL or have observations. PASS without issues need not
be listed unless the reviewer wants to call out good practice.

### Visual Hierarchy Assessment

For each heuristic area (typographic scale / spacing / contrast / proximity / alignment):
- Current state observation.
- Score: PASS / WARN / FAIL.
- Specific recommendation if WARN or FAIL.

### Design-System Conformance

Table: Token category | Compliant? | Violations found | Fix.

### References

For each design decision or recommendation, cite one or more sources from the
whitelist:
```
[R1] Refactoring UI — Chapter: "Not enough whitespace" — basis for spacing recommendation
[R2] Material 3 — Color system — contrast token rationale
```

### Design Spec

Deliver in this sub-section order:

1. **Typography** — proposed scale tokens, font weights, line-height values.
2. **Color** — proposed token assignments for each surface/text role.
3. **Spacing** — padding and margin values using grid tokens.
4. **Motion** — duration + easing tokens for each animated element.
5. **Breakpoints** — layout changes per breakpoint.
6. **Accessibility** — ARIA attributes, focus styles, alt text requirements.

### ASCII Sketches

For each component that requires a layout change, provide a simple ASCII sketch:

```
┌─────────────────────────┐
│  [Icon]  Label text      │  ← 44px min-height touch target
│                         │
└─────────────────────────┘
```

Keep sketches simple — they guide `frontend-engineer`, not replace Figma.

### Handoff to frontend-engineer

Summary of actionable items with priority:

| Priority | Item | Token/Value | File hint |
|---|---|---|---|
| MUST | Fix contrast on `btn-secondary` | `color: var(--text-on-muted)` | `components/Button.css` |
| SHOULD | Add `:focus-visible` style | `outline: 2px solid var(--focus-ring)` | `global.css` |
| NICE | Tighten card spacing | `padding: var(--space-4)` | `Card.css` |

---

## Anti-AI-Slop Principles

These principles prevent generic, pattern-matched design output.

1. **Evidence before prescription** — every recommendation must cite a specific
   observation in the current design (screenshot annotation or file:line).
   Generic "improve the typography" is not a finding.

2. **Token-first** — never prescribe raw values; prescribe token names. The
   concrete value is the design system's responsibility.

3. **One problem, one fix** — each finding maps to exactly one recommendation.
   Do not bundle multiple issues into a single item.

4. **No hallucinated references** — only cite sources from the whitelist and
   only cite sections you have actually read in this session.

5. **ASCII sketches for layout changes only** — do not produce ASCII art for
   changes that are purely cosmetic (color, spacing token swap). Sketches are
   for structural layout decisions only.

For additional guidance on avoiding generic AI output in design specs, cross-reference
the `frontend-design` plugin skill when available in the active context.
