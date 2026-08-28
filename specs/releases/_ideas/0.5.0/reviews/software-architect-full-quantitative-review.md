# software-architect — full quantitative review of the 0.5.0 definition

**Reviewed at:** commit `10320654` (`SPEC.md` 2 213 lines · `PLAN.md` 301 · `TASKS.md` 1 744,
status `Em revisão`) against the live tree, the forensic (`bug-history-forensic-100.md`), the
metrics baseline (`architecture-metrics-baseline.md`, HEAD `974a045f`), the test literature
review, the two prior architect passes, handoff D1–D15 and the standing order. **Mode:** REVIEW,
third pass, quantitative. Every number below is *baseline → projected*, with the SPEC mechanism
that produces it (or `UNSPECIFIED` when the SPEC claims a direction but names no measurable
mechanism). Projections are derived from the SPEC's own deletion/addition lists and the
baseline's anchors; they are estimates to be replaced by V19 at closure, never acceptance
values.

## 0. architect-core-workflow

**Core problem.** 82/100 recent bugs re-bug their own surface within 14 days; 72 % of
resolutions cannot be tied to a diff; the fix *shape* does not predict the next bug, the
*surface* does (forensic §2). The release must make that loop measurable without growing the
surfaces that generate it. **Constraints.** D1–D15 ratified (no new CLI validation, no hook
block, one record per bug, operator-only ADRs); `product-engineer` has no shell; `v0.4.5` is
live. **Success criteria.** The eight forensic §5 metrics computable from `BUGS.jsonl` + git;
the three hot surfaces (public-assets 18, specs-doctor 13, spec-context 10 — 39/41 re-bugged)
not grown; every "one writer" claim true on the executed path. **Assumptions made explicit.**
(a) that the auditor and the fixer can reach the record-store seam — false at HEAD, see §6;
(b) that `specs upgrade` automation is safe — chain 1 of the forensic says otherwise.
**Prior art surveyed** (no web fetch needed — the literature file already grounds the test
axis in Beck/Google/Fowler/Khorikov/Rothermel): event-sourced vs document-per-record ledgers
(D11 chose document; correct — the fold was the amplifier), ADR canon (Nygard/MADR, D12),
JSONL compare-and-swap rewrite (A2.9 refuse-stale is the standard shape). Chosen direction:
the SPEC's, with the corrections in §9.

## 1. Clarity

| Measure | Before → after | Mechanism | Verdict |
|---|---|---|---|
| Undefined terms at first use (sample: header, §1–§3, FR1/FR2/FR14) | **8** codes used with no definition anywhere in the trio: `S-1…S-13`, `N-2`/`N-3`, `AR-1`, `CR-11`, `SA-11`, `BL-CONFLICT` (review-fold ids leaking into normative text); `puxadinho`/`histo`/`live photo`/`seam`/`FR23` resolved by the §1.5 pointer to PLAN §0 | CR-13 fold | 8 → 0 required; **WORSENS** vs a reader who never saw the reviews |
| FR ↔ task traceability gaps | **6**: A4.1 mapped to T-050-11 whose done criterion is "`ACTIVE.md` still present" (A4.1 needs it gone); A16.4 depends on FR18 (S4) but FR16 runs in S3 and no final-`rc` task re-runs pillar 3; T-050-03A has no FR/A-id; `core/models/backlog.py` + its container registration (A13.4 "three registrations") are in no task write set; `registration_commit` for post-0.5.0 records has no named writer (pillar 1 writes only `audited`/`resolved_commit`/`resolution_granularity`); `specs/bugs/README.md` deleted in T-050-10 (S1) while its replacement `specs/bugs/AGENTS.md` is authored in T-050-16 (S2) — a D-F violation | — | 6 → 0 required |
| SPEC/PLAN/TASKS contradictions | **5**: V9 "pre-push refuses only branch + denylist" vs A9.2 three refusals; T-050-26/27 "cite transcripts by `.dadaia/tmp` path — never paste" vs A13.5/V24 "command + redacted one-line result, a path is never the citation"; T-050-26 carries two `Preconditions` lines; FR14 window scans `_ideas/**/RELEASE.jsonl` while AS-7/D10 make `_ideas` SPEC-only; FR8 A8.3 names `dadaia bugs resolve`, a verb that does not exist (`cli/commands/bugs.py` has `append`/`status`/`stats`) | — | 5 → 0 required |

