# GRILL — Release v0.7.0 — Test stewardship

**Status:** Aprovado
**Release ID:** v0.7.0
**Kind:** grill session record (`dadaia-grill-me`, mandatory pre-SPEC session for a release
defined from the picked backlog set — `DADAIA.md` §5 (Releases))
**Session:** operator Q&A of **2026-08-12**, recorded in
`.dadaia/tmp/software-engineer/20260812/stewardship-research-dossier.md`
**Interviewer:** product-engineer · **Respondent:** operator (product owner)
**Picked set:** `specs/backlog/test-stewardship-standardization.md` (single entry, consumed
in full)
**Explicitly NOT picked:** `specs/backlog/test-suite-remediation-stewardship.md` — the
companion. This release ships the doctrine; the companion applies it to this repo's own
suite afterwards.

---

## 0. Why this record exists

`dadaia-grill-me` is a hard precondition of the SPEC when a release is defined from
bugs + backlog. This file **is** that session's record: the substrate that was inspected,
the four questions put to the operator, the answers, and the design constraints those
answers pre-resolve. The rulings below are **binding on the SPEC**; where SPEC and this
record disagree, this record wins and the SPEC is corrected.

The substrate is unusually large for a governance release and was produced *before* the
interview, so almost nothing factual had to be asked:

| Input | What it contributed |
|---|---|
| The 30-statement report (S-01..S-30, groups A–H, LIT/NOSSO honesty tags) | The doctrine itself, with each statement tagged as literature-backed or declared-ours |
| Scan 1 — tautology/tombstone/coupling census (384 files scanned, 31 deep-read) | The named worst offenders; <10% of files affected |
| Scan 2 — lifecycle mechanics | Per-axis verdicts: 2 RED, 4 YELLOW, 2 GREEN |
| Scan 3 — existing QA surface | The 13-conflict map and a single-home recommendation for every concept |

Phase 0 of the skill ("inspect before asking") was therefore discharged by the scans. Only
the four genuinely unanswerable questions — the ones that are *choices*, not facts —
reached the operator.

---

## 1. Phase 0 — what inspection already answered

Recorded per the skill's "answered via inspection" rule. None of these was put to the
operator.

