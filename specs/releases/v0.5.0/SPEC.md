# SPEC — Release v0.5.0 — One context-resolution authority, a healable ledger, hardening at chokepoints

> **Status:** Aprovado

**Release ID:** v0.5.0
**Owner:** product-engineer
**Source:** operator decree, 2026-08-11 — one release consuming the three open backlog
entries and the one open bug. Binding principles named by the operator: simplicity,
bug-surface minimization, **no puxadinhos** (no additive patch where an authority can be
unified or a surface deleted), constitution §12.4 (additive-by-default fixes are rejected).
**Picked set:** `specs/backlog/20260806-clean-architecture-remediation.md` (items 4 + 6),
`specs/backlog/20260806-dadaia-md-workspace-system-prompt.md` (verification + terminal
disposition), `specs/backlog/20260810-security-low-carryforwards-v030.md`, and the open bug
`specs-doctor-spec-doc-033-unsatisfiable-on-historical-row`.

## 1. Problem

**The law is right; the code is five copies of it.** `DADAIA.md` §3 (source:
`dadaia_workspace/public/data/DADAIA.md:103-106`) promises exactly three rungs —
`DADAIA_CONTEXT` → your own session binding → the repo containing the working directory.
The tree carries **five independent ladder implementations**, none of which is that law:

| # | Site | What it actually does |
|---|---|---|
| A | `core/specs_resolver.py:294-321` `resolve_bound_context_name` | explicit → `DADAIA_CONTEXT` → `DADAIA_SESSION_ID` record (**no liveness gate**, `:161-169`) → harness-native-id record (TTL-gated, `:171-179`) → bind-epoch marker ancestry attribution (`:211-291`, ~81 lines of ordered-depth scoring + unordered membership + `getppid()` degradation) |
| B | `cli/_specs_resolution.py:106-158` `resolve_context_for_cli` | duplicate `DADAIA_CONTEXT` rung, a **pop/restore env workaround** (`:141-148`) to stop A re-reading the var it just rejected, then a hardcoded self-hosting-slug rung (`_is_self_hosting_checkout`, `:71`, `:96-103`, `:151-152`) |
| D | `hooks/ctx_inject.py:183-198` `_resolve_context` | a third ladder, with `_newest_qualifying_marker` (`:145-180`) — a **third** marker-attribution algorithm — plus `recorded_slug` sentinel fallbacks (`:444`, `:469`, `:501-506`) |
| E | `hooks/sdd_gate.py:77-96` `_context_slug` | path-first `repos/<slug>` → `DADAIA_CONTEXT`. Two rungs; the closest thing in the tree to the law |
| F | `hooks/sdd_post_gate.py:141` | inside `_adopt_attributed_bind` (`:108-176`): `DADAIA_CONTEXT` or `container.resolve_persisted_bind_context(markers)` — **and it is a writer**, see FR1 coupling 2 |

The audit that produced backlog item 4 measured the growth: `specs_resolver.py` **71 → 369
lines (5.2×)**, one rung per bug; `ctx_inject.py` 3.1× with five env reads. v0.1.77
declared "one resolution path for every verb" and both files kept growing after it. The
bind-epoch marker subsystem measures **132 occurrences across 18 `.py` files** under
`dadaia_workspace/ tests/` — the code universe every acceptance grep below is scoped to.
(A wider grep that also walks prose assets, memory atoms, the bug ledger and
`specs/_archive/` returns 150 across 30 files; the ledger and the archive are never
rewritten, and the prose assets are dispositioned by their own tasks, so they are outside
the code acceptance claim.) This is the exact accretion signature the audit proved:
*deleted surface stops producing bugs; surface added by a fix produces the next bug in
under a day.*

**A diagnostic that no legal action can satisfy.** `dadaia specs doctor` folds
`specs/bugs/bugs.jsonl` row by row through `advance_coherence`
(`features/specs/doctor_governance.py:432-460`). Exactly one historical row — **line 719**,
`closure-catalog-references-missing-memory-atom`, a `resolved` with no prior `reported` —
is flagged forever. The store is append-only, so **no legal append can clear a row-level
flag**: the check is permanently unsatisfiable on this context and violates the v0.1.72 law
*a gate never demands what its tooling refuses*.