Clarity verdict: **WORSENS** for an external reader (review-id leakage), **IMPROVES** internally
(PLAN §0, §1.5). Net: REWORK on the 19 items above; all textual.

## 2. Cleanliness — layering and boundaries

| Metric | Before → after | Mechanism | Verdict |
|---|---|---|---|
| Cross-feature module edges | 5 → **5** | none. The 3 invisible edges exist because `setup.cfg` lists 20 of the 25 feature packages in the independence contract (`reconcile`, `capabilities`, `certification`, `tmp_gc`, `workspace_*` unlisted); A22.2 "no new accepted edge" does not add the missing modules | **UNCHANGED** — and FR18 will promote this contract to a Part-1 principle *as it stands*, i.e. a principle that is measurably false at birth |
| hooks → features edges | 4 → **4** | FR4 removes `_active_field` (a local read, not an import); `sdd_gate.py:30` keeps `gate_policy` + `session_identity`, `sdd_post_gate.py:39–40` keeps three, `ctx_inject.py:76` one. FR4 *adds* hooks → `core/release_events` (legal) | **UNCHANGED**; the baseline's "should reduce to 0" does not follow from the SPEC |
| `ignore_imports` | 15 → **14** | A2.5 retires `cli.commands.bugs -> infrastructure.jsonl_bug_store` (`setup.cfg:232`) when the store is container-injected; SPEC does not name it | **IMPROVES** if T-050-08 names the edge; else 15 |
| Modules mixed compute + write | 53 → **53 ± 1** | `features/bugs/service.py` stays mixed (resolver + `write_record` + archive); `migrate_v5.py` pure by design (+0); `core/release_events.py` — "fold" is a read, but T-050-28/33 append records: if the append lands in the same module, core gains a mixed writer | **UNSPECIFIED** — SPEC must state that `release_events.py` is read-only and name the append seam |
| "Two writers of one truth" (forensic P2: 14) | 14 → **12** collapsed by name: `bugs-append-accepts-second-terminal-event` + `…-without-reported` (CLI append vs doctor coherence → one store seam + WARN). Not touched: the 12 in public-assets/spec-context/panel (install vs init, prune ×2, doctor severity ×4, `DADAIA_ALLOWED_SUBDIRS` vs AGENTS table, gate by name vs origin, upgrade vs doctor refresh) | FR2 | **IMPROVES 14 → 12** on the ledger; **UNCHANGED** on the surfaces that produced 12 of 14 |
| New truths given one home | 0 → **5** structurally single-sourced: release phase (28 consumers → 1 fold), verdict roots (glob ×2 → canon), skill/AGENTS map (2 files → 1), backlog exits (in-file LEDGER + BL-DUP → histo), audit dir pattern (`AUDIT_DIR_NAME_RE` ×2 → 1) | FR4, FR1-2a, FR10, FR5, FR15 | **IMPROVES** |
| New truths given **two** writers (regression) | 0 → **2**: `BUGS.jsonl` governance fields (see §6) and `RELEASE.jsonl` (agents with file tools + T-050-11's writer) | FR2/FR14/FR4 | **WORSENS** unless §9 change 1 lands |

## 3. Bug surface

| Metric | Before → after | Mechanism | Verdict |
|---|---|---|---|
| Hand-kept truth constants (264) | 264 → **≈258** (−13 named, +7 implied). Deleted: `_OPTIONAL_STR_FIELDS` (`core/models/bugs.py:204`, still a mirror tuple at HEAD despite the SPEC's "derived" claim — FR2 must delete it, not re-mirror), `_active_field` regex ×2, `_BUG_LOG_RE`, `ROWS_PER_FILE`, `_RELEASE_KEYS` (`migrate/bugs_jsonl.py:48`), `RELEASE_ARTIFACTS`, `AUDIT_DIR_NAME_RE` ×1, `doctor_closure_audit.py` regexes ×2, `backlog/document.py` LEDGER regexes (≈3 of 7), `_FROZEN_PREFIX`. Added: canon-root tuple (TREE-8), release-dir member tuple, seven event kinds, status enum, two granularity enums, 90-day threshold, `_HEADING_GROUP_*` growth in `memory_lint.py` (Part 1/Part 2 headings are new headings against an 85-entry hand list — T-050-06 names `memory_lint.py` but not what happens to the list) | FR2/3/4/5/15 | **IMPROVES marginally (−2 %)**; `memory_lint` is a P1 engine the SPEC feeds instead of deriving |
| Doctor check codes | 47 → **≈45** (+TREE-8; −BL-DUP; −SPEC-DOC-006/007/030/034 if their `CLOSURE.md` checks die under A4.4; SPEC-DOC-036/038 kept but folded) | FR1/5/15 | **IMPROVES**; SPEC gives no count — must state the post-release code list (V19) |
| CLI leaf commands | 71 → **73** (`bugs archive` A2.8 is a new leaf; a governance-field writer — resolve/audited — needs a verb that does not exist, see §6). Offset available: `specs release`/`specs segment` (T-050-21A: they write `ACTIVE.md`) become dead once the phase is a fold → delete both → **71** | FR2/FR4 | **WORSENS to 73 as written; 71 reachable** |
| Hook hard-exit scripts | 2 → **1** | FR9 | **IMPROVES** |
| Regex-parsed-prose sites (release docs) | 22 (baseline §5) → **≈9** (`doctor_governance.py` 6 stay: SPEC-DOC-031/032/033/035 parse SPEC/BACKLOG prose; `memory_lint.py` 3 stay) | FR15/25A | **IMPROVES −59 %** |
| Schemas with `additionalProperties:false` hand-mirrored in Python | 1 (`bug-event-v1` ↔ `_OPTIONAL_STR_FIELDS`) → **0 claimed / 3 at risk** (`bug-record-v1`, `finding-record-v1`, `release-event-v1` each get a `core/models/*` dataclass; nothing in A2.6 forbids a field tuple in the model — the test proves scrub coverage, not absence of a mirror) | FR2/13/4 | **UNSPECIFIED** — add "zero module-level field tuples in `core/models/{bugs,findings,release_events}.py`" to A2.6 |
| **public-assets** (forensic #1: 18 bugs, 18 re-bugged; engines: `shipped-hashes.json`, doctor goldens, skill rosters, projection twice) | engines touched: **0 of 4**. Exposure: the release runs **9 projection cycles** (T-050-03A/16/17/18/19/20/21/21A/23/24) and renames a skill, adds a skill, adds 5 scoped `AGENTS.md` — every one a `test-public-pipeline-stale-skill-roster` / `install-target-doctor-goldens-stale` trigger. FR10 covers only the stale-citation pair (2/18) | FR10/12 | **WORSENS exposure, UNCHANGED engines.** Acceptable **only** if stated as out of scope in §4 with the forensic numbers, and if FR10's glob-discovery rule is extended to retire the hand rosters it already makes redundant (`EXPECTED_SKILLS`-style tuples in `tests/`) |
| **specs-doctor** (13; chain 1 = `specs upgrade` → 4 followers) | FR1 **grows** `specs upgrade` (automated renames, case-only two-step `git mv`) and `doctor` (TREE-8, `--recipe`) — the two functions already at CC 26/30. FR15/25A shrink the closure-audit half | FR1 vs FR15 | **MIXED; the growth is on the chain-1 engine.** Recommend `--recipe` only, no `upgrade` automation (§9 change 3) |
| **spec-context** (10) | `gate_policy.py` −1/+1 prefix; no classifier change | FR6 | **UNCHANGED** |
| Scanner-vs-prose (P3: 10 bugs) | committed prose the scanner polices **grows**: `reviews/` ×4 QA closes + 3 reviews, `specs/audits/**`, the migration report counts, 5 `AGENTS.md` | V22/V24 | **WORSENS** — the SPEC adds scans (correct) but no structural move (forensic metric 7 target 0) |

## 4. Complexity

| Metric | Before → after | Mechanism | Verdict |
|---|---|---|---|
| Production LOC | 30 167 → **≈30 450 (+1 %)**: FR1 +≈200 (TREE-8, recipe, upgrade, scaffold), FR2 +≈50 (store +150, rewrite +60, fold/state machine −160), FR3 +≈280 (deletable), FR4 +≈50, FR5 −≈60, FR9 −≈60, FR13 +≈80, FR15/25A −≈200, FR6/7/8/10/11/12/14/16–21 ≈0 | A22.3 admits net-positive | honest; **WORSENS +1 %** |
| Functions CC > 10 | 131 → **≈133** (`specs.doctor` and `specs.upgrade` grow; FR15 deletes none above 10) | none | **UNSPECIFIED** — A22.5 talks about ceilings, not counts |
| Ruff `max-complexity` | 63 → **63** — A22.5 "unchanged or lowered" with no task lowering it; observed max is 61, so the ceiling is already 2 above reality | none | **UNSPECIFIED** → ratchet to 61 in T-050-34 (zero code risk) |
| Code modules | 274 → **278** (+`migrate_v5`, `jsonl_record_store`, `release_events`, `models/findings`, 2 protocols; −`jsonl_bug_store`, `protocols/bug_store`) | PLAN §2 | +1.5 %, each new module single-purpose — acceptable |
| AI-surface files | skills 21 → 22; skill siblings +9 (`LINEAGE`, `RC-FLOW`, `RELEASE-EVENTS`, `MEMORY-UPDATE`, 4 pillars) −4 (`CLOSURE-*`, `RUBRIC`, `TOOLING`); scoped `AGENTS.md` 4 → 9 | FR7/12/14 | file count +10; V11 lines claimed negative — **UNSPECIFIED until V11** |

## 5. Governance cycle

| Metric | Before → after | Mechanism | Verdict |
|---|---|---|---|
| Steps per bug (register → resolved) | 7 (append · reproduce · RED · fix · GREEN · resolved append · commit) → **9** (+ isolated registration commit, + phase-0 lineage read of every same-surface prior diff in the window) | FR7/FR8 | **WORSENS +2 steps**, justified by the loop — but phase 0 is O(prior bugs in window) with no cap; at 3.2 bugs/day and a 5-release window that is 100–300 records per fix |
| Commits per bug | 1–2 (often 0 attributable) → exactly **2**, both attributable | FR8 | **IMPROVES** (forensic metric 1: 28 % → target 100 %) |
| Hook blocks a human can hit | 2 → **0** at commit, 3 refusals at push (branch, denylist, runner) | FR9 | **IMPROVES** |
| Tasks per release | 41 (`v0.4.5`) → **48**, all `Parallelism: none` | TASKS | **WORSENS +17 %**, zero parallelism declared |
| Operator-only gates per release | 2 (trio approval, publish) → **5** (+ FR6 deletion presence, FR20 ADR sitting, AS-12 ratification) plus one per future ADR | D12/D-H/AS-12 | **WORSENS** by ruling; state it |
| Always-on tokens | 21 511 → **≈22 000 (+2 %)**: D15 section ≈80, lineage ≈120, audits ≈100, memory/ADR ≈100, preflight ≈40, anchors ≈40, §3 row ≈0; −`ACTIVE.md` sentence ≈−15. `v0.4.5` FR11 diets the same file in the same month | FR11/V12 | **WORSENS**; V12 measures it, nothing bounds it — add a ceiling: FR11 delta ≤ the `v0.4.5` reduction |
| Map coverage | 21 skills + 4 `AGENTS.md`, 5 rows mapped (16 %) → **22 + 9 = 31 members, 100 % validated, RED in 5 directions** | FR10 | **IMPROVES** — the release's cleanest gain |

## 6. Spaghetti and side effects

| Metric | Before → after | Mechanism | Verdict |
|---|---|---|---|
| Side-effect call sites | 358 → **≈360** (+record rewrite 4, +release append 2, +`log_added_lines` 1, +migration report 3, +archive 2; −`jsonl_bug_store` 4, −`ci.py` gate 2, −`_active_field` 1, −closure parsers 3) | — | **UNCHANGED (±1 %)** |
| Write seams per artifact — **the central fidelity defect** | `BUGS.jsonl`: claimed **1** (store seam); actual **3** — `dadaia bugs append` (registration, exists), the fixer's `status: resolved` rewrite (no verb exists: `bugs.py` has `append`/`status`/`stats`; event kinds die with FR2, so `append --event resolved` dies too), the auditor's `audited`/`resolved_commit` rewrite (FR14 A14.5 "zero CLI verbs" + FR13 "writes with its file tools"). Two of three writers are file tools, so A2.6 (redaction), A2.9 (refuse-stale), A14.6 (one atomic rewrite) are **unprovable on the executed path** for them. `FINDINGS.jsonl`: A13.4's generic store instance has **zero callers** (the auditor and the remediation closure both write with file tools) — dead code behind a protocol, the FR15 shape in `infrastructure/`. `RELEASE.jsonl`: agents append with file tools (T-050-28/33/26/40) — 1 writer class, no seam, fine as long as the SPEC says so. ADRs: 1, file tools, fine | FR2/13/14 | **WORSENS as written**; architecture-fidelity gate FAIL |
| In-place rewrite race semantics | last-write-wins (append was `O_APPEND`, race-benign) → **refuse-stale + caller retries** (A2.9) — correct only for the CLI writer; a file-tool writer has no retry loop | FR2 | **IMPROVES for 1 of 3 writers** |
| `migrate_v5.py` deletability vs FR8 resolver | FR3 declares the module deletable after the release; FR8's resolver "derives (FR3's algorithm, scoped to one id)" from it. A3.10 says the derivation is a "pure core function" but T-050-09 places it in `features/bugs/migrate_v5.py` | FR3/FR8 | **fidelity FAIL**: put the pure derivation in `core/` (e.g. `core/bug_provenance.py`), keep only the v5 adapter + one-shot runner in `migrate_v5.py` |
| Hooks importing features | 4 edges (§2) | — | **UNCHANGED** |

## 7. Test economy

| Metric | Before → after | Mechanism | Verdict |
|---|---|---|---|
| Test functions | 1 859 → **≈1 910 (+3 %)**. Named deletions: event-fold tests (implicit in T-050-08), `test_rules_skills_map.py` (9 ported), 2 hook tests (verdict), 26 + 4 `ACTIVE`/`CLOSURE` files (rewrite-or-delete). Named additions: ≈70 (V20 7 arms, A1.x 8, A2.x 8, A3 6, A4 4, A5 4, A6 4, A9 4, A10 5 + 9, A13/14 4, A17–19 4) | PLAN §6 "net-additive by nature" | **WORSENS +3 %**; no deletion is counted, only "verdict per file" |
| Private-symbol imports (24 stmts / 21 files) | 24 → **24** | none | **UNSPECIFIED** (literature rule 1 not adopted) |
| Undeclared intent files (302 = SCAFFOLD by doctrine) | 302 → **302** (intent required for *new* tests only) | standing rule | **UNCHANGED** — the release's own doctrine says these expire; nothing lists them |
| LARGE cap 30 / ~84 / 100 contradiction | 3 numbers → **3** | none; FR18 will promote "the LARGE-test census ceiling" as a principle with three conflicting values | **UNCHANGED** — a Part-1 principle whose `Measured by:` cannot name one number |
| Mutation floor on `core/` | none → **none** | none | **UNSPECIFIED** |
| Exact-string assertions | 117 → **≥117** (A8.3 "CLI-output-stability fixtures green untouched" pins more strings) | — | **WORSENS** |

Literature rules (Part 3) — adopted / partial / missing: 1 missing · 2 missing · 3 **partial**
(new tests only) · 4 missing · 5 **partial** (zero new e2e; no census ratchet) · 6 missing ·
7 missing · 8 missing · 9 missing · 10 missing. **0 of 10 adopted, 2 partial.** A release that
promotes test laws to ADR-gated principles (FR18) without adopting a single measurable test rule
promotes the contradiction, not the law.

## 8. The loop itself — pillar 1 vs forensic §5

| # | Forensic metric | Baseline | Where in SPEC | Gap |
|---|---|---|---|---|
| 1 | Per-bug diff attributability | 28 % | A3.2/A3.3 marker distribution "measured, reported, not thresholded"; pillar 1 filters `exact` | no target; add "share of post-0.5.0 resolutions with `resolution_granularity == exact`" as a pillar-1 output with target 100 % |
| 2 | FR23 triple coverage (`evidence_loop`/`_seam`/`_diff`) | 25 % | **absent** — FR2's field list has `solution` and `cause` only; the v0.4.4 FR23 evidence gate's three fields are **dropped** from the record model | **regression**: the one structured evidence the ledger had is deleted; FR3's migration cannot carry it. Restore the three fields (write-once) |
| 3 | Fix-shape ratio (STRUCTURAL / additive) | 0.68 | absent (no `shape` token) | add an enum field `diff_direction: net-negative\|net-neutral\|net-positive` (the standing order already requires the value in prose) |
| 4 | Same-surface re-bug rate 3 d / 14 d on a canonical surface id | 55 % / 73 % | pillar 1 "recurrence (same component/surface)" — but `surface`/`component` stay free text (86 distinct strings per 100 bugs) | make `surface` a closed enum (the forensic's 18 buckets); without it the metric is the noise the forensic had to normalise by hand |
| 5 | Hand-kept-list touch count | 16/83 | absent | add to pillar 1 (`git show --name-only` over a fixed path set) |
| 6 | Test-layer bug share | 21/100 | absent | add (component prefix `tests/`) |
| 7 | Scanner-vs-prose recurrence | 10/100 | absent; the release grows scanned prose (§3) | add, target 0 |
| 8 | Sweep closures as `resolved` | 9/92 | absent; `superseded` status exists but no rule that a sweep is `superseded` | one sentence in FR2 + a pillar-1 count |

Pillar 1 as written measures 6 things the forensic did not ask for (interval, core-field
mutation, cache disagreement, commit shape, unrouted net-positive diffs, missing cause) and
**2 of the 8** it did, both partially. A16.2 will pass on the four pinned chains (they are
findable by `caused_by: text-reference` alone) while the loop's aggregate rate stays unmeasured.

## 9. Ten changes, ranked by bug-surface impact

1. **One writer seam for `BUGS.jsonl`, on the executed path.** Add exactly one governance verb
   `dadaia bugs update <id> --set <field>=<value>` (governance fields only, through the record
   store: redaction, refuse-stale, atomic) used by the fixer *and* the auditor; fold `archive`
   into it or keep it and delete `specs release`/`specs segment` so leaves stay 71. Rewrite
   FR13/FR14 "writes with file tools" to name the verb for ledger writes (folder writes stay
   file-tool). D8 forbids new *validation*; a writer is not validation. Without this the
   release adds two file-tool writers to the one artifact it exists to make trustworthy.
2. **Restore the FR23 triple** (`evidence_loop`, `evidence_seam`, `evidence_diff`) as write-once
   fields in `bug-record-v1`; migrate them from v5; make forensic metric 2 a pillar-1 output.
3. **Do not automate `specs upgrade` renames.** Ship `doctor --recipe` only; the case-only
   `git mv` is a copy-paste step. Chain 1 of the forensic (4 followers in 8 days) is
   `specs upgrade`; growing a CC-26 function on that surface is the puxadinho shape.
4. **Move the derivation to `core/`** (`core/bug_provenance.py`, pure, protocol-injected);
   `migrate_v5.py` keeps the v5 adapter + runner and stays deletable. FR8's resolver imports
   core, never a migration module.
5. **Canonical `surface` enum** (18 buckets) in `bug-record-v1`; `component` stays free text.
   Metric 4 becomes computable; phase 0's filter becomes exact instead of substring.
6. **Add the 6 missing forensic metrics to `PILLAR-BUGS.md`** with baselines and targets
   (§8), and add `diff_direction` as an enum field. This is the release's stated purpose.
7. **Name the public-assets exposure and cap it.** §4 states public-assets is untouched (18/18
   re-bugged); T-050-34 reports bugs registered on that surface during S1–S4; FR10's glob
   rule retires every hand roster it makes redundant (list them by file).
8. **Complete the independence contract** (add the 5 unlisted feature packages; adjudicate
   `reconcile`'s 3 edges as capped ignores or fix them) *before* FR18 promotes it to P-NN —
   a principle must be true when accepted.
9. **Test economy with numbers:** V19 gains tests before/after, private-symbol count 24 →
   ratchet, undeclared files 302 → list produced at closure with expiry, one number for the
   LARGE cap in `PARAMETERS.md` before FR18 cites it, ruff `max-complexity` 63 → 61.
10. **Textual closure of §1:** the 8 undefined review ids, the 6 traceability gaps, the 5
    contradictions; `_OPTIONAL_STR_FIELDS` deletion named in T-050-07; `release_events.py`
    declared read-only with the append seam named; V12 given a ceiling.

## 10. Gates and verdict

- **Root-cause gate: PASS** (carried from pass 2; nothing in the fold re-opened a symptom
  patch). One caution: FR1's `specs upgrade` growth is not a bug fix but sits on the surface
  whose last structural fix bred four bugs.
- **Architecture-fidelity gate: FAIL** on three misrepresentations: (i) `BUGS.jsonl` is
  described as one writer seam while the executed path has three writers, two without the
  seam (§6); (ii) FR3's derivation is called a core function but placed in a deletable feature
  module that FR8 depends on (§6); (iii) A13.4's findings store instance has no caller
  (§6). Plus one omission that makes a claimed invariant false at birth: the independence
  contract covers 20/25 packages (§2).
- **Bug-surface axis (FR24):** on the surfaces it touches — bugs ledger, release state, hooks,
  closure parsers, skill map — the definition **reduces** the surface (P2 −2 instances, prose
  regexes −59 %, hook blocks −2, one map, one fold). On the three surfaces that produced 41/100
  bugs it **does not reduce** (public-assets 0/4 engines, specs-doctor mixed, spec-context 0)
  and it **raises exposure** (9 projection cycles, more scanned prose, `specs upgrade` growth).
  Aggregate: **IMPROVES where it acts, UNCHANGED where the loop lives.**

**Verdict: REWORK.** Changes 1–4 are structural and must land before `Aprovado`; 5–9 are
one-paragraph additions each; 10 is textual. None re-opens a ruling. With 1–4 the fidelity gate
passes; with 5–6 the release measures the loop it names; without 7 the #1 surface stays a
blind spot the release itself exercises nine times.

## 11. "Fica mais limpa ou mais suja?"

Where the release acts, cleaner, and measurably so: two-writers-of-one-truth 14 → 12 on the
ledger and five new truths born single-sourced; release-prose regexes 22 → ≈9; hook hard-exit
scripts 2 → 1 and human-blocking hooks 2 → 0; hand-kept constants 264 → ≈258; `ignore_imports`
15 → 14; map coverage 16 % → 100 % validated; commits per bug attributable 28 % → 100 % going
forward. Where the loop actually lives it is unchanged or slightly dirtier: cross-feature edges
5 → 5, hooks → features 4 → 4, side-effect sites 358 → ≈360, production LOC +1 %, tests +3 %
with zero counted deletions, always-on tokens +2 %, CLI leaves 71 → 73 as written, and — the
one real regression — `BUGS.jsonl` goes from one append writer to three writers of which two
bypass every seam the SPEC promises, while the FR23 evidence triple is dropped from the record.
Public-assets, specs-doctor and spec-context (39 of 41 re-bugged) get 0, mixed and 0 structural
change, and the release exercises the first of them nine times. Net: the architecture does not
get dirtier if changes 1–4 land; it gets cleaner on ≈40 % of the bug-producing surface and
leaves ≈60 % as it is — which the SPEC should say out loud instead of letting "the loop made
visible" imply the loop made smaller.
