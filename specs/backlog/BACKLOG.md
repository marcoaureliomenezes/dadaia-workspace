# Backlog — single source (ACTIVE only; exits live in backlog_histo.jsonl)

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

**Live-photo notice (2026-08-27, v0.5.0 FR5/T-050-13).** The in-file `## LEDGER` section retired: this document now holds `## ACTIVE` only. Every historical `LEDGER` line (117 rows) migrated to `specs/backlog/_archive/backlog_histo.jsonl`, one record per exit (`{id, ts, disposition, reason, release, by, entry_md, entry_md_source}`), 68 with `entry_md` recovered from an archived per-entry file and 49 with `entry_md: null` (post-consolidation entries, no per-entry archive file — recoverable via `git log -p` if ever needed). Mentions of `LEDGER`/`LEDGER line` in the notices below describe history as it happened and are left as-is; a closed item's terminal record now lives in the histo file, never a second `## ACTIVE` section.

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
