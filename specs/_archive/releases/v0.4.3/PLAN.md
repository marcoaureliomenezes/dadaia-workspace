# PLAN — Release v0.4.3 — claims-made-true / backlog-zero

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-17 (fila inteira em 1 release — goal directive)
**Release ID:** v0.4.3
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.3/SPEC.md`
**Source GRILL:** `specs/releases/v0.4.3/GRILL.md`
**Branch:** `feature/0.4.3` (cut from `develop` at `84e369a0`; branch contract: `dadaia-gitflow`)
**Segments:** `alpha-1` … `alpha-6` → `rc-1` (ADR R1, order amended by **R10**). Cadence:
qa-only per `alpha-N`; full trio + CLOSURE + archive at `rc-1`.

---

## 1. Strategy

Twenty-five records, six increments, one ordering principle: **measure before you rule,
state after you ship.** Every rule this release adds is pinned to a number the release
itself measured (FR18's census, FR21's complexity maxima, FR22's byte baseline, FR13's
twelve warnings), and every doctrine statement lands after the behaviour it describes.

The segment order is not a preference — each boundary is a constraint from the grill's
divergence matrix or a dispatcher ruling:

- **`alpha-1` first** because eight of the cheapest records share **one** projection cycle,
  because FR1's pin rule must exist before FR20 wires a sixth third-party tool (D-2), and
  because the Codex renderer in `alpha-4` consumes the persona/skill frontmatter this
  segment corrects.
- **`alpha-2` next** because the three FRs that rewrite the same 5k-token gate atom (FR11,
  FR12, FR13) are grouped so **one** memory pass closes them, because the two
  APPROVED-review LOWs waiting since v0.5.x are small and disjoint, and because the
  Arm-B rider (`specs-doctor-segment-router-silent-skip`) belongs with the other doctor
  and gate work.
- **`alpha-3` third** because FR18 perturbs the tree every later census would measure, and
  FR19/FR20 are unsatisfiable or noise before it.
- **`alpha-4` fourth** because FR22 is isolated by its own constraint (zero byte-changes to
  any non-Codex projection) and needs `alpha-1`'s frontmatter and `alpha-3`'s census rule.
- **`alpha-5` = WS-G (GC)** and **`alpha-6` = WS-F (consumer + CHANGELOG)**, per **R10**.
  The consumer round runs **last** and certifies the fully assembled surface, GC included.
  This removes the delta-re-check special case entirely: there is no window in which the
  release ships a surface the round did not see.

Three properties are non-negotiable throughout:

1. **RED before GREEN.** Every behavioural task writes its failing test first and observes
   it failing for the real reason (`DADAIA.md` §6).
2. **Green at every commit.** `dadaia ci preflight` + `backlog doctor` + `specs doctor` +
   `public doctor`. No `--no-verify`.
3. **Satisfiable diagnostics.** Every check this release adds (FR2, FR8, FR12, FR13, FR19,
   FR21 and the Arm-B rider) is **green at HEAD the moment it lands**. A check that cannot
   go green is a defect — and a check that goes silent instead of erroring is the same
   defect wearing the opposite mask, which is exactly what the rider fixes.

---

## 2. Layers affected

| Layer | Modules / paths | FRs |
|---|---|---|
| `public/skills` (ai-engineer only) | `dd-audit-project`, `dd-backlog-definition`, `dd-release-definition`, `dd-bug-registration`, `dd-bug-fix`, `dadaia-cli`, `dadaia-gitflow`, `dadaia-test-stewardship`, `dd-release-closure`, `project-orchestration`, `ai-harness-codex` | FR1–FR7, FR21, FR23, FR25 |
| `public/data`, `public/entities` | `DADAIA.md` (source only), `registry.json` | FR4, FR5, FR22 |
| `public/scripts` | `lint-memory-atoms.py`, `generate-memory-catalog.py` → thin wrappers | FR16 |
| `features/specs` | `doctor.py`, `doctor_memory.py`, `doctor_governance.py`, `doctor_release.py`, `doctor_structural.py` | FR8, FR12, FR16, Arm-B rider |
| `features/spec_context` | `gate_policy.py` | FR13 |
| `features/chokepoints` | `service.py`, `denylist_scan.py` | FR11, FR24 |
| `core` | `models/bugs.py`, `protocols/git_object_reader.py` | FR14, FR11 |
| `infrastructure` | `python_env.py`, `git_subprocess.py`, `git_objects.py`, `privacy_check.py`, `data/privacy_baseline.json`, `public_assets.py`, `codex_doctor.py`, `runtime_transforms/codex_assets.py` | FR9, FR10, FR11, FR12, FR17, FR22 |
| `hooks` | `venv_guard.py`, `pre_gate.py`, `sdd_post_gate.py` | FR26, FR27, FR28 |
| `cli` | `commands/bugs.py`, `commands/tmp.py` (new verb) | FR14, FR29 |
| `container.py` | `build_git_object_reader` seam | FR11 |
| `pyproject.toml` | ruff `C90` + `PLR1702` + mccabe ceiling; the pinned mutation tool | FR20, FR21 |
| `tests` | unit / contract / integration only — **zero new e2e** without a named qa exception | all |
| `CHANGELOG.md` | backfilled lineage + `[0.4.3]` at ship | FR31 |
| `specs/memory`, `specs/memory/.heading-allowlist` | closure window only | SPEC §5 |

**Layer rules hold unchanged:** `features/**` imports neither `cli`, `infrastructure` nor
`hooks`; `core/**` stays stdlib-pure with its existing authorized-I/O set; `cli` is the
sole composition point for injected ports. FR16 moves lint logic **into** the package as a
`features/specs` implementation imported by LINT-1 — a projected script may exec the
package entry point, never the reverse. `lint-imports` must stay green with **no new**
accepted edge in `setup.cfg`.

---

## 3. Execution order

```
W0  definition commit → milestone (a): merge → security review → push
      ↓
alpha-1  FR1 → FR2 → FR3 → FR4 → FR5 → FR6 → FR7 → FR8 → projection cycle → QA
      ↓                                   (FR1 first: D-2)
alpha-2  (FR9 ∥ FR10) → FR11 → FR12 → FR13 → FR14 → FR15 → FR16 → FR17
                                            → Arm-B rider (AB.1–AB.5) → QA + security
      ↓
alpha-3  census measure → FR18 curation → census re-measure → FR19 → FR20 → FR21 → QA
      ↓                                    (FR19/FR20 after FR18: D-3)
alpha-4  FR22 scoping+baseline → personas/law → doctor/certification → ENT-DERIVE+#37 → docs → QA
      ↓
alpha-5  FR23 → FR24 → FR25 → FR26 → FR27 → FR28 → FR29 → QA          (WS-G, R10)
      ↓
alpha-6  FR30 consumer round → remediation cycle → FR31 CHANGELOG → QA (WS-F, R10 — last)
      ↓
rc-1  code review (thawed tree) → memory window → CLOSURE + archive → ship
```

**The one sanctioned parallel pair:** FR9 (`infrastructure/python_env.py`) ∥ FR10
(`infrastructure/git_subprocess.py`) — disjoint write sets, disjoint tests, no shared
fixture. Everywhere else: **one `[-]` at a time**.

**Segment boundaries are commits, not ceremonies.** An `alpha-N` closes with a
`qa-engineer` review committed to the branch (ADR-3) — no CLOSURE.md, no archive, no ship.
Only `rc-1` runs the full trio, the memory window, CLOSURE and the archive move, in the
fixed order **review → closure → archive → ship** (D8/FR5).

---

## 4. Measurement plan (the OD-3 pattern — nothing asserted, everything measured)

`product-engineer` has no shell. Each row below is a numbered task step run by an agent
with a shell, its raw output captured under `.dadaia/tmp/<agent>/<YYYYMMDD>/` and cited as
CLOSURE evidence.

| id | Measurement | Command / method | Feeds |
|---|---|---|---|
| V1 | zero open bugs at pick | `dadaia bugs status` | SPEC §7 precedence claim |
| V2 | doctor baseline at branch cut | `dadaia specs doctor`, `dadaia backlog doctor` | the `rc-1` delta (A32.1) |
| V3 | the 12 `LINT-1` heading warnings, by name | `dadaia specs doctor` filtered to `LINT-1` | A13.3 |
| V4 | LARGE census, segment start | pytest collection over `tests/e2e/**` + Playwright spec count | A18.1 |
| V5 | LARGE census, segment end | same command, same selectors | A18.3 |
| V6 | complexity maxima | `ruff check --select C90,PLR1702` at a permissive ceiling | A21.1 |
| V7 | Codex TOML byte baseline | `wc -c .codex/agents/*.toml` before/after | A22.1 |
| V8 | non-Codex projection byte-diff | tree diff over `.claude/`, `.kimi-code/`, `.agents/` | A22.8 |
| V9 | projection health | `dadaia public doctor` (`public-privacy`, `entities-derivation`, `model-resolution`) | A32.2 |
| V10 | zombie/stale artifact counts before/after | reconciler reap output | A26.2 |
| V11 | mutation baseline | the pinned tool's own report | A20.4 |
| V12 | size accounting | `git diff --stat` split production / tests / docs | A21.5 |
| V13 | `SPEC-DOC-031` count **after** the archive move | `dadaia specs doctor` post-`git mv` | closure standing note |

**Zero-hit criteria** (A1.4, A3.2, A15.3, A22.6 …) are evaluated with the SPEC §3 standing
exclusions: `specs/_archive/**`, `specs/bugs/**`, `specs/backlog/**`,
`specs/releases/v0.4.3/**`, `CHANGELOG.md`, `.dadaia/{reports,handoff,tmp}/**`.

---

## 5. Segment exit criteria

| Segment | Exits when |
|---|---|
| `alpha-1` | FR1–FR8 `[x]`; one projection cycle run; V9 all `[ok]`; `qa-engineer` review committed |
| `alpha-2` | FR9–FR17 `[x]` **and** the Arm-B rider `[x]` with its bug closed; `security-reviewer` covered the gate delta; RED-then-GREEN evidence for FR11/FR12/AB; `qa-engineer` review committed |
| `alpha-3` | FR18–FR21 `[x]`; V4/V5/V6 captured; demotion map drafted; every deletion carries a qa verdict; `qa-engineer` review committed |
| `alpha-4` | FR22 `[x]`; V7/V8 captured; `entities-derivation` `[ok]`; live certification evidence; `qa-engineer` review committed |
| `alpha-5` | FR23–FR29 `[x]`; V10 captured; every GC capability fail-open-proven; `qa-engineer` review committed |
| `alpha-6` | FR30 round complete with limits **and** the exercised GC capabilities recorded (A30.6); remediation cycle spent or unused; FR31 `[x]`; `qa-engineer` review committed |
| `rc-1` | `code-reviewer` APPROVE on a **thawed** tree → memory window → CLOSURE (with `## Size accounting`, the disposition sweep and an empty `## ACTIVE`) → archive → ship |

A segment that cannot exit **stops the release and returns to the operator**. It is never
closed partially, and its unfinished FRs never become backlog demand — that is the whole
point of the residual budget.

---

## 6. Validation plan

**Per task:** RED-then-GREEN evidence, the task's acceptance ids, `dadaia ci preflight`
green, the commit sha.

**Per segment:** the exit criteria above, plus the segment's `qa-engineer` artifact naming
every acceptance id it verified and every id it could not (an unverified id is never
reported as passed).

**Per release (`rc-1`):**

1. `dadaia ci preflight` — `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`.
2. `dadaia doctor`, `dadaia specs doctor` (**0 errors**, and 0 `LINT-1` heading warnings),
   `dadaia backlog doctor`, `dadaia public doctor`.
3. `lint-imports --config setup.cfg --no-cache` — no new accepted edge.
4. The consumer round's artifact (FR30), which by construction covers the whole shipped
   surface including `alpha-5`'s GC work.
5. `## ACTIVE` empty; 24 new `LEDGER` lines + the rejection line written at definition = 25.
6. Six-axis `code-reviewer` review on the thawed tree; APPROVED `security-reviewer` verdict
   covering the pushed delta at each milestone.

---

## 7. Risks

Stated once, in SPEC §6 (D-1…D-9, R1–R10). The three that shape this plan:

- **R1 release size** — mitigated structurally by segmentation and by the rule that a
  segment either exits on its criteria or stops the release.
- **R2/R3 the tail order (R10)** — WS-G is L-sized and now lands second-to-last, with the
  consumer round after it: a GC regression is caught inside the release, at the cost of
  less runway after the round. Mitigated by capability-level task granularity (each of
  FR23–FR29 is independently revertible) and by the remediation cycle budgeted in `alpha-6`.
- **R4 FR18 destabilizes the suite** — mitigated by the census-freeze rule, verdict-only
  stewardship, and measuring at both ends of the segment.

---

## 8. Dispatcher and relay obligations

- **Shell-less reservation obligation (FR5 of v0.4.2, now canon).** When the dispatcher
  relays work for a shell-less sub-agent, it commits that sub-agent's `[ ]`→`[-]` flip
  **before** relaying the next work item — never batched at the end.
- **Lane discipline.** `ai-engineer` performs **every** skill/persona/rule/projected-asset
  edit; `software-engineer` performs every production-code and test edit; `qa-engineer`
  issues every test-deletion verdict; `project-manager` performs any backlog-file mechanics
  after the definition commit; `product-engineer` writes only specs and memory.
- **Escalate at discovery.** An actionable defect found mid-segment is fixed in that
  segment or escalated to the operator immediately. Accumulating it for the closure
  violates the residual budget.
- **Register every bug** hit while operating the tooling, before the turn ends
  (`dd-bug-registration`) — and close it in the session that proves the fix, exactly as
  the `alpha-2` Arm-B rider does.
