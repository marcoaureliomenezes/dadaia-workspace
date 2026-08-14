# SPEC — Release v0.9.0 — Push-range denylist scan

**Status:** Aprovado
**Release ID:** v0.9.0
**Owner:** product-engineer
**Opened:** 2026-08-14
**Created:** 2026-08-14
**Branch:** `feature/v0.9.0` (cut from `develop` at `1883b85b`; branch contract: `dadaia-gitflow`)
**Consumes:** the single backlog candidate
`specs/backlog/push-range-denylist-scan.md` (#1, P1), which by grill ADR #5 **absorbs**
`specs/backlog/redact-foreign-context-names-at-qa-authoring.md` (#17) and, by grill ADR #4,
the idea `tag-push-carve-out-reachability`. **No bug is picked into this release** (`dadaia
bugs status`: 0 open) and **no audit is outstanding** (both archived by v0.8.0).
**Grill (mandatory, done):**
`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T130830Z-refine-specs.html`
— ADRs #3, #3b, #4, #5 are binding and settled for this release; they are not re-litigated
here.

---

## 1. Problem and context

Two consecutive releases leaked the same class of private name into pushed history through
the same channel:

| Release | Push | Leak | Caught by | Remediation |
|---|---|---|---|---|
| v0.6.0 | definition push | SPEC named a consumer project | manual security diff review (REJECTED) | cherry-pick + amend history rewrite |
| v0.7.0 | ship push | `ALPHA-1-QA` transcribed a foreign presence record | manual security diff review (REJECTED) | cherry-pick + amend history rewrite |

Nothing mechanical sees the leak. The only privacy scanner in the product,
`check_public_privacy()` (`dadaia_workspace/infrastructure/privacy_check.py:184`), walks
`dadaia_workspace/public/**` plus the library `AGENTS.md` — `specs/**` is outside its roots
by construction. The push gate itself
(`dadaia_workspace/features/chokepoints/service.py:309`) inspects **refs**, never
**content**: branch policy, then a security-verdict lookup keyed on the pushed sha.

Both leaks entered the same way: a diagnostic line naming a foreign Spec Context
(`features/spec_context/doctor.py:325` — `[stale-presence] context '<name>'`, and
`:453`/`:487` for repo coherence) was transcribed verbatim into an authored `specs/`
document, and left through the push.

Per the root-cause doctrine (`specs/memory/quality-assurance.md` — *Root Cause, Always*),
two identical incidents in consecutive releases means the structural fix is owed. This
release closes both ends of the channel: the **exit** (a range-scoped denylist scan at the
push gate) and the **entry** (a redaction posture for diagnostic output at authoring time).

---

## 2. Objective

No push — branch or tag — publishes a new object carrying a private name, and the refusal
that says so is satisfiable without touching already-published history. Complementarily,
the diagnostic output that fed both incidents can be transcribed safely by construction.

Whole-tree scanning is deliberately **not** built: it stays in the audit lane
(`project-auditor` dispatch), mirroring the law's diff-based-push / full-scan-audit split
(`DADAIA.md` §6).

---

## 3. Scope

### FR1 — Range-scoped denylist scan on pushed branch refs

The push gate scans the **new objects the push would publish**, not the working tree and
not history.

For each non-deletion ref line git feeds the pre-push hook
(`<local-ref> <local-sha> <remote-ref> <remote-sha>`, already parsed into `PushRef`,
`service.py:61-83`), the scanned object set is:

| Condition | Object set |
|---|---|
| `remote_sha` non-zero and resolvable locally | `git rev-list --objects <local-sha> --not <remote-sha>` |
| `remote_sha` zero (new ref) or unresolvable | `git rev-list --objects <local-sha> --not --remotes` |
| `local_sha` zero (deletion) | empty — a deletion publishes no object |

**Refinement of ADR #3, recorded deliberately:** the ADR names
`git rev-list --objects origin/develop..develop`. That is exactly the first row above for
the `develop` push, computed from the `remote_sha` git itself supplies on stdin instead of
from the `origin/develop` remote-tracking ref, which may be stale (over-scan) or ahead
(under-scan). The scope — new objects of the pushed range — is unchanged.

Only **blob** entries (an object listed with a path) are scanned. Each blob is decoded as
UTF-8 and matched against the term set of FR3. A match refuses the push before any network
I/O. Blobs are de-duplicated by object sha within one push.

**Acceptance**

- A1.1 A push of a branch ref whose range contains a new blob carrying a denylist term is
  refused, and the process exits non-zero before any network call.
- A1.2 The same term present only in an object **already reachable from `remote_sha`** does
  not refuse the push (the range excludes it).
- A1.3 A deletion ref (zero `local_sha`) is not scanned and is not refused by this FR.
- A1.4 Blobs are scanned once per object sha per push (dedupe asserted on a range where the
  same blob is reachable from two commits).
- A1.5 Unit tests carry `Intent: CONTRACT — v0.9.0 A1.1…A1.4`.

### FR2 — Tag pushes are scan-covered (and stay review-exempt)

`service.py:344` builds `review_refs` by filtering out deletions **and tags before any
policy runs**, so a tag push reaches `Decision(allowed=True, …)` having been inspected by
nothing. Grill ADR #4: tags keep their carve-out from the *security verdict* (law §3
intact, release publication depends on it) but are **covered by the scan**.

The scan therefore runs over a ref set computed independently of `review_refs`: every
non-deletion ref, tag or branch. For a tag the object set is the second row of FR1
(`--not --remotes`).

**Acceptance**

- A2.1 A tag push whose new objects contain a denylist term is refused.
- A2.2 A tag push whose new objects are clean is allowed **with no security verdict** —
  the DP-5 carve-out is preserved exactly (regression test on the existing behavior).
- A2.3 A branch deletion is still allowed with no verdict and no scan.
- A2.4 The scan runs after branch policy and before the security-verdict lookup for branch
  refs; for tag refs it is the only policy that runs.

### FR3 — Term sources, fail-closed, and self-slug exclusion

Three additive term sources, mirroring the fail-closed posture already established by
`check_public_privacy()`:

1. **Operator denylist** (when present) — literal, case-insensitive substring terms loaded
   from `$DADAIA_PRIVACY_DENYLIST` or `<workspace>/.dadaia/states/privacy_denylist.json`
   via the existing loader (`privacy_check.py:125`). Operator-private by design: it is not
   in the repository and never enters it.
2. **Packaged structural baseline** — the versioned patterns already shipped in
   `dadaia_workspace/infrastructure/data/privacy_baseline.json` (IPv4/IPv6 literals,
   internal hostnames, `/home/<user>` absolute paths, emails, secret-looking tokens), with
   their `exclude_regex` carve-outs honored.
3. **Foreign repo slugs** — the directory names under `<workspace>/repos/`, **excluding
   the slug of the repository being pushed**. Matched with a word-boundary regex (not a
   bare substring), so a short slug cannot match inside an unrelated word.

When source 1 is absent (fresh clone, CI, pip install), sources 2 and 3 still run: the scan
is **never a no-op**. The gate names the mode it ran in on stderr, as
`check_public_privacy()` already does with its distinct `[ok]` markers
(`privacy_check.py:68`).

**Acceptance**

- A3.1 With no operator denylist file present, a new blob containing an IPv4 literal or a
  `/home/<user>` path is still refused (baseline layer proven live).
- A3.2 A new blob containing the **pushed repository's own slug** is never refused by the
  slug layer (regression guard: the slug appears in nearly every file of this repo).
- A3.3 A new blob containing a foreign `repos/` slug as a whole word is refused; the same
  slug embedded inside a longer word is not.
- A3.4 The baseline `exclude_regex` carve-outs still apply (loopback/documentation IPs,
  `example.com`, `/home/runner`) — no refusal on those.
- A3.5 The stderr mode line distinguishes "operator denylist + baseline" from
  "baseline only (no operator denylist)".

### FR4 — No amnesty list; the FROZEN↔scan invariant is documented

Per grill ADR #3b there is **no sanctioned-terms list**: a new object carrying a denylisted
term always blocks. The edge case that would have required one — the term already published
in `specs/_archive/releases/v0.7.0/` — is void by construction, and this SPEC is the place
that records why:

> **FROZEN↔scan invariant.** `specs/_archive/` is FROZEN (`DADAIA.md` §3): it is never
> edited, and it is entered only by `git mv`. A rename creates no new blob — git reuses the
> existing blob object. A tainted archived file therefore can never appear as a *new* object
> of any future pushed range, and the already-published term is amnestied by construction
> rather than by exception list. The invariant holds exactly as long as `_archive/` stays
> FROZEN; if a future release ever edits an archived file, the scan will — correctly —
> refuse the push.

**Acceptance**

- A4.1 No file in the delivered implementation contains a sanctioned-terms/allowlist
  structure for denylist terms (grep for an allowlist constant returns nothing).
- A4.2 A test proves the invariant mechanically: a `git mv` of a tainted file into
  `specs/_archive/` produces a range whose scan is clean (no new blob), while an **edit** of
  that same content produces a range whose scan refuses.
- A4.3 This SPEC's invariant paragraph is quoted verbatim in the `sdd-gate-v3` memory atom
  at closure.

### FR5 — The refusal is a satisfiable diagnostic

Per `specs/memory/quality-assurance.md` — *Satisfiable Diagnostics* — every violation must
be healable by an action the product accepts, and the message must name that action.

The refusal names, per offending object:

- the ref being pushed (`<local-ref> → <remote-ref>`);
- the blob path and the 1-based line number of the first match, plus the short object sha;
- the **masked** term — first character, ellipsis, last character — and its source layer
  (operator denylist / baseline pattern id / foreign slug);
- the law it enforces (`DADAIA.md` §7 — private names never enter public/pushed material);
- the sanctioned remediation: edit the file, then rewrite the offending commits
  (`--amend` / interactive rebase / cherry-pick) so no pushed object carries the term, and
  push again — **not** a rewrite of already-published history, which the range scope makes
  unnecessary.

The message **never prints the matched line content and never prints the term unmasked**: a
refusal that echoes the secret defeats its own purpose (CWE-532).

**Acceptance**

- A5.1 The refusal message contains the ref, `path:line`, the short blob sha, the masked
  term and its source layer.
- A5.2 The message contains no substring of the offending source line other than the masked
  term, and the unmasked term does not appear anywhere in stdout or stderr.
- A5.3 The message names the remediation as edit + rewrite-before-push, and does **not**
  instruct the operator to rewrite published history.
- A5.4 At most the first 10 offending objects are listed, followed by a count of the
  remainder — a 500-hit refusal must stay readable.

### FR6 — Fail-closed and fail-open boundaries are explicit

| Situation | Verdict | Rationale |
|---|---|---|
| A term matches | **refuse** | the whole point |
| `git rev-list` / object read fails (not a repo, git missing, non-zero exit) | **refuse**, naming the failure | a policy gate never skips what it cannot evaluate — same posture as the malformed-stdin rule (`service.py:332`) |
| An individual blob is not valid UTF-8 (binary) | **skip that blob**, count it, report the count in the allow/refuse line | undecodable bytes cannot be matched by a text denylist; silence would hide the skip |
| No object source wired into the decision function | **refuse** at the CLI boundary | the CLI always wires one; an unwired production path is a defect, not a bypass |

`git push --no-verify` remains the single traceable bypass, exactly as for the existing
gates. It is named in the refusal message.

**Acceptance**

- A6.1 A simulated `git rev-list` failure refuses the push with a message naming the git
  failure and `--no-verify` as the only sanctioned bypass.
- A6.2 A range containing a binary blob is scanned, the binary blob is skipped, and the
  skip count appears in the gate's output.
- A6.3 The CLI wiring is pinned by a contract test: `push-gate-check` always passes a real
  object source.

### FR7 — Architectural purity and performance budget

`features/chokepoints/service.py` is pure decision logic — its module docstring
(`:1-14`) states it "NEVER imports `infrastructure` and NEVER spawns a subprocess". The scan
needs git object I/O, so it arrives through a **port injected by the CLI**, exactly as
`ProcessAncestry` already does for `pre_commit_decision` (`cli/commands/ci.py:114-138`).
The candidate's phrasing ("wired into `push_gate_decision`") is satisfied by injection, not
by a subprocess call inside the pure module.

Budget: the scan adds **< 2 s** to the gate for a typical release-sized range.

**Acceptance**

- A7.1 `features/chokepoints/**` imports no `infrastructure` module and spawns no
  subprocess (existing import-linter contract + an AST/import-surface test stay green).
- A7.2 The decision function takes the object source as a parameter; unit tests inject
  fakes with no git and no filesystem.
- A7.3 A measured wall-clock figure for the scan over this release's own push range is
  recorded in `CLOSURE.md` and is < 2 s; the measurement command is recorded with it.

### FR8 — Redaction of foreign context names at authoring time (absorbed, ADR #5)

Defence in depth: FR1–FR7 close the exit path; this FR closes the entry path that both
incidents actually used.

1. **A `--redact` output mode** on the operator-facing diagnostic verbs whose output can
   name a Spec Context other than the caller's own:
   - `dadaia doctor` — issue descriptions, including `[stale-presence] context '<name>'`
     (`features/spec_context/doctor.py:325`) and the alive/dead repo coherence lines
     (`:453`, `:487`);
   - `dadaia context list` (table and `--json`);
   - `dadaia context show` (table and `--json`, including the `presence` block).

   With `--redact`, every context name and repo slug **other than the caller's resolved
   context** is replaced by a stable placeholder (`[REDACTED-CONTEXT-1]`,
   `[REDACTED-CONTEXT-2]`, … ordinal by first appearance within one invocation). Default
   output is byte-for-byte unchanged — `--redact` is opt-in.

2. **A doctrine line** in the QA authoring surface (`dadaia_workspace/public/agents/
   qa-engineer.md`): diagnostic output transcribed into any authored document — QA
   evidence, SPEC, CLOSURE, report, handoff — is captured with `--redact` or masked by
   hand; a foreign Spec Context name is never pasted verbatim.

**Acceptance**

- A8.1 `dadaia doctor --redact`, `dadaia context list --redact`, `dadaia context show
  --redact` (with and without `--json`) emit no context name or repo slug other than the
  caller's resolved context.
- A8.2 Without `--redact`, the output of all three verbs is unchanged — pinned by a
  contract test over the existing stable JSON contracts.
- A8.3 The placeholder is stable within one invocation: the same foreign context maps to
  the same ordinal everywhere it appears.
- A8.4 The `--redact` JSON output remains valid JSON with the same key set.
- A8.5 The doctrine line exists in the canonical source
  (`dadaia_workspace/public/agents/qa-engineer.md`) and is present in every projection
  after `dadaia public install --target all`; `dadaia public doctor` reports
  `[ok] public-privacy`.

### FR9 — Evidence of a clean gate

**Acceptance**

- A9.1 An end-to-end journey proves the whole chain on a throwaway git repository: a commit
  carrying a planted term is refused at `pre-push`, and the same repository pushes clean
  after the term is removed and the commit amended.
- A9.2 `dadaia ci preflight` is green (ruff format, ruff check, mypy --strict, pytest)
  before each push, per the branch contract.
- A9.3 Test intents are declared at birth for every test added by this release
  (`Intent: CONTRACT — v0.9.0 <A-id>` or `Intent: SENTINEL — <seam>`); no test lands as
  undeclared SCAFFOLD.
- A9.4 `CLOSURE.md` carries the FR7 timing measurement and the `## Dispositions` table
  flipping the two consumed backlog entries to terminal status.

---

## 4. Out of scope (non-goals)

1. **Whole-tree scanning.** Stays in the audit lane (`project-auditor`), per ADR #3.
2. **Commit-message scanning.** `rev-list --objects` lists commits without a path, and this
   release scans blobs only. A commit message naming a private project is a real residual
   channel — recorded as a backlog return at closure, not built here.
3. **Any rewrite of already-published history.** The range scope exists precisely so this is
   unnecessary; `dispose-published-denylist-term` is already terminal-`rejected` as void by
   construction.
4. **`commit-paths-index-scope-hardening` (candidate #18).** Paired with #9 in the index as
   an Arm-B hardening lane; **no ADR absorbs it into this release**. It stays a candidate
   and is not touched here — this release is strictly the #1 scope plus its two absorbed
   items (#17 and the `tag-push-carve-out-reachability` idea).
5. **`python-env-interpreter-probe-hardening` (candidate #9).** Same lane, not picked.
6. **No change to the pre-push hook script.** `public/scripts/pre-push-ci-gate.sh` already
   forwards stdin to `dadaia ci push-gate-check` (`:111`); the scan lands inside that verb,
   so no already-installed `.git/hooks/pre-push` needs reinstalling.
7. **No new denylist content in the repository.** The operator term list stays
   operator-private, outside the package (`privacy_check.py:47-58`). This release adds no
   private term to any tracked file.
8. **No backlog authoring or curation.** `specs/backlog/**` belongs to `project-manager`;
   see §7.
9. **No relaxation of the security-verdict rule.** Tags stay review-exempt; branches still
   require an APPROVED `security-reviewer` handoff covering the pushed delta.

---

## 5. Memory files affected at closure

| File | Change | When |
|---|---|---|
| `specs/memory/product/sdd/sdd-gate-v3.md` | `## Git Chokepoints` gains the range-scoped denylist scan as current push-boundary truth, the tag posture (review-exempt, scan-covered), the fail-closed/fail-open boundary, and the FROZEN↔scan invariant (FR4/A4.3) | **CLOSURE** |
| `specs/memory/quality-assurance.md` | the redaction-at-authoring posture (FR8) recorded as product truth; the *Satisfiable Diagnostics* section gains the refusal's healing action | **CLOSURE** |
| `specs/memory/product/platform/workspace-doctor.md` | `--redact` output mode as part of doctor's surface | **CLOSURE** |
| `specs/memory/product/platform/context-management.md` | `--redact` on `context list` / `context show` | **CLOSURE** |
| `specs/memory/product/catalog.json` | regenerated only if a touched atom's frontmatter `tldr`/`summary` changes | **CLOSURE** |
| `specs/memory/architecture.md` | the new port + adapter named in the chokepoint subsystem paragraph, if the seam is judged structural at closure | **CLOSURE** |
| `specs/memory/product/index.md`, `tech-stack.md` | no change expected — no feature added or removed, no dependency added (stdlib + git only) | — |

---

## 6. Dependencies and risks

| # | Item | Status |
|---|---|---|
| D1 | The operator privacy denylist file is operator-private and absent from the repo | Accepted by design; FR3 makes the absent case a degraded-but-live scan, never a no-op |
| D2 | `product-engineer` has no shell | Every git step is an explicit TASKS entry owned by the dispatcher / `software-engineer` |
| D3 | The `--redact` FR touches CLI output contracts pinned by existing tests | A8.2 makes "default unchanged" an acceptance criterion, not a hope |
| D4 | PM purge-on-pick of the consumed backlog entries | Pending — see §7 |
| R1 | **False positives block legitimate pushes.** A baseline pattern or a foreign slug fires on innocent new content | Range scope keeps the surface small; slugs are word-boundary matched; baseline `exclude_regex` carve-outs are honored (A3.3, A3.4); `--no-verify` remains the traceable escape |
| R2 | **Self-slug catastrophe.** Matching the pushed repo's own slug would block every push of this repository | A3.2 is a dedicated regression guard |
| R3 | **Performance.** A large range (first push of a new branch with `--not --remotes`) decodes many blobs | Sha-level dedupe, blob-size guard, measured budget A7.3; recorded in CLOSURE |
| R4 | **Architecture drift.** The temptation to call `subprocess` inside the pure module | FR7/A7.1; import-linter + import-surface tests already exist and stay green |
| R5 | **The refusal leaks what it protects.** Echoing the matched line into stderr publishes the term to logs | A5.2 forbids it; masking rule is normative in FR5 |
| R6 | **The scan becomes a silent no-op** in CI or a fresh clone where no operator denylist exists | A3.1/A3.5: baseline + slug layers always run and the mode is stated on stderr |
| R7 | **Fail-open drift.** A future maintainer widens the binary-blob skip into a general exception swallow | FR6 tabulates the boundary; A6.1/A6.2 pin both sides |
| R8 | **The entry path stays open** if `--redact` ships without the doctrine | A8.5 requires the doctrine line in the canonical source and its projections |

---

## 7. Traceability and provenance

| Item | Provenance | Disposition |
|---|---|---|
| `specs/backlog/push-range-denylist-scan.md` (#1) | v0.6.0 + v0.7.0 privacy incidents; renamed 2026-08-14 per ADR #3 | **picked** — this release; terminal `DELIVERED — v0.9.0` at closure |
| `specs/backlog/redact-foreign-context-names-at-qa-authoring.md` (#17) | v0.7.0 CLOSURE return; absorbed per ADR #5 | **absorbed as FR8**; terminal `DELIVERED — v0.9.0` at closure |
| `tag-push-carve-out-reachability` (idea) | v0.7.0 CLOSURE return; absorbed per ADR #4 | **absorbed as FR2**; terminal at closure |
| `dispose-published-denylist-term` | already terminal `rejected` (void by construction) | untouched — FR4 documents why |

**Purge-on-pick (operator-ratified doctrine, grill ADR #14) — delegated and pending.**
The doctrine requires a picked entry to leave the backlog in the same commit that creates
the release SPEC, with provenance recorded here. `specs/backlog/**` is `project-manager`
surface (`DADAIA.md` §2), and `product-engineer` does not curate it. Therefore:

- this section **is** the provenance record the doctrine requires;
- the removal of `push-range-denylist-scan.md` and
  `redact-foreign-context-names-at-qa-authoring.md` from the live backlog, and the
  corresponding LEDGER lines, are **delegated to `project-manager` and pending** at the time
  this SPEC was authored;
- the pending purge is a precondition of T-090-01 (see TASKS), so the definition commit
  carries it if the PM has acted by then, and CLOSURE records it either way.

---

## 8. Approval

**Approved by the operator on 2026-08-14** (via dispatcher). SPEC, PLAN and TASKS all
carry `**Status:** Aprovado`; milestone (a) of the `dadaia-gitflow` contract may fire once
the definition commit (T-090-01) lands.

Ratified with the approval:

- **§4.2 — commit-message scanning stays a non-goal.** The operator explicitly ruled
  *defer to backlog at closure*, exactly as §4.2 records. `rev-list --objects` lists
  commits without a path and this release scans blobs only; a commit message naming a
  private project remains a residual channel, routed to the backlog by T-090-12 and **not**
  built here. No scope change.
- The remaining definition-time refinements stand as written and are not re-litigated:
  the FR1 range computed from the pre-push `remote_sha` (ADR #3 instance), the FR3
  self-slug exclusion with word-boundary slug matching, and the FR7 injected-port
  resolution of the purity constraint.

Still delegated and pending at approval time: the PM's purge-on-pick of the two consumed
backlog entries (§7). It rides the T-090-01 definition commit if performed by then;
CLOSURE records the state either way.
