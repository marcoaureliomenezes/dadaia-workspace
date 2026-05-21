# UX/UI Review

Structured review of screenshots or existing UI against design token spec and UX principles, for `design-specialist`.

---

## Purpose

This skill provides a repeatable, structured review protocol that `design-specialist` follows when evaluating a screenshot or existing UI surface. It produces a findings table — not code, not images — that informs the design report and, transitively, the handoff to `frontend-engineer`. Applying this skill consistently ensures that every design review covers the same ground and that no review is blocked waiting for unstructured heuristics.

---

## Protocol

Apply the following steps in order when reviewing a screenshot or live UI surface.

### Step 1 — Token audit

For each visual element visible in the screenshot:

- Identify what design token the element should use (colour, spacing, radius, shadow, typography).
- Determine whether the implemented value matches a named token from the `frontend-design` skill token vocabulary.
- Flag any element where the implemented value is a raw hex, arbitrary px, or unnamed value.

Record in the findings table: `Element`, `Expected token`, `Actual value`, `Match (yes/no)`.

### Step 2 — Spacing audit

- Identify the spacing scale in use.
- Confirm that margins, paddings, and gaps resolve to multiples of the 4px base unit (`--space-N` tokens).
- Flag any spacing that is not on the 4px grid (e.g. 14px, 22px, 7px).

Add findings to the findings table.

### Step 3 — Typography audit

- Identify font sizes in use. Confirm each maps to a `--font-size-<step>` token.
- Identify font weights. Confirm each maps to a `--font-weight-<role>` token.
- Identify line heights. Confirm each maps to a `--line-height-<role>` token.
- Flag any typography value that cannot be traced to a named token.

Add findings to the findings table.

### Step 4 — A11y check

Evaluate the following for each interactive or content region visible:

| Check | Pass condition |
|---|---|
| Text contrast | >= 4.5:1 for normal text; >= 3:1 for large text |
| UI component contrast | >= 3:1 (buttons, inputs, icons) |
| Focus indicator | Visible; identifiable in the screenshot |
| Touch targets | Interactive elements appear >= 44px in both dimensions |
| Text size | No text visually smaller than ~12px |
| Information density | One clear primary action visible per view |

If the screenshot does not provide enough information to evaluate a check (e.g., contrast cannot be measured from a compressed image), record the check as "Unable to evaluate — needs measurement" and flag it for verification during implementation.

### Step 5 — Hierarchy assessment

Assess the visual hierarchy of the screen:

- Is there a clear primary heading or focal point?
- Does the content hierarchy map to the typography scale (largest = most important)?
- Are secondary and tertiary elements visually subordinate?
- Is whitespace used to group related elements?

Record one sentence per observation.

### Step 6 — Emit findings as structured text

After completing steps 1–5, produce a findings table with these columns:

| Element | Issue | Severity | Recommendation |
|---|---|---|---|
| `<element description>` | `<what is wrong>` | `low` / `medium` / `high` | `<what to change, using token names>` |

Severity definitions:

| Severity | Meaning |
|---|---|
| `high` | Blocks implementation or fails WCAG AA — must be fixed before handoff |
| `medium` | Significant UX or token deviation — should be fixed in this iteration |
| `low` | Minor improvement — may be deferred to a polish pass |

---

## Output format

The UX/UI review output is a markdown findings table embedded in the design report's `## Visual hierarchy findings` and `## A11y findings` sections. It is always structured text — never an image, never a patch, never a code snippet.

Example:

```markdown
| Element | Issue | Severity | Recommendation |
|---|---|---|---|
| Card title | Font size is 15px (not on scale) | medium | Use `--font-size-base` (16px) |
| Primary button | Background is #2563EB (raw hex) | high | Use `--color-brand-primary` |
| Input border | Contrast 2.8:1 on white background | high | Increase to meet 3:1 minimum; use `--color-neutral-600` |
| Section padding | 22px (not on 4px grid) | medium | Use `--space-6` (24px) |
```

---

## Guardrails

- No HTML, CSS, or JavaScript generation. This skill produces text findings only.
- No raster output. Do not generate, link to, or embed images or screenshots.
- Do not modify the source file being reviewed. This is a read-only review.
- Do not run Bash or Edit tools during the review. All steps are analytical and text-based.
- Do not report a contrast ratio as passing without a concrete measurement or cite "visually appears sufficient" as evidence. If in doubt, record as "Unable to evaluate — needs measurement".
- Do not propose implementation details (no code snippets, no DOM structure). Recommendations are token-level and intent-level only; `frontend-engineer` owns the implementation.
