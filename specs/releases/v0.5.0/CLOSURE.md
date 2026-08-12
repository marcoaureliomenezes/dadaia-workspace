# Closure: Release — v0.5.0

> **Status:** Aprovado
> **Release ID:** v0.5.0
> **Owner:** product-engineer
> **Closed:** 2026-08-12
> **Branch:** `feature/v0.5.0` (44 commits, `dad5afd8..HEAD`)

## Summary

v0.5.0 makes the workspace's written law and its code the same thing. `DADAIA.md` §3 has
always promised three rungs for answering "which Spec Context is this?" — the
environment, your own session binding, the repo you are standing in. The tree carried
**five** independent ladder implementations, none of which was that law, and a marker
subsystem that had grown to 132 occurrences across 18 files to bridge the gaps between
them. There is now exactly one function, `core.specs_resolver.resolve_context()`, whose
docstring *is* the law, and every consumer — the CLI seam, the composition root, the SDD
gate and the context-injection hook — calls it. The marker subsystem, the
`DADAIA_SESSION_ID` resolution channel, the dead `DADAIA_AGENT_RUNTIME` alias, the
hardcoded self-hosting slug, the env pop/restore workaround and the `cwd/specs` fallback
are gone with it. Resolution now reads one environment variable: `DADAIA_CONTEXT`.

The release also made a permanently-unsatisfiable diagnostic satisfiable. `dadaia specs
doctor` flagged one historical row in the append-only bug ledger that no legal action
could ever clear — a gate demanding what its own tooling refused. The rule now lives in
the domain model: a violation is reported only while no later compensating `reported`
event exists for the same bug, which is a compensation the append-only store already
accepts. Two legal appends healed the row, and `dadaia specs doctor` exits 0 on this
context for the first time. Four LOW security carry-forwards were fixed each at the one
authority that owns the value, a fifth was verified and re-scoped rather than patched,
and all twelve deferred bugs plus all three open backlog entries received a terminal
disposition.

The shape of the change is the point: this was a subtraction. The production package moved
**−194 net lines** while *adding* four hardening validations, a healing rule, a new test
file, an attesting import-surface guard and a named migration — because the demolition
commit alone removed 1,762 lines. Nothing here added a parallel mechanism to make a gate
pass.

## Metrics — the quantified subtraction

| Metric | Before | After | Δ |
|---|---|---|---|
| Context-resolution ladders in the package | 5 (A/B/D/E/F) | **1** (`resolve_context`) | −4 |
| `core/specs_resolver.py` | 369 lines | **202 lines** | −167 (−45%) |
| Marker-subsystem occurrences in `dadaia_workspace/ tests/` | 132 across 18 `.py` files | **0** | −132 |
| Environment variables participating in resolution | 5 | **1** (`DADAIA_CONTEXT`) | −4 |
| Dead env aliases (`DADAIA_AGENT_RUNTIME`, 0 writers) | 1 | 0 | −1 |
| Whole branch (`dad5afd8..HEAD`, 44 commits) | — | — | 62 files, **+4,288 / −2,253** |
| Production package only (`dadaia_workspace/`) | — | — | 27 files, **+744 / −938 = net −194** |
| Largest single commit (marker demolition) | — | — | **−1,762** |
| Suite | 2,072 passed | 2,072 passed | green throughout |
| Import-linter contracts | 9 kept, 0 broken | 9 kept, 0 broken | seam contract rewritten in place |
| `dadaia specs doctor` on this context | 1 permanent ERROR | **0 errors** | first exit-0 ever on this context |

Note on `specs_resolver.py`: it measured 200 lines at T-50-05, the acceptance point. The
F-01 code-review fix (deferring the `typer` import off the hook hot path, plus its
two-line justification comment) landed afterwards and brought it to 202. See *Accepted
deviations*.

## Tasks completed

