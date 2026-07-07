# SPEC — v0.1.62 — Injection Contract & Fan-out Containment

**Status:** Aprovado
**Branch:** `feature/v0.1.62` (created after `Aprovado`)
**Origin:** PM dispatch 2026-07-07 — theme: mechanical verifiability + defensive hardening. Three sibling releases
(v0.1.61 / v0.1.63 / v0.1.64) are defined in parallel; write-surface overlaps are REAL and are declared + sequenced
in §0 (the original "disjoint by construction" claim was FALSE — QA62-2/ARCHX-1, corrected in the review fold).
**Definition-time inspection** (product-engineer code read, 2026-07-07) — every claim below is a read fact from the
current post-v0.1.60 source, not a restatement of the backlog dossiers (the HIGH item's "handoff-v1.1 bump" premise is
stale — the schema is already at v1.1; corrected in §1/§9).
**Release-definition grill** (mandatory, from-backlog) run on the picked set before this SPEC — inspection-first; the
operator was unavailable, so every open decision is recorded as an operator-overridable ADR (§9), the v0.1.60 T-60-01
precedent.

## 0. PM binding rulings — dual-review fold (2026-07-07) + picked bug

Dual DEFINITION review returned REJECT (qa-engineer QA62-1..5 + QAX-1..4 — report
`.dadaia/reports/dadaia-workspace/qa-engineer/2026-07-07T020000Z-v0161-64-definition-review.md`; software-architect
ARCH62-1 INFO-positive, blast radius verified, no fold needed; cross-release ARCHX-1..3). PM binding rulings,
numbered per release:

- **Ruling 62-A (RULING A — ARCHX-1 + QAX-1 + QA62-2).** <!-- AMEND:ARCHX-1 --> <!-- AMEND:QA62-2 -->
  Implementation order is **FIXED: v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64.** The §4 "no overlap / disjoint by
  construction" claim is DELETED as false; the honest collision enumeration:
  - **The 12 agent bodies** (`public/agents/*.md` ×9 + `public/plugins/*/agents/*.md` ×3): written by **this
    release's W3 (handoff-instruction body prose) FIRST, THEN v0.1.64 W3** (`tier:` → `dispatch_band:`
    frontmatter rename; v0.1.64 rebases, re-runs its `^tier:` grep, AND verifies this release's AC-6 grep stays
    satisfied post-rename). v0.1.63 W2/W3 also touches the 3 plugin agent bodies' `skills:` frontmatter —
    sequenced between (v0.1.63 before v0.1.64).
  - `cli/commands/plugin.py` + `infrastructure/public_assets.py`: v0.1.61 W2 THEN v0.1.63 W1 — not this
    release's surface.
  Each later release REBASES and re-verifies its greps/goldens post-rebase; any undeclared collision is a
  STOP-and-rescope to PM.
- **Ruling 62-B (RULING B — ARCHX-2 + QAX-2).** <!-- AMEND:ARCHX-2 --> CLOSURE sequencing follows the same
  release order; §8 carries the shared-atom merge-order clause (`quality-assurance.md` is edited by v0.1.61,
  this release, and v0.1.64). `ACTIVE.md` is a single pointer — the four releases never hold DEFINITION/CLOSURE
  concurrently; PM owns the phase schedule.
- **Ruling 62-E (RULING E — QA62-1 HIGH, bug-always-solved).** <!-- AMEND:QA62-1 --> This release **formally
  CONSUMES open HIGH bug `reports-sidecar-version-detection-misroutes-future-tokens`**
  (`specs/bugs/20260707T03Z-00.jsonl`, reported 2026-07-07T03:16:25Z by product-engineer during this very
  grill): the FR2 detection fix is exactly its remedy. **Picked bug:**

  | Bug | Severity | Mapped → | Disposition (terminal event at CLOSURE) |
  |---|---|---|---|
  | `reports-sidecar-version-detection-misroutes-future-tokens` | HIGH | FR2 detection fix + AC-4 | `dadaia bugs append --bug-id reports-sidecar-version-detection-misroutes-future-tokens --event resolved --release v0.1.62` at T-62-70 (never silently absorbed) |

  AC-4's RED-first test is the bug's recorded repro **VERBATIM**: *"author a handoff with schema token
  handoff-v1.2 and run: `dadaia reports validate <file>` — the detector falls through to v1.0-compat and errors
  on findings[]"*. The §6 "Bug debt at pick: none" line is corrected.
- **Mechanical folds (no ruling):** QA62-3 positive 16/16 adoption contract in AC-6; QA62-4 real fate-ledger
  paths in T-62-40; QA62-5 one named parametrized 4-case version-matrix test; QAX-4 branch-point
  `pytest --collect-only -q` count pinned in the first implementation wave's fate ledger (T-62-10).

## 1. Problem

