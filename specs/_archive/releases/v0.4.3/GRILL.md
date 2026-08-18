# GRILL — Release v0.4.3 — claims-made-true / backlog-zero

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-17 (fila inteira em 1 release — goal directive)
**Release ID:** v0.4.3
**Owner:** product-engineer
**Session:** 2026-08-17 — mandatory `dadaia-grill-me` on the picked set (`dd-release-definition` §3)
**Scope:** the whole `## ACTIVE` queue + 2 folded external items; no bug (zero open), no audit outstanding

---

## 0. What this document is

A **pointer**, not a copy. The grill itself is a four-file report set; reproducing its
dossiers here would create a second writer for the same facts — the defect class the
previous release removed. This file records only what the release documents must be able
to cite without opening the report: where the grill lives, what it concluded numerically,
which rulings answered its open decisions, and what changed in the world between the
grill snapshot and this definition.

## 1. The grill report set (authoritative, read it there)

| Part | Path | Contents |
|---|---|---|
| index | `.dadaia/reports/dadaia-workspace/product-engineer/2026-08-17T143000Z-v0.4.3-grill.html` | summary, 26-row per-entry verdict table, the five shape-changing divergences, evidence, next action |
| part 1 | `…-v0.4.3-grill-part1-dossiers.html` | one dossier per record: what it asks, provenance/age, verification against the tree, true remaining scope, lane, size |
| part 2 | `…-v0.4.3-grill-part2-divergences.html` | the 25-finding divergence matrix (D1–D25) + the merge/disposition table |
| part 3 | `…-v0.4.3-grill-part3-vision.html` | six workstreams WS-0…WS-F, the wave order and its constraints, the complexity/LOC governance FR, the zero-residual mechanics, 8 risks, 9 open decisions |
| handoff | `.dadaia/handoff/dadaia-workspace/2026-08-17T143200Z-product-engineer-v0.4.3-grill.handoff.json` | machine record: 14 findings, 9 `decisions_required`, the metric block |

Tree at grill time: `develop` `84a66d13`, READ-ONLY dispatch — no SPEC authored, no
backlog mutated, no pick flipped. **D1–D25, the 26 verdicts and WS-0…WS-F stand as
written** except where §3 below adjusts them.

## 2. Numeric result (carried, not re-derived)

26 records dossiered · 25 divergences (4 HIGH / 9 MEDIUM / 9 LOW / 3 INFO) ·
21 IMPLEMENT + 2 MERGE + 1 operator ruling + 1 recommended disposition + 1 routed out of
release (Arm B) · 6 workstreams · 9 open decisions · 8 risks · 16 code anchors verified ·
3 records found stale or partly void · 2 new defects found outside the queue (PE-1, PE-2).

## 3. Dispatcher rulings on the nine open decisions

All nine were ruled on 2026-08-17, **operator-delegated ruling**. They are recorded as
ADRs **R1–R9** in `SPEC.md` §2, which is their authoritative statement; the table below
is the index from the grill's decision id to the ADR that closed it.

| Grill OD | Question | Ruling | ADR |
|---|---|---|---|
| OD-G | segmented or flat? | **SEGMENTED**, the grill's wave order, schema-v2 cadence, qa-only per `alpha-N`, full trio + CLOSURE at `rc-1` | R1 |
| OD-F | #32's unsatisfiable acceptance | **rewritten** — scope is the two exact-duplicate `dd-` pairs only; `applyTo: "**"` globs are by design and out of scope | R2 |
| OD-D | #34 delivered or one sentence? | the **honest terminal the HEAD verification dictates** — see §4 | R3 |
| OD-E | `bugs.jsonl` sharding idea | **REJECTED** — complexity > value (3 shapes / 4 consumers / 2 laws); revisit only on a measured problem | R4 |
| OD-C | CHANGELOG backfill shape | **minimal honest form** — compact retroactive section per published version lacking one, derived from git history, no invention; the 3 phantom headings annotated as unpublished-internal, nothing deleted | R5 |
| OD-B | standing OD-2 disposition token | **no new disposition token**; #12 implements within its own scope | R6 |
| OD-H | #5's environment | a **throwaway REAL workspace** via `dadaia init` under the workspace tmp; limits recorded honestly | R7 |
| OD-I | complexity ceiling basis | **MEASURED RATCHET** — ruff `C90`/`C901` + `PLR1702` pinned at the observed maxima, ratchet-only-down, plus a mandatory `## Size accounting` CLOSURE table. Never aspirational | R8 |
| OD-A | de-personalise the git identity | **stays the operator's**; restated in CLOSURE | R9 |

## 4. HEAD verification the rulings required

**R3 / #34 — both halves measured at HEAD (`feature/0.4.3`).** The always-on *pointer*
the record prescribes **exists**: `dadaia_workspace/public/data/DADAIA.md:235-236` ends
the register-every-bug paragraph with "Command, redaction rule and context routing:
`dd-bug-registration`." The *content* half is **absent**: no always-on sentence names
what the rule forbids. Honest terminal, therefore, is both — the pointer half is
`DELIVERED` against that anchor and is recorded as such; the missing sentence is
implemented exactly (SPEC FR4). No rehydration of the dehydrated block.

## 5. State changes since the grill snapshot (verified before authorship)

| Grill item | Status now | Evidence |
|---|---|---|
| **D17 / PE-1** — the pick-blocking open bug names a symbol absent at HEAD | **DEAD** — closed by Arm B on `develop` | `specs/bugs/bugs.jsonl:889` `resolved` (2026-08-17T13:34:22Z): the normalizer deleted, 38 lines removed / 0 added, full gate green |
| the incidental orphan factory found while closing it | **closed the same way** | `bugs.jsonl:890-891` — `_memory_catalog_regenerator` reported and `resolved` (22 lines removed), cascade boundary stated |
| pick precedence | **clean — no bug outranks** | zero open bugs; the two 2026-07 audits stay archived and fully dispositioned |
| the 25th `ACTIVE` entry `dadaia-artifact-event-driven-gc` | **NEW, in the pick as WS-G** | operator-created in a parallel session (`84e369a0`), direct ADR #15 intake; the standing order "fila inteira em 1 release" brings it in, sequenced after WS-F |
| **PE-2** — `tech-stack.md:16` claims version `0.5.0` | **still false, scheduled** | `pyproject.toml:3` reads `0.4.2`; fixed in the `rc-1` CLOSURE memory window (SPEC §5) |

WS-G was not in the grill's six workstreams — it did not exist at snapshot time. Its six
capabilities plus the `dadaia tmp gc` backstop are specified as FR25–FR31 from the
entry's own intents and its evidence report
(`.dadaia/reports/dadaia-workspace/claude/2026-08-17T132142Z-dadaia-ttl-strategy.html`);
its L-size risk is carried in SPEC §6.

## 6. What this grill does **not** re-open

The 25 divergences and the per-entry verdicts are settled input. Where an entry's own
text and the code disagreed, the code won and the disagreement is recorded in the report
set. Nothing in `SPEC.md`, `PLAN.md` or `TASKS.md` re-litigates a D-finding; they cite
them (`D5`, `D10`, `D12`, `D17`, `D18`, …) as constraints.
