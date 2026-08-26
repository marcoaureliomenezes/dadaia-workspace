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

**Operator-approved intake materialization — v0.4.4 intake (2026-08-24).** The v0.4.4
intake report (handoff
`.dadaia/handoff/dadaia-workspace/2026-08-24T172302Z-project-manager-v044-intake-report.handoff.json`)
was adjudicated by the operator on 2026-08-24: **all 15 candidates approved** ("De
preferência todos — veja, classifique, mapeie"). They enter `ACTIVE` below, themed:
**A** structural-consolidation (4), **B** security-gate-hardening (4 as entries),
**C** token-economy / AI-surface (6), **E** operator-ruling (1). Item **B1 is deliberately
NOT an entry** — it is a time-boxed, operator-only GitHub-settings action (the intake
itself marks it "not backlog material in the ordinary sense"): add the context
"Security verdict gate (PR head sha)" to required checks on **both** the `develop` and
`main` PR edges, **due before the rc-2 PR**; recorded here so it is scheduled, not lost.
Rulings recorded with the intake: **R1** — v0.4.5 direction is hardening & consolidação
(bugs sweep + themes A/B + the token-economy program); **R2** — the nine-skill study
dispositions are RATIFIED (Update×5, Merge×3, Fuse×1, zero Retire; the 2 CLI-help merges
adjudicated jointly with `cli-help-architecture-and-session-injection`); **R3** —
`.dadaia/references/` is the sanctioned home for operator-placed reference material
(entry `dadaia-references-doctor-sanction`). Nothing was picked in this commit — picking
happens at release definition.

**Pick-precedence update (2026-08-24) — supersedes the 2026-08-17 notice above.**
"Currently outranking" is no longer "nothing": **7 open bugs** (zero HIGH/CRITICAL, per
`dadaia bugs status` at intake compile time) outrank every fresh entry at pick time
(DADAIA.md §6). Lead order: the two MEDIUM AGENTS.md-vs-gate bugs
(`sdd-gate-blocks-fresh-repo-root-agents-md` + `repo-agents-md-law-gate-contradicts-template`
— one structural root-cause investigation, not two patches, per the standing
architecture-review order) and the MEDIUM
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` (bundle with entry
`bug-event-control-character-sanitation`). The LOW
`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` is superseded-in-spirit
by entry `atomic-write-primitive-consolidation` — formalize with a `superseded` event when
that entry is picked. The ledger remains the source of truth.

**Purge-on-pick notice — release v0.4.5 "hardening and consolidation" (2026-08-24).**
**Fourteen** `ACTIVE` subsections left this document in the same commit that created
`specs/releases/v0.4.5/SPEC.md`, whose §7 is their provenance record: the four theme-**A**
entries (`atomic-write-primitive-consolidation`,
`byte-golden-test-inventory-roster-split`, `coupled-inventory-shared-oracle`,
`scan-test-vacuity-guard`), the four theme-**B** entries
(`doctor-slug-ownership-uniqueness`, `bug-append-write-time-denylist-redaction`,
`specs-init-symlinked-target-refusal`, `bug-event-control-character-sanitation`), five of
the six theme-**C** entries (`always-on-token-diet`, `memory-catalog-digest-trimming`,
`persona-line-ceiling-trim`, `ai-surface-hygiene-residuals`,
`intent-taxonomy-vocabulary-ruling`) and the theme-**E** entry
(`dadaia-references-doctor-sanction`). All fourteen are declared in that SPEC's
`**Consumes:**` line and each receives a `CONSUMED · v0.4.5` `LEDGER` line **in this same
commit**, to be **updated in place** to its terminal token (`DELIVERED`/`SUPERSEDED`/
`DEFERRED`) at the closure disposition sweep — never a second line (BL-DUP). Nothing was
deleted. **Twelve entries stay `ACTIVE` by operator ruling O1 (2026-08-24):**
`nine-skill-study-execution` (its dispositions ratified as provenance, execution deferred),
`cli-help-architecture-and-session-injection`, `specs-canon-v6`, `entity-behavior-map`, and
the eight skills proposed by the 2026-08-23 skills audit. One item rides the release without
ever becoming an entry: the operator-only GitHub-settings action B1 (the verdict-gate
required check on both PR edges), scheduled as a v0.4.5 task, due before the `rc-2` PR.

**Bug pick — release v0.4.5 (2026-08-24).** All **8** open bugs were picked; the ledger
(`dadaia bugs status`) remains the source of truth for their state.
`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` carries a `superseded`
event appended in the definition commit, naming `atomic-write-primitive-consolidation`.
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` is bundled into the
same fix as `bug-event-control-character-sanitation`. The two MEDIUM AGENTS.md-vs-gate bugs
are one structural investigation, not two patches, per the standing architecture-review
order. `windows-xdist-workers-crash-on-unit-fast-tier` may end the release **still open** —
its SPEC assumption AS-5 states that a quarantine is never a resolution.

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
- **Title:** specs-canon-v6 — canonical SDD specs pattern v6: per-area layout, RELEASE.jsonl with milestone shas, BUGS.jsonl record model, `ADRs/`, live-photo BACKLOG.md, doctor "nothing beyond canon" + --recipe
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Reshape the canonical `specs/` pattern (specs_pattern_version 5 → 6) and make `dadaia specs doctor` measure it. **Amended 2026-08-26 — grill handoff `2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill` (rulings D3, D11, D12; the prior 2026-08-23 wording is kept below and re-worded only where a ruling reversed it — nothing deleted silently).** **Canon root (context-relative, nothing else is conformant):** `backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, `ADRs/` (added 2026-08-26, D12 — layout owned by `memory-two-tier-principles`), `constitution.md`, `AGENTS.md`. Per area: **backlog/** = `BACKLOG.md` (live photo — ACTIVE entries only; the in-file LEDGER section retires) + `AGENTS.md` + `_archive/backlog_histo.jsonl` (every exit appends `{ts, slug, disposition, reason, release?, by, entry_md}` with the full entry snapshot; disposition vocabulary unchanged; legacy `_archive/*.md` stay frozen, no retro-conversion); **bugs/** = `BUGS.jsonl` (rename of `bugs.jsonl`) + `AGENTS.md` + `_archive/bugs_histo.jsonl`. *2026-08-23 wording, reversed by D11:* "event-sourced append-only kept … reopen is a new `reported` with the same `bug_id`; `reported` requires …; `resolved` requires …". *Re-worded 2026-08-26 (D11 — the record model):* `BUGS.jsonl` holds **ONE record per bug, appended once** — not an event stream, no fold; the record's **core fields are immutable** (`id`, `ts`, `reported_by`, `title`, `severity`, `surface`, `component`, `context`, `symptom`, `repro`, `expected`, and `root_cause`/`solution` once set) and its **governance fields are mutable** (`status`, `cause`, `caused_by`, `resolved_commit`, `resolved_release`, `audited`) — a governance-field update rewrites that record's line in place (JSONL is a document keyed by `id`, the line is the unit; git history is the change log). A reopen is a **new record** with a new `id` that declares `caused_by: <prior-id>` (no recurrence counter, no second `reported` for the same id). Required at registration: `symptom` + `repro` + `severity` + `expected`; required to reach `status: resolved`: `cause` + `resolved_release` (+ the regression-test seam in `solution`) — the full field contract, `caused_by` procedure and examples are owned by `bug-lineage-and-commit-discipline`; this entry owns only the path (`BUGS.jsonl`), the per-area `_archive/` and the doctor/scaffold surface. `_archive/bugs_histo.jsonl`: `dadaia bugs archive` (idempotent, run at release close, doctor warns when overdue) **moves whole records** whose `status` is terminal for >90 days — one line out of `BUGS.jsonl`, the same line into `bugs_histo.jsonl` (a record move, never an event-chain fold; the prior "moves event chains" wording is retired). Example of the record model:
```json
{"id":"panel-report-index-double-slash-047","ts":"2026-08-26T09:14:02Z","reported_by":"qa-engineer","title":"panel report index renders double slash","severity":"LOW","surface":"dadaia panel","component":"features/panel","context":"dadaia-workspace","symptom":"Reports tab hrefs contain '//'","repro":"1. dadaia panel 2. open Reports tab 3. inspect any href","expected":"single-slash hrefs","status":"open","cause":null,"caused_by":null,"resolved_commit":null,"resolved_release":null,"audited":null}
```
After the fix the SAME line reads (only governance fields changed; every field above `status` is byte-identical): `…"status":"resolved","cause":"os.path.join on a URL segment","caused_by":"none","resolved_commit":"a1b2c3d","resolved_release":"0.4.5","audited":null…`. **memory/** = `ARCHITECTURE.md`, `TECHSTACK.md`, `QUALITY.md` (renames of the lowercase trio), `AGENTS.md`, `product/` (+`catalog.json`, `index.md`; dotfiles tolerated; only rendered `*.html` gitignored — every spec is committed; the Part 1 Principles / Part 2 Implementation split inside the trio is owned by `memory-two-tier-principles`); **releases/** = `AGENTS.md` + at most ONE live `{version}/` (bare semver, no `v` prefix) holding `RELEASE.jsonl` + `SPEC.md` + `PLAN.md` + `TASKS.md`, plus `_ideas/{version}/` (N future releases allowed, `SPEC.md` Draft only; renumbered and promoted by `git mv` when the live release archives) and `_archive/{version}/` (future archives); **`ACTIVE.md` and `CLOSURE.md` retire** — `RELEASE.jsonl` is the source (`release-event-v1`: `{ts, event, agent, session_id, data}` with kinds `created`, `spec_status` (Draft/Em revisão/Aprovado), `phase` (DEFINITION/IMPLEMENTATION/CLOSURE — the SDD gate folds the last `phase` for the MEMORY class), `rc_open`/`rc_close`, `review`, `push`/`pr`, `ship`, `archive`, `note`, and — added 2026-08-26 — `audited`). *2026-08-23 wording, reversed by D3:* "individual commits stay out — git is that ledger". *Re-worded 2026-08-26 (D3):* individual commits stay out, **but milestone records carry `sha` (+ `pr`) as immutable facts** at exactly three milestones — `defined` (SPEC/PLAN/TASKS `Aprovado`; sha of the definition commit, `pr` of the definition PR to `develop`), `implemented` (final `rc` QA close; sha of the last rc commit), `shipped` (merge to `main`; merge sha + the `develop`→`main` `pr`) — plus `audited` (sha the audit ran at + the audit folder) whenever an audit runs, so rollback and audit windows are sha ranges read straight from the file. Milestone examples (one line each, immutable once written):
```json
{"ts":"2026-08-28T14:02:11Z","event":"defined","agent":"product-engineer","session_id":"s-9f1c","data":{"sha":"4e5f6a7","pr":210}}
{"ts":"2026-09-03T18:40:05Z","event":"implemented","agent":"qa-engineer","session_id":"s-77ab","data":{"sha":"b8c9d0e","rc":2}}
{"ts":"2026-09-04T10:15:00Z","event":"shipped","agent":"project-manager","session_id":"s-77ab","data":{"sha":"f1a2b3c","pr":214,"tag":"0.4.5"}}
{"ts":"2026-10-20T09:00:00Z","event":"audited","agent":"project-auditor","session_id":"s-3d4e","data":{"sha":"c0ffee1","audit":"audits/20261020-five-release-window"}}
```
(`defined`/`implemented`/`shipped`/`audited` are the milestone kinds; `push`/`pr`/`ship` from the 2026-08-23 list remain valid as the finer-grained events between them — `shipped` is the sha-bearing form of `ship`.) **audits/** — *2026-08-23 wording:* "minimal structural now (`AGENTS.md`, one live audit at a time; redesign deferred to its own entry)". *Re-worded 2026-08-26 (D5):* `audits/` = `AGENTS.md` + one folder per audit `<YYYYMMDD>-<slug>/` holding `AUDIT.md` + `FINDINGS.jsonl` (record model as D11; committed, inside specs, never HTML outside), `_archive/` for fully-dispositioned audits; `README.md` retires into `AGENTS.md`. The folder content, the FINDINGS record and the pillar procedures are owned by `audit-canon-v1` — this entry emits the folder + `AGENTS.md` in the scaffold and teaches doctor the shape. **ADRs/** (D12): `AGENTS.md` + `NNNN-<slug>.md`, one decision per file, monotonic numbering — scaffold + doctor shape here; fields, status vocabulary and acceptance rule in `memory-two-tier-principles`. `specs/assets/` retires — `memory/ARCHITECTURE.md` is the canonical home (fold what is still referenced, fix `memory/architecture.md`’s `../assets/` links). **Root `specs/_archive/` is deleted in the migration (operator ruling 2026-08-23: git history is the archive)** — destructive step, executed only with the operator present; FROZEN gate class repoints to per-area `*/_archive/`. `specs/backlog/remote-bugs/` dies (content adjudicated at intake). Doctor gains TREE-8 "nothing beyond canon" and `--recipe` (ordered concrete steps for whatever `specs upgrade` cannot do alone); `specs upgrade` automates the safe renames; compliance stays WARN-only — agent + user decide, never a block (D15: no new blocking CLI or hook for procedure anywhere in this front). Scaffold (`public/scaffold/`) reshaped to emit the v6 tree with scoped `AGENTS.md` (READMEs die). Migration of this repo’s own `specs/` included — the BUGS.jsonl migration folds each existing event chain into one record (`reported` → core fields; the terminal event → `status`/`cause`/`resolved_release`; `resolved_commit` back-filled by `git log -S<bug_id>` where unambiguous, else left null for the first audit).
- **Provenance:** operator request (2026-08-23 dd-grill-me session, 2 rounds, 20 questions — handoff `.dadaia/handoff/dadaia-workspace/2026-08-23-claude-code-specs-canon-grill.handoff.json`); amended by operator ratification 2026-08-26 dd-grill-me (3 rounds, 18 questions — handoff `.dadaia/handoff/dadaia-workspace/2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill.handoff.json`, rulings D3/D11/D12); relates-to `gitflow-contract-v2-consolidation` (CONSUMED v0.4.4 — RELEASE.jsonl records the same push/pr/ship milestones that contract defines); depended-on by `entity-behavior-map`, `bug-lineage-and-commit-discipline`, `audit-canon-v1`, `memory-two-tier-principles`
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/doctor.py#SpecsDoctor
    surface: existing
  change: "pattern v6: TREE-8 nothing-beyond-canon check, per-area _archive, BUGS.jsonl/ARCHITECTURE.md/TECHSTACK.md/QUALITY.md names, bare-semver live release dir, RELEASE.jsonl presence, _ideas/ rules, audits/<YYYYMMDD>-<slug>/ + ADRs/NNNN-<slug>.md shapes, --recipe output; WARN-only"
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/scaffolder.py#ScaffoldResult
    surface: existing
  change: "scaffold emits the v6 tree: scoped AGENTS.md per area incl. audits/ and ADRs/ (hash-projected), BUGS.jsonl, RELEASE.jsonl-ready releases/, _ideas/, no READMEs, no assets/, specs_pattern_version 6"
- subject:
    kind: code
    ref: dadaia_workspace/features/bugs/service.py#BugService
    surface: existing
  change: "BUGS.jsonl path; one-record-per-bug model (append once, governance fields rewritten in place); registration requires symptom+repro+severity+expected; idempotent `dadaia bugs archive` moves terminal records >90 days to _archive/bugs_histo.jsonl; v5 event-chain -> v6 record migration (resolved_commit back-filled via git log -S where unambiguous)"
- subject:
    kind: code
    ref: dadaia_workspace/hooks/sdd_gate.py#evaluate_payload
    surface: existing
  change: "MEMORY phase resolution folds the last phase event from the live release RELEASE.jsonl (ACTIVE.md retired); FROZEN class repoints to per-area */_archive/"
- subject:
    kind: doc
    ref: specs/releases/RELEASE.jsonl
    surface: new
  change: "release-event-v1 schema: {ts,event,agent,session_id,data}; kinds created/spec_status/phase/rc_open/rc_close/review/push/pr/ship/archive/note plus sha-bearing milestones defined/implemented/shipped (+pr) and audited (+audit folder); individual commits excluded, milestone shas included (D3 2026-08-26)"
- subject:
    kind: doc
    ref: specs/backlog/_archive/backlog_histo.jsonl
    surface: new
  change: "never-delete moves here: full-snapshot JSONL record per entry exit; BACKLOG.md becomes the live photo (ACTIVE only)"
```


### entity-behavior-map
- **Title:** entity-behavior-map — mandatory validated map: EVERY core skill and EVERY scoped AGENTS.md ↔ exactly one DADAIA.md section (incl. Audits and ADRs rows), contract tests RED on any unmapped member; the D15 enforcement-posture section; plus the skill surface that rides the v6 canon
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Make the rules→skills→scoped-AGENTS.md trios a **validated map instead of a convention**, so the three layers complement each other and never restate or contradict (the repetition/contradiction pattern the 2026-08-23 audit measured). **Amended 2026-08-26 — grill handoff `2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill` (rulings D14, D15); prior text kept, the "5 rows" scope is superseded as stated below.** (1) Manifest `dadaia_workspace/public/entities/behavior-map.json`. *2026-08-23 wording:* "with 5 rows: Backlog Definition → `dd-backlog-definition` → `backlog/AGENTS.md`; Bug Registration → `dd-bug-registration` → `bugs/AGENTS.md`; Bug Resolution → `dd-bug-resolution` → `bugs/AGENTS.md`; Release Definition → `dd-release-definition` → `releases/AGENTS.md`; Release Implement (includes memory update + closure) → `dd-release-implement` → `releases/AGENTS.md` + `memory/AGENTS.md`. Audit row deferred until audits are redesigned." *Re-worded 2026-08-26 (D14 — full coverage is mandatory):* the map covers **EVERY core skill** shipped under `dadaia_workspace/public/skills/` and **EVERY scoped `AGENTS.md`** — both the scaffolded ones (`specs/AGENTS.md`, `backlog/`, `bugs/`, `releases/`, `memory/`, `audits/`, `ADRs/`) and the library's own (`.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `tests/AGENTS.md`, `repos/<slug>/AGENTS.md` template) — each mapped to **exactly one** `DADAIA.md` section; `DADAIA.md` is the always-on rules file and the map's spine. The five original rows stay and the deferral is lifted: **Audits → `dd-audit-project` → `audits/AGENTS.md` → DADAIA.md §6 "Audits"** and **ADRs → (no core skill; the ADR procedure is `memory-two-tier-principles`' `ADRs/AGENTS.md`) → `ADRs/AGENTS.md` → DADAIA.md §6 "Memory"** are added, and every remaining skill (`dd-grill-me`, `dd-gitflow-default`, `dd-cli-library`, `dd-manager-orchestration`, `dd-ai-eng-knowhow`, `dadaia-test-stewardship`, `dadaia-handoff-emitter`, `dadaia-task-manager`, `dadaia-workspace-manager`, `dadaia-workspace-spec-navigator`, `dadaia-workspace-spec-reviewer`, `dadaia-step0-memory-bootstrap`, `dd-workspace-doctor`, `dev-server-registry`, `architect-core-workflow`, and the candidates `dd-diagnose` / `dd-architecture-survey` / `dd-code-review` the moment they exist) gets its row, extending the existing `rules-skills-map.json` (topic → section → skill) rather than replacing it — `behavior-map.json` is that file's superset with the scoped-AGENTS.md column added. Row example:
```json
{"section":"§7 Quality — Register every bug you hit","skill":"dd-bug-registration","scoped_agents_md":["specs/bugs/AGENTS.md"],"hash_tuple":{"section":"sha256:…","skill":"sha256:…","scoped":["sha256:…"]},"recorded_by":"ai-engineer","recorded_at":"2026-09-01"}
```
(2) **Contract tests in the lib** (`tests/contract/test_behavior_map.py`, extending `tests/contract/test_rules_skills_map.py`'s enforcer): every member exists; each member carries the pointers to its row companions; a recorded hash tuple per row goes RED when any member changes without the tuple being re-recorded — forcing the joint review; *added 2026-08-26 (D14):* the suite goes **RED when any skill on disk has no row, when any scoped `AGENTS.md` on disk has no row, and when any `DADAIA.md` section has no owner row** (or vice-versa: a row whose section/skill/AGENTS.md does not exist) — mutation fixtures prove each direction, in the pattern of `test_mutation_fixture_2_unmapped_skill_turns_red`. The semantic equalization (scopes complement, nothing contradicts) is the `ai-engineer`’s act when re-recording the tuple, and any inconsistency found is asked, never silently patched. (3) `DADAIA.md` gains stable per-behavior anchors (named subsections) for the map to point at — *added 2026-08-26 (D15):* one short section states the **enforcement posture** that every entry of the 2026-08-26 front is measured against, verbatim in intent: "*Skills instruct procedure. Audits measure conformance from git and JSONL history. Hooks and the CLI validate only at the publication boundary (push / PR) and never block a human.*" — plus the short sections those entries specify for `DADAIA.md` (bug lineage + commit shapes from `bug-lineage-and-commit-discipline`; audits from `audit-canon-v1`; memory two-tier + ADRs from `memory-two-tier-principles`): **this entry is the single owner of the `DADAIA.md` file write** (BL-CONFLICT adjudication 2026-08-26); the three entries specify their section text and depend on this entry to land it, and whichever release picks any of them without this entry rebases that section into this entry's scope first. (4) Skill surface riding the canon: rename `dd-bug-fix` → `dd-bug-resolution` (all references updated); `dd-release-implement` rebuilt in the robust skills-examples shape — short SKILL.md with per-step "Done when" + 3 disclosed siblings `RC-FLOW.md` (state ladder, absorbs CLOSURE-CHECKS.md), `RELEASE-EVENTS.md` (RELEASE.jsonl append recipes per milestone — now including the sha-bearing `defined`/`implemented`/`shipped` milestones of `specs-canon-v6` D3), `MEMORY-UPDATE.md` (memory protocol; no separate dd-memory-update skill — operator ruling Q11a); `CLOSURE-TEMPLATE.md` dies with CLOSURE.md; `dd-backlog-definition` rewritten for the live-photo BACKLOG.md + histo JSONL (its §2 "no JSONL for backlog" clause retires); `dd-bug-registration`/`dd-release-definition` updated to the v6 record fields and RELEASE.jsonl flow; the scoped `AGENTS.md` files authored short and direct, hash-projected under the TREE-5 regime. Depends-on `specs-canon-v6` (the layout the map validates). Relates-to ACTIVE `dd-diagnose` (touches the same `dd-bug-fix` file — the rename lands here, the method extraction lands there; whichever release picks second rebases on the first). Relates-to `bug-lineage-and-commit-discipline` (owns `bugs/AGENTS.md` content and the `dd-bug-resolution/LINEAGE.md` sibling; this entry owns `dd-bug-resolution/SKILL.md` and its pointer to that sibling), `audit-canon-v1` (owns `dd-audit-project/SKILL.md` + `audits/AGENTS.md`; this entry adds their row), `memory-two-tier-principles` (owns `ADRs/AGENTS.md` + `memory/AGENTS.md` content; this entry adds their rows).
- **Provenance:** operator request (2026-08-23 dd-grill-me session, 2 rounds — same handoff as `specs-canon-v6`); amended by operator ratification 2026-08-26 dd-grill-me (3 rounds, 18 questions — handoff `.dadaia/handoff/dadaia-workspace/2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill.handoff.json`, rulings D14/D15); depends-on `specs-canon-v6`; relates-to `bug-lineage-and-commit-discipline`, `audit-canon-v1`, `memory-two-tier-principles`, `dd-diagnose`, `dd-architecture-survey`, `dd-code-review`
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/entities/behavior-map.json
    surface: new
  change: "behavior manifest superset of rules-skills-map.json: one row per core skill AND per scoped AGENTS.md (scaffolded + library) -> exactly one DADAIA.md section, incl. Audits and ADRs rows, with a recorded hash tuple per row (D14 2026-08-26 — full coverage, not 5 rows)"
- subject:
    kind: code
    ref: tests/contract/test_behavior_map.py#test_behavior_map_rows
    surface: new
  change: "contract tests: members exist, cross-pointers present, hash tuple matches; RED on any skill or scoped AGENTS.md on disk without a row, on any DADAIA.md section without an owner row, and on any row naming a missing member — mutation fixtures per direction"
- subject:
    kind: doc
    ref: dadaia_workspace/public/data/DADAIA.md
    surface: new
  change: "stable per-behavior anchors (named subsections) for Backlog/Bugs/Releases/Memory/Audits/ADRs behaviors; the D15 enforcement-posture section (skills instruct, audits measure from git/JSONL history, hooks+CLI only at the publication boundary and never block a human); hosts the short sections specified by bug-lineage-and-commit-discipline, audit-canon-v1 and memory-two-tier-principles — single owner of the DADAIA.md write; no content duplication with skills or scoped AGENTS.md"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-release-implement/SKILL.md
    surface: new
  change: "robust shape: short SKILL.md with Done-when steps + disclosed siblings RC-FLOW.md / RELEASE-EVENTS.md (incl. sha-bearing defined/implemented/shipped milestones) / MEMORY-UPDATE.md; CLOSURE-TEMPLATE.md and CLOSURE-CHECKS.md retire; RC-FLOW.md segment-close step names the survey as an operative dependency — Call the Skill tool with \"dd-architecture-survey\" [absorbed from dd-architecture-survey, adjudication 2026-08-23]"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-bug-fix/SKILL.md
    surface: new
  change: "renamed to dd-bug-resolution; all references updated; content aligned to the BUGS.jsonl record model; reproduce/RED/root-cause steps become an operative dependency — Call the Skill tool with \"dd-diagnose\" [absorbed from dd-diagnose, adjudication 2026-08-23]; the lineage step is a pointer to the disclosed sibling LINEAGE.md owned by bug-lineage-and-commit-discipline [adjudication 2026-08-26] — the skill keeps only the bug lifecycle (branch, record update, commit, no push)"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md
    surface: new
  change: "live-photo BACKLOG.md + backlog_histo.jsonl snapshot records; intake must confront existing ACTIVE (annulment only with operator ratification); LEDGER-in-file clause retires; isolated `chore(backlog): add <slug>` commit per entry (D10 pointer to bug-lineage-and-commit-discipline)"
```


### nine-skill-study-execution
- **Title:** nine-skill-study-execution — execute the operator-ratified nine-skill dispositions: Update×5, Merge×3, Fuse×1, zero Retire
- **Opened:** 2026-08-24
- **Status:** candidate
- **Description:** Theme **C** (token-economy / AI-surface) · priority **HIGH** · size **MEDIUM** (execution spread over one release). The T-044-23/FR14 nine-skill study (ai-engineer handoff 2026-08-24T015304Z; nine remaining public skills, 1,046 lines, audit scores 4.3–7.5) produced per-skill proposals; **operator ruling R2 (2026-08-24) RATIFIES the dispositions — Update×5, Merge×3, Fuse×1, zero Retire — as recorded provenance; execution still needs a release pick.** Dependencies: (1) the 2 CLI-help-related merges were adjudicated **jointly with ACTIVE `cli-help-architecture-and-session-injection`** — whichever release picks either entry rebases its scope on the other; (2) the single Fuse (architect-core-workflow → dadaia-codebase-design) is two-stage: ACTIVE `dadaia-codebase-design` must land first, only then is the source absorbed and retired; (3) open bug `dadaia-task-manager-stale-workspace-protocol-citation` (LOW) is named inside the dadaia-task-manager Update — fixing the bug via Arm B does not pre-empt the disposition. Sequence after/with `coupled-inventory-shared-oracle` (the shared roster oracle cheapens every skill-surface change). Shaves the same always-on budget as the C2–C4 token-economy program.
- **Provenance:** intake-report item C1 (v0.4.4 intake, approved 2026-08-24) + operator ruling R2 (2026-08-24) ratifying the study handoff dispositions
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md
    surface: new
  change: "representative anchor for the ratified execution set: apply the nine per-skill dispositions (Update x5, Merge x3, Fuse x1, zero Retire) exactly as recorded in the study handoff; every merge/fuse updates all cross-references and the projection roster in the same change"
```

### bug-lineage-and-commit-discipline
- **Title:** bug-lineage-and-commit-discipline — BUGS.jsonl record contract (immutable core / mutable governance), `caused_by` lineage check on every fix, isolated-commit shapes, no push on resolve, hooks de-slopped to the publication boundary — procedure in skills + scoped AGENTS.md + one short DADAIA.md section, conformance measured by audits, never by new CLI validation or hook blocks
- **Opened:** 2026-08-26
- **Status:** candidate
- **Description:** Turn the bug loop the 2026-08-23 audit measured (490 bug_ids / 1005 events; 132 of 471 resolutions with zero evidence; 92 cross-bug references living only as prose; documented chains such as gitignore ×4 recurrences, the certify probe re-bugged 37 min after its fix, and frozen-clock → guard (+294 LOC) → guard's own bug) into a **recorded lineage with a measurable discipline**. Rulings D2, D4, D8, D9, D10, D11 (bug part) of the 2026-08-26 grill. Enforcement posture (D15, acceptance criterion of every item below): **skills instruct the procedure; scoped `AGENTS.md` and one short `DADAIA.md` section state it always-on; audits (`audit-canon-v1` pillar 1) measure conformance from git and JSONL history; NO new CLI validation and NO new hook block is added for any of it** — the only mechanical surface is the publication boundary (push/PR) and it never blocks a human. **(A) The record contract (D11).** `BUGS.jsonl` (path and migration owned by `specs-canon-v6`) holds one record per bug, appended once — no event stream, no fold. Immutable core fields: `id`, `ts`, `reported_by`, `title`, `severity`, `surface`, `component`, `context`, `symptom`, `repro`, `expected`, `root_cause` (immutable once set), `solution` (immutable once set — carries the regression-test seam). Mutable governance fields: `status` (`open|picked|resolved|superseded|deferred|rejected`), `cause` (one sentence, the structural cause), `caused_by` (`<bug-id>` | `none` — never absent on a resolved record), `resolved_commit` (sha, see the open question), `resolved_release`, `audited` (audit folder slug or null). `bug-event-v1.schema.json` is replaced by `bug-record-v1.schema.json` (`additionalProperties: false` kept; the mutable/immutable split is documented per property) and `core/models/bugs.py#BugEvent` + the coherence checker become the record model (coherence = a resolved record carries `cause`, `caused_by`, `resolved_release`; a `superseded` record carries `superseded_by` — checked by `dadaia bugs status`/doctor as WARN, not a block, and measured by the audit). Registration example — the line as first appended (governance fields present and null so the record shape never changes):
```json
{"id":"ci-preflight-quick-skips-lint-imports-048","ts":"2026-08-26T10:02:41Z","reported_by":"software-engineer","title":"ci preflight --quick skips lint-imports","severity":"MEDIUM","surface":"dadaia ci preflight","component":"cli/commands/ci.py","context":"dadaia-workspace","symptom":"--quick returns 0 while lint-imports fails in CI","repro":"1. break an import contract 2. dadaia ci preflight --quick 3. exit 0","expected":"--quick runs lint-imports (only e2e is skipped)","status":"open","cause":null,"caused_by":null,"resolved_commit":null,"resolved_release":null,"audited":null}
```
Resolution example — the SAME line after the fix (core fields byte-identical; `root_cause`/`solution` set once; governance fields filled): `…"root_cause":"quick mode built its step list from a hard-coded tuple that never included lint-imports","solution":"single step registry consumed by both modes; regression test tests/integration/test_ci_preflight.py::test_quick_runs_lint_imports","status":"resolved","cause":"duplicated step list (two code paths)","caused_by":"frozen-clock-guard-tz-boundary-031","resolved_commit":"9d8e7f6","resolved_release":"0.4.5","audited":null…`. **(B) Lineage check on every fix (D8).** Before writing the fix, the fixer (1) filters `BUGS.jsonl` for records with the same `component` or `surface` in the audit window (since the last `audited` milestone in RELEASE.jsonl, or the whole file when none), (2) reads each prior record's resolution diff — `git show <resolved_commit>`, or `git log -S<prior-id> --oneline` when `resolved_commit` is null — and (3) declares `caused_by` with evidence in `cause`: either `caused_by: <prior-id>` ("the prior fix introduced/left the structure this bug rides on") or `caused_by: none` ("prior diffs read: <ids>; no causal link"). Example declaration written into the record and echoed in the fix commit body:
```text
caused_by: frozen-clock-guard-tz-boundary-031
evidence: git show 4c1d2e3 added _quick_steps tuple in ci.py (+18) separate from STEPS; this bug is that second path drifting.
prior diffs read: frozen-clock-guard-tz-boundary-031 (4c1d2e3), ci-preflight-runner-fail-closed-029 (7a7b7c7)
```
A `caused_by` pointing at a prior fix is the trigger of the standing architecture-review order — the fixer must show the structural cause and a diff that does not grow the feature; a net-positive diff routes to `software-architect` before the commit (DADAIA.md §7, unchanged). Procedure home: disclosed sibling `dd-bug-resolution/LINEAGE.md` (this entry) pointed at from `dd-bug-resolution/SKILL.md` (pointer owned by `entity-behavior-map`; the reproduce/RED method is `dd-diagnose`'s — this entry never restates it), summarized in `specs/bugs/AGENTS.md` (this entry) and in a short `DADAIA.md` section whose text this entry specifies and `entity-behavior-map` lands (single owner of the DADAIA.md write). **(C) Commit shapes (D10, D2, D4)** — rules in `dd-gitflow-default` §3 + `dd-bug-registration` + `dd-backlog-definition` + scoped AGENTS.md, measured by the audit's bug and spec pillars via `git log`, never by hooks: (1) bug registration is an **isolated commit** staging only `specs/bugs/BUGS.jsonl` — `chore(bugs): report ci-preflight-quick-skips-lint-imports-048` — so the registration sha is **derivable from git** (`git log -S'"id":"ci-preflight-quick-skips-lint-imports-048"' --diff-filter=A` finds it; nothing is hand-written); (2) backlog entry = isolated commit `chore(backlog): add <slug>` staging only `specs/backlog/BACKLOG.md`; ADR = isolated commit `docs(adr): propose 0007-<slug>` (rule owned by `memory-two-tier-principles`); (3) the fix is **contained in the commit that resolves**: `fix(ci): quick preflight runs lint-imports (resolves ci-preflight-quick-skips-lint-imports-048)` stages the code, the regression test, and the `BUGS.jsonl` line with `status: resolved`, `cause`, `caused_by`, `resolved_release` — then, because a commit cannot contain its own sha, `resolved_commit` is written in an immediately following ledger-only commit `chore(bugs): resolved_commit 9d8e7f6 for ci-preflight-quick-skips-lint-imports-048` (see the open question); (4) **no push on bug resolve** — commit only; a push happens when the operator asks (e.g. "deploy the bug fixes without a release") and then the agent runs `dadaia ci preflight` first as an always-on rule (D9), not because a hook forces it; (5) release definition = one bundled commit (SPEC+PLAN+TASKS + purge-on-pick + `status: picked` on the picked bug records); `_ideas/` SPEC = SPEC only. **(D) Hooks de-slop (D9) — folded here, not a separate entry:** the three hook surfaces are exactly the commit/push chokepoints whose posture rules (C) replace; a separate entry would edit the same three files (BL-CONFLICT by construction) with no separable release value. Changes: `pre-commit-presence-gate.sh` becomes advisory-only (presence WARN, exit 0 always) or is removed outright — the `backlog doctor` BLOCK and the fail-closed runner are agent-created slop that blocked humans (`cli/commands/ci.py#pre_commit_check` drops `_run_backlog_doctor_gate`; the CI `backlog-doctor` job already covers it); `pre-push-ci-gate.sh` keeps ONLY the publication boundary — branch-name policy + range-scoped denylist scan (the `ci preflight --quick` call leaves the hook; the preflight becomes the always-on rule "run `dadaia ci preflight` before you push" in `DADAIA.md` §7 + `dd-gitflow-default` + `dd-release-implement`, and the audit measures pushes whose CI went red for preflight-class failures). The security-verdict CI gate on PRs is untouched (it is the publication boundary). **Open question for the definition grill (handoff findings[2] / decisions_required[1]):** D2 stores `resolved_commit` as a mutable field while the fix is contained in the commit that resolves, and a commit cannot carry its own sha. Both options honour D2/D11 — (i) the follow-up ledger-only commit in the same session (shown in (C)(3); costs one extra commit per bug, sha is explicit in the file), or (ii) leave `resolved_commit` null and derive it on read (`git log -S'"id":"<id>"' -- specs/bugs/BUGS.jsonl` — the commit that flipped `status` to `resolved`; zero extra commits, the field is an audit-filled cache written when pillar 1 reviews the bug). The `dd-release-definition` grill picks one before the SPEC; the record schema admits both (the field is nullable). Relates-to `dd-diagnose` (method, called by dd-bug-resolution — untouched here), `dd-architecture-survey` (consumes `caused_by` chains as its recurrence input), `dd-code-review` (bug-surface axis cites `caused_by`). Depends-on `specs-canon-v6` (BUGS.jsonl path + migration, RELEASE.jsonl `audited` milestone the window reads).
- **Provenance:** operator ratification 2026-08-26 dd-grill-me (3 rounds, 18 questions — handoff `.dadaia/handoff/dadaia-workspace/2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill.handoff.json`, rulings D2/D4/D8/D9/D10/D11; hooks-de-slop fold decided by project-manager per decisions_required[0]); depends-on `specs-canon-v6`; relates-to `entity-behavior-map` (owns `dd-bug-resolution/SKILL.md` and the `DADAIA.md` write), `audit-canon-v1` (measures this discipline), `dd-diagnose`, `dd-architecture-survey`, `dd-code-review`
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/schemas/bugs/bug-event-v1.schema.json
    surface: new
  change: "replaced by bug-record-v1.schema.json: one record per bug; immutable core (id, ts, reported_by, title, severity, surface, component, context, symptom, repro, expected, root_cause/solution once set) + mutable governance (status, cause, caused_by, resolved_commit, resolved_release, audited); additionalProperties false"
- subject:
    kind: code
    ref: dadaia_workspace/core/models/bugs.py#BugEvent
    surface: existing
  change: "becomes BugRecord with the immutable/mutable split; coherence checker validates the record (resolved => cause+caused_by+resolved_release; superseded => superseded_by) as WARN surfaced by `dadaia bugs status`/doctor — never a block"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-bug-registration/SKILL.md
    surface: new
  change: "record-model registration (required symptom+repro+severity+expected, governance fields null); isolated commit `chore(bugs): report <id>` staging only BUGS.jsonl; registration sha derivable via git log -S, never hand-written"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-bug-resolution/LINEAGE.md
    surface: new
  change: "disclosed sibling: the lineage check — same component/surface filter over the audit window, git show of prior resolution diffs (git log -S fallback), caused_by <id>|none with evidence, fix contained in the resolving commit, resolved_commit fill per the definition-grill answer, commit only / no push"
- subject:
    kind: doc
    ref: specs/bugs/AGENTS.md
    surface: new
  change: "scoped law for bugs/: record model, isolated registration commit, lineage check before any fix, resolving-commit shape, no push on resolve; points at dd-bug-registration / dd-bug-resolution and the DADAIA.md section"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md
    surface: new
  change: "§3 gains the commit-shape rows (isolated chore(bugs)/chore(backlog)/docs(adr) commits, fix-in-resolving-commit, bundled definition commit, _ideas SPEC-only) and the always-on rule `dadaia ci preflight` before push; §5 row 2 re-worded: preflight is discipline measured by audit, the hook keeps only branch policy + denylist"
- subject:
    kind: doc
    ref: dadaia_workspace/public/scripts/pre-commit-presence-gate.sh
    surface: new
  change: "advisory-only (presence WARN, always exit 0) or removed; backlog-doctor block and fail-closed runner deleted"
- subject:
    kind: doc
    ref: dadaia_workspace/public/scripts/pre-push-ci-gate.sh
    surface: new
  change: "publication boundary only: branch-name policy + range-scoped denylist scan; the `ci preflight --quick` invocation leaves the hook"
- subject:
    kind: code
    ref: dadaia_workspace/cli/commands/ci.py#pre_commit_check
    surface: existing
  change: "backlog-doctor gate removed from the pre-commit path (_run_backlog_doctor_gate and _staged_backlog_paths deleted); the CI backlog-doctor job keeps the unscoped sweep"
```

### audit-canon-v1
- **Title:** audit-canon-v1 — audits as committed spec artifacts (`specs/audits/<YYYYMMDD>-<slug>/AUDIT.md` + `FINDINGS.jsonl` record model), three pillars always together (bug history · spec compliance · memory/constitution drift), window = since the last `audited` milestone, SUGGESTED every 5 releases and never mandatory, `project-auditor` writes `specs/audits/**`, `dd-audit-project` rewritten, SPEC-DOC-036 regex retired in favour of the FINDINGS fold
- **Opened:** 2026-08-26
- **Status:** candidate
- **Description:** Rebuild the audit from a HEAD-snapshot HTML report (today: `dd-audit-project` + `project-auditor` compare memory ↔ code on 6 dimensions, read no bugs, no diffs, no recurrence, no history; the persona is forbidden `specs/**` and writes only `.dadaia/reports`; `specs/audits/README.md` claims a folder convention no tool honours; SPEC-DOC-036 checks dispositions by regex over prose; the skill is `disable-model-invocation: true` and absent from the persona's skill list) into an **auditable artifact inside specs that measures conformance from git and JSONL history**. Rulings D5, D6, D7 (+ D11 for the record model, D15 for the posture). **(A) Location and format (D5).** `specs/audits/<YYYYMMDD>-<slug>/` with `AUDIT.md` (Markdown: scope, window `[from-sha, to-sha]` and the releases inside it, method per pillar, the score, the operator-facing summary) and `FINDINGS.jsonl` (one record per finding, appended once — D11). `specs/audits/AGENTS.md` replaces `README.md` (scoped law + index of audits). `project-auditor`'s `write_allowlist` gains `specs/audits/**` (it stays forbidden everywhere else in `specs/`; it still never fixes). The HTML report/handoff remains the operator-facing emission (DADAIA.md §5) but is derived from, never a substitute for, the committed folder. Immutable finding fields: `id` (`<audit-slug>-F<nnn>`), `pillar` (`bugs|specs|memory`), `severity`, `refs` (file:line, bug ids, commit shas, release ids), `claim` (what is wrong, one sentence), `evidence` (the command + the observed output, redacted). Mutable governance fields: `disposition` (`open|fixed|superseded|deferred|rejected`), `release` (the remediation release that dispositioned it), `reason`. Example — as appended, then the SAME line after the remediation release:
```json
{"id":"20261020-five-release-window-F003","pillar":"bugs","severity":"HIGH","refs":["ci-preflight-quick-skips-lint-imports-048","frozen-clock-guard-tz-boundary-031","4c1d2e3","9d8e7f6"],"claim":"fix-induced bug: 048 rides the second step list that the 031 fix introduced; 031 resolved without a structural cause","evidence":"git show 4c1d2e3 -- dadaia_workspace/cli/commands/ci.py (+18 _quick_steps); BUGS.jsonl 031 cause=null","disposition":"open","release":null,"reason":null}
{"id":"20261020-five-release-window-F003", … same immutable fields … ,"disposition":"fixed","release":"0.5.0","reason":"single step registry (T-050-04)"}
```
**(B) Three pillars, always together (D6)** — one audit runs all three; none is optional, none runs alone. *Pillar 1 — bug history.* Input: every `BUGS.jsonl` record whose registration or resolution falls in the window, found by `git log -S'"id":"<id>"' -- specs/bugs/BUGS.jsonl` (the `--diff-filter=A` hit is the registration commit; the hit that flipped `status` to `resolved` is the resolution commit) and `git show <resolved_commit>` (or that derived sha) for each resolution diff. Measures: recurrence (same `component`/`surface` re-registered after a resolution — the gitignore ×4 pattern), fix-induced bugs (a resolution diff whose touched files appear in a later bug's `refs`/`component`; must agree with the record's `caused_by`, and a `caused_by: none` contradicted by the diff is a finding), resolutions without `cause`/regression seam, net-positive diffs that never routed to `software-architect`, commit-shape conformance (isolated `chore(bugs): report <id>`, fix contained in the resolving commit, no push on resolve — read from `git log --format` + `--stat`). On each record reviewed the auditor sets `audited: <audit-slug>` (mutable governance field) so the next audit's window is exact. *Pillar 2 — spec compliance.* `dadaia specs doctor --json` across every release in the window (archived ones too), conformance to the dadaia-workspace specs pattern (canon v6 tree, RELEASE.jsonl milestone completeness — `defined`/`implemented`/`shipped` each with sha, SPEC provenance/`**Consumes:**`, purge-on-pick executed in the SPEC commit), and commit-shape discipline via `git log` (one bundled definition commit, `chore(backlog): add <slug>` isolated, `chore(tasks): start <id>` reservations present, one commit per completed task group, `docs(adr):` isolated). *Pillar 3 — memory/constitution drift.* Every Part-1 principle of `ARCHITECTURE.md`/`QUALITY.md`/`TECHSTACK.md` (layout owned by `memory-two-tier-principles`) is **measured by the check it names** (`lint-imports` contract, the contract test, the doctor rule, the census) and the result recorded; `product/` atoms vs the code they describe (the existing 6-dimension method survives here); `constitution.md` violations; and the finding class **"Part 1 principle changed without an accepted ADR"** — `git log -p` on the Part-1 sections of the trio in the window, each hunk matched to an `accepted` ADR in `specs/ADRs/` named in the same commit; an unmatched hunk is a HIGH finding. Example pillar-3 finding: `{"id":"…-F011","pillar":"memory","severity":"HIGH","refs":["specs/memory/ARCHITECTURE.md#P-04","e5f6a7b"],"claim":"Part-1 principle P-04 (features mutually independent) re-worded in e5f6a7b with no accepted ADR in the commit","evidence":"git log -p e5f6a7b -- specs/memory/ARCHITECTURE.md; ls specs/ADRs/ shows no ADR dated within the commit","disposition":"open","release":null,"reason":null}`. **(C) Cadence and window (D6, D7).** An audit is **SUGGESTED every 5 releases — never mandatory**; the operator triggers it (`project-manager` surfaces the suggestion at release close when 5 or more `shipped` milestones have accrued since the last `audited`). The window is **from the last audited release to the current one** — not a fixed 5: the auditor scans every `RELEASE.jsonl` (live, `_ideas/`, `_archive/`) for the newest `audited` milestone, takes `[that sha, HEAD]`, and at the end appends an `audited` milestone (`{"event":"audited","data":{"sha":"<HEAD>","audit":"audits/<folder>"}}`) to the RELEASE.jsonl of the release it runs in — archived or not — so the chain never gaps. First audit under this canon: window = since the last archived audit's release when one is dispositioned, else operator-chosen. **(D) Lifecycle.** One audit → exactly one remediation release that gives every finding a disposition (unchanged law, DADAIA.md §6 Audits) — the release CLOSURE step rewrites each `FINDINGS.jsonl` line's governance fields (`disposition`, `release`, `reason`); an audit folder moves to `specs/audits/_archive/` only when no record is `open`. `dadaia specs doctor`'s SPEC-DOC-036/038 stop parsing prose: the check **folds `FINDINGS.jsonl`** (any `open` record in an archived audit = error; a live audit with all records terminal and a named release = "archive due" WARN). No new CLI verb for the audit itself: `project-auditor` writes the folder with its file tools; conformance of the audit to this canon is what the next audit's pillar 2 reads. **(E) Skill and persona.** `dd-audit-project` rewritten in the robust shape (short SKILL.md with per-pillar "Done when" + disclosed siblings `PILLAR-BUGS.md`, `PILLAR-SPECS.md`, `PILLAR-MEMORY.md`, `FINDINGS-FORMAT.md`), `disable-model-invocation` lifted, listed in `project-auditor`'s skills; the persona's mission becomes the three pillars over the window, its evidence-agent dispatch unchanged. Relates-to `dd-architecture-survey` (the survey is the operator-invoked, single-top-candidate sibling of pillar 1 — the audit measures, the survey proposes; they share `caused_by` chains as input and never duplicate the ranking), `dd-code-review` (its bug-surface axis is the per-PR miniature of pillar 1), `dd-diagnose` (the seam rule pillar 1 checks). Depends-on `specs-canon-v6` (folder in canon root, `audited` milestone, BUGS.jsonl path) and `bug-lineage-and-commit-discipline` (the record fields and commit shapes pillar 1 measures — an audit before them measures only what exists and records the gap as findings).
- **Provenance:** operator ratification 2026-08-26 dd-grill-me (3 rounds, 18 questions — handoff `.dadaia/handoff/dadaia-workspace/2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill.handoff.json`, rulings D5/D6/D7 + D11/D15); depends-on `specs-canon-v6`, `bug-lineage-and-commit-discipline`; relates-to `memory-two-tier-principles` (pillar 3 measures its principles and ADR rule), `entity-behavior-map` (Audits row + the `DADAIA.md` write), `dd-architecture-survey`, `dd-code-review`, `dd-diagnose`
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: specs/audits/AGENTS.md
    surface: new
  change: "scoped law for audits/: folder <YYYYMMDD>-<slug>/ with AUDIT.md + FINDINGS.jsonl, three pillars together, window since last audited milestone, suggested every 5 releases never mandatory, one remediation release per audit, archive only when no finding is open; index of audits; README.md retires into it"
- subject:
    kind: doc
    ref: specs/audits/README.md
    surface: new
  change: "retired — content folded into specs/audits/AGENTS.md (scaffold stops emitting READMEs)"
- subject:
    kind: doc
    ref: dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json
    surface: new
  change: "FINDINGS.jsonl record: immutable id/pillar/severity/refs/claim/evidence, mutable disposition/release/reason; additionalProperties false"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-audit-project/SKILL.md
    surface: new
  change: "rewritten: three-pillar protocol over the [last audited sha, HEAD] window with Done-when per pillar; disclosed siblings PILLAR-BUGS.md (git log -S / git show, recurrence, fix-induced vs caused_by, commit shapes, audited field update), PILLAR-SPECS.md (specs doctor across releases, milestone completeness, commit-shape discipline), PILLAR-MEMORY.md (Part-1 principles measured, product/ vs code, constitution, principle-changed-without-accepted-ADR), FINDINGS-FORMAT.md; disable-model-invocation lifted; appends the audited milestone"
- subject:
    kind: doc
    ref: dadaia_workspace/public/agents/project-auditor.md
    surface: new
  change: "write_allowlist gains specs/audits/**; mission = three pillars over the audit window, committed AUDIT.md + FINDINGS.jsonl, HTML derived; dd-audit-project listed in skills; still never fixes, still forbidden elsewhere in specs/"
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/doctor_closure_audit.py#ClosureAuditValidator
    surface: existing
  change: "check_audit_disposition / SPEC-DOC-036/038 fold FINDINGS.jsonl instead of regex over prose: open record in an archived audit = error; live audit fully dispositioned with a named release = archive-due WARN"
```

### memory-two-tier-principles
- **Title:** memory-two-tier-principles — ARCHITECTURE/QUALITY/TECHSTACK split into Part 1 "Principles" (ADR-gated, every principle carries `Measured by:`) and Part 2 "Implementation" (evolves with releases); first inventory promotes the import-linter contracts, LOC/complexity ratchets, LARGE census and test pyramid/lifecycle laws; `specs/ADRs/` canon (Nygard + MADR fields, operator-only acceptance, one decision per file, commit rule); constitution references principles; product/ = functional descriptions
- **Opened:** 2026-08-26
- **Status:** candidate
- **Description:** Make memory's fundamental rules **audit pillars instead of decoration** (rulings D13 and D12 of the 2026-08-26 grill; pillar 3 of `audit-canon-v1` measures them). Today `specs/memory/architecture.md` (294 lines), `tech-stack.md` (52), `quality-assurance.md` (324) and `specs/constitution.md` (261, outside memory/) carry no Principles/Implementation split and zero ADRs exist, while the measurable rules are scattered: the `[importlinter:contract…]` sections of `setup.cfg` (9 at HEAD — the grill counted 8; the inventory rule is "every contract", so the count is read from the file, never hard-coded), LOC ceilings, the complexity ratchet, the LARGE-test census (100), the diagram drift-guard tests; memory↔code drift is checked only documentarily (CLOSURE `## Drifts`). Enforcement posture (D15): skills + scoped `AGENTS.md` + a short `DADAIA.md` section instruct; pillar 3 measures; no CLI verb, no doctor rule, no hook for any of it. **(A) The split (D13).** Each of `ARCHITECTURE.md`, `QUALITY.md`, `TECHSTACK.md` (uppercase names owned by `specs-canon-v6`) is explicitly divided: **Part 1 — Principles**: fundamental, ADR-gated (a change to any Part-1 line lands in the commit that carries the `accepted` ADR, see (C)), numbered `P-NN`, each carrying a `Measured by:` line naming the existing mechanical check — **a principle without a measure is not admitted** (a rule nobody can measure is Part-2 prose or a proposed ADR, never a principle). **Part 2 — Implementation**: modules, diagrams, flows, dependencies, boundaries, tunables — the living description that `product-engineer` evolves at DEFINITION/CLOSURE with every release, no ADR needed. `product/<area>/<feature>.md` atoms stay **functional descriptions of features** (what the feature does, its contract and edge cases — never architecture principles, never implementation tours). `specs/constitution.md` stops restating rules and **references principles by id** (`see ARCHITECTURE.md P-04`); a constitution clause with no principle behind it is a candidate for an ADR or is deleted. Part-1 principle example (ARCHITECTURE.md):
```markdown
## Part 1 — Principles

### P-04 · Features are mutually independent
Features compose through the container, never through sibling imports; a helper two
features need lives inside each feature (duplication over coupling).
Measured by: `lint-imports` contract "features must be mutually independent (compose via
container, not sibling imports)" (`setup.cfg`), run by `dadaia ci preflight` and CI.
Accepted by: ADR 0002 (2026-09-02). Amended by: —
```
Example from QUALITY.md: `### P-12 · Every test declares intent and size at birth … Measured by: tests/contract/test_test_stewardship.py (undeclared test = SCAFFOLD, expires) + the LARGE census ceiling (100) in the same suite. Accepted by: ADR 0005`. **(B) First inventory (D13 — the first authoring is an inventory, not new rules):** one principle per import-linter contract in `setup.cfg` (layer direction core←infrastructure←features←cli/hooks; features never import infrastructure/subprocess directly; core imports no OS primitive except the platform seam; `kernel_tunables` imports no upper layer; features mutually independent; cli never imports infrastructure; `core.specs_resolver` single authority) — `Measured by:` the contract by name; the LOC ceilings and complexity ratchet (`Measured by:` the ratchet tests/`ruff` config that hold them); the LARGE-test census and the test pyramid/lifecycle laws of `dadaia-test-stewardship` (intent + size at birth, timeouts per tier, quarantine bug-gated, demotion at closure — `Measured by:` the stewardship contract tests); the diagram drift-guard (`Measured by:` its test). Each inventory principle is admitted through its own `accepted` ADR (one decision per ADR, so the inventory is ~a dozen ADRs 0001…, authored `proposed` by `product-engineer`/`software-architect`, accepted by the operator in one review sitting). **(C) `specs/ADRs/` canon (D12).** Folder in the canon root (layout/scaffold/doctor shape owned by `specs-canon-v6`; content rule here): `specs/ADRs/AGENTS.md` (the law + the index table `NNNN · title · status · date`) and one file per decision `NNNN-<slug>.md`, monotonic 4-digit numbering never reused; fields per Nygard (2011) + MADR 4: **Title**, **Status** (`proposed | accepted | rejected | superseded by NNNN`), **Date**, **Context**, **Decision** ("We will …"), **Consequences** (positive and negative), **Confirmation** (`Measured by:` — the import-linter contract / contract test / doctor check / audit pillar that proves the decision holds; an ADR with no confirmation cannot be accepted), and links **Supersedes** / **Amends** / **Amended by**. Rules: `accepted` is immutable — a reversal is a new ADR that supersedes (the old one's Status flips to `superseded by NNNN`, its only permitted edit); one decision per ADR, never a changelog; any agent may author `proposed`; **ONLY the operator flips Status to `accepted`, after reviewing** (an agent that writes `accepted` has violated the law — pillar 3 finding); commit rule: the ADR is an isolated commit `docs(adr): propose 0007-<slug>` at proposal, and the commit that changes a Part-1 principle **carries the accepted ADR** (`docs(adr): accept 0007-<slug>` stages the ADR file's status flip + the Part-1 hunk + the constitution reference in the same commit — that is what pillar 3's "Part 1 changed without accepted ADR" check reads). Skeleton:
```markdown
# ADR 0007 — Hooks validate only at the publication boundary

Status: proposed
Date: 2026-09-10
Supersedes: — · Amends: — · Amended by: —

## Context
Pre-commit hooks grew a backlog-doctor block and a fail-closed runner that blocked human
commits (bugs precommit-backlog-doctor-blocks-unrelated-commits, …).

## Decision
We will keep hooks and CLI validation at the push/PR boundary only; procedure lives in
skills and scoped AGENTS.md; audits measure conformance from git history.

## Consequences
+ humans are never blocked at commit; − discipline drift surfaces only at audit time.

## Confirmation
Measured by: tests/contract/test_hooks_publication_boundary.py (pre-commit exits 0 on any
staged set) + audit pillar 2 commit-shape review.
```
Accepted form differs only in `Status: accepted` (+ `Accepted by: operator, 2026-09-12`). No CLI verb, no doctor rule: `specs doctor` only knows the folder shape (canon-v6). Relates-to `dd-architecture-survey` (its top candidate, once grilled, becomes a `proposed` ADR when it changes a principle), `dd-code-review` (reviews cite the principle id a diff touches), `dd-diagnose` ("no correct seam → architecture finding" is a `proposed` ADR trigger). Depends-on `specs-canon-v6` (uppercase trio, `ADRs/` folder, `audits/` for pillar 3); relates-to `audit-canon-v1` (pillar 3 measures `Measured by:` and the ADR rule), `entity-behavior-map` (ADRs and Memory rows; owns the `DADAIA.md` write for the short section this entry specifies: "memory Part 1 is ADR-gated and measured; only the operator accepts an ADR").
- **Provenance:** operator ratification 2026-08-26 dd-grill-me (3 rounds, 18 questions — handoff `.dadaia/handoff/dadaia-workspace/2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill.handoff.json`, rulings D12/D13 + D15); depends-on `specs-canon-v6`; relates-to `audit-canon-v1`, `entity-behavior-map`, `dd-architecture-survey`, `dd-code-review`, `dd-diagnose`
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: specs/memory/ARCHITECTURE.md
    surface: new
  change: "Part 1 Principles (P-NN, ADR-gated, each with Measured by: naming the import-linter contract / ratchet / drift-guard test) + Part 2 Implementation (modules, diagrams, flows, dependencies, boundaries); first inventory promotes every setup.cfg import-linter contract and the LOC/complexity ratchets"
- subject:
    kind: doc
    ref: specs/memory/QUALITY.md
    surface: new
  change: "Part 1 Principles (test pyramid, intent+size at birth, timeouts per tier, quarantine bug-gated, demotion at closure, LARGE census ceiling — each Measured by: the stewardship contract tests) + Part 2 Implementation (suites, runners, evidence paths)"
- subject:
    kind: doc
    ref: specs/memory/TECHSTACK.md
    surface: new
  change: "Part 1 Principles (pinned toolchain laws with Measured by: the preflight/CI job that proves them) + Part 2 Implementation (versions, dependencies, runtime seams)"
- subject:
    kind: doc
    ref: specs/memory/AGENTS.md
    surface: new
  change: "scoped law: Part 1 changes only in the commit carrying an accepted ADR; a principle without Measured by: is not admitted; Part 2 evolves at DEFINITION/CLOSURE; product/ atoms are functional descriptions only"
- subject:
    kind: doc
    ref: specs/ADRs/AGENTS.md
    surface: new
  change: "ADR law + index: NNNN-<slug>.md, monotonic numbering never reused, Nygard+MADR fields incl. Confirmation (Measured by:), status vocabulary proposed|accepted|rejected|superseded by NNNN, accepted immutable, one decision per file, any agent proposes, ONLY the operator accepts, isolated docs(adr) commits, the Part-1 change rides the accepting commit"
- subject:
    kind: doc
    ref: specs/constitution.md
    surface: new
  change: "stops restating rules; references principles by id (ARCHITECTURE.md P-NN / QUALITY.md P-NN / TECHSTACK.md P-NN); clauses with no principle behind them become proposed ADRs or are deleted"
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
- atomic-write-primitive-consolidation · CONSUMED · v0.4.5 — picked at definition, FR2; updated in place at the closure sweep · 2026-08-24
- byte-golden-test-inventory-roster-split · CONSUMED · v0.4.5 — picked at definition, FR3; updated in place at the closure sweep · 2026-08-24
- coupled-inventory-shared-oracle · CONSUMED · v0.4.5 — picked at definition, FR4; updated in place at the closure sweep · 2026-08-24
- scan-test-vacuity-guard · CONSUMED · v0.4.5 — picked at definition, FR5; updated in place at the closure sweep · 2026-08-24
- doctor-slug-ownership-uniqueness · CONSUMED · v0.4.5 — picked at definition, FR9 (invariant or recorded rule-out, AS-4); updated in place at the closure sweep · 2026-08-24
- bug-append-write-time-denylist-redaction · CONSUMED · v0.4.5 — picked at definition, FR6; updated in place at the closure sweep · 2026-08-24
- specs-init-symlinked-target-refusal · CONSUMED · v0.4.5 — picked at definition, FR8; updated in place at the closure sweep · 2026-08-24
- bug-event-control-character-sanitation · CONSUMED · v0.4.5 — picked at definition, FR7, bundling the open MEDIUM unicode-line-separator bug; updated in place at the closure sweep · 2026-08-24
- always-on-token-diet · CONSUMED · v0.4.5 — picked at definition, FR11 (consumed by executing and measuring the pass, AS-3); updated in place at the closure sweep · 2026-08-24
- memory-catalog-digest-trimming · CONSUMED · v0.4.5 — picked at definition, FR12; updated in place at the closure sweep · 2026-08-24
- persona-line-ceiling-trim · CONSUMED · v0.4.5 — picked at definition, FR13 (bounded to existing sibling mechanisms, AS-1); updated in place at the closure sweep · 2026-08-24
- ai-surface-hygiene-residuals · CONSUMED · v0.4.5 — picked at definition, FR14; updated in place at the closure sweep · 2026-08-24
- intent-taxonomy-vocabulary-ruling · CONSUMED · v0.4.5 — picked at definition, FR15 (executed directly on the stewardship taxonomy, AS-2); updated in place at the closure sweep · 2026-08-24
- dadaia-references-doctor-sanction · CONSUMED · v0.4.5 — picked at definition, FR10, operator ruling O4; updated in place at the closure sweep · 2026-08-24
