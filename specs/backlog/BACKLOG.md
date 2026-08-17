# Backlog — single source (ACTIVE + LEDGER)

Consolidated 2026-08-15 by `project-manager` (v0.12.0 FR7, task T-120-07) from the 31 live
per-entry files and `candidates.md` (both `git mv`-archived to `_archive/` at the v0.12.0
cutover, never deleted). Schema: `dd-backlog-definition` §2 — five required keys per
`ACTIVE` subsection plus the optional `Intents` key (OD-1); `LEDGER` grammar
`slug · DISPOSITION · release-or-reason · date`. Never-delete proven by count (ADR D4):
28 ACTIVE subsections + 54 LEDGER rows carry every pre-consolidation record — the
consolidation landed at 30 + 52 and v0.12.0's own closure sweep moved its two picked
entries across, the same 82 slugs; the set-equality evidence is captured under
`.dadaia/tmp/project-manager/20260815/`. Counts are as of the 2026-08-15 consolidation;
later curation (operator-adjudicated intake) appends entries and LEDGER lines on top,
never renumbering.
Entry numbering (`#N`) from the retired `candidates.md` index is carried in each Title —
rows are never renumbered, and LEDGER rows are never deleted.

**`## ACTIVE` is EMPTY (2026-08-17).** Release **v0.4.3 "claims-made-true / backlog-zero"**
picked the entire queue in one release under the operator's standing order ("fila inteira
em 1 release"). This is a deliberate, recorded state — not a lost document. The 24
consumed slugs receive their `LEDGER` lines at that release's closure disposition sweep;
the single rejected idea already carries its line below. New demand enters as it always
has: only the operator creates it, and `project-manager` curates it here.

**Pick-precedence notice (DADAIA.md §5).** At release-pick time, open bugs and
undispositioned audits outrank every fresh entry. **Currently outranking: nothing.**
Zero open bugs: the two LOWs that outranked the queue on 2026-08-16 —
`memory-token-estimate-normalizer-dead-code` and the orphan factory it surfaced,
`memory-catalog-regenerator-orphaned-factory` — were both closed by Arm B on `develop`
on 2026-08-17 (`specs/bugs/bugs.jsonl:889` and `:891`; commits `7971eefb`, `9a09b551`;
pure deletions, full gate green). Both 2026-07 audits remain archived and fully
dispositioned (v0.8.0). The ledger (`dadaia bugs status`) remains the source of truth.