v0.1.57 (R9 "Injection canon") ratified **self-pull** for the Layer-1 deep atoms (Ruling A:
constitution / architecture / quality-assurance are never injected at Layer-1; `ctx_inject.py#_build_memory` stays
byte-identical) and shipped the **Layer-2** mechanical proof (role→atom map records refs in `InjectedContext.refs`;
`FRAG-COH-4` asserts coverage). The **Layer-1** half was deliberately deferred: nothing proves a Layer-1 session
actually read the atoms it was supposed to self-pull — step0 is discipline, not a checkable contract. Separately, two
independent security reviews (plus the 2026-07-06 retier pass) flagged the consumer fan-out write path as trusting
`repo_slug` verbatim (`..`/separator traversal unsanitized) **and** `shutil.copy2` following destination symlinks; and
the v0.1.59 W5 AC-9(e) sabotage proved the panel response-guard e2e null-guards a dropped `.memory-chip` (2 passed with
the chip gone).

**Read facts (source, 2026-07-07):**

1. **The handoff schema is ALREADY `handoff-v1.1`.** `public/schemas/handoff-v1.schema.json` carries
   `"$id": "handoff-v1.1"` and `schema_version` enum `["handoff-v1", "handoff-v1.1"]`. The backlog's "needs a
   handoff-v1.1 schema bump" is stale wording — the bump this release ships is **`handoff-v1.2`**. The top-level object
   is `additionalProperties: false`, so a new field is unreachable without a schema edit, and a version token is the
   only coherent way to make the new field conditionally required.
2. **The stdlib validator cannot express a conditional requirement.** `infrastructure/stdlib_handoff_validator.py`
   whitelists exactly `$schema/$id/type/required/enum/pattern/properties/items/additionalProperties/format/minimum/
   minItems/title/description` and **raises `HandoffSchemaError` on any other keyword** — no `if`/`then`/`allOf`.
   "Required only when `schema_version == handoff-v1.2`" must therefore be enforced in the service layer
   (`features/reports/validation.py#ReportsValidationService`), not in the JSON schema.
3. **A v1.2 token would be misdetected as v1.0 today (latent hard-error).** `cli/commands/reports.py:80-86`
   `_detect_sidecar_version` returns `"1.1"` only for the exact string `"handoff-v1.1"` (or `"v1.1" in $id`); any other
   value — including `"handoff-v1.2"` — falls to `"1.0"`, and `_check_v10_compat` then **hard-errors** on a missing
   `findings[]` (reports.py:99-106). Unfixed, every new-format handoff without findings fails `dadaia reports validate`.
4. **Two accept-set pins break Layer-2 emission on a bump.** `features/lifecycle/gates.py:195` rejects any
   `schema_version` outside `{"handoff-v1", "handoff-v1.1"}` ("malformed schema_version") and
   `infrastructure/runtime_files.py:210-211` raises `RuntimeFilePathError` on the same set. The two Layer-2 code
   emitters — `features/lifecycle/service.py:216` and `features/lifecycle/report_workflow.py:80` — emit
   `"handoff-v1.1"` today.
5. **The Layer-2 refs the audit line mirrors already exist.** `features/lifecycle/role_atoms.py` owns
   `ROLE_ATOM_MAP` (`software-architect → memory/architecture.md`, `qa-engineer → memory/quality-assurance.md`,
   `product-engineer → memory/product/catalog.json`) and records `specs/`-prefixed refs into `InjectedContext.refs`.
   The map lives in `features/lifecycle`; `features/reports` cannot import it (feature-independence contract, R6
   lint-imports 8-kept) — a validator-side coverage check needs the map **data** in `core`.
6. **The all-agent adoption blast radius is enumerable.** Emission-instruction surfaces citing the handoff contract:
   the 9 core agents + 3 plugin agents (`public/agents/*.md`, `public/plugins/*/agents/*.md`), the
   `dadaia-handoff-emitter` skill (`public/skills/dadaia-handoff-emitter/SKILL.md`), `public/data/handoff-AGENTS.md`,
   and `public/lifecycle_fragments/shared/output-handoff.md`. Code surfaces: the two emitters + two accept-sets above,
   `cli/commands/reports.py` detection, `features/reports/validation.py`, `features/panel/reports_doctor.py` (grep
   sweep confirms fates at implementation).
7. **The fan-out trusts `repo_slug` verbatim.** `infrastructure/workspace_guardrail.py#_consumer_repos_for_root`
   (L59-104) joins `repos_dir / slug` with **no** component validation — a registry slug `"../outside"` or `"a/b"`
   derives a path outside (or deeper than) `repos/`, and `_install_guardrail_pair` (L182-337) then **writes** the
   AGENTS.md/CLAUDE.md pair there via `shutil.copy2` / `_atomic_write_text`. `shutil.copy2(source, dst)` **follows a
   symlinked `dst`** — a planted `repos/<slug>/AGENTS.md → <anywhere>` symlink is written through (the FR9 provenance
   banner does not save the case where the symlink's target carries the banner, and `_write_consumer_agents`'s absent
   branch would follow a dangling symlink). The doctor path (`_doctor_consumer_pair_lines`) reads through the same
   symlinks.
