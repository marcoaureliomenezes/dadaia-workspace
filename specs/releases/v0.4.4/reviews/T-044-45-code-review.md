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