Per-task final commits are the `feature/v0.5.0` history; the shas below are the ones cited
by the reviews and by this closure.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-50-01 | The single context-resolution authority (additive) | branch history |
| T-50-02 | Re-point all five consumers to the authority | `45e91b75` (+ `77d37aee` UP037 fix) |
| T-50-03 | Re-point ctx_inject: name resolution AND injection trigger | branch history |
| T-50-04 | Delete the competing ladders and the bind-epoch marker subsystem | the −1,762 demolition commit |
| T-50-05 | Delete the workarounds and the dead alias; add the bind warning | branch history |
| T-50-06 | Rewrite the import-linter seam contract | branch history |
| T-50-07 | Amend `DADAIA.md` §3 and re-project the law | branch history |
| T-50-08 | Update the skills and the consumer recipe | branch history |
| T-50-09 | FR2: the healing rule in the domain model | branch history |
| T-50-10 | FR2: compensate the historical row | branch history (ledger appends only) |
| T-50-11 | FR3.1: install-ledger relpath validation at `LedgerEntry` | branch history |
| T-50-12 | FR3.2: control-character escaping in `DoctorLine.render()` | branch history |
| T-50-13 | FR3.3: entities-derivation shape tolerance at the parse seam | branch history |
| T-50-14 | FR3.4: kimi telemetry reader containment + its first test file | branch history |
| T-50-15 | FR3.5: certification re-scope disposition (no code) | this commit |
| T-50-16 | FR4: verify the 12 deferred bugs against current main | verification handoff |
| T-50-17 | FR4: append the compensating ceremony for the obsolete bugs | branch history (ledger appends only) |
| T-50-18 | Memory delta preview (DEFINITION phase, no memory write) | SPEC §5 |
| T-50-19 | QA `alpha-1`: live-instance validation and the SPEC §6 sweep | `77d37aee` (review committed: `ALPHA-1-QA.md`) |
| T-50-20 | Review, security verdict, push, PR, CI green | `4974852e` (code-review APPROVE); **PR: pending merge** |
| T-50-21 | CLOSURE, memory atoms, dispositions, archive | this commit |

**T-50-20 is honestly still `[-]` at close time.** Both verdicts are APPROVE and the
branch is pushed, but the PR is not merged; the marker flips when it is. This is recorded
rather than pre-flipped — see *Drifts → closure-before-merge*.

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Live-instance rung matrix, four mandatory harness/shell profiles | real subprocesses + the installed kimi shims against this instance | **16/16 PASS** — `specs/releases/v0.5.0/ALPHA-1-QA.md` §1 |
| kimi-code profile: injection + gate mode + heartbeat all present under launch-env `DADAIA_CONTEXT` | kimi ctx-inject / pre-gate / post-gate / post-compact shims | P2.1–P2.4 PASS — `ALPHA-1-QA.md` §1 |
| Gate attribution stays path-first | write into `repos/consumer-repo-b/…` with `DADAIA_CONTEXT=dadaia-workspace` | X1 PASS → attributed `consumer-repo-b` |
| Intended widening: no-repo write resolves via rungs 2–3 | MUTATING write outside `repos/`, no `DADAIA_CONTEXT` | X2 PASS |
| Bind warning fires exactly when neither channel can carry the binding | `dadaia context bind` with/without `DADAIA_CONTEXT` | X3 PASS |
| Format + lint | `ruff format --check dadaia_workspace/ tests/`; `ruff check …` | `758 files already formatted`; `All checks passed!` (ruff 0.16.2, after `77d37aee`) |
| Strict types | `mypy --strict dadaia_workspace/` | `Success: no issues found in 261 source files` |
| Import contracts incl. the rewritten seam | `lint-imports --config setup.cfg --no-cache` | `Contracts: 9 kept, 0 broken.` |
| Suite | `pytest -p no:cacheprovider -q` | `2072 passed` (full); `333 passed` on the hooks/core spot-run |
| Workspace health | `dadaia doctor` | `All invariants OK — workspace is healthy.` |
| SDD health, healed ledger | `dadaia specs doctor` | `[ok] overall: 0 error(s), 6 warning(s)` — first exit-0 on this context |
| Projection of the amended law | `dadaia public doctor` | `[ok] public-privacy`, zero drift, four `0444` byte-identical copies |
| Consumer-validation entrypoint, no certify source change | `dadaia certify --json` | **11/11 PASS** (run 1 was a load flake on a contended host; deterministic PASS on immediate retry, no code change between — `ALPHA-1-QA.md` §4) |
| Hook write-path latency after removing the container import | measured pre-gate round trip | **2.25 s → 0.46 s**; pinned by a new attesting import-surface guard test (F-01) |
| Ledger appends only | `git diff specs/bugs/bugs.jsonl` | appended lines only; no row edited, reordered or deleted |
| No certify code change | `git diff dadaia_workspace/features/certification/` | empty for this release (T-50-15 done criterion) |

## Review chronology

Both review arcs opened with a rejection and closed with an approval. That is the system
working, and it is recorded as such rather than smoothed over — each rejection caught a
defect that the "everything is green" path would have shipped.

