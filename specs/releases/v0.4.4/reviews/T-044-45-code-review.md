# Six-axis code review — v0.4.4 release delta (T-044-45)

**Release:** v0.4.4 · **Task:** T-044-45 · **Reviewer role:** code-reviewer ·
**Date:** 2026-08-24

---

## Verdict: REQUEST_CHANGES

One **HIGH** finding (F-1). Per T-044-45's own contract a HIGH blocks the task, so the
marker stays `[-]` and `rc-1` (T-044-52) does not open until F-1 is closed and this
review is re-run.

Everything else the release set out to do, it did, and did in the shape the standing
order asks for: the two headline mechanisms (the chokepoint inversion, the `ctx_inject`
trim) are **deletions**, not additions — a whole policy step and a whole constant leave
the codebase with no replacement branch, flag or second code path. Eight of eleven
touched features reduce their bug surface with ledger evidence. The single feature that
grows outside the sanctioned `S4` additive budget is F-1, and it grows in exactly the
direction the operator's standing order forbids: a new destructive reach-in across a
boundary the ledger has already burned once.

**Scope reviewed:** `git diff f5cce371..HEAD` — 162 files, +13 528/−5 452, ~80 commits.
`HEAD` = `b530a3fd`; its only delta from the measured commit `dc393506` (T-044-44) is the
one-line T-044-45 marker flip, so T-044-44's measurements carry unchanged.

---

## CI status

No PR is open — `rc-1` is T-044-52, still `[ ]`. The gates were re-run independently at
`HEAD` for this review:

| Gate | Result |
|---|---|
| `dadaia ci preflight --quick` | **PASS** — `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest (no e2e)`, all 5 green |
| `dadaia specs doctor` | **0 errors**, 4 warnings (all pre-existing: 2 legacy `_archive` release-dir names, 2 legacy audit dispositions) |
| `dadaia backlog doctor` | **clean** |
| `dadaia public doctor` | `[ok] public-privacy`, `[ok] entities-derivation` (9↔9), `[ok] model-resolution`; one `[foreign]` operator file, expected |

**Environment note, not a diff defect (see INFO-11):** this working copy has **no
pre-push hook installed** — `.git/hooks/` holds only `.sample` files and
`core.hooksPath` is unset. FR3's inverted chokepoint therefore will not fire on
T-044-52's push unless `dadaia ci install-hook` is run first. The release's headline
mechanism would otherwise ship having never executed on the path it governs.

---

## Findings

### F-1 · Architecture · **HIGH** · `dadaia_workspace/features/spec_context/service.py:352`

**An associated repo slug is validated only against its own context's main repo, so one
context can register — and then destroy — another context's working tree.**

`add_repo` refuses exactly one collision: `if slug == ctx.repo_slug`. It never consults
the registry. `create --associated` (`cli/commands/context.py:243`) applies the same
single check. Nothing anywhere compares the slug against the other contexts' repos, and
`AssociatedRepo` maps directly onto `repos/<slug>` — the namespace every context shares.

Reproduced on the executed path against a throwaway states dir (live registry untouched):

```
create ctx-a (main repo-a); create ctx-b (main repo-b)
add_repo("ctx-a", slug="repo-b", url=<any>)  -> ACCEPTED, added=True
ctx-a.all_repos() -> [repo-a, repo-b]
```

`dead("ctx-a")` then walks that same set (`service.py:854` `repo_paths = [... for repo in
ctx.all_repos()]`) and, in Phase 2, for **every** entry: `commit_all(...)` if dirty →
`push(...)` if a remote exists → `shutil.rmtree(repo_path, ...)`. So a single mistyped
slug makes `dadaia context dead ctx-a` auto-commit another context's uncommitted work,
push it to that repo's remote, and delete its checkout — while that context may be ALIVE
and another session may be working in it.

Phase 1's preflight is not a backstop: it refuses only on *untracked* files, so a
tracked-but-dirty foreign tree sails through, and `--commit` waives even that.

This is the class the ledger already carries (`dadaia context alive` committing foreign
dirty work) and the class the standing order names directly — no feature reaches into
another's internals, no shared mutable state across features. The `repos/` namespace is
shared mutable state and FR17 reaches into it without a registry check.

**Fix direction:** widen the guard already in `add_repo` from "this context's main slug"
to "any slug registered by any context" (`store.list_all()` × `all_repos()`), refusing
with the existing `AssociatedRepoConflictError`. That is one predicate at one seam —
`create --associated` already routes through `add_repo`, so it inherits the fix with no
second code path. Do not add a check inside `dead()`: that would be the puxadinho, a
second guard on the destructive side of a boundary that should never have been crossable.

---

### F-2 · Security · **MEDIUM** · `.github/scripts/pr-verdict-check.sh:92-102, 44-60`

**The relocated verdict gate has two fail-open shapes. Route to T-044-46.**

1. **The coverage check fails open.** The "nothing but verdict evidence landed since the
   review" test reads `$(git diff --name-only "$sha" "$PR_HEAD_SHA")` from inside a
   heredoc. A command substitution that fails inside a heredoc does not trip
   `set -euo pipefail`: the heredoc is simply empty, `offenders` stays empty, and the
   verdict is ruled to cover the head. Any condition that makes that `git diff` fail
   silently converts "prove nothing unreviewed landed" into "assume nothing did".
2. **`RELEASE_ID` is unvalidated and attacker-influenceable.** It is read from the PR
   head's own `specs/releases/ACTIVE.md` (`:52`) and interpolated straight into
   `VERDICTS_DIR="specs/releases/${RELEASE_ID}/verdicts"` (`:60`). Only whitespace is
   stripped; no release-id canon is enforced, so the value carries traversal shape into
   a path the gate then trusts.

