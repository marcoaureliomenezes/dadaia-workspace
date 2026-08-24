# AR-2 Ruling — "the enforcement surface must shrink, not move" (S1 close)

**Release:** v0.4.4 · **Segment:** S1 · **Task:** T-044-11 (AR-2 half)
**Author:** software-architect · **Date:** 2026-08-23
**Mandate:** SPEC §6 AR-2 — state the before/after count of enforcement points and refuse
any dual path (A3.4, A4.5, D4). Standing order applied: permanent architecture review,
oriented by bug history.

**Verdict: ENFORCEMENT-SURFACE SHRUNK** — one point relocated by ratified design (G6),
zero dual paths, net −2 in the enforced-rule inventory. Arithmetic in §1; each dual-path
candidate ruled in §2; bug-surface direction in §3.

Evidence basis (all read on this branch): `dadaia_workspace/features/chokepoints/service.py`,
`dadaia_workspace/infrastructure/git_objects.py`, `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`,
`.github/workflows/ci.yml`, `.github/scripts/pr-verdict-check.sh`, `.github/scripts/check-verdict.sh`,
`dadaia_workspace/cli/commands/ci.py`, `tests/contract/test_ci_v2_gitflow_pr_gate.py`,
`specs/bugs/bugs.jsonl`. Baseline (v1) = origin/develop's law as recorded in
`specs/memory/product/sdd/sdd-gate-v3.md` (release_origin v0.4.2) and SPEC I1.

---

## 1. Before/after count of enforcement points

An enforcement point = a code path that can refuse an operation. Bookkeeping that cannot
refuse (§2.4) is not counted.

### BEFORE (v1, origin/develop) — 6 points

| # | Point | Where (v1) |
|---|---|---|
| 1 | Pre-push CI preflight (ruff/mypy/pytest) | `pre-push-ci-gate.sh` step 1 |
| 2 | Pre-push branch policy (develop-only pushable; 4-pattern name validator incl. `hotfix/`, `feature/v…` regex) | `push_gate_decision` step 1 |
| 3 | Pre-push range-scoped denylist scan (two-shape range derivation) | `push_gate_decision` step 2 |
| 4 | Pre-push security-verdict requirement (APPROVED handoff, `metrics.commit_sha` == pushed develop tip) | `push_gate_decision` step 3 (FR-W1-02/DP-5) |
| 5 | CI `pr-source-guard` — one rule (`main` accepts PR only from `develop`) | `ci.yml` |
| 6 | CI `verdict-gate` — dual-approval (qa + security) `workflow_dispatch` closure gate | `ci.yml` + `check-verdict.sh` |

### AFTER (this branch) — 6 points

| # | Point | Where (file:line) |
|---|---|---|
| 1 | Pre-push CI preflight (now + `lint-imports`, FR6 parity) | `dadaia_workspace/public/scripts/pre-push-ci-gate.sh:105` |
| 2 | Pre-push branch policy, inverted: `feature/{M.m.p}` only pushable; 3 patterns, no `v`, no `hotfix`; remote-side refspec policed; fail-closed stdin parse | `features/chokepoints/service.py:117-121` (patterns), `:672-700` (policy), `:658-668` (fail-closed) |
| 3 | Pre-push range-scoped denylist scan — now the **last** policy step; **one** range/exclusion formula | `features/chokepoints/service.py:705-710`; `infrastructure/git_objects.py:122-149` |
| 4 | CI `pr-source-guard` — **two** rules, **one** job (`main`←`develop`; `develop`←`feature/{M.m.p}`) | `.github/workflows/ci.yml:437-471` |
| 5 | CI `security-verdict-gate` — APPROVED security verdict covering the PR head sha, from committed evidence | `.github/workflows/ci.yml:503-520`; `.github/scripts/pr-verdict-check.sh` |
| 6 | CI `verdict-gate` — dual-approval closure gate, **pre-existing, unchanged** | `.github/workflows/ci.yml:533-545`; `.github/scripts/check-verdict.sh` |

### The arithmetic

- **Gross points: 6 → 6.** One point relocated: the security verdict left the pre-push
  hook (v1 point 4) and re-materialized as CI point 5. This relocation is not drift — it
  is G6, a ratified operator decision this SPEC consumes. AR-2's named risk was ending
  with **both** halves alive; that did not happen (§2.1).
- **Hook policy steps: 4 → 3.** `push_gate_decision`'s docstring states "There is no
  third step" (`service.py:644-646`) and the code has none.
- **Enforced-rule inventory: net −2.** Deleted: (a) the push-time per-sha verdict
  freshness rule; (b) the `hotfix/{M.m.p}` pattern row and its PATCH-mint validator;
  (c) the `feature/v…` regex — the contradiction I1 documented is gone (A3.2); (d) the
  two-shape range derivation (a rule-shaped branch, §3). Added: (a) the PR-head coverage
  predicate (the relocation, not an addition); (b) the `develop`-edge PR-source rule —
  genuinely new, but it exists only because v2's topology created a PR edge that had no
  prior equivalent; it is the CI-side counterpart of the hook's branch policy, which
  cannot see a PR.
