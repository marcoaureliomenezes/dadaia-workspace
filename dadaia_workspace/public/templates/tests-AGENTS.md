# Test Rules — <project-name>

> Installed by dadaia. Replace every `<ANGLE-BRACKET>` placeholder below with this
> project's own values before relying on it — a placeholder left in place means that
> section is not yet calibrated.

These rules override general workspace guidance for everything under `tests/`.
Agents creating or editing tests must follow them. Full protocol: skill
`dadaia-test-stewardship`. Numbers below are this project's adjustable defaults.

## Intent Taxonomy

- Every test declares intent in its module docstring — `Intent: <KIND> — <AC id |
  bug-id | task-id>` — **never** as a pytest marker.
- CONTRACT (permanent, asserts an AC or a bug) / SENTINEL (permanent, the single
  integration test of one seam) / SCAFFOLD (temporary, expires at its task/release
  closure) / QUARANTINE (flaky, carries a registered bug id).
- An undeclared test is **SCAFFOLD** — the default is to die, not to stay.

## Architecture (size tiers)

- `tests/unit/**` (SMALL): pure or near-pure tests only. No real subprocess
  execution, server threads, network, sleeps, or real external services.
- `tests/contract/**` (SMALL): public API/CLI/schema/security contracts.
- `tests/integration/**` (MEDIUM): multi-component tests using a tmp filesystem
  or local service wiring.
- `tests/e2e/**` (LARGE): named end-to-end journeys only; every file names an
  owner in a comment or docstring.
- `tests/tmp/**`: SCAFFOLD only — excluded from default collection, deleted or
  promoted before closure.

## Admission filter

A new test enters the permanent suite only if it: compiles and runs; is
deterministic; adds real detection (covers previously-uncovered behavior or kills
a mutant no current test kills). Prohibited: change-detector tests (mirror the
implementation), tautologies (expected value re-derived from the code under
test), reflex-regenerated snapshots.

## Deletion criteria and the tombstone ban

Delete, with `file:line` evidence in the commit, a test that meets any of:

| Criterion | Evidence |
|---|---|
| Feature removed | link to the removal |
| Duplicate coverage exists | `file:line` of the equivalent test |
| Tautology / no-op | shows the assertion never consults the product |
| Reflex-regenerated snapshot, no review | diff history |
| Failure→defect ratio ≈ 0 | flake/failure history, zero real defects |
| Expired quarantine/skip, no plan | see Flake Policy below |

**Tombstone ban.** A test whose central assertion is the *absence* of something
removed (deleted feature now errors, module became a stub, directory/repo
removed, old migration gone) validates a historical event, not a live behavior.
It is SCAFFOLD of the release that removed the thing and dies at that release's
closure — the memory of the removal belongs to CLOSURE/changelog, never the
suite.

**Separation of powers.** The implementer never prunes to go green. Pruning is a
quality-steward verdict carrying this table's evidence; the implementer executes
the commit, quoting the verdict.

## Markers, cost and flake policy

- Layer markers are applied automatically by directory.
- Per-test timeout defaults by tier (adjustable): unit `<UNIT_TIMEOUT_S>`s /
  contract `<CONTRACT_TIMEOUT_S>`s / integration `<INTEGRATION_TIMEOUT_S>`s / e2e
  `<E2E_TIMEOUT_S>`s. A test needing more is mis-tiered — fix the tier, never the
  default.
- `flaky` and `quarantine` markers exist; `quarantine` without a registered bug
  id is refused at collection. Every gating selector excludes `quarantine`.
- LARGE cap (declared, reported as a warning until achievable): `<LARGE_CAP>` per
  module (abstract default 12–15).
- Wall-clock budget is frozen at `<WALL_CLOCK_BASELINE>` per job; raising it
  requires a justification recorded at closure.

## Good Test Standard

A test is allowed only if it can fail for a meaningful regression in current
product behavior, public contract, security boundary, data integrity, or a real
user journey. If it mainly records implementation history, delete it — it does
not belong in release notes either.
