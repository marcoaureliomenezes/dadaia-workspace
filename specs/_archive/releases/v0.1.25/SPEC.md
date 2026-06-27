# SPEC — Release: v0.1.25 — Backlog-consistency foundation (R1 of FEAT-BACKLOG-DEFINITION-WORKFLOW-01)

**Status:** Aprovado
**Release ID:** v0.1.25
**Owner:** product-engineer
**Opened:** 2026-06-26
**Approved:** 2026-06-26 — architect (APPROVED-WITH-CHANGES, 3 findings folded) + qa
(FINDINGS, 5 constraints/acceptance lines folded). Folds: architect #1 → §3.2 + ADR-A
(R1 5-kind auto-derive; panel/api alias-only, R2 defers); architect #2 → §3.4a (resolve/
preview surface + corrected backfill sequence); architect #3 → §3.6 + ADR-C (sidecar
`specs/_archive/<release>/consumed_backlog.json`); qa #4 → §3.7.8 (fixed `tmp_path` fixture
tree); qa #5 → §3.7.9 (git-hook-level e2e); qa #6–#8 → §3.8 (injected paths / module-relative
anchors / test-pyramid + parameterized BL-*).
**Branch:** `feature/v0.1.25`
**Consumes (R1 slice):** `specs/backlog/backlog-definition-workflow-dedup-conflict-control.md`
(FEAT-BACKLOG-DEFINITION-WORKFLOW-01) — this release is **§11 R1** of that epic. R2
(v0.1.26) ships the workflow body (§4), the removal-on-release closure hook (§6), and the
real fragments.

---

## 1. Problem and context

The backlog is filed across time by a forgetful operator + agents; **nothing compares a
new demand against the existing backlog.** Three compounding failure modes have already
corrupted a project (epic §1):

1. **Duplication** — two files request the same change.
2. **Divergent conflict (the dangerous one)** — `C→D` filed day 1, then (forgotten)
   `C→E` filed day 2. Both touch **subject C** with **incompatible targets**. Undetected,
   one becomes a release and silently contradicts the other. The defect was the
   **inconsistent backlog**, not the code.
3. **Staleness** — an item shipped via a release is never removed, accumulating as dead
   crap (the 2026-06-26 cleanup deleted 22 such files).

**Architect root-cause finding (binding):** the true root cause is **uncanonicalized
subjects**. Any design where `subject` is free text the model emits is theater — it fails
on exactly the naming drift ("the panel API" vs `/api/dadaia-workflows` vs
`WorkflowDetailDTO`) that caused the incident. The architect **REJECTED** an earlier
free-text-subject version. The non-negotiable core is a **Python-owned canonical-subject
registry + a deterministic Python-disposes classifier + a doctor chokepoint** — NOT model
judgment, NOT human/agent vigilance (both have already failed).

### Why R1 ships before the workflow (slice rationale, epic §11)

R1 makes the backlog **mechanically consistent BEFORE the workflow exists**. Shipping the
workflow body first (R2) would ship theater: an oriented happy-path with no enforced
backstop and no canonicalized subjects to reason over. R1 delivers the mechanism (schema +
registry + classifier + enforced doctor) and backfills the live tree so the backstop runs
green from day one. R2 then layers the human-facing `backlog_definition` workflow on top of
an already-consistent foundation.

### Verified current-state facts (source-inspected; engineers rely on these)

- **`features/backlog/` does not yet exist.** R1 creates it: `subject_registry.py`,
  `classifier.py`, `doctor.py`.
- **The `dadaia backlog` CLI group already exists** (`cli/main.py:67` →
  `cli/commands/lifecycle.py:59` `backlog_app`, with `define` at `:327`; a second `backlog
  new` lives in `newartifacts.py:85`). R1 wires a new **`backlog doctor`** subcommand into
  this existing group — no new top-level command.
- **The pre-commit chokepoint exists** as a shell git-hook
  (`public/scripts/pre-commit-lease-gate.sh`) with a Python backend
  (`dadaia ci pre-commit-check`); CI runs `dadaia ci preflight`. R1 wires `backlog doctor`
  into both, mirroring the existing CI-preflight pattern.
