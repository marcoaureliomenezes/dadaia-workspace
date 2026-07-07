---
name: design-system-authoring
description: >
  Use this skill when authoring or evolving a design system — design tokens,
  type/space/color scales, component specs, and the visual language a frontend
  implementation consumes. Carries the token-taxonomy, scale-construction,
  component-spec, and versioning protocol. Producer side of the token-fidelity
  contract; browser-frontend-implementation is the consumer. Shipped by the
  frontend-design plugin pack; owned by design-specialist.
---

# Skill: design-system-authoring

The design-system *authoring* protocol for the `frontend-design` pack. `design-specialist`
uses it to define the tokens, scales, and component specs that `frontend-engineer` implements.
This is the **producer** side of the token-fidelity contract: the consumer-side checklist
(how implementers stay faithful to what you author here) lives in the
`browser-frontend-implementation` skill — the two compose, they do not overlap. Reach for
this skill at the start of every design-system or component-spec task.

## When to use

- Defining or extending design tokens (colour, spacing, typography, radius, elevation, motion).
- Constructing or revising the type/space/color scales for a product surface.
- Authoring a component spec (anatomy, states, variants, accessibility direction).
- Closing a token gap returned by an implementer ("this value has no token").

## 1. Token taxonomy — name by role, not by value

| Layer | Example | Rule |
|---|---|---|
| Primitive | `blue-500`, `space-4` | Raw values on a documented scale; never referenced directly by components. |
| Semantic | `color-action-primary`, `space-inset-md` | Role-named aliases of primitives; the ONLY layer implementations consume. |
| Component | `button-padding-x` | Optional; alias a semantic token, never a raw value. |

- A token's name states its **role**; its value can change without renaming (rebrand-safe).
- Every semantic token documents where it applies and its state variants (hover/focus/
  active/disabled) when interactive.
- Tokens ship in one canonical machine-readable file per repo (e.g. `*.tokens.json`);
  prose docs derive from it, never the reverse.

## 2. Scale construction

| Scale | Rule |
|---|---|
| Space | One geometric or fixed-step scale; every gap/inset/stack value comes from it. No off-scale one-offs. |
| Type | Paired size + line-height + weight steps; name steps by role (`body`, `heading-2`), not px. |
| Color | Each hue as a graded ramp; semantic tokens pick ramp steps that meet WCAG AA in their intended pairing. |
| Radius / elevation | Small enumerated sets (3–5 steps); consistency beats variety. |
| Motion | Named duration/easing pairs; every animated pattern maps to one and defines its `prefers-reduced-motion` fallback. |

A request for a value between steps is a scale-design question, not a one-off exception —
either the scale grows deliberately or the design snaps to an existing step.

## 3. Component specs

Every component spec answers, in order:

1. **Anatomy** — the named parts and which tokens each consumes.
2. **States** — default/hover/focus/active/disabled + loading/empty/error where applicable;
   every state's token deltas enumerated.
3. **Variants + sizes** — the allowed set, each mapped to tokens; no free-form variants.
4. **Behaviour** — keyboard interaction, focus handling, and motion (with reduced-motion
   fallback).
5. **Accessibility direction** — contrast pairings verified AA, target sizes, required
   semantics/labels. Call out any pattern that cannot meet AA instead of shipping it.
6. **Responsive rules** — how the component adapts across the documented breakpoints.

A spec an implementer must guess about is an unfinished spec — ambiguity returns to you via
PM; resolve it in the spec, never in a side channel.

## 4. Evolution and versioning

- **Additive first:** new tokens/steps extend the system; renames and removals are breaking
  changes that ship with a migration note listing every affected token.
- **Gap protocol:** when `browser-frontend-implementation`'s token-fidelity rule surfaces a
  missing token, either mint the semantic token (correct scale step, documented role) or
  redirect the design to an existing one. Never let the implementer invent a value.
- **Single source of truth:** one canonical token file per repo; a second competing source is
  drift by construction.

## Guardrails

| Rule | Detail |
|---|---|
| Producer, not implementer | You author tokens/scales/specs; markup, styles, and components belong to `frontend-engineer`. |
| Consumer contract | The implementation-side fidelity checklist lives in `browser-frontend-implementation` — reference it, never restate it. |
| Accessibility floor | No token pairing or component spec ships below WCAG AA. |
| No invented product intent | Product scope belongs to `product-engineer`; design serves the intent. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the task. |
