# TASKS — Release v0.5.0 — One context-resolution authority, a healable ledger, hardening at chokepoints

> **Status:** Aprovado

**Release ID:** v0.5.0
**Owner:** product-engineer
**Source PLAN:** `specs/releases/v0.5.0/PLAN.md`
**Branch:** `feature/v0.5.0`

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **Authority first, deletions second, prose last.** Every task ends with an importable
  package and a collectable suite.
- **RED before GREEN.** Every behavioral change (FR1 rungs, FR2 healing, FR3 items 1-4)
  lands its failing test first, on the executed path.
- **No `skip`/`xfail` placeholders.** A test that pins a deleted rung is deleted with the
  rung, in the same commit.
- **Append-only ledger.** `specs/bugs/bugs.jsonl` is written **only** through
  `dadaia bugs append`; any non-append diff hunk fails the task.
- **No new mechanism to make a gate pass.** If certify, a hook or a doctor check regresses,
  the remedy is inside the single authority or its inputs — never a re-added rung.
- **Parallelism.** T-50-09/10 (FR2) and T-50-11..14 (FR3) declare write sets disjoint from
  the FR1 chain and may hold a concurrent `[-]`; every other task is strictly sequential.
  **Carve-out: golden fixtures are NOT disjoint.** T-50-12 (escaping) and T-50-07/T-50-08
  (asset re-projection) can both move goldens. T-50-07/08 land **before** T-50-12 so any
  golden movement has one candidate cause; if that order is inverted, the commit message
  says so explicitly and both goldens are re-derived from scratch, never hand-merged.
- **History is never rewritten**: `specs/_archive/**` and `CHANGELOG.md` history stay verbatim.

---

- [x] **T-50-01 — The single context-resolution authority (additive)**

**Owner role:** software-engineer

**Write set:** `dadaia_workspace/core/specs_resolver.py` (add `resolve_context` and
`context_name_for_repo_slug`); `tests/unit/core/test_specs_resolver*.py` (new law tests).

**Description:** Add the one function implementing `DADAIA.md` §3 verbatim — rung 0 caller
input (`explicit`, or the context derived from `target_path` under `<ws>/repos/<slug>/`),
rung 1 `DADAIA_CONTEXT`, rung 2 this session's **live** record keyed by
`core.session_env.harness_session_id`, rung 3 the repo containing the cwd. Rung 3 maps slug →
context NAME through the registry inverse of `repo_slug_for_context` (`specs_resolver.py:93-125`).
Purely additive: no existing rung is removed in this task.

**Done criterion:** RED-then-GREEN tests for each of the four rungs, including a rung-0
`target_path` case that resolves `x` while `DADAIA_CONTEXT=y`; suite green; nothing deleted.

---

- [x] **T-50-02 — Re-point all five consumers to the authority**

**Owner role:** software-engineer

**Preconditions:** T-50-01 `[x]`.

**Write set:** `dadaia_workspace/cli/_specs_resolution.py`; `dadaia_workspace/hooks/sdd_gate.py`
(`_context_slug`); `dadaia_workspace/hooks/sdd_post_gate.py` (the **read** side of presence
attribution only — `_adopt_attributed_bind` is dispositioned in T-50-04);
`dadaia_workspace/container.py`; their tests.
**Explicitly NOT in this write set:** `hooks/ctx_inject.py` — see the description.

**Description:** One commit per consumer so each is independently revertible. The gate passes
`target_path=fpath` so its **path-first** attribution is preserved through rung 0 — the single
inversion risk of the whole release. **ctx_inject is re-pointed in T-50-03, not here:**
`_newest_qualifying_marker` (`ctx_inject.py:145-180`) fuses name resolution with the injection
trigger, so a name-only delegation would either double-inject on every prompt for
marker-bound sessions or keep the marker call anyway. Both halves move together.

The intended semantic widening is proven here too: a write under **no** repo, which today
resolves via `DADAIA_CONTEXT` only (`sdd_gate.py:94-95`), now falls through to rungs 2-3.