- **Branch patterns: 4 → 3.** **Range-derivation shapes: 2 → 1.** **Verdict-reading
  production enforcement paths: 2 → 2** (v1: push gate + closure gate; v2: PR gate +
  closure gate — no growth).

---

## 2. Dual-path rulings — each candidate, explicitly

### 2.1 Hook remnant of the verdict check — **NONE. A3.4/A4.5 hold.**

- `push_gate_decision` (`service.py:621-717`) contains no verdict read and no disabled
  flag — the check is **deleted**, not dark-launched. The module docstring names the
  deletion (`service.py:17-21`).
- Grep over the tree: `iter_security_approvals` has exactly **one** production caller —
  `cli/commands/ci.py:399`, the `gc-push-verdicts --dry-run` listing. It survives
  explicitly and only as the GC read side (§2.4); it gates nothing.
- The installed hook script runs exactly two steps — preflight, then
  `ci push-gate-check` (`pre-push-ci-gate.sh:104-108`); no handoff path appears in it.
- The deletion is **pinned by a contract test**:
  `tests/contract/test_ci_v2_gitflow_pr_gate.py:116-125` fails if
  `iter_security_approvals` re-enters `push_gate_decision`'s body.

**Ruling: no dual path. Nothing to delete.**

### 2.2 Two CI verdict jobs (`security-verdict-gate` vs `verdict-gate`) — **NOT a dual path.**

Same word ("verdict"), different rules, and AR-2's criterion is *same rule enforced in
two places*:

| Axis | `security-verdict-gate` | `verdict-gate` |
|---|---|---|
| Trigger | automatic, every PR → develop/main (`ci.yml:506`) | `workflow_dispatch` only in practice (no-ops on push/PR: `.dadaia/handoff/` is gitignored, `check-verdict.sh:56-59`) |
| Predicate | security only; sha-coverage: `metrics.commit_sha` is the PR head **or an ancestor with a verdicts-only diff** (`pr-verdict-check.sh:86-108`) | qa **and** security; `release_id`/context match, no sha at all (`check-verdict.sh:99-107`) |
| Evidence channel | committed `specs/releases/<id>/verdicts/*.handoff.json` | dispatched sidecar paths / local handoff dir |
| Constitutional moment | every PR merge | release CLOSURE ceremony |

No predicate is a subset of the other executed at the same moment on the same evidence.
`verdict-gate` is also the **only** mechanical check of the qa-engineer verdict —
deleting it would drop coverage, which D4's own rule ("coverage is moved, never
dropped") forbids. The `ci.yml:473-479` comment states this distinctness for AR-2;
the code matches the comment.

**Ruling: distinct mechanisms, not a dual path. Nothing to delete.** One observation
for PM intake (not an S1 action): `verdict-gate`'s security half is now the weaker
sibling of a stronger automatic gate; a later release should decide whether it sheds
that half or re-points at the committed-verdicts channel. Distinct today; watch it.

### 2.3 Two verdict scripts (`pr-verdict-check.sh` vs `check-verdict.sh`) — **NOT a dual path.**

They implement the two distinct jobs of §2.2 — they do not even read the same key set
(`metrics.commit_sha` + git ancestry vs `release_id` + context). The shared handoff
qualification (agent == `security-reviewer`, verdict == `APPROVED`, non-empty
`metrics.commit_sha`) is declared once in `service.py::iter_security_approvals` and
`pr-verdict-check.sh:28-32` names itself a second **reader** of that one schema — a
reader of one schema is not a second enforcement of one rule.

**Ruling: distinct mechanisms. Nothing to delete.**

### 2.4 `dadaia ci gc-push-verdicts` (re-keyed, D5) — **bookkeeping, not an enforcement point.**

`cli/commands/ci.py:358-419` + `service.py::gc_consumed_push_verdicts`: runs strictly
after a confirmed merge, **always exits 0**, deletes consumed handoffs after appending a
ledger line. It cannot refuse anything; the D5 re-key (develop tip → merged PR head sha)
is a semantic change inside one existing path. Not counted on either side of §1.

### 2.5 The branch pattern in two syntaxes — **derived copy, not a second source; keep it pinned.**

`_FEATURE_RE` (`service.py:119`) is the declared one pattern source (A3.2);
`ci.yml:459-465` carries its POSIX-ERE translation with a cross-reference comment
(POSIX ERE has no `\d` — a literal share is impossible across the runtime boundary).
Two runtimes enforcing the same law at two different boundaries (local push vs PR) is
the topology, not a duplication. This is, however, the one seam where drift could
re-enter; the contract test suite for the CI workflow must keep pinning both sides.

