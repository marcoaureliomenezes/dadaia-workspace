---
name: frontend-design
description: Canonical frontend design vocabulary for design-specialist, including workspace surfaces, token naming, typography, spacing, states, and handoff conventions.
---

# Frontend Design

Defines the workspace UI surfaces, design token naming conventions, typography scale, spacing system, and component handoff conventions for `design-specialist`.

---

## Purpose

This skill gives `design-specialist` a stable vocabulary for authoring design specs that `frontend-engineer` can implement without ambiguity. Every token name, spacing unit, and handoff field defined here is the canonical form; if `frontend-engineer` sees a different name in a design report, they must flag it as a discrepancy.

---

## Workspace surfaces

| Surface ID | Description | Primary concern |
|---|---|---|
| `portfolio` | Personal portfolio site | Visual polish, typography, motion |
| `dadaia-bots` | Bot management dashboard | Clarity, information density, a11y |
| `dadaia-workspace-panel` | Workspace agent/workflow panel | Functional UI, data tables, navigation |

---

## Design token naming conventions

Token names use the pattern `--<category>-<variant>[-<modifier>]`. All tokens are named; raw hex or px values are forbidden in design reports.

### Colour tokens

| Category | Pattern | Example |
|---|---|---|
| Brand | `--color-brand-<role>` | `--color-brand-primary`, `--color-brand-secondary` |
| Neutral | `--color-neutral-<step>` | `--color-neutral-100` through `--color-neutral-900` |
| Semantic | `--color-<intent>-<state>` | `--color-success-default`, `--color-error-hover` |
| Background | `--color-bg-<layer>` | `--color-bg-base`, `--color-bg-elevated` |
| Text | `--color-text-<role>` | `--color-text-primary`, `--color-text-muted` |

### Spacing tokens

Base unit: 4px. Scale: `--space-<n>` where `n * 4px = value`.

| Token | Value |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-12` | 48px |
| `--space-16` | 64px |

### Typography tokens

| Token | Meaning |
|---|---|
| `--font-family-sans` | Primary sans-serif family |
| `--font-family-mono` | Monospace family |
| `--font-size-<step>` | `xs` / `sm` / `base` / `lg` / `xl` / `2xl` / `3xl` / `4xl` |
| `--font-weight-<role>` | `regular` (400) / `medium` (500) / `semibold` (600) / `bold` (700) |
| `--line-height-<role>` | `tight` (1.25) / `normal` (1.5) / `relaxed` (1.75) |
| `--letter-spacing-<role>` | `tight` / `normal` / `wide` |

### Radius and shadow tokens

| Token | Meaning |
|---|---|
| `--radius-<size>` | `sm` / `md` / `lg` / `full` |
| `--shadow-<level>` | `sm` / `md` / `lg` / `none` |

### Motion tokens

| Token | Meaning |
|---|---|
| `--duration-<speed>` | `fast` (100ms) / `normal` (200ms) / `slow` (400ms) |
| `--easing-<curve>` | `standard` / `decelerate` / `accelerate` |

### Breakpoints (informational — not CSS tokens)

| Name | Value |
|---|---|
| mobile | 360px |
| tablet | 768px |
| desktop | 1280px |

---

## Protocol

When `design-specialist` authors a design spec, this skill is the reference for every token name and layout convention. Follow these steps in order:

1. **Identify the surface** from the dispatch input. Map it to the surface table above.
2. **Audit existing tokens** via `Grep` in the frontend repo for `--color-`, `--space-`, `--font-` to find which tokens already exist. Do not introduce a new token if an existing one fits.
3. **Spec new tokens** using the naming patterns above. List each new token with its intended value in the design report's `## Design specification` section.
4. **Use the ASCII sketch format** for layout recommendations:

```
+-------------------------------+
| --color-bg-elevated           |
|  [Logo]     [Nav links]  [CTA]|
+-------------------------------+
|  Hero text: --font-size-4xl   |
|  Subtext:   --font-size-lg    |
+-------------------------------+
```

   Each sketch must label at minimum: outer background token, text-size token, and spacing token between major regions.

5. **Write the handoff section** using the component handoff conventions below.

---

## Component handoff conventions

The `## Handoff notes` section of every design report must list, for each new or changed component:

| Field | Required content |
|---|---|
| Component name | `PascalCase` identifier |
| Props | Explicit prop names and types (text, not TypeScript) |
| States | normal / hover / focus / disabled / loading / error |
| Token list | Every token the component consumes |
| A11y requirements | ARIA role, label strategy, keyboard interaction, contrast minimum |
| Edge cases | Empty state, overflow, very long strings, RTL if applicable |

---

## How tokens flow to frontend-engineer

`design-specialist` emits a design report (HTML) to `.dadaia/reports/<ctx>/design-specialist/<ts>-design.html`.

`frontend-engineer` reads the `## Design specification` section to extract the token table, then maps each named token to a CSS custom property or Tailwind config entry. No raw hex or arbitrary px values may appear in the implementation — only tokens from this vocab.

---

## Guardrails

- `design-specialist` NEVER writes HTML, CSS, JS, TS, or TSX. Design output is always a design report or textual spec.
- `design-specialist` NEVER generates raster images. Sketches are ASCII only.
- `design-specialist` NEVER invokes Bash, Edit, or Playwright tools.
- If a token name is needed but does not fit the naming conventions above, `design-specialist` proposes a new convention in the design report and flags it for operator approval before `frontend-engineer` implements it.
- A design report that contains raw hex colours or arbitrary pixel values fails the `design-report-quality-gate` check.