**Done criterion:** the four non-ctx_inject sites call the one authority; a test writes into
`repos/x/…` with `DADAIA_CONTEXT=y` and asserts the gate attributes `x`; a test pins the
no-repo write resolving via rungs 2-3; full suite green;
`dadaia doctor`/`specs doctor`/`public doctor`/`certify --json` green; **still nothing deleted**.

---

- [x] **T-50-03 — Re-point ctx_inject: name resolution AND injection trigger, together**

**Owner role:** software-engineer

**Preconditions:** T-50-02 `[x]`.

**Write set:** `dadaia_workspace/hooks/ctx_inject.py` (`:145-198` — `_resolve_context` and the
trigger path, one commit); `tests/unit/hooks/test_ctx_inject.py`,
`tests/unit/hooks/test_ctx_inject_compact.py`,
`tests/e2e/features/test_ctx_inject_bind_boundary.py`.

**Description:** Delegate name resolution to the single authority **and** replace "bind-epoch
marker mtime newer than the sentinel" with "the session record's `bound_at` newer than the
sentinel" — the two are fused in `_newest_qualifying_marker` and cannot be split. The
sentinel / `recorded_slug` compaction fallbacks (`:444`, `:469`, `:501-506`) are a separate
mechanism and stay.

**This is not a one-for-one swap, and the difference is intended.** Today a **same-context
re-bind does not re-inject** (the `recorded_slug == context` guard, `:531`); under the
`bound_at` trigger it will. That is the desired correction: a re-bind is how a mode or
release change reaches a live session, and today that change never reaches the injected
context.

**Done criterion:** injection fires once per bind and not on a re-prompt; a **same-context
re-bind DOES re-inject** (new pinned behavior); **FR-W2-02 re-proven** — a pre-existing bind
never injects into a fresh session; post-compact re-injection behaves as
`CONSUMER_VALIDATION_RECIPE.md:376` describes; suite green.

---

- [x] **T-50-04 — Delete the competing ladders and the bind-epoch marker subsystem**

**Owner role:** software-engineer

**Preconditions:** T-50-03 `[x]`.

**Write set:** `core/specs_resolver.py` (`_persisted_bind_context`, `_marker_chain`, the
`DADAIA_SESSION_ID` channel in `_session_context`, the old `resolve_bound_context_name`);
`features/spec_context/session_identity.py` (`write_bind_epoch`, `iter_bind_epochs`,
`read_bind_epoch_pids`, `read_bind_epoch_sid`, `bind_epoch_dir`, **and the now-false marker
narrative at `:115-123`**); `container.resolve_persisted_bind_context`;
**`hooks/sdd_post_gate.py` — `_adopt_attributed_bind` (`:108-176`) and its call site
(`:296-305`), deleted by name**; `hooks/ctx_inject._newest_qualifying_marker`;
`cli/_specs_resolution.current_ancestry_pids`; `features/spec_context/service.py` (marker
writes); the pinning tests (`tests/unit/features/spec_context/test_bind_epoch_sid.py`, the
marker cases in `test_session_identity.py`, `test_specs_resolver*.py`, `test_ctx_inject*.py`,
`test_sdd_post_gate_behavior.py`, `test_cli_context.py`,
`test_cli_bound_session_resolution.py`).

**Description:** The rungs and their tests die in the **same** commit — a pin that outlives
its subject leaves the suite red across a task boundary and is indistinguishable from a
demolition mistake. `DADAIA_SESSION_ID` survives only as a session **identity** for the
CLI/hook heartbeat, never as a resolution rung.

**`_adopt_attributed_bind` is the load-bearing deletion, not an incidental one.** It is the
sole caller of `resolve_persisted_bind_context` (`:141-143`) and `read_bind_epoch_sid`
(`:147`), so deleting the callees without it leaves an import error or a silently dead path.
It is also the **writer** that made rung 2 true for kimi-code, which has no native
session-id env var (its docstring, `:111-114`, names the bug it fixed). Its replacement is
SPEC FR1 coupling 2: kimi binds via `DADAIA_CONTEXT` exported at harness launch, backed by
the T-50-05 warning, the T-50-08 teaching updates and the T-50-19 kimi rung-matrix profile.
Stale prose about a deleted mechanism (`session_identity.py:115-123`) is exactly the drift
this release exists to kill, so it goes in the same commit.