| Reviewer | First verdict | Finding that blocked | Final verdict |
|---|---|---|---|
| `software-architect` | **REJECT** (round 1) | The kimi coupling: `_adopt_attributed_bind` is a **writer**, not a reader — deleting the markers without a disposition would have left kimi-code with no injection, no bind mode and no heartbeat, *silently*, on a first-class Layer-1 harness | **APPROVE** after SPEC FR1 coupling 2 named the launch-env binding, the bind warning, the teaching updates and the mandatory kimi rung-matrix profile |
| `code-reviewer` (six-axis) | **CHANGES REQUIRED** | **F-01 HIGH** — the unified seam pulled the composition root onto the hook write path (2.25 s per gated tool call). **F-02** — name≠slug confusion at a mapping site. **F-03** — law-section ordering | **APPROVE at `4974852e`** — container import removed from hooks (0.46 s, pinned by an attesting guard test), F-02 and F-03 fixed |
| `qa-engineer` (alpha-1) | **REJECTED** | one `ruff check` violation (UP037) inside this release's own diff, `tests/fixtures/harness_env.py:385` — QA refused to fix outside its write scope | **PASS at `77d37aee`**; the REJECTED verdict and its finding are preserved verbatim in `ALPHA-1-QA.md` §3 as the historical record |
| `security-reviewer` | — | FR3 items 1–4 re-verified fixed at their authority; item 5 re-scoped | **APPROVED** handoff matching the pushed ref sha |

F-01 deserves naming: the release's own consolidation created a real regression, the
six-axis review caught it before merge, and the remedy was subtractive (remove the import,
sanction `hooks` as a direct importer in the seam contract, pin it with a test) rather than
a cache or a lazy-import puxadinho.

## Drifts

### specs-resolver-line-budget

**Description:** SPEC FR1 accepted `core/specs_resolver.py` at **≤ 200 lines**. It measured
exactly 200 at T-50-05, the acceptance point. The later F-01 fix deferred the `typer`
import into `resolve_specs_dir` and carried a two-line comment explaining why, taking the
file to **202**.

**Resolution:** Kept. Reverting a measured 5× hook-latency improvement to recover two lines
would be optimising the metric instead of the product. Recorded as accepted deviation N-3.

**Memory updates:** none — memory states the seam, not its line count.

### memory-write-set-widened-by-one-atom

**Description:** SPEC §5 enumerated six atoms plus the generated catalog.
`specs/memory/product/harness/harness-claude-code.md` was not on that list, but its usage
flow asserted that "the bind-epoch marker is pid-attributed, so a concurrent session's bind
never steals this session's injection" — a claim about a mechanism this release deleted.

**Resolution:** Corrected in the same CLOSURE. Memory is current truth; leaving a false
sentence in an unlisted atom to respect an enumeration would be exactly the drift this
release exists to kill. The rewrite states the real mechanism: Claude Code exposes a native
session id, so the record is this session's own (rung 2) and the trigger is that record's
`bound_at` against this session's sentinel.

**Memory updates:** `specs/memory/product/harness/harness-claude-code.md`.

### closure-before-merge

**Description:** T-50-20's done criterion includes "PR merged". CLOSURE is being written
with both verdicts APPROVE and the branch pushed, but the PR not yet merged.

**Resolution:** The ship record below says **`PR: pending merge`** and stays that way. It is
the honest state at close time; the coordinator does not need to rewrite it. T-50-20's
marker flips to `[x]` on merge, which is also when `dadaia specs doctor`'s SPEC-DOC-024
phase↔markers check (phase `CLOSURE` requires every marker `[x]`) will report clean.

**Memory updates:** none.

### certify-flake-under-host-load

**Description:** `dadaia certify --json` run 1 returned `ok: false`, 10/11, with
`workspace-init-all-harnesses` exceeding its own 180 s internal subprocess timeout on a
host at load average 21–25.

**Resolution:** Deterministic 11/11 PASS on immediate retry with no code change in between —
an environment-load flake, not a regression. It does, however, sharpen the backlog return
below: the 11 checks have no automated test, so a real regression and a load flake are
currently distinguished only by a human re-running the command.

**Memory updates:** none.

## Memory updates

Written during this CLOSURE phase (`ACTIVE.md` phase `CLOSURE`, the memory gate open).
Memory describes the product **as it is now** — one resolution authority, no marker
subsystem, no "we used to attribute by ancestry".

