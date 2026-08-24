# Backlog — single source (ACTIVE + LEDGER)

Consolidated 2026-08-15 by `project-manager` (v0.12.0 FR7, task T-120-07) from the 31 live
per-entry files and `candidates.md` (both `git mv`-archived to `_archive/` at the v0.12.0
cutover, never deleted). Schema: `dd-backlog-definition` §2 — five required keys per
`ACTIVE` subsection plus the optional `Intents` key (OD-1); `LEDGER` grammar
`slug · DISPOSITION · release-or-reason · date`. Never-delete proven by count (ADR D4):
28 ACTIVE subsections + 54 LEDGER rows carry every pre-consolidation record — the
consolidation landed at 30 + 52 and v0.12.0's own closure sweep moved its two picked
entries across, the same 82 slugs; the set-equality evidence is captured under
`.dadaia/tmp/project-manager/20260815/`. Counts are as of the 2026-08-15 consolidation;
later curation (operator-adjudicated intake) appends entries and LEDGER lines on top,
never renumbering.
Entry numbering (`#N`) from the retired `candidates.md` index is carried in each Title —
rows are never renumbered, and LEDGER rows are never deleted.

**`## ACTIVE` is EMPTY (2026-08-17).** Release **v0.4.3 "claims-made-true / backlog-zero"**
picked the entire queue in one release under the operator's standing order ("fila inteira
em 1 release"). This is a deliberate, recorded state — not a lost document. The 24
consumed slugs receive their `LEDGER` lines at that release's closure disposition sweep;
the single rejected idea already carries its line below. New demand enters as it always
has: only the operator creates it, and `project-manager` curates it here.

**Pick-precedence notice (DADAIA.md §5).** At release-pick time, open bugs and
undispositioned audits outrank every fresh entry. **Currently outranking: nothing.**
Zero open bugs: the two LOWs that outranked the queue on 2026-08-16 —
`memory-token-estimate-normalizer-dead-code` and the orphan factory it surfaced,
`memory-catalog-regenerator-orphaned-factory` — were both closed by Arm B on `develop`
on 2026-08-17 (`specs/bugs/bugs.jsonl:889` and `:891`; commits `7971eefb`, `9a09b551`;
pure deletions, full gate green). Both 2026-07 audits remain archived and fully
dispositioned (v0.8.0). The ledger (`dadaia bugs status`) remains the source of truth.