### D4 (`lint-skill-collisions.py` retirement) — **out of S1 scope, pending.**

D4/FR9 belongs to S2. At S1's close the script still stands and no second enforcer of
its invariants exists yet, so no dual path exists *today*; I will re-check the
one-enforcer property when ruling on S2 artifacts if dispatched.

---

## 3. Bug-surface direction (standing order — ledger evidence)

Ledger (`specs/bugs/bugs.jsonl`), prior bugs on the push-scan surface:
`pre-push-gate-cannot-locate-workspace-venv`,
`prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound`,
`push-gate-refuses-its-own-privacy-baseline-fixtures`,
`prepush-gate-omits-import-boundary-contracts-ci-runs` (resolved in S1, FR6),
`new-branch-push-loses-prior-published-denylist-amnesty` (resolved in S1).

**The change REDUCED the bug surface of the push-scan feature.** Evidence:

1. **The verdict push path is deleted, verified in code** (§2.1). The entire per-push
   verdict-freshness coupling — the hook reading `.dadaia/handoff/` at push time — is
   gone from the hook. That class of failure (stale/missing handoff blocking a push it
   should not, or vice versa) can no longer occur at the hook.
2. **The two-shape range derivation is deleted, verified in code.**
   `git_objects.py:122-149` (`_base_exclusions`): one exclusion formula — `--remotes`
   always, plus `remote_sha` when it resolves — with the module docstring stating
   "There is no branch left choosing between" the two shapes. This is the standing
   order executed literally: the amnesty bug was **caused by** a two-code-path
   structure (resolvable base vs fallback, with the prior-text anchor lacking the
   fallback entirely); the fix removed the branch instead of patching the fallback.
   Anti-puxadinho by deletion, not addition.
3. **The preflight gained parity, not surface**: `lint-imports` is one command in an
   existing list (`pre-push-ci-gate.sh:104-105`), closing the local-green/CI-red import
   class the ledger records (FR6).
4. **Honest accounting of new surface**: `pr-verdict-check.sh` is ~120 lines of new
   bash (git ancestry + jq + coverage semantics) — a new, smaller-but-nonzero surface
   where the hook's four historical bug classes (runner resolution, local venv,
   perf-bound preflight, push-time handoff freshness) structurally cannot recur.
   One finding on it below.

### Findings

**[MEDIUM] Verdicts-path coverage exemption is path-based, not content-based**
Location: `.github/scripts/pr-verdict-check.sh:96`
Issue: the coverage predicate exempts every changed path matching
`specs/releases/*/verdicts/*` from "unreviewed change since the reviewed sha" — any
file placed under a `verdicts/` directory after the review (not only a qualifying
`*.handoff.json`) rides the exemption unreviewed to the PR head.
Why it matters: the exemption exists because evidence can never be inside the commit it
reviews — but its glob is wider than the evidence class, opening a narrow unreviewed
lane through the only automatic security gate.
Trade-off if fixed: narrowing the glob to `specs/releases/*/verdicts/*.handoff.json`
costs one line and closes the lane; residual risk (a hostile handoff-named file) remains
but is then bounded to the evidence class itself.
Recommendation: narrow the exemption glob to `*.handoff.json`; route to
security-reviewer with the S1 delta. Not a dual path and not an A3.4/A4.5 blocker.

**[LOW] Verdict qualification predicate duplicated inside one file**
Location: `features/chokepoints/service.py:340-349` vs `:922-926`
Issue: `iter_security_approvals` and `gc_consumed_push_verdicts` each restate
agent/verdict/`metrics.commit_sha` qualification inline.
Why it matters: same-file, same-feature — cosmetic today; a future edit to one site is
the classic drift seed.
Trade-off if fixed: one extracted `_qualifies(data) -> str | None` helper; trivial cost.
Recommendation: extract when the file is next touched. Not an enforcement dual path
(GC cannot refuse anything).

---

## 4. Gates and verdict

- **Root-cause gate: PASS.** Both S1 bug fixes on this surface address structure
  (branch deleted; check list unified), not symptoms — §3 items 2–3.
- **Architecture-fidelity gate: PASS.** FR3/FR4/A3.4/A4.5 as written in the SPEC match
  the code exactly: right boundary (local publication policy at the hook, review
  authority at the PR), no leaked abstraction, the SPEC's "no dual path survives" is
  true on disk and test-pinned.

**AR-2 verdict: ENFORCEMENT-SURFACE SHRUNK.** Gross points 6 → 6 with exactly one
G6-ratified relocation; hook 4 → 3 policy steps; enforced-rule inventory net −2; branch
patterns 4 → 3; range-derivation shapes 2 → 1; dual paths found: **zero**; deletions
demanded: **none**. The AR-2 failure mode — a hook remnant coexisting with the CI job —
did not materialize, and a contract test keeps it that way.