8. **Symlinked consumer DIRS are a legitimate first-party pattern.** The CI panel bootstrap itself does
   `ln -sfn "$PWD" repos/dadaia-workspace` (`.github/workflows/ci.yml:296`) — a containment design that `resolve()`s
   the consumer dir and rejects out-of-tree targets would false-block real usage. Slug validation must be **lexical**;
   the symlink refusal applies to destination **files**.
9. **The response-guard null-guard is real and the fixture is deterministic.** `tests/e2e/panel/response-guard.spec.ts`
   lines 76-83 and 128-131 do `const firstChip = await page.$('.memory-chip'); if (firstChip) { … }` in BOTH guards.
   The CI e2e job seeds `spec_contexts.json` with the dadaia-workspace context and **fast-fails if the memory atoms are
   absent** ("data-dependent panel paths (memory chip clicks) run in CI", ci.yml:291-326) — the Projects fixture can
   never legitimately have zero contexts, so the graceful-empty branch is dead defensive slop. The primary guardrail
   (`tests/unit/features/panel/test_index_dom_contract.py#test_memory_chip_present_with_populated_context`) survives
   unchanged.

## 2. Goals

1. **Make Layer-1 self-pull mechanically verifiable** — a `handoff-v1.2` schema bump adding a `self_pull` audit line
   (mirroring the Layer-2 `InjectedContext.refs` proof) + a version-conditional validator check, with historical
   handoffs on disk still validating (transition posture).
2. **All-agent adoption** — every emission-instruction surface (12 agents + skill + handoff-AGENTS + output-handoff
   fragment) and both Layer-2 code emitters emit v1.2 with the audit line; both accept-sets widened; the v1.0
   misdetection latent error fixed.
3. **Contain the consumer fan-out write path** — lexical slug validation at derivation + containment assertion at the
   write, defense-in-depth (both, per the two security reviews + PM retier to MEDIUM).
4. **Close the symlink write-through** — never write through a symlinked destination file; non-silent classification.
5. **Response-guard hardening** — the `.memory-chip` click path becomes a real assertion (defence-in-depth behind the
   FR1/v0.1.59 DOM-contract unit lock), graceful-empty branch removed.

## 3. Functional requirements

### FR1 — `handoff-v1.2` schema bump: the `self_pull` audit line

- **Schema edit** (`public/schemas/handoff-v1.schema.json` — filename UNCHANGED, it names the v1 family; `$id`/`title`
  bump to `handoff-v1.2`): `schema_version` enum becomes `["handoff-v1", "handoff-v1.1", "handoff-v1.2"]`; NEW
  **optional** top-level property `self_pull`:
  ```json
  "self_pull": {
    "type": "object",
    "required": ["refs"],
    "additionalProperties": false,
    "properties": {
      "refs": {
        "type": "array",
        "minItems": 1,
        "items": { "type": "string", "pattern": "^(?!/)(?!.*(?:^|/)\\.\\.(?:/|$))[a-zA-Z0-9_./-]+$" }
      }
    }
  }
  ```
  `refs` records the Layer-1 self-pull atoms the session actually loaded, in the `InjectedContext` ref style
  (context-relative, `specs/`-prefixed — e.g. `specs/memory/architecture.md`, `specs/constitution.md`). Only
  whitelisted stdlib-validator keywords are used (read fact 2) — the schema stays loadable by
  `StdlibHandoffValidator` with **zero** validator-keyword change.
- **Schema-expressible half only.** The schema declares the field's shape (optional at schema level); the
  version-conditional requirement is FR2's service-layer check (ADR-2).
- **Domain model untouched.** `core/models/handoff.py#HandoffDocument` does not gain the field this release (no
  consumer needs it; see §4).

### FR2 — Version-conditional validator + detection fix (`dadaia reports validate`)

- **Conditional requirement (service layer).** `features/reports/validation.py#ReportsValidationService.validate_file`
  gains a v1.2 check, evaluated after the schema pass: when `schema_version == "handoff-v1.2"`, `self_pull` MUST be
  present with a non-empty `refs` array; absence → `HandoffValidationError("self_pull", ...)`, invalid → the schema
  errors already fire. `handoff-v1` / `handoff-v1.1` documents are **exempt** (transition posture, ADR-2) — the
  existing on-disk corpus keeps validating under `validate_all`.
- **Existence check (mechanical honesty).** Each `self_pull.refs` entry must resolve to an existing file:
  resolution order (a) `<workspace>/repos/<context>/<ref>` (the handoff's `context` field as slug), (b)
  `<workspace>/<ref>` (self-hosting root specs). Both guarded by the existing `_within_workspace` boundary
  (resolve + relative_to, symlink-safe). Missing in both → `HandoffValidationError("self_pull.refs[i]", "ref does not
  exist")`. When `_workspace_root` is `None` (non-canonical handoff root), the existence check degrades to shape-only
  (fail-soft, mirrors the artifact-path posture).
- **Role-map coverage (the FRAG-COH-4 symmetric check).** When the emitting `agent` has a role→atom mapping, the
  mapped atom's ref MUST appear in `self_pull.refs` (e.g. a `qa-engineer` v1.2 handoff must list
  `specs/memory/quality-assurance.md`). Unmapped agents: no coverage requirement. The map **data** is single-sourced:
  relocate `ROLE_ATOM_MAP` to NEW `core/role_atom_map.py` (pure dict, stdlib-only `core` leaf);
  `features/lifecycle/role_atoms.py` imports and **re-exports it under the same name** (all three Layer-2 assembly
  surfaces + existing tests keep their import path); `features/reports/validation.py` imports from `core` (a legal
  `features → core` edge; NO new cross-feature edge — lint-imports ignore-cap UNCHANGED).
