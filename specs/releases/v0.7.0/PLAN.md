# PLAN — Release v0.7.0 — Test stewardship

**Status:** Aprovado
**Release ID:** v0.7.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.7.0/SPEC.md`
**Grill:** `specs/releases/v0.7.0/GRILL.md`
**Branch:** `feature/v0.7.0` (cut from `develop`; branch contract: `dadaia-gitflow`)

---

## 1. Strategy

This is a **governance release with a mechanical tail**. Roughly 80 % of the work is text on
the `public/` surface plus two repo-scoped rule files; the remaining 20 % is Python and YAML
that makes the text unavoidable. The strategy follows from one constraint: *nothing may
defer to something that does not exist yet*.

Four properties drive every ordering decision below:

1. **The skill is the sink.** Twelve surfaces will end up saying "see
   `dadaia-test-stewardship`". It is authored first, alone, so every later edit can delete
   text instead of inventing where to send the reader.
2. **The law is second, and stays thin.** `DADAIA.md` is injected on every turn. Five points,
   two sentences, zero numbers. Every operational value belongs to the skill (defaults) or
   to the repo (values).
3. **Consumer surface before agent surface.** Agents will cite `constitution §8`; the article
   must exist first or v0.6.0's A6.2 citation check goes red again.
4. **Edit, never append.** The 13 conflicts (GRILL §5) are pre-resolved. Every tier-2 edit is
   a *relocation*: a rule leaves a file only when it demonstrably lives elsewhere. The A4.1
   grep is the proof, and it is run twice — by the author and independently by QA.

The mechanical work is TDD in the strict sense: the tier→timeout mapping, the
quarantine-needs-a-bug-id rule, the marker-set pin, and the scaffolder's three-case copy
are all pure contracts with observable outcomes. They are written RED, proven failing for the
real reason, then implemented. The CI-side work (flake detection, durations, ceilings) is
proven by demonstration on the branch, not by unit test — with the demonstration output
captured, because a CI rule nobody ever fired is a claim.

---

## 2. Layers affected

| Layer | What moves |
|---|---|
| Law (`public/data/DADAIA.md`) | §6 five-point block + never-delete scoping sentence + push-green quarantine carve-out. Source only; four `0444` projections regenerated |
| Skills (`public/skills/`) | **new** `dadaia-test-stewardship`; edits to `dadaia-release-closure`, `drift-detection`, `project-orchestration` |
| Agents (`public/agents/`) | `qa-engineer` (steward duties + frontmatter narrowing + coverage), `software-engineer` (executes verdicts + coverage) |
| Consumer scaffold (`public/scaffold/`, `public/templates/`) | constitution **§8**; **new** `templates/tests-AGENTS.md`; `scaffold/memory/quality-assurance.md` sync |
| Repo-scoped rules (`tests/`) | `tests/AGENTS.md` rewritten; `tests/README.md` collapsed |
| Package code | `features/spec_context/service.py` (template copy seam, `:387-390`); `features/ci_preflight/service.py` (dead `--ignore`, quarantine exclusion) |
| Test harness | `pyproject.toml` markers + `pytest-timeout` dep; `tests/conftest.py` tier timeouts + marker rules |
| CI / E2E config | `.github/workflows/ci.yml` (`-m` selectors, `--durations`, `timeout-minutes`, flake-detection step); `tests/e2e/panel/playwright.config.ts` (JSON reporter outside the repo) |
| Memory (CLOSURE phase only) | `quality-assurance.md`, `tech-stack.md`, `public-asset-distribution.md`, `architecture.md`, `index.md`/`catalog.json`, `.heading-allowlist` |

---

## 3. Execution order

The chain is deliberately serial at the top and forks once the skill and the law exist.

```
T-070-01  skill                        (nothing may defer to a non-existent skill)
   ↓
T-070-02  DADAIA.md §6 + projection    (the law delegates to the skill)
   ↓