**Purge-on-pick notice — release v0.4.3 "claims-made-true / backlog-zero" (2026-08-17).**
All **25** `ACTIVE` subsections left this document in the same commit that created
`specs/releases/v0.4.3/SPEC.md`, whose §7 is their provenance record: the 20 candidates
(`test-suite-remediation-stewardship` #2, `consumer-side-validation-round` #5,
`thin-wrapper-projected-scripts` #6, `bug-picked-ledger-event` #7,
`codex-persona-law-context-dehydration` #8, `python-env-interpreter-probe-hardening` #9,
`panel-runtime-reliability-dangling-ledger-pointer` #12,
`mutation-testing-tool-selection-and-wiring` #13,
`intent-docstring-mechanical-enforcement` #14, `gitflow-reconciliation-merge-mechanic` #15,
`memory-path-class-dotfiles` #16, `commit-paths-index-scope-hardening` #18,
`commit-message-scanning-residual` #21, `baseline-carve-out-review-cadence` #24,
`dd-skills-applyto-glob-collisions` #32,
`dd-release-definition-orchestration-pointer-loop` #33,
`bug-event-redaction-always-on-reinforcement` #34,
`dd-audit-project-pinned-tool-installs` #35, `dadaia-cli-skill-agent-grant` #36,
`codex-skill-ref-phantom-memory-ctx-prefix` #37) plus `dadaia-artifact-event-driven-gc`
and the four ideas (`bugs-jsonl-whole-blob-per-append`,
`repo-agents-md-symlink-hardening`, `stewardship-relocation-grep-homonym-note`,
`tests-agents-md-placeholder-doctor-warning`). Twenty-four are declared in that SPEC's
`**Consumes:**` line and receive `DELIVERED · v0.4.3` (or `SUPERSEDED · v0.4.3` for #37)
at the closure sweep. The twenty-fifth, `bugs-jsonl-whole-blob-per-append`, was
**REJECTED** by operator ruling and its `LEDGER` line is written below in this same
commit. Two external items ride the release without ever becoming entries (ADR #15): the
co-author-trailer carve-out gap (folded into #24) and the CHANGELOG-backfill intake
candidate. Nothing was deleted.

**Purge-on-pick notice — release v0.4.2 "residual-convergence" (2026-08-16).** Thirteen
ACTIVE subsections left this document in the same commit that created
`specs/releases/v0.4.2/SPEC.md`, whose §7 is their provenance record:
`backlog-grammar-single-writer-seam` (#38), `denylist-masking-predicate-parity` (#39),
`derived-values-computed-not-stored` (#43), `knowledge-duplication-doc-pass` (#44),
`flat-release-ship-task-evidence`, `intake-signal-calibration`,
`amnesty-multi-path-blob-fail-closed` (#40), `git-batch-epipe-swallow-width` (#41),
`self-scan-sentinel-archive-authored-blobs` (#45), `document-parser-fence-filter-complexity`
(#42), `retire-dead-hotfix-surface` (#4), `changelog-version-axis-reconciliation` (#11) and
`spec-doc-031-citation-classes` (#10). Their `LEDGER` lines were written by that release's
closure disposition sweep on 2026-08-16 (`DELIVERED · v0.4.2`, at the end of `## LEDGER`) —
nothing was deleted. `baseline-carve-out-review-cadence` (#24) was a **partial** pick: it
stayed ACTIVE, rewritten to its residual, and was picked **in full** by v0.4.3.

**Standing operator decision, RULED 2026-08-17 (was v0.8.0 CLOSURE return #3).** Is
`deferred` terminal for bug `panel-telemetry-sqlite-corrupts-under-concurrent-access`?
Ruled by the v0.4.3 dispatcher (operator-delegated, ADR R6): **no new disposition token**
— the dangling-pointer repair `panel-runtime-reliability-dangling-ledger-pointer` (#12)
implements within its own scope, using the existing vocabulary. The question no longer
surfaces at pick.

**Standing operator question, pending (PM decision record 3 — restated at intake #3,
operator adjudication 2026-08-16; carried again at the v0.4.3 pick as ADR R9).** Should
the git commit identity used in this workspace be de-personalised going forward? Both
v0.12.0 security reviews dispositioned the existing identity as pre-existing published
metadata (1,063 of 1,203 commits) — not a leak; it is an operator policy call and stands
open until ruled. v0.4.3 restates it in its CLOSURE rather than deciding it. The question
travelled to `specs/backlog/_archive/candidates.md` at the cutover; restated here so it
is no longer archive-only.

## ACTIVE

## LEDGER

- push-range-denylist-scan · DELIVERED · v0.9.0 · 2026-08-14
- redact-foreign-context-names-at-qa-authoring · DELIVERED · v0.9.0 · 2026-08-14
- tag-push-carve-out-reachability · DELIVERED · v0.9.0 · 2026-08-14
- 20260814-dd-lifecycle-skills-family · DELIVERED · v0.10.0 · 2026-08-15
- prior-published-term-amnesty · DELIVERED · v0.11.0 · 2026-08-15
- denylist-scan-skip-note-oversized-mislabel · DELIVERED · v0.11.0 · 2026-08-15
- registry-derived-foreign-name-set · DELIVERED · v0.11.0 · 2026-08-15
- refusal-path-redaction · DELIVERED · v0.11.0 · 2026-08-15
- push-ref-sha-validation-git-argv-hardening · DELIVERED · v0.11.0 · 2026-08-15
- git-objects-batch-parse-typed-error-boundary · DELIVERED · v0.11.0 · 2026-08-15
- git-objects-streamed-batch-reads · DELIVERED · v0.11.0 · 2026-08-15
- closure-v14-perf-figure-correction · DELIVERED · v0.11.0 · 2026-08-15
- self-scan-sentinel-integration-marker · DELIVERED · v0.11.0 · 2026-08-15
- backlog-tooling-reconciliation · DELIVERED · v0.12.0 · 2026-08-15
- backlog-md-physical-consolidation · DELIVERED · v0.12.0 · 2026-08-15
- loud-flake-stats-key-residual · DELIVERED · fixed before materialization · 2026-08-14
- frozen-wall-clock-baselines-in-repo-text · DELIVERED · baselines embedded in memory · 2026-08-14
- dispose-published-denylist-term · REJECTED · void by construction under the range-scoped scan · 2026-08-14
- 20260714-panel-games-pong-codex-v026 · REJECTED · surface removed in v0.3.0, nothing to validate · 2026-08-14
- 20260714-snake-wall-wrap-v025-pi-validation · REJECTED · same removal, nothing to validate · 2026-08-14
- intake-2-6-consumer-validation-recipe-glob · REJECTED · operator discard at intake (delegated) · 2026-08-15
- intake-2-8-spec-drafting-zero-hit-grep-lesson · REJECTED · operator discard at intake (delegated) · 2026-08-15
- 20260704-fast-tier-persona-validation · REJECTED · v0.1.64 · 2026-07-09
- 20260707-dispatch-band-legacy-fallback-removal · SUPERSEDED · deprecation-strips-and-doctor-cleanup (2026-07-10 consolidation) · 2026-07-10
- 20260707-platform-seam-todo-retirement · SUPERSEDED · lock-lease-session-identity-kernel (2026-07-10 consolidation) · 2026-07-10
- 20260707-specs-doctor-partial-archive-invariant · SUPERSEDED · deprecation-strips-and-doctor-cleanup (2026-07-10 consolidation) · 2026-07-10
- 20260708-panel-tab-reorg-agentic-layers · DELIVERED · v0.1.79 · 2026-07-11
- 20260709-central-bind-resolution-seam · DELIVERED · v0.1.77 · 2026-07-11
- 20260709-implement-review-write-scope-from-tasks-parity · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-preflight-block-reasons-missing-operator-command · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-tasks-write-scope-traversal-hardening · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-test-suite-remediation-waves · CONSUMED · v0.1.75 (PR #145) · 2026-07-10
- 20260710-deprecation-strips-and-doctor-cleanup · DELIVERED · v0.1.81 (date gate operator-waived 2026-07-11) · 2026-07-11
- 20260710-lifecycle-pipeline-correctness-and-diagnosability · DELIVERED · v0.1.78 · 2026-07-11
- 20260710-lock-lease-session-identity-kernel · DELIVERED · v0.1.76 (NO-LOCKS doctrine) · 2026-07-10
- 20260711-context-name-allowlist-at-resolution-rungs · DELIVERED · v0.1.80 · 2026-07-11
- 20260715-bugfix-workflow-tdd · REJECTED · v0.3.0 engine demolition — strict-TDD bug flow is law (constitution §1) · 2026-08-12
- 20260806-clean-architecture-remediation · CONSUMED · v0.5.0 · 2026-08-12
- 20260806-dadaia-md-workspace-system-prompt · CONSUMED · v0.5.0 · 2026-08-12
- 20260810-security-low-carryforwards-v030 · CONSUMED · v0.5.0 · 2026-08-12
- backlog-definition-workflow-dedup-conflict-control · DELIVERED · v0.1.26 · 2026-07-02
- codex-runtime-fidelity · DELIVERED · v0.1.13 (WS-CDX waves; protocol+hygiene verified at HEAD) · 2026-07-02
- gitflow-standardization · DELIVERED · v0.6.0 · 2026-08-12
- l1-agent-model-governance-panel · DELIVERED · v0.1.65 · 2026-07-08
- lifecycle-prompt-fragments-ai-surface-dehydration · DELIVERED · v0.1.30 (Waves A/E) · 2026-07-02
- selfrepo-agents-md-doubled-header · DELIVERED · v0.1.61 · 2026-07-07
- shared-headless-adapter-base · DELIVERED · v0.1.30 Wave A · 2026-07-02
- test-artifact-hygiene · CONSUMED · bug panel-e2e-artifacts-no-consumer (operator ruling 2026-08-12 — bad tests are bugs) · 2026-08-12
- test-runtime-efficiency · CONSUMED · bug test-suite-real-venv-and-ci-longpole (operator ruling 2026-08-12 — bad tests are bugs) · 2026-08-12
- test-stewardship-standardization · DELIVERED · v0.7.0 · 2026-08-12
- wire-consumed-ledger-producer-at-release-definition · DELIVERED · v0.1.27 · 2026-07-02
- workflow-model-governance-operator-profiles-and-context-overlays · DELIVERED · workflow-engine era, terminal frontmatter (engine removed v0.3.0) · 2026-07-02
- workflow-model-governance-panel-control-plane · DELIVERED · v0.1.28 · 2026-07-02
- workflow-step-handoff-data-plane-cleanup · DELIVERED · workflow-engine era, terminal frontmatter (engine removed v0.3.0) · 2026-07-02
- intake-3-2-match-throughput-fallback · REJECTED · v0.11.0 measured rejection ratified at intake #3 (fallback is the rare shape; a matcher-engine change is its own correctness surface; 55 s one-time scan inside tolerance) · 2026-08-16
- backlog-grammar-single-writer-seam · DELIVERED · v0.4.2 · 2026-08-16
- denylist-masking-predicate-parity · DELIVERED · v0.4.2 · 2026-08-16
- derived-values-computed-not-stored · DELIVERED · v0.4.2 · 2026-08-16
- knowledge-duplication-doc-pass · DELIVERED · v0.4.2 · 2026-08-16
- flat-release-ship-task-evidence · DELIVERED · v0.4.2 · 2026-08-16
- intake-signal-calibration · DELIVERED · v0.4.2 · 2026-08-16
- amnesty-multi-path-blob-fail-closed · DELIVERED · v0.4.2 · 2026-08-16
- git-batch-epipe-swallow-width · DELIVERED · v0.4.2 · 2026-08-16
- self-scan-sentinel-archive-authored-blobs · DELIVERED · v0.4.2 · 2026-08-16
- document-parser-fence-filter-complexity · DELIVERED · v0.4.2 · 2026-08-16
- retire-dead-hotfix-surface · DELIVERED · v0.4.2 · 2026-08-16
- changelog-version-axis-reconciliation · DELIVERED · v0.4.2 · 2026-08-16
- spec-doc-031-citation-classes · DELIVERED · v0.4.2 · 2026-08-16
- bugs-jsonl-whole-blob-per-append · REJECTED · v0.4.3 operator ruling (ADR R4) — complexity exceeds value: three divergent candidate shapes, four consumers (panel, doctor, pick precedence, closure sweep) and two laws (never-delete, ADDITIVE class) in the blast radius, while the content-resurfacing half is already neutralized by the shipped prior-published-term amnesty and the measured scan cost stayed inside tolerance; revisit only on a measured problem · 2026-08-17