Both compound AR-2's own recorded open MEDIUM — the exemption at `:96` is **path**-based,
not content-based, so anything at all may land under `specs/releases/*/verdicts/` after
the review and still be ruled "pure evidence".

**Fix direction:** capture the diff into a variable and check its exit status explicitly
before interpreting an empty result; constrain `RELEASE_ID` against the release-id canon
before it reaches a path.

---

### F-3 · Dead code · **MEDIUM** · `.github/workflows/ci.yml:3,453,466` · `.github/scripts/pr-verdict-check.sh:17`

**The stale-section-citation bug this release fixed is still live in `.github/`.**

FR1 inserted Gitflow as `DADAIA.md` **§4**; §5 is now "Where things are written". Four
sites still cite §5 for the branch contract, two of them inside user-facing `::error::`
messages a blocked PR author reads:

- `ci.yml:453` — `Gitflow law (DADAIA.md §5): main accepts PRs from 'develop' only.`
- `ci.yml:466` — `Gitflow law (DADAIA.md §5): develop accepts PRs from 'feature/{M.m.p}' only`
- `ci.yml:3` — the header comment
- `pr-verdict-check.sh:17` — cites §5 for a "review artifact committed on the branch"
  cadence §5 does not describe

The production code got this right: `features/chokepoints/service.py` says §4 throughout.
The bug `t044-04-renumber-stale-DADAIAmd-section-citations` was resolved in this same
release — but its RED census was scoped to `dadaia_workspace/public/`, so `.github/`
was never examined. The surface it looked at closed; the class did not.

**Fix direction:** apply that bug's own structural remedy — title-anchor these four
citations (e.g. "§4 Gitflow") so a future renumbering cannot silently break them again.

---

### F-4 · Tests · **MEDIUM** · `dadaia_workspace/features/migrate/state_v3.py:124-126`

**The atomic-writer battery this release built does not cover the atomic writer this
release added.**

`test_migration_symlink_hardening.py:311` declares its inclusion criterion as a source
census — `grep ^def _*atomic / ^def _*write.*atomic`, "exactly 8 hits". `state_v3`
performs its `tmp → os.replace` **inline**, with no named helper, so it is structurally
invisible to that census. Same for `state_v2.py:166`, `presence`/`session_identity`
excepted (those do have named helpers and are covered). The battery is a census of named
helpers; the S5 close reports it as covering "all 8 writers", which is true of helpers and
not of atomic-write call sites.

The concrete consequence: `tmp = ctx_file.with_suffix(".tmp")` is a **fixed, predictable**
name written via `Path.write_text`, which follows a symlink planted at that path — the
CWE-59 class S5 spent T-044-40 hardening at the resolver seam. The 8 covered writers use
`mkstemp`/uuid and do not have this shape.

**Fix direction:** make the census criterion "atomic-write call site", not "function
matching a name pattern", and let the existing battery parametrize over the widened set —
or fold `state_v3` into the consolidation the S5 close already routed to intake (§4.2).
Adding a bespoke test for `state_v3` alone would re-create the 2-of-8 selectivity the
retired guard was deleted for.

---

### F-5 · Dead code · **MEDIUM** · `dadaia_workspace/features/academy/knowledge_basis/07_codex/03_skills_plugins_and_mcp.md:19,33,34,36`

**Shipped academy content still teaches two skills FR11 fused out of existence.**

Its "Skills in dadaia" section lists `ai-harness-codex` and `harness-primitives` as live,
its frontmatter example is `name: ai-harness-codex`, and it instructs `ai-engineer` to
"use `ai-harness-codex` when changing Codex-facing agents". All four were fused into
`dd-ai-eng-knowhow`; the on-disk inventory is 21 skills and neither name is among them.

A21.10 does not reach this — it is scoped to `public/**`, and this file lives under
`features/academy/`. That is precisely why it survived FR27's sweep: the citation check
enforces a surface, and this is the sediment sitting just outside it. Every other
retired-name hit in the tree is a *historical* citation that names the thing as retired
(correct); this one is a live instruction.

**Fix direction:** repoint the three prose references and the frontmatter example at
`dd-ai-eng-knowhow`.

---

### F-6 · Tests · **MEDIUM** · `tests/integration/test_cli_context_repo_verbs.py`

**FR17's only CLI coverage is undeclared, and therefore SCAFFOLD-by-default — scheduled
to expire at the closure this release is walking into.**

Precise census of the 22 new test files: 18 `Intent: CONTRACT`, 3 `Intent: REGRESSION`,
1 with no `Intent:` line at all — the FR17 file. `dadaia-test-stewardship` §A: "An
**undeclared test is SCAFFOLD** — the default is to die, not to stay."

Separately, `REGRESSION` is not one of the four taxonomy kinds (CONTRACT / SENTINEL /
SCAFFOLD / QUARANTINE) and is not one of the two forms this release's own standing rule
permits (`Intent: CONTRACT — v0.4.4 <A-id>` or `Intent: SENTINEL — <seam>`). The three
new files using it are all bug-pinning regressions, which the taxonomy calls CONTRACT
("Asserts an AC or a bug fix"). Repo-wide the off-taxonomy kinds now stand at 8
`REGRESSION` + 3 `BUG` against 128 `CONTRACT` — a drift this release added to rather
than closed.

**Fix direction:** declare `Intent: CONTRACT — v0.4.4 A17.1–A17.3` on the FR17 file and
re-label the three `REGRESSION` declarations as CONTRACT with their bug ids.