| Finding | Type | Evidence found by inspection |
|---|---|---|
| The tombstone ban already exists — in `tests/AGENTS.md` "No Slop", first bullet | `[OPEN QUESTION ANSWERABLE]` | `tests/AGENTS.md:21` "Do not add tests that only prove deleted code remains deleted." The doctrine **extends** it in place; it is not new text |
| `tests/README.md` is a near-verbatim duplicate of `tests/AGENTS.md` | `[INCONSISTENCY]` | `tests/README.md` Layers/No-Slop-Policy vs `tests/AGENTS.md` Architecture/No-Slop — a live violation of the "no fact twice" law the constitution §12 states |
| `qa-engineer` frontmatter grants `tests/**`; its body forbids unit and integration tests | `[INCONSISTENCY]` | `public/agents/qa-engineer.md:48-52` (`write_allowlist: tests/**`) vs `:63` ("You never write application code, unit tests, or integration tests") |
| The coverage doctrine is split **four** ways | `[INCONSISTENCY]` | scaffold `constitution.md:44` "Cobertura mínima: **80%**" · `qa-engineer.md:169` "Coverage percentage means nothing" · `drift-detection/SKILL.md:175-182` line-coverage rubric (≥90% = 10) · `software-engineer.md:176` "Coverage is a by-product… never a target" |
| `dadaia-release-closure` has **no** test section, and its `:184` forbids the closer touching tests at all | `[DRIFT spec↔code]` | `public/skills/dadaia-release-closure/SKILL.md:184` "Writing source code, tests, or pipelines (other agents)" — demotion-at-closure has nowhere to land until this line is amended |
| The pytest marker set is **closed in six places** that must move together | `[UNDECLARED DEPENDENCY]` | `pyproject.toml:123-130` · `tests/conftest.py:118-124` `_PATH_MARKERS` · `tests/AGENTS.md` "Markers And Cost" · `specs/memory/tech-stack.md:21` · `.github/workflows/ci.yml` `-m` selectors (`:144,174,201,227,251,275`) · `features/ci_preflight/service.py:257` |
| `pytest-timeout` is **not installed**; there is zero mechanical per-test timeout | `[DRIFT spec↔code]` | absent from `pyproject.toml`; the only ceilings are CI `timeout-minutes` job caps; the local pre-push preflight is unbounded |
| `ci_preflight` still excludes a directory that does not exist | `[DRIFT spec↔code]` | `features/ci_preflight/service.py:257` `--ignore=tests/performance`; no `tests/performance/` in the tree; pinned by `tests/unit/features/ci_preflight/test_service.py:28,34` |
| Playwright CI runs `retries: 1` and reports `list` only — a pass-on-retry is **silently green** | `[DRIFT spec↔code]` | `tests/e2e/panel/playwright.config.ts:35,47-49` |
| Memory h2 headings are gated by an allowlist; `Root Cause, Always` and `Satisfiable Diagnostics` are **already** un-allowlisted | `[INCONSISTENCY]` | `specs/memory/.heading-allowlist` — neither string appears, though both are live h2s in `quality-assurance.md` |
| `quality-assurance.md` claims ~2,100 collected tests | `[STALE MEMORY]` | `:43`; the measured figure at scan time is ~2,399 |
| `tech-stack.md` omits `pytest-xdist` and `pytest-randomly` although CI runs `-n auto` | `[STALE MEMORY]` | `tech-stack.md:21` marker/tool list vs `ci.yml:144` `-n auto` |
| The scaffold constitution carries **zero** test doctrine and has free slots 8/10/12 | `[ANSWERABLE]` | `public/scaffold/constitution.md` — §5 is the only quality article and states only the 80% floor; sections present are 1–7, 9, 11, 13, 14 |
| Consumer memory template is a thin diverged PT-BR doc | `[DRIFT]` | `public/scaffold/memory/quality-assurance.md` — 4 bullets, `last_updated: 2026-01-01` |

---

## 2. Scan evidence — the RED verdicts and the named offenders

This table is the SPEC's problem statement. It is evidence, not opinion; every row was
produced by a read-only scan on 2026-08-12.

### 2.1 Lifecycle-mechanics verdicts (scan 2)

| Axis | Verdict | Evidence |
|---|---|---|
| Ownership | **RED** | 26 LARGE files / ~84 LARGE tests, **0** with a named owner. "Without clear ownership, a test rots" (S-11) |
| Flaky infrastructure | **RED** | No quarantine, no rerun recording; Playwright `retries: 1` masks pass-on-retry; the only tracking is the reactive bug ledger — **5** already-resolved flake bugs |
| Size/tier enforcement | YELLOW | Layer markers + directory auto-marking exist; **no `pytest-timeout`**, no per-test ceiling, local pre-push unbounded |
| Skips | YELLOW | 34 skips, all honest env gates, **0** carrying a plan ref; the journey spec skips permanently *locally* (`PANEL_TEST_REGISTRY` seeded only in CI) |
| Scaffold | YELLOW | `tests/tmp/` is exemplary (expiry contract); **1 orphan**: `tests/scripts/check_skill_orphans.py` has no invoker |
| Wall-clock | YELLOW | `--durations` only on integration/e2e jobs; no budget ratchet; no session timeout |
| Sleeps | GREEN | 0 bare sleeps; 1 justified settle-wait |
| Artifacts | GREEN (post-2026-08-12 bug fixes) | Residue only: dead `.gitignore:69` entry; unbounded local `os.tmpdir()` Playwright outputs; `run-panel-e2e-server.sh` never GCs temp workspaces |

### 2.2 Named worst offenders (scan 1 — all CLEAR-CUT)

