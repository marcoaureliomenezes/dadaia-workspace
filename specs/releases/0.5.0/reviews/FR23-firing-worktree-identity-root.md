# FR23 firing — `push-gate-own-repo-slug-not-excluded-from-a-git-worktree-outside-repos`

**Release:** 0.5.0 · **Arm:** B (bug, MEDIUM, `surface: cli`) · **Author:** software-architect ·
**Date:** 2026-08-28 (UTC)
**Trigger:** the fix is net-positive on production (`cli/commands/ci.py` +22/−2; test +35) —
a net-positive Arm-B diff routes to the architect before the resolving commit (standing
order; `DADAIA.md` §7).
**Method:** no shell in this session. Read whole at the uncommitted working tree:
`cli/commands/ci.py`, `features/chokepoints/service.py:224-239` (`context_slug_for_path`),
`tests/contract/test_push_gate_wiring.py`, `tests/unit/features/chokepoints/test_pre_commit_decision.py:88-95`,
`core/protocols/git_client.py`, `infrastructure/git_subprocess.py:327-340`,
`container.py:186-213`, `:389-419`, `core/workspace_resolver.py:23-48`,
`public/scripts/pre-push-ci-gate.sh`, `setup.cfg` import-linter contracts, `ARCHITECTURE.md`
P-02/P-07/P-08/P-09 and the "Git chokepoints" section, `bug-history-forensic-100.md` P2/P3,
and the ledger records `BUGS.jsonl:29`, `:389`, `:391`, `:433`, `:470`, `:483`, `:495`, `:499`,
`:517` (the record under review). `git log -p` was not available; lineage is read from the
ledger's `component`/`resolved_commit` fields and the docstrings that cite prior bugs by id.

**Verdict: SOUND.** The fix corrects the *input* of an identity derivation that was fed a
checkout position instead of a repository identity. It is the structural cause, it repeats no
prior fix, and it collapses two cases (main checkout, linked worktree) into one path. One
MEDIUM amendment on a silent git-version dependency and two LOW notes; none blocks the commit.

---

## 0. Problem, constraints, prior art (architect-core-workflow)

**Core problem.** "Which repo is being pushed" must be answered from the repository, not
from where the checkout happens to sit on disk — a linked worktree is the same repository at
a different path.

**Constraints (from the tree).** `features/chokepoints` spawns no subprocess (P-02,
`features-no-subprocess`) and holds no load-time infrastructure edge; every I/O it needs is
injected by the CLI (`ARCHITECTURE.md` "Git chokepoints"). `cli` may not import
`infrastructure` directly (P-08, `cli-no-infrastructure`) but is under no `subprocess`
contract — `_repo_root()` (`ci.py:38-49`) has spawned `git rev-parse --show-toplevel` from
this module since the hook's first version, and the hook script does the same (`pre-push-ci-gate.sh:44`).
`context_slug_for_path` is a pure `Path → str | None` function with its own unit pin
(`test_pre_commit_decision.py:88-95`). Preflight must lint the *worktree's* files.

**Success criteria.** (1) From a linked worktree parked under `.dadaia/tmp/`, the own slug is
subtracted from the foreign set exactly as from the main checkout. (2) The pre-commit
presence probe names the same context from either checkout. (3) Preflight still targets the
worktree. (4) No new flag, branch, allowlist or second code path in the chokepoints feature.

**Assumptions made explicit.** (a) The repository's identity under `<workspace>/repos/` is the
*main* working tree, which is the parent of the git common dir for every non-bare repo with
the default `.git` layout — the layout `dadaia context create` produces. (b) A worktree parked
*outside* the workspace is out of scope: `_resolve_workspace_root(repo_root)` (`ci.py:122-132`)
still walks up from the worktree, and a worktree outside the workspace already loses the
registry-derived layer today (pre-existing, §3 note 2). (c) `git rev-parse --git-common-dir`
exists since git 2.5; `--path-format=absolute` since git 2.31 (§3 F1).

**Prior art.** Three candidate homes for the identity resolution:

| Candidate | Fit | Integration | Verdict |
|---|---|---|---|
| (i) private helper beside `_repo_root` in `ci.py` (the diff) | 100 % — same shape as its twin, called at the two slug sites only | no new import, no new port, no contract touched | **chosen** — the composition point already owns "which git roots do the verbs run against" |
| (ii) `GitClient` port method + `GitSubprocessClient` adapter + `build_git_client()` | 100 % | P-08-clean, but `_repo_root` would then be the odd one out — the honest version of (ii) moves *both* probes, a refactor with no bug behind it | the right home **when the CLI's git probes are next touched**; not for an Arm-B fix |
| (iii) inside `context_slug_for_path` / the chokepoints feature | would need an injected port for one `rev-parse`; breaks the function's pure `Path → slug` contract and its unit pin | P-02 forbids the subprocess; injecting a port adds a parameter to a pure function for a fact the CLI already knows | rejected |

