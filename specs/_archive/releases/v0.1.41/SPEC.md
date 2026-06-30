# SPEC: v0.1.41 - Open bug root-cause sweep

**Status:** Aprovado
**Release ID:** v0.1.41
**Owner:** product-engineer
**Created:** 2026-06-29

## Workflow Evidence

Release definition was started through the workflow-first path:

```bash
dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.41 \
  --run-id v0141-open-bug-root-cause-sweep \
  --intent "Resolve the remaining open dadaia-workspace bug ledger by grouping shared root causes and fixing all feasible root-cause classes in one governance/infrastructure release." \
  --bug agents-md-says-validate-html-reports-with-json-only-validator \
  --bug codex-config-emits-invalid-approved-commands \
  --bug context-dead-plain-git-push-fails-mismatched-upstream \
  --bug grill-and-oq-decisions-records-gitignored-not-version-controlled \
  --bug import-linter-contracts-red-but-not-ci-enforced \
  --bug layer1-hooks-create-repo-pycache \
  --bug memory-heading-allowlist-not-consumer-extensible \
  --bug panel-csp-blocks-mermaid-cdn-script-and-stale-ops-subsection-test \
  --bug reports-validate-rejects-html-despite-agents-md-contract \
  --bug root-whitelist-misses-nested-new-toplevel-writes \
  --bug spec-doc-029-false-forgery-harness-uuid-vs-session-record-id \
  --bug specs-doctor-does-not-resolve-persisted-bound-context \
  --bug specs-doctor-ignores-persisted-context-bind \
  --harness fake --json
```

The workflow completed through `definition_commit_gate`. The fake harness produced only
placeholder artifacts, so the canonical release files were replaced by this root-cause
definition. `ACTIVE.md` remains on `v0.1.40 alpha-1` because that implementation is still
in progress; this release is the prepared next bug-sweep release.

## Picked Scope

This release picks every true-open `dadaia-workspace` bug as of 2026-06-29. The closed
`bug-report-fake-bug-write-emits-stub-and-discards-fields` record is not picked; it only
matched naive text search because its body contains an old example with `status: Open`.

| Bug | Classification | Root-cause disposition |
|-----|----------------|------------------------|
| `agents-md-says-validate-html-reports-with-json-only-validator` | Duplicate/report-validation contract drift | Fixed with `reports-validate-rejects-html-despite-agents-md-contract` by making docs and CLI behavior agree. |
| `reports-validate-rejects-html-despite-agents-md-contract` | Report-validation CLI UX | Fixed by clear handoff-only behavior or HTML-report validation support; no raw JSON parse for HTML inputs. |
| `specs-doctor-does-not-resolve-persisted-bound-context` | Duplicate specs-dir context resolution | Fixed with `specs-doctor-ignores-persisted-context-bind`. |
| `specs-doctor-ignores-persisted-context-bind` | Specs resolver ignores persisted bind when env is not exported | Fixed by resolving the persisted session/incumbent bind without requiring `eval $(...)`. |
| `context-release-ignores-persisted-bind-and-requires-dadaia_session_id-env` | Context release ignores persisted bind | Fixed with the persisted-bind resolver group so cleanup can release the bound session without env-only state. |
| `spec-doc-029-false-forgery-harness-uuid-vs-session-record-id` | Lease/session identity namespace + isolation | Fixed by comparing like identity spaces and isolating `--specs-dir` doctor runs from live workspace locks unless explicitly intended. |
| `root-whitelist-misses-nested-new-toplevel-writes` | Root guard under-enforcement | Fixed by classifying the first path component below workspace root for nested writes. |
| `layer1-hooks-create-repo-pycache` | Runtime hygiene / bytecode side effects | Fixed by disabling or redirecting bytecode for Layer-1 hook and CLI execution paths that import from repo source. |
| `grill-and-oq-decisions-records-gitignored-not-version-controlled` | Governance evidence gitignore omission | Fixed by tracking `GRILL.md` and `OQ-DECISIONS.md` in release root and segment dirs. |
| `import-linter-contracts-red-but-not-ci-enforced` | Architecture boundary drift + missing CI gate | Fixed by removing current import-linter violations and adding import-linter to local/CI preflight. |
| `codex-config-emits-invalid-approved-commands` | Stale Codex projection config | Fixed by removing invalid `approved_commands` TOML emission and pinning a projection contract test. |
| `context-dead-plain-git-push-fails-mismatched-upstream` | Context lifecycle git push portability | Fixed by pushing to the configured upstream ref explicitly or recognizing already-contained commits. |
| `memory-heading-allowlist-not-consumer-extensible` | Consumer extensibility gap in memory lint | Fixed by adding a workspace-level heading extension mechanism or narrowing lint to forbidden/changelog headings plus structural canon. |
| `panel-csp-blocks-mermaid-cdn-script-and-stale-ops-subsection-test` | Stale open bug after existing panel fix | Closed by verification and bug status update; if verification fails, add the missing panel E2E/preflight guard in this release. |