**Done criterion:** `grep -rn "bind_epoch\|read_bind_epoch_\|iter_bind_epochs\|write_bind_epoch\|resolve_persisted_bind_context\|_adopt_attributed_bind" dadaia_workspace/ tests/`
→ **0 matches** (baseline: 132 across 18 `.py` files in that universe); no `DADAIA_SESSION_ID`
read inside any resolution function; no stale marker narrative in `session_identity.py`;
suite green.

---

- [x] **T-50-05 — Delete the workarounds and the dead alias; add the bind warning**

**Owner role:** software-engineer

**Preconditions:** T-50-04 `[x]`.

**Write set:** `cli/_specs_resolution.py` (pop/restore `:141-148`; `_SELF_HOSTING_SLUG` `:71`;
`_is_self_hosting_checkout` `:96-103`, `:151-152`; stale docstring `:22-23`);
`core/specs_resolver.resolve_specs_dir` (`cwd/specs` fallback + workspace-root refusal patch,
`:351-363`); `hooks/sdd_gate.py:200` and `cli/commands/context.py:519`
(`DADAIA_AGENT_RUNTIME`); `cli/commands/context.py` (`:276`, `:516`, `:599`, `:630` → one
session-id helper; **plus the new bind warning**).

**Test pins, named per surface** (deleted with their surface, or re-pointed at the authority):
- self-hosting fallback → `tests/contract/cli/test_cli_context.py` (self-hosting-slug cases),
  `tests/integration/cli/test_cli_bound_session_resolution.py` (no-bind-in-checkout cases);
- `cwd/specs` fallback + root refusal → `tests/unit/core/test_specs_resolver.py`
  (`cwd_specs`/workspace-root-refusal cases);
- `DADAIA_AGENT_RUNTIME` → `tests/unit/hooks/` gate-runtime cases and the
  `cli/commands/context.py` bind-record runtime cases;
- session-id micro-ladders → the four per-verb sid cases in `tests/contract/cli/test_cli_context.py`,
  re-pointed at the single helper.

**Description:** Each deleted item exists only because another authority existed. The
self-hosting literal is a special case of rung 3; the pop/restore block is a symptom of two
ladders reading one env var; `DADAIA_AGENT_RUNTIME` has **zero writers** in the tree.

**The one addition, with its §12.4 justification:** `dadaia context bind` prints a loud
warning when it can neither key a harness-native record nor see `DADAIA_CONTEXT` — "this
binding is reachable only if you export `DADAIA_CONTEXT=<ctx>`". T-50-04 removed the adoption
path that used to make such a binding work invisibly; without this warning the removal would
convert a working flow into a silent no-op, which is the failure mode this release exists to
prevent.

**Done criterion:** `grep -rn "DADAIA_AGENT_RUNTIME\|_SELF_HOSTING_SLUG\|_is_self_hosting_checkout" dadaia_workspace/ tests/`
→ **0 matches**; `core/specs_resolver.py` **≤ 200 lines** (baseline 369); one session-id
helper in `cli/commands/context.py`; a RED-first test proving the warning fires with no
harness id and no `DADAIA_CONTEXT`, and stays silent otherwise; every named pin above is
deleted or re-pointed (no orphans); suite green; goldens byte-identical.

---

- [x] **T-50-06 — Rewrite the import-linter seam contract**

**Owner role:** software-engineer

**Preconditions:** T-50-05 `[x]`.

**Write set:** `setup.cfg` (`[importlinter:contract:bind-resolution-seam-is-a-single-home]`,
`:241-275`); the contract's test/doc references.

**Description:** The contract names 23 source modules and takes zero `ignore_imports`. It must
describe the **new** seam in the same release: a stale contract passing green certifies a seam
that no longer exists.

**Done criterion:** `lint-imports --config setup.cfg --no-cache` green; still **zero**
`ignore_imports`; the contract name and `name =` line describe the single authority.

---

