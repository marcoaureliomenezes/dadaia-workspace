# GRILL — Release v0.4.2 — residual-convergence

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-16 (resolva todos — goal directive)
**Release ID:** v0.4.2
**Owner:** product-engineer
**Session:** 2026-08-16 — mandatory `dadaia-grill-me` on the picked set (`dd-release-definition` §3)
**Scope:** the 14 picked backlog entries (13 full picks + 1 partial), no bug, no audit

---

## 0. Operator law for this release (verbatim, binding)

> "resolva de forma inteligente, retire complexidade, diminua superficie de bugs, o simples
> é sempre melhor se atente nossas funcionalidades"

> "Na proxima rodada não quero ver essa desgraça de erros e bugs residuais"

Every decision below was taken against that law: **prefer deletion over addition**, one
authoritative statement per fact, no second parse path, no new module where an existing seam
can carry the behaviour, no literal-by-literal treadmill.

---

## 1. Phase 0 — inspection before questions

Every finding below was verified against the working tree at `feature/0.4.2` (cut from
`develop` at `36412845`). Nothing here is inferred from a backlog description alone; where the
entry's text and the code disagreed, the code won and the disagreement is recorded.

| # | Type | Anchor | What inspection found |
|---|---|---|---|
| P1 | Confirmed | `features/spec_artifacts/new_artifacts.py:192` | `_append_active_subsection` splices before the first `## LEDGER` match of a **private, fence-blind** `_LEDGER_HEADING_RE`; `_backlog_slug_exists` re-derives `### <slug>` and the LEDGER-row grammar with two more private regexes (`:117`, `:120`). Three private copies of a grammar the parser owns. |
| P2 | **Blocker for the stated fix** | same module, `:105-113` | The module's own comment states it deliberately does **not** import `features/backlog/document` because `features/spec_artifacts` and `features/backlog` are independent siblings under the `features-no-cross-feature` import-linter contract. The intent's "shared grammar seam" is therefore *unimplementable as an import* without a new lint exception. → **D1**. |
| P3 | Confirmed | same module, `:262`, `:283` | `_SLUG_RE.match` (accepts a trailing newline) and a plain `write_text` for the whole-file rewrite. |
| P4 | **Contradiction** | `atomic_write_text` | Defined in `hooks/_common.py:231`, mirrored in `infrastructure/**`. `features/**` may import neither. The entry's atomic-write rider cannot land without adding file I/O to `core/` (whose authorized-I/O set is an architecture rule). → **D2**. |
| P5 | Confirmed | `features/backlog/document.py:147` | `_outside_fences` is `[m for m in matches if not any(start <= m.start() < end for ...)]` — the O(headings × fences) rescan, exactly as measured. |
| P6 | Confirmed | `document.py:230`, `:40` | `yaml.safe_load` per `**Intents:**` block through the default (pure-Python) loader; one parse per block, ~23 per document. |
| P7 | Confirmed | `document.py:43` | `from dadaia_workspace.features.backlog.preview import _format_yaml_error` — a leaf importing a sibling leaf's underscore-private symbol. |
| P8 | Confirmed | `core/redaction.py:32-47` | `compile_candidates` compiles with **no** `re.IGNORECASE` and with `-` as a word char. The detector layers are case-insensitive (`denylist_scan.py:112` slug layer, `:179` operator layer). The masker is strictly narrower than the detector. |
| P9 | Confirmed | `chokepoints/service.py:561-567` | The git-failure refusal interpolates `{exc}` verbatim; `git_objects.py:257` builds that exception embedding the raw blob path. Two unmasked channels. |
| P10 | Confirmed | `git_objects.py:130-166` | `_blob_info` returns `{sha: (first-seen path, size)}` — `if sha in blob_sizes and sha not in info` keeps the first path only; the surviving path depends on `rev-list` order. |
| P11 | Confirmed | `git_objects.py:328-390` | `_read_oversized_blob_prefix` never inspects the process exit status; only `proc.wait()`/`proc.kill()` are called. A failed read returns a 0-byte prefix reported as "partially scanned". |
| P12 | **Anchor correction** | `git_objects.py:155`, `:160`, `:215` | The silently-dropped `--batch-check` row lives in `_blob_info` (`len(parts) != 3` and the `int()` `except ValueError: continue`) and in `_resolve_prior_texts`, **not** in `_read_blobs` as the entry names. `_read_blob_chunk` already aborts on desync (v0.11.0 FR8). |
| P13 | Confirmed | `cli/commands/ci.py:227-273` | A malformed registry is already swallowed by `container.load_registry_context_identities`; `_foreign_repo_slugs` silently degrades to the directory-derived set with no note. |
| P14 | Confirmed | `tests/integration/test_repo_self_scan.py:120` | `_EXCLUDED_PREFIXES = ("specs/_archive/", "specs/audits/_archive/")` — a whole-subtree exclusion, blind to a file authored directly into the archive. |
| P15 | Confirmed | `infrastructure/data/privacy_baseline.json:41-45` | `home-abs-path` matches `/home/<user>` only. Zero occurrences of `Users` or `/root` in the file. Six patterns, `version: 4`. |
| P16 | Confirmed + **anchor correction** | `features/spec_artifacts/new_artifacts.py:202-239`, `features/specs/scaffolder.py:386-404` | `release_new` writes a **SPEC stub only** — there is **no flat-release TASKS template** anywhere. `_SEGMENT_TASKS_STUB` is a four-line placeholder with one `T1` and no ship/archive ordering. The entry's named code anchor cannot carry the ordering fix. → **D8**. |
| P17 | Confirmed | `cli/commands/specs.py:346-449`, `features/specs/scaffolder.py:213-342` | `dadaia specs hotfix open` is live; its `else` branch at `:411-416` prints the `candidates.md not found` WARNING **unconditionally** in every workspace (the file class no longer exists), advising a file that trips SPEC-DOC-035. `scaffold_hotfix_release` + `_HOTFIX_TASKS_STUB` + the two `.j2` templates + a golden (`tests/unit/infrastructure/_golden/doctor_all_four_v0158.json`) are the rest of the dead surface. `core/specs_version.py` and `doctor_release.py` mention hotfixes only in comments — no dead logic there. |
| P18 | Confirmed | `features/specs/doctor_governance.py:67-95` | SPEC-DOC-031's evidence is `if slug in raw_line` over **every line** of every archived SPEC + CLOSURE, with exactly one section exclusion (`## Backlog returns`). Free-text matching is the false-positive engine. |
| P19 | New finding | `specs/_archive/releases/*/SPEC.md` | 27 archived SPEC/CLOSURE files carry a `**Consumes:**` line, several as prose ("the single backlog candidate") and several wrapped across two lines. A `**Consumes:**`-keyed check must tokenize slug-shaped words across the declaration's continuation lines. |
| P20 | Confirmed | `CHANGELOG.md:7,51,101,141,168,194,214,237,314,384,443`; `pyproject.toml:3` | `pyproject` already reads **`0.4.2`**; the CHANGELOG's top sections are `[0.9.0] … [0.5.1]`, then three `[Unreleased] — spec release vX` sections, then `[0.5.0] — Unreleased`, then the genuinely published `[0.1.x]` lineage. There is **no** `0.2.x`–`0.4.x` section at all. |
| P21 | New finding | `features/specs/catalog.py:206`, `public/scripts/generate-memory-catalog.py:188` | **Two** catalog generators, both copying `int(fm.get("token_estimate", 0))` from frontmatter, both listing it in a `_REQUIRED` tuple. The computation itself lives in a third place: `public/scripts/lint-memory-atoms.py:353` (`round(len(body.split()) * 1.35)`) behind a 20 %-drift WARN. |
| P22 | **Phase blocker** | `features/spec_context/gate_policy.py` (MEMORY class) | Atom frontmatter is `specs/memory/**` — writable only in `DEFINITION`/`CLOSURE`. Any change to the 26 atoms' frontmatter cannot ride an IMPLEMENTATION-phase task. → **D5**. |
| P23 | Confirmed | `public/schemas/memory/memory-frontmatter-v1.schema.json:7,8,15,52` | `additionalProperties: false` **and** `token_estimate` in `required`. Removing the key from the schema and from the atoms must therefore land in a coherent order, or `specs doctor` goes red between commits. |
| P24 | Confirmed | `dd-release-closure/SKILL.md:93`; `dd-release-definition/SKILL.md:89` | The closure skill still templates a per-entry disposition row (`specs/backlog/<slug>.md`); the definition skill still says the sweep "Flips each fully-consumed slug's `## LEDGER` line" where the shipped mechanism **adds** a LEDGER line and **removes** the ACTIVE subsection. |
| P25 | New finding | `public/agents/product-engineer.md:137` | The PE persona's file-hierarchy tree still documents `candidates.md` as "index of per-entry candidates" — a fourth stale statement of the retired backlog shape, in the persona of the agent that authors releases. |
| P26 | Confirmed | `features/telemetry/store/schema.py:93,102` | Two DEAD-marker comments still point readers at `backlog/candidates.md`. |
| P27 | Confirmed | `specs/assets/architecture/doctor-decomposition.md:44` | The diagram still shows `check_backlog_schema()` on `GovernanceValidator` — retired at the v0.12.0 cutover. |
| P28 | Verified clean | `specs/audits/**` | Every audit lives under `_archive/` — **no undispositioned audit outranks this pick** (`DADAIA.md` §5). |
| P29 | Unverifiable without a shell | `specs/bugs/bugs.jsonl` (883 events) | `product-engineer` cannot run `dadaia bugs status`. The PM-curated pick-precedence notice in `BACKLOG.md` (2026-08-15) states **zero open bugs**. Confirmation is a named task step. → **OD-3**. |