No external library question arises: the fact needed is one git plumbing call.

---

## 1. Structural cause or symptom patch? Lineage.

**Structural.** The record's `root_cause` is accurate and complete: both slug call sites fed
`context_slug_for_path` with `git rev-parse --show-toplevel`, i.e. the checkout's filesystem
position. The function's contract ("a Spec Context repo lives at `<workspace>/repos/<slug>`",
`service.py:227`) was never wrong — it was handed the wrong path. The fix changes the argument
at both sites and leaves the function, its unit pin and the `_foreign_repo_slugs` set algebra
(`ci.py:181-227`) untouched.

**Repetition check — same seam.** The ledger has no prior bug on the own-identity input of
`_foreign_repo_slugs`. The three prior push-gate bugs are all in the *scan*, not the identity:
`push-gate-refuses-its-own-privacy-baseline-fixtures` (`:433`, fixture literals),
`new-branch-push-loses-prior-published-denylist-amnesty` (`:470`, zero-sha base),
`push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-substrings` (`:495`, token bounds,
`net-neutral`). The A3.2 regression the `_foreign_repo_slugs` docstring cites (own slug not
subtracted → every push blocked) was a *review* finding at v0.9.0/v0.11.0, not a ledger bug,
and its fix — subtract both `name` and `repo_slug` — is exactly the mechanism this bug bypassed
by yielding `own_slug = None`. `caused_by: none` is correct.

**Repetition check — same class.** The *class* is not new: "identity derived from a path
interpolation instead of from the authority" is `a1-context-specs-resolution-ignores-repo-slug`
(`:389`, CRITICAL, 28 call sites deriving `repos/<name>`) and `a2-…` (`:391`), and P-09's
rationale ("every context bug this product has had came from a second resolution path"). This
fix does **not** open a second authority: `repos/<repo_slug>` *is* the registry's slug by
construction (`context create` clones to it), and `context_slug_for_path` remains the one
path-derived reading. It corrects the path fed to the one reading; it does not add a registry
lookup beside it. That is the shape the forensic's STRUCTURAL fixes have ("collapse", not
"add").

**Not a puxadinho.** No flag, no allowlist, no special case for `.dadaia/tmp/`, no
worktree-detection branch in the feature. The one conditional added — the
`CalledProcessError`/`FileNotFoundError` fallback to `worktree_root` (`ci.py:67-68`) —
returns exactly the pre-fix behaviour, so a non-git directory degrades to today's path.

**Root-cause gate (§0.1 gate 1): PASS.**

## 2. Placement — does it respect the boundaries?

| Invariant | HEAD (working tree) |
|---|---|
| Features encapsulated; chokepoints spawns no subprocess (P-02) | `features/chokepoints` untouched ✓ |
| CLI composes, never imports infrastructure (P-08) | no new import; `subprocess` was already this module's tool for `_repo_root` ✓ |
| No cross-cutting helper hiding coupling | module-private, two callers, one fact, no state ✓ |
| Preflight lints the worktree | `preflight` still uses `_repo_root()` (`ci.py:84`) ✓; `push_gate_decision(repo=repo_root)` reads objects from the worktree, which shares the common object store ✓ |
| Test exercises the executed path | only `_repo_root` is monkeypatched (`test_push_gate_wiring.py:199`); `_repo_identity_root`, the real object reader and a real `git worktree add` run ✓ |

