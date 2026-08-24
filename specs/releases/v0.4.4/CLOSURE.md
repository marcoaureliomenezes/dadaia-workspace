# Closure: Release — v0.4.4 "organize the core"

> **Status:** Aprovado
> **Release ID:** v0.4.4
> **Owner:** product-engineer
> **Closed:** 2026-08-24

## Summary

v0.4.4 organized the core entities of the workspace. Four things the operator could
previously only hold in their head are now stated once and enforced once: the git
contract lives in one law section and one skill, with the mechanical chokepoints inverted
to agree with it byte for byte; every skill maps to exactly one law topic through one
JSON map with one deterministic enforcer; the skill surface fell from 25 to 21 folders,
each a short `SKILL.md` whose depth is disclosed to siblings; and a Spec Context Project
can now own one main repository plus any number of associated repositories, on one
accessor, with ALIVE/DEAD, the CLI verbs, export/import and the panel all covering the
full set.

Amendment 1 folded the 2026-08-23 skills audit into the same release and turned the
operator's standing order — permanent architecture review oriented by bug history — from
an exhortation into machinery: `dd-bug-fix` gained a six-phase diagnosing method with a
checkable "Done when" per phase, `dadaia bugs append --event resolved` now refuses
evidence a reader cannot check, a net-positive diff on a touched feature routes through
`software-architect` before the commit, and the bug-surface delta became a required field
of every review verdict. The law now reaches each harness exactly once, the per-prompt
injection carries memory rather than a restatement of the law, and 25 verified sediment
citations were corrected under a machine citation check that keeps them corrected.

Thirteen bugs picked at definition were closed or superseded, and roughly a dozen more
were found and closed in flight — including two HIGH cross-context defects that a
completeness challenge on a fix uncovered. The release ends smaller than it started:
production LOC net **−130**, AI-surface net **−943**, one enforcer where there were two,
one branch-resolution seam where there were two, one atomic-writer idiom where there were
two, and one resolution-evidence gate where there was a length floor that 132 historical
events cleared by saying nothing.

## Tasks completed

`TASKS.md` carries 57 declared markers; the retired ids (T-044-12/17/25/32/43) were
removed at the D8 restructure and are not reused. The branch log is the authoritative
per-task record — the table names the commits this closure could cite from the review
artifacts and the reflog; every other task's final commit is recoverable from
`git log --oneline f5cce371..HEAD` on `feature/0.4.4`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-044-01 … 02 | definition commit + milestone (a), the v1 mechanic once (E-1/D2) | branch log |
| T-044-03 | HIGH marker bug — evidenced negative + contract test | ledger line 948 |
| T-044-04 | FR1 — one gitflow law section | branch log |
| T-044-05 | FR2 — `dd-gitflow-default` (rename + v2 rewrite) | branch log |
| T-044-06 | FR3 — chokepoint inversion | `a9a40b8f` |
| T-044-07 | FR4 — CI triggers, two-edge `pr-source-guard`, verdict PR gate | branch log |
| T-044-08 | FR5 — 14 surfaces become pointers | `3dfb201c` |
| T-044-09 | FR6 — preflight/CI parity | `d28405e8` |
| T-044-10 | denylist amnesty bug (found mid-segment) | branch log |
| T-044-11 | `S1` QA close + AR-2 ruling | `reviews/S1-qa-close.md`, `reviews/S1-AR2-ruling.md` |
| T-044-13 | FR7 — the rules-skills map | `e6421966` |
| T-044-14 | FR8 — the map is core law (both constitutions) | `b4ad29a7`, `288c9ba9` |
| T-044-15 | FR9 — one deterministic enforcer | `2023e8af` |
| T-044-16 | `S2` QA close | `reviews/S2-qa-close.md` |
| T-044-18 | FR10 — `dd-release-closure` folded in | branch log |
| T-044-19 | FR11 — `dd-ai-eng-knowhow` | branch log |
| T-044-20 | FR12 — four renames + `dd-grill-me` ratified | `033bc6f7`, `14746d8d`, `7c608ea9`, `e563ab2a` |
| T-044-21 | FR13 — the single projection cycle + golden regen | `43feb5f6` |
| T-044-22 | AR-1 ruling | `reviews/S3-AR1-ruling.md` |
| T-044-23 | FR14 — the nine-skill study | handoff `2026-08-24T015304Z-ai-engineer-nine-skill-study` |
| T-044-24 | `S3` QA close | `reviews/S3-qa-close.md` |
| T-044-54 | FR25 — the four kept skills trimmed | `decd19df` |
| T-044-55 | FR26 — depth moved to siblings | branch log |
| T-044-56 | FR28 — the invocation model | branch log |
| T-044-57 | FR24 + FR29 — the verdict axis and the persona pass | `ec6cce73` |
| T-044-58 | FR27 — 25 sediments + the citation check | branch log |
| T-044-59 | FR31 — the law loaded once per harness | `caa32d1c` |
| T-044-60 | FR30 — `ctx_inject` stops restating the law | `8815df07` |
| T-044-26 … 30 | FR15–FR19 — the associated-repo model, verbs, surfaces | `9163932d` `69c279b2` `80d4a329` `2299c01f` `a86b9e1a` `627b8ae5` |
| T-044-31 | `S4` QA close | `reviews/S4-qa-close.md` |
| T-044-61 | FR22 — `dd-bug-fix` becomes a method | `170b0e61` |
| T-044-62 | FR23 — the three-field `resolved` gate | `8d94bbe7` |
| T-044-33 … 40 | the eight-bug sweep | `f3b95a4d` `5af53a7c` `7d9e8382`+`d3346382` `d9bb8004` and siblings |
| T-044-41 | FR20 — branch hygiene | `19f9ad9f` |
| T-044-42 | `S5` QA close | `reviews/S5-qa-close.md` |
| T-044-44 | scope-complete gate capture | `7a8a0175` |
| T-044-45 | six-axis code review, 3 passes → APPROVED | `reviews/T-044-45-code-review.md`, reviewed `3bf5824c` |
| T-044-46 | security review APPROVED + QA release verdict | `1bc9a5ea`, `6bdf15d0` |
| T-044-52 | `rc-1` — PR 208 merged into `develop`, CI green | `ee67e47c` (merge), `8dce63d7` (record) |
| T-044-53 | `rc` adjustment rounds — accepted with zero rounds | `15afd9fd` |
| T-044-47 | the memory window | this commit's parent |
| T-044-48 | this `CLOSURE.md` | this commit |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| V6 — FR3 net production LOC ≤ 0 | `git show --numstat a9a40b8f` | net **−35** (`reviews/S1-qa-close.md` §1 A3.6) |
| V7 — golden regen multiset diff, every line FR-attributed | `UPDATE_INSTALL_GOLDENS=1` regen + Counter-diff | `.dadaia/tmp/software-engineer/20260824/V7-golden-multiset-diff.md`; policy golden sha256 identical before/after |
| V8 — v2→v3 registry migration on real data | `state_v3.plan_migration()` / `execute_migration()` against a byte-verified copy | `reviews/S4-qa-close.md` §1 A15.1 — backup byte-identical, re-run a proven no-op, live registry untouched |
| V9 — projection truth across four targets | `dadaia public doctor` | `[ok] public-privacy`, `[ok] entities-derivation` (9↔9), `[ok] model-resolution`, 207 `[ok]`, zero `[drift]`/`[missing]` |
| V10 — `origin` before/after the branch sweep | `git ls-remote --heads origin` / `--tags` | `.dadaia/tmp/claude/20260824/T-044-41-V10-before.txt` and `-after.txt`; after = `main` + `develop` + 50 `archive/*` tags |
| V11/V12 — scope-complete gate capture (A21.4 / A21.8) | `dadaia ci preflight`, `specs doctor`, `backlog doctor`, `public doctor` | T-044-44 capture at `7a8a0175`: production **−130**, AI-surface **−943**, suite 0 failed |
| V14/V15/V16 — always-on tokens, negations, description cost | per-file counts at T-044-57/56 | negations **189 → 123** (−34.9 %); persona bodies **3165 → 2170** lines (−31.5 %); `disable-model-invocation` on exactly the human-entry skill |
| V17 — body size across the trimmed/disclosed skills | `wc -c` / `wc -l` baseline vs HEAD | four kept skills 364 → 353 lines; the four retired AI-harness `SKILL.md` files 78,289 → 8,194 bytes (**−89.5 %**); fused `SKILL.md` 122 lines (≤ 200) |
| V18 — injected prefix, bound and unbound, on a real session | `ctx_inject` measured on a live session | `.dadaia/tmp/claude/20260824/T-044-60-V18.txt` — measured **−313 tokens**; AFTER-bound **2,778.8–2,787.8** tokens, target ≤ 0.7k **NOT met** (see Drifts) |
| V19 — AI-surface accounting | `git diff --numstat` over `public/{agents,skills,data,entities}/**` | **+3021 / −3964 = −943**; skills 25 → 21 |
| A9.1/A9.2/A27.20 — the one enforcer, green at HEAD, mutation-proven | `pytest -q tests/contract/test_rules_skills_map.py` | **23/23 passed**, including two dead-citation mutation fixtures |
| A23.6 — the FR23 gate is satisfiable, and refuses precisely | `dadaia bugs append --event resolved` against a throwaway specs dir | `reviews/S5-qa-close.md` §2 — missing field refused by name, nothing written; complete event accepted first try |
| A31.1 — the law loads once in a Claude Code session | `pytest -q tests/integration/test_claude_code_law_single_load.py` | green against a real `install --target all` tree; `.codex/`/`.kimi-code/` verified "already single" |
| Full suite at the release verdict | `pytest -p no:cacheprovider -q` | **2822 passed, 4 skipped, 0 failed**, 94.29 s at `c7cc8d04` |
| Local CI preflight | `dadaia ci preflight` | **PASS** — format, lint, `mypy --strict`, `lint-imports`, pytest (5/5) |
| `specs doctor` | `dadaia specs doctor` | **0 errors**, 4 pre-existing warnings (2 legacy `_archive` release-dir names, 2 legacy audit dispositions) |
| `backlog doctor` | `dadaia backlog doctor` | clean |
| Self-scan (privacy) | `pytest -q tests/integration/test_repo_self_scan.py` | 5 passed at the final code-review pass |
| Push-gate probe, real refspec | `dadaia ci push-gate-check` | exit 0; `develop` push refused naming the PR path (`reviews/S1-qa-close.md` A3.1) |

