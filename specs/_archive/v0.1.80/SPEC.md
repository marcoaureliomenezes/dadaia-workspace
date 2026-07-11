# SPEC — Release v0.1.80 — LOW-debt cleanup & resolution-rung allowlist

**Status:** Aprovado
**Source:** the two open LOW bugs (`perf-hygiene-scan-rss-ceiling-flaky-in-sandbox`,
`handoff-emitter-example-omits-required-artifact`) + backlog
`20260711-context-name-allowlist-at-resolution-rungs` (P4, v0.1.77 security-review
INFO). Numbering note: the date-gated deprecation strips (formerly planned as
v0.1.80) renumber to **v0.1.81**, keeping their ship-on/after-2026-08-01 constraint —
recorded in `specs/backlog/candidates.md`.

## FRs

- **FR1 (bug: RSS-ceiling perf flake).** Root-cause fix, no workaround: the perf test
  asserts an ABSOLUTE `rss_delta_bytes` ceiling that bakes in a host/sandbox baseline
  assumption (interpreter baseline RSS can exceed the assumed headroom, ~500MB observed
  vs 96MB ceiling). Rework the measurement to what the test actually protects — the
  hygiene scan must not read unbounded file content — using an environment-independent
  signal (e.g. tracemalloc-based allocation delta of the scan itself, or bytes-read
  accounting), keeping a genuine regression detector. The test must pass
  deterministically on this sandbox AND on CI runners without weakening the invariant
  it pins.
- **FR2 (bug: handoff-emitter example).** The handoff-emitter skill's default
  handoff-only example omits the `artifact` object the validator requires — fix the
  public skill source so the example validates; add/extend the pinning test if the
  skill's examples are test-covered; propagate via `public stage/install/doctor`.
- **FR3 (backlog: allowlist at resolution rungs).** Apply the existing
  `[A-Za-z0-9_-]+` context-name allowlist to the `explicit` and `DADAIA_CONTEXT` rungs
  of `resolve_context_for_cli`, rejecting traversal-shaped names with an actionable
  message before any path join. Executed-path unit cases: traversal-shaped
  explicit/env names rejected; valid names unchanged; the seam contract tests stay
  green.

## Acceptance

- Both LOW bugs resolved with evidence at closure; backlog entry delivered.
- Full suite green WITHOUT deselecting the perf test; mypy --strict; doctors;
  per-sha security APPROVE.