**Four LOW findings re-verified across four push verdicts** (shas 8e4ce5e2 → f07bca39 →
153a0722 → 29ab43b8) plus two new LOWs from the 2026-08-11 verdict, all of the same shape:
a value crosses a trust boundary and is validated (or not) at the *call site* rather than at
the *authority* that owns it.

**Twelve deferred bugs**, several naming a subsystem that no longer exists —
`dadaia_workspace/features/lifecycle/` contains **zero `.py` files** after the v0.3.0 engine
demolition — and one (`import-linter-contracts-red-but-not-ci-enforced`) whose premise CI
already refutes (`.github/workflows/ci.yml:88-92` runs `lint-imports --config setup.cfg
--no-cache`). They sit un-dispositioned, overstating the ledger's open debt.

## 2. Objective

Reduce the workspace to **one** context-resolution authority that implements the written
law verbatim, delete every ladder, marker, alias and workaround that competed with it, make
the bug-ledger diagnostic healable by the event-sourced means the store already provides,
move four hardening validations from call sites to the single authority each belongs to,
and give every deferred bug and picked backlog entry a terminal disposition.

Every FR below is subtractive or authority-consolidating. No FR adds a parallel mechanism.

## 3. Scope

### FR1 — One context-resolution authority (critical path)

**The contract.** `core/specs_resolver.py` exposes exactly one resolution function, and
`DADAIA.md` §3 is its docstring:

```
resolve_context(explicit: str | None = None, *, target_path: Path | None = None) -> str | None

  rung 0  caller-supplied input  — the `--context` flag, or the context derived from an
                                   explicit write TARGET under <ws>/repos/<slug>/
  rung 1  DADAIA_CONTEXT
  rung 2  this session's own LIVE session record, keyed by the harness-native session id
          (core.session_env.harness_session_id)
  rung 3  the repo containing the current working directory (<ws>/repos/<slug>/…)
```

Rungs 1–3 are the law's three rungs, in the law's order. Rung 0 is not a fourth rung: it is
the caller's *explicit* input, which the law has always allowed a verb to pass. `target_path`
exists so the SDD gate keeps its **path-first** semantics — a write into `repos/x/` is
attributed to `x` even when `DADAIA_CONTEXT=y`, because the write target *is* explicit
input. Without this parameter the unification would silently invert the gate's attribution;
with it, sites A/B/D/E/F all consume the same function.