## Size accounting

**Mandatory** (A21.4). Measured at T-044-44 (`7a8a0175`) over `dadaia_workspace/**`, and
re-confirmed at the release verdict.

| Metric | Value |
|--------|-------|
| Production LOC added | `4528` |
| Production LOC deleted | `4658` |
| Production LOC net | `−130` (**−813** excluding `S4`'s sanctioned additive scope) |

**Three largest additions by file** (from the reviews' per-commit accounting):

| File | LOC added |
|------|-----------|
| `dadaia_workspace/features/spec_context/service.py` | `+296` |
| `dadaia_workspace/features/migrate/state_v3.py` | `+127` (new file) |
| `dadaia_workspace/cli/commands/context.py` | `+267` |

**Three largest deletions by file:**

| File | LOC deleted |
|------|-------------|
| `dadaia_workspace/features/chokepoints/service.py` | `−112` (against `+75`) |
| `dadaia_workspace/public/scripts/lint-skill-collisions.py` | `−232` (deleted with its `DECLARED_OVERLAPS` table) |
| `dadaia_workspace/hooks/ctx_inject.py` | `−28` (against `+15`) |

| Ceiling | Before | After | Justification (only if decreased) |
|---------|--------|-------|------------------------------------|
| `C90` (`max-complexity`) | `63` | `63` | n/a — unchanged; an increase would have been refused |
| `PLR1702` (`max-nested-blocks`) | `6` | `6` | n/a — unchanged |

**Nesting-violation count:** `0` against the pinned `PLR1702` ceiling (`ruff check
--no-cache` clean at every segment close and at the release verdict).

### AI-surface accounting *(Amendment 1 — A21.8)*

Measured over `dadaia_workspace/public/{agents,skills,data,entities}/**`.

| Metric | Value |
|--------|-------|
| Lines added | `+3021` |
| Lines deleted | `−3964` |
| **Net** | **`−943`** — A21.8 holds; no operator ruling on a positive net was needed |
| Skill folders | `25 → 21` (A21.11 holds; the audit's ~19 is the post-FR14 target, D12) |

**The measured targets, with their V-ids:**

| Target | Before | After | Result |
|---|---|---|---|
| Skill count (A21.11) | 25 | **21** | MET |
| AI-surface net lines (A21.8, V19) | — | **−943** | MET |
| Citation zero (A21.10, A27.20) | 25 verified sediments | **0**, machine-verified | MET |
| Fused AI skill size (A11.4/A11.8, V17) | 78,289 bytes / 1,372 lines across 4 folders | 8,194 bytes / **122 lines** | MET (−89.5 %, ceiling ≤ 200) |
| Persona bodies (A29.1, V17) | 3,165 lines | 2,170 lines | **PARTIAL** — 5/9 inside 120–220; 4 overflow (273/334/274/252), each justified per A29.3 |
| Negations (A21.9, V15) | 189 | 123 | **MISSED** against ≤ 60 — net-negative, target not reached |
| Always-on tokens (A21.9, V14/V16) | ~8.4k | 8.2k–11.8k measured | **MISSED** against ≤ 3.5k |
| Injected prefix, bound (A30.2, V18) | ~3.09k | 2.78k | **MISSED** against ≤ 0.7k; FR30's own deletion fully verified (−313 tokens) |

Every missed target moved in the right direction and none regressed. The residual gap is
one structural cause, disclosed at `S3` close and re-confirmed at the release verdict: the
lean memory prefix — explicitly **unchanged** by FR30 per A30.3 — is now essentially the
whole payload, because `catalog.json` carries 26 feature entries. Closing it belongs to
whichever feature owns catalog curation, not to `ctx_inject` or to a persona trim; it is
routed to the PM intake report (theme C), not silently carried.

### The audit-fold record *(Amendment 1)*

| Audit item | Carried by | Evidence |
|---|---|---|
| A.1 — "root cause" becomes a method | **FR22** (inside `dd-bug-fix`, no new skill) | `170b0e61`; six phases each ending in a "Done when"; the no-seam clause stated once |
| A.2 — the `resolved` evidence gate | **FR23** | `8d94bbe7`; refusal names the missing field, nothing written; `bug-event-v1` extended; historical events still fold |
| A.5 — the bug-surface axis in verdicts | **FR24** (three personas, no new skill) | `ec6cce73`; one statement per persona, "tests green is insufficient" once each |
| B · manter — the four kept skills trimmed | **FR25** | `decd19df`; 364 → 353 lines; no sha, no private branch example, no "one question per turn" |
| B · disclose — depth to siblings | **FR26** | `RUBRIC.md`, `TOOLING.md`, `PARAMETERS.md`, `CLOSURE-TEMPLATE.md`, `CLOSURE-CHECKS.md`; the audit-dimension contradiction resolved to one list |
| B · corrigir sediment — 25 items | **FR27** | all 19 enumerated items fixed, then the citation check landed green at HEAD (A27.20), mutation-proven red on a planted dead citation |
| B · user-invoked + C.4 — the invocation model | **FR28** | `disable-model-invocation` on the human-entry skill; equivalence checked in both directions by the enforcer; "Call the Skill tool with `X`" for operative dependencies |
| C.1 — the law loaded twice | **FR31** *(registered as a bug and fixed as Arm B)* | `caa32d1c`, net −1 LOC at the projection seam; other harnesses verified "already single" |
| C.2 — personas carry only what the law does not | **FR29** | `ec6cce73`; −31.5 % lines; coverage table per removed block |
| C.3 — `ctx_inject` restates the law | **FR30** | `8815df07`, net −13 LOC, no new branch or flag |

**Refused items, and where they went:**

| Refused | Reason | Where it went |
|---|---|---|
| Delete/fuse `dadaia-workspace-doctor` and `project-orchestration` | D9 — the grill (G11) wins over a research report; both are **kept and renamed** (`dd-workspace-doctor`, `dd-manager-orchestration`) | closed here; not re-litigated |
| Delete/fuse proposals for `dadaia-workspace-manager`, `dadaia-workspace-spec-reviewer`, `dev-server-registry`, `architect-core-workflow` | D9 — evidence, not authority | **evidence input to FR14's study** (A14.5); the operator decides |
| Section D — eight proposed new skills (`dd-diagnose`, `dadaia-codebase-design`, `dd-architecture-survey`, `dd-code-review`, `dadaia-glossary`, `dadaia-router`, `dd-tasks-as-tracer-bullets`, `dadaia-wizard`) | operator ruling 2026-08-23 — out of scope (§4.10) | **backlog**, registered by `project-manager`; all eight are `## ACTIVE` candidates today |
| Roadmap R3 (vocabulary, glossary, architecture survey) | same ruling | backlog |

## Drifts

### a30-2-injected-prefix-target-unmet

**Description:** A30.2 required a bound session's injected prefix at ≤ 0.7k tokens. FR30's
own deletions landed and are fully verified (A30.1 and A30.4 both PASS, net −13 LOC, a
measured −313-token delta), but the measured AFTER-bound figure is 2,778.8–2,787.8 tokens
— about 4× the target. A30.3 required the memory prefix to be **unchanged**, and that
prefix (tech-stack digest + `catalog.json` digest) is now essentially the entire payload,
because this repo's catalog carries 26 feature entries.

**Resolution:** Disclosed rather than closed. The two acceptances are in genuine tension —
A30.3 passing is the reason A30.2 cannot close inside FR30's scope — so the number was
reported honestly at `S3` close, re-confirmed at `S5` and at the release verdict, and the
structural fix (catalog trimming/paging at the memory layer) routed to the PM intake
report. Nothing was weakened to make the number look met.

**Memory updates:** `specs/memory/product/platform/context-management.md` records what the
injection now carries (state, not a restatement) without claiming a token figure it does
not meet.

### a29-1-four-personas-over-the-line-ceiling

**Description:** A29.1 states a hard 120–220 line range for every persona. Five of nine
land inside it; four overflow (273, 334, 274, 252). Each overflow's load-bearing content —
the three-harness table, the SDD file hierarchy, the E2E toolchain, the three operating
modes — has no sibling mechanism to move to.

**Resolution:** Disclosed by the implementer's own commit and independently re-confirmed at
`S3` close. Justified per A29.3's own rule ("a fact with no other home stays"), with every
persona still net-negative against its pre-`S3` baseline. Routed to intake as a follow-up
trim pass if the operator wants one.

**Memory updates:** `specs/memory/architecture.md` states the persona contract as a
**target** (120–220) with the "a fact with no other home stays" carve-out, rather than as a
met invariant.

### ar-1-byte-goldens-fuse-policy-and-inventory

**Description:** Two byte goldens encode the entire projected file inventory alongside the
policy they exist to lock, so every legitimate rename forces a full regen — and a regen is
where an unintended change hides. Three further tests hardcode copies of the same
inventory. Four registered recurrences of this class span v0.2.5 → v0.4.4, two of them in
this release.

**Resolution:** `software-architect` ruled **(c) split the inventory out of the byte
golden** — a derived roster oracle for the inventory, a small stable byte golden for the
policy. The execution is **intake, not v0.4.4 scope** (SPEC §4.3). Interim law until it
lands: the T-044-21 regen protocol (multiset diff, every line FR-attributed in the commit
body, the policy golden byte-identical or it is a defect), whose reference execution is
`43feb5f6` + the V7 capture.

**Memory updates:** none — the mechanism is test architecture, not product truth.

### rc-1-ci-surfaced-two-platform-defects-the-local-gate-could-not

**Description:** The `rc-1` PR was the first time this release's work ran the full CI
matrix, and it turned red twice on Windows-specific defects a Linux-only local preflight
structurally cannot see: the citation enforcer resolved projected instance paths against
the checkout, and its mutation fixtures could never turn red on Windows.

**Resolution:** Both root-caused and fixed on the branch inside the `rc-1` round
(`a7a67541`, `8ca3ea3c`), each registered as a bug with three-field evidence, each
re-reviewed by `security-reviewer` on its own sha, and the second ruled by
`software-architect` as FR23 firing 7. This is the `rc` lane behaving exactly as D8
intends — a defect in this scope's own delta, found by exercising the merged state, fixed
here rather than deferred.

**Memory updates:** none — the fixes restored the enforcer's stated contract rather than
changing it.

## Memory updates

Written in the CLOSURE phase, one authoring pass per atom (T-044-47).

- `specs/memory/product/sdd/sdd-gate-v3.md` — **mandatory rewrite**: the chokepoint
  inverted (`feature/{M.m.p}` the only pushable ref; `develop`/`main` refused as PR-only),
  three branch patterns with no `v` and no `hotfix`, the preflight/CI parity, the security
  verdict relocated to the PR gate with its committed-evidence channel and fail-closed
  coverage check, `gc-push-verdicts` re-keyed to the merged PR head sha, and the branch
  model itself reduced to a pointer at the law and `dd-gitflow-default`.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — **mandatory rewrite**:
  "Branches And Stage Placement" collapsed to a pointer with every stage on the one live
  feature branch; "Merge Cadence" re-expressed as PR-only `develop`, the `rc-N` ladder with
  no alpha or beta, segments that burn no `rc`; the hotfix doctrine retired; a new
  "Resolution" section carrying FR23's three required evidence fields and the
  net-positive-diff architect trigger, plus FR22's six-phase method and its no-seam clause.
- `specs/memory/quality-assurance.md` — CI triggers now include `feature/**` and both PR
  edges; the two-rule single `pr-source-guard`; the security-verdict PR gate and its
  advisory-first window; preflight/CI check parity pinned by a test; the bug-surface delta
  as a required verdict field; suite figure re-measured (2,822 passed, 4 skipped).
- `specs/memory/architecture.md` — the pre-push script row drops the verdict step; the
  Agent Surface section gains the branch-contract pointer, the persona size/positive-target
  contract, the one-map/one-enforcer/citation-check statement, and the one-load-per-harness
  law-projection rule.
- `specs/memory/product/agents/agentic-entities.md` — skills are folders projected whole;
  the `dd-` family named without the retired closure skill; a new "The rules-skills map"
  subsection covering the map, the single enforcer's six failure modes, the citation check,
  the bidirectional invocation-model equivalence, and the retired collision lint with its
  ported self-tests; `dadaia-cli` → `dd-cli-library`.
- `specs/memory/product/agents/agent-orchestration.md` — the stage→skill list folds closure
  into `dd-release-implement`; the bug arm's ordered method and its evidence gate;
  merge-gated (not push-gated) security evidence; the bug-surface axis on every verdict.
- `specs/memory/product/distribution/public-asset-distribution.md` — a skill is a folder
  and every sibling is staged, installed, manifest-tracked and doctor-checked; 21 skills;
  `dd-gitflow-default` named; `dd-ai-eng-knowhow` as the one harness-literacy home; the
  law reaching each harness exactly once, decided at the projection seam.
- `specs/memory/product/platform/context-management.md` — main + associated repo model,
  the one accessor, the backup-first idempotent v3 migration, ALIVE/DEAD over the full set,
  the `context repo` verbs, the single-owner slug invariant at both write seams, a new
  "Usage" section covering `list`/`show` branch agreement and export/import round-trip, the
  associated-repo resolution walk, the lean bind-driven injection, and one place of control.
- `specs/memory/product/philosophy/spec-context-project.md` — one main repo as the sole
  source of specs, bind, memory, releases and backlog; associated repos carry source only.
- `specs/memory/product/platform/repos-catalog.md` — `repos/` mirrors the full repo set;
  the catalog feeds `--associated` and `context repo add` too.
- `specs/memory/product/panel/panel.md` — the context card lists main + associated.
- `specs/memory/product/harness/harness-claude-code.md` — 21 skill folders; the root
  `CLAUDE.md → AGENTS.md → DADAIA.md` chain named as the single law load path.
- `specs/memory/product/harness/harness-codex.md` — the native `AGENTS.md` path verified as
  a single law load.
- `specs/memory/product/harness/harness-kimi-code.md` — same verification recorded.
- `specs/memory/product/distribution/pypi-distribution.md` — the published lineage
  `0.4.2 → 0.4.4`, with `0.4.3` recorded as a retired local-only mint.
- `specs/memory/product/index.md` + `catalog.json` — the changed `tldr`/`summary` values
  mirrored; catalog **membership and order are unchanged**, so no atom was added, removed
  or re-ranked.
- `specs/memory/product/sdd/specs-doctor.md` — **no change**: no `specs doctor` rule was
  added, removed or altered by this release. The doctor changes this release touched are
  `backlog doctor`'s parser (recorded in `sdd-bug-backlog-governance.md`) and `public
  doctor`'s existing checks, which are unchanged in identity.
- `specs/memory/tech-stack.md` — **no change**: the release added no dependency and changed
  no pinned version (`new_dependencies: 0` in the security handoff).

## Dispositions

### Backlog — 4 entries, `DELIVERED · v0.4.4`

Each is an **update** of the `CONSUMED` line purge-on-pick wrote at definition, never a
second `## LEDGER` line (BL-DUP).

| Record | Kind | Terminal disposition | Evidence |
|--------|------|-----------------------|----------|
| `specs/backlog/BACKLOG.md` (`gitflow-contract-v2-consolidation`) | backlog | `DELIVERED · v0.4.4` | FR1–FR6; `reviews/S1-qa-close.md` |
| `specs/backlog/BACKLOG.md` (`rules-skills-governance-map`) | backlog | `DELIVERED · v0.4.4` | FR7–FR9; `reviews/S2-qa-close.md` |
| `specs/backlog/BACKLOG.md` (`core-skills-consolidation`) | backlog | `DELIVERED · v0.4.4` | FR10–FR14 + FR24–FR31; `reviews/S3-qa-close.md` |
| `specs/backlog/BACKLOG.md` (`spec-context-associated-repos`) | backlog | `DELIVERED · v0.4.4` | FR15–FR19; `reviews/S4-qa-close.md` |

`## ACTIVE` is **not** empty at this closure: it carries the eight section-D skills the
operator ruled to the backlog on 2026-08-23 plus three later operator-created entries
(`cli-help-architecture-and-session-injection`, `specs-canon-v6`, `entity-behavior-map`).
None was picked by this release; A21.5's "`## ACTIVE` empty" clause is therefore **not
met**, and correctly so — those entries are new operator demand created *during* the
release, not residuals this release failed to consume.

### Bugs — 12 `Closed`, 1 `Closed` + `superseded_by`

| Record | Kind | Terminal disposition | Evidence |
|--------|------|-----------------------|----------|
| `sdd-artifact-linter-mutates-task-markers` (HIGH) | bug | `Closed` | evidenced negative + `tests/contract/test_sdd_writers_never_mutate_task_markers.py` (6/6); ledger line 948 |
| `prepush-gate-omits-import-boundary-contracts-ci-runs` (MEDIUM) | bug | `Closed` | FR6 parity test 2/2; ledger line 950 |
| `dadaia-md-projected-twice-into-claude-code-context` (MEDIUM) | bug | `Closed` | FR31; `caa32d1c`; ledger line 960 |
| `codex-live-probe-gate-checks-presence-not-usability` (MEDIUM) | bug | `Closed` | adapter-seam classification; ledger line 945 |
| `backlog-doctor-silent-on-duplicate-top-level-sections` (MEDIUM) | bug | `Closed` | `f3b95a4d`; FR23 firing 1 SOUND; ledger line 974 |
| `atomic-writer-drift-guard-is-brittle-and-covers-only-two-of-eight-writers` (LOW) | bug | `Closed` | `5af53a7c`; FR23 firing 2 SOUND; ledger line 975 |
| `backlog-doctor-rejects-deferred-status-documented-by-skill` (LOW) | bug | `Closed` | ledger line 976 |
| `migration-normalises-crlf-atoms-to-lf-contradicting-its-byte-preserve-wording` (LOW) | bug | `Closed` | ledger line 977 |
| `crlf-fixture-makes-a-windows-assertion-pass-for-the-wrong-reason` (LOW) | bug | `Closed` | ledger line 979 |
| `no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` (LOW) | bug | `Closed` | `7d9e8382` + `d3346382`; FR23 firing 3 SOUND; ledger line 981 |
| `symlinked-specs-root-is-followed-by-migration-and-repair` (LOW) | bug | `Closed` | `d9bb8004`; FR23 firing 4 SOUND; ledger line 982 |
| `read-only-atom-honouring-is-advisory-and-root-bypasses-it` (LOW) | bug | `Closed` | ledger line 983 |
| `context-list-current-branch-stale-for-alive-repo` (LOW) | bug | `Closed` + `superseded_by: spec-context-associated-repos` | `superseded` 2026-08-23, `archived` 2026-08-24; acceptance carried by FR18/A18.1–A18.3 |

### Bugs closed in flight (Arm-B riders, not picked at definition)

Registered and resolved on `feature/0.4.4` during implementation. Every one carries a
`resolved` event; those appended after T-044-62 carry FR23's three fields.

| Record | Severity | Evidence |
|---|---|---|
| `new-branch-push-loses-prior-published-denylist-amnesty` | HIGH | ledger 952 — two range-derivation shapes collapsed to one |
| `context-repo-add-accepts-foreign-context-slug` | HIGH | ledger 986 — code review F-1; `1f50dbdf`; FR23 firing 5 SOUND |
| `context-create-accepts-slug-owned-by-another-context` | HIGH | ledger 988 — F-12, found by the architect's mirror-gap check; `ed5d64cd`/`3bf5824c`; FR23 firing 6 CONFIRMED |
| `citation-mutation-fixtures-never-turn-red-on-windows` | HIGH | ledger 994 — `rc-1` CI; `8ca3ea3c` |
| `v0.4.4-reviews-dir-untrackable-gitignore-recurrence` | MEDIUM | ledger 955 |
| `t044-04-renumber-stale-DADAIAmd-section-citations` | MEDIUM | ledger 956 — 44 citations title-anchored |
| `gitignore-verdict-evidence-untrackable-fourth-recurrence` | MEDIUM | ledger 990 — closed **structurally** (`c7cc8d04`), inverting the release-tree ignore rule instead of a fifth per-artifact whitelist line |
| `citation-enforcer-resolves-projected-instance-paths-against-the-checkout` | MEDIUM | ledger 992 — `a7a67541`; FR23 firing 7 SOUND |
| `skill-orphan-checker-misses-disable-model-invocation` | LOW | ledger 963 |
| `test-public-assets-stale-grill-me-name` | LOW | ledger 964 |
| `test-public-pipeline-stale-skill-roster` | LOW | ledger 965 |
| `s2-qa-close-review-leaks-home-abs-path` | LOW | ledger 967 — privacy, redacted at authoring |
| `self-scan-baseline-drift-t04427-test-fixture-email` | LOW | ledger 969 — fixed at the fixture value, never by widening the baseline |
| `self-scan-baseline-drift-s4-qa-close-review-prose` | LOW | ledger 972 |

**A23.4 restatement.** Two `resolved` events were appended **before** FR23 landed and
therefore predate the three-field gate; their ledger events are not rewritten (A23.2), and
their evidence is restated here in FR23's shape:

| Bug | Red-loop command | Test seam | Diff direction |
|---|---|---|---|
| `sdd-artifact-linter-mutates-task-markers` (T-044-03, `S1`) | `pytest -p no:cacheprovider -q tests/contract/test_sdd_writers_never_mutate_task_markers.py` | `tests/contract/test_sdd_writers_never_mutate_task_markers.py` — a contract test over every product-owned writer of `specs/releases/**/*.md` | `net-neutral` on production: evidenced negative (no product-owned writer mutates a marker or a `**Status:**` token); the diff adds the pinning test only |
| `prepush-gate-omits-import-boundary-contracts-ci-runs` (T-044-09, FR6) | `python -c "import dadaia_workspace.features.ci_preflight.service as svc; print(svc.checks_for(quick=True))"` then `pytest -q tests/contract/test_ci_preflight_ci_gating_parity.py` | `tests/contract/test_ci_preflight_ci_gating_parity.py` — fails when either side gains a check the other lacks | `net-negative` on documentation, `net-neutral` on production: `lint-imports` was already wired; the fix removed the false CI-equivalence claim and pinned the parity |

The other two pre-Amendment-1 sweep bugs (`v0.4.4-reviews-dir-untrackable-gitignore-recurrence`,
`t044-04-renumber-stale-DADAIAmd-section-citations`) already carry three-field-shaped
evidence in their own events and need no restatement.

### Bugs open at closure — 8, zero HIGH, zero CRITICAL

None is a defect of this release's delta; all are recorded for the PM's intake feed.

| Bug | Severity | Why it stays open |
|---|---|---|
| `sdd-gate-blocks-fresh-repo-root-agents-md` | MEDIUM | foreign to every task's write set; reported by another session mid-release |
| `repo-agents-md-law-gate-contradicts-template` | MEDIUM | same gate surface; likely shares a root cause with the above — routed to intake together |
| `bug-event-field-with-unicode-line-separator-silently-drops-the-event` | MEDIUM | pre-existing writer/reader mismatch surfaced by the code review's probe; FR23 widened its exposure without causing it |
| `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` | LOW | found **by** T-044-35's battery, pinned as current behaviour by a self-destructing test; the architect ruled the consolidation subsumes it, so a two-call-site patch was deliberately refused |
| `dadaia-task-manager-stale-workspace-protocol-citation` | LOW | pre-existing citation drift, unrelated to any FR surface |
| `certify-skip-detail-leaks-full-codex-output` | LOW | pre-existing, registered before `S5` opened |
| `codex-probe-unit-fixture-carries-real-session-uuid` | LOW | pre-existing, registered before `S5` opened |
| `windows-xdist-workers-crash-on-unit-fast-tier` | LOW | `rc-1` CI observability finding; the tier is green, the worker crash is a reporting defect |

## Test dispositions

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| demotion | `tests/unit/features/chokepoints/test_push_gate_decision.py` (whole file — the v1 verdict-in-push-gate coverage) | `test_push_branch_policy.py` + `test_iter_security_approvals.py`; the latter's docstring names the supersession | A4.5; deleted under the QA verdict route, not by the implementer |
| SCAFFOLD expiry | `tests/integration/test_cli_context_repo_verbs.py` (undeclared → SCAFFOLD-by-default, due to expire at this closure) | **promoted to CONTRACT** — now declares `Intent: CONTRACT — A17.1, A17.2, A17.3` | code review F-6, closed at `76d9db9b` |
| quarantine expiry | none | no test entered or left quarantine this release; the cap (8) was never approached | `pytest -m quarantine` selectors unchanged |
| coverage growth, governed | `tests/unit/.../test_migration_symlink_hardening.py` grew from a 2-of-8 comparator to a 32-item battery (46 passed, 9 cases) | earned exception, ruled SOUND (FR23 firing 2); the brittle comparator was **deleted at root** | `reviews/S5-FR23-first-firing-ruling.md` Firing 2 |
| e2e budget | zero new `tests/e2e/**` files | `tests/e2e` is net **−38 lines**; the LARGE census stays at 100 | code review §3 |

**Off-taxonomy declarations, record-only:** repo-wide the `Intent:` kinds now stand at 129
CONTRACT, 8 REGRESSION, 6 SENTINEL, 3 BUG. `REGRESSION` and `BUG` are outside the four
declared kinds; five of the eight `REGRESSION` labels predate this release. Nothing keys
off the string, so no test is at risk. This is a vocabulary decision for the stewardship
skill's owner, routed to intake rather than relabelled here.

## Record-only observations

| Source (reviewer/handoff) | Observation | Why record-only |
|---|---|---|
| `code-reviewer` F-9 | `context list --json` now issues 2 git subprocesses per on-disk repo where it previously read a stored snapshot | Measured **inside** CLI-startup noise (~1.23–1.33 s for 11 contexts against a ~1.23–1.45 s baseline); the trade is the correctness fix that killed the branch-disagreement bug |
| `code-reviewer` F-7 / F-8 / F-10 | vestigial names (`review_refs`, `ctx_latest`) and a "byte-for-byte" docstring using universal-newline I/O | LOW, cosmetic, no behaviour; deferred to the next touch of each file |
| `code-reviewer` INFO-11 | this working copy has no pre-push hook installed (`.git/hooks/` holds only samples) | Environment state, not a diff defect; `dadaia ci install-hook` before the ship push — named as the one operational item |
| `software-architect` AR-2 §2.2 | `verdict-gate`'s security half is now the weaker sibling of the stronger automatic PR gate | Distinct predicate at a distinct moment today; deleting it would drop the only mechanical qa-verdict check. Awareness-only |
| `qa-engineer` S4 §5.1 | the v2→v3 migration has no CLI verb — it is a library call by design, with a v2-tolerant read path | Explicit, disclosed scope boundary with a stated rationale (the version-gate-with-no-repair-path bug class); acceptance is met at the function level |
| `qa-engineer` S4 §5.2 | `TASKS.md` T-044-26's write-set line names `state_v2.py`; the work correctly landed in a new `state_v3.py` sibling | Definition-time typo, zero behavioural effect |
| `qa-engineer` S5 §4.3 | T-044-39's `TASKS.md` entry carries no inline `**Resolution:**` narrative, unlike its siblings | Documentation-consistency gap; the full evidence is in the commit body and the ledger event, both verified complete |
| `qa-engineer` S5 §3 | T-044-41's task prose named 15 branches; the sweep archived-and-deleted ~34 more pre-existing slop branches to satisfy A20.2's broader invariant | Every deleted branch is tag-reachable and spot-verified; the prose under-described its own blast radius |
| T-044-44 gate capture | `dadaia doctor` alone fails on an unlisted operator research directory at the workspace root | Pre-existing, outside this repo, untouched by any v0.4.4 commit; the four SDD/CI doctors are green independently |

## Intake candidates

The closer creates **no** backlog entry. Every residual below was compiled by
`project-manager` into the operator-facing intake report
`.dadaia/handoff/dadaia-workspace/2026-08-24T172302Z-project-manager-v044-intake-report.handoff.json`
(15 candidates, nothing materialized into `BACKLOG.md`).

### To be adjudicated

1. **`atomic-write-primitive-consolidation`** (theme A, HIGH) — collapse the package's 8
   near-identical atomic-writer primitives into one parameterized primitive; structurally
   subsumes the open LOW bug rather than patching two call sites, and shrinks the battery
   from 8 seams to 1.
2. **`INTAKE-AR1-1`** — split the inventory out of the two byte goldens into a derived
   roster oracle, keeping a policy-only byte golden. Zero production-code change.
3. **`INTAKE-AR1-2`** — one shared oracle for the three coupled-inventory tests, closing
   the cross-write-scope drift seam that produced two bugs this release.
4. **Catalog trimming/paging at the memory layer** (theme C) — the structural cause of the
   A30.2 miss.
5. **Persona line-ceiling follow-up trim** — the four personas over 220 lines.
6. **`scan-test-vacuity-guard`** — none of ~15 tree-walking scan tests asserts its
   enumerated population is non-empty; a mis-rooted walker would pass vacuously green.
7. **`specs-init-symlinked-target-refusal`** — `specs init`'s explicit `--specs-dir` lane
   still resolves a symlinked target, the last unguarded rung of the CWE-59 class.
8. **`verdict-gate` security-half decision** — shed it or re-point it at the committed
   evidence channel (AR-2 §2.2).
9. **B2 — doctor-lane slug-ownership uniqueness** — the two write-seam guard never heals a
   pre-existing duplicate imported verbatim by the v2→v3 migration.
10. **A `dadaia migrate` verb for the v2→v3 hop** — reachable today only as a library call.
11. **Three inline `.tmp` writers outside the name-based census** (`state_v2.py`,
    `import_/service.py` ×2) — none added by v0.4.4; belongs to candidate 1.
12. **Off-taxonomy `Intent:` vocabulary** — absorb `REGRESSION`/`BUG` as declared kinds or
    relabel the eleven files.
13. **Citation residual** — `public/agents/ai-engineer.md` cites `§5` for content at `§3`
    and `§8`; the F-3 class at a different section.
14. **F-7 / F-8 / F-10 naming and wording residuals.**

### Pre-approved intake

- **The audit's section D — eight proposed new skills**, and **roadmap R3**. Operator
  ruling of 2026-08-23 during this release's Amendment 1: already-approved intake, already
  materialized by `project-manager` into `## ACTIVE`. Not re-adjudicated.

### Operator-only action items (not backlog)

- **B1 (HIGH, time-boxed):** the relocated CI verdict gate is a **required** check on
  neither PR edge. A4.4 sanctions this for `rc-1` only. Making it required is a repository
  setting — and `gh api PATCH required_status_checks` **clobbers** the list, so the full
  list must be re-supplied. Due before the next `develop` PR edge.
- **INFO-11:** run `dadaia ci install-hook` in this working copy before the ship push, so
  FR3's inverted chokepoint executes on the path it governs.

## Artifact GC sweep

Run after the `## Validations` and `## Dispositions` evidence pointers above were final.
Lane guard (AG.1) applied: every candidate resolved inside `.dadaia/`, no symlinked
directory followed, deletion scoped to individual consumed files.

| Artifact class | Kept (still referenced) | Deleted/archived | Evidence |
|----------------|--------------------------|-------------------|----------|
| `.dadaia/handoff/dadaia-workspace/*.handoff.json` (this release) | `3` — the grill handoff, the skills-audit handoff, the nine-skill study handoff (all three are cited by SPEC §7 / `## Validations`); the PM intake handoff is cited by `## Intake candidates` | **deferred to the dispatcher** — the per-consume ack-on-consume deletions already removed the coordination handoffs as they were read; no unreferenced residue was identified from the artifact list this closure could inspect | this section |
| `.dadaia/reports/dadaia-workspace/**` (this release) | `1` — the skills-audit research report (pages 01–05), cited by SPEC §7 as Amendment 1's provenance | `0` | SPEC §7 |
| `.dadaia/tmp/<agent>/**` (this release's captures) | `5` — `V7-golden-multiset-diff.md`, `T-044-60-V18.txt`, `T-044-41-V10-before.txt`/`-after.txt`, `gitflow-inventory.md` (all cited above or in SPEC §1) | **deferred to the dispatcher** — the QA E2E scratch state under `.dadaia/tmp/qa-engineer/20260824/` is unreferenced by any surviving pointer and is safe to delete | `## Validations`, SPEC §1 |

**Honest gap:** this closure is authored by a shell-less agent, so the two "deferred" cells
record a *decision* (what may be deleted and what must be kept), not an executed deletion
with counts. The kept column is exhaustive and binding — nothing it names may be deleted.
The dispatcher executes the sweep against exactly that list and may amend the deleted
counts in the archive commit.

## The `rc` ledger

Every `rc` burned, and what motivated it (A21.7 — the evidence that no `rc` carried new
scope).

| `rc` | What it carried | Found by / on | Merge |
|---|---|---|---|
| `rc-1` | the **whole** implemented scope S1–S5, gate-green, QA-closed, trio-approved | — (the first merge of the release; milestone (b)) | PR 208 → `develop`, `ee67e47c`, all CI jobs green |
| — | Two Windows-only CI defects surfaced **by the `rc-1` PR itself** and fixed inside that same round before the merge (`a7a67541`, `8ca3ea3c`), each with its own security verdict on its own sha | `rc-1` CI matrix | folded into the `rc-1` merge |
| `rc-2 … rc-N` | **none** — the merged `develop` was exercised and accepted with **zero adjustment rounds** | operator + `qa-engineer` (T-044-53) | n/a |
| final `rc` | the memory window, this `CLOSURE.md`, the archive move, the version bump | this closure | the final `feature/0.4.4` → `develop` merge (T-044-50) burns it |

**The final `rc` is `rc-1`**, exactly as D8 provides for when no adjustment is found. No
`rc` carried scope outside SPEC §3; the two in-round fixes were defects in this scope's own
delta, which the lane explicitly admits and which new backlog explicitly does not.

## Architecture rulings

### AR-2 — "the enforcement surface must shrink, not move" (`S1` close)

**Verdict: ENFORCEMENT-SURFACE SHRUNK.** Gross enforcement points 6 → 6 with exactly one
G6-ratified relocation (the security verdict, hook → CI); hook policy steps 4 → 3;
enforced-rule inventory net **−2**; branch patterns 4 → 3; range-derivation shapes 2 → 1;
**dual paths found: zero**; deletions demanded: none. The named failure mode — a hook
remnant coexisting with the CI job — did not materialize, and a contract test keeps it that
way. Two findings routed onward: a MEDIUM path-based coverage exemption (closed by the code
review's F-2 fix) and a LOW duplicated qualification predicate (deferred to next touch).

**Disposition:** recorded, no further work in scope.

### AR-1 — "byte goldens over a file inventory are fragile by construction" (`S3` close)

**Verdict: (c) SPLIT THE INVENTORY OUT OF THE BYTE GOLDEN**, with the execution routed to
intake (SPEC §4.3) and the T-044-21 regen protocol standing as the interim law. Reasoning
in the Drifts section above.

**Disposition:** ruling recorded; `INTAKE-AR1-1` and `INTAKE-AR1-2` filed as intake
candidates, unexecuted by design.

### The seven FR23 firings

Every net-positive diff this release produced on a touched feature was ruled by
`software-architect` **before** its commit, as FR23 requires.

| # | Task / fix | Verdict | Category |
|---|---|---|---|
| 1 | T-044-33, `f3b95a4d` — backlog duplicate-section enforcement | **SOUND** | missing enforcement at the owning seam |
| 2 | T-044-35, `5af53a7c` — atomic-writer behavioural battery | **SOUND** | governed test-coverage growth, defect deleted at root |
| 3 | T-044-38, `7d9e8382`/`d3346382` — frozen-clock aging ratchet | **SOUND** | mechanism growth, a third category earned on four stated conditions |
| 4 | T-044-40, `d9bb8004` — symlinked explicit specs root refused | **SOUND** | firing 1's category; production growth earned by behaviour deletion |
| 5 | F-1 fix, `1f50dbdf` — foreign-slug ownership at `add_repo` | **SOUND**, with one HIGH mirror gap named | firing 1's category; the "one seam" claim proven false |
| 6 | mirror-seam fix, `ed5d64cd` — the same predicate at `create` | **CONFIRMED** | firing 5's prescription executed verbatim, no drift, no extra shapes |
| 7 | `a7a67541` — citation enforcer proves the instance path by executing its generator | **SOUND** | mechanism-precision correction inside the one enforcer |

Zero REJECT. Zero puxadinho detected across seven independent reviews. Firing 5 is the one
worth naming twice: challenging a fix for *completeness* rather than accepting it green
found a second, still-open destructive seam — which firing 6 then closed.

## Standing-order verdict record

Per segment, whether the bug surface of each touched feature went down, with bug-history
evidence rather than test results.

| Segment | Direction | Evidence |
|---|---|---|
| `S1` — gitflow v2 | **REDUCED** | A whole enforcement step deleted with no replacement branch; the `hotfix` pattern and the `feature/v…` regex deleted outright; the two-shape range derivation — the *cause* of the amnesty bug — collapsed to one formula rather than patched in its fallback. Prior ledger bugs on this surface: 5, all on the push-scan feature. AR-2 measures enforced-rule inventory **−2**. |
| `S2` — the map | **REDUCED** | Two enforcers → one: a 232-line lint retired **with** its hard-coded table, its self-test fixtures ported. Net production **−17**. No second script, no new CI job, no new hook. |
| `S3` — skills consolidation | **REDUCED** | Five bugs closed with root-cause fixes (one MEDIUM structural double-load at the projection seam, net −1 LOC; four LOW stale-inventory-copy instances). The one internal line increase (`dd-release-implement` +24) is matched by deleting the entire donor folder. |
| `S4` — associated repos | **REDUCED net of its own sanctioned additive scope** | The only additive segment by design (R-2). Two LOW bugs closed structurally — the branch-disagreement fix collapses two divergent call sites into one seam rather than adding a refresh call. One unregistered data-loss defect (export dropping a field on every ALIVE export) was found and eliminated at its root within the same session, before ever shipping. Every "this context's repos" consumer resolves through **one** accessor. |
| `S5` — the sweep | **REDUCED** | All eight sweep bugs close REDUCED; three are pure deletions or docstring-only; two are net-positive in lines but net-**negative** in behaviours (a silent-acceptance path deleted in each). The one new production gap the segment surfaced was **found by** the fix, registered rather than hidden, and pinned by a test that self-destructs in the fix direction. |
| Whole release | **REDUCED on 10 of 11 touched features**, sanctioned-INCREASED on 1 (`S4`) | Code review's final per-feature tally. Ledger arithmetic: 23 `resolved` + 1 `superseded`/`archived` since release start against 8 open at closure, all LOW/MEDIUM, **zero HIGH/CRITICAL**. Production **−130**, AI-surface **−943**. |

**The repetition signal, and how it was answered.** One class in this release showed
textbook recurrence: `v0.4.4-reviews-dir-untrackable-gitignore-recurrence` →
`gitignore-verdict-evidence-untrackable-fourth-recurrence`, both the same `.gitignore`
catch-all shape, with three prior per-artifact whitelist lines already inline in the file as
evidence that the earlier fixes were symptom patches. It was diagnosed as exactly that and
closed **structurally** at `c7cc8d04` — the rule inverted for the whole release tree instead
of a fifth per-artifact line. That is the standing order's prescribed remedy, applied to the
one place this release earned it.

## The restated v0.4.3 git-identity question (R9)

**Restated for the operator, not decided here.** Should the git commit identity used in
this workspace be de-personalised going forward? Both v0.12.0 security reviews
dispositioned the existing identity as pre-existing published metadata (1,063 of 1,203
commits at that time) — not a leak, an operator policy call. v0.4.3 restated it in its own
closure rather than deciding it; v0.4.4 does the same. It remains open until the operator
rules.

## Archive decision

**MOVE** — `specs/releases/v0.4.4/` moves to `specs/_archive/releases/v0.4.4/` via
`git mv` (T-044-49, dispatcher-executed), and `ACTIVE.md` advances to `phase: ARCHIVED`
before being repointed at the next release or `release: none`.

**Standing note (CLOSURE-CHECKS §2):** capture the `SPEC-DOC-031` count **after** that
archive move, never before — this closure's own archived `## Dispositions` rows add one
WARN per non-terminal `ACTIVE` slug they name, and they name none, so the expected delta is
zero.