**Answered via inspection, no operator question needed:** P1, P3, P5–P15, P17, P18, P20, P21,
P23, P24, P26–P28.

---

## 2. Operator pre-rulings ratified into this release (ADRs)

Recorded with provenance **operator ruling, 2026-08-16**. Not re-litigated.

| ADR | Ruling | Where it lands |
|---|---|---|
| **R1** | Multi-path blob amnesty is **fail-closed**: a blob reachable at more than one path in the pushed range receives no amnesty. Never a per-sha amnesty. | FR7 |
| **R2** | The **PyPI lineage is the only version axis**. The package is minted `0.4.2` at ship and the release id **is** the minted version. The never-published `0.5.0`–`0.9.0` headers are reconciled without rewriting history. | FR13, §7 |
| **R3** | **Review-before-archive** is canon: the pre-PR six-axis review of the delta runs before the `git mv` archive step; only ship steps follow. | FR5 |
| **R4** | **Intake calibration**: record-only observations terminate in the release CLOSURE; only actionable defects reach the PM intake report; zero observations lost. | FR6, and this release's own closure |
| **R5** | **Simplicity law**: resolve at the root, remove complexity, shrink the bug surface — deletion beats addition. | Every FR; the tie-breaker for D1–D10 |

---

## 3. Grill decisions (D1–D10) — the refinements this session added