- [x] **T-50-07 — Amend `DADAIA.md` §3 and re-project the law**

**Owner role:** ai-engineer

**Preconditions:** T-50-06 `[x]`.

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (§3 context/memory paragraph,
`:103-106`); projections via `dadaia public stage` → `install --target all` → `public doctor`.

**Description:** Precision only — "your own session binding" becomes the live session record
keyed by the harness session id, and the non-harness-shell guidance is stated
(`dadaia context bind` prints `export DADAIA_CONTEXT=<ctx>`; for a plain shell the env var
**is** the binding). Projected law files are PROTECTED and are never hand-edited.

**Done criterion:** the four projected copies are byte-identical to source and mode `0444`;
`dadaia public doctor` reports `[ok] public-privacy` and zero drift; suite green.

---

- [x] **T-50-08 — Update the skills and the consumer recipe**

**Owner role:** ai-engineer

**Preconditions:** T-50-07 `[x]`.

**Write set:** `public/skills/dadaia-workspace-manager/SKILL.md`,
`public/skills/dadaia-workspace-spec-navigator/SKILL.md`, `public/skills/dadaia-cli/SKILL.md`,
`public/data/CONSUMER_VALIDATION_RECIPE.md` (`:115-120`), `public/data/dadaia-AGENTS.md`;
projections.

**Description:** Every teaching surface describes the same three rungs and the plain-shell
`DADAIA_CONTEXT` path. Three things are taught **by name**: the **kimi-code launch-env
binding** (`DADAIA_CONTEXT` exported by the harness — the FR1 coupling-2 disposition),
`context heartbeat` (whose marker-sid path dies with the subsystem, so a plain-shell bind
without `eval` no longer resolves through a marker), and the T-50-05 bind warning. No skill
or asset may mention a bind-epoch marker after this task.

**Done criterion:** `grep -rn "bind_epoch\|ancestry" dadaia_workspace/public/` → **0 matches**
about binding; projections green; the recipe's bind steps — including the kimi profile —
match observable behavior on this instance.

---

- [x] **T-50-09 — FR2: the healing rule in the domain model**

**Owner role:** software-engineer

**Preconditions:** none (disjoint write set — may run parallel to T-50-01..08).

**Write set:** `dadaia_workspace/core/models/bugs.py` (new whole-history diagnosis function
beside `advance_coherence`, which is **unchanged**);
`dadaia_workspace/features/specs/doctor_governance.py` (`_fold_bug_coherence`, `:432-460`,
becomes a thin caller); the doctor-governance and bug-model tests.

**Description:** A violation row is reported **only while no LATER `reported` event exists for
the same `bug_id`** — the store's own compensation vocabulary, which already clears terminal
state in the fold (`bugs.py:70-73`). Enforcement (`BugService.append_event`,
`features/bugs/service.py:71-72`) is untouched: diagnosis answers *is the history healed*,
enforcement answers *may this event be appended*, and they agree because the compensation is
an event enforcement accepts.

**Done criterion:** RED-first test for the healing rule and for an uncompensated violation
still ERRORing; the append-refusal tests unchanged and green; suite green.

---

- [x] **T-50-10 — FR2: compensate the historical row**

**Owner role:** software-engineer

**Preconditions:** T-50-09 `[x]`.

**Write set:** `specs/bugs/bugs.jsonl` (appends **only**, via `dadaia bugs append`).

**Description:** Two legal appends against `closure-catalog-references-missing-memory-atom`:
`reported` documenting the historical repair, then `resolved` re-affirming the original
resolution with `--resolution-evidence` citing `specs/bugs/bugs.jsonl:719` and release `0.4.2`.
Redact before writing — no absolute local paths, IPs or hostnames in any event field.

**Done criterion:** `dadaia specs doctor` and `dadaia specs doctor --json` exit **0** with 0
errors on this context; `git diff specs/bugs/bugs.jsonl` shows appended lines only; the open
bug `specs-doctor-spec-doc-033-unsatisfiable-on-historical-row` carries its own `resolved`
event with evidence.

---

- [x] **T-50-11 — FR3.1: install-ledger relpath validation at `LedgerEntry`**

