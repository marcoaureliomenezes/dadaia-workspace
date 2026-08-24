# QA Close — Segment S2 (rules→skills governance map)

**Release:** v0.4.4 · **Segment:** S2 · **Task:** T-044-16 (QA verdict)
**Author:** qa-engineer · **Date:** 2026-08-23
**Scope:** FR7–FR9 (T-044-13/14/15), plus the Arm-B citation-drift bug
(`t044-04-renumber-stale-DADAIAmd-section-citations`) closed in-segment.

**Verdict: APPROVE.**

Every acceptance id A7.1–A9.5 was independently re-run on this branch (not read off an
implementer handoff) and holds. The full suite is green, `lint-skill-collisions.py` is
gone from source and every projection, and the retired script's coverage moved into one
contract test rather than being dropped. A fresh full-corpus re-scan of the citation fix
found one additional bare `DADAIA.md §N` mismatch — pre-existing, not caused by S1/S2,
newly registered as a residual (see §3).

---

## 1. Per-FR verdict table

### FR7 — One JSON map, owned by dadaia-workspace (T-044-13)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A7.1 | PASS | `python -c "import json,jsonschema; jsonschema.validate(json.load(open('dadaia_workspace/public/entities/rules-skills-map.json')), json.load(open('dadaia_workspace/public/schemas/rules-skills-map-v1.schema.json')))"` | Validates clean; schema is `$id: rules-skills-map-v1`, versioned. |
| A7.2 | PASS | Set-diff of `rows[*].skills[]` vs `dadaia_workspace/public/skills/*/SKILL.md` (independent Python script, not the shipped test) | 25 unique skill mentions, 25 skills on disk, **zero** in either direction's set-difference — full bijection. Only one row (`AI surface`) names more than one skill (4), and it carries a non-empty `justification`. |
| A7.3 | PASS | Read `rows[0]` | `{"topic": "Gitflow", "section": "§4 Gitflow — the branch contract", "skills": ["dd-gitflow-default"]}` — first row, correct skill, correct section. |
| A7.4 | PASS | `grep -rn "rules-skills-map\|rules→skills\|rules-to-skills" dadaia_workspace/public/` minus the map/schema files themselves | Three residual hits, none a second section↔skill declaration: `DADAIA.md` §10's pointer row (no restatement), `dd-backlog-definition/SKILL.md`'s `declared_overlaps` rationale table (explicitly states "the JSON is the one authoritative source"), and `scaffold/constitution.md` §15 (FR8's own rule statement, generic, names no specific topic→skill pair). |

### FR8 — The map is core law (T-044-14, two commits)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A8.1 | PASS | `grep -n "^## 16" specs/constitution.md`; `grep -n "^## 15" dadaia_workspace/public/scaffold/constitution.md`; `head -4 specs/constitution.md` | `specs/constitution.md` §16 "Rules Map to Skills" (commit `b4ad29a7`, `constitution_version: 4.0.0 -> 4.1.0`); scaffold §15 "O Mapa Regras→Skills é Lei Central" (commit `288c9ba9`). Operator confirmation is SPEC §8's approval per D-8's own text ("approval of this SPEC is the confirmation, recorded in §8") — verified by reading SPEC.md line 1049/1123-1134. |
| A8.2 | PASS | `sed -n '318,324p' dadaia_workspace/public/data/DADAIA.md` | §10 "Where to look next" Skills row: "which skill operates which rule is declared once, in `public/entities/rules-skills-map.json`, never listed ad hoc here" — points at the map, lists no skill ad hoc. |
| A8.3 | PASS | `grep -rln "Rules Map to Skills\|Mapa Regras.*Skills\|declared in exactly one controlled source\|is mapped to exactly the skill" --include="*.md" .` | Exactly two hits: `specs/constitution.md`, `dadaia_workspace/public/scaffold/constitution.md` — the two sanctioned homes, no third. |

### FR9 — One deterministic enforcer, gating every deploy (T-044-15)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A9.1 | PASS | `pytest -p no:cacheprovider -q tests/contract/test_rules_skills_map.py` | **15/15 passed** at HEAD: 1 schema test + 6 "green at HEAD" failure-mode tests + 6 mutation fixtures + 2 ported self-tests. |
| A9.2 | PASS | Read `test_mutation_fixture_{1..6}_*` bodies | Each mutates an in-memory `copy.deepcopy` of the real map or a `tmp_path` skill tree (never a repo file) and asserts the same check function used by the green-at-HEAD test turns non-empty/red for that one failure mode. All 6 present, one per mode (missing section, unmapped skill, missing skill, undeclared shared topic, ceiling violation, undeclared activation overlap). |
| A9.3 | PASS | `find . -iname "lint-skill-collisions*"` (repo-wide); `ls dadaia_workspace/public/scripts/`; `ls &lt;workspace-root&gt;/.dadaia/scripts/` | Zero hits for the script file anywhere in the tree. `public/scripts/` now holds only `lint-dadaia-cli-reachability.py` and `lint-memory-atoms.py`; the workspace-root projection (`.dadaia/scripts/`) mirrors the same two, no orphaned third file. Manifest/registry greps for the retired name are also empty. Remaining textual mentions are exclusively historical ("retired"/"replaces") in `SPEC.md`, `PLAN.md`, `TASKS.md`, `reviews/`, and the new test's own docstring/comments — none is a live invocation. |
| A9.4 | PASS | Read `test_ported_self_test_a_*` / `test_ported_self_test_b_*`; both re-run green in the A9.1 run above | Self-test (a) — a `**` universal-glob skill never fires even on an obvious path collision; self-test (b) — an undeclared duplicate glob pair does fire. Both ported verbatim onto the pure `_find_overlap_pairs`, matching the retired script's own `--self-test` shape. Coverage moved, not dropped. |
| A9.5 | PASS | `git show --stat e6421966 2023e8af` (independently re-run, not taken from the commit message) | FR7 (`e6421966`): `rules-skills-map.json` +125, `rules-skills-map-v1.schema.json` +67 = 192. FR9 (`2023e8af`): map.json +8, schema +15 = 23. Combined production = 215. Retired `lint-skill-collisions.py`: 232 lines (confirmed by the same `git show --stat`'s `-232` line-count on its deletion). **Net = 215 − 232 = −17 ≤ 0.** Test LOC (`tests/contract/test_rules_skills_map.py`, 410 lines) is correctly excluded from this count — it is test, not production, surface. |

### Gating confirmation (FR9's "gating every deploy" clause, independently checked)

- `pytestmark = pytest.mark.contract` in the test file, and `-m "contract"` collection returns all 15 tests (`pytest tests/contract/test_rules_skills_map.py -m contract --collect-only -q`).
- CI: `.github/workflows/ci.yml` line 177/230 runs `-m "(unit or contract) and not quarantine" ... tests/unit tests/contract` on both matrix legs.
- Local preflight: `dadaia_workspace/features/ci_preflight/service.py:260` builds `-m "not quarantine"` over the full suite (contract included) — same selector class, not a narrower one that could silently exclude this file.

### Bug `t044-04-renumber-stale-DADAIAmd-section-citations` (closed in S1, cited by this segment's dispatch)

| Check | Verdict | Evidence |
|---|---|---|
| `resolved` event present, 3-field evidence (RED/SURFACE/GREEN) | PASS | `specs/bugs/bugs.jsonl` line 956: RED = 30-file/80-citation census before fix; SURFACE = 44 stale citations fixed across 9 agent files + 13 skill files + scaffold constitution.md, title-anchored; GREEN = `dadaia public stage && install --target all` clean, `pytest -k 'public or agent or skill' -n auto` 452 passed. |
| Not in open-bug list | PASS | `dadaia bugs status` — absent from the 13 currently-open bugs. |
| Independent re-scan for residual drift | **1 new finding (LOW, filed this session, not blocking)** | See §3. |

---

## 2. Full-suite and e2e re-run (independent, this session)

```
pytest -p no:cacheprovider -q -m "not quarantine" -n auto --ignore=tests/e2e
  -> 2604 passed, 3 skipped (all environment-gated: 2 Windows-only, 1 codex-live-probe
     honest-degrade), 0 failed, 33.41s

pytest -p no:cacheprovider -q tests/e2e/features/test_public_pipeline.py
  -> 11 passed, 3.68s
```

`tests/integration` is included in the first run (only `tests/e2e` is excluded by
`--ignore`) — 2604 vs S1's 2589 passed is exactly +15, matching T-044-15's 15 new
`test_rules_skills_map.py` cases with zero regressions elsewhere.

### Test-stewardship spot check on `tests/contract/test_rules_skills_map.py`

- **Intent declared** in the module docstring: `Intent: CONTRACT — A9.1, A9.2, A9.4
  (SPEC v0.4.4). Size: SMALL` — present, correctly kinded (CONTRACT, permanent), correct
  size class.
- **Tier matches placement**: file lives in `tests/contract/`, collection confirms
  `pytest.mark.contract` auto-applied and all 15 tests appear under `-m contract`.
- **No scaffold, no tautology, no change-detector pattern**: every "green at HEAD" test
  reads the real `public/entities/rules-skills-map.json`, real `public/data/DADAIA.md`
  (title-anchored, not a hardcoded copy), and the real on-disk skills inventory — no
  mocks of the code under test; the mutation fixtures each mutate an in-memory copy or a
  `tmp_path` fixture, never a repo file, and independently target the same production
  function the green test uses, proving real detection (A9.2) rather than an
  always-green assertion.
- **Not volume padding**: one file for FR9's six named failure modes plus the schema
  contract plus the two mandated ported self-tests (A9.4) is proportionate — 15 tests,
  no near-duplicates, one behavior per test.
- **D4 upheld**: this is the ONE enforcer FR9 mandates; no second lint script or CI step
  independently re-implements any of the six checks (confirmed by the A9.3 grep above).

---

## 3. Bug-surface statement (operator standing order)

Net direction across S2, measured, not asserted:

- **Deleted:** the second enforcer — `lint-skill-collisions.py` (232 production lines)
  and its hardcoded `DECLARED_OVERLAPS` Python list — replaced by the map's
  `declared_overlaps` JSON field (D4, "one enforcer, not two").
- **Added:** exactly one new production surface — `rules-skills-map.json` +
  `rules-skills-map-v1.schema.json` (215 combined lines across the two FR7/FR9 commits)
  — and exactly **one** new contract test file (`test_rules_skills_map.py`, 410 test
  lines, not counted against the production ceiling). No new script, no new CI job, no
  new hook: the enforcer runs inside the pre-existing `contract` pytest tier, already
  gated by both the local preflight and CI.
- **Production LOC (FR7+FR9 combined, A9.5):** net **−17** against the retired script,
  independently summed from `git show --stat` on both commits, matching the commits'
  own claims exactly (125+67+8+15 = 215; 215−232 = −17).
- **Documentation touch:** `dd-backlog-definition/SKILL.md` §7's collision-rationale
  table was rewritten (10 lines) to point at the JSON as the one authoritative source
  instead of restating it — consistent with A7.4's finding of zero third declarations.
- **Golden fixtures:** two byte-goldens regenerated
  (`doctor_all_four_v0158.json`, `install_target_resolution_v0158.json`) — diff scoped
  to exactly the now-absent script's projection lines and the two new map/schema files'
  `[ok]` stage lines; no unrelated drift introduced (confirmed by the 452-test
  `-k 'public or agent or skill'` run cited in the S1-closed bug's own resolution
  evidence, re-verified green again in this session's full-suite run).

**S2's own new bug-surface contribution, honestly stated:**

1. **`dadaia-task-manager-stale-workspace-protocol-citation`** (LOW, filed this
   session). During the independent re-scan of every bare `DADAIA.md §N` citation under
   `public/` (the specific check this segment's dispatch asked for — "any remaining §N
   citation must be either correct or title-anchored"), one mismatch surfaced:
   `dadaia-task-manager/SKILL.md` line 32 cites `DADAIA.md (the workspace law) §1` for a
   description of the SDD-gate's path-class × presence × phase × mode mechanism — that
   content lives at the current §3 ("What is enforced deterministically"), not §1 ("The
   flow"). **Confirmed pre-existing, not caused by S1's or S2's renumbering**: `git show
   90dfc5f2^:.../dadaia-task-manager/SKILL.md` (the commit immediately before T-044-04
   inserted the new Gitflow section) already reads "(the workspace law) §1" at that same
   line, and DADAIA.md's own §1 title was "The flow — the mandatory default" both before
   and after T-044-04 — the renumbering never touched §1's identity, so this citation was
   already wrong prior to this release. It does not fail any A7–A9 acceptance id (none
   scope this file), and it is not a regression S2 introduced. Filed as a residual for
   the next citation-accuracy pass, sharing the same remediation lane as
   `t044-04-renumber-stale-DADAIAmd-section-citations` (S1's own open residual — still
   open, unaddressed by S2, since S2's declared scope was FR7–FR9 only). Every other
   `DADAIA.md §N` citation found in the same re-scan (~55 bare or title-anchored hits
   across 30+ files) was individually read against the live section titles and confirmed
   correct — this is the sole mismatch found.

Net: S2 collapses a duplicate enforcement mechanism into one JSON-declared source with a
single deterministic test, at a net-negative production LOC, with coverage moved rather
than dropped and zero new code paths, scripts, or CI jobs. The one new bug this segment's
own re-scan surfaced is LOW, pre-existing (not introduced by S1 or S2), and does not touch
any FR7–FR9 surface.

---

## 4. Open residuals

1. **`t044-04-renumber-stale-DADAIAmd-section-citations`** (MEDIUM, still open, carried
   from S1). Unaddressed by S2 — its declared scope was narrowly FR7–FR9, not a citation
   sweep. Still recommended before S3 (`core-skills-consolidation`) does its own
   persona/skill pass, per S1's own residual note.
2. **`dadaia-task-manager-stale-workspace-protocol-citation`** (LOW, new, filed this
   session). One-line fix (`§1` → `§3`) in `dadaia-task-manager/SKILL.md`; batch it with
   residual 1's remediation pass rather than as a standalone Arm-B fix, since both are
   the same citation-accuracy class.
3. **The verdict-gate advisory window** (carried from S1, unchanged) — still nothing to
   do at segment close; flagged again only so `rc-1`'s ship step does not mistake
   "advisory" for "broken".
4. **The installed venv is editable and runs this branch's code** (carried from S1,
   reconfirmed this session) — every command above validates `feature/0.4.4` HEAD, not a
   released package.

---

## 5. Verdict

**APPROVE.** All of A7.1–A9.5 independently re-verified true on this branch, by the
executed path. Full suite green (2604 passed, 0 failed, +15 over S1 with zero
regressions) plus the public-pipeline e2e journey (11 passed). `lint-skill-collisions.py`
is confirmed gone from source and both projections, its coverage ported (not dropped),
net production LOC −17. The map is schema-valid, bijective with the 25 on-disk skills,
and is the map's own sole section↔skill declaration under `public/`; both constitutions
carry FR8's law section with no third statement. One new LOW citation bug was found by
this session's own independent re-scan and registered; it predates S1/S2, is unrelated to
FR7–FR9, and does not block this verdict.

S2 is closed on `feature/0.4.4`. No merge, no PR, no `rc` burned (D8) — `S3` may proceed
once T-044-16 flips `[-]` → `[x]` (product-engineer/software-engineer, per this
segment's own precedent — QA does not flip task markers).