- **Detection fix (read fact 3).** `cli/commands/reports.py#_detect_sidecar_version` treats `"handoff-v1.2"` (and
  `"v1.2" in $id`) as modern ≥ 1.1 — a v1.2 sidecar must NEVER route into `_check_v10_compat` (no spurious
  "missing findings[]" hard error).

### FR3 — Accept-set widening + Layer-2 emitter bump

- **Accept-sets** (read fact 4): `features/lifecycle/gates.py#_schema_version` and
  `infrastructure/runtime_files.py:210` each gain `"handoff-v1.2"` (sets become `{v1, v1.1, v1.2}`).
- **Layer-2 code emitters** (`features/lifecycle/service.py:216`, `features/lifecycle/report_workflow.py:80`) emit
  `"handoff-v1.2"` and populate `self_pull.refs` from the run's recorded `InjectedContext` refs (reuse the existing
  mechanical data — never a second bookkeeping path; ADR-5). A run with zero recorded refs omits `self_pull`? **No —**
  a v1.2 doc requires it; the emitter falls back to the step's role-mapped atom refs via the relocated core map, and
  when even that is empty it emits `schema_version: "handoff-v1.1"` (honest legacy token rather than a fabricated
  proof). This fallback is the ONLY sanctioned v1.1 emission after this release.
- **`features/panel/reports_doctor.py`** and any other version-keyed consumer found by the implementation-time grep
  (`rg 'handoff-v1'`) are updated or explicitly ledgered as version-agnostic.

### FR4 — All-agent instruction adoption (ai-engineer, `public/**`)

- **Update every emission-instruction surface** (read fact 6): the 12 agent bodies (9 core `public/agents/*.md` + 3
  plugin `public/plugins/*/agents/*.md`), `public/skills/dadaia-handoff-emitter/SKILL.md` (required-fields table +
  both examples gain `self_pull`; `schema_version` literal → `"handoff-v1.2"`), `public/data/handoff-AGENTS.md`, and
  `public/lifecycle_fragments/shared/output-handoff.md`. The instruction: record in `self_pull.refs` the memory atoms
  the session actually self-pulled (step0 atoms + any deep atom read during the task), in `specs/`-prefixed
  context-relative form; never list an atom that was not read.
- **Grep-complete.** A final `rg 'handoff-v1\.1' dadaia_workspace/public/` must return only historical/back-compat
  mentions explicitly adjudicated in the fate ledger (e.g. the transition-posture note itself) — no surviving "emit
  v1.1" instruction.
- **Fragment goldens.** `output-handoff.md` is a shared fragment — any prompt-assembly golden that embeds it is
  re-baselined as a **deliberate recorded amendment** (golden-first law: capture the diff, never silently regen).

### FR5 — Fan-out slug containment (defense-in-depth; PM-retiered MEDIUM)

- **Lexical slug validation at derivation** (`workspace_guardrail.py#_consumer_repos_for_root`): a `repo_slug` is
  REJECTED unless it is a single, relative, non-dot path component — reject when it contains `/` or `\\`, equals `.`
  or `..`, is absolute (`Path(slug).is_absolute()` or a Windows drive/UNC form), or `len(PurePosixPath(slug).parts)
  != 1` / `len(PureWindowsPath(slug).parts) != 1` (both checked — platform-independent). A rejected slug is
  **non-silent**: one stderr line `[reject] repo_slug '<slug>' (unsafe path component) — skipped` (the A3
  never-silent law; distinct from the existing silent skip of absent dirs). Fail-open posture preserved — never
  raises. Derivation-level validation protects BOTH consumers of the helper (install fan-out and doctor).