---

### F-7 · Dead code · **LOW** · `dadaia_workspace/features/chokepoints/service.py:670,703`

The rewritten `push_gate_decision` still calls its branch-policy ref list `review_refs`,
and the comment at `:703` positions the denylist scan relative to a review step that no
longer exists ("Runs after branch policy … this is now the LAST policy step"). The name
is the only surviving trace of the deleted concept. Rename to `branch_policy_refs`.

### F-8 · Dead code · **LOW** · `dadaia_workspace/features/spec_context/service.py` (`alive`)

`alive()` reads `self._store.get(name)` into `ctx`, then reads it again into `ctx_latest`
on the next statement, with the same not-found raise. `ctx_latest` earned its name when
it was read *later*, after the state checks; the FR16 clone loop moved it to the top and
the name now means nothing. Collapse to one read.

### F-9 · Performance · **LOW** · `dadaia_workspace/cli/commands/context.py` (`list_all`)

`context list --json` now calls `repos_live_status` per context — 2 git subprocesses per
on-disk repo (`is_git_root`, `current_branch`) where it previously issued **zero** and
read the stored snapshot. This is the correct trade: A18.3 collapsing the two disagreeing
seams into one is exactly what killed `context-list-current-branch-stale-for-alive-repo`,
and correctness beats a stale field. It is invisible today — measured ~1.23–1.33 s for 11
contexts against a ~1.23–1.45 s bare CLI-startup baseline, i.e. inside the noise. Recorded
because the cost is O(contexts × repos) on a hot read path agents call routinely, and
associated repos multiply the second factor. No action now.

### F-10 · Patterns · **LOW** · `dadaia_workspace/features/migrate/state_v3.py:111`

The backup step documents itself as copying the v2 file "verbatim / byte-for-byte" (A15.1)
but uses `read_text`/`write_text`, which apply universal-newline translation. On Windows
an LF-terminated registry backs up as CRLF. Either pass `newline=""` on both sides or
soften the docstring to the LF-canonical contract the rest of the package declares.

### F-11 · Security · **MEDIUM** · registered as a bug, not a defect of this diff

`dadaia bugs append` writes with `json.dumps(..., ensure_ascii=False)` while
`iter_events` reads with `text.splitlines()`. `splitlines()` terminates on U+2028/U+2029/
U+0085/U+000B/U+000C, none of which `json.dumps` escapes. A free-text field containing one
splits the appended record into two unparseable fragments, both skipped with a WARN — the
event is silently absent from `bugs status`/`stats` after the CLI has already printed
`[ok] appended`. Verified against the store's exact serialisation.

Record forgery is **not** reachable (the `"` and `}` needed to close the object are
escaped), so the impact is silent event loss and ledger corruption, not a forged verdict.
Writer and reader are both untouched by v0.4.4; FR23 widens the exposed field set from one
free-text evidence field to four, which is how this surfaced. Registered as
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM).

---

## The six axes

### 1. Architecture — boundaries held, with one breach

`lint-imports` is green and the layer rules of A21.2 hold: nothing in the delta has
`features/**` importing `cli`, `infrastructure` or `hooks`. Two semantic improvements the
linter cannot see:

- `cli/commands/context.py` **stopped** reaching into `container` from inside a display
  helper (the old `_ctx_to_dict` did `from dadaia_workspace import container` inline to
  build a git client). Git access now goes through `SpecContextService.repos_live_status`.
  A CLI-layer infrastructure reach-in was deleted, not relocated.
- The one-accessor discipline (A15.3) is real, not decorative: `all_repos()` is the single
  definition of "this context's repos" and the lifecycle, the display verbs, export and
  the panel all resolve through it. `RepoLiveStatus` is one result shape with one
  producer.

The breach is F-1: `all_repos()` is honoured as the accessor, but the *namespace* it
resolves into (`repos/<slug>`) is shared across every context and FR17 writes into it
without asking the registry who else is there.

### 2. Patterns — consistent with the repo's idioms

Deferred `typer` import, injected seams (`push_gate_decision` still takes every I/O port
as a parameter; `GitObjectReader` never becomes a direct subprocess), event-sourced ledger
append-only with redaction extended to all three new fields, advisory presence untouched.
`state_v3` mirrors `state_v2` statement for statement — replicating the sibling idiom is
the right call even though that idiom carries F-4 and F-10; diverging would have been
worse. The `context repo` sub-typer follows the existing `specs release`/`specs segment`
nesting.

One pattern worth calling out as exemplary: `json_context_store` tolerates a v2 file on
read rather than hard-refusing it, and the docstring names *why* — a version gate with no
reachable repair path is the `memory-agent-tier-migration-deadlock` CRITICAL class. That
is bug-history-oriented design reasoning written into the code, which is what the standing
order asks for.

### 3. Tests — pyramid sane, two stewardship defects

22 new test files, ~180 new test functions, one deleted file
(`test_push_gate_decision.py` — the v1 verdict-in-push-gate coverage, replaced by
`test_push_branch_policy.py` + `test_iter_security_approvals.py`, deleted under a QA
verdict per A4.5, which is the sanctioned route). Tiering is sound: contract tests for the
map enforcer and CI hygiene, integration for CLI verbs and scripts, unit for the decision
functions. Zero new `tests/e2e/**`; `tests/e2e` is net **−38** lines.

No tombstones and no vacuous greens found in the new files sampled at the risk
concentrations. The battery at `test_migration_symlink_hardening.py` deserves specific
credit for the opposite of vacuity: its first run surfaced a real production gap and the
gap was **registered as a bug and pinned as current behaviour** rather than asserted away,
with the pinning test written to self-destruct in the fix direction.

