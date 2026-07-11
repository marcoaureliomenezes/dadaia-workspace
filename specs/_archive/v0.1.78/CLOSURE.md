# CLOSURE — Release v0.1.78 — Lifecycle correctness & diagnosability

**Shipped:** PR #153, squash-merged to main as `e7d7f28c` (2026-07-11). All PR checks
green; post-merge main CI green.

## Delivered

All 5 FRs (T-A..T-E) + T-F validation. The lifecycle engine now tells the truth:
persisted state == reported state; every block carries evidence + the exact next
command.

## Dispositions — all 4 HIGH bugs RESOLVED with executed-path evidence

- `single-implement-verb-gated-as-review` — explicit step kind; bug-ratifying test
  flipped; no test ratifies the old behavior (QA grep-verified).
- `full-pipeline-success-persists-running-empty-ledger` — atomic terminal COMPLETED
  save + per-step ledger payloads; real-store reload proof.
- `split-cleanup-engines-strand-stale-step-payloads` — one cleanup contract; the
  reported loop (doctor flags → official remediation reclaims → doctor clean) proven.
- `worker-noncompliance-block-carries-no-diagnostic-evidence` — redacted bounded
  WorkerDiagnostic referenced from BlockedState.detail; PI `--thinking` wired
  (argv-safe); 3-layer proof.

Backlog `lifecycle-pipeline-correctness-and-diagnosability` (absorbing
`preflight-block-reasons`, `implement-review-write-scope-parity`,
`tasks-write-scope-traversal-hardening`): **delivered**, archived.

Ledger after closure: **1 open** (`perf-hygiene-scan-rss-ceiling-flaky-in-sandbox`,
LOW — pre-existing sandbox RSS-ceiling flake, tracked).

## Corrections recorded during implementation

- SPEC said "seven" null `operator_command` sites; reality at HEAD was FIVE (v0.1.76
  had already converted the two lease sites to advisory warnings) — QA independently
  confirmed via diff; all 13 blocked reasons now assert non-null in the matrix.
- FR-D wording corrected (QA LOW): `actual_reasoning` is honestly unset when the PI
  CLI does not report it back — never fabricated.

## Validations

- Full suite 2,860 passed / 10 skipped (single failure = the registered LOW flake).
- mypy --strict clean; ruff clean; doctors green (specs 0 errors, public ok).
- QA APPROVED (per-bug executed-path verification); security APPROVED (+ re-key after
  the marker amend): diagnostic redaction real/bounded/pre-persist, cleanup confined
  to `.dadaia/runs`, `--thinking` injection-safe, write-scope net improvement.
