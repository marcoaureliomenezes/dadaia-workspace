# T-050-32 — FR21 coverage table: `specs/constitution.md` references principles

**Author role:** product-engineer · **Task:** T-050-32 · **Release:** 0.5.0, segment `S4`
**Acceptance covered:** A21.1 (every surviving clause names a principle id or an ADR number —
**partially, by construction; see §4**), A21.2 (**this table** + **V15**), A21.3 (zero rule
text duplicated between `constitution.md` and the memory trio — §3's scan).

**Inputs:** SPEC FR21 + A21.1–A21.3, ruling D13, PLAN §"FR21 deletes the constitution's
restatements last"; the Part-1 principle inventories written at T-050-28
(`ARCHITECTURE.md` P-01…P-17, `QUALITY.md` P-18…P-27, `TECHSTACK.md` P-28, commit `b076b0f2`);
the 28 `proposed` ADRs at `specs/ADRs/0001…0028`; the pre-rewrite `specs/constitution.md`
at HEAD.

**Brought forward.** T-050-31 (the operator's ADR acceptance sitting) has **not** happened.
All 28 ADRs are `proposed`, so **every** reference written into the constitution carries
`(ADR 00NN proposed)` verbatim, and the file states once, in its "How to read a reference"
block, that the ids become final at T-050-31 and that a rejected ADR takes its principle —
and the constitution's reference to it — with it. No ADR was authored by this task.

**Line numbers** in the first column are the **pre-rewrite** file's, so a reviewer can diff
old → new clause by clause.

**Legend.** `REF` = the restatement is deleted and replaced by a principle reference ·
`POINT` = the restatement is deleted and replaced by a pointer to the law's one home (no
principle exists) · `KEEP+C` = the clause is genuinely constitutional, nothing else states it,
and it survives carrying a `C-NN` ADR-candidate marker · `DELETED` = removed outright, reason
stated · `C-NN` = a `proposed`-ADR **candidate** for the operator (§4) — **no ADR was authored
here**, per T-050-30's shape.

---

## 1. `specs/constitution.md` — 37 rows (K1…K37, every clause of the pre-rewrite file)

| # | Old clause (pre-rewrite line) | Disposition | New home / reason |
|---|---|---|---|
| K1 | Frontmatter (1–4) — `constitution_version: 4.1.0` | KEEP | Bumped to **5.0.0**: §15's own rule makes a changed or removed article MAJOR, and this rewrite changes every article. `specs_pattern_version` left at `5` — FR1's `dadaia specs upgrade` owns that re-stamp, not this task (residual R2) |
| K2 | Preamble (8–11) — "Each article is a binding, verifiable principle; mechanism and inventory live in the memory canon (§13) and are cited, never duplicated (§12.3)" | REF | Rewritten as the file's operating rule (8–12) plus a new **"How to read a reference"** block (14–21) that defines the `P-NN` ranges, the `(ADR NNNN proposed)` tag, the T-050-31 finalisation, and the `C-NN` candidate marker. This is the block A21.1 is read against |
| K3 | §0 (15–19) — identity, product statement, vision/architecture links | KEEP | Verbatim in meaning; the only place the product defines itself. Not a rule, so it carries no id |
| K4 | §0 (21–23) — Spec Context Project definition + "the bind → inject → enforce → parallel chain is the value spine" | POINT | Collapsed into the definitions table row → [[spec-context-project]]. The value-spine sentence is that atom's own opening claim — a second home here is slop (§12.3) |
| K5 | §0 (24–28) — Entry harness definition + "the roster is enumerated in exactly ONE memory atom — [[tech-stack]] §Agent runtimes — set-equal to `core/harness_registry.py`. This constitution never enumerates the roster" | KEEP+C (**C-01**), citation **repaired** | The roster law survives as the article's one **Law** line. Two stale citations fixed: the atom heading `§Agent runtimes` no longer exists (T-050-28 rewrote it into `Part 2 › Snapshot`), and `core/harness_registry.py` did not resolve from the repo root (SPEC-DOC-028) — now `dadaia_workspace/core/harness_registry.py`. Measured today by `dadaia specs doctor` SPEC-DOC-037 |
| K6 | §0 (29–31) — harness isolation, `--target <t>`, "scaffolding follows the choice" | POINT | Definitions table row → the `specs/memory/product/harness/` atoms. The install-flag mechanic is memory's, not law |
| K7 | §0 (32–36) — Agentic entity definition + registry path | POINT | Definitions table row → [[agentic-entities]] + `dadaia_workspace/public/entities/registry.json`; the derivation **law** that uses these terms stays at §12.5 |
| K8 | §0 (38–40) — "The SDD flow is agent-dispatched and document-governed: agents execute the phases of §7 against the SDD documents (SPEC/PLAN/TASKS/**ACTIVE.md**) … ships no agent-execution runtime" | **DELETED** (**STALE**) | Two facts, neither of which belongs here. `ACTIVE.md` was **retired at T-050-21A** — the clause was false on the day it was read. "Agent-dispatched, no execution runtime" already has two homes: `DADAIA.md` §1 (the flow) and [[architecture]] Part 2 › Overview ("The workspace ships no agent-execution runtime"). Deleted rather than re-pointed |
| K9 | §1 (44–47) — approved gate, reserved task, bypass language, the three canonical status tokens | KEEP+C (**C-02**) partial / POINT | The imperative survives in one sentence ("No production change lands without an approved release gate and a reserved task"). **The artifact list, the status-token vocabulary and the marker lifecycle are deleted** — `DADAIA.md` §6 (Task lifecycle) is their one home |
| K10 | §1 (49–56) — the operational-change lane + the memory-bearing test | KEEP+C (**C-03**) | Genuinely unique constitutional law; nothing else in the workspace states it. One stale phrase repaired: "with `ACTIVE.md` at `release: none`" → "the only sanctioned lane with no live release" (`ACTIVE.md` retired, T-050-21A) |
| K11 | §1 (58–65) — the bug-hotfix lane, the full register → root-cause → RED → fix → GREEN → `resolved` sequence, `dadaia bugs append`, the evidence triple | POINT + KEEP+C (**C-04**) | **The sequence is deleted**: `DADAIA.md` §1 Arm B and `dd-bug-resolution` are its two working homes and the constitution was a third. What survives is the two-sentence law nothing else carries — bugs never travel through a release, and **fix approval belongs to the operator and the consumer-side validator, never an internal gate** |
| K12 | §2 (69–72) — the private-material list ("no private project names, hostnames, IPs, credentials, personal paths or non-generic domain packs") | POINT | The enumeration is `DADAIA.md` §8's (public assets stay generic) and §9's (credentials). The constitution keeps the principle — an asset must be safe for **any** consumer — and stops carrying the list. **C-05** |
| K13 | §3 (76–79) — "committed product memory describing the CURRENT product — never a changelog (history belongs in release **`CLOSURE.md`** and `_archive/`). Memory source is Markdown with frontmatter; generated formats are never committed" | **DELETED** (**STALE**) + KEEP+C (**C-06**) | `CLOSURE.md` was **retired at T-050-21**; the current-truth posture is `DADAIA.md` §6 and the format rules are `specs/memory/AGENTS.md` › Atom Format. Only the sentence nothing else states survives: *a claim in memory the product does not honor is a defect of the same severity as failing code* |
| K14 | §4 (83–87) — runtime-parity law + "documented in [[architecture]] and the `memory/product/harness/` atoms" | KEEP+C (**C-07**) | Unique law, kept in two sentences; the pointer now names [[architecture]] **Part 2** (the two-tier split moved it) |
| K15 | §5 (91–93) — "never tracks generated runtime projections, harness artefacts, or tool caches. Temporary files belong under … `.dadaia/tmp/` … Repos never contain `.dadaia/` or cache/state dirs" | POINT | `DADAIA.md` §5 carries the exclusion list, the per-tool redirection recipes and the root whitelist. The constitution keeps the one-sentence law. **C-08**, measured today by `dadaia doctor`'s ROOT checks + `tests/contract/test_source_repo_hygiene.py` — a strong promotion candidate |
| K16 | §6 (97–101) — the whole layering paragraph: ring assignment, `core` imports nothing / no I/O, features import neither CLI nor infrastructure, ports + container injection, cross-feature composition through the container, "`container.py` is the sole composition root" | **REF** (the article's whole body) | Every clause is now a measured principle and the prose is deleted: **P-01, P-02, P-03, P-04, P-05, P-06, P-07, P-08, P-09, P-10, P-11, P-12** (ADRs 0001–0012, all `proposed`). The ring **description** is deleted too — [[architecture]] Part 2 › Overview is its one home. **The word "sole" is not carried forward**: T-050-28 row A5 already downgraded that claim to "the general composition root the CLI and the panel build through" because no check asserts singularity; restating "sole" here would re-introduce the unmeasured absolute memory just removed |
| K17 | §7 (105) — "Every action belongs to one of eight phases. This table is normative." | KEEP | The eight-phase enumeration survives as one line; it is the constitution's own vocabulary and is stated nowhere else |
| K18 | §7 (107–116) — the 8-row phase table (Owner · Writes to · Class · Concurrency) | **DELETED** | Three of its four columns are second homes: **Owner** = `DADAIA.md` §2, **Class** + **Writes to** = `DADAIA.md` §3's path-class table, **Concurrency** = `DADAIA.md` §3 + §8 here. Two cells were also **stale**: row 2's "`specs/bugs/**` (JSONL **events**)" (D11 retired the event stream — one record per bug) and row 8's "`specs/memory/**`, **CLOSURE, ACTIVE**" (both retired at T-050-21/21A) |
| K19 | §7 (118–120) — "MUTATING actors coordinate through task ownership … concurrent writes are surfaced through advisory presence" | **DELETED** | Verbatim duplicate of §8 (one article below) and of `DADAIA.md` §3 |
| K20 | §7 (120–123) — audit output is committed Markdown named `<ts>-<session_id_8chars>`; one audit → one remediation release; archives only when fully dispositioned | POINT (**C-09**) | Reduced to a pointer at `DADAIA.md` §6 (Audits). **The naming law is deleted**, deliberately: D5 moved audit folders to `<YYYYMMDD>-<slug>` while `doctor_closure_audit.py`'s SPEC-DOC-030 still enforces `<ts>-<sid8>`. The constitution asserting either would freeze a live contradiction into law — the drift is recorded as residual R4 instead. The one-release rule already has two homes (`DADAIA.md` §6, [[sdd-bug-backlog-governance]]) |
| K21 | §7 (111) — the phase vocabulary itself | **REF** (new) | The phases a release may *record* are now anchored on the measured envelope: **P-15** (ADR 0015 proposed, seven closed event kinds) and **P-14** (ADR 0014 proposed, the fold never writes) — so "what phase is this release in" has exactly one answer, and the constitution names the check that keeps it that way |
| K22 | §8 (127–139) — eight bullets: no lock/lease/steal · races surfaced · presence fail-open · ADDITIVE concurrency-independent · READ mode caller-local · pre-commit warns / pre-push may block · injection follows own bind · "Mechanism … `[[sdd-gate-v3]]`, `[[context-management]]`, `core/kernel_tunables.py`" | POINT | All eight are `DADAIA.md` §3's, restated. Collapsed to one law sentence — **the workspace never serializes its actors** — plus the pointer. `core/kernel_tunables.py` (an unresolvable SPEC-DOC-028 ref) and `[[context-management]]` dropped with the mechanism list they annotated. **C-10** |
| K23 | §9 (143–149) — PM coordinates the MUTATING span; PE/SE as sub-agents with caller-scoped binds; ai-engineer outside a release span; **Dispatcher purity** | REF + POINT | Dispatcher purity survives (unique law). The sub-agent/bind mechanics are `DADAIA.md` §2 and each persona's own frontmatter. The persona → law-section mapping is now measured: **P-17** (ADR 0017 proposed) |
| K24 | §10 (153–159) — PM curates; PE sanitizes stale items; picks the set; bug supersession; mandatory grill; PM does not unblock without `Aprovado` | POINT | Every clause is `DADAIA.md` §6 (Backlog, Releases) and `dd-release-definition`. The article is now a four-line pointer that adds nothing — kept only so the lane keeps a constitutional address (and so `§10` stays a valid citation). **C-11** |
| K25 | §11 (163–172) — checkpoint vs gate; "commits always flow"; the full review cadence (qa first, architect parallel, SE last, qa → commit, security → push, code-review → PR, memory after code review, REJECT re-opens `[-]` → `[ ]`) | KEEP + POINT | **The checkpoint-vs-gate distinction survives** — it is the constitution's own definition and nothing else states it. **The cadence is deleted**: `DADAIA.md` §7 and `dd-release-implement`'s `RC-FLOW.md` gate-cadence table are its two working homes |
| K26 | §11 (174–177) — the three channels with their paths + "The panel serves only channel 1" + "No `specs/releases/<id>/evidence/` subtree exists" | POINT + **DELETED** | The count law (**exactly three, no fourth**) survives; the three paths are deleted (`DADAIA.md` §5 + §6). The panel sentence moves to [[panel]]'s own truth. **The `evidence/` prohibition is deleted**: FR1's v6 canon root and `specs doctor`'s TREE checks are the structural authority for what a release folder may contain, so a hand-written negative here is a second, weaker home. **C-12** |
| K27 | §12.1 (181–182) — "No agent, skill, rule, or hook ships without a §7 phase it owns or gates" | **REF** | **P-17** (ADR 0017 proposed) — the behavior map's bijection is exactly this check: every asset maps to a law section and every section has at least one owner |
| K28 | §12.2 (183–184) — no store without a GC mechanism | KEEP+C (**C-13**) | Unique law, no check measures it today |
| K29 | §12.3 (185–188) — no fact in two sources / two channels; injected context carries no filler | KEEP+C (**C-14**) + REF | The law survives — it is the article FR21 itself executes. Its **parameter** case is measured: **P-26** (ADR 0026 proposed, one number per parameter). The general case is unmeasured (**C-14**) |
| K30 | §12.4 (189–191) — additive-only fixes carry a justification; reviewers reject additive-by-default | KEEP+C (**C-15**) | Unique law; the bug-surface axis every verdict must state is re-pointed to `DADAIA.md` §7 rather than restated |
| K31 | §12.5 (192–198) — the derivation law + "enforced by the derivation contract test and the `public doctor` `entities-derivation` check" + the operator-exemption | KEEP+C (**C-16**) | Unique law, kept nearly intact. The check is now named exactly (`tests/contract/test_agentic_entities_derivation.py`) instead of described — a Tier-B promotion candidate (T-050-28 row A22) |
| K32 | §13 (202–210) — the memory file list `specs/memory/architecture.md` · `quality-assurance.md` · `tech-stack.md`, the `product/**` catalog rule, `dadaia memory catalog generate`, vision at `product/philosophy/product-vision.md`, "snapshots, never changelogs; `Changelog`/`History`/`Histórico`/`Versions` forbidden", sole-author rule | POINT + **DELETED** (**STALE**) | **All three filenames were stale** — FR1 renamed them to `ARCHITECTURE.md` / `QUALITY.md` / `TECHSTACK.md`, so three SPEC-DOC-028 warnings were live in this file. The catalog rule, the regeneration verb, the atom format and the forbidden-section list are `specs/memory/AGENTS.md`'s, which *itself* points back here (line 23) for exactly one thing: **`product-engineer` is the sole memory author, in DEFINITION and CLOSURE**. That sentence — the "who" half no hook can verify — is all that survives. The two-tier shape and the Part-1 admission rule are **not** restated: they are that file's §"The Two Tiers" and the trio's own Part-1 preambles (A21.3) |
| K33 | §14 (214–233) — "Nine core agents" + the 9-row roster table (Agent · Phase · Class · Concurrency) + the persona/domain paragraph | **REF** + **DELETED** | The table is `DADAIA.md` §2's roster in another shape, and its `Phase` column re-encodes §7's table (deleted at K18). **The literal "Nine" is deleted** — a count that changes with the roster, in a document that must not drift; "the roster is **closed**" is the law and is what survives. Membership → `DADAIA.md` §2; every persona-to-section mapping → **P-17** (ADR 0017 proposed). The generic-agent rule and the operator-exemption survive; the "browser frontend, CI/CD → `software-engineer`" example is deleted (`DADAIA.md` §2 and the persona itself carry it) |
| K34 | §15 (237–241) — semver rule; "Amendment history lives in the amending releases' **CLOSURE files** and `_archive/`"; "The `specs doctor` invariants (including **SPEC-DOC-037**, the no-roster-enumeration guard)" | KEEP+C (**C-19**) + **STALE** repaired | The semver rule is unique law and survives. `CLOSURE.md` retired at T-050-21 → history now lives in "the amending release's `RELEASE.jsonl` notes and in `_archive/`". The SPEC-DOC-037 name-drop moves to where it belongs — beside the clause it measures (§0, **C-01**) — leaving §15 pointing at `dadaia specs doctor` as a whole. **New:** an amendment lands with the ADR that decided it (§13) |
| K35 | §16 (245–252) — every always-on rule is a `DADAIA.md` section; the relation declared in exactly one controlled source, **`public/entities/rules-skills-map.json` (schema `rules-skills-map-v1`)**, rows of `{topic, section, skills[], justification}`; "A deterministic test … gates every deploy" | **REF** + **STALE** repaired | `rules-skills-map.json` was **retired at T-050-19** and replaced by `dadaia_workspace/public/entities/behavior-map.json` — the constitution was naming a file that no longer exists. The row schema is deleted (the JSON schema is its own home). The whole article now resolves to **P-17** (ADR 0017 proposed), the bijection contract |
| K36 | §16 (254–259) — "Rule and skill divide, never overlap … Depth belongs to the skill, law belongs to the rule … One topic has one skill; two or more require a justification … A skill no topic claims is fused or retired by default" | **DELETED** | Authoring guidance, not law. Its working homes are `dd-ai-eng-knowhow`'s `AUTHORING.md` (writing-for-agents contract) and the behavior map's own schema (`justification` is a field there). The measurable half — one section per skill, one owner per section — is **P-17** |
| K37 | §16 (261) — "Provenance: v0.4.4 FR8, operator ruling 2026-08-23." | **DELETED** | History inline in a current-truth document — the same rule §3/§13 impose on memory, applied to the constitution. Provenance lives in `git log` and in the amending release's records (§15) |

---

## 2. V15 — the measured delta

| Measure | Before | After | Delta |
|---|---|---|---|
| `wc -l specs/constitution.md` | **261** | **207** | **−54** (−20.7 %) |

Command, for re-verification: `wc -l specs/constitution.md` (SPEC FR21's stated baseline is
**261**, and it matches HEAD). **The delta is negative — A21.2 satisfied.**

Composition of the −54: the deletions are concentrated in the two tables (§7's 8-row phase
table, §14's 9-row roster table = 20 lines), §8's eight bullets (13 lines), §6's layering prose
(7 lines → a reference block), §16's authoring paragraph (7 lines) and §1/§10/§11's procedural
restatements. The additions are the "How to read a reference" block (8 lines), §0's definitions
table (7 lines) and the per-reference `(ADR NNNN proposed)` tags — a cost this release
deliberately pays so the file is auditable **before** T-050-31 rather than after.

### Reference count

| | Count |
|---|---|
| Inline principle references written | **19** |
| Distinct principles cited | **16** — P-01…P-12, P-14, P-15, P-17, P-26 |
| Distinct ADRs cited (all `proposed`) | **16** — 0001–0012, 0014, 0015, 0017, 0026 |
| `DADAIA.md` section pointers | **19** (§1 ×1, §2 ×4, §3 ×3, §5 ×2, §6 ×5, §7 ×2, §8 ×1, §9 ×1) |
| Memory-atom pointers (wikilink or path) | **8** |
| `C-NN` candidates raised | **19** |

**Principles the constitution does not cite: 12** — P-13, P-16 and P-18…P-25, P-27, P-28.
This is expected, not a gap: P-18…P-28 are `QUALITY.md`/`TECHSTACK.md` principles and the
constitution carries **no quality article** (it never did). Recorded as observation O-1 in §5
so the operator can decide whether that is a hole worth filling — this task did not invent one.

---

## 3. A21.3 — the FR8/A8.1 duplicate scan, extended to the constitution

Method: every rule surviving in the rewritten `constitution.md` was reduced to its key phrase
and grepped, case-insensitively, across the memory trio
(`specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK}.md`).

Phrases scanned (19): `serializes` · `phase-less` · `GC mechanism` · `fact in two` ·
`Dispatcher purity` · `Derivation law` · `sole memory author` · `Exactly three` ·
`memory-bearing` · `Operational-change` · `roster is enumerated` · `safe for any consumer` ·
`severity as failing code` · `eight phases` · `checkpoint` · `reserved task` ·
`bypass language` · `nothing private` · `constitutional`.

Second pass (8): `never serializes` · `no plugin agent` · `generic implementations` ·
`project-domain knowledge` · `three sanctioned importers` · `remediation release` ·
`no fourth` · `APPROVE handoff`.

**Result: zero matches in the trio. A21.3 holds — no rule text is duplicated between
`constitution.md` and `ARCHITECTURE.md` / `QUALITY.md` / `TECHSTACK.md`.**

Three duplications the scan found **outside** the trio were fixed anyway, because §12.3 is
broader than A21.3's file set:

| Phrase | Second home found | Action |
|---|---|---|
| "only the operator creates demand" | `product/sdd/sdd-bug-backlog-governance.md:122` (+ `DADAIA.md` §6) | Deleted from §10 (row K24) |
| "one audit generates exactly one remediation release" | `product/sdd/sdd-bug-backlog-governance.md:250` (+ `DADAIA.md` §6) | Deleted from §7 (row K20) |
| "`features/` owns product behavior by domain" / ring assignment | `ARCHITECTURE.md:154–158` (Part 2 › Overview) | §6's ring description deleted (row K16) |

Four **stale citations** were repaired in passing — each was a live `specs doctor`
SPEC-DOC-028 warning or a reference to a retired artifact: `specs/memory/architecture.md`,
`specs/memory/quality-assurance.md`, `specs/memory/tech-stack.md` (renamed by FR1),
`public/entities/rules-skills-map.json` (retired T-050-19), `core/harness_registry.py` and
`core/kernel_tunables.py` (unresolvable from the repo root), `[[tech-stack]] §Agent runtimes`
(heading removed by T-050-28), plus `ACTIVE.md` ×2 and `CLOSURE.md` ×2 (retired at
T-050-21/21A).

---

## 4. A21.1 — the honest state, and the `C-NN` candidate list for the operator

**A21.1 reads:** *every surviving constitution clause names a principle id or an ADR number.*

**Where it holds:** every clause with a measured principle behind it now names that principle
**and** its ADR — §6 in full (12 principles), §7's phase-vocabulary anchor (P-14/P-15), §9,
§12.1, §12.3's parameter case, §14 and §16 (P-17, P-26).

**Where it cannot hold yet, and why this task did not force it.** Nineteen clauses are
genuine constitutional law that **no Part-1 principle measures**. FR21 offers two exits:
become a `proposed` ADR, or be deleted. This task's dispatch is explicit — *do **not** author
new ADRs here; list them in the coverage table for T-050-30's shape* — and T-050-30/31 is the
sitting where the operator rules. Deleting nineteen live laws to satisfy a syntactic criterion
would have destroyed law that nothing else states; writing nineteen ADRs would have fabricated
a decision the operator has not made. So each such clause survives carrying an explicit
**`C-NN`** marker, the convention is stated once at the top of the file, and the decision is
handed over intact.

**The candidate list.** Each row is a `proposed`-ADR candidate in T-050-30's shape (Title ·
Status · Date · Context · Decision · Consequences · **Confirmation**). The `Measured today by`
column is what makes a candidate promotable **now**: a candidate with a check already running
needs only an ADR and a Part-1 entry; a candidate with none needs a check written first, or
must be accepted as Part-2 description and dropped from the constitution.

| Id | Clause (article) | Measured today by | Promotable now? |
|---|---|---|---|
| **C-01** | The harness roster is enumerated in exactly one memory atom, set-equal to the registry module (§0) | `dadaia specs doctor` SPEC-DOC-037 (ERROR) + `dadaia_workspace/core/harness_registry.py` | **Yes** — strongest of the nineteen |
| **C-02** | No production change without an approved gate and a reserved task (§1) | nothing — the SDD gate reads no `TASKS.md` marker, by design | No — would need a new check (A18.3 forbids one this release) |
| **C-03** | The operational-change lane + the memory-bearing test (§1) | nothing — judgment at human PR review, stated as such | No |
| **C-04** | Fix approval belongs to the operator and the consumer-side validator (§1) | `tests/contract/test_consumer_validation_recipe.py` covers the recipe, not the approval | Partial |
| **C-05** | A public asset must be safe for any consumer (§2) | `dadaia public doctor` `public-privacy` + the pre-push denylist scan | **Yes** |
| **C-06** | A false memory claim is a defect of failing-code severity (§3) | nothing — pillar 3 of an audit measures it, and audits are suggested, not mandatory | No |
| **C-07** | No projection or doctor line claims enforcement a runtime does not perform (§4) | nothing mechanical; the harness atoms describe posture | No |
| **C-08** | The source repo never tracks what a runtime generates (§5) | `dadaia doctor` ROOT checks + `tests/contract/test_source_repo_hygiene.py` | **Yes** |
| **C-09** | One audit → one remediation release, every finding dispositioned before archive (§7) | `specs doctor` SPEC-DOC-031 covers the backlog half only | Partial |
| **C-10** | The workspace never serializes its actors (§8) | `tests/contract/test_push_gate_wiring.py` + the gate's own suite prove the absence of blocking, per surface | Partial — needs one assertion that *no* lock primitive exists |
| **C-11** | The backlog → release lane (§10) | `dadaia backlog doctor` BL-STALE + `specs doctor` SPEC-DOC-031 | Partial |
| **C-12** | Exactly three channels, no fourth, one path each (§11) | `dadaia reports validate` enforces shape per channel, not the count | No |
| **C-13** | No store without a GC mechanism (§12.2) | nothing — `PRESENCE-GC` and the session sweep exist per store, uncounted | No — the cleanest new-check candidate for a later release |
| **C-14** | No fact in two sources, no fact in two channels (§12.3) | `QUALITY.md` P-26 for the parameter case only | Partial — the general case is what this very table had to run by hand |
| **C-15** | An additive-only fix carries a justification (§12.4) | nothing — reviewer discipline (`DADAIA.md` §7) | No |
| **C-16** | The derivation law (§12.5) | `dadaia public doctor` `entities-derivation` + `tests/contract/test_agentic_entities_derivation.py` | **Yes** |
| **C-17** | `product-engineer` is the sole memory author, in DEFINITION and CLOSURE (§13) | the SDD gate enforces the **phase** half; the **who** half is unverifiable by any hook, and the constitution says so | Partial — the honest form is "phase measured, author disciplined" |
| **C-18** | The scaffolded roster is closed (§14) | `tests/contract/test_behavior_map.py` (P-17) proves every persona maps to a section; nothing proves closure | Partial |
| **C-19** | Constitution semver + amendment-with-ADR (§15) | nothing — `specs doctor` reads the stamp, not the bump | No |

**Five are promotable today with no new check** (C-01, C-05, C-08, C-16, and C-14's parameter
half, already P-26). Seven are partial. Seven need a check written, which A18.3 puts outside
this release.

**A20.3 mirror.** If the operator **rejects** an ADR at T-050-31, that principle leaves Part 1
and the constitution's reference to it must go with it — §6 loses that clause's id, §7/§9/§12/
§14/§16 lose theirs. The file's "How to read a reference" block states this consequence
explicitly so no reference is left pointing at a rejected decision.

---

## 5. Residuals — work this task cannot do (owner named)

`product-engineer` writes no production code, no tests and no backlog entry. Each row is
named for its owner; **no backlog entry was created** — these are listed for PM's
operator-facing intake report.

| # | What | Owner | Why |
|---|---|---|---|
| R1 | `specs/AGENTS.md` still lists `releases/ACTIVE.md` in its Load Order and its Artifact Authority table, still says the gate's "literal decision authority" is `ACTIVE.md`'s `phase:` line, and still records `memory/**` as writable "in `CLOSURE` only" | `ai-engineer` (source: `dadaia_workspace/public/templates/specs-AGENTS.md`) | `ACTIVE.md` was retired at T-050-21A, and §13 + `DADAIA.md` §6 both say **DEFINITION and CLOSURE**. The constitution is now correct and its scoped sibling contradicts it — the exact stale-citation class this release exists to remove |
| R2 | `specs_pattern_version` is still `5` in the constitution frontmatter; the canon is 6 | `software-engineer`, via `dadaia specs upgrade` (FR1) | The re-stamp is the migration verb's, not a hand edit. Until it runs, `specs doctor` emits the WARN-only `SPECS-VERSION` finding |
| R3 | Article numbering 0–16 was **deliberately preserved**, including the now-pointer-only §10 | — (recorded, no action) | `doctor_release.py` cites "constitution §7" in four operator-facing messages, `doctor_closure_audit.py` cites "§8", and `memory_lint.py`'s heading allowlist names §4/§7/§9/§11/§14. Renumbering would have created five stale citations in code while removing one from a document |
| R4 | Audit-folder naming is contradictory in the product itself: ruling D5 says `specs/audits/<YYYYMMDD>-<slug>/`, `doctor_closure_audit.py`'s SPEC-DOC-030 enforces `<YYYYMMDDTHHMMSSZ>-<session_id_8chars>` | `software-engineer` (code) after a PM/operator ruling on which wins | Row K20 deleted the naming law from the constitution rather than freeze either side. Until it is resolved, an audit folder written per D5 trips SPEC-DOC-030 |
| R5 | **A21.1 is not fully satisfiable before T-050-31**: 19 clauses carry `C-NN`, not an ADR number | operator, at the T-050-30/31 sitting | §4 is the decision packet. `qa-engineer` should record this at the S4 close (T-050-33) as a number, not an adjective: **19 candidates · 5 promotable with no new check · 7 partial · 7 needing a check A18.3 forbids this release** |
| R6 | Intake candidate (no backlog entry written — PM's intake report decides): extend the FR8/A8.1 duplicate scan from a hand-run grep to a check | PM → operator | §3's scan was executed by hand, phrase by phrase. C-14 (no fact in two sources) is the one anti-slop law with no mechanical detector, and this task is the evidence of that cost. Outside A18.3's letter for this release |
| O-1 | Observation, not a residual: the constitution cites **no** `QUALITY.md` or `TECHSTACK.md` principle except P-26 — it carries no quality article and never did | operator, if desired | P-18…P-25, P-27, P-28 (test tiers, ratchets, quarantine, marker set) are governed entirely by `QUALITY.md` Part 1 + `DADAIA.md` §7. Inventing a constitutional quality article was outside FR21's scope; flagged so the absence is a decision rather than an oversight |