**D1 — the backlog writer moves to the feature that owns the grammar.**
P2 proves the "shared seam" cannot be an import across `spec_artifacts` → `backlog`. Two ways
out: add a lint-imports exception, or move `backlog_new` into `features/backlog/` where
`document.py` already lives. The move is chosen: one feature owns the backlog document for
both reading and writing, no new import exception exists to be copied later, and
`new_artifacts.py` shrinks to `release_new`. Deletion beats configuration (R5).

**D2 — the atomic-write rider is declined, with the reason recorded.**
P4: landing it means adding file I/O to `core/` (an architecture-rule change) or breaking the
layering. The silent-loss class the rider targets is fully covered by **write-then-verify**
(re-parse after write, raise if the fresh slug is absent), which is the entry's own primary
fix. Recorded as an explicit non-goal (SPEC §4), not forgotten.

**D3 — masking parity by sharing the detector's matchers, not by widening the CLI primitive.**
P8's fix could widen `core/redaction.compile_candidates` with a flag. Instead the gate-side
`_PathMasker` consumes the **detector's own compiled matchers** (`denylist_scan`, the same
feature) — parity becomes structural rather than promised, `cli/redact.py` stays
byte-identical *by construction*, and one predicate exists where there were two.

**D4 — fail-closed multi-path amnesty needs no matcher change.**
The conservative form (R1) is implemented entirely in the adapter: a blob reachable at more
than one path in the range simply carries **no prior text**. The matcher, its amnesty
predicate and its tests are untouched. The "suppress only if every path amnesties" form would
require a new multi-path input on `ScannedObject` and new predicate logic — it is **not**
equally simple, so R1's default stands.

