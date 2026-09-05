# SPEC — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer
**Opened:** 2026-08-31
**Consumes:** release-candidates-system

---

## 1. Problem and context

Since PyPI `0.4.4`, four internal version ids (0.5.0–0.5.3) and multiple feature
branches accumulated without a publication — version/branch slop, mint-at-ship
misalignment, and a governance gap the operator ordered closed (grill
`20260831T181256Z`, ADRs 0005–0009). The release model must make that slop
structurally impossible: one live version, one live branch, versions minted at
birth from the PyPI lineage, scope growing by stacked candidates instead of new
versions.

## 2. Objective

Implement the release-candidates system: an open-scope release (named
last-published-PyPI + 1 patch) whose scope grows by closed-scope candidates,
each archived to `rc-N/` on the operator's "continue" ruling — version increment
and next branch happen only at operator-approved deploy.

## 3. Scope (candidate 1)

- FR1 — `core/release_state.py` owns the state filename: `_RELEASE.json`
  (canonical) with the legacy `RELEASE.json` recognised for a doctor-fixable
  rename. One decider; every reader (doctor, specs_tree, CLI, reports) imports it.
- FR2 — canon: `releases/<v>/_RELEASE.json` replaces the RELEASE.json entry;
  `releases/<v>/rc-N/{SPEC,PLAN,TASKS}.md` admitted as candidate archives; the
  legacy filename stays admitted only as the rename-lane input; the scaffolded
  segment lane (`alpha-N`, `**Segment:**` docs) is retired (ADR 0006).
- FR3 — doctor: fixable legacy→canonical rename rule; exactly-one-live-release
  rule; segment-era rules retired; per-candidate phase cycle honoured
  (DEFINITION→IMPLEMENTATION→CLOSURE per candidate; DISCOVERY between candidates;
  ARCHIVED at deploy).
- FR4 — CLI: `dadaia release rc-archive` (ADR 0008) — validates candidate closure
  (trio present, all tasks `[x]`, phase CLOSURE), moves the root trio to the next
  `rc-N/`, bumps the archived-candidate counter, logs, sets phase DISCOVERY.
  `dadaia release new` creates the new shape and refuses a second live release.
- FR5 — version minted at release birth: pyproject `0.4.6`, CHANGELOG top section
  `[0.4.6]` accumulating per candidate — the mint-at-ship step is deleted.
- FR6 — migration (ADR 0007): `RELEASE.json` → `_RELEASE.json` in every archived
  release under `specs/releases/_archive/`, and in this release itself.
- FR7 — law and skills: DADAIA.md §4.2/§6.7 + glossary rewritten (candidate,
  rc-N archive, promote-or-continue gate; segment removed); `dd-gitflow-default`
  and `dd-release-definition` updated; behavior-map hashes re-recorded;
  CONTEXT.md glossary sharpened (Release, Candidate, rc-N; Segment retired).
- FR8 — memory: release-lifecycle truth updated at candidate closure.

## 4. Out of scope

- Any automation that blocks a human (the promote-or-continue question is agent
  protocol — DADAIA §3.5).
- Renaming archived release *directories* (ids 0.5.0–0.5.3 stay as history).
- CI/CD changes beyond what the law rewrite documents.

## 5. Dependencies and risks

- Consumer instances carry legacy `RELEASE.json` — covered by the doctor-fixable
  rename (FR1/FR3); reader accepts both until fixed.
- Canon/doctor/scaffolder segment retirement deletes tests with it — deletions
  staged (ratchet reads `git ls-files`).
- The release is self-hosting: born in the old shape, flips to its own new shape
  at FR6 inside candidate 1.
