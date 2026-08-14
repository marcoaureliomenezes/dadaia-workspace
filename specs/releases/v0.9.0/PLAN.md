# PLAN — Release v0.9.0 — Push-range denylist scan

**Status:** Aprovado
**Release ID:** v0.9.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.9.0/SPEC.md`
**Grill:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T130830Z-refine-specs.html`
**Branch:** `feature/v0.9.0` (cut from `develop` at `1883b85b`; branch contract: `dadaia-gitflow`)

---

## 1. Strategy

This release adds one policy to an existing gate and one opt-in output mode to three
diagnostic verbs. Four properties shape every choice below.

1. **The pure module stays pure.** `features/chokepoints/service.py` is business logic
   that "NEVER imports `infrastructure` and NEVER spawns a subprocess" (`:1-14`). Git object
   access therefore arrives as an injected port, exactly as `ProcessAncestry` already does
   for `pre_commit_decision` (`cli/commands/ci.py:114-138`). Nothing in the decision path
   touches a subprocess; every unit test injects a fake and runs with no git.
2. **RED before GREEN.** Each behavioral FR gets its failing test first — the leak this
   release closes is a *missing* refusal, so a test that fails because the push is allowed
   is the honest starting point.
3. **The term sources already exist.** The operator denylist loader, the packaged
   structural baseline and its `exclude_regex` carve-outs are shipped and tested
   (`infrastructure/privacy_check.py`, `infrastructure/data/privacy_baseline.json`). This
   release **reuses** them behind a public accessor; it does not fork a second denylist.
4. **Flat release, one implementation increment.** No `alpha-N` / `rc-N` segment: there is a
   single increment, closed by one `qa-engineer` review committed to the branch (T-090-10) —
   the `alpha-N` obligation discharged in flat form. Security review runs at both merge
   milestones, unchanged; `code-reviewer`'s six-axis pass rides milestone (b).

---

## 2. Layers affected

| Layer | What moves |
|---|---|
| `core/protocols/` | **new** `git_object_reader.py` — `GitObjectReader` Protocol + a frozen `ScannedObject` dataclass (`path`, `sha`, `text`, `decodable`). Zero I/O, per the `core` ring rule |
| `features/chokepoints/` | **new** `denylist_scan.py` — the pure matcher (terms × patterns × slugs → hits, masking, message composition). `service.py` — `push_gate_decision` gains an injected object source and the scan step |
| `infrastructure/` | `git_subprocess.py` (266 lines) gains the `rev-list --objects` + `cat-file` adapter, or a sibling `git_objects.py` if that file passes ~450 lines. `privacy_check.py` exposes a public `load_privacy_terms()` / `load_baseline_patterns()` accessor over today's private loaders |
| `cli/commands/ci.py` | `push_gate_check` (`:226`) wires the adapter, the term sources and the foreign-slug set, and fails closed on a git failure |
| `cli/commands/doctor.py`, `cli/commands/context.py` | `--redact` flag on `doctor`, `context list`, `context show`; a shared redaction helper applied at the render boundary only |
| `dadaia_workspace/public/agents/qa-engineer.md` | the redaction doctrine line (canonical source → re-projected) |
| `specs/memory/` | four atoms updated at CLOSURE (SPEC §5) |
| `tests/` | unit (matcher, decision, redaction), contract (CLI wiring, default-output stability, no-amnesty grep), integration (CLI verb over a real temp repo), e2e (planted-term journey) |

---

## 3. Execution order

```
T-090-01  commit definition content on feature/v0.9.0 (trio + ACTIVE.md → IMPLEMENTATION)
   │
   ▼
T-090-02  milestone (a): merge → develop · security review · push develop
   │
   ▼
T-090-03  port + adapter: GitObjectReader, ScannedObject, git object listing/reading
   │
   ▼
T-090-04  pure matcher: denylist_scan.py (terms, slugs, baseline, masking, message)
   │        ├── depends on T-090-03 only for the ScannedObject shape
   ▼
T-090-05  wire the scan into push_gate_decision (branch + tag ref sets, policy order)
   │
   ▼
T-090-06  CLI wiring in ci.py push_gate_check + fail-closed on git failure
   │
   ▼
T-090-07  FR8a: --redact on doctor / context list / context show   ← disjoint write set
   │
   ▼
T-090-08  FR8b: doctrine line in the qa-engineer canonical source + re-projection
   │
   ▼
T-090-09  e2e journey + FR7 timing measurement
   │
   ▼
T-090-10  qa-engineer review of the increment (flat alpha-close), committed to the branch
   │
   ▼
T-090-11  memory update (CLOSURE phase) — four atoms + catalog if frontmatter moved
   │
   ▼
T-090-12  CLOSURE.md · dispositions · ACTIVE.md → ARCHIVED · release dir → _archive
   │        version bump + CHANGELOG entry
   ▼
T-090-13  milestone (b): merge → develop · security review · push · PR develop→main · CI green
```