Defects: F-6 (one undeclared file, three off-taxonomy declarations) and F-4 (the census
criterion misses the writer S4 added).

### 4. Security — quick pass, three items for T-044-46

Handed to `security-reviewer` with F-2 (both fail-open shapes plus AR-2's path-based
exemption), F-4's predictable, symlink-followable tmp name, and F-11's ledger corruption.

On the **verdict-step deletion**: I confirmed there is no coverage hole *by construction*
— `push_gate_decision` contains no verdict read and no disabled remnant, and
`iter_security_approvals` survives with exactly one caller, `ci.py:399`
(`gc-push-verdicts`). The hole is not in the code, it is in the **window**: A4.4's advisory
period means `rc-1`'s PR is gated by a job that cannot yet be required. That is disclosed
and time-boxed, not a defect.

On **FR23's evidence fields as an injection surface into JSONL**: not an injection surface.
Values are serialised through `json.dumps`, which escapes every newline and quote, and all
three fields pass through `redact()`. The only reachable harm is F-11's corruption, which
predates the release.

On the **branch-deletion sweep**: nothing in the diff; verified independently by S5 QA
against per-branch `archive/<name>` tags.

### 5. Performance — no regression that matters

`ctx_inject` shrank (−28/+15) and lost a ~20-line constant from every emission path, so
the hook path is strictly cheaper. `pre_gate` is untouched by this delta. Suite runtime is
unchanged in kind — the preflight ran green in one pass. The only new O(N) loop is F-9's,
measured and inside startup noise. The `dead()` and `alive()` loops are O(repos in one
context), bounded by the registry.

### 6. Dead code — three leftovers, all named

F-3 (stale citations), F-5 (academy teaching retired skills), F-7/F-8 (vestigial names).
Everything else checks out: `lint-skill-collisions.py` is gone with its `DECLARED_OVERLAPS`
table, `dd-release-closure` has zero references, and every other retired-skill hit in the
tree is a historical citation that correctly names the thing as retired.

---

## Bug-surface delta, per touched feature

Required form under the operator's standing order. Ledger at `HEAD`: **481 events, 458
resolved, 6 open**; 27 bug ids appear in this release's `specs/bugs/` delta.

| # | Feature | Delta | Evidence |
|---|---|---|---|
| 1 | gitflow / chokepoints | **REDUCED** | `push_gate_decision` +75/−112; an entire policy step deleted with no replacement branch; `handoff_root` param removed; branch patterns 4→3, `hotfix` row deleted outright. AR-2 measures enforced-rule inventory **net −2**. Resolved: `prepush-gate-omits-import-boundary-contracts-ci-runs`, `new-branch-push-loses-prior-published-denylist-amnesty`. Residual: F-7 (naming only). |
| 2 | CI verdict gate | **UNCHANGED, new edge** | Gross enforcement points 6→6 (AR-2): the point relocated, it did not multiply. But the new carrier is a 120-line shell script with two fail-open shapes (F-2) and a path-based exemption, replacing a typed, unit-tested Python predicate. Net-neutral in count, riskier in kind. |
| 3 | rules→skills map / enforcer | **REDUCED** | Two enforcers → one: `lint-skill-collisions.py` retired *with* its hard-coded table (D4/D10), coverage moved not dropped. Resolved: `skill-orphan-checker-misses-disable-model-invocation`, `test-public-pipeline-stale-skill-roster`, `test-public-assets-stale-grill-me-name`. |
| 4 | skills surface | **REDUCED** | 25 → 21 skills (A21.11 holds, verified on disk); AI-surface **net −943** lines; four harness skills fused into one. Residual: F-5. |
| 5 | law projection | **REDUCED, class not closed** | Resolved: `dadaia-md-projected-twice-into-claude-code-context` (law now loads once per harness), `t044-04-renumber-stale-DADAIAmd-section-citations` (44 citations title-anchored). But that fix censused `public/**` only — F-3 shows the same class alive in `.github/`. The surface closed; the class did not. |
| 6 | `ctx_inject` | **REDUCED** | −28/+15: one constant, three call sites, zero branches added. The cleanest instance of the standing order's shape in the whole delta. |
| 7 | spec-context model + alive/dead + CLI + surfaces | **INCREASED** | The sanctioned additive segment (R-2/A21.4): +45 core, +248 service, +267 CLI, +126 migration. Genuine structural win inside it — `context-list-current-branch-stale-for-alive-repo` resolved by collapsing two branch-resolution seams into one, making the disagreement impossible rather than refreshing the divergent path. **But** `add_repo`/`dead()` opens a new destructive cross-context path no prior bug covers (F-1), on a feature the ledger already burned once. This increase is **not** absorbed by S4's budget. |
| 8 | backlog doctor | **REDUCED** | Silent-drop/first-wins path closed at the one owning parser seam (`document.py` +52/−20), `doctor.py` untouched. Resolved: `backlog-doctor-silent-on-duplicate-top-level-sections`, `backlog-doctor-rejects-deferred-status-documented-by-skill`. Architect Firing 1: SOUND. |
| 9 | atomic writers / migration | **REDUCED, with residual** | A brittle 2-of-8 text-equality comparator with four documented failure modes deleted **at root**, replaced by a 32-item behavioural battery; the gap it found was registered, not asserted away. Architect Firing 2: SOUND. Residual: F-4 — the census criterion misses the ninth call site S4 added. |
| 10 | bugs CLI / FR23 | **REDUCED** | The v0.1.73 blanket ≥20-char free-text floor is **deleted**, not stacked on: three independently checkable fields replace it, one validation on the existing append path, no second command, no bypass flag, refusal naming exactly what is missing. Redaction extended to all three. Newly registered: F-11, which FR23 widens the exposure of without causing. |
| 11 | branch hygiene | **REDUCED** | G8 sweep: slop branches tagged `archive/<name>` then deleted; independently re-verified by S5 QA. No code surface. |