T-070-03  consumer surface             (constitution §8 + template + memory template)
   ↓
   ├── T-070-04  tier-2 single-home edits (public/** text + tests/*.md)   ─┐  sanctioned
   └── T-070-05  markers/timeouts/preflight (package + pyproject + tests) ─┘  parallel pair
                                        ↓
   ┌── T-070-06  CI + Playwright flake detection  ─┐  sanctioned
   └── T-070-07  scaffolder wiring (spec_context)  ─┘  parallel pair
                                        ↓
T-070-08  QA alpha-1 on the live instance
   ↓
T-070-09  code review + diff-based security verdict
   ↓
T-070-10  milestone (b): merge → push → PR → CI green → merge
   ↓
T-070-11  memory → CLOSURE → archive
```

**Why each edge exists**

- **01 → 02.** The law's five points end with "operational detail: `dadaia-test-stewardship`".
  Writing the law first would either duplicate the protocol or dangle.
- **02 → 03.** The scaffold constitution article points at the law and the skill; a consumer
  article that cites a law paragraph not yet written is the drift this release exists to end.
- **03 → 04.** `qa-engineer.md` and `software-engineer.md` will cite `constitution §8`.
  A3.2 re-runs v0.6.0's citation check; §8 must exist when the citation lands.
- **04 ∥ 05.** Disjoint write sets: `public/**` + `tests/AGENTS.md` + `tests/README.md`
  (text) vs `pyproject.toml` + `tests/conftest.py` + `features/**` + `tests/unit/**` (code).
  No file appears in both.
- **05 → 06.** CI selectors reference marker names. The markers must exist before a `-m`
  selector can exclude them, or the pipeline fails on an unknown marker.
- **06 ∥ 07.** Disjoint: workflow YAML + Playwright config vs `features/spec_context/` +
  its unit tests.
- **07 → 08.** QA validates the whole contract from the live instance, including the
  scaffolder's three cases.
- **10 → 11.** Memory is written in the **CLOSURE** phase — the memory path class is
  phase-gated (`DADAIA.md` §3). `ACTIVE.md` phase flips to `CLOSURE` **before** the first
  memory write. Finalization order is **memory → CLOSURE → archive**.

**Projection chain after every task that touches `dadaia_workspace/public/`** (01, 02, 03,
04): `dadaia public stage` → `dadaia public install --target all` → `dadaia public doctor`.
This is not optional and it is not deferred to the end — v0.6.0's alpha-1 QA rejected
precisely because a source edit landed without a completed re-projection.

---

## 4. TDD contracts (what is written RED first)

| Contract | Test location | The real failure it must show |
|---|---|---|
| Tier→timeout mapping, four layers | `tests/unit/` (conftest behavior) | Before the change: no `timeout` marker is applied at all |
| Explicit `@pytest.mark.timeout` is never overridden | same | Before: the fixture does not exist, so precedence is undefined |
| `quarantine` without a bug id errors at collection | `tests/contract/` | Before: the marker does not exist; after the marker is added but before the rule, a bug-less quarantine collects silently |
| Marker-set pin: `pyproject.toml` ≡ `conftest.py` known markers | `tests/contract/` | Before: the two can diverge with no signal — the M1 drift risk made visible |
| Every gating selector excludes `quarantine` | `tests/unit/features/ci_preflight/` | Before: `ci_preflight` passes no `-m` at all |
| `--ignore=tests/performance` is gone | `tests/unit/features/ci_preflight/test_service.py` | The existing pin at `:28,34` is the RED — it asserts the dead flag's presence |
| Scaffolder copies `tests/AGENTS.md` when `tests/` exists and the file does not | `tests/unit/features/spec_context/` | Before: nothing is copied |
| Scaffolder leaves an existing `tests/AGENTS.md` byte-identical | same | Before: no code path exists to leave alone |
| Scaffolder creates **no** `tests/` directory when absent | same | Before: vacuous; after a naive implementation, this is the test that catches `mkdir(parents=True)` |

Everything else — the CI flake gate, the durations, the ceilings — is proven by
**demonstration with captured output** on the branch (SPEC A5.5), because its execution
environment is GitHub Actions, not pytest.

---

## 5. Validation plan

| # | What | Command / method | Owner |
|---|---|---|---|
| V1 | Projection integrity after every text task | `dadaia public doctor` → `[ok] public-privacy`, zero drift, four `0444` byte-identical `DADAIA.md` | ai-engineer |
| V2 | Law token growth | Token count of `public/data/DADAIA.md` before and after; cap **+400** | ai-engineer |
| V3 | Citation resolution | Extract every `constitution §N` in `public/agents/**` + `public/skills/**`; intersect with the scaffold's section set; expect empty difference | ai-engineer |
| V4 | Relocation (A4.1) | Grep `SENTINEL`, `SCAFFOLD`, `QUARANTINE`, `tombstone`, `demotion` across `public/`, `tests/AGENTS.md`, `tests/README.md`; every hit resolves to the skill, the law, `tests/AGENTS.md`, or a reference | ai-engineer **and** qa-engineer, independently |
| V5 | Coverage stance (A7.1) | Grep coverage statements in `public/`; exactly four sites, one stance; no line-% score anchor | ai-engineer |
| V6 | Suite under the new timeouts | `pytest -p no:cacheprovider -q` (full) | software-engineer |
| V7 | Quality ladder | `ruff format --check`; `ruff check`; `mypy --strict`; `lint-imports --config setup.cfg --no-cache` | software-engineer |
| V8 | Quarantine exclusion | A quarantined sample runs under `-m quarantine` and does **not** run in any gating selector | software-engineer |
| V9 | Flake gate fires | Deliberately flaky throwaway spec → panel E2E job **fails** on unregistered pass-on-retry; output captured; spec removed in the same task | software-engineer |
| V10 | Doctors | `dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor` all exit 0 on this live instance | qa-engineer |
| V11 | Consumer landing | Scaffolder unit tests (three cases) + a read of the generated `tests/AGENTS.md` for placeholder correctness | qa-engineer |
| V12 | Memory truth (A6.2) | Every number in memory cross-checked against `pyproject.toml`, `conftest.py`, `ci.yml`, `tests/AGENTS.md` | qa-engineer (not the author) |

**Baselines to capture before any change** (they become the frozen reference recorded in
CLOSURE, and V12 checks memory against them): collected test count; LARGE (e2e) test count;
preflight quick wall-clock; preflight full wall-clock; panel E2E wall-clock;
`DADAIA.md` token count.

---

## 6. Risks — the four that will actually bite

Full register in SPEC §5. These four shape the plan itself.

### R1 — Marker-set drift (six surfaces must move together)

`pyproject.toml`, `tests/conftest.py`, `tests/AGENTS.md`, `specs/memory/tech-stack.md`,
`.github/workflows/ci.yml`, `features/ci_preflight/service.py`. A marker added to five of six
produces a suite that silently selects the wrong tests — the worst failure mode in this
release, because it is green.

**Plan response:** the six are **one task** (T-070-05, with `ci.yml` following immediately in
T-070-06 as the only split, justified by its disjoint environment), the write set names all
of them explicitly, and A5.3's contract test pins `pyproject.toml` against `conftest.py`
permanently so the pair cannot drift again after this release.

### R2 — "Quarantine" read as a green-with-exclusions violation

A future agent reads *Push green* and the quarantine marker and concludes the push law was
loosened.

**Plan response:** the carve-out sentence is mandatory in the same edit that introduces the
marker (never in a later task), and it is paired: quarantine costs a **registered bug** and
**expires**, and an unregistered pass-on-retry **fails the job**. The net posture is stricter
than today, where the flake is simply invisible. QA verifies both halves exist before
approving.

### R3 — `DADAIA.md` token cap (+400, again)

The always-on prefix already sits at ~3.5 k against a ≤3 k aspiration; v0.6.0 spent its
budget on the branch law.

**Plan response:** the law carries **no number and no marker name** (A2.4) — five imperative
sentences plus two clauses. The measurement is taken before and after in T-070-02 and
reported regardless of outcome. If the increment exceeds +400, the fix is to cut law text,
never to raise the cap.

### R4 — Agent truncation on long text tasks

T-070-04 touches seven files and must *remove* text from most of them. A sub-agent that runs
out of turns leaves a half-relocated governance surface — the exact state this release exists
to end.

**Plan response:** every dispatch carries an **economy directive**: read only the files named
in the write set, edit in place, do not explore the tree, do not re-derive the conflict map
(it is in GRILL §5, already decided). T-070-04 is explicitly declared splittable at execution
time — an implementer may close it in two commits over two dispatches without a spec
amendment, provided the A4.1 grep is clean at the end. The task's Done criterion is stated
per-file so partial progress is legible to the next dispatch.

---

## 7. Segment and ship

Segment `alpha-1`. Per ADR-3 the segment closes with a **qa-only** review committed to the
branch (T-070-08); the full trio (code + security) is T-070-09, and the release CLOSURE +
archive happen at ship. Milestone (a) — definition trio `Aprovado` → merge to local
`develop` → diff-based security review of `origin/develop..develop` → push `develop` — is
executed by the coordinator on approval of this trio, not by a task in this file. Milestone
(b) is T-070-10.

If T-070-08 returns **REJECTED**, the offending tasks return to `[-]` and the rejection is
preserved verbatim in `specs/releases/v0.7.0/ALPHA-1-QA.md` as the historical record. That is
what happened in v0.6.0 and it is the intended behavior of the segment, not an incident.