**Sanctioned parallel pair:** T-090-07 (`cli/commands/{doctor,context}.py` +
`features/spec_context/doctor.py` render sites) has a write set disjoint from
T-090-03…T-090-06 (`core/protocols/`, `features/chokepoints/`, `infrastructure/`,
`cli/commands/ci.py`). Two `[-]` markers are permitted **only** for that pair, and only
while both TASKS entries name their disjoint sets. Everything else is strictly serial.

---

## 4. Phases

### Phase 0 — DEFINITION (product-engineer, done at authoring)

Author `SPEC.md`, `PLAN.md`, `TASKS.md`; point `ACTIVE.md` at `v0.9.0` / `DEFINITION`.
Nothing is committed by the author — `product-engineer` has no shell. Memory is **not**
written in this phase: this release changes behavior, so memory tells the truth only after
the behavior exists (CLOSURE).

### Phase 1 — Approval and milestone (a)

Operator approves the trio (`Em revisão` → `Aprovado`, three files). `ACTIVE.md` advances
to `IMPLEMENTATION`; the definition content is committed (T-090-01) and milestone (a) fires
(T-090-02): merge into local `develop`, diff-based `security-reviewer` review of
`origin/develop..develop`, push `develop` — in that order.

### Phase 2 — The scan (T-090-03 … T-090-06)

Built bottom-up so each layer is provable without the one above it:

- **Port + adapter.** `GitObjectReader.new_objects(repo, local_sha, remote_sha)` returns
  `ScannedObject`s for the FR1 range; the adapter runs `git rev-list --objects` and reads
  each blob (`git cat-file --batch`), decoding UTF-8 and marking undecodable blobs
  `decodable=False` instead of raising. Any non-zero git exit raises a typed error the CLI
  maps to a refusal (FR6).
- **Pure matcher.** `scan_objects(objects, terms, patterns, slugs)` → ordered hits
  (`path`, `line`, `masked_term`, `source_layer`). Term matching is case-insensitive
  substring for operator terms, compiled regex with `exclude_regex` for baseline patterns,
  word-boundary regex for foreign slugs. Masking (`first…last`) happens inside the matcher,
  so an unmasked term never reaches a `Decision`.
- **Decision.** `push_gate_decision` computes a scan ref set independently of `review_refs`
  (`service.py:344`) — every non-deletion ref, tags included — and evaluates: malformed
  stdin → branch policy → **scan** → security verdict. Branch policy stays first because it
  is free and pure; the scan precedes the verdict lookup so a leaking push is refused for
  the leak, not for a missing handoff.
- **CLI.** `push_gate_check` builds the adapter, loads terms + baseline, derives foreign
  slugs from `<workspace>/repos/` minus the pushed repo's own slug, and passes them in. Git
  failure → refuse with the failure named. No object source → refuse (FR6 row 4).

### Phase 3 — The entry path (T-090-07, T-090-08)

A single redaction helper maps context names to stable ordinal placeholders and is applied
**at the render boundary only** — the services keep returning true names, so no internal
consumer is corrupted. `--redact` is opt-in on all three verbs, table and `--json`. The
doctrine line is authored in `dadaia_workspace/public/agents/qa-engineer.md` and propagated
with `dadaia public stage` → `install --target all` → `doctor`.

### Phase 4 — Prove and close (T-090-09 … T-090-13)