| File / lines | Defect | Statement |
|---|---|---|
| `tests/unit/infrastructure/test_public_assets_doctor.py` | Byte-matches rendered output of ~10 **private** methods (`_compare`, `_dcx1..6`, `== "[ok] test:label"`) — the most implementation-coupled file in the suite | S-05 change-detector |
| `tests/unit/infrastructure/test_public_assets_hooks.py:87-190` | Hand-copies generator constants back as "expected"; also embeds old-wiring tombstone asserts (`:108,148,168`) | S-05 + S-17 |
| `tests/unit/infrastructure/runtime_transforms/test_model_mapping.py:28-30`, `tests/unit/features/telemetry/test_pricing.py:218-228` | `f(x) == f(x)` — both sides derive from the same REGISTRY comprehension | S-05 tautology |
| `tests/unit/hooks/test_root_whitelist.py:41-55` | Asserts `x in f(x)` where `f` joins `x` | S-05 tautology |
| `tests/integration/test_public_doctor_parity.py` | Whole-file self-consistency loop: install writes, the product's own doctor agrees | S-05 tautology |
| `tests/unit/core/test_harness_registry.py:110-137` | Greps product **source text** for spellings | S-05 change-detector |
| `test_no_auth_contract.py:240-269`, `test_views_api_sessions.py:190`, `test_doctor_ledger_invariants.py:595-637`, `test_model_registry_doctor.py:88-94` | ~6 tombstones — the central assertion is the **absence** of a removed feature | S-17 |

Census: unit 9 tautologies / 6 tombstones / 6 impl-coupled; contract 1 arguable;
integration 2; e2e 0. **Under 10% of files affected — the rest earn their keep.** Goldens
are the best-governed setup seen (flag-gated regeneration, no-regen meta-test, attesting
guard); residual risk is the classic S-05 reflex-regenerate.

**These offenders are named here as the release's *justification*, not its scope.** Fixing
them is the companion backlog entry (§5).

---

## 3. The decision record (operator answers, 2026-08-12 — binding)

Four questions. Each is binding; each maps to at least one FR.

### D1 — The skill is named `dadaia-test-stewardship`, and it is universal

> **Q:** The doctrine needs one operational home. Is it a new skill, and under what name and
> distribution — universal (read natively by every harness) or per-harness derived?

**A.** A new skill, `dadaia-test-stewardship`, at
`dadaia_workspace/public/skills/dadaia-test-stewardship/SKILL.md`, **universal** — no
per-harness derivation, no `public/entities/registry.json` entry, projected to all four
harness roots by `dadaia public install --target all`. Its body is groups A–H as an
operational protocol; §10 of the source report is carried inside it as **declared adjustable
defaults**, so a consumer workspace re-parameterizes without forking the doctrine.

→ **FR1.**

### D2 — The steward is verdict-only; no activity class changes anywhere

> **Q:** S-19 says the implementer never prunes and curation belongs to a steward. In this
> workspace the steward is `qa-engineer` — but `qa-engineer` is `activity_class: ADDITIVE`.
> Does it become MUTATING so it can delete tests?

**A.** **No.** The steward is **verdict-only**: `qa-engineer` issues curation verdicts —
delete / demote / quarantine — each carrying S-16 evidence with `file:line`;
`software-engineer` executes the commits. **No activity-class change anywhere**, no new
write authority, no new dispatch edge. The separation of powers S-19 demands is achieved by
splitting *sentence* from *execution*, which is exactly what makes it a separation.

Corollary the operator accepted without being asked: `qa-engineer`'s frontmatter allowlist
currently says `tests/**`, which its own body forbids. Narrow the allowlist to match the
body — the contradiction is resolved toward the body, never toward the allowlist.

→ **FR4** (qa-engineer + software-engineer text), **FR2** (law point 3).

### D3 — The parameter package (workspace defaults; consumers adjust)

> **Q:** §10 of the report isolates every number we chose ourselves. Approve them, one by
> one, as the workspace defaults?

**A.** Approved as follows.