**One intended semantic widening, declared.** Today the gate resolves a write that is under
**no** repo through `DADAIA_CONTEXT` **only** (`sdd_gate.py:94-95`, "explicit override
only"); under the unified authority such a write falls through to rungs 2-3 — the session
record, then the cwd's repo. This is **intended**, not incidental: a write outside
`repos/<slug>/` made by a session that is demonstrably bound belongs to that session's
context, and the alternative — pinning the gate to env-only through a parameter — would
re-introduce a per-caller rung table, i.e. the thing this FR deletes. The widening is
proven by test, and it cannot mis-attribute a repo write, because any target under
`repos/<slug>/` is decided at rung 0 before rung 1 is consulted.

Rung 3 subsumes and generalizes two things the tree special-cases today: the gate's
path-first rung (E, `sdd_gate.py:85-93`) and B's hardcoded `"dadaia-workspace"` literal
(`_specs_resolution.py:71`). The self-hosting checkout lives at
`<ws>/repos/dadaia-workspace`, so the general path rule already answers it — the literal was
a special case of the rule, which is the definition of a puxadinho. Rung 3 resolves the
slug, then maps slug → context NAME through the registry (the inverse of the existing
`repo_slug_for_context`, `specs_resolver.py:93-125`), falling back to the slug itself when
unregistered.

**Deleted in the same change** (each is a competing authority, not a feature):

1. The `DADAIA_SESSION_ID` resolution channel (`specs_resolver.py:161-169`) — an
   un-liveness-gated rung the law does not name. `DADAIA_SESSION_ID` survives only where it
   is genuinely a session **identity** for the CLI/hook heartbeat, never as a resolution rung.
2. The **entire bind-epoch marker subsystem**: all three attribution algorithms
   (`specs_resolver._persisted_bind_context` + `_marker_chain`,
   `ctx_inject._newest_qualifying_marker`, `container.resolve_persisted_bind_context`) and
   the writers/readers in `features/spec_context/session_identity.py` (`write_bind_epoch`,
   `iter_bind_epochs`, `read_bind_epoch_pids`, `read_bind_epoch_sid`, plus the now-false
   marker narrative at `:115-123`), **`hooks/sdd_post_gate._adopt_attributed_bind`
   (`:108-176`) and its call site (`:296-305`) — the subsystem's only remaining consumer,
   deleted by name (coupling 2 below)**, `.dadaia/states/bind_epoch/`, and
   `cli/_specs_resolution.current_ancestry_pids`.
3. The pop/restore env workaround (`_specs_resolution.py:141-148`) — it exists only because
   two ladders read the same env var; one ladder deletes its reason to exist.
4. The `cwd/specs` fallback in `resolve_specs_dir` (`specs_resolver.py:351-363`) **and** the
   workspace-root refusal patch bolted onto it — a patch on a fallback the law never
   granted.
5. The dead env alias `DADAIA_AGENT_RUNTIME` (readers: `sdd_gate.py:200`,
   `cli/commands/context.py:519`; **zero writers** anywhere in the tree). `DADAIA_RUNTIME`
   remains.
6. The copy-pasted session-id micro-ladders in `cli/commands/context.py` (`:276`, `:516`,
   `:599`, `:630`) → one helper.
7. The stale docstring claim `cli/_specs_resolution.py:22-23` ("first-ALIVE context"),
   which describes behavior the module does not have.

**Explicitly KEPT** (not resolution rungs; deleting them would be scope creep):
`DADAIA_MODE` (the separate §3 mode law), `DADAIA_RUNTIME` / `DADAIA_HOOK_OUTPUT` /
`DADAIA_HOOK_EVENT` (transport concerns of the codex/kimi hook shims), `WORKSPACE_ROOT`,
and `repo_slug_for_context` (the name→slug registry mapping — orthogonal and correct).

**Couplings this SPEC resolves (each was verified on the tree):**

1. **ctx-inject's injection trigger.** Today the trigger is bind-epoch marker mtime vs the
   session sentinel (`ctx_inject.py:167-180`). New trigger: **the session record's bind
   timestamp vs the sentinel**. This is a replacement, not a new mechanism:
   `dadaia context bind` already writes the session record, and §3 already declares bind
   the sole trigger for context-memory injection. (PLAN Lane A step 3 and T-50-03 pin the
   one intended behavior difference: a same-context re-bind will now re-inject.) The
   `recorded_slug` sentinel fallbacks
   (`:444`, `:469`, `:501-506`) survive unchanged — they are compaction recovery, not
   resolution.
2. **kimi-code binding — `_adopt_attributed_bind` is a WRITER, and it is deleted by name.**
   `hooks/sdd_post_gate.py:108-176` is not "presence attribution that reads a record": it is
   the code that **makes rung 2 true** for a harness with no native session-id env var. Its
   own docstring names the bug (`kimi-ctx-inject-bind-attribution-gap`, `:111-114`):
   kimi-code exposes no session-id env, so `dadaia context bind` run through the kimi shell
   tool keys its record by a **minted** `sess_*` id (`cli/commands/context.py:516-517`), and
   the only bridge from that record to the kimi session's own harness-keyed record is marker
   ancestry attribution (`:141-143`, `:147`). Deleting the markers without a disposition
   would leave kimi with no injection, no bind mode and no heartbeat context — **silently**,
   which is precisely this release's named failure mode landing on a first-class Layer-1
   harness.

   **Disposition (chosen):** for kimi-code the binding is `DADAIA_CONTEXT`, exported at
   harness launch — rung 1 of the law, the same channel every non-harness shell uses. The
   adoption path `_adopt_attributed_bind` is therefore **deleted by name** together with the
   marker subsystem (`sdd_post_gate.py:108-176` and its call site `:296-305`); post-gate
   presence then reads this session's own record via rung 2, which for kimi is written under
   the `DADAIA_CONTEXT` it launched with. Three obligations ride with it, none optional:
   (a) `dadaia context bind` prints a **loud warning** when it can neither key a
   harness-native record nor see `DADAIA_CONTEXT` — "this binding is reachable only if you
   export `DADAIA_CONTEXT=<ctx>`" — so the flow can never fail silently;
   (b) `specs/memory/product/harness/harness-kimi-code.md` and
   `public/data/CONSUMER_VALIDATION_RECIPE.md` teach the launch-env binding;
   (c) **kimi-code joins the live-instance rung matrix** (acceptance below, T-50-19) — the
   Claude/plain-shell/repos-cwd matrix alone cannot detect this regression.

   The same doctrine change also retires `context heartbeat`'s marker-sid path
   (`read_bind_epoch_sid`, bug `context-heartbeat-requires-env-after-persisted-bind`): a
   plain-shell bind without `eval` no longer resolves through a marker. `heartbeat` is named
   explicitly in the teaching updates for that reason.
3. **Plain shells with no harness id.** `dadaia context bind` prints
   `export DADAIA_CONTEXT=<ctx>` guidance (the existing `--print-env` path): for a
   non-harness shell the env var **is** the binding, which is rung 1 of the law. Skills and
   docs are updated to teach that: `public/skills/dadaia-workspace-manager`,
   `public/skills/dadaia-workspace-spec-navigator`, `public/skills/dadaia-cli`, and
   `public/data/CONSUMER_VALIDATION_RECIPE.md:115-120`.
4. **Certification needs no code change.** `features/certification/service.py:82-89` scrubs
   `DADAIA_CONTEXT`/`DADAIA_SESSION_ID`/the three harness ids from the child env, then
   `:195-213` passes `CODEX_THREAD_ID="certification-session"` explicitly for the
   bind + heartbeat checks. That is the harness-native channel, i.e. surviving rung 2 —
   verified live. Should a check regress, the sanctioned remedy is for certify to export
   `DADAIA_CONTEXT` for its scratch workspace (rung 1), never to re-add a rung.
5. **The import-linter contract** `bind-resolution-seam-is-a-single-home`
   (`setup.cfg:241-275`, 23 source modules, zero `ignore_imports`) is **rewritten in the
   same change** to police the new single seam. A contract that outlives the seam it
   describes is worse than no contract.
6. **The law text** `public/data/DADAIA.md:103-106` is amended for precision — "your own
   session binding" becomes the live session record keyed by the harness session id, and
   the non-harness-shell guidance from coupling 3 is stated — then re-projected via
   `dadaia public stage` → `install --target all` → `doctor`. Projected law files are
   PROTECTED and are never hand-edited.
7. **Test blast radius ≈ 23 files** (18 `.py` files carry the marker surface itself). Tests pinning a **deleted rung** are deleted with the
   rung (`tests/unit/features/spec_context/test_bind_epoch_sid.py`,
   `tests/unit/core/test_specs_resolver_delete_bind.py` marker cases, the marker cases in
   `test_ctx_inject.py` / `test_ctx_inject_compact.py` / `test_specs_resolver_harness_bind.py`).
   Tests pinning a **law rung** are re-pointed at the single authority. No `skip`/`xfail`
   placeholders.

**Acceptance (measurable):**

- `grep -rn "bind_epoch\|read_bind_epoch_\|iter_bind_epochs\|write_bind_epoch\|resolve_persisted_bind_context\|_adopt_attributed_bind" dadaia_workspace/ tests/` → **0 matches** (baseline: 132 across 18 `.py` files in that same universe). Prose assets are covered by their own task's grep (`dadaia_workspace/public/`); `specs/bugs/**` and `specs/_archive/**` are excluded by law and are not part of any claim.
- `grep -rn "DADAIA_SESSION_ID" dadaia_workspace/` matches **only** session-identity/heartbeat sites; **0** inside any resolution function.
- `grep -rn "DADAIA_AGENT_RUNTIME" dadaia_workspace/ tests/` → **0 matches** (today: 2).
- `grep -rn "_SELF_HOSTING_SLUG\|_is_self_hosting_checkout" dadaia_workspace/` → **0 matches**.
- Exactly **one** function in the package resolves a context name; A/B/D/E/F all call it. `core/specs_resolver.py` ends **≤ 200 lines** (today 369).
- `lint-imports --config setup.cfg --no-cache` green with the rewritten contract, still **zero** `ignore_imports`.
- The projected `DADAIA.md` copies are byte-identical to `public/data/DADAIA.md` and mode `0444`; `dadaia public doctor` reports `[ok] public-privacy`.
- **Live-instance rung matrix — four harness/shell profiles, all four mandatory:** (i) a **Claude Code** session (rung 2, native session id); (ii) a **kimi-code** session launched with `DADAIA_CONTEXT` exported (rung 1 — the coupling-2 disposition; injection, gate mode and heartbeat context all present); (iii) a **plain shell** exporting `DADAIA_CONTEXT` (rung 1); (iv) a bare **`repos/<slug>/` cwd** with no env at all (rung 3). In each: `dadaia context bind` → `context show --json` → a MUTATING write all resolve the same context.
- `dadaia context bind` emits the loud warning when neither a harness-native id nor `DADAIA_CONTEXT` can carry the binding (proven by test **and** observed once on the live instance).
- `dadaia certify --json` green with no certify source change.

### FR2 — A healable event-sourced ledger (bug `specs-doctor-spec-doc-033-unsatisfiable-on-historical-row`, MEDIUM)

**The healing rule, stated once, in the domain model.** All coherence semantics stay in
`core/models/bugs.py` beside `advance_coherence`: a violation row is **reported by the
doctor only while no LATER `reported` event exists for the same `bug_id`**. A later
`reported` is the canonical event-sourced compensation — it already clears terminal state
inside the fold (`bugs.py:70-73`) — so the store's own append-only vocabulary heals the
history. `advance_coherence` (the per-event **enforcement** authority consumed by
`BugService.append_event`, `features/bugs/service.py:71-72`) is **unchanged**; the doctor's
`_fold_bug_coherence` (`doctor_governance.py:432-460`) becomes a thin caller of the new
whole-history diagnosis function.

This does not reopen the v0.1.72 divergence the law forbids. Enforcement answers *may this
next event be appended?*; diagnosis answers *is this history healed?* The diagnostic becomes
satisfiable **precisely because** the compensation is a pair of events enforcement already
accepts — the two gates agree by construction, which is what the law demands.

**The compensation for line 719.** Two legal appends against
`closure-catalog-references-missing-memory-atom`: a `reported` documenting the historical
repair, then a `resolved` re-affirming the original resolution with evidence pointing at the
original event (`specs/bugs/bugs.jsonl:719`, release `0.4.2`). No row is ever edited,
reordered or deleted.

**Acceptance:**

- RED-first: a test asserting the healing rule fails before the change and passes after.
- `dadaia specs doctor` (and `--json`) exits **0** on this context, 0 errors.
- A **new**, uncompensated `resolved`-without-`reported` still produces a `SPEC-DOC-033` **ERROR** — the rule heals history, it does not disable the check.
- `dadaia bugs append` still **refuses** an incoherent event (enforcement unchanged), proven by the existing service tests.

### FR3 — LOW hardening, each at its one chokepoint

Every item states the authority that will own the validation. The disposition rule the
backlog itself named applies: **one chokepoint each, never scattered call-site defences.**

1. **Install-ledger relpath (CWE-22 class).** Validate in `LedgerEntry` itself
   (`core/models/install_ledger.py:32-44`): reject empty, absolute, any `..` part, any
   backslash, and any non-normalized POSIX form. `from_dict`'s existing `ValueError` →
   store-returns-`None` bootstrap path absorbs a malformed persisted ledger. One authority
   covers **both** consumers — the prune/unlink loop (`infrastructure/public_assets.py:773-788`)
   and the foreign-projection scan (`:1365-1385`).
2. **CWE-117 doctor-line injection.** Escape control characters (`\n`, `\r`, ESC) in
   `DoctorLine.render()` (`core/models/doctor_report.py:75-77`) — **the** rendering
   authority, through which `DoctorReport.rendered()` (`:91-93`) and every golden already
   pass. No producer, present or future, can forge a second physical line.
3. **entities-derivation shape tolerance.** Widen the one parse seam,
   `infrastructure/codex_doctor.py:654-664`: after `json.loads`, normalize the shape
   (top-level `dict`; `personas`/`behaviors` lists of dicts; `implementations` a mapping)
   and emit a typed `[error] entities-derivation: … (ENT-DERIVE-1)` `DoctorLine` on
   violation, instead of letting `AttributeError`/`TypeError` escape. No `isinstance`
   scattering downstream.
4. **Kimi telemetry reader containment.** At the one seam
   (`features/telemetry/reader/kimi.py:103-109`), lexically contain `sessionDir` against
   `index_path.parent` **before** `Path(...).stat()`; a failure takes the existing `OSError`
   degradation branch (`:108-109`). Ships with the reader's **first** test file — none
   exists today, and the `DADAIA_KIMI_SESSION_INDEX` override already makes fixtures
   possible.
5. **Certification re-scope — a disposition, not code.** Recon proves all 11 certify checks
   are live post-demolition (the 8 workflow checks died with v0.3.0), with zero dead
   references; certify is the consumer-validation entrypoint (packaged script +
   `CONSUMER_VALIDATION_RECIPE.md:73` F-03/F-25 + the capabilities contract). The finding is
   recorded **re-scoped/verified** with no change. The one debt worth naming, and
   deliberately **not** fixed here, is that those 11 checks have no automated test — routed
   to the backlog as a return.

**Acceptance:** four RED-first tests, one per item 1–4; `pytest`, `ruff`, `mypy --strict`,
`lint-imports` green; doctor goldens byte-identical **except** lines whose text legitimately
changes under escaping (each such line explained in the commit message); a security-reviewer
re-verify records items 1–4 fixed and item 5 re-scoped.

### FR4 — Deferred-debt triage and terminal dispositions

**The twelve deferred bugs** (`specs/bugs/bugs.jsonl` lines 199-205, 586, 721-724). Each is
verified against current `main`; obsolete ones receive the **legal compensating ceremony**
(a `reported` reopen-note, then `superseded`-by-demolition or `resolved` with evidence);
still-real ones stay `deferred`, untouched, with their reason intact.

| # | bug_id | line | Prior (recon) |
|---|---|---|---|
| 1 | `gate-self-blocks-lease-holder-own-session` | 199 | likely obsolete post-NO-LOCKS |
| 2 | `spec-doc-029-false-forgery-harness-uuid-vs-session-record-id` | 200 | re-verify against FR1's post-state |
| 3 | `import-linter-contracts-red-but-not-ci-enforced` | 201 | premise refuted: `ci.yml:88-92` runs `lint-imports` |
| 4 | `panel-telemetry-sqlite-corrupts-under-concurrent-access` | 202 | verify |
| 5 | `context-dead-nonwritable-guard-rejects-standard-git-objects` | 203 | verify |
| 6 | `context-dead-plain-git-push-fails-mismatched-upstream` | 204 | verify |
| 7 | `memory-heading-allowlist-not-consumer-extensible` | 205 | verify |
| 8 | `lifecycle-release-define-stalls-before-worker` | 586 | names the demolished engine |
| 9 | `codex-lifecycle-timeout-not-enforced-041` | 721 | names the demolished engine |
| 10 | `blocked-close-leaves-closure-artifact` | 722 | names the demolished `close` verb |
| 11 | `backlog-subjects-readme-uses-unsupported-positional-resolve` | 723 | verify |
| 12 | `dadaia-cli-skill-command-drift` | 724 | verify |

`dadaia_workspace/features/lifecycle/` holds **zero `.py` files** — the evidence for #8/#9/#10.

**Backlog terminal dispositions, written at CLOSURE:**

- `20260806-dadaia-md-workspace-system-prompt` → **CONSUMED**. Verified live: four
  byte-identical `0444` projections, `public/rules/` retired, the PROTECTED gate class live.
  The measured always-on token count is **~3.5k against the entry's ≤3k aspiration** —
  recorded as an **accepted deviation**, operator-approved at v0.3.0, not a silent miss.
- `20260806-clean-architecture-remediation` → **CONSUMED**. Items 1-3 and 5 by v0.3.0 /
  v0.4.0 / constitution §12.4; item 4 by FR1; item 6 by FR4.
- `20260810-security-low-carryforwards-v030` → **CONSUMED**. The four original findings plus
  the two new 2026-08-11 LOWs dispositioned by FR3.

**Acceptance:** every one of the 12 deferred bugs carries an explicit disposition with a
reason or evidence; **zero** bug rows are edited or deleted (append-only proven by
`git diff` touching only appended lines); `dadaia bugs status` reflects the new counts;
all three backlog entries carry a terminal token per the ADR-11 vocabulary and appear in the
CLOSURE `## Dispositions` table.

## 4. Out of scope (non-goals)

- **Certification code.** No change to `features/certification/service.py` or its 11 checks
  (FR3 item 5 is a disposition). Its missing test coverage is a backlog return, not work.
- **`DADAIA_MODE`, `DADAIA_RUNTIME`, `DADAIA_HOOK_OUTPUT`, `DADAIA_HOOK_EVENT`,
  `WORKSPACE_ROOT`.** Mode is a separate §3 law; the rest are hook transport. None is a
  resolution rung and none is touched.
- **The panel entities loader** (`features/panel/entities`). FR3 item 3 widens the
  *independent verifier* seam only — the verifier deliberately does not share the loader
  (`codex_doctor.py:642-644`) and that separation stands.
- **The gate's path classes, presence model, mode resolution and git chokepoints.** FR1
  changes *how a context name is resolved*, never what the gate does with it.
- **`repo_slug_for_context`** and the registry's name↔slug duality — orthogonal and correct.
- **Bug/backlog history.** `specs/bugs/**` rows are appended to, never rewritten;
  `specs/_archive/**` and `CHANGELOG.md` are untouched.
- **The `core` duplicate of the session-record reader.** `specs_resolver._read_session_record`
  (`:37-56`) exists because `core` may not import
  `features/spec_context/session_identity.read_session` (constitution §6, documented
  exception). After FR1 the single authority is the natural home for record-*reading* in
  `core`, with `features` delegating downward — a real unification, but one that moves a
  layer boundary and therefore belongs to its own release. **Named here as a deletion
  candidate and routed to the backlog as a return at CLOSURE**, so it is recorded rather
  than forgotten.
- **A new release for the LOW findings' successors.** Anything discovered mid-flight that is
  not in the picked set is a backlog return, not scope.

## 5. Memory atoms affected at closure

- `specs/memory/product/platform/context-management.md` — rewrite to the single authority
  and its three law rungs; the bind-epoch marker mechanism (2 mentions) is removed, not
  narrated.
- `specs/memory/product/sdd/sdd-gate-v3.md` — the gate's context attribution now names the
  shared authority and its `target_path` (path-first) input.
- `specs/memory/architecture.md` — the resolution seam and the retired marker subsystem in
  the module map; the rewritten import-linter contract.
- `specs/memory/product/philosophy/spec-context-project.md` — binding described as the
  session record + `DADAIA_CONTEXT`, with no marker.
- `specs/memory/product/harness/harness-kimi-code.md` — **required by FR1 coupling 2**:
  kimi's binding is `DADAIA_CONTEXT` exported at harness launch; the adoption path is gone.
  A kimi atom still describing ancestry adoption after this release is exactly the drift
  this release exists to kill.
- `specs/memory/quality-assurance.md` — the FR2 rule that a healable diagnostic is part of
  the "a gate never demands what its tooling refuses" law.
- `specs/memory/product/index.md` + `catalog.json` — regenerated only if an atom's summary
  changes (`dadaia memory catalog generate`; never hand-edited).
- `specs/memory/tech-stack.md` — **expected: no change** (no dependency moves); stated
  explicitly in CLOSURE either way.

## 6. Acceptance criteria (release-level)

1. Full suite green: `pytest -p no:cacheprovider -q`.
2. `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports --config setup.cfg --no-cache` green.
3. `dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia certify --json` all exit **0** on a clean workspace **and** on this live self-hosting instance.
4. Exactly one context-resolution authority; the FR1 grep assertions all return 0 in the declared universe; `core/specs_resolver.py` ≤ 200 lines; the four-profile live rung matrix (Claude, **kimi-code**, plain shell, `repos/<slug>/` cwd) passes on this instance.
5. `dadaia specs doctor` exits 0 with the healed ledger, and a fresh uncompensated violation still ERRORs.
6. All 12 deferred bugs and all 3 backlog entries dispositioned, recorded in the CLOSURE `## Dispositions` table.
7. A `security-reviewer` APPROVED handoff whose `metrics.commit_sha` equals the pushed ref sha; CI green on every job.
8. Quantified subtraction recorded in CLOSURE: net line delta, env-var count before/after, marker-occurrence count before/after, suite count.