- **`consumed_backlog` is referenced only by `specs doctor`** today
  (`features/specs/doctor.py` SPEC-DOC-031), which heuristically matches a slug against
  archived-release prose (WARN-only, false-positive-prone by design). R1 defines a
  **structured `consumed_backlog` ledger schema** that the new `backlog doctor` reads
  **mechanically** (exact slug membership), superseding the NLP-prose heuristic for the
  BL-STALE check. The ledger is **written** by release-definition/closure in **R2**; R1
  only needs the doctor to **read** it (and tolerate its absence).
- **14 surviving backlog item files** exist (excluding `ideas.md`, `candidates.md`, and the
  epic itself): they carry no `intents[]` frontmatter and must be backfilled.

---

## 2. Objective

Ship the **mechanically-enforced backlog-consistency foundation**: the `intents[]` item
schema, the auto-derived canonical-subject **registry** (model proposes → Python binds →
HALT on unresolved/ambiguous), the **Python-disposes fail-closed classifier**
(UNRELATED/DUPLICATE/DIVERGENT_CONFLICT via canonical-anchor set-intersection), and
`dadaia backlog doctor` (BL-SCHEMA/DUP/CONFLICT/STALE) wired into the **pre-commit
chokepoint + CI** — then **backfill** valid bound `intents[]` onto all 14 survivors so
`backlog doctor` exits 0 on the live tree. The `backlog_definition` workflow body itself is
explicitly deferred to R2.

---

## 3. Scope (R1 — the foundation, not the workflow)

Seven clusters (3.1, 3.2, 3.3, 3.4, 3.4a, 3.5, 3.6). Implementer = `software-engineer`
unless noted. Each carries verifiable acceptance (the consolidated acceptance criteria are
§3.7; binding constraints are §3.8).

### 3.1 — `intents[]` item schema

The `(subject{kind,ref} → change)` frontmatter shape every backlog item carries (epic §2):

```yaml
intents:
  - subject: { kind: code,      ref: "dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind" }
    change: "remove OPENCODE_RUN"
  - subject: { kind: api,       ref: "panel:/api/dadaia-workflows" }
    change: "add per-step model_options"
  - subject: { kind: doc,       ref: "memory/architecture.md#layer-2" }
    change: "..."
  - subject: { kind: invariant, ref: "INV-no-claude-at-L2" }
    change: "..."
```

- `subject.kind` ∈ `{code, api, cli, panel, doc, invariant, catalog}` (the registry source
  classes of §3.2). `subject.ref` is a **typed reference**, never free text. **R1 note:**
  `code`/`cli`/`catalog`/`doc`/`invariant` are auto-derived; `panel`/`api` bind via the
  operator alias map only (no auto-derivation in R1 — §3.2, ADR-A).
- `change` is a short human string (the *what* of the delta on that subject).
- A typed, validated dataclass shape lives in `core/models/` (pure, no I/O), consumed by
  the registry, classifier, and doctor. The schema is the contract; it does not itself
  resolve subjects — binding is the registry's job (§3.2).

### 3.2 — Canonical-subject registry (the linchpin)

`features/backlog/subject_registry.py` — **AUTO-DERIVED, recomputed from live truth on
every run** (epic §2; OQ-5 resolved). It is **derived, never a stored file that can itself
go stale** (the meta-version of the bug we are fixing).