**Overall:** REDUCED on 8 of 11, sanctioned-INCREASED on 1, UNCHANGED-with-new-edge on 1,
REDUCED-with-residual on 1. This release genuinely shrinks the thing it set out to shrink —
production net **−130** (−813 excluding sanctioned S4), AI-surface net **−943**, one
enforcer where there were two, one branch-resolution seam where there were two, one
resolution-evidence gate where there was a floor that 132 events cleared by saying nothing.

The one exception is F-1, and it is the exception the standing order exists for: a new
feature reaching across a boundary into shared mutable state, on a surface whose ledger
already records the same class of harm. Closing it is one predicate at one seam.

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 1 (F-1) |
| MEDIUM | 5 (F-2, F-3, F-4, F-5, F-6) + F-11 registered as a bug |
| LOW | 4 (F-7, F-8, F-9, F-10) |
| INFO | 1 (INFO-11, hooks not installed in this working copy) |

**Actionable before `rc-1`:** F-1 (blocking). F-2 to `security-reviewer` at T-044-46.
**Record-only / PM intake:** F-9, F-10, INFO-11, and the F-4 consolidation, which the S5
close already routed.

---

## Recommendation: **REQUEST_CHANGES**

`T-044-45` stays `[-]`. Re-run this review after F-1 lands.

**Self-scan:** this artifact was written to carry no home-absolute path, no email
literal, no IP and no hostname — every path in it is repo-relative — so
`pytest tests/integration/test_repo_self_scan.py` stays green on the `specs/` strict-zero
scope. Checked by inspection before commit.

---

# Re-review — 2026-08-24

Re-run after the four fix commits `1f50dbdf`, `f0a1ac0b`, `76d9db9b`, `beb7bc8c` (plus
`8ff359ee`, the F-1 bug registration). Each fix was verified against its finding by
reading the diff and re-executing the original repro, not by reading the commit message.

## Verdict: REQUEST_CHANGES

**Five of six findings are closed, several better than the fix direction I gave.** The
sixth, F-1, is closed **at the seam I named and not as a class** — and the release's own
architect proved that during the FR23 fifth firing, registering
`context-create-accepts-slug-owned-by-another-context` (**HIGH, open**). I reproduced it
at `HEAD`. The destructive invariant F-1 exists to protect is still violable by a
one-command path, so the verdict cannot be APPROVED.

This is not a new goalpost. It is F-1's own structural claim, unmet: `repos/<slug>` is a
namespace every context shares, `dead()` destroys every entry in `all_repos()` with no
ownership check, and **two** methods write into that namespace, not one.

## Per-finding disposition

| # | Severity | Disposition | Verification |
|---|---|---|---|
| **F-1** | HIGH | **PARTIALLY CLOSED — still blocking** | `add_repo` seam fixed and proven; mirror seam `create` still open (F-12 below) |
| **F-2** | MEDIUM | **CLOSED** | Both halves independently proven, incl. a pre-fix/post-fix differential |
| **F-3** | MEDIUM | **CLOSED** | 5 sites title-anchored (one more than I found) |
| **F-4** | MEDIUM | **CLOSED** | Writer normalised onto the sibling idiom; 9th battery case; census self-enforcing |
| **F-5** | MEDIUM | **CLOSED** | Swept wider than the finding — 2 files, 8 retired names |
| **F-6** | MEDIUM | **CLOSED** (blocking half) | FR17 file now declares `Intent: CONTRACT — A17.1, A17.2, A17.3` |
| F-7 / F-8 / F-10 | LOW | Unchanged, correctly deferred | Non-blocking by design |
| F-9 / F-11 / INFO-11 | LOW / INFO | Unchanged; F-11 registered as a bug | Record-only |

### F-1 — the seam closed, the class did not

`1f50dbdf` implements exactly the direction I gave: one predicate, `_foreign_slug_owner`,
consulting `store.list_all()` at the existing `add_repo` seam, raising the existing
`AssociatedRepoConflictError`, with the message naming the owning context; `create
--associated` inherits it verbatim; no guard added inside `dead()`. Re-running my
original repro against `HEAD`:

| Case | Result |
|---|---|
| Another context's **main** slug (my original repro) | **REFUSED** — `AssociatedRepoConflictError`, names the owner |
| Another context's **associated** slug | **REFUSED** — same error, names the owner |
| Own main slug (A17.3 no-regression) | **REFUSED** — original message intact |
| Genuinely unowned slug | **ACCEPTED** — no over-refusal |
| Idempotent re-add of own associated slug | `added=False` — A17.1 intact |

That is a clean, correctly-scoped fix. The problem is the claim it rests on. The new
docstring states that `add_repo` "is the one seam that writes into that shared namespace,
so it is the one seam that must keep the assumption true". `create` is the other one, and
it checks only for a context-**name** collision (`service.py:289-304`). Reproduced at
`HEAD` against a throwaway states dir:

```
create ctx-a --repo repo-shared          -> ok
add_repo(ctx-b, "repo-shared")           -> REFUSED   (F-1 fixed)
create ctx-c --repo repo-shared          -> ACCEPTED  (mirror seam open)
   ctx-a.all_repos() -> [repo-shared]
   ctx-c.all_repos() -> [repo-shared]
```