The e2e journey plants a term in a throwaway repository, proves the refusal, removes the
term, amends, proves the clean push. Timing is measured on this release's own range.
`qa-engineer` closes the increment (T-090-10). Memory is written in CLOSURE phase
(T-090-11) *before* `CLOSURE.md` (T-090-12), per the finalization order memory → CLOSURE →
archive. T-090-13 ships.

---

## 5. Validation plan

| # | What is validated | How | Evidence for CLOSURE |
|---|---|---|---|
| V1 | Range scope (A1.1–A1.4) | unit tests over injected fake object sets: term in range → refuse; term only behind `remote_sha` → allow; deletion → no scan; dedupe by sha | test ids + `pytest` output |
| V2 | Tag coverage, carve-out intact (A2.1–A2.4) | unit: tainted tag → refuse; clean tag → allow with **no** verdict lookup; deletion unchanged | test ids |
| V3 | Term sources + self-slug (A3.1–A3.5) | unit with and without an operator denylist file; own-slug guard; word-boundary slug; baseline excludes | test ids + the stderr mode line |
| V4 | No amnesty + FROZEN↔scan (A4.1–A4.2) | grep contract test for an allowlist constant; integration over a temp repo: `git mv` into `_archive/` → clean, edit → refuse | grep result + integration test id |
| V5 | Satisfiable, non-leaking diagnostic (A5.1–A5.4) | unit asserting message fields present, unmasked term absent from stdout+stderr, line content absent, 10-item cap | captured message in CLOSURE (with a synthetic term) |
| V6 | Fail-closed / fail-open (A6.1–A6.3) | unit: git failure → refuse; binary blob → skipped + counted; contract test on the CLI wiring | test ids |
| V7 | Purity + budget (A7.1–A7.3) | import-linter + import-surface tests green; measured wall clock of the scan over this release's push range | linter output + timing figure |
| V8 | Redaction (A8.1–A8.5) | unit + integration on all three verbs, table and `--json`; default-output stability contract; `dadaia public doctor` after projection | test ids + `public doctor` stdout |
| V9 | End-to-end journey (A9.1) | throwaway repo: planted term refused at `pre-push`, clean after amend | e2e test id + captured output |
| V10 | Suite green (A9.2) | `dadaia ci preflight` before each push; full `pytest` locally | preflight output |
| V11 | Test intents declared (A9.3) | every new test module carries `Intent: …` | grep over the added modules |
| V12 | Memory atomic (SPEC §5) | `dadaia specs doctor` green; no changelog/history section added; catalog regenerated only if frontmatter moved | doctor stdout |

---

## 6. Technical risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | The scan blocks this repository's own pushes on its own slug | A3.2 regression guard written **before** the slug layer is wired (T-090-04) |
| R2 | `--not --remotes` on a fresh branch enumerates a huge range | Row 1 of FR1 (stdin `remote_sha`) is the normal path; dedupe by sha; a blob-size guard skips oversized blobs as undecodable-equivalent and counts them |
| R3 | The pure module acquires a subprocess import under time pressure | Port + adapter split is the first task of Phase 2; A7.1 is checked by tooling that already exists |
| R4 | Baseline patterns produce noisy false positives on legitimate new content | Only NEW objects are scanned; `exclude_regex` honored; any real false positive is a registered bug, not a reason to add an amnesty list (ADR #3b) |
| R5 | `--redact` changes a stable JSON contract for existing consumers | A8.2: default output pinned unchanged by contract test; `--redact` is opt-in |
| R6 | Redaction applied inside a service corrupts internal consumers | Applied at the render boundary only (Phase 3) |
| R7 | The refusal message itself becomes the leak | Masking inside the matcher; A5.2 asserts the unmasked term appears nowhere in output |
| R8 | The parallel pair drifts into overlapping writes | Both TASKS entries name their write sets; any overlap discovered → serialize and note it in CLOSURE as a drift |

---

## 7. Rollback

Every change is additive behind a policy step and an opt-in flag. Reverting T-090-05 and
T-090-06 restores the previous push-gate behavior exactly (branch policy + security
verdict); reverting T-090-07 removes the flag with no effect on default output. The port,
adapter and matcher are inert without the wiring, so a partial revert leaves no half-armed
gate. Nothing in this release rewrites history or moves an archived file, so no step is
irreversible before T-090-12's release-directory move.
