# Test Rules — <project-name>

> Installed by dadaia. Replace every `<ANGLE-BRACKET>` placeholder below with this project's own values before relying on it.
> A placeholder left in place means that section is not yet calibrated.

These rules override general workspace guidance for everything under `tests/`.
Agents creating or editing tests must follow them. Full protocol: skill `dd-test-stewardship`.
Numbers below are this project's adjustable defaults.

## 1. Intent taxonomy

- Every test declares intent in its module docstring: `Intent: <KIND> — <AC id | bug-id | task-id>`.
- Never as a pytest marker.
- CONTRACT (permanent, asserts an AC or a bug).
- SENTINEL (permanent, the single integration test of one seam).
- SCAFFOLD (temporary, expires at its task/release closure).
- QUARANTINE (flaky, carries a registered bug id).
- An undeclared test is SCAFFOLD — the default is to die, not to stay.

## 2. Architecture (size tiers)

- `tests/unit/**` (SMALL): pure or near-pure tests only.
- No real subprocess execution, server threads, network, sleeps, or real external services in unit tests.
- `tests/contract/**` (SMALL): public API/CLI/schema/security contracts.
- `tests/integration/**` (MEDIUM): multi-component tests using a tmp filesystem or local service wiring.
- `tests/e2e/**` (LARGE): named end-to-end journeys only; every file names an owner in a comment or docstring.
- `tests/tmp/**`: SCAFFOLD only — excluded from default collection, deleted or promoted before closure.

## 3. Admission filter

- A new test enters the permanent suite only if it compiles and runs, is deterministic, adds real detection.
- Real detection: covers previously-uncovered behavior, or kills a mutant no current test kills.
- Prohibited: change-detector tests (mirror the implementation).
- Prohibited: tautologies (expected value re-derived from the code under test).
- Prohibited: reflex-regenerated snapshots.

## 4. Deletion criteria and the tombstone ban

Delete, with `file:line` evidence in the commit, a test that meets any of:

| Criterion | Evidence |
|---|---|
| Feature removed | link to the removal |
| Duplicate coverage exists | `file:line` of the equivalent test |
| Tautology / no-op | shows the assertion never consults the product |
| Reflex-regenerated snapshot, no review | diff history |
| Failure-to-defect ratio ~= 0 | flake/failure history, zero real defects |
| Expired quarantine/skip, no plan | see Markers, cost and flake policy (§5) |

- Tombstone ban: a test whose central assertion is the absence of something removed validates a historical event.
- That test is SCAFFOLD of the release that removed the thing, and dies at that release's closure.
- The memory of the removal belongs to CLOSURE/changelog, never the suite.
- Separation of powers: the implementer never prunes to go green.
- Pruning is a quality-steward verdict carrying this table's evidence; the implementer executes the commit, quoting the verdict.

## 5. Markers, cost and flake policy

- Layer markers are applied automatically by directory.
- Per-test timeout defaults by tier (adjustable): unit `<UNIT_TIMEOUT_S>`s / contract `<CONTRACT_TIMEOUT_S>`s.
- Timeout defaults (continued): integration `<INTEGRATION_TIMEOUT_S>`s / e2e `<E2E_TIMEOUT_S>`s.
- A test needing more time than its tier allows is mis-tiered — fix the tier, never the default.
- `flaky` and `quarantine` markers exist; `quarantine` without a registered bug id is refused at collection.
- Every gating selector excludes `quarantine`.
- LARGE cap (declared, reported as a warning until achievable): `<LARGE_CAP>` per module (abstract default 12-15).
- Wall-clock budget is frozen at `<WALL_CLOCK_BASELINE>` per job; raising it requires a justification recorded at closure.

## 6. Good test standard

- A test is allowed only if it can fail for a meaningful regression: product behavior, public contract, security boundary.
- Also: data integrity, or a real user journey.
- If it mainly records implementation history, delete it — it does not belong in release notes either.