`dead("ctx-c")` then walks `all_repos()` and runs `commit_all` → `push` → `shutil.rmtree`
on `repos/repo-shared`, which is **ctx-a's main working tree**. Identical blast radius to
the original F-1, reached by a shorter path — a single `context create`, no associated
repo involved at all.

### F-12 · Architecture · **HIGH** · `dadaia_workspace/features/spec_context/service.py:289`

**`create` admits a main repo slug already owned by another context.** The release's own
architect found this during the FR23 fifth-firing mirror-gap check and registered it as
`context-create-accepts-slug-owned-by-another-context` (HIGH, open). Confirmed
independently above.

**Fix direction:** call the predicate that already exists —
`self._foreign_slug_owner(name, repo_slug)` — in `create`, before `self._store.save(ctx)`,
raising the same error type with the same owner-naming message. `_foreign_slug_owner`
skips `other.name == name`, and no context named `name` exists yet at that point, so it is
correct at this seam with no change. Then correct the docstring: there are two write seams
into the shared namespace, and both hold the invariant.

That is one call at one seam, and it makes the invariant true rather than locally
enforced — which is what F-1 asked for the first time. The bug's own `notes` also raise
the historical-collision question (a registry that already contains a duplicate, imported
verbatim by the v2→v3 migration); that is a doctor-lane decision and correctly **intake**,
not part of this fix.

### F-2 — closed, with a demonstrated exploit shape

`f0a1ac0b` captures the diff into a variable and checks its exit status before
interpreting it, and pins `RELEASE_ID` to the release-id canon before path interpolation.
I proved both, and proved the first was a **real** fail-open rather than a theoretical one,
by running the pre-fix and post-fix scripts against the identical scenario — a genuine
unreviewed commit between the reviewed sha and the PR head, with a shim making `git diff`
exit non-zero:

| Script | Outcome |
|---|---|
| pre-fix (`f0a1ac0b^`) | `PASS: … APPROVED … covers PR head` — **exit 0**, gate satisfied |
| post-fix (`HEAD`) | `SKIP: … cannot prove nothing unreviewed landed` — **exit 1** |

`RELEASE_ID='../../../etc'` is now refused before it reaches a path; `RELEASE_ID='v0.4.4'`
still flows through to the ordinary refusal. The bash pattern is a faithful restatement of
`core/specs_version.py::RELEASE_SEMVER_RE` (`\d` → `[0-9]`), with the reason for restating
rather than re-deriving written at the site.

### F-3 — closed; one LOW residual elsewhere

All five `.github/` citations now read `DADAIA.md §4 (Gitflow)`, including a fifth site at
`ci.yml:488` I had missed. Title-anchoring means the next renumbering breaks loudly.

Record-only residual, **not** blocking and outside F-3's stated scope: `public/agents/ai-engineer.md:239`
cites `§5` for "its projections are PROTECTED and human-only" — PROTECTED is `§3` and the
re-projection contract is `§8` (The library surface). Same class, different section, in a
file this release touched. Routed to PM intake alongside the other citation residuals.

### F-4 — closed, and closed structurally

`76d9db9b` extracts `state_v3._atomic_write_json`, mirroring `presence._atomic_write_json`
(uuid4-suffixed tmp name, `os.replace`, cleanup on `OSError`). This does three things at
once: it removes the fixed, symlink-followable tmp name (CWE-59); it makes the writer fall
into the name-based census **by construction** rather than by hand-maintenance; and it
collapses two divergent shapes onto one sibling idiom. It is characterised honestly as the
battery's 9th case on all four dimensions rather than asserted clean.
`test_census_covers_every_atomic_writer_def_in_the_package` closes the escape route itself.
Battery re-run: **46 passed**, 9 cases.

Record-only residual: three *inline* `with_suffix(".tmp")` writers remain outside a
name-based census — `state_v2.py:166`, `import_/service.py:135` and `:167`. **None was
added by v0.4.4**, and they belong to the atomic-writer consolidation the S5 close already
routed to intake.

### F-5 — closed, wider than asked

`beb7bc8c` swept `features/academy/knowledge_basis/` for all eight retired/renamed names
and fixed two files (`07_codex/03_skills_plugins_and_mcp.md` plus `EXERCISES.md`, which I
had not found). Zero hits remain for any of the eight.

### F-6 — closed on the blocking half; LOW residual

`tests/integration/test_cli_context_repo_verbs.py` now declares
`Intent: CONTRACT — A17.1, A17.2, A17.3`, so FR17's only CLI coverage is no longer
SCAFFOLD-by-default and will not expire at closure. That was the defect.

Record-only residual: the three new `Intent: REGRESSION` declarations are unchanged
(repo-wide: 129 CONTRACT, 8 REGRESSION, 6 SENTINEL, 3 BUG). Nothing keys off the string —
the tests run and stay — and five of the eight `REGRESSION` labels predate this release.
This is a vocabulary decision for the stewardship skill's owner (absorb `REGRESSION`/`BUG`
as declared kinds, or relabel the eleven files), not a code fix, and it does not block.

## Regression check at HEAD

| Gate | Result |
|---|---|
| `dadaia ci preflight` (**full**, incl. e2e) | **PASS** — `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest`, 5/5 |
| `dadaia specs doctor` | **0 errors**, 4 warnings (the same 4 pre-existing legacy rows) |
| `dadaia backlog doctor` | **clean** |
| `dadaia public doctor` | 207 `[ok]`; only `[foreign]` operator-owned files, expected |
| `pytest tests/integration/test_repo_self_scan.py` | **5 passed** |
| Working tree | clean; `T-044-45` marker `[-]`, unflipped |

