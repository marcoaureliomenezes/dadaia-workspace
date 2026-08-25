# PLAN — Release v0.4.5 — hardening and consolidation

**Status:** Aprovado
**Release ID:** v0.4.5
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.5/SPEC.md`
**Branch:** `feature/0.4.5` (cut from `main` at the shipped v0.4.4 — branch model:
`DADAIA.md` §4, operations: `dd-gitflow-default`)
**Segments:** `S1 … S4` — internal work boundaries, each closed by a `qa-engineer` review
**committed on the branch**, no merge, no PR (SPEC D8).
**Candidates:** `rc-1 … rc-N`. `rc-1` burns when the **whole** scope is implemented,
gate-green and closed by QA, and is merged into `develop`; `rc-2 … rc-N` are adjustment
rounds on that same scope; the final `rc` carries memory → CLOSURE → archive and ships
**without publishing** (O5). If nothing is found, the final `rc` **is** `rc-1`.

---

## 1. Strategy

One ordering principle: **fix the gate, then build the net, then delete into it.**

Every segment of this release removes something. That is its value and its danger: a
release whose diff is dominated by deletion has no natural safety net, and v0.4.4's R-2
(guarding its single additive segment) inverts here into R-2 (guarding four demolitions).
So the order is not preference — each boundary is a constraint:

- **`S1` first** — FR1 changes the classifier that gates every write the rest of the
  release performs, and the four remaining sweep items want a tree nobody else is
  rewriting. It is also the smallest surface: the release starts by *closing* the ledger.
- **`S2` second** — the consolidations. Each one builds its replacement, switches every
  consumer, and only then deletes (**expand → switch → contract**, D7). FR4's shared oracle
  lands here because every later `public/**` change in `S3`/`S4` is cheaper once the three
  inventories are one.
- **`S3` third** — the gate/doctor/seam lane. Small, independent fixes on a stable tree.
- **`S4` last** — the token-economy program: measure once, cut the dominant contributor,
  re-measure. It touches the largest number of authored files and the fewest executable
  paths, so it wants everything else already green.

**Then, and only then, the `rc` lane.** A segment never reaches `develop` on its own: the
four close on the branch and the release integrates **once**, whole, as `rc-1`.

Five properties are non-negotiable throughout:

1. **RED before GREEN**, on the executed path.
2. **Green at every commit** — `dadaia ci preflight`, `backlog doctor`, `specs doctor`,
   `public doctor`; no `--no-verify`.
3. **The standing order is an acceptance.** No puxadinho: no new branch, flag, second code
   path or cross-feature reach-in. Every review verdict states the bug-surface delta of the
   feature it touched, with bug-history evidence.
4. **Deletion needs its net first.** No writer, inventory, golden assertion or persona block
   is deleted before the thing that proves its behaviour survives exists and is green.
5. **No number is estimated.** Every figure this release asserts is captured by a shell task.

---

## 2. Layers affected

| Layer | Modules / paths | FRs |
|---|---|---|
| `features/spec_context` | `gate_policy.py` (`_is_law_path`, `classify_path`); `doctor.py` (references sanction, slug-ownership lane) | FR1, FR9, FR10 |
| `core` | **new** `atomic_write.py` (single primitive, added to the core file-I/O authorized set); `models/bugs.py` (`redact_text`) | FR2, FR6 |
| `hooks` | `_common.py` — its named writer retires in favour of the core primitive (import-light, no container) | FR2 |
| `infrastructure` | `public_assets_common.py`, `json_agent_model_policy_store.py` — named writers retire; `privacy_check.py` (`load_privacy_terms`) becomes the single denylist loading seam; `jsonl_bug_store.py` (serialise/iterate) | FR2, FR6, FR7 |
| `features/migrate` | `frontmatter_keys.py`, `state_v2.py` (inline `.tmp` writer) | FR2 |
| `features/specs` | `doctor_structural.py` (named writer); `specs init --specs-dir` symlink refusal | FR2, FR8 |
| `features/import_` | `service.py` — two inline `.tmp` writers | FR2 |
| `features/certification` | `service.py` — skip/fail detail redaction (`S1` bug) | `S1` |
| `cli` | `commands/bugs.py` — `bugs status` rendering after sanitation | FR7 |
| `public/scaffold` | the repo `AGENTS.md` template header, aligned with the gate contract | FR1 |
| `public/data` | `DADAIA.md` (source only — the projected law is PROTECTED) | FR11 |
| `public/agents` | the nine personas: four trimmed under the ceiling pass, `ai-engineer.md` citation | FR13, FR14 |
| `public/skills` | `dadaia-task-manager` (citation bug), `dadaia-test-stewardship` (Intent vocabulary) | `S1`, FR15 |
| `specs/memory/product` | `catalog.json` curation policy + `index.md` | FR12 |
| `tests` | unit / contract / integration only — **zero new e2e** without a named qa exception; the injected-failure battery, the derived roster, the shared inventory oracle, the scan-population convention | FR2–FR5 |
| `.dadaia/` | `references/` recognized as a sanctioned operator-owned subtree | FR10 |
| `pyproject.toml`, `CHANGELOG.md` | `0.4.4 → 0.4.5` + `[0.4.5]` stating once that it is minted unpublished | final `rc` |
| `specs/memory/**` | closure window only | SPEC §5 |

**Layer rules hold unchanged:** `features/**` imports neither `cli`, `infrastructure` nor
`hooks`; `core/**` stays stdlib-pure; `lint-imports` green with **no new** accepted edge.
D5's placement of the atomic-write primitive in `core/` is what keeps that true — it is the
single home `features/`, `infrastructure/` and `hooks/` may all import without a forbidden
sibling edge, on the existing `core/specs_repair` precedent.

---

## 3. Execution order

```
W0   definition commit (SPEC+PLAN+TASKS+ACTIVE.md+BACKLOG.md purge+superseded event)
       → push feature/0.4.5 → definition PR → develop  [milestone (a), burns no rc]
       → [operator] wire the verdict-gate required check on BOTH PR edges (due < rc-2)

S1   FR1 gate LAW-class by origin (2 MEDIUM bugs, one cause)  → venv reinstall + refusal probe
       → task-manager citation → certify detail redaction → codex fixture uuid
       → windows-xdist bounded attempt (AS-5)
       → QA close S1 (committed on branch)

S2   AR-1 ruling (atomic-write home) → FR2 expand/switch/contract → FR3 roster split
       → FR4 shared inventory oracle → FR5 scan-population convention
       → QA close S2

S3   FR6 denylist at the write seam → FR7 control/format sanitation (+ the MEDIUM bug)
       → FR8 specs init symlink refusal → FR9 slug-ownership decision
       → FR10 .dadaia/references sanction
       → QA close S3

S4   FR11 baseline measure + diet pass → FR12 catalog digest curation
       → FR13 persona ceiling trim → FR14 hygiene residuals → FR15 Intent vocabulary
       → QA close S4

scope complete   FR16 invariants measured → six-axis code review (thawed tree)
                 → security review + QA release verdict
rc-1             PR feature/0.4.5 → develop, CI green, merge
rc-2 … rc-N      adjustment rounds on this scope only
final rc         memory → CLOSURE → archive → version bump + merge to develop
                 → ship develop → main, WITHOUT publish (O5)
                 → delete feature/0.4.5 + cut feature/0.4.6 from main, same step
```

---

## 4. Approach per segment

### `S1` — the sweep

FR1 is a **one-predicate** change and must be provable as such. The approach: write the two
RED probes first (fresh-repo `Write`, existing non-tracked `Edit`), then the manifest-
enumerating contract test that pins what must **stay** LAW, then change the predicate so
origin — not basename — decides. The scaffold template is corrected in the same commit, so
the two surfaces never state opposite contracts even transiently. The venv reinstall (D-3)
plus a live refusal probe closes the segment: gate code that is not installed is not live.

The four remaining items are ordinary Arm B under `dd-bug-fix` with the FR23 evidence gate.
`windows-xdist` is time-boxed: reproduce on the CI matrix, look at worker count vs runner
memory and at the specific interleaving, and stop at the box. AS-5 then applies — a
quarantine is a `qa-engineer` verdict with evidence, executed by `software-engineer`, and
the bug stays open.

### `S2` — the consolidations

**FR2 is the release's largest structural change and its clearest deletion.** Sequence:

1. `software-architect` rules on the home (**AR-1**) — recorded before any consumer moves.
2. **Expand:** author `core/atomic_write.py` with the full parameter surface; re-point the
   injected-`os.replace`-failure battery at it and prove every parameter combination cleans
   up its temp file. The net exists before anything is cut.
3. **Switch:** move the eleven call sites over, one coherent commit per module family, suite
   green at each.
4. **Contract:** delete the eight named writers and the three inline `.tmp` writers, delete
   the leak characterization test in the same commit that makes leaking impossible, and land
   the derived call-site census that makes regression impossible.

FR3 and FR4 are pure test architecture with zero production change; both are the same
move — replace a hand-kept list with a derived one — and both prove themselves by an
executed fixture (add an asset / rename a skill and watch exactly one assertion fail).
FR5 is a two-line convention applied test-by-test, with three sampled mis-rooted-walker
proofs; no harness, per the standing ruling.

### `S3` — gate, doctor and seam

FR6 and FR7 both touch the bug ledger and are sequenced FR6 → FR7 so the redaction seam is
settled before the sanitation pass wraps it. FR7's riskiest property is backward
compatibility: the whole live `bugs.jsonl` must still parse, and no historical event is
rewritten. FR8 reuses the existing refusal posture verbatim — the fix is a check, not a new
vocabulary. FR9 is a decision task whose deliverable may be one recorded paragraph. FR10 is
one allowlist line plus the outside-context-lifecycle test, which is the part that matters:
lifecycle verbs acting on foreign trees destroyed work before.

### `S4` — the token-economy program

Measure the baseline **once** (V6/V7/V8) before any cut, then cut in contribution order:
FR12 first (the catalog digest is the dominant single contributor to the bound-session
overage), FR11's law/rule/persona pass second, FR13's persona relocation third, re-measuring
after each. FR11 and FR13 each carry a **coverage table** — removed block → surviving home —
and the six-axis review reads that table, not the diff alone. FR14 and FR15 are hygiene and
vocabulary, landing last so the citation check runs against the final text.

---

## 5. Measurement plan

Every figure is captured by an agent with a shell into
`.dadaia/tmp/<agent>/<YYYYMMDD>/` and cited by id in `CLOSURE.md`.

| id | What | When |
|---|---|---|
| V1 | `dadaia bugs status` — the 8 open bugs, one already `superseded` | W0 |
| V2 | `dadaia specs doctor` + `dadaia backlog doctor` clean | W0 and at each segment close |
| V3 | Gate refusal probe on the installed venv (fresh repo `AGENTS.md` allowed; a manifest-tracked projection still refused) | `S1` close |
| V4 | Atomic-writer call-site census (before: 8 named + 3 inline; after: 1) | `S2` |
| V5 | Test-LOC delta for FR3+FR4+FR5 | `S2` close |
| V6 | Always-on token count (the law as each harness loads it, the 9 persona bodies, every always-loaded skill description) | `S4` open **and** close |
| V7 | Negation count across the always-on set | `S4` open and close |
| V8 | Bound-session injection prefix, measured on a real session | `S4` open and close |
| V9 | Per-persona line counts, all nine | `S4` open and close |
| V10 | Production LOC net for the release | scope complete |
| V11 | AI-surface LOC net over `public/{agents,skills,data,entities}/**` | scope complete |
| V12 | `release.yml` `approve` job state, `git tag --list 'v0.4.5'`, PyPI latest version | after ship (A16.8) |

---

## 6. Validation plan

| Boundary | Who | What must be true |
|---|---|---|
| Per task | implementer | RED observed for the real reason; suite green; local CI preflight green; `implementation-complete` handoff; marker stays `[-]` |
| End of `S1 … S4` | `qa-engineer` only | every acceptance id of that segment evidenced; a qa-gated review **committed on the branch**; no push, no PR, no CLOSURE |
| `S2` head | `software-architect` | **AR-1** ruling on the atomic-write home, recorded verbatim |
| Scope complete | `qa-engineer` + `code-reviewer` + `security-reviewer` | all three `APPROVE` the **same** commit, on a thawed tree; each verdict states the bug-surface delta with bug-history evidence |
| `rc-1` | CI + `security-reviewer` | APPROVED verdict covering the PR head sha; CI green; merged |
| `rc-N ≥ 2` | `qa-engineer` + delta reviews | the finding is named, on this scope; one QA close and one merge per round |
| Final `rc` | `product-engineer` + trio | memory → CLOSURE → disposition sweep → artifact GC → archive, one commit, in that order, before the ship PR |
| After ship | dispatcher | V12: no publication, no `v0.4.5` tag, PyPI still `0.4.4` |

**Test stewardship.** Intent and size declared at birth. FR2–FR5 are net test deletions by
construction; every deletion is a `qa-engineer` verdict with evidence, executed by
`software-engineer` — the implementer never prunes to go green. Any quarantine carries its
registered bug id (AS-5).

---

## 7. Technical risks

Full register: SPEC §6. The three that shape this plan's order:

- **R-1 — FR1 touches the security boundary itself.** Mitigated by RED-first on both
  executed paths **plus** a manifest-enumerating contract test for what must stay LAW, and
  by installing the fix (D-3) before trusting it.
- **R-2 — the additive risk is inverse.** Four demolitions and no natural net. Mitigated by
  building each net first (battery, derived census, derived roster/oracle, coverage tables)
  and by `expand → switch → contract` making every step independently green.
- **R-6 — a second minted-unpublished version.** Mitigated by recording it as product truth
  in `pypi-distribution.md` at closure, stating it once in `CHANGELOG.md`, and verifying it
  with V12.

---

## 8. Definition of done

- Every acceptance id in SPEC §3 evidenced, or explicitly dispositioned by an operator
  ruling recorded in `CLOSURE.md`.
- Seven bugs `Closed` (six fixed, one bundled into FR7) + one `Closed` with `superseded_by`;
  the eighth either `Closed` or recorded still-open per AS-5 — no bug silently dropped.
- Fourteen `LEDGER` lines updated `CONSUMED · v0.4.5` → their terminal token, in place.
- FR16's invariants all hold, including **A16.8: nothing was published**.
- Memory updated, `CLOSURE.md` written, the release archived, `ACTIVE.md` repointed.
- `feature/0.4.5` deleted and `feature/0.4.6` cut from `main` in the same step.