| Parameter | Value | Note |
|---|---|---|
| LARGE (E2E) cap | **30 for `dadaia-workspace`**; abstract default **12–15 per module** | Current ~84 LARGE tests → the gap is the companion release's remediation target, **not** this release's |
| Flake rate | **< 0.5 %** of runs, **hard ceiling 1 %** | Between Google's operational 0.15 % and SWE ch11's 1 % value-loss point |
| Quarantine | max **8** tests; **30 days** → `disabled`; **+1 release** without a plan → **deleted** | Fowler's literal cap; Datadog's 30/30 escalation; the deletion step is ours |
| Per-test timeout (`pytest-timeout`) | unit **10 s** / contract **30 s** / integration **60 s** / e2e **120 s** | Bazel's model, re-scaled to this suite. A test that needs more is **mis-tiered**, never re-budgeted |
| Wall-clock budget | **frozen at the current baseline**: preflight quick **2:38**, preflight full **~5:30**, panel E2E **1:10** | Freezing the baseline forces demotion to pay its own bill |
| Mutation testing | **1× per release**, off the push path | Tool choice is a separate task; the cadence is what is being declared |
| Skip/disabled expiry | **> 1 release without a registered plan → deleted** | S-18 |

→ **FR1** (defaults inside the skill), **FR5** (the mechanically enforceable subset).

### D4 — Where the law lands: a minimal §6 increment + a consumer article + a public template

> **Q:** How much of this becomes always-on law, given that `DADAIA.md` is injected on every
> turn and already exceeds its token aspiration?

**A.** Three landings, and no more:

1. **`DADAIA.md` §6 — a five-point increment, minimal.** The law states, the skill operates.
   (i) every test declares intent **and** size; (ii) demotion is a step of closure;
   (iii) the implementer never prunes — curation is a `qa-engineer` verdict with evidence,
   executed by `software-engineer`; (iv) tombstone tests and expired SCAFFOLD are slop;
   (v) test-artifact capture is failure-gated. Plus **two single sentences**: the
   never-delete law is scoped to bugs and backlog (tests are prunable under the criteria),
   and a quarantine carve-out inside *Push green*.
2. **A new numbered article in `public/scaffold/constitution.md` — "Disciplina de Testes"**,
   so the doctrine reaches consumer workspaces at law level (free slots: 8, 10, 12).
3. **A public template of `tests/AGENTS.md`**, so a consumer repo receives the scoped rule
   file rather than a paragraph telling it to invent one.

Operational detail goes to the skill, never to the law.

→ **FR2** (1), **FR3** (2 + 3).

---

## 4. Decisions product-engineer had to make (not covered by the interview)

Recorded separately and honestly: these are **mine**, taken to make the rulings executable.
Any of them may be overturned by the operator without reopening D1–D4.