**D5 — `token_estimate` is deleted from atom frontmatter, not merely recomputed.**
A value that is stored *and* derivable will drift again (two instances, 37 % and 42 % off).
The only fix that ends the class is zero stored copies: the catalog **computes** it and the
frontmatter stops carrying it. P22/P23 force the execution order: the code half (catalog
computes; schema field becomes optional; the lint drift check is deleted) rides
IMPLEMENTATION; the memory half (strip the key from every atom, drop it from the schema
properties, regenerate `catalog.json`) rides **CLOSURE**, where memory writes are legal.
Green at every commit is preserved because an optional-but-present key is valid in between.

**D6 — SPEC-DOC-031 keys on consumption-asserting evidence; the section-exclusion treadmill is
deleted.** Adding "non-goal", "out-of-scope", "inheritance" and "provenance" to the excluded
section list is the same literal-by-literal treadmill entry #24 already named in another
surface. Instead the check reads only what actually *asserts* consumption: an archived SPEC's
`**Consumes:**` declaration (with its wrapped continuation lines, P19) and an archived
CLOSURE's `## Dispositions` rows. Everything else in a release document is prose. The
`## Backlog returns` special case is **removed** as subsumed. Net: less code, no treadmill,
and the 13-slug curation debt evaporates instead of being annotated 13 times.

**D7 — parser perf: bisect + `CSafeLoader`; the second parse mode is declined.**
A slug/status-only parse path is a second grammar reader — precisely the class this release
exists to remove. `CSafeLoader`-when-available is a three-line change that benefits every
caller, including the SPEC-DOC-031 re-parse. If the budget is still missed, that is a recorded
residual, not a licence to fork the parser.

**D8 — the ordering canon lands in the skill surface, not in a generated template.**
P16: `release_new` emits no TASKS at all, so there is nothing to reorder there, and generating
a new opinionated template would be addition where a statement suffices. The canon is stated
once in the lifecycle skills and **dogfooded by this release's own TASKS** — the code review
task sits before closure/archive, with only ship steps after.

**D9 — new baseline patterns bring their own self-scan baseline rows.**
FR10's positive fixtures must contain a literal that *matches* the new pattern, and
`tests/**` is inside the self-scan sentinel's scope. Those literals are declared rows in
`_TESTS_SCOPE_BASELINE`. "Shrink-only" survives as doctrine: the count may rise only by this
release's explicitly declared fixture rows, and QA verifies the delta is exactly that set.

**D10 — `/root` is evaluated and excluded from FR10.**
The pattern family exists to catch an **operator-identifying** path segment. `/home/<user>`,
`/Users/<name>` and `C:\Users\<name>` all carry a personal name; a bare `/root` carries none
and appears routinely in container documentation. Adding it would buy false positives and no
privacy. Recorded as a deliberate boundary, not an oversight.

---

## 4. Picked-set refinements per entry