**Owner role:** software-engineer

**Preconditions:** none (parallel-safe).

**Write set:** `dadaia_workspace/core/models/install_ledger.py` (`LedgerEntry.__post_init__`
— the validation site, `:32-44`); its tests.

**Description:** Reject empty, absolute, any `..` part, any backslash, and any
non-normalized-POSIX relpath **in the model**, in `__post_init__` so **every** construction
path is covered — `from_dict` (`:87`), the installer's own writer (`public_assets.py:764-766`)
and any future caller alike. `from_dict`'s existing `ValueError` → store-returns-`None`
bootstrap path absorbs a malformed persisted ledger. One authority covers both the
prune/unlink loop (`public_assets.py:773-788`) and the foreign-projection scan (`:1365-1385`)
— neither call site is touched.

**Done criterion:** RED-first tests for each rejected shape; **a cross-OS guard test proving
the writer's own `rel_posix` entries always validate on Windows** (the OS that natively
produces backslashes — the validator must never brick `dadaia public install` there);
**zero** validation added at either call site; `dadaia public install/doctor` green; suite
green on all CI OS targets.

---

- [x] **T-50-12 — FR3.2: control-character escaping in `DoctorLine.render()`**

**Owner role:** software-engineer

**Preconditions:** none (parallel-safe).

**Write set:** `dadaia_workspace/core/models/doctor_report.py` (`render`, `:75-77`); doctor
goldens **only** where the escaping legitimately changes a line.

**Description:** CWE-117 fixed at **the** rendering authority, through which
`DoctorReport.rendered()` (`:91-93`) and every golden already pass — no producer, present or
future, can forge a second physical line.

**Done criterion:** RED-first test proving an embedded `\n`/`\r`/ESC cannot produce a second
physical line; goldens byte-identical **except** legitimately escaped lines, each explained in
the commit message; a broader diff is reported as a finding, not regenerated.

---

- [x] **T-50-13 — FR3.3: entities-derivation shape tolerance at the parse seam**

**Owner role:** software-engineer

**Preconditions:** none (parallel-safe).

**Write set:** `dadaia_workspace/infrastructure/codex_doctor.py` (`:654-664` parse seam of
`check_entities_derivation`); its tests.

**Description:** After `json.loads`, normalize the shape (top-level `dict`;
`personas`/`behaviors` lists of dicts; `implementations` a mapping) and emit a typed
`[error] entities-derivation: … (ENT-DERIVE-1)` `DoctorLine` instead of letting
`AttributeError`/`TypeError` escape. No `isinstance` scattering downstream; the verifier keeps
its deliberate independence from the features-layer loader (`:642-644`).

**Done criterion:** RED-first tests for each malformed-but-valid-JSON shape; every case yields
a blocking typed line, never a traceback; suite green.

---

- [x] **T-50-14 — FR3.4: kimi telemetry reader containment + its first test file**

**Owner role:** software-engineer

**Preconditions:** none (parallel-safe).

**Write set:** `dadaia_workspace/features/telemetry/reader/kimi.py` (`:103-109`);
`tests/unit/features/telemetry/test_reader_kimi.py` (**new** — the reader has no test today).

**Description:** Lexically contain `sessionDir` against `index_path.parent` **before**
`Path(...).stat()`; a containment failure takes the existing `OSError` degradation branch
(`:108-109`) — no new failure mode. Fixtures use the existing `DADAIA_KIMI_SESSION_INDEX`
override.

**Done criterion:** RED-first test with an escaping `sessionDir` proving no `stat` outside the
index parent; the reader's first test file exists and covers the happy path, the skip paths
and the containment path; suite green.

---

- [x] **T-50-15 — FR3.5: certification re-scope disposition (no code)**

**Owner role:** product-engineer

**Preconditions:** T-50-14 `[x]`.

**Write set:** `specs/releases/v0.5.0/CLOSURE.md` (`## Dispositions`); `specs/backlog/`
return recorded in CLOSURE `## Backlog returns` (PM curates the file itself).