- `specs/memory/product/platform/context-management.md` — new **Resolution** section: the
  single authority and its four-row rung table (0 caller input / 1 `DADAIA_CONTEXT` / 2 own
  live record / 3 cwd's repo), and the statement that `DADAIA_CONTEXT` is the only env var
  that resolves a context. **Binding** rewritten: bind writes exactly one artifact (the
  session record with `bound_at`), prints the loud warning when neither channel can carry
  the binding, and that record's `bound_at` is the sole injection trigger. Runtime-state
  list drops the marker dir and names the injection sentinel.
- `specs/memory/product/sdd/sdd-gate-v3.md` — new **Context Attribution** section: the gate
  holds no ladder of its own, calls the shared authority with the write target as caller
  input (path-first preserved), and falls through the law rungs for an out-of-repo write.
  **Context Injection** restated on `bound_at` vs the sentinel; runtime-state list updated.
- `specs/memory/architecture.md` — new **The resolution seam** subsection: one authority,
  the documented §6 reason `core` keeps its own session-record reader, the
  `bind-resolution-seam-is-a-single-home` contract naming exactly three sanctioned direct
  importers (`cli._specs_resolution`, `container`, `hooks`) with zero ignored imports, and
  the **hooks-never-import-container** law with its attesting guard test. ctx-inject's
  re-arm restated. Runtime-state table drops the marker row; the retired-state paragraph
  names the `remove_legacy_bind_epoch_state` install migration, kept one release.
- `specs/memory/product/philosophy/spec-context-project.md` — **Bind** is the session record
  *plus* `DADAIA_CONTEXT` (a plain shell, or a harness with no session id, carries the
  binding in the env var); **Inject** is `bound_at` vs the sentinel.
- `specs/memory/product/harness/harness-kimi-code.md` — new **Binding** section (required by
  FR1 coupling 2): kimi exposes no session-id env var, so its binding is `DADAIA_CONTEXT`
  exported at harness launch — rung 1 — and all three effects (injection, gate mode,
  heartbeat context) follow from the shared authority. `bind` run inside a kimi shell tool
  prints the warning naming the export to add. No ancestry adoption anywhere.
- `specs/memory/quality-assurance.md` — new **Satisfiable Diagnostics** section, the FR2
  law: every diagnostic must be healable by an action the product accepts; in an
  append-only store the healing action is a compensating event, never an edit; enforcement
  and diagnosis are separate authorities that agree by construction; healing history never
  disables the check.
- `specs/memory/product/harness/harness-claude-code.md` — see drift
  *memory-write-set-widened-by-one-atom*.
- `specs/memory/tech-stack.md` — **no change**, as SPEC §5 predicted and as required to be
  stated explicitly either way: this release moved no dependency, no Python version, no
  harness roster entry, no model policy and no packaging contract.
- `specs/memory/product/index.md` + `specs/memory/product/catalog.json` — **regeneration
  required and pending.** Two atoms' `tldr`/`summary` frontmatter moved
  (`context-management`, `harness-kimi-code`), and both files are generated, never
  hand-edited. The stale generated text is the only remaining false statement under
  `specs/memory/`. `dadaia memory catalog generate` clears it; no atom was added or removed,
  so the CAT-1 slug-set check is unaffected and doctor stays at 0 errors either way.

## Dispositions

### Backlog entries (3)

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/20260806-clean-architecture-remediation.md` | backlog | `CONSUMED — v0.5.0` | frontmatter `disposition:` block; items 1-3+5 by v0.3.0/v0.4.0/constitution §12.4, item 4 by FR1, item 6 by FR4 |
| `specs/backlog/20260806-dadaia-md-workspace-system-prompt.md` | backlog | `CONSUMED — v0.5.0` | frontmatter `disposition:` block; four `0444` byte-identical projections, `public/rules/` retired, PROTECTED gate class live, `[ok] public-privacy`; token deviation N-1 recorded |
| `specs/backlog/20260810-security-low-carryforwards-v030.md` | backlog | `CONSUMED — v0.5.0` | frontmatter `disposition:` block; 4 original + 2 new LOWs dispositioned per FR3 |

### FR3.5 — certification re-scope (verified finding, no code)

Recorded here as its own disposition because it is the one FR3 item that ships **no source
change**, and that is the finding rather than an omission:

- All **11** certify checks are live post-demolition — the 8 workflow checks died with the
  v0.3.0 engine and left **zero dead references** behind. Verified 11/11 green on this
  instance (`ALPHA-1-QA.md` §4).
- Certify is the **consumer-validation entrypoint**: a packaged script referenced by
  `CONSUMER_VALIDATION_RECIPE.md:73` (F-03/F-25) and by the capabilities contract. It is
  not vestigial surface awaiting deletion.
- `git diff dadaia_workspace/features/certification/` is **empty** for this release.
- The one debt this deliberately does **not** fix: those 11 checks have **no automated
  test**. Routed to the backlog as a return (below), not silently absorbed.

### Deferred bugs (12) — all dispositioned, zero rows edited or deleted

Every disposition is an **append** to `specs/bugs/bugs.jsonl` (a `reported` reopen-note
referencing the original stream, then the terminal event). No bug was deleted; the ledger
diff is appends only.

| # | bug_id | Terminal status | Evidence |
|---|---|---|---|
| 1 | `gate-self-blocks-lease-holder-own-session` | `superseded` | v0.1.76 NO-LOCKS — the lease the bug describes no longer exists |
| 2 | `spec-doc-029-false-forgery-harness-uuid-vs-session-record-id` | `superseded` | v0.1.76 NO-LOCKS; SPEC-DOC-029 retired. Re-verified against FR1's **post-deletion** tree, as the SPEC required |
| 3 | `import-linter-contracts-red-but-not-ci-enforced` | `resolved` | premise refuted on main: `.github/workflows/ci.yml:88-92` runs `lint-imports --config setup.cfg --no-cache` |
| 4 | `panel-telemetry-sqlite-corrupts-under-concurrent-access` | **stays `deferred`** | verified **still real** on current main; reason intact, row untouched |
| 5 | `context-dead-nonwritable-guard-rejects-standard-git-objects` | `resolved` | verified fixed on main, with evidence |
| 6 | `context-dead-plain-git-push-fails-mismatched-upstream` | `resolved` | verified fixed on main, with evidence |
| 7 | `memory-heading-allowlist-not-consumer-extensible` | `resolved` | verified fixed on main, with evidence |
| 8 | `lifecycle-release-define-stalls-before-worker` | `superseded` | v0.3.0 demolition — `dadaia_workspace/features/lifecycle/` holds **zero `.py` files** |
| 9 | `codex-lifecycle-timeout-not-enforced-041` | `superseded` | v0.3.0 demolition (same evidence) |
| 10 | `blocked-close-leaves-closure-artifact` | `superseded` | v0.3.0 demolition — the `close` verb it names no longer exists |
| 11 | `backlog-subjects-readme-uses-unsupported-positional-resolve` | `resolved` | verified fixed on main, with evidence |
| 12 | `dadaia-cli-skill-command-drift` | `resolved` | verified fixed on main, with evidence |

**Totals: 5 superseded** (3 by the v0.3.0 demolition, 2 by v0.1.76 NO-LOCKS), **6 resolved
with evidence on main**, **1 still deferred** because it is still real.

### The picked bug

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs-doctor-spec-doc-033-unsatisfiable-on-historical-row` | bug | `resolved` | FR2: the healing rule in `core/models/bugs.py` + two compensating appends against `closure-catalog-references-missing-memory-atom` healing `bugs.jsonl` line 719; `dadaia specs doctor` exits 0 |

### Ledger state at close

**One open bug remains on this context:**
`release-workflow-coverage-file-in-checkout`. It is **owned by a concurrent session** and is
deliberately untouched by this release — not picked, not dispositioned, not commented on.
Recorded here so the ledger's open count is not read as this release's residue.

## Backlog returns

Four items discovered or deliberately deferred during this release. `project-manager`
curates the files themselves; these are the returns this closure hands over.

- `backlog/candidates.md` ← **no chokepoint scans tracked publishable `specs/`
  content against the privacy denylist** (SEC-V050-04, MEDIUM, security push
  verdict). `check_public_privacy` covers only `public/` + the root `AGENTS.md`;
  the `.gitignore` privacy backstop was force-bypassed for the QA review file
  (`gitignore-alpha-qa-review-untrackable`), and the first file admitted through
  the bypass carried a denylisted term — caught only by the human verdict. Pair
  the chokepoint with the gitignore-whitelist fix so admitting a release artifact
  never institutionalizes the bypass.
- `backlog/candidates.md` ← **certify's 11 checks have no automated test.** The
  consumer-validation entrypoint is verified only by running it. A load flake and a real
  regression are currently distinguished by a human re-running the command
  (`ALPHA-1-QA.md` §4). Named in SPEC §4 as explicitly out of scope; returned here so it is
  recorded rather than forgotten.
- `backlog/candidates.md` ← **the `core` duplicate session-record reader.**
  `core/specs_resolver._read_session_record` (`:37-56`) duplicates
  `features/spec_context/session_identity.read_session` because `core` may not import
  `features` (constitution §6, documented exception). After FR1 the single authority is the
  natural home for record-*reading* in `core`, with `features` delegating downward — a real
  unification, and a **named deletion candidate**. It moves a §6 layer boundary, so it
  belongs to its own release, not to a closure edit. Declared in SPEC §4 for exactly this
  reason.
- `backlog/ideas.md` ← **`CHANGELOG.md` has no entry for spec release v0.4.0.** The plugin
  demolition shipped without one; the `[0.5.0] — Unreleased` section covers spec release
  v0.3.0 only, and this release adds its own section. History is never rewritten, so the
  gap is a forward fix (an added section), not an edit — and it is not this release's scope.

## Accepted deviations

Four, each recorded rather than quietly met.

- **N-1 — `DADAIA.md` always-on token count: ~3.5k measured against the ≤3k aspiration.**
  Operator-approved at v0.3.0. Every other acceptance criterion of the
  `dadaia-md-workspace-system-prompt` entry is met and verified live; this one is a stated
  miss, not a silent one.
- **N-2 — the FR1 code grep returns 7, not the literal 0.** In the declared universe
  (`dadaia_workspace/ tests/`) the marker subsystem is gone: 132 → 0 for the deleted
  symbols. Seven mentions of the *string* remain and are all legitimate: **2** are
  deletion-history comments explaining to a future reader why an adoption path is absent
  (`cli/commands/context.py`, `tests/contract/cli/test_cli_context.py`), and **5** belong to
  the new named migration `remove_legacy_bind_epoch_state`, which must name the state it
  sweeps. Deleting either class would remove true information.
- **N-2b — the same shape inside `specs/memory/`.** The done-grep
  `grep -rn "bind_epoch\|_adopt_attributed_bind" specs/memory/` returns **2** lines, both in
  `architecture.md`, both naming the live install migration that sweeps orphan marker state
  in an upgraded workspace. That migration exists in code and is retained for one release,
  so memory naming it is current truth, not narration of a past version. Every other memory
  mention of the marker mechanism is gone. (`catalog.json` also still carries the stale
  generated summary until the catalog is regenerated — see *Memory updates*.)
- **N-3 — `core/specs_resolver.py` is 202 lines against the ≤200 criterion.** 200 at the
  acceptance point; +2 from the F-01 hook-latency fix. See drift
  *specs-resolver-line-budget*.

## Ship record

- **Branch:** `feature/v0.5.0`, 44 commits, `dad5afd8..HEAD`
- **Code review:** APPROVE at `4974852e`
- **QA alpha-1:** PASS at `77d37aee`, committed to the branch as `ALPHA-1-QA.md`
- **Security verdict:** APPROVED, `metrics.commit_sha` equal to the pushed ref sha
- **PR: pending merge**

## Archive decision

**MOVE — deliberately deferred, matching the v0.3.0 and v0.4.0 precedent.**

`specs/_archive/releases/` contains only `.gitkeep`: v0.2.5 through v0.4.0 all still sit in
`specs/releases/`, each with an approved CLOSURE declaring MOVE and deferring the mechanical
step. v0.4.0's CLOSURE states the reason verbatim — archiving is a `git mv` into a FROZEN
path, `product-engineer` has no `Bash`, and it is the operator's ship decision. Following
that precedent exactly beats satisfying the letter of T-50-21 while breaking the pattern of
every release before it.

`specs/releases/ACTIVE.md` therefore stays `release: v0.5.0 / phase: CLOSURE` until the
operator ships and repoints it. **`phase: SHIPPED` is not written**: `SHIPPED` is not in
`CANONICAL_PHASES` (`features/specs/doctor_release.py:30-40`), so writing it would turn
`dadaia specs doctor` red on SPEC-DOC-003 — a closure that breaks the doctor is not a
closure. When the operator ships, the sweep is:

```bash
git mv specs/releases/v0.5.0 specs/_archive/releases/v0.5.0
# then repoint specs/releases/ACTIVE.md at the next release (v0.6.0 is drafted) or `release: none`
```

`specs/releases/v0.2.5`–`v0.4.0` are archived in the same sweep; each of their CLOSUREs
lists the mechanical steps still pending there.
