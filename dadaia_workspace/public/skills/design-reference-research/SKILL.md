---
name: design-reference-research
description: Approved design reference whitelist and citation protocol for design-specialist research across trusted UI, accessibility, and CSS documentation sources.
---

# Design Reference Research

Centralizes the approved reference whitelist and citation protocol for `design-specialist`.

---

## Purpose

`design-specialist` is authorised to search and fetch from a fixed set of trusted design sources. This skill defines that whitelist, the search strategy, and the citation format that must appear in every design report. Any source not on this list requires explicit operator approval before it may be fetched or cited.

---

## Approved sources (whitelist)

| Source | Domain / URL prefix | Use cases |
|---|---|---|
| Dribbble | `dribbble.com` | Visual direction, colour palettes, layout patterns |
| Mobbin | `mobbin.com` | Real-world mobile and web UI patterns |
| Figma Community | `figma.com/community` | Open component libraries and templates |
| Refactoring UI | `refactoringui.com` | Typography, spacing, and visual hierarchy principles |
| Apple Human Interface Guidelines | `developer.apple.com/design/human-interface-guidelines` | Native-feel patterns, accessibility expectations |
| Material Design 3 | `m3.material.io` | Token system, motion, component anatomy |
| W3C WCAG 2.1 | `www.w3.org/WAI/WCAG21/quickref` | Accessibility success criteria (minimum AA) |
| MDN Web Docs | `developer.mozilla.org` | CSS property reference, semantic HTML |

---

## Search protocol

Follow these steps when researching a design problem:

1. **Identify the design question.** State it precisely before searching. Example: "What spacing between a card title and body text reads cleanly at 360px?"

2. **Select the relevant whitelist source(s).** Match the question to the source most likely to answer it:
   - Visual style, palette, layout inspiration → Dribbble, Mobbin, Figma Community
   - Spacing, typography, hierarchy principles → Refactoring UI
   - Accessibility criteria → W3C WCAG 2.1
   - Token/component anatomy → Material Design 3, Apple HIG
   - CSS property behaviour → MDN

3. **Use `WebSearch` within the approved domain.** Constrain the search with `site:<domain>` when using `WebSearch`. Do not follow links that resolve outside the whitelisted domain.

4. **Use `WebFetch` to retrieve the specific page.** Read only the relevant section. Do not download binary or image content.

5. **Record the citation immediately.** See citation format below.

6. **Reject unapproved sources immediately.** If a search result surface from outside the whitelist appears relevant, do NOT fetch it. Record the URL as "rejected — not on whitelist" in the research notes and continue with approved alternatives.

---

## Citation format

Every reference used in a design report must appear in the `## References` section using this format:

```
- [Title of page or section](URL)
  Relevance: <one sentence explaining what this reference contributed to the design decision>
```

Example:

```
- [Color — Material Design 3](https://m3.material.io/styles/color/overview)
  Relevance: Used the tonal palette model to derive --color-brand-primary and its on-color pair for accessible contrast.

- [Using color — WCAG 2.1 Success Criterion 1.4.3](https://www.w3.org/WAI/WCAG21/quickref/#use-of-color)
  Relevance: Confirmed that contrast ratio 4.5:1 minimum applies to all body text; verified against proposed --color-text-primary on --color-bg-base.
```

A design report with zero citations in `## References` fails the `design-report-quality-gate` check.

---

## Rejecting unapproved sources

If a source outside the whitelist appears during research:

1. Do NOT fetch or cite it.
2. Add a note in the report's `## References` section:
   ```
   - [Rejected] <URL> — not on approved whitelist; operator approval required.
   ```
3. Continue with whitelist alternatives. If no whitelist source answers the design question, note it in `## Handoff notes` and ask `project-manager` to approve an additional source before the next design iteration.

---

## Guardrails

- Never generate or link to raster/image outputs. Research output is text and URLs only.
- Never cite a source that was not actually fetched and read during this session.
- Never exceed one citation per reference page — if multiple sections of the same page are relevant, cite the page once and quote the relevant section titles.
- If the operator requests a source outside the whitelist, acknowledge the request, note it in the report, but do not fetch until an explicit approval (updated whitelist) is received.
