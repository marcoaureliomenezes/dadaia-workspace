# SPEC — Release v0.1.78 — Lifecycle correctness & diagnosability

**Status:** Aprovado
**Source:** backlog `20260710-lifecycle-pipeline-correctness-and-diagnosability` (P1);
disposes the 4 open HIGH bugs (`single-implement-verb-gated-as-review`,
`full-pipeline-success-persists-running-empty-ledger`,
`split-cleanup-engines-strand-stale-step-payloads`,
`worker-noncompliance-block-carries-no-diagnostic-evidence`); release definition +
per-intent CONFIRMED research in `specs/backlog/candidates.md` (all anchors verified).

## Contract theme

The lifecycle engine must tell the truth (persisted state == reported state) and every
block must carry evidence plus the exact next command.

## FRs (= tasks T-A..T-E)

- **FR-A (bug: implement gated as review).** Step kind becomes EXPLICIT, independent of
  transition target: `is_review`/StepKind threaded like `PipelineStep.is_review`
  (pipeline.py:102); `implement`/`close` are is_review=False, review verbs True. The
  test asserting the bug as contract (`test_lifecycle_command_skeletons.py`) flips to
  the corrected truth: a SUCCEEDED create result with artifact_refs and no self-verdict
  passes the create gate.
- **FR-B (bug: pipeline persists running+empty ledger).** CLI success and persisted
  terminal state are ATOMIC: `run()` saves `replace(run, status=COMPLETED)` before
  returning (mirroring implement-review's pipeline.py:418-419); save failure fails the
  command; the full ladder produces run-scoped per-step payloads via the
  handoff_resolver exactly like implement-review.
- **FR-C (bug: split cleanup engines + preflight remediation).** ONE canonical cleanup
  contract: `hygiene clean` delegates to (or aliases) the RetentionSweep so the
  official remediation can reclaim what handoffs doctor flags;
  status/preflight-remediation/doctor/dry-run/apply share one candidate classifier;
  safety gates preserved, doctor not weakened. PLUS the seven preflight `_blocked`
  sites that default `operator_command=None` each gain the exact remediation command;
  the preflight test matrix asserts non-null operator_command for EVERY blocked reason.
- **FR-D (bug: worker noncompliance evidence + PI --thinking).** Every real worker
  attempt persists ONE redacted run-scoped diagnostic (runtime, model,
  requested/actual reasoning, exit, parser classification, redacted output tail,
  session ref) referenced from `BlockedState.detail`; a no-op result still blocks —
  now with evidence. `PiHeadlessConfig.reasoning_effort` forwards to PI `--thinking`
  (PI >= 0.80.3) and requested==actual is recorded/verified.
- **FR-E (write-scope parity + parser hardening).** `implement-review` gains
  `write_scope_from_tasks` + a `--write-scope` escape hatch (parity with `pipeline`);
  `_extract_globs` rejects absolute/`..`/`~`/`$` tokens at parse time
  (defense-in-depth; each rejected token maps to no captured glob); frozen FR3 grammar
  tests stay green.

## Acceptance

- Per-bug executed-path RED→GREEN tests; each of the 4 HIGH bugs resolved with
  `--resolution-evidence` at closure; no test ratifies old broken behavior.
- Full suite green; mypy --strict; ruff; lint-imports; doctors; per-sha security
  APPROVE on every push.
