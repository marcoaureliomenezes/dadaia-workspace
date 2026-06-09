# CLOSURE — Release 0.1.7 "Audit Remediation + Unlock the Workflow"

**Status:** Aprovado
**Release ID:** 0.1.7 (minor over 0.1.6)
**Closed:** 2026-06-09
**Branch:** `feature/0.1.7` → merged to `main` (PyPI publish deferred to the cross-platform release per operator directive)

---

## 1. Summary

0.1.7 matured across four segments on a single `feature/0.1.7` branch:

- **alpha (T-017-01..20)** — deep-audit remediation of the library: 14 audit findings fixed,
  the `public_assets.py` god-module split (2350→596 lines, T-017-11), net-new gate
  persona-fallback (later removed in rc-3) and the SEC-01 PROTECTED `.dadaia/sessions` fix,
  preflight-absent coverage.
- **rc-2** — independent re-audit PASS (9.2/10 and 7.8/10 two-reviewer), `bug-registration-guardrail`
  rule added across runtimes.
- **rc-3 "Unlock the Workflow" (T-017-21..28)** — removed the backlog-ownership persona gate (a
  *lock with no key* that blocked the legitimate owner in **both** Claude and Codex). New product
  law: **no workflow is ever lock-blocked; the single-session lease is the ONLY deterministic
  lock.** Deletion-dominant; backlog/`specs/backlog/**` is now plain ADDITIVE.
- **rc-4 "Bug root-cause sweep" (T-017-29..36)** — root-caused and fixed **all 8** open reported
  bugs, headlined by the CRITICAL `gate-cross-context-lock-contamination` (the kept lease itself
  was buggy — it resolved context from first-ALIVE/env, not the write-target path).

Full CI-equivalent suite green at close: **2365 passed, 2 skipped, 1 xpassed**;
`ruff format --check` + `ruff check` + `mypy --strict` (193 files) clean; `dadaia public doctor`
and `dadaia specs doctor` exit 0; `public-privacy [ok]`. All 39 tasks `[x]`.

## 2. What shipped (by segment)

| Segment | Tasks | Outcome |
|---|---|---|
| alpha | T-017-01..20 | 14 audit findings remediated; `public_assets.py` split to 596 lines; lock-liveness memory; preflight-absent coverage; T-017-11 module split (T-017-11 also deferred-then-reopened). |
| rc-2 | re-audit | Two independent verification re-audits PASS; `bug-registration-guardrail` rule (Claude `.claude/rules` + Codex root `AGENTS.md`). |
| rc-3 | T-017-21..28 | Deleted the backlog-ownership persona block + the dormant RULE-D write-allowlist deny from `sdd-spec-gate.sh`. `specs/backlog/**` → plain ADDITIVE-allow. `.dadaia/sessions/**` stays PROTECTED, re-justified on lease `.ptr` integrity. Reworded `backlog-ownership.md`, `ctx-inject.sh`, `specs/AGENTS.md`, personas, and 2 memory atoms → ownership is a coordination convention, not a gate. 3 gate tests flipped to assert ALLOW. End-to-end proof: a previously-blocked backlog epic registered via the live reprojected gate. |
| rc-4 | T-017-29..36 | All 8 reported bugs fixed + closed `resolved_in: 0.1.7`. |

### rc-4 bug fixes (8/8)

| Bug | Sev | Task | Fix |
|---|---|---|---|
| gate-cross-context-lock-contamination | CRITICAL | T-029 | Lease context derived PATH-first from `repos/<slug>/…`, not first-ALIVE/env. |
| repeated-visible-userpromptsubmit-memory-injection | CRITICAL | T-030 | `ctx-inject.sh` rewrite: harness-native session id resolved once; sentinel guards the whole injection. |
| constitution-persona-single-source-drift | HIGH | T-031 | Memory-write phase aligned (DEFINITION+CLOSURE) + SINGLE-SRC-1 lint. |
| install-does-not-prune-orphan-projections | HIGH | T-032 | Orphan-prune sweep across all copy strategies. |
| agent-skill-surface-slop | HIGH | T-032/036 | Prune + stage agent→skill ref-gate. |
| specs-upgrade-fails-on-preexisting | MEDIUM | T-033 | Pre/post error-diff; pre-existing errors `[warn]`, only new `[fail]`. |
| specs-doctor-dual-error-counter | LOW | T-033 | Authoritative final verdict line. |
| ci-preflight-raw-traceback | LOW | T-034 | `FileNotFoundError` → `(127, "command not found …")`. |

## 3. Review evidence

- **rc-2 re-audit:** two independent verification re-audits — **PASS** (9.2/10, 7.8/10).
- **rc-3:** code-reviewer found 6 residual "hard-gated" drift surfaces in the first self-review;
  all fixed, re-reviewed **APPROVE**. End-to-end gate proof recorded.
- **rc-4 ship-trio — unanimous APPROVE:**
  - **security-reviewer — APPROVE.** No CRITICAL/HIGH; PROTECTED `.dadaia/sessions` boundary intact.
  - **code-reviewer — APPROVE.** `bash -n` clean both scripts; gate path-derivation + ctx-inject
    sentinel verified.
  - **qa-engineer — APPROVE.** Full suite green; all 8 regression tests genuine (not slop).
  - One pre-existing MEDIUM (FPATH not realpath-normalized before the bash classifier, **no current
    bypass**) registered as `gate-fpath-not-canonicalized-before-classifier` for a dedicated fix
    rather than a late rc-4 change.

## 4. Deferred / follow-ups (tracked, not lost)

- **T-017-11 module-split** beyond `public_assets.py` — additional deferrals tracked for 0.1.8.
- `gate-fpath-not-canonicalized-before-classifier` (MEDIUM, no live bypass) — bug filed.
- `lease-shell-write-coverage-gap` (MEDIUM, ADR-3) — backlog candidate: the lease mediates only
  agent file-tools, not Bash/CLI writes.
- Cross-platform OS compatibility (FEAT-XPLAT-OS-COMPAT-01) — backlog candidate, picked into the
  next release.

## 5. Product law established by this release

> No workflow — research, backlog definition, release definition, implementation+review, audits —
> is ever lock-blocked for ownership reasons. The **only** deterministic lock in the workspace is
> the single-session-per-Spec-Context lease, enforced during release-definition and
> implementation+review. `project-manager` always spawns and coordinates freely.

## 6. Validation at close

```
pytest: 2365 passed, 2 skipped, 1 xpassed
ruff format --check: 424 files already formatted
ruff check: All checks passed!
mypy --strict: Success: no issues found in 193 source files
dadaia public doctor: exit 0 — [ok] public-privacy
dadaia specs doctor: exit 0
```
