---
name: response-guard-chip-presence-hardening
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.59 closure backlog return (W5 AC-9(e) sabotage finding — response-guard null-guards a missing memory chip)
intents:
  - subject: { kind: code, ref: "tests/unit/features/panel/test_index_dom_contract.py#test_memory_chip_present_with_populated_context" }
    change: "harden the panel response-guard e2e to ASSERT the presence of the first .memory-chip instead of null-guarding it. v0.1.59's AC-9(e) mutation sabotage (rename the live .memory-chip → .memory-chip-SABOTAGED) revealed that response-guard.spec.ts:76-77 does `const firstChip = await page.$('.memory-chip'); if (firstChip) { … }` — a null-guard that degrades gracefully, so the tour still passes (2 passed) even with the chip dropped. The dropped selector was caught only by the FR1 DOM-contract unit lock (test_index_dom_contract.py), which is the intended primary guardrail. Add a browser-level `expect(firstChip).not.toBeNull()` (or `await page.waitForSelector('.memory-chip')`) so the memory-chip click path is a real assertion, not an optional branch — defence-in-depth BEHIND the DOM contract. Keep the graceful-empty behaviour only if the Projects fixture may legitimately have zero contexts; otherwise require the chip."
---

# BACKLOG — Response-guard e2e: assert memory-chip presence

**Priority:** LOW (QA / defence-in-depth). Returned at v0.1.59 (R11) closure from the W5
AC-9(e) mutation-sanity finding.

The v0.1.59 panel-UX-overhaul release captured a NEW FR1 **DOM-contract unit lock**
(`tests/unit/features/panel/test_index_dom_contract.py`) as the primary dropped-selector
guardrail, golden-first. During W5's AC-9(e) sabotage — rename the live `.memory-chip`
(`index.py:234-238`) → `.memory-chip-SABOTAGED` — the DOM-contract lock FAILED correctly
(`test_memory_chip_present_with_populated_context`, exit 1), but the **browser-level**
`tests/e2e/panel/response-guard.spec.ts` did **not**: it **null-guards** the missing chip at
lines 76-77 —

```ts
const firstChip = await page.$('.memory-chip');
if (firstChip) {
  // Open chip in the panel (it navigates to /memory-view/...)
  await firstChip.click();
  …
}
```

— and degrades gracefully, so the 6-tab tour + chip click still reports **2 passed** even with
the chip dropped. That is exactly why the FR1 DOM-contract lock is the real dropped-selector
guardrail (recorded as a v0.1.59 CLOSURE drift). This item hardens the e2e as a **second,
browser-level guard behind the DOM contract**: assert the first `.memory-chip` is present
(`expect(firstChip).not.toBeNull()` / `waitForSelector('.memory-chip')`) so the memory-chip
navigation path is a genuine assertion rather than an optional `if`. The graceful-empty branch
should survive only if the Projects fixture can legitimately have zero contexts.

**Anchor:** `tests/unit/features/panel/test_index_dom_contract.py#test_memory_chip_present_with_populated_context`
(the primary DOM-contract guardrail this item adds browser-level defence-in-depth behind — the
registry derives Python symbols only, so the intent anchors at the paired unit lock). **File to
change:** `tests/e2e/panel/response-guard.spec.ts` (the `.memory-chip` null-guard, lines 76-77).