**Architecture-fidelity gate (§0.1 gate 2): PASS** — the helper's docstring states the
layer fact correctly ("named by the git common dir's parent, never by the worktree's own
filesystem position"), and `_foreign_repo_slugs`'s docstring ("*own_slug* is the pushed repo's
directory name under `repos/`") remains true.

Ruling on the placement question: **(i) is correct for this fix.** (ii) becomes the right
move the day a third git probe appears in `cli/` or `_repo_root` is touched for its own
reason — then both probes move to `GitClient` in one commit and `ci.py` loses its
`subprocess` import entirely (a net deletion). Recorded as a follow-up, not an amendment.

## 3. Findings

### [MEDIUM] `--path-format=absolute` makes the fix silently version-dependent
Location: `dadaia_workspace/cli/commands/ci.py:61`, `:67-68`
Issue: `--path-format` exists since git 2.31 (2021). On an older git the call fails with
`CalledProcessError`, the fallback returns `worktree_root`, and the bug under review recurs
with no message — a fail-open to the defect, indistinguishable from success. `--git-common-dir`
alone (git ≥ 2.5) prints a path that is relative to the *cwd* when it is not absolute;
`(worktree_root / out).resolve().parent` is correct on every git that has the flag at all.
Why it matters: a fallback that reproduces the bug is the "second code path" the standing
order forbids, reachable by environment rather than by input. CI runners and containers pin
old git more often than developer machines.
Trade-off if fixed: −1 flag, +1 `Path` join; the fallback branch stays but is then reachable
only outside a git repo (where `_repo_root` has already refused). Zero new lines net.
Recommendation: drop `--path-format=absolute`; resolve the printed path against
`worktree_root`. Amend before the resolving commit if cheap; otherwise the next touch.

### [LOW] The new test relies on the module-level intent declaration only
Location: `tests/contract/test_push_gate_wiring.py:181-184`
Issue: the two neighbouring tests (`:124`, `:156`) redeclare `Intent: CONTRACT` per function;
the new one opens with `Bug …:` and inherits the module docstring's `Intent: CONTRACT`
(`:3`), which the e2e-scoped checker does not even read for this tier. Not undeclared — but
inconsistent with the file's own convention, and the bug id is the AC this test pins.
Recommendation: first docstring line `Intent: CONTRACT — bug push-gate-own-repo-slug-not-excluded-from-a-git-worktree-outside-repos.`

### [LOW] Residuals outside this fix's scope (pre-existing, recorded so they are not re-found)
1. `install-hook` (`ci.py:388-391`) resolves `root / ".git" / "hooks"` — in a linked worktree
   `.git` is a file, so the verb refuses; hooks live in the common dir and already apply to
   every worktree, so the correct instruction is "install from the main checkout". Not a bug
   in this fix; a docstring line would close it.
2. `_resolve_workspace_root(repo_root)` at all three verbs walks up from the *worktree*. A
   worktree parked outside the workspace finds no `.dadaia/states/` and degrades to the
   worktree itself — the registry layer vanishes silently. Feeding it the identity root
   instead would make both derivations agree on "the repository's workspace". Adopt when (ii)
   in §0 lands, so the identity root is computed once and both facts derive from it.

## 4. Bug-surface direction (FR24 / `dd-bug-registration` §5)

**Touched feature:** the CLI composition point of `features/chokepoints` (pre-commit presence
context + push-gate own-identity). **Feature code touched:** none.

| Axis | Before | After |
|---|---|---|
| Sources of "which repo is this" at the two slug sites | checkout position (wrong for 1 of 2 checkout kinds) | repository identity (right for both) |
| Checkout kinds with distinct behaviour | 2 (main, linked) | 1 |
| Branches/flags/allowlists added in the feature | — | 0 |
| Fallback paths | — | 1, identical to the prior behaviour (and, per F1, reachable by git version until amended) |
| Push-gate ledger lineage (`:433` → `:470` → `:495` → `:517`) | three scan fixes, none on identity | first identity fix; no prior fix repeated or stacked |

**Direction: REDUCED.** The linked-worktree case — the one the workspace's own tooling
recommends for concurrent sessions (`:499`, open, "git worktree per session") — is folded
into the main-checkout path rather than special-cased. With F1 amended the reduction holds
across git versions; without it, the reduction is conditional on git ≥ 2.31.

## 5. Gate record

| Gate | Verdict |
|---|---|
| Root-cause gate | **PASS** — wrong input to a correct derivation corrected at its two call sites; feature untouched; no retry/flag/allowlist |
| Architecture-fidelity gate | **PASS** — chokepoints stays subprocess-free and port-fed; CLI stays the composition point; docstrings describe the executed path |
| Bug-surface axis (FR24) | **REDUCED** — §4 |

## 6. Disposition

**SOUND.** The diff may become the resolving commit as it stands; F1 is the one amendment
worth landing in the same commit (it deletes a flag and a version dependency at zero net
lines). The `resolved` record should carry `diff_direction: net-positive` honestly, with the
note that the executable growth is one 18-line helper and its two call-site arguments — the
rest is docstring. Follow-up for the next CLI git-probe touch: move `_repo_root` and
`_repo_identity_root` together into `GitClient` (§2), and feed `_resolve_workspace_root` the
identity root (§3 note 2). No production code, tests, specs or TASKS touched by this session.