## Requirements

### R1 - Report validation contract is unambiguous

`dadaia reports validate` and all projected AGENTS/handoff instructions MUST describe the
same contract.

Acceptance:

- Running `dadaia reports validate <html-report>` no longer emits a raw JSON parse error.
- If HTML validation remains out of scope, the CLI emits a clear handoff-JSON-only message.
- `dadaia_workspace/public/data/AGENTS.md`, `handoff-AGENTS.md`, and handoff-emitter skill
  examples point validation at handoff JSON paths when validating report integrity.

### R2 - Specs doctor honors bind-driven context resolution

Specs commands MUST honor the persisted context created by `dadaia context bind` without
requiring shell-exported environment variables.

Acceptance:

- From the workspace root, after `dadaia context bind dadaia-workspace --mode read`,
  `dadaia specs doctor` resolves `repos/dadaia-workspace/specs`.
- After `dadaia context bind ... --mode implementation --release <id>`, plain
  `dadaia context release` can release that persisted session without requiring
  `DADAIA_SESSION_ID` to be exported.
- Error text no longer instructs only the legacy `eval $(...)` path.
- The duplicate specs-doctor bind bugs and the context-release bind bug are closed with one
  shared evidence block.

### R3 - SPEC-DOC-029 compares coherent identities and isolates scoped runs

The lease/session coherence backstop MUST detect real forgery without flagging normal
harness UUID vs `sess_*` namespace differences.

Acceptance:

- A live coherent session with harness UUID and session-record id does not raise
  SPEC-DOC-029 ERROR.
- `dadaia specs doctor --specs-dir <tmp specs>` does not inspect unrelated live workspace
  locks unless a workspace-state dir is explicitly supplied by the caller.
- Stale dead-session locks remain WARN/reclaimable, not false ERROR.

### R4 - Root and repo hygiene guards cover nested and generated artifacts

The workspace and repo hygiene rules MUST be deterministic for common agent/tool writes.

Acceptance:

- Root whitelist blocks `<workspace>/<forbidden-top-level>/<nested-file>` when the first
  root component is forbidden and not operator-excepted.
- Layer-1 hooks and CLI invocations do not recreate repo-local `__pycache__/` trees.
- `.gitignore` re-includes release `GRILL.md` and `OQ-DECISIONS.md` for root, `alpha-*`,
  and `rc-*` release dirs.

### R5 - Architecture contracts are green and enforced

Import-linter contracts MUST hold and run in the same preflight surfaces operators rely on.

Acceptance:

- `lint-imports` exits 0 on the repo.
- Feature modules no longer import infrastructure concrete stores or subprocess through
  CLI transitive paths.
- `dadaia ci preflight` and GitHub CI include import-linter or an equivalent contract job.

### R6 - Stale runtime/config surfaces are removed

Public runtime projections and lifecycle helpers MUST not advertise dead enforcement paths.

Acceptance:

- Codex config generation emits no `approved_commands` key.
- Contract tests assert invalid Codex config keys remain absent.
- `dadaia context dead` succeeds when local branch name differs from its configured upstream
  branch, or skips push when HEAD is already contained upstream.

### R7 - Memory lint supports consumer vocabulary

Memory heading lint MUST preserve generic governance without forcing consumer workspaces to
use dadaia-workspace-specific headings.

Acceptance:

- A consumer workspace can extend allowed H2 headings without editing library source, or
  the lint is narrowed to forbidden-history/changelog headings plus structural canon.
- The scaffolded memory files pass the generic lint without permanent WARN noise.
- Existing dadaia-workspace memory warnings are reduced or justified by local extension.

### R8 - Panel CSP bug is either closed as shipped or guarded

The stale panel CSP bug MUST not remain open without a current failing reproduction.

Acceptance:

- Current panel code has no CDN mermaid import and no CSP console error.
- The ops-tab subsection assertion matches the live order.
- Either local panel E2E is added to preflight when dependencies are available, or QA
  instructions require panel E2E for releases touching `features/panel/**`.

## Out Of Scope

- Solving bugs in other contexts such as `dd-chain-capture` or `dd-chain-explorer`.
- Renaming legacy archived release folders that only produce SemVer warnings.
- Closing `v0.1.40`; that active implementation must finish independently.

## Feasibility

All picked bugs have feasible root-cause fixes. The only special handling is
`panel-csp-blocks-mermaid-cdn-script-and-stale-ops-subsection-test`, whose own record says
the code fix was already applied; this release must verify and close it rather than
inventing a second fix.