| # | Decision | Why |
|---|---|---|
| P1 | The constitution article takes slot **§8** ("Disciplina de Testes"), immediately after §7 *Mapa* and before §9 *Autoridade de Dispatch* | First free slot; keeps the quality material in the document's first half |
| P2 | The public `tests/AGENTS.md` template lives at `dadaia_workspace/public/templates/tests-AGENTS.md` and is copied into a repo by `spec_context` `alive()` **only when `tests/` already exists and `tests/AGENTS.md` does not** | `public/scaffold/**` becomes `specs/**` and cannot host it; `templates/repo-AGENTS.md` at `features/spec_context/service.py:388` is the existing, proven seam. Never create a `tests/` directory in a repo that has none |
| P3 | Intent (CONTRACT / SENTINEL / SCAFFOLD / QUARANTINE) is declared in the **module docstring** — `Intent: <KIND> — <AC id \| bug-id \| task-id>` — **not** as a pytest marker | The marker namespace already binds `contract` to the *layer* `tests/contract/`. An intent marker of the same name would silently re-tier tests and corrupt every `-m` selector in CI |
| P4 | Exactly **two** markers are added to the closed set: `flaky` and `quarantine`. `quarantine` is excluded from every gating selector and requires a bug id; `flaky` records a known intermittent that still gates | Minimum viable addition; six surfaces must move together for each new marker (§1) |
| P5 | The LARGE cap (30) is **declared and measured, reported as a WARN**, not a hard failure, in this release | The repo currently sits at ~84. A hard cap would refuse this release's own push — the enforcement turns red in the companion release, once the number is achievable. A gate that no legal action can satisfy is a defect in the gate (`quality-assurance.md` "Satisfiable Diagnostics") |
| P6 | The wall-clock ratchet is implemented as **CI `timeout-minutes` set at ≈1.5× the frozen baseline** plus `--durations` on the unit/contract jobs — no new tooling | The ceiling already exists as a first-class CI field; raising one becomes a visible diff that must be justified in CLOSURE |
| P7 | An **unregistered** Playwright pass-on-retry **fails the job**; a registered one (bug id + `quarantine`) passes | This is what makes quarantine coherent with *Push green* instead of a loophole: the flake is either loud or formally quarantined, never invisible |
| P8 | `qa-engineer`'s narrowed allowlist keeps `specs/releases/**/ALPHA-*-QA.md` alongside `tests/e2e/**` | The segment protocol (ADR-3) makes the committed alpha-N review a qa-engineer deliverable; narrowing must not strip a path the agent legitimately writes today |
| P9 | Mechanical enforcement of the **intent docstring** is *not* built in this release | 384 existing files are non-compliant; the check can only go green after the companion remediation. Declared as law now, enforced there — recorded as a backlog return |

---

## 5. The 13 conflicts as pre-resolved design constraints

Scan 3 mapped every place the doctrine's concepts already have — or wrongly have — a home.
Each row below is **a constraint on the SPEC, already decided**: the concept goes to exactly
one home and every other surface either loses it or points at it. This is the anti-slop
contract of the release: **EDIT, never append.**

| # | Concept in conflict | Single home (decided) | What must be removed / changed elsewhere |
|---|---|---|---|
| C1 | Intent taxonomy (CONTRACT/SENTINEL/SCAFFOLD/QUARANTINE) | `tests/AGENTS.md` — the "Good Test Standard" section **rewritten** as the taxonomy | `quality-assurance.md` *Layers* gains only the layer→size **mapping**, not the taxonomy prose |
| C2 | Size tiers + enforced timeouts | Mechanical: `pyproject.toml` + `tests/conftest.py`. Prose: one table in `tests/AGENTS.md` | Nothing else states the numbers; the skill carries them as *defaults*, the repo as *values* |
| C3 | Admission filter (compiles + deterministic + adds real detection) | `tests/AGENTS.md` — single owner | Not restated in `software-engineer.md`, which points at it |
| C4 | Demotion at closure (S-12/S-15) | `dadaia-release-closure/SKILL.md` — **new block** | `:184` amended: the closer does not *write* tests, it **records dispositions** |
| C5 | Deletion criteria (S-16) + tombstone ban (S-17) | `tests/AGENTS.md` — the existing tombstone bullet **extended in place** | One scoping sentence in `DADAIA.md` §6: never-delete is **bugs and backlog only** |
| C6 | Flake / quarantine pipeline | `quality-assurance.md` **new h2 "Flake Policy"** + marker/CI wiring + the law carve-out | `qa-engineer.md` references it; no second policy statement anywhere |
| C7 | Test-artifact hygiene | `DADAIA.md` §4 (the existing artifact law) — **only** the failure-gating fact is added, in §6 | Duplicated artifact prose elsewhere is subtracted, not re-worded |
| C8 | Suite health metrics + mutation cadence | `quality-assurance.md` **new h2 "Test Health"** + `tech-stack.md` tooling line | `drift-detection` Dimension E **rewritten off line-coverage** onto detection quality |
| C9 | Who prunes (steward identity) | `qa-engineer.md` persona — verdict-only | `software-engineer.md` gains a one-line "executes curation verdicts" note; nothing else |
| C10 | Consumer-facing law | scaffold `constitution.md` **§8** + `templates/tests-AGENTS.md` | scaffold `memory/quality-assurance.md` receives the doctrine pointer, not a copy |
| C11 | `tests/README.md` duplicates `tests/AGENTS.md` | `tests/AGENTS.md` is the rules file | `tests/README.md` **collapses to Commands + a pointer** — its Layers and No-Slop-Policy sections are deleted, not summarized |
| C12 | `qa-engineer` frontmatter `tests/**` vs body | The **body** wins | Frontmatter narrows to `tests/e2e/**` + `specs/releases/**/ALPHA-*-QA.md` + reports + handoff (P8) |
| C13 | Coverage doctrine, split four ways | **One stance:** the 80 % floor stays a CI gate; coverage is a **by-product metric, never an acceptance target** | All four divergent statements edited to that one stance (scaffold `constitution.md:44`, `qa-engineer.md:169`, `drift-detection:175-182`, `software-engineer.md:176`); `code-reviewer.md:144` checked for a numeric target and left alone if clean |