**Purge-on-pick notice — release v0.4.3 "claims-made-true / backlog-zero" (2026-08-17).**
All **25** `ACTIVE` subsections left this document in the same commit that created
`specs/releases/v0.4.3/SPEC.md`, whose §7 is their provenance record: the 20 candidates
(`test-suite-remediation-stewardship` #2, `consumer-side-validation-round` #5,
`thin-wrapper-projected-scripts` #6, `bug-picked-ledger-event` #7,
`codex-persona-law-context-dehydration` #8, `python-env-interpreter-probe-hardening` #9,
`panel-runtime-reliability-dangling-ledger-pointer` #12,
`mutation-testing-tool-selection-and-wiring` #13,
`intent-docstring-mechanical-enforcement` #14, `gitflow-reconciliation-merge-mechanic` #15,
`memory-path-class-dotfiles` #16, `commit-paths-index-scope-hardening` #18,
`commit-message-scanning-residual` #21, `baseline-carve-out-review-cadence` #24,
`dd-skills-applyto-glob-collisions` #32,
`dd-release-definition-orchestration-pointer-loop` #33,
`bug-event-redaction-always-on-reinforcement` #34,
`dd-audit-project-pinned-tool-installs` #35, `dadaia-cli-skill-agent-grant` #36,
`codex-skill-ref-phantom-memory-ctx-prefix` #37) plus `dadaia-artifact-event-driven-gc`
and the four ideas (`bugs-jsonl-whole-blob-per-append`,
`repo-agents-md-symlink-hardening`, `stewardship-relocation-grep-homonym-note`,
`tests-agents-md-placeholder-doctor-warning`). Twenty-four are declared in that SPEC's
`**Consumes:**` line and receive `DELIVERED · v0.4.3` (or `SUPERSEDED · v0.4.3` for #37)
at the closure sweep. The twenty-fifth, `bugs-jsonl-whole-blob-per-append`, was
**REJECTED** by operator ruling and its `LEDGER` line is written below in this same
commit. Two external items ride the release without ever becoming entries (ADR #15): the
co-author-trailer carve-out gap (folded into #24) and the CHANGELOG-backfill intake
candidate. Nothing was deleted.

**Purge-on-pick notice — release v0.4.2 "residual-convergence" (2026-08-16).** Thirteen
ACTIVE subsections left this document in the same commit that created
`specs/releases/v0.4.2/SPEC.md`, whose §7 is their provenance record:
`backlog-grammar-single-writer-seam` (#38), `denylist-masking-predicate-parity` (#39),
`derived-values-computed-not-stored` (#43), `knowledge-duplication-doc-pass` (#44),
`flat-release-ship-task-evidence`, `intake-signal-calibration`,
`amnesty-multi-path-blob-fail-closed` (#40), `git-batch-epipe-swallow-width` (#41),
`self-scan-sentinel-archive-authored-blobs` (#45), `document-parser-fence-filter-complexity`
(#42), `retire-dead-hotfix-surface` (#4), `changelog-version-axis-reconciliation` (#11) and
`spec-doc-031-citation-classes` (#10). Their `LEDGER` lines were written by that release's
closure disposition sweep on 2026-08-16 (`DELIVERED · v0.4.2`, at the end of `## LEDGER`) —
nothing was deleted. `baseline-carve-out-review-cadence` (#24) was a **partial** pick: it
stayed ACTIVE, rewritten to its residual, and was picked **in full** by v0.4.3.

**Standing operator decision, RULED 2026-08-17 (was v0.8.0 CLOSURE return #3).** Is
`deferred` terminal for bug `panel-telemetry-sqlite-corrupts-under-concurrent-access`?
Ruled by the v0.4.3 dispatcher (operator-delegated, ADR R6): **no new disposition token**
— the dangling-pointer repair `panel-runtime-reliability-dangling-ledger-pointer` (#12)
implements within its own scope, using the existing vocabulary. The question no longer
surfaces at pick.

**Standing operator question, pending (PM decision record 3 — restated at intake #3,
operator adjudication 2026-08-16; carried again at the v0.4.3 pick as ADR R9).** Should
the git commit identity used in this workspace be de-personalised going forward? Both
v0.12.0 security reviews dispositioned the existing identity as pre-existing published
metadata (1,063 of 1,203 commits) — not a leak; it is an operator policy call and stands
open until ruled. v0.4.3 restates it in its CLOSURE rather than deciding it. The question
travelled to `specs/backlog/_archive/candidates.md` at the cutover; restated here so it
is no longer archive-only.

## ACTIVE

### dd-diagnose
- **Title:** dd-diagnose — model-invoked diagnosing-bugs method called by dd-bug-fix: loop red before any hypothesis, minimise, falsifiable hypotheses, instrument, regression test at the right seam, "no correct seam → architecture finding"
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Turn "root cause, always" (DADAIA.md §6) from a law into a **method with checkable "Done when" per phase**. A new core skill `dd-diagnose`, model-invoked and called by `dd-bug-fix` ("Call the Skill tool with \"dd-diagnose\""), carries the diagnosing-bugs phases: (1) a reproduction loop that is already red-capable and has actually been run red **before** any hypothesis is written; (2) minimise the failing input/path; (3) hypotheses stated so they can be falsified, one at a time; (4) instrument (logs/asserts/probes) rather than guess; (5) a regression test at the **correct seam** — the boundary the bug actually crossed, not the nearest convenient unit; (6) cleanup of instrumentation. **Key clause:** when no correct seam exists for the regression test, the fix does not proceed — the agent registers an architecture finding and the dispatcher routes `software-architect` before the fix. This is the audit's answer to the bug loop (464 registered bugs, 132/438 `resolved` events with empty evidence, re-bug within 72 h per surface): `dd-bug-fix` §3–§5 today states the outcome but not the procedure. Reference: `mattpocock/skills/skills/engineering/diagnosing-bugs/` (`SKILL.md` + `agents/` + `scripts/`). Scope boundary: this entry creates the skill and the operative pointer from `dd-bug-fix`; the three mandatory `--resolution-evidence` fields and the CLI refusal of empty `resolved` evidence are section A material folded into v0.4.4, not re-registered here. Governance: the new skill maps to the DADAIA.md §6 bold topic "Root cause, always" (one skill ↔ one topic). **Audit roadmap hint (not a disposition):** R1 — "anti-loop in Arm B". **Surface ownership (BL-CONFLICT adjudication 2026-08-23):** the edit of `dd-bug-fix`/`dd-bug-resolution` SKILL.md — including the operative pointer "Call the Skill tool with \"dd-diagnose\"" — is owned by `entity-behavior-map`; this entry creates only the new skill.
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement R1 (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-diagnose/SKILL.md
    surface: new
  change: "new model-invoked core skill, writing-for-agents pattern: six ordered phases (loop red → minimise → falsifiable hypotheses → instrument → regression test at the right seam → cleanup) each ending on a checkable Done-when; the no-correct-seam clause registers an architecture finding and yields to software-architect before any fix; adapted from mattpocock/skills/skills/engineering/diagnosing-bugs"
```

### dadaia-codebase-design
- **Title:** dadaia-codebase-design — model-invoked reference vocabulary (seam, deep module, deletion test, adapter, locality, replace-don't-layer) shared by engineer, architect, reviewer and QA; replaces architect-core-workflow
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Give every agent that touches code the **same design vocabulary** so reviews, fixes and architecture findings speak one language: *seam* (where a test or a replacement can be inserted without editing the module), *deep module* (small interface, large implementation), *deletion test* ("if this module vanished, what would break and would anyone notice?" — apply it to the module you are about to grow), *adapter* (translate at the boundary, never leak the foreign shape inward), *locality* (what changes together lives together), *replace-don't-layer* (a fix that wraps the old path instead of replacing it is a layer, and layers are how the bug loop grows). Delivered as a new model-invoked reference skill `dadaia-codebase-design` with disclosed companion files (deepening procedure; design-it-twice: sketch two shapes before committing to one). It **replaces** `architect-core-workflow` (retired): the old "WebSearch for existing solutions" step becomes "apply the deletion test to the module you are about to grow". Users: `software-engineer`, `software-architect`, `code-reviewer`, `qa-engineer` — each persona points to the skill instead of carrying its own partial vocabulary. Reference: `mattpocock/skills/skills/engineering/codebase-design/` (`SKILL.md` + `DEEPENING.md` + `DESIGN-IT-TWICE.md`). Governance: maps to the DADAIA.md §6 bold topic "Root cause, always" jointly with the quality bar, or to a §2 architecture row — the exact single topic is a grill-me question. **Audit roadmap hint (not a disposition):** R3 — "vocabulary and survey".
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement R3 (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dadaia-codebase-design/SKILL.md
    surface: new
  change: "new model-invoked reference skill: the shared vocabulary (seam, deep module, deletion test, adapter, locality, replace-don't-layer) in a short SKILL.md, with DEEPENING and DESIGN-IT-TWICE disclosed as sibling files; adapted from mattpocock/skills/skills/engineering/codebase-design"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/architect-core-workflow/SKILL.md
    surface: new
  change: "retire — delete the folder; software-architect, software-engineer, code-reviewer and qa-engineer personas point to dadaia-codebase-design; the WebSearch-for-existing-solutions step is replaced by the deletion test"
```

### dd-architecture-survey
- **Title:** dd-architecture-survey — user-invoked (PM/operator) or at alpha/release close: bug-ledger stats per surface + git churn in, ranked architecture cards + one top candidate out, then grill
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Operationalize the operator's standing order **"permanent architecture review oriented by bug history"** as a procedure with a defined input and output instead of an exhortation. New skill `dd-architecture-survey`, user-invoked (by the operator or `project-manager`; `disable-model-invocation: true`) or run at the close of each `alpha-N`/release. **Input:** `dadaia bugs stats` aggregated per surface/component (re-bug rate, time-to-re-bug, resolved-without-evidence count) joined with `git log` churn per path. **Output:** architecture cards — *files · problem · deepening (what deep module would absorb it) · before/after sketch · confidence tag Strong / Worth exploring / Speculative* — plus exactly **one top candidate**, which then goes to a `dadaia-grill-me` session before anything is picked. The survey writes a report/handoff only (ADDITIVE); it never edits code and never materializes backlog — its top candidate reaches `BACKLOG.md` only through the operator-gated intake (ADR #15). Reference: `mattpocock/skills/skills/engineering/improve-codebase-architecture/` (`SKILL.md` + `HTML-REPORT.md` + `agents/`). Depends on the vocabulary of `dadaia-codebase-design` (cards use seam/deep-module/deletion-test terms). Governance: maps to the DADAIA.md §5 bold topic "Releases" (close of each alpha) or §6 — single topic to settle in grill-me. Success metric proposed by the audit: every alpha closes with one survey and one dispositioned top candidate. **Audit roadmap hint (not a disposition):** R3. **Surface ownership (BL-CONFLICT adjudication 2026-08-23):** the segment-close step that names this survey as an operative dependency lands inside `entity-behavior-map`’s rebuild of `dd-release-implement` (its `RC-FLOW.md`); this entry creates only the new skill.
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement R3 (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-architecture-survey/SKILL.md
    surface: new
  change: "new user-invoked core skill (disable-model-invocation): input = dadaia bugs stats per surface + git churn; output = architecture cards (files · problem · deepening · before/after · Strong/Worth exploring/Speculative) and one top candidate routed to dadaia-grill-me; report/handoff only, never code or backlog writes; adapted from mattpocock/skills/skills/engineering/improve-codebase-architecture"
```

### dd-code-review
- **Title:** dd-code-review — three-axis review used by code-reviewer: Standards (+12 smells) × Spec × Bug-surface, each axis a subagent, findings merged without rerank
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Replace the reviewer's single monolithic pass with **three independent axes** run as separate subagents whose findings are reported side by side, **never reranked against each other**: (1) **Standards** — the codebase's own conventions plus the reference's fixed baseline of twelve Fowler smells (Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest — each a labelled judgement call, the repo's documented standard always overriding the baseline, anything tooling already enforces skipped); (2) **Spec** — does the diff do what the approved SPEC/TASKS say, nothing more, nothing less; (3) **Bug-surface** — the subagent receives the bug ledger of the feature touched (`dadaia bugs stats` filtered to its surface) and answers, with evidence, "did this diff reduce or increase the bug surface of this feature?" — the operator's rule "a diff that grows the feature is a stop" applied as a review axis. The skill is model-invoked, owned by `code-reviewer` (its six-axis review collapses onto these three; security/perf stay with `security-reviewer` and the gates); `qa-engineer` and `software-architect` verdicts reuse the bug-surface axis. Reference: `mattpocock/skills/skills/engineering/code-review/` (`SKILL.md` + `agents/`). Note: this workspace's sub-agents cannot dispatch further sub-agents — the "three subagents" run as three sequential passes or as PM-dispatched siblings; grill-me settles which. Governance: maps to the DADAIA.md §2 row "Six-axis review before a PR" (rewritten to name the three axes) — one skill, one topic. **Audit roadmap hint (not a disposition):** R1.
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement R1 (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-code-review/SKILL.md
    surface: new
  change: "new model-invoked core skill: three axes (Standards with the fixed 12-Fowler-smell baseline, repo standards overriding × Spec conformance × Bug-surface reduced-or-increased with ledger evidence), each an independent pass, findings reported side by side without rerank; adapted from mattpocock/skills/skills/engineering/code-review"
- subject:
    kind: doc
    ref: dadaia_workspace/public/agents/code-reviewer.md
    surface: new
  change: "persona invokes the skill — Call the Skill tool with \"dd-code-review\" — and drops its inline six-axis description; qa-engineer and software-architect verdicts cite the bug-surface axis"
```

### dadaia-glossary
- **Title:** dadaia-glossary — model-invoked domain glossary plus a CONTEXT.md per repo: sharpen terms inline, kill homonyms (scaffold / sentinel / quarantine / context / workflow), one-paragraph ADRs with the triple test
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** The audit found the same word carrying several meanings across skills, personas and code — *scaffold* (test tier vs spec scaffold), *sentinel* (ctx-inject file vs self-scan marker), *quarantine* (test mark vs bug state), *context* (spec context vs harness context window vs ctx-inject), *workflow* (retired engine vs GitHub Actions vs "the flow") — and the notes that patched them (`stewardship-relocation-grep-homonym-note`, `dadaia-test-stewardship` FR7) are symptoms. Remedy: a model-invoked skill `dadaia-glossary` whose job is to **sharpen inline** — when an agent writes or reads a term that has a glossary entry, it uses the canonical sense and names the other sense explicitly — backed by a **`CONTEXT.md` per repo** (the bounded-context file: ubiquitous language, each term with one definition and its non-meanings) and a **one-paragraph ADR format** with the triple test (what we decided · what we rejected · what would make us revisit). For this self-hosting repo, `CONTEXT.md` lives under `specs/memory/` (product-engineer-owned, DEFINITION/CLOSURE writable) or at the repo root — placement is a grill-me question, as is whether the glossary file is memory or a skill attachment. Reference: `mattpocock/skills/skills/engineering/domain-modeling/` (`SKILL.md` + `CONTEXT-FORMAT.md` + `ADR-FORMAT.md`). Governance: maps to the DADAIA.md §5 bold topic "Memory is current product truth" — one skill, one topic. **Audit roadmap hint (not a disposition):** R3.
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement R3 (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dadaia-glossary/SKILL.md
    surface: new
  change: "new model-invoked core skill: sharpen-inline procedure over a per-repo CONTEXT.md (one definition per term, explicit non-meanings) and a one-paragraph ADR format with the triple test (decided · rejected · revisit-when); CONTEXT-FORMAT and ADR-FORMAT disclosed as sibling files; adapted from mattpocock/skills/skills/engineering/domain-modeling"
- subject:
    kind: doc
    ref: specs/memory/CONTEXT.md
    surface: new
  change: "first CONTEXT.md for dadaia-workspace seeded with the five known homonyms (scaffold, sentinel, quarantine, context, workflow) resolved to one canonical sense each; the inline homonym notes in dadaia-test-stewardship and the stewardship-relocation note are replaced by pointers to it (placement root vs specs/memory settled in grill-me)"
```

### dadaia-router
- **Title:** dadaia-router — user-invoked entry point: one name to remember instead of nineteen; maps the main flow (Arm A), the on-ramps (Arm B, audit) and the standalone skills, and decides at phase boundaries
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** An operator (or a PM session) should need to remember **one** skill name. `dadaia-router` is user-invoked (`disable-model-invocation: true` — its description is not loaded into every agent's catalogue) and, given a plain-language demand, answers *where am I in the flow and which skill operates the next step*: the **main flow** — Arm A: `dd-backlog-definition → dd-release-definition → dd-release-implement (incl. closure) → dd-audit-project`; the **on-ramps** — Arm B: `dd-bug-registration → dd-bug-fix (→ dd-diagnose)`; audit: `dd-audit-project`; and the **standalone** skills (`dadaia-grill-me`, `dadaia-gitflow`, `dadaia-cli`, `dadaia-test-stewardship`, the AI-harness skill, `dd-architecture-survey`). It carries a disclosed `PHASE-BOUNDARIES.md`: the exact decision to make at each boundary (backlog→release: grill done?; definition→implementation: trio Aprovado + milestone (a) pushed?; alpha→rc: qa review committed?; ship→closure: trio APPROVE + memory→CLOSURE→archive order). The router replaces nothing and restates no law — it points, using the `rules-skills-governance-map` rows as its table, so it can never drift from DADAIA.md. Reference: `mattpocock/skills/skills/engineering/ask-matt/` (`SKILL.md` + `PHASE-BOUNDARIES.md`). Governance: maps to the DADAIA.md §1 bold topic "The flow — the mandatory default" — the one skill for that topic (the `dd-*` family maps to §1's stages individually; the router is the §1 index). **Audit roadmap hint (not a disposition):** R3.
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement R3 (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dadaia-router/SKILL.md
    surface: new
  change: "new user-invoked core skill (disable-model-invocation): demand → current arm/stage → next skill to call; main flow (Arm A), on-ramps (Arm B, audit), standalone list; table generated from / checked against the rules-skills-governance-map rows; PHASE-BOUNDARIES.md disclosed with the decision at each boundary; adapted from mattpocock/skills/skills/engineering/ask-matt"
- subject:
    kind: doc
    ref: dadaia_workspace/public/data/DADAIA.md#§9 Where to look next
    surface: new
  change: "skills row names dadaia-router as the single entry name for the flow; no other law text changes"
```

### dd-tasks-as-tracer-bullets
- **Title:** dd-tasks-as-tracer-bullets — TASKS authored as tracer bullets: each task declares "blocked by" and "what it delivers", demolitions use expand–contract; reference skill or a section of dd-release-definition
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** TASKS.md today lists tasks with a write set and acceptance; it does not force the author to state the **dependency edge** ("blocked by T-x") nor the **end-to-end slice delivered** ("after this task the operator can …"). The result is task groups that are internally consistent but cannot be verified as a vertical slice, and demolitions (deleting a subsystem — the dominant shape of this repo's releases: v0.3.0 engine, v0.5.0 marker subsystem, v0.4.4 skill consolidation) that land as a single big-bang commit. Remedy: author TASKS as **tracer bullets** — every task carries `blocked by:` (explicit, may be none) and `delivers:` (the observable slice), ordered so the first tasks cut a thin end-to-end path; demolitions follow **expand–contract** (add the new path, switch consumers, then contract by deleting the old path — three tasks, each independently green). Delivered either as a small reference skill `dd-tasks-as-tracer-bullets` invoked from `dd-release-definition`, or as a section of `dd-release-definition` itself — the audit leaves both open; grill-me decides (governance leans to a section: one skill ↔ one DADAIA.md topic, and "Task lifecycle" in §5 already has `dadaia-task-manager`). Reference: `mattpocock/skills/skills/engineering/to-tickets/` (`SKILL.md` + `agents/`). `specs doctor` may later lint the two keys (out of scope here). **Audit roadmap hint (not a disposition):** R3.
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement R3 (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-tasks-as-tracer-bullets/SKILL.md
    surface: new
  change: "new reference content (standalone skill or a section of dd-release-definition — settled in grill-me): every TASKS entry carries blocked-by and delivers keys, tasks ordered as tracer bullets (thin end-to-end slice first), demolitions decomposed expand → switch → contract; adapted from mattpocock/skills/skills/engineering/to-tickets"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-release-definition/SKILL.md
    surface: new
  change: "TASKS authoring step references the tracer-bullet rule (operative pointer or inline section) so product-engineer authors blocked-by/delivers on every task and expand–contract on every demolition"
```

### dadaia-wizard
- **Title:** dadaia-wizard — model-invoked: human-only runbooks (cutovers, secret rotation, OIDC role wiring) emitted as a guided, idempotent bash script instead of a numbered prose procedure
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Some steps are human-only by law (DADAIA.md §8 credentials; projected law files; GitHub branch-protection edits; cloud-side role cutovers) — today they are handed to the operator as 10–14 numbered prose steps in a report, which the operator re-reads, re-types and gets partly wrong. Remedy: a model-invoked skill `dadaia-wizard` that turns any human-only runbook into a **guided bash script** from a template: each step prints what it is about to do and why, asks for confirmation (or a value, never a secret echoed back), runs one idempotent command, verifies the post-condition, and stops loud on failure with the exact resume point. Scripts are written under `.dadaia/tmp/<agent>/<YYYYMMDD>/` (§4) and referenced from the handoff; secrets are read from the operator's root `.env` or prompted silently, never embedded (§8). Reference: `mattpocock/skills/skills/engineering/wizard/` (`SKILL.md` + `template.sh` + `agents/`). Governance: maps to the DADAIA.md §8 bold topic "Credentials" (the human-only lane) or §4 "Where things are written" — single topic settled in grill-me. **Audit roadmap hint (not a disposition):** unplaced in the audit's R1–R3 roadmap; picked on value when a human-only runbook is next produced.
- **Provenance:** operator ratification (2026-08-23) of the research report `.dadaia/reports/dadaia-workspace/claude-code/2026-08-23T183323Z-skills-audit-vs-reference/` (handoff `.dadaia/handoff/dadaia-workspace/2026-08-23T183323Z-claude-code-skills-audit-vs-reference.handoff.json`), section D "new skills proposed" — ruled to the backlog while sections A–C fold into release v0.4.4; relates-to `core-skills-consolidation` and `rules-skills-governance-map` (both CONSUMED by v0.4.4) and to the governance rule "every skill maps to one DADAIA.md bold topic"; roadmap placement: unplaced (hint)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dadaia-wizard/SKILL.md
    surface: new
  change: "new model-invoked core skill: human-only runbook → guided idempotent bash script from a disclosed template.sh (explain → confirm → run one command → verify → loud stop with resume point); written under .dadaia/tmp/<agent>/<date>/ and referenced from the handoff; secrets never embedded or echoed; adapted from mattpocock/skills/skills/engineering/wizard"
```


### cli-help-architecture-and-session-injection
- **Title:** cli-help-architecture-and-session-injection — help docker-style como fonte única da superfície da CLI + injeção do digest de help por hook em toda sessão (startup/resume/compact), aposentando a skill dadaia-cli
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** A skill `dadaia-cli` transcreve manualmente a superfície da CLI e está estruturalmente condenada a envelhecer — medição 2026-08-23 (CLI v0.4.3, 68 leaf commands reais): a skill cobre 36/68 verbos (53%), documenta 1 verbo fantasma (`specs hotfix` — hard-fail para quem segue o mapa), lista `specs release`/`specs segment` como leaves quando são grupos, omite 4 grupos inteiros (`repos`, `academy`, `memory`, `tmp`) e custa ~1.700 tokens por load; o problema é maior que ela — ~120 transcrições `dadaia <verbo>` espalhadas por 15 das 21 skills públicas (pior: `dadaia-workspace-manager`, 48 menções, incluindo invocação comprovadamente errada de `academy create`). Proposta do operador (modelo docker/cobra — help gerado da própria árvore de comandos, fonte única, nunca transcrito): (A) **help forte na CLI** — a árvore Typer já existe (23 apps) mas usa 0× `rich_help_panel`, 0× `epilog`, e 27/68 leaves têm docstring de uma linha; adotar agrupamento Common/Management no help raiz, `Examples:` via epilog nos leaves de alto tráfego, `rich_markup_mode` e `no_args_is_help` em todo grupo, e um guard de qualidade de help no CI; (B) **digest derivado, nunca escrito à mão** — novo verbo (ex. `dadaia help tree --digest`) que introspecta a árvore Click/Typer e emite um digest compacto (~root+groups; dump completo mede ~33.5k tokens — inviável; alvo do digest ≤4k) gravado version-stamped em `.dadaia/agentic/`; regenerado por install/reconcile/doctor — NUNCA no fire do hook (lei de latência: hook não importa o container); (C) **injeção por hook** — `ctx_inject` (autoridade única já provada, cross-harness, sentinel exactly-once, fail-open) passa a anexar o digest como payload bind-independent; Claude ganha os matchers SessionStart `startup|resume` que hoje só o Codex tem (Claude tem só `compact|clear`; sessão nova recebe zero até o 1º prompt); Kimi segue via UserPromptSubmit/marker de compact; Codex headless permanece AGENTS.md-only (fallback documentado); (D) **descomissionar** a skill `dadaia-cli` preservando o que o --help não deriva (semântica de bind/DADAIA_CONTEXT, sequência capabilities→reconcile→certify, "não há workflow engine", lei do venv) nos epilogs dos próprios comandos e/ou no DADAIA.md, e varrer as ~105 transcrições restantes das outras skills para "consulte `dadaia <grupo> --help`".
- **Provenance:** operator request 2026-08-23 ("skill constantemente desatualizada; estratégia de --help robusta tipo docker + hook que injeta o help na sessão nova e pós-compact") — pesquisa quantitativa desta data em `.dadaia/tmp` da sessão; números-chave conferidos ao vivo contra a CLI instalada
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/cli/main.py#app
  change: "docker-style help architecture - rich_help_panel grouping (Common vs Management) no help raiz, rich_markup_mode configurado, no_args_is_help em todos os grupos"
- subject:
    kind: cli
    ref: capabilities
  change: "novo verbo de dump derivado da arvore Typer/Click (ex. dadaia help tree --digest) emitindo digest compacto version-stamped em .dadaia/agentic/ (alvo <=4k tokens; capabilities --json hoje cobre so 14/68 leaves e nao substitui)"
- subject:
    kind: code
    ref: dadaia_workspace/hooks/ctx_inject.py#_emit_bootstrap
  change: "anexar o digest de help como payload bind-independent do bootstrap (rides _generic_preflight tambem em sessao sem bind); hook apenas LE o artefato pre-gerado, nunca gera"
- subject:
    kind: code
    ref: dadaia_workspace/hooks/ctx_inject.py#main
  change: "reinjetar o digest nos eventos SessionStart (startup, resume, compact, clear) com o mesmo sentinel exactly-once; fallback quando o digest esta ausente ou com stamp de versao divergente - instruir dadaia doctor"
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/runtime_config.py#_CLAUDE_MATCH_ALL
  change: "claude_settings ganha matchers SessionStart startup|resume (paridade com codex_hooks, que ja os tem); kimi mantem canal UserPromptSubmit/compact-marker"
- subject:
    kind: code
    ref: dadaia_workspace/features/capabilities/service.py#build_capabilities
  change: "regeneracao do digest acoplada a install/reconcile/doctor --fix quando distribution_version != stamp do digest"
- subject:
    kind: catalog
    ref: public-asset-distribution
  change: "aposentar a skill dadaia-cli (dadaia_workspace/public/skills/dadaia-cli/); idioms nao-derivaveis do help (bind/DADAIA_CONTEXT, capabilities->reconcile->certify, no-workflow-engine, lei do venv) migram para epilogs dos comandos e/ou DADAIA.md; varrer ~105 transcricoes de verbos nas outras 14 skills (pior ofensor dadaia-workspace-manager, 48 mencoes)"
- subject:
    kind: cli
    ref: ci preflight
  change: "guard de qualidade de help no preflight - falha quando um leaf command nasce sem docstring multi-linha/exemplo ou quando o digest esta stale vs a arvore de comandos (equivalente estrutural do lint de reachability que a skill carregava)"
```
### specs-canon-v6
- **Title:** specs-canon-v6 — canonical SDD specs pattern v6: per-area layout, event-sourced RELEASE.jsonl, live-photo BACKLOG.md, doctor "nothing beyond canon" + --recipe
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Reshape the canonical `specs/` pattern (specs_pattern_version 5 → 6) and make `dadaia specs doctor` measure it. **Canon root (context-relative, nothing else is conformant):** `backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, `constitution.md`, `AGENTS.md`. Per area: **backlog/** = `BACKLOG.md` (live photo — ACTIVE entries only; the in-file LEDGER section retires) + `AGENTS.md` + `_archive/backlog_histo.jsonl` (every exit appends `{ts, slug, disposition, reason, release?, by, entry_md}` with the full entry snapshot; disposition vocabulary unchanged; legacy `_archive/*.md` stay frozen, no retro-conversion); **bugs/** = `BUGS.jsonl` (rename of `bugs.jsonl`; event-sourced append-only kept, NO recurrence counter — reopen is a new `reported` with the same `bug_id`; `reported` requires `symptom`+`repro`+`severity`; `resolved` requires `release`+`cause`+`test`) + `AGENTS.md` + `_archive/bugs_histo.jsonl` (idempotent `dadaia bugs archive` moves event chains resolved >90 days; run at release close; doctor warns when overdue); **memory/** = `ARCHITECTURE.md`, `TECHSTACK.md`, `QUALITY.md` (renames of the lowercase trio), `AGENTS.md`, `product/` (+`catalog.json`, `index.md`; dotfiles tolerated; only rendered `*.html` gitignored — every spec is committed); **releases/** = `AGENTS.md` + at most ONE live `{version}/` (bare semver, no `v` prefix) holding `RELEASE.jsonl` + `SPEC.md` + `PLAN.md` + `TASKS.md`, plus `_ideas/{version}/` (N future releases allowed, `SPEC.md` Draft only; renumbered and promoted by `git mv` when the live release archives) and `_archive/{version}/` (future archives); **`ACTIVE.md` and `CLOSURE.md` retire** — `RELEASE.jsonl` is the event-sourced source (`release-event-v1`: `{ts, event, agent, session_id, data}` with kinds `created`, `spec_status` (Draft/Em revisão/Aprovado), `phase` (DEFINITION/IMPLEMENTATION/CLOSURE — the SDD gate folds the last `phase` for the MEMORY class), `rc_open`/`rc_close`, `review`, `push`/`pr`, `ship`, `archive`, `note`; individual commits stay out — git is that ledger); **audits/** = minimal structural now (`AGENTS.md`, one live audit at a time; redesign deferred to its own entry). `specs/assets/` retires — `memory/ARCHITECTURE.md` is the canonical home (fold what is still referenced, fix `memory/architecture.md`’s `../assets/` links). **Root `specs/_archive/` is deleted in the migration (operator ruling 2026-08-23: git history is the archive)** — destructive step, executed only with the operator present; FROZEN gate class repoints to per-area `*/_archive/`. `specs/backlog/remote-bugs/` dies (content adjudicated at intake). Doctor gains TREE-8 "nothing beyond canon" and `--recipe` (ordered concrete steps for whatever `specs upgrade` cannot do alone); `specs upgrade` automates the safe renames; compliance stays WARN-only — agent + user decide, never a block. Scaffold (`public/scaffold/`) reshaped to emit the v6 tree with scoped `AGENTS.md` (READMEs die). Migration of this repo’s own `specs/` included.
- **Provenance:** operator request (2026-08-23 dd-grill-me session, 2 rounds, 20 questions — handoff `.dadaia/handoff/dadaia-workspace/2026-08-23-claude-code-specs-canon-grill.handoff.json`); relates-to `gitflow-contract-v2-consolidation` (CONSUMED v0.4.4 — RELEASE.jsonl records the same push/pr/ship milestones that contract defines)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/doctor.py#SpecsDoctor
    surface: existing
  change: "pattern v6: TREE-8 nothing-beyond-canon check, per-area _archive, BUGS.jsonl/ARCHITECTURE.md/TECHSTACK.md/QUALITY.md names, bare-semver live release dir, RELEASE.jsonl presence, _ideas/ rules, --recipe output; WARN-only"
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/scaffolder.py#ScaffoldResult
    surface: existing
  change: "scaffold emits the v6 tree: scoped AGENTS.md per area (hash-projected), BUGS.jsonl, RELEASE.jsonl-ready releases/, _ideas/, no READMEs, no assets/, specs_pattern_version 6"
- subject:
    kind: code
    ref: dadaia_workspace/features/bugs/service.py#BugService
    surface: existing
  change: "BUGS.jsonl path; required fields (reported: symptom+repro+severity; resolved: release+cause+test); idempotent `dadaia bugs archive` (>90-day resolved chains to _archive/bugs_histo.jsonl); reopen = reported with same bug_id"
- subject:
    kind: code
    ref: dadaia_workspace/hooks/sdd_gate.py#evaluate_payload
    surface: existing
  change: "MEMORY phase resolution folds the last phase event from the live release RELEASE.jsonl (ACTIVE.md retired); FROZEN class repoints to per-area */_archive/"
- subject:
    kind: doc
    ref: specs/releases/RELEASE.jsonl
    surface: new
  change: "release-event-v1 schema: {ts,event,agent,session_id,data}; kinds created/spec_status/phase/rc_open/rc_close/review/push/pr/ship/archive/note; commits excluded"
- subject:
    kind: doc
    ref: specs/backlog/_archive/backlog_histo.jsonl
    surface: new
  change: "never-delete moves here: full-snapshot JSONL record per entry exit; BACKLOG.md becomes the live photo (ACTIVE only)"
```


### entity-behavior-map
- **Title:** entity-behavior-map — behavior manifest (DADAIA.md anchor ↔ skill ↔ scoped AGENTS.md) with hash-tuple contract tests, plus the skill surface that rides the v6 canon
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Make the rules→skills→scoped-AGENTS.md trios a **validated map instead of a convention**, so the three layers complement each other and never restate or contradict (the repetition/contradiction pattern the 2026-08-23 audit measured). (1) Manifest `dadaia_workspace/public/entities/behavior-map.json` with 5 rows: Backlog Definition → `dd-backlog-definition` → `backlog/AGENTS.md`; Bug Registration → `dd-bug-registration` → `bugs/AGENTS.md`; Bug Resolution → `dd-bug-resolution` → `bugs/AGENTS.md`; Release Definition → `dd-release-definition` → `releases/AGENTS.md`; Release Implement (includes memory update + closure) → `dd-release-implement` → `releases/AGENTS.md` + `memory/AGENTS.md`. Audit row deferred until audits are redesigned. (2) **Contract tests in the lib**: every member exists; each member carries the pointers to its row companions; a recorded hash tuple per row goes RED when any member changes without the tuple being re-recorded — forcing the joint review; the semantic equalization (scopes complement, nothing contradicts) is the `ai-engineer`’s act when re-recording the tuple, and any inconsistency found is asked, never silently patched. (3) `DADAIA.md` gains stable per-behavior anchors (named subsections) for the map to point at. (4) Skill surface riding the canon: rename `dd-bug-fix` → `dd-bug-resolution` (all references updated); `dd-release-implement` rebuilt in the robust skills-examples shape — short SKILL.md with per-step "Done when" + 3 disclosed siblings `RC-FLOW.md` (state ladder, absorbs CLOSURE-CHECKS.md), `RELEASE-EVENTS.md` (RELEASE.jsonl append recipes per milestone), `MEMORY-UPDATE.md` (memory protocol; no separate dd-memory-update skill — operator ruling Q11a); `CLOSURE-TEMPLATE.md` dies with CLOSURE.md; `dd-backlog-definition` rewritten for the live-photo BACKLOG.md + histo JSONL (its §2 "no JSONL for backlog" clause retires); `dd-bug-registration`/`dd-release-definition` updated to the v6 required fields and RELEASE.jsonl flow; the four scoped `AGENTS.md` authored short and direct, hash-projected under the TREE-5 regime. Depends-on `specs-canon-v6` (the layout the map validates). Relates-to ACTIVE `dd-diagnose` (touches the same `dd-bug-fix` file — the rename lands here, the method extraction lands there; whichever release picks second rebases on the first).
- **Provenance:** operator request (2026-08-23 dd-grill-me session, 2 rounds — same handoff as `specs-canon-v6`); depends-on `specs-canon-v6`
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/entities/behavior-map.json
    surface: new
  change: "behavior manifest: 5 rows of DADAIA.md-anchor/skill/scoped-AGENTS.md members with a recorded hash tuple per row"
- subject:
    kind: code
    ref: tests/contract/test_behavior_map.py#test_behavior_map_rows
    surface: new
  change: "contract tests: members exist, cross-pointers present, hash tuple matches — RED on any member change without joint re-record"
- subject:
    kind: doc
    ref: dadaia_workspace/public/data/DADAIA.md
    surface: new
  change: "stable per-behavior anchors (named subsections) for Backlog/Bugs/Releases/Memory behaviors; no content duplication with skills or scoped AGENTS.md"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-release-implement/SKILL.md
    surface: new
  change: "robust shape: short SKILL.md with Done-when steps + disclosed siblings RC-FLOW.md / RELEASE-EVENTS.md / MEMORY-UPDATE.md; CLOSURE-TEMPLATE.md and CLOSURE-CHECKS.md retire; RC-FLOW.md segment-close step names the survey as an operative dependency — Call the Skill tool with \"dd-architecture-survey\" [absorbed from dd-architecture-survey, adjudication 2026-08-23]"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-bug-fix/SKILL.md
    surface: new
  change: "renamed to dd-bug-resolution; all references updated; content aligned to BUGS.jsonl required fields; reproduce/RED/root-cause steps become an operative dependency — Call the Skill tool with \"dd-diagnose\" — the skill keeps only the bug lifecycle (branch, resolved event, commit) [absorbed from dd-diagnose, adjudication 2026-08-23]"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md
    surface: new
  change: "live-photo BACKLOG.md + backlog_histo.jsonl snapshot records; intake must confront existing ACTIVE (annulment only with operator ratification); LEDGER-in-file clause retires"
```


## LEDGER

- push-range-denylist-scan · DELIVERED · v0.9.0 · 2026-08-14
- redact-foreign-context-names-at-qa-authoring · DELIVERED · v0.9.0 · 2026-08-14
- tag-push-carve-out-reachability · DELIVERED · v0.9.0 · 2026-08-14
- 20260814-dd-lifecycle-skills-family · DELIVERED · v0.10.0 · 2026-08-15
- prior-published-term-amnesty · DELIVERED · v0.11.0 · 2026-08-15
- denylist-scan-skip-note-oversized-mislabel · DELIVERED · v0.11.0 · 2026-08-15
- registry-derived-foreign-name-set · DELIVERED · v0.11.0 · 2026-08-15
- refusal-path-redaction · DELIVERED · v0.11.0 · 2026-08-15
- push-ref-sha-validation-git-argv-hardening · DELIVERED · v0.11.0 · 2026-08-15
- git-objects-batch-parse-typed-error-boundary · DELIVERED · v0.11.0 · 2026-08-15
- git-objects-streamed-batch-reads · DELIVERED · v0.11.0 · 2026-08-15
- closure-v14-perf-figure-correction · DELIVERED · v0.11.0 · 2026-08-15
- self-scan-sentinel-integration-marker · DELIVERED · v0.11.0 · 2026-08-15
- backlog-tooling-reconciliation · DELIVERED · v0.12.0 · 2026-08-15
- backlog-md-physical-consolidation · DELIVERED · v0.12.0 · 2026-08-15
- loud-flake-stats-key-residual · DELIVERED · fixed before materialization · 2026-08-14
- frozen-wall-clock-baselines-in-repo-text · DELIVERED · baselines embedded in memory · 2026-08-14
- dispose-published-denylist-term · REJECTED · void by construction under the range-scoped scan · 2026-08-14
- 20260714-panel-games-pong-codex-v026 · REJECTED · surface removed in v0.3.0, nothing to validate · 2026-08-14
- 20260714-snake-wall-wrap-v025-pi-validation · REJECTED · same removal, nothing to validate · 2026-08-14
- intake-2-6-consumer-validation-recipe-glob · REJECTED · operator discard at intake (delegated) · 2026-08-15
- intake-2-8-spec-drafting-zero-hit-grep-lesson · REJECTED · operator discard at intake (delegated) · 2026-08-15
- 20260704-fast-tier-persona-validation · REJECTED · v0.1.64 · 2026-07-09
- 20260707-dispatch-band-legacy-fallback-removal · SUPERSEDED · deprecation-strips-and-doctor-cleanup (2026-07-10 consolidation) · 2026-07-10
- 20260707-platform-seam-todo-retirement · SUPERSEDED · lock-lease-session-identity-kernel (2026-07-10 consolidation) · 2026-07-10
- 20260707-specs-doctor-partial-archive-invariant · SUPERSEDED · deprecation-strips-and-doctor-cleanup (2026-07-10 consolidation) · 2026-07-10
- 20260708-panel-tab-reorg-agentic-layers · DELIVERED · v0.1.79 · 2026-07-11
- 20260709-central-bind-resolution-seam · DELIVERED · v0.1.77 · 2026-07-11
- 20260709-implement-review-write-scope-from-tasks-parity · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-preflight-block-reasons-missing-operator-command · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-tasks-write-scope-traversal-hardening · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-test-suite-remediation-waves · CONSUMED · v0.1.75 (PR #145) · 2026-07-10
- 20260710-deprecation-strips-and-doctor-cleanup · DELIVERED · v0.1.81 (date gate operator-waived 2026-07-11) · 2026-07-11
- 20260710-lifecycle-pipeline-correctness-and-diagnosability · DELIVERED · v0.1.78 · 2026-07-11
- 20260710-lock-lease-session-identity-kernel · DELIVERED · v0.1.76 (NO-LOCKS doctrine) · 2026-07-10
- 20260711-context-name-allowlist-at-resolution-rungs · DELIVERED · v0.1.80 · 2026-07-11
- 20260715-bugfix-workflow-tdd · REJECTED · v0.3.0 engine demolition — strict-TDD bug flow is law (constitution §1) · 2026-08-12
- 20260806-clean-architecture-remediation · CONSUMED · v0.5.0 · 2026-08-12
- 20260806-dadaia-md-workspace-system-prompt · CONSUMED · v0.5.0 · 2026-08-12
- 20260810-security-low-carryforwards-v030 · CONSUMED · v0.5.0 · 2026-08-12
- backlog-definition-workflow-dedup-conflict-control · DELIVERED · v0.1.26 · 2026-07-02
- codex-runtime-fidelity · DELIVERED · v0.1.13 (WS-CDX waves; protocol+hygiene verified at HEAD) · 2026-07-02
- gitflow-standardization · DELIVERED · v0.6.0 · 2026-08-12
- l1-agent-model-governance-panel · DELIVERED · v0.1.65 · 2026-07-08
- lifecycle-prompt-fragments-ai-surface-dehydration · DELIVERED · v0.1.30 (Waves A/E) · 2026-07-02
- selfrepo-agents-md-doubled-header · DELIVERED · v0.1.61 · 2026-07-07
- shared-headless-adapter-base · DELIVERED · v0.1.30 Wave A · 2026-07-02
- test-artifact-hygiene · CONSUMED · bug panel-e2e-artifacts-no-consumer (operator ruling 2026-08-12 — bad tests are bugs) · 2026-08-12
- test-runtime-efficiency · CONSUMED · bug test-suite-real-venv-and-ci-longpole (operator ruling 2026-08-12 — bad tests are bugs) · 2026-08-12
- test-stewardship-standardization · DELIVERED · v0.7.0 · 2026-08-12
- wire-consumed-ledger-producer-at-release-definition · DELIVERED · v0.1.27 · 2026-07-02
- workflow-model-governance-operator-profiles-and-context-overlays · DELIVERED · workflow-engine era, terminal frontmatter (engine removed v0.3.0) · 2026-07-02
- workflow-model-governance-panel-control-plane · DELIVERED · v0.1.28 · 2026-07-02
- workflow-step-handoff-data-plane-cleanup · DELIVERED · workflow-engine era, terminal frontmatter (engine removed v0.3.0) · 2026-07-02
- intake-3-2-match-throughput-fallback · REJECTED · v0.11.0 measured rejection ratified at intake #3 (fallback is the rare shape; a matcher-engine change is its own correctness surface; 55 s one-time scan inside tolerance) · 2026-08-16
- backlog-grammar-single-writer-seam · DELIVERED · v0.4.2 · 2026-08-16
- denylist-masking-predicate-parity · DELIVERED · v0.4.2 · 2026-08-16
- derived-values-computed-not-stored · DELIVERED · v0.4.2 · 2026-08-16
- knowledge-duplication-doc-pass · DELIVERED · v0.4.2 · 2026-08-16
- flat-release-ship-task-evidence · DELIVERED · v0.4.2 · 2026-08-16
- intake-signal-calibration · DELIVERED · v0.4.2 · 2026-08-16
- amnesty-multi-path-blob-fail-closed · DELIVERED · v0.4.2 · 2026-08-16
- git-batch-epipe-swallow-width · DELIVERED · v0.4.2 · 2026-08-16
- self-scan-sentinel-archive-authored-blobs · DELIVERED · v0.4.2 · 2026-08-16
- document-parser-fence-filter-complexity · DELIVERED · v0.4.2 · 2026-08-16
- retire-dead-hotfix-surface · DELIVERED · v0.4.2 · 2026-08-16
- changelog-version-axis-reconciliation · DELIVERED · v0.4.2 · 2026-08-16
- spec-doc-031-citation-classes · DELIVERED · v0.4.2 · 2026-08-16
- bugs-jsonl-whole-blob-per-append · REJECTED · v0.4.3 operator ruling (ADR R4) — complexity exceeds value: three divergent candidate shapes, four consumers (panel, doctor, pick precedence, closure sweep) and two laws (never-delete, ADDITIVE class) in the blast radius, while the content-resurfacing half is already neutralized by the shipped prior-published-term amnesty and the measured scan cost stayed inside tolerance; revisit only on a measured problem · 2026-08-17
- test-suite-remediation-stewardship · DELIVERED · v0.4.3 · 2026-08-18
- consumer-side-validation-round · DELIVERED · v0.4.3 · 2026-08-18
- thin-wrapper-projected-scripts · DELIVERED · v0.4.3 · 2026-08-18
- bug-picked-ledger-event · DELIVERED · v0.4.3 · 2026-08-18
- codex-persona-law-context-dehydration · DELIVERED · v0.4.3 · 2026-08-18
- python-env-interpreter-probe-hardening · DELIVERED · v0.4.3 · 2026-08-18
- panel-runtime-reliability-dangling-ledger-pointer · DELIVERED · v0.4.3 · 2026-08-18
- mutation-testing-tool-selection-and-wiring · DELIVERED · v0.4.3 · 2026-08-18
- intent-docstring-mechanical-enforcement · DELIVERED · v0.4.3 · 2026-08-18
- gitflow-reconciliation-merge-mechanic · DELIVERED · v0.4.3 · 2026-08-18
- memory-path-class-dotfiles · DELIVERED · v0.4.3 · 2026-08-18
- commit-paths-index-scope-hardening · DELIVERED · v0.4.3 · 2026-08-18
- commit-message-scanning-residual · DELIVERED · v0.4.3 · 2026-08-18
- baseline-carve-out-review-cadence · DELIVERED · v0.4.3 (picked in full; absorbed the co-author-trailer carve-out gap and the CR-6 Windows escape) · 2026-08-18
- dd-skills-applyto-glob-collisions · DELIVERED · v0.4.3 · 2026-08-18
- dd-release-definition-orchestration-pointer-loop · DELIVERED · v0.4.3 · 2026-08-18
- bug-event-redaction-always-on-reinforcement · DELIVERED · v0.4.3 · 2026-08-18
- dd-audit-project-pinned-tool-installs · DELIVERED · v0.4.3 · 2026-08-18
- dadaia-cli-skill-agent-grant · DELIVERED · v0.4.3 · 2026-08-18
- codex-skill-ref-phantom-memory-ctx-prefix · SUPERSEDED · v0.4.3 — merged into codex-persona-law-context-dehydration at pick and shipped inside FR22/A22.6; the prefix proved real (a documented Codex runtime adapter), bound to the on-disk inventory by test · 2026-08-18
- dadaia-artifact-event-driven-gc · DELIVERED · v0.4.3 · 2026-08-18
- repo-agents-md-symlink-hardening · DELIVERED · v0.4.3 · 2026-08-18
- stewardship-relocation-grep-homonym-note · DELIVERED · v0.4.3 · 2026-08-18
- tests-agents-md-placeholder-doctor-warning · DELIVERED · v0.4.3 · 2026-08-18
- spec-context-associated-repos · DELIVERED · v0.4.4 — FR15–FR19 shipped; closure sweep, specs/_archive/releases/v0.4.4/CLOSURE.md `## Dispositions` · 2026-08-24
- gitflow-contract-v2-consolidation · DELIVERED · v0.4.4 — FR1–FR6 shipped; closure sweep, specs/_archive/releases/v0.4.4/CLOSURE.md `## Dispositions` · 2026-08-24
- rules-skills-governance-map · DELIVERED · v0.4.4 — FR7–FR9 shipped; closure sweep, specs/_archive/releases/v0.4.4/CLOSURE.md `## Dispositions` · 2026-08-24
- core-skills-consolidation · DELIVERED · v0.4.4 — FR10–FR14 + FR24–FR31 shipped; closure sweep, specs/_archive/releases/v0.4.4/CLOSURE.md `## Dispositions` · 2026-08-24