**Description:** Record the verified finding: all 11 certify checks are live
post-demolition, zero dead references, and certify is the consumer-validation entrypoint
(`CONSUMER_VALIDATION_RECIPE.md:73` F-03/F-25). **No source change.** The one debt named and
deliberately not fixed here — the 11 checks have no automated test — is routed to the backlog.

**Done criterion:** `git diff dadaia_workspace/features/certification/` is **empty** for this
release; the disposition and the backlog return are written; `dadaia certify --json` green.

---

- [x] **T-50-16 — FR4: verify the 12 deferred bugs against current main**

**Owner role:** software-engineer (verification runs) with product-engineer (verdicts)

**Preconditions:** T-50-10 `[x]` **and T-50-05 `[x]`** — bug #2
(`spec-doc-029-false-forgery-harness-uuid-vs-session-record-id`) must be verified against
FR1's **post-deletion** state, as the SPEC requires; a verdict taken against the pre-deletion
tree would be worthless.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (verification handoff); no source files.

**Description:** One verdict per bug with its evidence, for lines 199-205, 586, 721-724.
Known priors: `dadaia_workspace/features/lifecycle/` holds **zero `.py` files** (evidence for
`lifecycle-release-define-stalls-before-worker`, `codex-lifecycle-timeout-not-enforced-041`,
`blocked-close-leaves-closure-artifact`); `.github/workflows/ci.yml:88-92` runs `lint-imports`
(refutes `import-linter-contracts-red-but-not-ci-enforced`);
`gate-self-blocks-lease-holder-own-session` predates NO-LOCKS;
`spec-doc-029-false-forgery-harness-uuid-vs-session-record-id` is re-checked against FR1's
post-state.

**Done criterion:** 12 verdicts, each `obsolete` (with the superseding evidence) or
`still real` (with the reproduction that still fails); no source file touched.

---

- [x] **T-50-17 — FR4: append the compensating ceremony for the obsolete bugs**

**Owner role:** software-engineer

**Preconditions:** T-50-16 `[x]`.

**Write set:** `specs/bugs/bugs.jsonl` (appends **only**, via `dadaia bugs append`).

**Description:** For each obsolete bug: a `reported` reopen-note referencing the original
stream, then `superseded` (by the demolition/release that removed the surface) or `resolved`
with evidence. Still-real bugs stay `deferred` and are **not touched**. Never delete a bug.

**Done criterion:** every obsolete bug carries a terminal event with evidence; every still-real
bug is byte-identical to before; `dadaia bugs status` reflects the new counts;
`dadaia specs doctor` still exits 0; the diff is appends only.

---

- [x] **T-50-18 — Memory delta preview (DEFINITION phase, no memory write)**

**Owner role:** product-engineer

**Preconditions:** none — runs during DEFINITION, before implementation.

**Write set:** `specs/releases/v0.5.0/SPEC.md` §5 only. **No file under `specs/memory/` is
written before the `ACTIVE.md` phase is `CLOSURE`.**

**Description:** Enumerate, per atom, the section that changes and the statement that becomes
true after this release: `product/platform/context-management.md` (single authority + three
rungs; marker mechanism removed, not narrated), `product/sdd/sdd-gate-v3.md` (attribution via
the shared authority's `target_path`), `architecture.md` (resolution seam, retired marker
subsystem, rewritten import-linter contract),
`product/philosophy/spec-context-project.md` (binding = session record + `DADAIA_CONTEXT`),
`product/harness/harness-kimi-code.md` (binding = `DADAIA_CONTEXT` at harness launch; no
ancestry adoption), `quality-assurance.md` (a diagnostic must be healable by a legal event),
`product/index.md` + `catalog.json` (regenerate only if a summary moves), `tech-stack.md`
(expected: no change — stated explicitly either way).

**Done criterion:** SPEC §5 lists atom + section + resulting statement for each;
`git status specs/memory/` is clean until the CLOSURE flip.

---

- [x] **T-50-19 — QA `alpha-1`: live-instance validation and the SPEC §6 sweep**

**Owner role:** qa-engineer

