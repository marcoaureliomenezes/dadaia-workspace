# CLOSURE — Release v0.1.70 — Contract & Repo-Hygiene Drift (+ remediation-arc finale)

> **Status:** Aprovado
> **Release ID:** v0.1.70
> **Merged:** `40ff24b1` (PR #134, squash), all CI green post-merge.

## Summary

Final release of the 3-release remediation arc (v0.1.68–70) that dispositioned the **9
live sample-consumer bugs** — all live on `main` at HEAD `54e9be0e`, the exact commit
the remote reporter ran. Release C fixed two shipped self-inconsistencies:

| Bug | Fix | Disposition |
|---|---|---|
| `specs-doctor-rejects-current-memory-agent-tier-frontmatter` (HIGH) | FR1 — corrected the `agent_tier` authoring lie in 4 doc surfaces to match the schema (which correctly rejects it); re-projected; doc↔schema consistency test | resolved |
| `remote-bugs-gitignore-blocks-new-intake` (HIGH) | FR2 — `.gitignore` negation un-ignores the `remote-bugs/` intake subtree; repo-hygiene test | resolved |

**Arc total: 9/9 bugs resolved across v0.1.68 (3 engine HIGH), v0.1.69 (1 CRITICAL + 3
context/CLI), v0.1.70 (2 contract-drift HIGH).** All remote-bugs intake files archived
(redacted) to `specs/backlog/remote-bugs/_archive/`. One side-bug found during the arc —
`stray-dadaia-tmp-inside-repo` (a `code-reviewer` sub-agent wrote `.dadaia/` inside the
repo) — remains tracked/open as a separate AI-surface concern.

## Validations

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | PASS — 5028 passed / 19 skipped / 0 failed | `pytest -p no:cacheprovider` |
| Mutation-sanity | PASS — FR1 per-surface + FR2, all correctly RED under revert | qa-engineer handoff `2026-07-09T093240Z` |
| Schema untouched | PASS — `git diff -- public/schemas/memory/` empty (docs-not-workaround) | qa-engineer |
| Projection | PASS — `dadaia public doctor` exit 0, `[ok] public-privacy`, 0 drift | pre-push + CI |
| Architect / security | APPROVE / APPROVED (FR2 negation tightly scoped; no secrets) | handoffs |
| CI (full matrix) | GREEN — ubuntu + Windows/macOS, PR #134 + post-merge main | GitHub Actions |

## Drifts

- The v0.1.66-era archived remote-bug intake files carried the reporter's `/home/ubuntu`
  env paths + a VM IP; redacted during archival (they became committable via FR2).
- Release B surfaced a CI-only flake (non-hermetic CLI test + a Rich-box-wrap substring
  assert) — corrected; the box-wrap gotcha was already documented in `quality-assurance.md`
  (v0.1.26) but not applied by the test author (a process gap, folded into the post-mortem).

## Memory updates

`specs/memory/quality-assurance.md` gained four durable laws distilled from this arc
(the post-mortem below): validate at the workflow boundary (adapter-green ≠ workflow-green);
"resolved" means the reported need is met; a constant-return stub is an unbuilt subsystem;
guard shipped contracts with a self-consistency test. Catalog regenerated.

## Post-mortem — why these 9 escaped detection before the operator hit them

**One-line root cause: we validated one layer below where the operator lives, and
declared victory from there.**

1. **Adapter-validated, never workflow-validated.** v0.1.66/67 fixed the pi/codex
   *adapter* and proved it with fake harnesses + adapter unit tests. No test ever drove
   the actual `dadaia lifecycle pipeline` / `implement-review` a real operator runs. The
   engine *above* the adapter — evidence selection, payload consumption, write-scope
   derivation, the whole preflight subsystem — was never exercised end to end. Three HIGH
   engine bugs and the inert-preflight bug lived precisely in that untested gap.
   **Fix embedded going forward:** every operator-facing workflow verb now has a
   full-pipeline E2E on a throwaway context (v0.1.68 FR4, v0.1.69 FR5).

2. **"Resolved" was allowed to mean "narrowed."** v0.1.66 closed a write-scope bug by
   shipping only a manual `--write-scope` flag; the operator's real need (auto-derive
   from `TASKS.md`) was never delivered and came back as a new bug. A disposition that
   patches a sub-case is not a fix.

3. **A stub masqueraded as a diagnostic.** `lifecycle preflight` returned a hardcoded
   BLOCKED for every release because its probe subsystem was never built — invisible
   until an operator tried to use it. Constant-return stubs in user-facing commands are
   unbuilt features, not wiring.

4. **Nothing guarded the library against contradicting itself.** The schema rejected
   `agent_tier` while the docs told authors to write it; `.gitignore` ignored the intake
   dir it called tracked truth. No consistency test existed for either. Both now have one.

5. **A known gotcha wasn't applied.** The CI-only CLI-test flake in Release B (Rich
   box-wrap) was already a documented law in `quality-assurance.md` — the process gap was
   the test author not consulting it. Memory laws only help if read before authoring.

**What I got wrong in reporting.** After v0.1.66/67 I let "the 7 adapter bugs are fixed"
sound like "the workflow is usable." It wasn't verified end to end, and I shouldn't have
implied it was. The arc's discipline — reproduce-first against the real executed path,
mutation-sanity to kill false positives, and an E2E at the operator's boundary — is the
corrective.

## Next

Remediation arc complete. Open follow-ups (all tracked): `stray-dadaia-tmp-inside-repo`
(bug), `preflight-block-reasons-missing-operator-command`,
`tasks-write-scope-traversal-hardening`, `implement-review-write-scope-from-tasks-parity`
(backlog). No PyPI publish this arc.