| Entry | Refinement from this session |
|---|---|
| `backlog-grammar-single-writer-seam` (#38) | Fix shape changed by D1 (move, not import) and narrowed by D2 (atomic-write rider declined). Write-then-verify and the `fullmatch` rider stand. |
| `denylist-masking-predicate-parity` (#39) | D3 fixes the shape; the `GitObjectReadError` structured-path half is unchanged. The FR6-class sentence in the gate atom is a **CLOSURE** memory edit, not an implementation task. |
| `derived-values-computed-not-stored` (#43) | D5 raises the fix from "recompute" to "stop storing"; P21 adds the second generator and P22/P23 add the two-phase execution constraint. |
| `knowledge-duplication-doc-pass` (#44) | Item (2) (gate-atom wording) and item (3) (the architecture diagram) move to the **CLOSURE memory window**; P25 adds a sixth surface (the PE persona's stale `candidates.md` tree). |
| `flat-release-ship-task-evidence` | D8 relocates the fix from the code anchor to the skill surface; the shell-less-dispatcher reservation obligation rides the same statement. |
| `intake-signal-calibration` | Acceptance is bound to **this** release's own closure (R4): its CLOSURE carries a record-only section, its intake list carries only actionable defects. |
| `amnesty-multi-path-blob-fail-closed` (#40) | D4 settles the semantics choice the entry left to the grill: conservative form, adapter-only. |
| `git-batch-epipe-swallow-width` (#41) | P12 corrects the anchor for sub-item (3): the drop sites are `_blob_info` / `_resolve_prior_texts`, not `_read_blobs`. Sub-item (1)'s predicate is sharpened: raise only when the process failed **and** fewer than cap bytes arrived. |
| `self-scan-sentinel-archive-authored-blobs` (#45) | "NEW at HEAD" is defined precisely: a blob whose sha is absent from `HEAD^`'s tree. A rename into the archive republishes an existing sha and stays excluded; an unavailable `HEAD^` degrades to today's behaviour, never to a failure. |
| `baseline-carve-out-review-cadence` (#24) | **Partial pick**: the cross-platform half only (FR10). The cadence/rationale half and the internal-hostname dotted-chain structural fix stay ACTIVE, rewritten to that residual. D9 and D10 bound the picked half. |
| `document-parser-fence-filter-complexity` (#42) | D7 declines the second parse mode. |
| `retire-dead-hotfix-surface` (#4) | P17 completes the deletion set (CLI verb + scaffolder function + stub + two templates + tests + one golden) and confirms nothing else depends on it. |
| `changelog-version-axis-reconciliation` (#11) | R2 collapses the two axes; P20 shows `pyproject` is already at `0.4.2`, so the work is the reconciling preamble plus the `[0.4.2]` section at ship — and the retirement of ADR-2's two-axis claim from the `pypi-distribution` atom at closure. |
| `spec-doc-031-citation-classes` (#10) | D6 settles the semantics; the 13-slug debt is discharged by the root fix, not by 13 annotations. |

---

## 5. Open decisions (recorded, not blocking)

- **OD-1** — Should the git commit identity used in this workspace be de-personalised?
  Standing operator question, restated at intake #3; unrelated to this scope, stays open.
- **OD-2** — Is `deferred` terminal for bug
  `panel-telemetry-sqlite-corrupts-under-concurrent-access`? Still undecided; entry #12
  (the dangling-pointer repair) was not picked and proceeds either way.
- **OD-3** — The published PyPI version lineage must be read from the index at implementation
  time; the FR13 preamble states measured fact, and `product-engineer` has no shell. Same
  constraint applies to the zero-open-bugs confirmation (P29).
- **OD-4** — Should `token_estimate` remain in `catalog.json` at all? Kept (computed) — it is
  the only cost signal an agent has when choosing atoms. Revisit only if it goes unused.

---

## 6. Synthesis

**Core problem resolved:** the picked set is not fourteen unrelated defects but **three
root-cause classes plus their downstream instances** — knowledge stated twice and drifting,
a process order that freezes the artifact before it is reviewed, and a review pipeline that
manufactures intake volume — and every fix in this release is now bound to the class rather
than to the instance.

**Post-refinement status:** ready for SPEC.

**Declared dependencies:** FR14 (SPEC-DOC-031 semantics) must land **before** FR3's skill pass
restates the check, or the skills will restate the retired wording. FR2's memory half and
FR3's memory half both ride the CLOSURE window. No other ordering constraint.

**Checklist (`dd-release-definition`):**

- [x] Picked set recorded (14 entries: 13 full, 1 partial).
- [x] Bug-always-solved: **no bug picked** — the ledger carries zero open bugs (PM notice,
      2026-08-15; confirmation is a named task step, OD-3). Nothing is dropped.
- [x] `dadaia-grill-me` session completed — this report.
- [x] SPEC authored from the refined, picked set.
- [x] `**Consumes:**` declared for the 13 fully-consumed entries; #24 excluded as a partial.