### Mechanical constraints riding along

| # | Constraint | Consequence for the SPEC |
|---|---|---|
| M1 | The marker set is closed in **six** surfaces (§1) | Adding `flaky`/`quarantine` is a single atomic task touching all six, or the suite silently mis-selects |
| M2 | Memory h2 headings are gated by `specs/memory/.heading-allowlist` | `Flake Policy` and `Test Health` must be appended; the two already-un-allowlisted headings are fixed in the same pass |
| M3 | CLOSURE evidence forms are closed (SHA \| fenced stdout \| report path) | Health *metrics* must be expressed in one of those three forms, or the closure skill is amended to admit a fourth. Chosen: fenced stdout — no schema change |
| M4 | `DADAIA.md` is the always-on prefix and already ~3.5 k tokens | The §6 increment is capped at **+400 tokens**, measured before and after (same cap v0.6.0 accepted) |

---

## 6. Synthesis

**Core problem resolved.** Agents create tests well and curate them badly; the workspace had
a proto-doctrine scattered across nine surfaces, contradicting itself in four of them, with
two RED mechanical axes and no timeout, quarantine or flake signal at all. After this
release the doctrine has one operational home (`dadaia-test-stewardship`), one law-level
statement (`DADAIA.md` §6, five points), one consumer landing (scaffold constitution §8 +
`tests/AGENTS.md` template), and a mechanical floor (tiered timeouts, quarantine markers,
loud flake, budget ratchet).

**Post-refinement status:** **Ready for approval.** No open question remains; every
parameter was answered with a number, not with "it depends".

**Scope boundary that must not blur.** This release **ships the doctrine**. It does not
remediate the suite: the 6 tombstones, the tautology families, the 0/26 LARGE ownership, the
orphan script and the artifact residue are the companion entry
`specs/backlog/test-suite-remediation-stewardship.md`, which stays `candidate` and is
explicitly *not* dispositioned here. A release that tried to do both would be judged on the
part that is easiest to measure and would ship the doctrine untested against reality.

**Decisions recorded, with their FR:**

| # | Decision | Consumed by |
|---|---|---|
| D1 | `dadaia-test-stewardship`, universal skill, groups A–H + §10 defaults | FR1 |
| D2 | Steward is verdict-only; no activity-class change; allowlist narrows to the body | FR2, FR4 |
| D3 | The parameter package (LARGE cap, flake ceiling, quarantine caps, timeout tiers, frozen wall-clock, mutation cadence, skip expiry) | FR1, FR5 |
| D4 | Law lands as a 5-point §6 increment + scaffold constitution §8 + public `tests/AGENTS.md` template | FR2, FR3 |
| C1–C13 | Single-home map — edit, never append | FR4, FR6, FR7 |
| P1–P9 | Product-engineer's own executable choices | FR1–FR7 |