Nothing regressed. The two behavioural fixes were each proven against their own pre-fix
state, not merely observed green.

## Bug-surface delta of the fix round

Open bugs **6 → 8**: `bug-event-field-with-unicode-line-separator-silently-drops-the-event`
(F-11, MEDIUM, registered by this review) and
`context-create-accepts-slug-owned-by-another-context` (F-12, HIGH). A rising open count is
the correct signal here, not a regression — both are pre-existing defects that were
invisible before, and the second was found by the release's own architect ruling applying
a mirror-gap check to the first fix. That is the standing order working.

Per-feature, the fix round moves two rows of the round-one table:

| Feature | Round 1 | Now | Why |
|---|---|---|---|
| CI verdict gate | UNCHANGED, new edge | **REDUCED** | The relocated gate now fails **closed** on both shapes it previously failed open on, with the fail-open proven against the pre-fix script. It is strictly stronger than the pre-push check it replaced. |
| spec-context model + alive/dead + CLI | INCREASED | **INCREASED (unchanged)** | One of the two write seams into the shared `repos/<slug>` namespace now holds the invariant; the other does not. The surface shrinks only when F-12 lands. |

`atomic writers / migration` improves within its REDUCED row: the ninth writer joined the
battery and the census became self-enforcing, so the specific escape mechanism is closed
rather than the specific escapee.

The release's overall direction is unchanged and good — production and AI-surface both net
negative, one enforcer where there were two, one branch-resolution seam where there were
two, and now one atomic-writer idiom where there were two. F-12 is the last structural
hole, and it is one call to a predicate that already exists.

## Recommendation: **REQUEST_CHANGES**

`T-044-45` stays `[-]`. One HIGH open: **F-12**. Re-run this review after it lands; every
other finding is closed and will not need re-verifying.

**Self-scan:** this section carries no home-absolute path, no email literal, no IP and no
hostname — every path is repo-relative. Checked by inspection, and
`pytest tests/integration/test_repo_self_scan.py` re-run green with the file staged.

### Addendum — the F-12 fix is in flight, uncommitted

While this re-review was being written, an F-12 fix appeared **uncommitted** in the
working tree (`features/spec_context/service.py`, `tests/unit/features/spec_context/test_repo_verbs.py`,
`tests/integration/test_cli_context_repo_verbs.py`). It is exactly the direction given
above: `_foreign_slug_owner(name, repo_slug)` called in `create` before `save`, the same
error type carrying the same owner-naming message, and `_foreign_slug_owner`'s docstring
corrected from "`add_repo` is the one seam" to "`create` and `add_repo` are the TWO seams".

Verified against the working tree: `create` with another context's **main** slug and with
another context's **associated** slug are both refused; a free slug is still accepted (no
over-refusal); the targeted suite (`tests/unit/features/spec_context/` +
`tests/integration/test_cli_context_repo_verbs.py`) is **183 passed**.

This does **not** change the verdict. An approval cites the commit it reviewed, and this
work is not committed. Recorded here so the next round is a formality: once it lands with
its bug `resolved` event, re-running F-12's repro and the full preflight is the whole of
the remaining verification.

---

# Final verdict — 2026-08-24

Third and last pass, against `ed5d64cd` (`fix(bugs): create applies the ownership
predicate at the second registry seam`), the tree clean.

## Verdict: APPROVED

Zero CRITICAL, zero HIGH. Every finding of this review is closed; the residuals are LOW
or record-only and are named below so nothing rides to closure unstated.

`ed5d64cd` is byte-for-byte the fix I verified in the working tree during the re-review,
plus the docstring correction: `_foreign_slug_owner` now reads "`create` (the main
`--repo` slug) and `add_repo` (associated slugs) are the **TWO** seams that write into
that shared namespace, so both consult this predicate". The claim and the code finally
agree.

### F-12 — closed at both seams

Re-ran the repro against the committed tree:

| Seam | Case | Result |
|---|---|---|
| `create` | another context's **main** slug (the F-12 repro) | **REFUSED** |
| `create` | another context's **associated** slug | **REFUSED** |
| `create` | a free slug | ACCEPTED — no over-refusal |
| `add_repo` | another context's main slug | **REFUSED** — F-1 unregressed |
| `add_repo` | own main slug (A17.3) | **REFUSED** |
| `add_repo` | a free slug, then re-added | ACCEPTED, then `added=False` — A17.1 intact |

Final registry state carries no slug owned twice.

### Why this closes the *class*, not another surface

The whole arc of F-1 → F-12 was a fix that closed the seam it was pointed at while its
own docstring asserted a completeness it did not have. So the closing check is
completeness, not another repro. Every store write in `SpecContextService`:

| Line | Write | Can it introduce a slug? |
|---|---|---|
| 325 | `create` → `save` | **Yes** (`repo_slug=repo_slug`, line 319) — **guarded** |
| 443 | `add_repo` → `update` | **Yes** (`AssociatedRepo(slug=slug, …)`, line 441) — **guarded** |
| 352 | `update_url` → `update` | No — copies `ctx.repo_slug` / `ctx.associated_repos` |
| 474 | `remove_repo` → `update` | No — filters the tuple only |
| 716 | `alive` → `update` | No — copies `ctx_fresh.*` |
| 960 | `dead` → `update` | No — copies `ctx.*` |

Exactly two sites can introduce a slug from an argument, and both now consult the one
predicate. The other four carry an existing slug forward and are structurally incapable
of violating the invariant. There is no third seam to find — the invariant is enforced
where it can be broken and nowhere else, which is the shape the standing order asks for:
one predicate, at the seams that own the write, never a guard bolted onto `dead()`'s
destructive side.