- **Containment assertion at the write** (`_install_guardrail_pair`): before writing any consumer pair, assert the
  lexical join stays inside `repos/` (`(repos_dir / slug).parent == repos_dir` — trivially true post-validation;
  belt-and-braces per the backlog's symmetric ask). A failing assertion skips the repo with the same `[reject]` line —
  never writes, never raises.
- **NOT `resolve()`-based on the consumer dir** — a symlinked `repos/<slug>` dir is a legitimate first-party pattern
  (read fact 8; ADR-7) and stays allowed.

### FR6 — Fan-out symlink write-through refusal

- **Destination-file symlink posture: REFUSE.** In `_install_guardrail_pair`, when the destination `AGENTS.md` or
  `CLAUDE.md` **is a symlink** (`Path.is_symlink()` — including dangling), it is NEVER written through (neither
  `shutil.copy2` nor `_atomic_write_text`): classify `[foreign] <path> — left untouched (symlink)`; the paired
  `CLAUDE.md` follows its sibling's fate exactly as FR9/v0.1.60 defined (no orphan drop).
- **Doctor is symlink-aware.** `_doctor_consumer_pair_lines` classifies a symlinked `AGENTS.md`/`CLAUDE.md` as
  `[foreign]` (never `[ok]`/`[drift]`/`[missing]`) so `public doctor` exits 0 and never prescribes an install that
  would be refused.
- **The v0.1.60 FR9 provenance ladder is otherwise unchanged** — banner-match/foreign/absent semantics survive
  byte-identically for regular files.

### FR7 — Response-guard chip-presence assertion (qa-engineer)

- **Both guards assert the chip** (`tests/e2e/panel/response-guard.spec.ts`, the L76-83 and L128-131 null-guards):
  replace `const firstChip = await page.$('.memory-chip'); if (firstChip) { … }` with a required-presence form —
  `await page.waitForSelector('.memory-chip', { timeout: 8000 })` then click — so a dropped selector fails the e2e
  loudly (defence-in-depth BEHIND the DOM-contract unit lock, which survives unchanged).
- **Graceful-empty branch REMOVED** (ADR-8): the CI fixture deterministically seeds ≥1 context + memory atoms and
  fast-fails otherwise (read fact 9) — zero contexts is an infrastructure failure, not a legitimate state.
- **Sabotage replay.** The v0.1.59 AC-9(e) mutation (rename the live `.memory-chip` in
  `features/panel/views/index.py` → `.memory-chip-SABOTAGED`) must now fail BOTH the DOM-contract unit lock AND the
  e2e guards (pre-fix: unit lock only, e2e "2 passed" — the RED-first proof), then be reverted.

## 4. Non-goals

- **No Layer-1 injection expansion.** `hooks/ctx_inject.py` stays **byte-identical** — Ruling A (v0.1.57 FR4) stands;
  this release verifies self-pull, it does not replace it. (The backlog's override — bounded phase-aware L1 digests —
  was NOT exercised; recorded in ADR-1's override line.)
- **No schema filename change** (`handoff-v1.schema.json` names the family; container wiring untouched).
- **No `HandoffDocument` domain-model change** and no `stdlib_handoff_validator.py` keyword change (the new field uses
  only whitelisted keywords).
- **No retro-migration of on-disk handoffs** — historical v1/v1.1 documents stay valid forever (transition posture).
- **No FRAG-COH doctor change** — the Layer-2 proof (FRAG-COH-4) is untouched; this release adds the Layer-1 mirror in
  `reports validate`, not a new doctor check.
- **No lease/gate/spec_context change.** The release lives in `public/schemas/`, `features/reports/`,
  `cli/commands/reports.py`, `features/lifecycle/{gates,service,report_workflow,role_atoms}.py`, NEW
  `core/role_atom_map.py`, `infrastructure/{runtime_files,workspace_guardrail}.py`, `public/**` instruction surfaces,
  and two test trees — it never enters `hooks/`, lease, or gate paths. The v0.1.50 frozen no-steal suite is expected
  **zero-diff**.
- **Parallel-release overlap is DECLARED, not denied (Ruling 62-A — the earlier "write sets are foreign to
  every file above" claim was FALSE).** <!-- AMEND:QA62-2 --> <!-- AMEND:ARCHX-1 --> W3's write set (the 12
  agent bodies) is also written by v0.1.63 W2/W3 (plugin agents' `skills:` frontmatter) and v0.1.64 W3
  (`tier:` → `dispatch_band:` rename). Sequenced by the fixed order v0.1.61→62→63→64 (§0): this release lands
  its body-prose edits FIRST; each later sibling rebases and re-verifies (v0.1.64 re-runs its `^tier:` grep AND
  confirms this release's AC-6 grep still holds). Undeclared collisions = STOP-and-rescope to PM.

## 5. Acceptance criteria

- **AC-1 (back-compat corpus lock — golden-first):** BEFORE any schema/service edit, a test locks that every existing
  v1/v1.1 handoff fixture in the tree (and a representative emitter-skill example) passes `dadaia reports validate`;
  the SAME test must stay green post-FR1/FR2 (transition posture is provable, not asserted).
- **AC-2 (v1.2 conditional — RED-first; ONE named parametrized matrix — QA62-5):** <!-- AMEND:QA62-5 --> a
  `schema_version: "handoff-v1.2"` document WITHOUT `self_pull` fails validation with a `self_pull`-pathed error;
  WITH a valid `self_pull.refs` (existing atoms) it passes. RED-first: against the pre-fix tree the same
  v1.2-without-self_pull doc passes schema-blind (only the enum rejects the token — shown by the enum error
  disappearing post-FR1 and the conditional error appearing post-FR2). **The 4-case version matrix is a single
  named parametrized test** (`test_schema_version_matrix[...]` in `test_handoff_v12_validation.py`):
  v1 ✓ / v1.1 ✓ / v1.2+self_pull ✓ / v1.2−self_pull ✗ — one auditability point; AC-1's corpus lock and this
  matrix cover the same posture from the fixture and the synthetic side respectively.
- **AC-3 (existence + coverage):** (a) a v1.2 doc whose `refs` lists a non-existent atom fails with
  `self_pull.refs[i]` evidence; (b) a `qa-engineer` v1.2 doc omitting `specs/memory/quality-assurance.md` from `refs`
  fails the coverage check; a `software-engineer` (unmapped) doc has no coverage requirement; (c) a `..`-carrying ref
  is rejected by the schema pattern.
- **AC-4 (detection fix — RED-first = the picked bug's repro VERBATIM; Ruling 62-E / QA62-1):**
  <!-- AMEND:QA62-1 --> per bug `reports-sidecar-version-detection-misroutes-future-tokens`
  (`specs/bugs/20260707T03Z-00.jsonl`): *author a handoff with schema token `handoff-v1.2` and run
  `dadaia reports validate <file>`* — pre-fix (RED) the detector falls through to v1.0-compat and hard-errors on
  the missing `findings[]`; post-fix the same v1.2 sidecar with NO `findings[]` exits 0 (never routed to
  `_check_v10_compat`). Resolving this AC resolves the bug; terminal `resolved --release v0.1.62` event at
  T-62-70.
- **AC-5 (Layer-2 emitter round-trip):** a lifecycle run's emitted handoff carries `schema_version: "handoff-v1.2"` +
  `self_pull.refs` equal to the run's recorded `InjectedContext` refs, and passes both `gates.py` (no "malformed
  schema_version") and `runtime_files.py` (no `RuntimeFilePathError`) and `reports validate`. The zero-refs fallback
  emits v1.1 (never a fabricated `self_pull`).
- **AC-6 (adoption — negative grep AND positive 16/16 contract; QA62-3):** <!-- AMEND:QA62-3 -->
  **Negative:** `rg 'handoff-v1\.1' dadaia_workspace/public/` post-FR4 returns only fate-ledgered back-compat
  mentions. **Positive (mechanical, file-enumerated — a surface mentioning neither token must FAIL):** a
  contract test enumerates the **16 surfaces** — the 12 agent bodies (9 core + 3 plugin), the
  `dadaia-handoff-emitter` skill's TWO examples (each its own assertion), `handoff-AGENTS.md`, and
  `output-handoff.md` — and asserts each contains the `handoff-v1.2`/`self_pull` emission instruction (16/16,
  not a manual sweep). The emitter skill's required-fields table additionally carries `self_pull`.
- **AC-7 (containment — RED-first):** with a registry carrying slugs `"../evil"`, `"a/b"`, `"C:\\x"` (or POSIX
  absolute), `".."` — and matching directories planted so the pre-fix join resolves — `public install --target all`
  writes NOTHING outside `repos/` and emits one `[reject]` stderr line per bad slug; `_consumer_repos_for_root`
  returns only valid consumer dirs (doctor protected too). RED-first: pre-fix, the `"../evil"` fixture receives the
  AGENTS.md/CLAUDE.md pair OUTSIDE `repos/`.
- **AC-8 (symlink refusal — RED-first):** (a) a consumer `AGENTS.md` symlinked to an out-of-repo target file survives
  install byte-identical at the target, with `[foreign] ... (symlink)` reported and NO write through the link
  (including the banner-bearing-target case); (b) a DANGLING `AGENTS.md` symlink is refused (never "absent → create");
  (c) `public doctor` reports the pair `[foreign]` and exits 0; (d) a **symlinked consumer DIR** with a regular
  canonical `AGENTS.md` file inside keeps today's `[ok]` behavior (the CI-pattern guard — no false-block). RED-first:
  pre-fix, `shutil.copy2` writes through the (a) link and clobbers the target.
- **AC-9 (response-guard — RED-first sabotage replay):** with `.memory-chip` renamed in `index.py` (the v0.1.59
  AC-9(e) sabotage), the e2e guards FAIL (pre-fix they pass "2 passed"); reverted, both guards pass and the chip
  click path executes unconditionally. The DOM-contract unit lock stays byte-identical.
- **AC-10 (mutation-sanity per new test):** (a) drop the FR2 conditional (accept v1.2 without `self_pull`) ⇒ AC-2
  FAILS; (b) skip the existence check ⇒ AC-3(a) FAILS; (c) skip coverage ⇒ AC-3(b) FAILS; (d) revert
  `_detect_sidecar_version` ⇒ AC-4 FAILS; (e) drop the slug reject ⇒ AC-7 FAILS; (f) drop the `is_symlink()` refusal
  ⇒ AC-8(a) FAILS; each captured on its task line, then reverted.
- **AC-11 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, full **unpiped** `pytest`,
  `lint-imports --no-cache` (**8 kept / 0 broken**; ignore-cap UNCHANGED — `core/role_atom_map.py` is a stdlib-only
  `core` leaf; `features→core` edges are legal), `dadaia specs doctor` (exit 0), `dadaia backlog doctor` (exit 0).
  Ship wave: `dadaia public stage` → `dadaia public install --target all` → `dadaia public doctor`
  (`[ok] public-privacy`, exit 0). The v0.1.50 frozen no-steal suite is **zero-diff**. *(PE runs no shell — surfaces
  commands to PM/operator or requests devops-engineer.)*
- **AC-12 (fate ledger per wave — file-enumerated):** each wave records concrete files + fates; every version-token
  grep includes `tests/` AND non-import textual references (docstrings, fragment prose, skill examples). No
  implementation-wave commit stages `specs/backlog/**` (dispositioned at CLOSURE).

## 6. Consumed backlog

| Item | Kind | Priority | Consumed → FR | Anchor fate |
|---|---|---|---|---|
| `layer1-selfpull-handoff-audit-line` | backlog (candidate) | HIGH | schema bump → FR1; validator → FR2; accept-sets + L2 emitters → FR3; all-agent adoption → FR4 | Anchors `hooks/ctx_inject.py#main` (survives **byte-identical** — the entry verifies self-pull, never reopens Ruling A) → **CLOSURE** |
| `fanout-repo-slug-containment` | backlog (candidate) | LOW→**MEDIUM** (PM retier — two independent security reviews + the 2026-07-06 pass) | slug containment → FR5; symlink refusal → FR6 (folded per the retier findings) | Anchors `workspace_guardrail.py#_install_guardrail_pair` (survives, hardened) → **CLOSURE** |
| `response-guard-chip-presence-hardening` | backlog (candidate) | LOW | chip assertion → FR7 | Anchors `test_index_dom_contract.py#test_memory_chip_present_with_populated_context` (survives byte-identical — the primary lock) → **CLOSURE** |

**Bug debt at pick (corrected — Ruling 62-E / QA62-1):** <!-- AMEND:QA62-1 --> ONE open HIGH bug is consumed by
this release — `reports-sidecar-version-detection-misroutes-future-tokens` (`specs/bugs/20260707T03Z-00.jsonl`,
found during this grill; mapped to FR2 + AC-4; terminal `resolved --release v0.1.62` at T-62-70 — see the §0
picked-bug table). The original "Bug debt at pick: none" claim was FALSE against the ledger. The one open LOW
bug (pipeline `accepted=True` on illegal transition, synthetic-only) is out of theme and remains with PM.
**Audit debt at pick:** none open.

**Archival timing.** All three anchors SURVIVE → dispositioned + archived at CLOSURE (`DELIVERED — v0.1.62`); no dead
anchor → no SHIP-time archival. Discipline: **no `specs/backlog/**` staged in W1–W5** (AC-12). The
`fanout-repo-slug-containment` override path ("REJECTED — trusted-input") is **declined** — ADR-9.

## 7. Risks

- **Schema-bump ecosystem breakage.** Any missed version-keyed consumer rejects v1.2 handoffs at runtime. Mitigation:
  read facts 3/4/6 enumerate the known set; AC-5 round-trips the full Layer-2 path; an implementation-time
  `rg 'handoff-v1'` sweep is a task deliverable with per-file fates (AC-12).
- **Fabricated audit lines.** The handoff is self-reported — an agent could list atoms it never read. The contract is
  honest-by-construction where mechanical (existence check + role-map coverage) and discipline beyond that; the same
  boundary FRAG-COH-4 accepts at Layer-2. Recorded, not solved (a hook-level read-tracker is out of scope).
- **Coverage check false-blocks a legitimate handoff.** A mapped agent doing pure-ADDITIVE work might not re-read its
  atom. Mitigation: step0 is mandatory once per session and names exactly these atoms; the coverage check applies only
  to the 3 mapped roles; operator can override via ADR-3.
- **Containment false-blocks a legitimate slug.** Lexical validation could reject an exotic-but-real slug. Mitigation:
  the rule is minimal (single relative non-dot component — matching how `context create` mints slugs); rejection is
  non-silent so a false positive is immediately visible; AC-8(d) pins the symlinked-dir CI pattern green.
- **Fragment-golden churn (FR4).** `output-handoff.md` edits re-baseline prompt goldens. Mitigation: golden-first law —
  deliberate recorded amendment with a captured diff; FRAG-COH doctor green before/after.
- **Parallel-release collision.** Three sibling releases in flight WITH real declared overlaps on the 12 agent
  bodies. Mitigation: the §0 Ruling 62-A fixed order + rebase-and-reverify discipline (v0.1.64 re-runs its grep
  AND this release's AC-6); any UNdeclared overlap is a STOP-and-rescope to PM, never a silent merge.
  <!-- AMEND:QA62-2 -->

## 8. Memory files affected at CLOSURE

- `specs/memory/product/agents/agent-comms.md` — **primary**: handoff contract v1.2, the `self_pull` audit line,
  transition posture, validator checks (tldr/summary change ⇒ catalog regen, length-capped).
- `specs/memory/product/distribution/public-asset-distribution.md` — fan-out slug containment + symlink posture.
- `specs/memory/product/sdd/lifecycle-foundation.md` — Layer-2 emitters at v1.2 (self_pull from `InjectedContext`);
  role→atom map data relocated to `core` (re-export preserved).
- `specs/memory/quality-assurance.md` — response-guard is now a real assertion; the "null-guard degrades gracefully"
  drift note retired.
- `specs/memory/architecture.md` — `core/role_atom_map.py` leaf (assess: only if the module map enumerates core leaves).
- `specs/memory/tech-stack.md` — no change expected (no dependency, no tool).
- Regen `catalog.json` (+ `index.md` if order/entries change) only where `tldr`/`summary` changed; `release_origin` →
  v0.1.62 on each edited atom. Closure ORDER LAW: memory edits + catalog regen BEFORE `ACTIVE.md` → none.
- **Shared-atom merge order (Ruling 62-B / RULING B — ARCHX-2 + QAX-2):** <!-- AMEND:ARCHX-2 --> shared with
  siblings: `quality-assurance.md` (v0.1.61 ×2, this release, v0.1.64), `public-asset-distribution.md`
  (v0.1.61, this release, v0.1.63), `architecture.md` (v0.1.61, this release assess, v0.1.63),
  `lifecycle-foundation.md` (v0.1.61 pass A, this release). **PM sequences CLOSURE in release order (this
  release closes after v0.1.61, before v0.1.63/64); the later-closing release REBASES each shared atom on the
  sibling's closed state (never reverts a sibling's correction); every `catalog.json` regen includes all prior
  tldr/summary deltas.**

## 9. ADRs (operator unavailable — every one overridable)

- **ADR-1 — version token `handoff-v1.2`.** The schema is already `$id: handoff-v1.1` (read fact 1); the new field
  behind `additionalProperties: false` requires a new token for coherent conditional validation. *Override:* fold the
  field into v1.1 silently (rejected: old validators/gates would reject the field; version-conditional enforcement
  becomes impossible). The backlog's own override (reopen Ruling A with L1 digests) was NOT exercised —
  `ctx_inject.py` stays byte-identical.
- **ADR-2 — transition back-compat, service-layer conditional.** Accept `{v1, v1.1, v1.2}`; `self_pull` required
  ONLY for v1.2, enforced in `ReportsValidationService` (the stdlib validator has no `if`/`then` — read fact 2);
  hard-cut applies to NEW emissions via instructions + code emitters. *Override:* hard-cut the enum to v1.2-only
  (rejected: the historical on-disk corpus would fail `validate_all` forever).
- **ADR-3 — field shape `self_pull: {"refs": [...]}`, minItems 1, existence + role-map coverage.** Mirrors
  `InjectedContext.refs` naming/ref-style for Layer-1↔Layer-2 symmetry; the validator checks what is mechanically
  checkable (refs exist on disk; mapped role's atom present). *Override:* presence-only (weaker) or a per-atom
  read-proof hash (stronger, out of scope).
- **ADR-4 — map relocation to `core/role_atom_map.py` with same-name re-export.** The coverage check needs the map in
  `features/reports`; cross-feature import is illegal (R6 contract) — pure data moves to a `core` leaf, single source
  preserved, zero import-path churn for the three Layer-2 surfaces. *Override:* duplicate the dict (rejected:
  two-sources drift) or skip coverage (ADR-3 override).
- **ADR-5 — Layer-2 emitters reuse `InjectedContext` refs; zero-refs falls back to v1.1.** Never fabricate a proof;
  never build a second refs-bookkeeping path. *Override:* always-v1.2 with empty-refs allowance (rejected: violates
  minItems-1 honesty).
- **ADR-6 — defense-in-depth: lexical slug-reject AND write-time containment assert.** Both hardening surfaces from
  the two security reviews land; rejection is non-silent (`[reject]` stderr line, A3 law). *Override:* single-layer.
- **ADR-7 — symlink policy: REFUSE destination-file symlinks; ALLOW symlinked consumer dirs.** `shutil.copy2`
  write-through is closed; the CI's own `ln -sfn` repos-dir pattern (read fact 8) stays green — no `resolve()`-based
  dir rejection. *Override:* refuse dirs too (would break the CI bootstrap + operator symlink workflows).
- **ADR-8 — response-guard requires the chip; graceful-empty branch REMOVED.** The CI fixture deterministically seeds
  ≥1 context and fast-fails on missing atoms (read fact 9) — zero-context is an infra failure, not a state to degrade
  into. *Override:* keep a fixture-flagged empty branch.
- **ADR-9 — the `fanout-repo-slug-containment` "REJECTED — trusted-input" override is DECLINED.** PM retiered to
  MEDIUM on two independent security reviews + the 2026-07-06 pass (which added the `..` and symlink findings) —
  implement, don't reject.