**Preconditions:** T-50-08, T-50-10, T-50-14, T-50-17 all `[x]`.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (+ HTML report if the operator asks); no
source files.

**Description:** Validate FR1 on **this live instance**, not only in fixtures. The rung matrix
has **four mandatory profiles**:

1. **Claude Code** session — rung 2 via the native session id;
2. **kimi-code** session launched with `DADAIA_CONTEXT` exported — rung 1, the FR1 coupling-2
   disposition. Assert all three effects that `_adopt_attributed_bind` used to provide:
   context-memory **injection** fires, the **gate resolves the bind mode**, and the
   **heartbeat carries the context**. This profile is the only thing that can detect the
   regression the marker deletion risks; a matrix without it is not an acceptance.
3. **plain shell** exporting `DADAIA_CONTEXT` — rung 1, including `context heartbeat`;
4. bare **`repos/<slug>/` cwd** with no env at all — rung 3.

Plus the gate-attribution case (write into `repos/x/` while `DADAIA_CONTEXT=y` → attributed
`x`), the no-repo write resolving via rungs 2-3, the bind warning observed once, and the full
SPEC §6 list including post-compact injection per `CONSUMER_VALIDATION_RECIPE.md:376`.

**Done criterion:** all four profiles pass on the live instance; `pytest`, `ruff format
--check`, `ruff check`, `mypy --strict`, `lint-imports`, `dadaia doctor`, `specs doctor`,
`public doctor`, `certify --json` all green; the `alpha-1` review is committed to the branch.

---

- [x] **T-50-20 — Review, security verdict, push, PR, CI green**

**Owner role:** code-reviewer + security-reviewer (verdicts), software-engineer (push/PR)

**Preconditions:** T-50-19 `[x]`.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (verdict handoffs); no source files except
fixes a reviewer requires (each returning its task to `[-]`).

**Description:** Six-axis code review; security re-verification that FR3 items 1-4 are fixed
at their authority and item 5 is re-scoped, ending in an APPROVED handoff whose
`metrics.commit_sha` equals the pushed ref sha. Then push → PR → watch CI until **every** job
is green, fixing causes and re-pushing as needed.

**Done criterion:** APPROVED security handoff matching the pushed sha; code-review APPROVE;
every CI job green; PR merged.

---

- [x] **T-50-21 — CLOSURE, memory atoms, dispositions, archive**

**Owner role:** product-engineer

**Preconditions:** T-50-20 `[x]`; `ACTIVE.md` phase set to `CLOSURE` **before** any memory
write (memory is phase-gated).

**Write set:** `specs/releases/v0.5.0/CLOSURE.md`;
`specs/memory/product/platform/context-management.md`,
`specs/memory/product/sdd/sdd-gate-v3.md`, `specs/memory/architecture.md`,
`specs/memory/product/philosophy/spec-context-project.md`,
`specs/memory/product/harness/harness-kimi-code.md`,
`specs/memory/quality-assurance.md`, `specs/memory/product/{index.md,catalog.json}`
(regenerated via `dadaia memory catalog generate`); `specs/releases/ACTIVE.md`; `CHANGELOG.md`.

**Description:** Memory describes the product **after** this release — one resolution
authority, no marker subsystem, no "we used to attribute by ancestry". Record the disposition
sweep (12 bugs + 3 backlog entries, including the ~3.5k-vs-≤3k token count as an **accepted
deviation**), the backlog returns (**certify's 11 checks have no automated test**; **the
`core` duplicate session-record reader `specs_resolver.py:37-56` vs
`session_identity.read_session`, a named deletion candidate whose fix moves a §6 layer
boundary and so belongs to its own release**), and the quantified subtraction: net line
delta, env-var count before/after, marker occurrences 132 → 0 in the code universe, suite
count.

**Done criterion:** `grep -rn "bind_epoch\|_adopt_attributed_bind" specs/memory/` → **0
matches**; the kimi atom describes launch-env binding; `dadaia specs
doctor` green; CLOSURE complete with the `## Dispositions` table; release archived via
`git mv specs/releases/v0.5.0 specs/_archive/releases/v0.5.0` and `ACTIVE.md` repointed.