## Gate state at `ed5d64cd`

| Gate | Result |
|---|---|
| `dadaia ci preflight` (**full**, incl. e2e) | **PASS** — `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest`, 5/5 |
| `dadaia specs doctor` | **0 errors**, 4 warnings (the same 4 pre-existing legacy rows) |
| `dadaia backlog doctor` | **clean** |
| `dadaia public doctor` | 207 `[ok]`; only `[foreign]` operator-owned files |
| `pytest tests/integration/test_repo_self_scan.py` | **5 passed** |
| Open bugs | **7** — zero HIGH, zero CRITICAL |
| Working tree | clean |

`context-create-accepts-slug-owned-by-another-context` carries a `resolved` event with all
three FR23 fields populated and checkable (red-loop command, `service.py:create` seam,
`net-positive: +31/-7` — routed to the architect as FR23 requires).

## Findings ledger — final state

| # | Severity | Final disposition |
|---|---|---|
| F-1 | HIGH | **CLOSED** (`1f50dbdf` + `ed5d64cd`) — closed as a class, per the seam census above |
| F-2 | MEDIUM | **CLOSED** (`f0a1ac0b`) — fail-open proven real against the pre-fix script, then closed |
| F-3 | MEDIUM | **CLOSED** (`f0a1ac0b`) — 5 sites title-anchored |
| F-4 | MEDIUM | **CLOSED** (`76d9db9b`) — writer normalised, 9th battery case, census self-enforcing |
| F-5 | MEDIUM | **CLOSED** (`beb7bc8c`) — 2 files, 8 retired names, zero hits |
| F-6 | MEDIUM | **CLOSED** (`76d9db9b`) — FR17 coverage no longer SCAFFOLD-by-default |
| F-12 | HIGH | **CLOSED** (`ed5d64cd`) — verified above |
| F-7, F-8, F-10 | LOW | Open, non-blocking — cosmetic naming/wording, no behaviour |
| F-9 | LOW | Open, record-only — measured inside CLI-startup noise |
| F-11 | MEDIUM | Registered as a bug — pre-existing, not a defect of this diff |
| INFO-11 | INFO | Pre-push hook not installed in this working copy — see below |

### Carried to PM intake (record-only, none blocking)

- `public/agents/ai-engineer.md:239` cites `§5` for content in `§8` — the F-3 class, a
  different section, in `public/**`.
- Three inline `.tmp` writers outside the name-based census (`state_v2.py:166`,
  `import_/service.py:135` and `:167`) — none added by v0.4.4; belongs to the
  atomic-writer consolidation the `S5` close already routed.
- Eleven off-taxonomy `Intent:` declarations repo-wide (8 `REGRESSION`, 3 `BUG`) — a
  vocabulary decision for the stewardship skill's owner, not a code fix.
- F-7 / F-8 / F-10's naming and wording residuals.

### One operational item before `rc-1`

`INFO-11` stands: this working copy has **no pre-push hook installed** (`.git/hooks/`
holds only `.sample` files, `core.hooksPath` unset). FR3's inverted chokepoint is the
release's headline mechanism and T-044-52's push is the first chance to exercise it on
its own executed path. Run `dadaia ci install-hook` before that push.

## Bug-surface delta — final

Open bugs across the three passes: **6 → 8 → 7**. Two pre-existing defects were made
visible (F-11's ledger corruption, F-12's mirror seam), one of which was found by the
release's own architect applying a mirror-gap check to the first fix, and closed within
the release. That is the standing order working end to end: a fix was challenged for
completeness, the challenge found a real hole, and the hole was closed at the owning seam
rather than papered over.

Two rows of the round-one per-feature table move, and neither moves by accident:

| Feature | Round 1 | Final | Why |
|---|---|---|---|
| CI verdict gate | UNCHANGED, new edge | **REDUCED** | Fails closed on both shapes it previously failed open on, with the fail-open demonstrated against the pre-fix script. Strictly stronger than the pre-push check it replaced. |
| spec-context model + alive/dead + CLI | INCREASED | **INCREASED (sanctioned only)** | The destructive cross-context path is gone at every seam that can create it. What remains is the `S4` additive budget R-2/A21.4 already sanctions — no unaccounted growth. |

Final tally across the eleven touched features: **REDUCED on 10**, sanctioned-INCREASED
on 1 (`S4`). Production net **−130** (−813 excluding `S4`), AI-surface net **−943**, skills
25 → 21. One enforcer where there were two, one branch-resolution seam where there were
two, one atomic-writer idiom where there were two, one resolution-evidence gate where
there was a floor that 132 events cleared by saying nothing — and one ownership predicate
guarding both writes into the shared repo namespace.

The release does what it set out to do, and the diff is smaller than what it replaced.

## Recommendation: **APPROVED**

Commit reviewed: **`ed5d64cd`**, on `feature/0.4.4`, base `f5cce371`.
Evidence: this artifact (`specs/releases/v0.4.4/reviews/T-044-45-code-review.md`), the
five `qa-engineer` segment closes and the `software-architect` rulings alongside it, and
the gate output recorded above.

`T-044-45` → `[x]`. T-044-46 (security review + the QA release verdict) is unblocked;
F-2's closed fail-open shapes and F-11 are named inputs for it.

**Self-scan:** no home-absolute path, no email literal, no IP, no hostname — every path
repo-relative. Verified by inspection and by re-running
`pytest tests/integration/test_repo_self_scan.py` with the file staged.
