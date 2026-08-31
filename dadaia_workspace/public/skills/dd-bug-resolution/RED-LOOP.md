# RED-LOOP.md — building the feedback loop (Phase 1)

Disclosed reference of [`SKILL.md`](SKILL.md) Phase 1. Adapted from the reference
corpus (`mattpocock/skills`, `engineering/diagnosing-bugs`). Spend disproportionate
effort here: with a tight loop the cause falls out; without one no amount of staring
at code will save you.

## Ways to construct one, in roughly this order

1. **Failing test** at whatever seam reaches the bug: unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server (registered via
   `dadaia server register`).
3. **CLI invocation** with a fixture input, diffing stdout against a known-good
   snapshot.
4. **Headless browser script** (Playwright) driving the UI, asserting on
   DOM/console/network.
5. **Replay a captured trace** — save a real request/payload/event log to disk;
   replay it through the code path in isolation.
6. **Throwaway harness** — a minimal subset of the system (one service, mocked deps)
   exercising the bug path with a single call; delete it in Phase 6.
7. **Property / fuzz loop** — for "sometimes wrong output", run many random inputs
   and look for the failure mode.
8. **Bisection harness** — bug appeared between two known states: automate "boot at
   state X, check" so `git bisect run` can drive it.
9. **Differential loop** — same input through old vs new version (or two configs),
   diff the outputs.
10. **HITL script** — last resort when a human must click; drive them with a
    structured script so the loop still captures output.

## Tighten the loop

Treat the loop as a product. Once you have *a* loop:

- Faster — cache setup, skip unrelated init, narrow the scope.
- Sharper — assert the specific symptom, never "didn't crash".
- Deterministic — pin time, seed RNG, isolate filesystem, freeze network.

A 30-second flaky loop is barely better than none; a 2-second deterministic one is
tight — a debugging superpower.

## Non-deterministic bugs

The goal is a **higher reproduction rate**, not a first clean repro: loop the trigger
100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug
is debuggable; 1% is not — raise the rate until it is.

## When you genuinely cannot build a loop

Stop and say so explicitly, listing what you tried. Ask the operator for: (a) access
to the reproducing environment, (b) a redacted captured artifact (HAR, log dump, core
dump, recording with timestamps), or (c) permission for temporary instrumentation.
Hypothesising without a loop is Phase 1's named failure — the gate holds.