**R1 minimum-viable auto-derived anchor set (architect finding #1 — binding).** The R1
registry auto-derives exactly **five** anchor kinds, all backed by a real registry of
truth in the live tree:

1. **code** — module-relative `path#symbol`, validated to exist via AST (with a grep
   fallback) of the live tree;
2. **cli** — Typer command ids (the `dadaia <group> <verb>` surface, walkable from the
   Typer app tree);
3. **catalog** — `specs/memory/product/catalog.json` slugs (and product-atom ids);
4. **doc** — spec-doc ids (e.g. `SPEC-DOC-NNN`, memory-atom heading anchors);
5. **invariant** — named invariants (e.g. `INV-no-claude-at-L2`).

**Panel / API ids are NOT auto-derivable in R1 and are demoted to alias-map-only.** There
is **no route registry** in the codebase from which a panel route or API endpoint id can
be derived as live truth; grep-deriving them would be exactly the fuzzy heuristic this
release rejects. In R1 a `subject.kind` of `panel` or `api` resolves **only** through an
explicit operator alias-map entry that maps it to one canonical anchor; there is **no
auto-derivation for these kinds**. Auto-derivation of panel/API ids is **deferred to R2**
(when a route registry can be introduced). The `intents[]` schema still accepts
`kind ∈ {…, panel, api}` (§3.1) so the shape is forward-compatible — R1 simply binds those
kinds via alias only.

Plus an operator-maintained **alias map** at `.dadaia/states/backlog_subject_aliases.txt`
(one `synonym -> canonical-anchor` per line) that collapses known synonyms to one canonical
anchor — and, in R1, is the **sole** binding path for `panel`/`api` subjects. The alias map
is read via an **explicitly injected path**, never a cwd lookup (mirrors the
`ci_preflight` injected-root pattern; see §3.7 constraint 6).

**Binding contract:** the model **proposes** a subject string; Python **normalizes + binds**
it to a registry anchor and **HALTs (rejects, not silent NEW)** any intent whose subject
resolves to **no known anchor** or to an **ambiguous set**. No unverified subject is ever
written to a backlog item. Without this registry the entire mechanism is theater (architect
finding #1).

### 3.3 — Deterministic conflict classifier (Python disposes, fail-closed)

`features/backlog/classifier.py` — Python owns the UNRELATED/CONFLICT boundary via canonical
**anchor set-intersection** (epic §3); the model never decides UNRELATED-vs-not:

1. **Python** computes the canonical-anchor set intersection between new intents and every
   existing item. **Empty intersection → `UNRELATED`** (final, no model call).
2. For each shared-anchor pair, Python checks change-equality → **`DUPLICATE`** if identical.
3. A shared-anchor pair with **differing** change defaults **fail-closed** to
   **`DIVERGENT_CONFLICT`**. A model may only **downgrade** it (to `OVERLAP`/`SUPERSEDES`)
   with an **explicit, structured, proven-compatible merge** — it can never *miss* a
   conflict, because same-anchor+differing-change defaults to conflict.

| class | basis | meaning |
|---|---|---|
| `UNRELATED` | empty anchor intersection (Python) | no relationship |
| `DUPLICATE` | same anchors + same change (Python) | same demand |
| `OVERLAP` | anchors intersect, model-proven compatible | fold/split with cross-refs |
| `SUPERSEDES` | new replaces old (model-proven) | rewrite existing |
| `DIVERGENT_CONFLICT` | shared anchor + differing change, not proven-compatible (DEFAULT) | the dangerous twin — HALT |
| `DEPENDS_ON` | new needs old's outcome | dependency edge |

**R1 ships the deterministic core** (steps 1–2 + the fail-closed default of step 3). The
**model-adjudication step** (the downgrade path) is *exercised end-to-end* by R2's workflow;
R1's classifier exposes the seam and proves the deterministic verdicts with the model
**OFFLINE** — including the `C→D`/`C→E` `DIVERGENT_CONFLICT` (acceptance §3.7.3).

### 3.4 — `dadaia backlog doctor` (the ENFORCED backstop)

`features/backlog/doctor.py` + CLI wiring into the existing `backlog` group +
**pre-commit chokepoint + CI** integration. **Honest oriented-vs-enforced posture**
(architect finding #5): `specs/backlog/` is gitignored + ADDITIVE, so the PreToolUse/lease
gate does NOT classify a hand-written backlog file as MUTATING — the **workflow (R2) is the
ORIENTED happy-path; the doctor at the git chokepoint is the real ENFORCEMENT**. Checks:

- **BL-SCHEMA** — every item has bound `intents[]` (every subject resolves in the registry)
  + valid status.
- **BL-DUP** — two items share anchor-set + change → ERROR.
- **BL-CONFLICT** — two items share an anchor with incompatible change → ERROR (the
  divergent twin, **caught even if hand-written**).
- **BL-STALE** — a slug listed in any archived release's `consumed_backlog` **ledger**
  (mechanical exact-membership, **not NLP**) that still exists in `specs/backlog/` → ERROR.

Wiring: `backlog doctor` runs in **pre-commit** (alongside the existing lease/CI checks) and
in **CI**, so a hand-written divergent twin is **rejected at commit**, closing the
gitignore/ADDITIVE bypass.

### 3.4a — Read-only resolve/preview surface (architect finding #2 — breaks the chicken-and-egg)

The backfill (§3.5) cannot author `intents[]` against the registry if there is no way to
*see* how a proposed subject resolves before committing a backlog file. R1 therefore ships a
**read-only resolve/preview surface** as a first-class deliverable, so PE backfills against
**real** registry output (never fabricated anchors):

- **`dadaia backlog subjects`** — list the live auto-derived anchor set (optionally filtered
  by `kind`), so the author can see what `code`/`cli`/`catalog`/`doc`/`invariant` anchors
  exist right now.
- **`dadaia backlog doctor --explain`** (and/or a `backlog subjects --resolve "<ref>"`
  mode) — given a proposed subject string, show how it **resolves**: the bound canonical
  anchor, or `UNRESOLVED` / `AMBIGUOUS` with the candidate set and the actionable
  alias-map suggestion. Read-only — it never writes a backlog file or the alias map.

This fixes the R1 build/backfill sequence to:
**schema → registry + preview surface → run preview over the 14 survivors → capture
alias-map gaps (seed `.dadaia/states/backlog_subject_aliases.txt`) → author the backfill
against resolved anchors → wire BL-* into pre-commit/CI.** PE/impl backfills against REAL
anchors surfaced by this preview, never fabricated ones.

### 3.5 — Backfill the 14 survivors (owner: product-engineer, DEFINITION/CLOSURE phase)

Backfill valid **bound** `intents[]` onto all 14 surviving backlog item files (every
`specs/backlog/*.md` except `ideas.md`, `candidates.md`, and the epic itself), so each
subject resolves in the registry and **`backlog doctor` exits 0** on the live tree. The
backfill is driven by the **resolve/preview surface (§3.4a)**: run the preview over each
survivor's true subjects, capture the genuine alias-map gaps, seed
`.dadaia/states/backlog_subject_aliases.txt`, then author the bound `intents[]` against the
**real** anchors the preview surfaced — **never** a fabricated anchor. Where an item's true
subject has no registry anchor, add the appropriate **alias** entry rather than inventing a
fake anchor. Backfill is authoring of backlog content; it stays inside the
DEFINITION/CLOSURE memory-write window per constitution §13 — **but `specs/backlog/` is
ADDITIVE**, so the writes are gate-free regardless.

### 3.6 — `consumed_backlog` ledger FORMAT (R1 defines + reads; R2 writes)

Define the structured ledger schema the BL-STALE check reads. R1 obligations only:

- **Specify** the ledger shape (location + fields). Fixed by ADR-C to a **machine-readable
  JSON sidecar** at `specs/_archive/<release-id>/consumed_backlog.json` — one file per
  archived release, listing `{slug, shipped_anchors[]}` keyed by the **verified
  subject-anchor set actually shipped** in that release (epic §6). It is a sidecar JSON,
  **not** a markdown CLOSURE.md section, so BL-STALE never parses prose.
- **Read** it mechanically in `backlog doctor` (BL-STALE) by exact slug membership across
  all `specs/_archive/*/consumed_backlog.json` files, tolerating their **absence**
  (no archived ledger yet → BL-STALE is a no-op, never a false ERROR).
- **NOT** write it. The release-definition/closure **writer** is **R2**.

### 3.7 — Consolidated R1 acceptance criteria (maps from epic §9, R1 subset)

1. **Unresolved subject HALTs.** A proposed intent whose subject resolves to no registry
   anchor (or an ambiguous set) is **rejected (HALT, not silent NEW)** by the registry —
   unit-tested, with an actionable message naming the unresolved ref.
2. **Duplicate detection.** Two items with matching anchor-set + change classify
   `DUPLICATE` (Python, no model) — unit-tested.
3. **Divergent twin caught deterministically.** A `C→D`-then-`C→E` pair is classified
   `DIVERGENT_CONFLICT` by **Python set-intersection ALONE with the model OFFLINE** —
   tested with a FAKE fixture.
4. **Hand-written twin rejected at pre-commit.** A hand-written divergent twin (and planted
   BL-SCHEMA / BL-DUP / BL-CONFLICT / BL-STALE violations) is **rejected at the pre-commit
   chokepoint**; a clean tree passes — tested.
5. **Registry is live-derived.** The registry recomputes anchors from the live tree each run
   (a symbol added/removed in source changes resolution without editing any stored registry
   file); the alias map collapses a known synonym to one canonical anchor — unit-tested.
6. **Ledger read tolerates absence.** `backlog doctor` reads a structured `consumed_backlog`
   ledger for BL-STALE by exact slug membership, and is a no-op (no false ERROR) when no
   archived ledger exists — unit-tested.
7. **Live tree green.** The 14 surviving items carry valid bound `intents[]` after backfill;
   **`dadaia backlog doctor` exits 0** and `pytest` is green.
8. **Registry-consuming tests run over a fixed fixture tree (QA finding #4).** Every unit
   test that consumes the registry/classifier/doctor runs against a **fixed `tmp_path`
   fixture tree** built from inline `MINIMAL_*` constants (a minimal source tree + a minimal
   `catalog.json` + a minimal alias map), **NOT** the live repo — so the suite does not flake
   when unrelated source edits land. Live derivation is exercised by exactly one **scoped**
   test that creates and deletes its own anchor source file, and by the backfill integration
   test (§3.7.7).
9. **Pre-commit enforcement proven by a git-hook-level e2e (QA finding #5).** A
   **git-hook-level e2e** runs `dadaia ci pre-commit-check` in a fixture git repo: a planted
   divergent twin (and each planted BL-SCHEMA/DUP/CONFLICT/STALE violation) **BLOCKS** the
   commit; a clean tree **PASSES**. A doctor exit-code unit test alone does not satisfy this
   criterion.

### 3.8 — Constraints (QA findings #6–#8, binding)

- **Injected paths, never cwd lookups (QA finding #6).** The alias map
  (`.dadaia/states/backlog_subject_aliases.txt`) and the ledger
  (`specs/_archive/*/consumed_backlog.json`) are read via **explicitly injected paths**
  passed into the pure functions, never resolved from `os.getcwd()` or an ambient default.
  This mirrors the `ci_preflight` injected-root pattern; the conftest has a repo-root write
  guard, so any cwd-relative read/write would flake or be blocked.
- **Module-relative anchors only — no operator-local paths (QA finding #7, privacy).** A
  code anchor stored in a committed `intents[]` is **always** module-relative `path#symbol`
  (e.g. `dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind`). The registry must
  **never** embed an operator-local absolute path or a private repo name into a committed
  intent or alias entry; the backfill (§3.5) is held to the same rule.
- **Test pyramid + no copy-paste fan-out (QA finding #8).** The test suite follows the
  ~70 unit / 20 integration / 10 e2e pyramid. The four BL-* checks are exercised by a
  **single parameterized** test (one fixture matrix), **not** four copy-pasted test
  functions — a test-quality requirement, not just a count.

---

## 4. Out of scope (R2 / later — explicit)

- The `backlog_definition` **workflow body** (epic §4) — `dadaia lifecycle backlog define`'s
  sequenced, scoped-prompt step ladder. **R2.**
- The **removal-on-release closure hook** (epic §6) — rewrite-to-residual + full-removal +
  archive-copy at closure, and the code that **writes** the `consumed_backlog` ledger. **R2.**
  (R1 defines the ledger format and reads it; it does not write it.)
- The **real fragment prompts** (`public/lifecycle_fragments/backlog_definition/`
  `conflict-scan`, `backlog-authoring`) replacing the v0.1.24 `_README` stub. **R2.**
- The **model-adjudication step** running end-to-end (the classifier's downgrade path
  invoking a live model). R1 ships the deterministic core + fail-closed default and exposes
  the seam; **R2** exercises the model step inside the workflow.
- `context_selector.backlog_index` selector, the `_deferred.py` → real workflow swap, and
  any panel description of the backlog workflow. **R2.**
- Deleting or rewriting backlog files on consumption — never in R1 (never-delete law holds
  regardless).

---

## 5. Architecture decision records (ADRs — fixed for this release)

### ADR-A — Canonical-subject registry: auto-derived from live truth + operator alias map

The subject registry (`features/backlog/subject_registry.py`) is **recomputed from live
truth on every run**. **R1 auto-derives exactly five anchor kinds** — `code`
(AST/grep-validated `path#symbol`), `cli` (Typer command ids), `catalog` (`catalog.json`
slugs + atom ids), `doc` (spec-doc ids), and `invariant` (named invariants) — unioned with
an operator-maintained alias map at `.dadaia/states/backlog_subject_aliases.txt` (read via
an explicitly injected path, never cwd). **Panel/API ids are NOT auto-derivable in R1**: no
route registry exists, and grep-deriving them is the fuzzy heuristic this design rejects, so
`panel`/`api` subjects bind through the **alias map only** in R1; auto-derivation of those
kinds is **deferred to R2** (when a route registry can be introduced). The registry is
**never a stored registry file** (which would itself go stale — the meta-version of the bug
we fix). The model proposes a subject string; Python normalizes + **binds** it to a single
canonical anchor and **HALTs on unresolved or ambiguous**. *Rationale:* a free-text or
stored-file subject is theater (architect finding #1, REJECTED); only a live-derived typed
registry survives naming drift, and only kinds with a real registry-of-truth may be
auto-derived. *(OQ-1, OQ-5 — RESOLVED.)*

### ADR-B — Python-disposes, fail-closed conflict classifier

`features/backlog/classifier.py` owns the UNRELATED/CONFLICT boundary via canonical-anchor
**set-intersection**; the model never decides UNRELATED-vs-not. Empty intersection →
`UNRELATED` (final); same-anchor+same-change → `DUPLICATE`; **same-anchor+differing-change
defaults fail-closed to `DIVERGENT_CONFLICT`**, downgradable only by an explicit
model-proven compatible merge. *Rationale:* the dangerous twin must be caught by Python
arithmetic, not model attention — the model can only downgrade with evidence, never miss
(architect finding, epic §3). R1 ships the deterministic core; R2 exercises the model
downgrade. *(OQ-4 — RESOLVED.)*

### ADR-C — `consumed_backlog` ledger: structured + mechanical BL-STALE (not NLP)

BL-STALE keys on a **structured `consumed_backlog` ledger** fixed to a **machine-readable
JSON sidecar at `specs/_archive/<release-id>/consumed_backlog.json`** (one file per archived
release; entries `{slug, shipped_anchors[]}` keyed by the verified shipped subject-anchor
set) and matches by **exact slug membership** — replacing the prose-heuristic SPEC-DOC-031
approach and **dropping** the infeasible "match intents against archived prose" ambition
(epic §7). The sidecar JSON is deliberately **not** a CLOSURE.md markdown section: BL-STALE
reads JSON, never parses prose. R1 **defines** the ledger schema + fixes its on-disk
location (`specs/_archive/<release-id>/consumed_backlog.json`) and **reads** it (tolerating
absence as a no-op); the **writer** is R2's release-definition/closure. *Rationale:*
mechanical exact-membership over a JSON sidecar is the only honest, false-positive-free
staleness signal. *(OQ-2 — RESOLVED.)*

### ADR-D — Honest enforcement via pre-commit doctor; workflow deferred to R2

Because `specs/backlog/` is gitignored + ADDITIVE, the PreToolUse/lease gate cannot classify
a hand-written backlog file as MUTATING. The **enforced backstop is therefore
`dadaia backlog doctor` wired into the pre-commit git chokepoint + CI**, not the workflow.
The R2 workflow is the **ORIENTED happy-path**; the doctor is the **ENFORCEMENT**. R1 ships
the enforcement first so the consistency invariants hold the moment the backlog is touched —
even by hand, even before the workflow exists. *Rationale:* shipping the oriented workflow
without the enforced doctor would ship theater (architect finding #5; epic §11 slice law).

---

## 6. Dependencies and risks

### Sequencing (within R1)

- 3.1 (`intents[]` schema) is foundational — the registry, classifier, and doctor all
  consume it; lands first.
- 3.2 (registry) blocks 3.3 (classifier), 3.4 (doctor), 3.4a (preview), and 3.5 (backfill).
- 3.3 (classifier) is consumed by 3.4 (BL-DUP/BL-CONFLICT).
- 3.6 (ledger format) is needed by 3.4 (BL-STALE) — define + read before wiring the check.
- 3.4a (resolve/preview surface) lands **after** the registry and **before** 3.5 (backfill):
  backfill is authored against the anchors the preview surfaces, never fabricated ones
  (architect finding #2 — breaks the chicken-and-egg).
- 3.4 (doctor + chokepoint wiring) lands before 3.5 (backfill) so backfill is validated by
  the real exit-0 gate.
- 3.5 (backfill) is last — it is the live-tree proof that the foundation is sound. Corrected
  end-to-end sequence (§3.4a): schema → registry + preview → run preview over the 14
  survivors → capture alias-map gaps → author backfill against resolved anchors → wire BL-*
  into pre-commit/CI.

### Risk table

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Registry anchor precision / AST coverage (the linchpin).** If the auto-derived registry under-resolves real subjects (AST misses a symbol class; a surface id format is unmodeled), legitimate intents falsely HALT and backfill cannot reach exit 0; if it over-resolves (ambiguous anchors collapsed wrongly), a real conflict could be mislabeled. | HIGH | Treat the registry as the linchpin: cover code anchors via AST **and** grep fallback; unit-test each source class (code/catalog/api/cli/panel/doc/invariant) against fixtures; make HALT-on-ambiguous the default (fail-closed); give the **operator alias map** as the documented escape hatch for any real subject the auto-derivation misses — backfill (3.5) is the integration test that the registry resolves all 14 real items, with aliases filling genuine gaps rather than fake anchors masking them. |
| **`consumed_backlog` ledger has no writer in R1.** BL-STALE reads a ledger that nothing writes until R2 — risk of a check that is silently inert or falsely errors. | MEDIUM | Specify the schema in ADR-C; BL-STALE is a **no-op when absent** (never a false ERROR) and unit-tested against a hand-crafted ledger fixture so the read path is proven before R2 supplies the writer. |
| **Backfill drift — hand-authored `intents[]` may not match real subjects.** A backfilled intent could bind to the wrong anchor or invent one. | MEDIUM | Backfill is validated by `backlog doctor` exit 0 (BL-SCHEMA forces every subject to resolve); product-engineer authors against the live registry output, adding aliases for genuine synonyms, never fabricating anchors. |
| **Pre-commit chokepoint surface change.** Wiring `backlog doctor` into the pre-commit hook + CI could block legitimate commits or slow the hook. | MEDIUM | Mirror the existing CI-preflight pattern (`dadaia ci pre-commit-check` backend, shell hook); keep the check fast (registry derivation scoped, cached per run); a clean tree must pass (acceptance §3.7.4) — tested for both block and pass. |
| **Model-adjudication seam unexercised in R1.** R1 ships only the deterministic core; the downgrade path is not run end-to-end until R2. | LOW | The fail-closed default means an unexercised downgrade can only *over-report* conflict (safe); the seam is unit-tested with the model OFFLINE; R2 owns the live model step. Documented in §4 + ADR-B. |
| **`specs/backlog/` is gitignored in this source repo (privacy backstop).** New backlog files / backfilled edits stay local and may not reach CI. | LOW | The backfill targets **existing** tracked survivors (edits to tracked files commit normally); the doctor runs in pre-commit on the working tree regardless of gitignore; CI runs `backlog doctor` against the checked-out tree. |

### Memory files affected at closure (CLOSURE phase only — R1 ships no new product feature page)

- `specs/memory/architecture.md` — add `features/backlog/` to the features list
  (`subject_registry`, `classifier`, `doctor`); note `dadaia backlog doctor` +
  pre-commit/CI chokepoint wiring; note the `consumed_backlog` ledger read contract.
- `specs/memory/product/*` — only if a product atom states the backlog/governance surface;
  otherwise "no change" recorded in CLOSURE.
- `specs/memory/tech-stack.md` — no change expected (no new dependency).

### Open decisions (grill output — none blocking; all resolved)

All epic OQs are RESOLVED (epic §12): OQ-1 (subject canonicalization → typed live registry),
OQ-4 (classification → Python-disposes fail-closed), OQ-2 (ledger → structured mechanical
membership), OQ-3 (sequence → R1 before R2 before workflow-model-governance), OQ-5 (registry
source + alias policy → auto-derived + operator alias map). **No open decision blocks SPEC
approval.** The one decision deferred *by design* to R2 (not blocking R1): the exact prompt
shape of the model-adjudication downgrade step.

---

## 7. Traceability

This release **consumes the R1 slice** (§11) of backlog
`FEAT-BACKLOG-DEFINITION-WORKFLOW-01`
(`specs/backlog/backlog-definition-workflow-dedup-conflict-control.md`). At R1 CLOSURE the
backlog item is **rewritten to its R2 residual** (the workflow body, removal-on-release
hook, real fragments, and model-adjudication step survive as the R2 scope) — not deleted,
not flipped fully DELIVERED, per the never-delete law and the epic's own §3 OVERLAP→UPDATE
discipline. R2 ships as v0.1.26.
