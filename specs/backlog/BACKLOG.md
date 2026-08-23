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

### spec-context-associated-repos
- **Title:** spec-context-associated-repos — a Spec Context Project owns ONE main repo (where `specs/` lives) plus N associated repos that follow its ALIVE/DEAD lifecycle
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** Today `SpecContextProject` carries a single `repo_slug`/`repo_url`, so a product that spans several repositories (one specs-bearing repo plus sibling service repos) cannot be modelled as one context — the operator must either create disjoint contexts (splitting the specs) or fall back to submodules the tool does not see. Demand: keep exactly one **main** repo per context as the home of `specs/` and the bind/memory target, and allow any number of **associated** repos registered against the same context; `context alive` clones/keeps every repo (main + associated) on disk and `context dead` syncs and removes every one of them, so the set of repos on disk always mirrors the context's state. New verbs (names to settle in grill-me): `context repo add <ctx> <slug> [--url]` / `context repo remove <ctx> <slug>` / `context repo list <ctx>`; `context show`/`list`/panel expose main + associated; export/import, the state migration (v2 → v3 registry schema) and `ci` foreign-slug derivation follow. Operator phrasing (2026-08-23): "cada spec context project tem um repo main — onde vivem as Specs; só 1 é possível como main, mas é possível adicionar outros, o que faz com que os repos sejam mantidos em disco ou não ao alternar o spec context project de ALIVE para DEAD e vice-versa."
- **Provenance:** operator request, 2026-08-23 — surfaced while trying to attach two sibling capture repos to an existing consumer context (the tool offered no verb for it)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/core/models/spec_context.py#SpecContextProject
  change: "add an ordered associated_repos collection (slug + url each) next to the single main repo_slug/repo_url; main stays unique and is the only specs/bind target"
- subject:
    kind: code
    ref: dadaia_workspace/features/migrate/state_v2.py#plan_migration
  change: "ship the registry schema bump (v2 -> v3) that introduces associated_repos with a backup-first, idempotent migration (schema-drop law - a schema change ships its migration)"
- subject:
    kind: cli
    ref: context alive
  change: "clone/keep the main repo AND every associated repo under repos/; idempotent when already ALIVE, reporting each repo"
- subject:
    kind: cli
    ref: context dead
  change: "git-sync and remove the main repo AND every associated repo from disk, refusing as today when any of them is dirty or unpushed"
- subject:
    kind: cli
    ref: context create
  change: "accept optional repeatable --associated <slug>[=<url>] at creation, in addition to the new context repo add/remove/list subcommands"
- subject:
    kind: cli
    ref: context show
  change: "render main repo plus the associated-repo list (slug, url, on-disk, live branch) in table and --json"
- subject:
    kind: cli
    ref: context list
  change: "show an associated-repo count (or list in --json) per context; keep current_branch semantics consistent with show (bug context-list-current-branch-stale-for-alive-repo)"
- subject:
    kind: code
    ref: dadaia_workspace/features/export/service.py#ExportService
  change: "export/import carry associated repos (url + branch) so a workspace round-trips with its full repo set"
- subject:
    kind: code
    ref: dadaia_workspace/features/panel/service.py#PanelContext
  change: "panel card lists main + associated repos per context"
```

### gitflow-contract-v2-consolidation
- **Title:** gitflow-contract-v2-consolidation — one DADAIA.md section + one skill (`dadaia-gitflow`) as the sole home of the git/gitflow contract; feature/{M.m.p} cut from main, develop and main advance only via PR, one live feature branch at a time, deleted after deploy
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** The git/gitflow contract is restated today in at least fourteen places and contradicts itself in at least two; the operator's v2 contract (2026-08-23) replaces it and collapses every restatement into exactly one always-on law section plus one operational skill. **The v2 contract, faithful in substance:** (1) the `dadaia-gitflow` skill is KEPT and becomes the operational home — it governs clearly how gitflow works, avoids ambiguity, stale-branch starts and merge conflicts, teaches how to start work by checking the remote branches, and carries one clear branch-creation rule. (2) Branch name `feature/{version}`, version = `major.minor.patch` with no prefix (e.g. `feature/1.0.0`). (3) The `main` / `develop` / `feature/{version}` strategy is kept; work always merges into `develop`. (4) An agent NEVER creates or works on any branch other than `feature/{version}`; it may pull, merge, open PRs, and check out `develop` and `main`; any other branch kind exists only on an explicit operator request. (5) Explicit instructions against stale branches and slop branches (many branches without a pattern); naming and flow consistency. (6) `main` is updated only by a PR coming from `develop`; `develop` is updated by the agent only via PR (from `feature/{version}`). (7) `feature/{version}` is ALWAYS created from `main` — which forces the previous version to be released on `main` before a new feature branch can exist. (8) Start-of-work protocol: fetch; check and diff `main` vs `develop`; identify which `feature/{version}` is being worked; detect whether a `feature/{version}` already exists that was created after `develop` was last updated. (9) Strong explicit rules: never two branches with the same `feature/{version}` at the same time; a `feature/{version}` is created only for a version incremented from `main` — the deploy of `{version}` on `main` is mandatory before `feature/{version+1}` (or `hotfix/{version+1}`) may be created; after the deploy of `{version}` on `main`, `feature/{version}` MUST be deleted. (10) The rules are agentic (a DADAIA.md section + the skill) and always suggest to the operator that they be implemented in CI/CD, so the process is deterministic and does not depend on agent or operator memory. **Scope includes the consolidation.** The 2026-08-23 scan (`.dadaia/tmp/claude/20260823/gitflow-inventory.md`) found the branch model restated in ≥14 places — DADAIA.md §3/§5/§6, the `dadaia-gitflow` skill, two memory atoms (`sdd-gate-v3`, `sdd-bug-backlog-governance`), the `pre-push-ci-gate.sh` header comments, eight agents (ai-engineer, project-manager, qa-engineer, software-engineer, code-reviewer, security-reviewer, product-engineer, plus `entities/registry.json` mandates), `dd-release-definition`, `dd-release-implement`, `dd-release-closure`, `dd-bug-fix`, `dd-bug-registration` — and these inconsistencies: the code regex in `features/chokepoints/service.py` requires `feature/v…` while the law, the skill and every real branch use no `v`; `dd-release-implement` L43 says "push implementation commits to `feature/{M.m.p}`", contradicting the local-only rule; remote slop branches survive on origin (`chore/*` ×7, `feature/pi-fourth-harness-v1`, `feature/v0.1.10`, six old `feature/*` never deleted); local `hotfix/0.4.3` was never deleted. Target state: **1 DADAIA.md section + 1 skill** (a second skill later only if mapped and justified through the rules→skills governance map, backlog `rules-skills-governance-map`); every other surface becomes a one-line pointer. Enforcement surface impacted: `features/chokepoints/service.py` (`_PERMITTED_BRANCH_RES` loses the `v`; the develop-only push policy inverts — allow `feature/{M.m.p}` pushes, refuse direct `develop`/`main` pushes), `.github/workflows/ci.yml` `pr-source-guard` (+ a develop-accepts-feature-only guard), the `sdd-gate-v3` and `sdd-bug-backlog-governance` memory atoms, the agents' branch/push rows, and the dd-* skills. **Open questions for the mandatory grill-me (not decided here):** (Q1) does `hotfix/{v+1}` survive as an operator-requested branch kind, or does Arm B also run on `feature/{v+1}`? (Q2) with `develop` PR-only, does milestone (a) (definition `Aprovado`) also become a PR feature→develop, or only ship? (Q3) security-review delta: does the PR diff feature→develop replace `origin/develop..develop`? (Q4) is the feature branch pushed continuously (for its PR), and does CI run on `feature/*` pushes?
- **Provenance:** operator request, 2026-08-23 (session transcript; scan evidence at workspace-relative `.dadaia/tmp/claude/20260823/gitflow-inventory.md`), triggered by the standing order of permanent architecture review oriented by bug history
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/data/DADAIA.md#gitflow
    surface: new
  change: "rewrite DADAIA.md §3 git chokepoints + §5 Branches/Hotfixes + §6 Push green into ONE gitflow section carrying the v2 contract (feature/{M.m.p} from main, develop and main via PR only, one live feature branch, delete after deploy, start-of-work protocol, CI/CD automation suggestion); every other DADAIA.md mention becomes a cross-reference"
- subject:
    kind: catalog
    ref: public-asset-distribution
  change: "rewrite dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md to the v2 contract (start-of-work protocol, branch-creation rule, uniqueness + deletion rules, slop/stale-branch avoidance, always-suggest-CI/CD section); collapse dd-release-definition/implement/closure, dd-bug-fix, dd-bug-registration and the pre-push-ci-gate.sh header to pointers into that skill (fix dd-release-implement L43 push-to-feature contradiction)"
- subject:
    kind: code
    ref: dadaia_workspace/features/chokepoints/service.py#_PERMITTED_BRANCH_RES
  change: "drop the `v` prefix so the regex matches feature/{M.m.p} and hotfix/{M.m.p} exactly as the law, the skill and the real branches spell them"
- subject:
    kind: code
    ref: dadaia_workspace/features/chokepoints/service.py#_PUSHABLE_BRANCH
  change: "invert the push policy: feature/{M.m.p} becomes the pushable ref (to open its PR); direct pushes to develop and main are refused"
- subject:
    kind: code
    ref: dadaia_workspace/features/chokepoints/service.py#push_gate_decision
  change: "branch policy step refuses develop/main direct pushes and any ref outside feature/{M.m.p} (plus operator-requested kinds per grill-me Q1); the security-verdict delta follows the grill-me Q3 decision (PR diff feature->develop)"
- subject:
    kind: cli
    ref: ci push-gate-check
  change: "help text and decision messages state the v2 push policy; the corrected-command hint names the PR path instead of a develop push"
- subject:
    kind: doc
    ref: memory/quality-assurance.md#CI
  change: "ci.yml pr-source-guard kept for main<-develop; add a develop-accepts-feature-only guard (PR to develop must come from feature/{M.m.p}); CI triggers extend to feature/* pushes per grill-me Q4; atom rewritten to the v2 branch model"
- subject:
    kind: doc
    ref: memory/product/sdd/sdd-gate-v3.md#Git Chokepoints
  change: "push-boundary policy rewritten to v2 (feature pushable, develop/main PR-only, no `v` prefix); atom points to the DADAIA.md gitflow section instead of restating it"
- subject:
    kind: doc
    ref: memory/product/sdd/sdd-bug-backlog-governance.md#Branches And Stage Placement
  change: "branch model restatement collapses to a pointer to the DADAIA.md gitflow section; stage placement rows updated to feature-from-main and PR-only develop"
- subject:
    kind: doc
    ref: memory/product/sdd/sdd-bug-backlog-governance.md#Merge Cadence
  change: "two milestones re-expressed under PR-only develop per grill-me Q2 (PR at (a) and (b), or only at ship)"
- subject:
    kind: doc
    ref: memory/architecture.md#Agent Surface
  change: "the eight agents' branch/push rows (ai-engineer, project-manager, qa-engineer, software-engineer, code-reviewer, security-reviewer, product-engineer + registry.json mandates) collapse to one pointer line each into the DADAIA.md gitflow section / dadaia-gitflow skill"
```

### rules-skills-governance-map
- **Title:** rules-skills-governance-map — a JSON-controlled map from DADAIA.md rule sections to the skill(s) that operate them, declared in constitution.md, linted for duplication
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** We force agent behaviors with a set of rules (always-on, concentrated in `DADAIA.md`) and a set of skills (on-demand operational protocols). To keep that set manageable and governed there must be an explicit **map of rule sections → skills**. Gitflow is the first example (the `DADAIA.md` gitflow section ↔ `dadaia-gitflow`, backlog `gitflow-contract-v2-consolidation`), but the map applies to every behavior the workspace enforces. This is core/architectural and must live in `constitution.md` of dadaia-workspace (the scaffold `dadaia_workspace/public/scaffold/constitution.md`, as a new core-law section). The map itself is controlled through a JSON owned by dadaia-workspace (location to decide in definition — e.g. under `dadaia_workspace/public/entities/` next to `registry.json`, or `dadaia_workspace/public/schemas/` with a versioned schema). Goal: harmony between what is a rule and what is a skill, no duplication, no two skills repeating the same content, governance over the core rules and skills. Each `DADAIA.md` section maps to exactly 1 skill (2 only if mapped and justified in the map itself). Candidate initial rows from the 2026-08-23 scan (`.dadaia/tmp/claude/20260823/gitflow-inventory.md` §F): §gitflow ↔ `dadaia-gitflow`; §6 tests ↔ `dadaia-test-stewardship`; §5 tasks ↔ `dadaia-task-manager`; §5 backlog ↔ `dd-backlog-definition`; §4 emission ↔ `dadaia-handoff-emitter`; §7 library surface ↔ `dadaia-workspace-doctor`; CLI ↔ `dadaia-cli`; §1 Arm B ↔ `dd-bug-registration` / `dd-bug-fix`; §5 releases ↔ `dd-release-definition` / `dd-release-implement` / `dd-release-closure`. A lint (extending `dadaia_workspace/public/scripts/lint-skill-collisions.py` or a new sibling script run at projection time, `--self-test` proving both directions) must fail when a `DADAIA.md` section has no mapped skill, a skill is mapped to no section, or two skills restate the same section's content. `DADAIA.md` §9 ("where to look next") points to the map rather than listing skills ad hoc.
- **Provenance:** operator request, 2026-08-23, same session as `gitflow-contract-v2-consolidation`; depends-on / relates-to `gitflow-contract-v2-consolidation` (first consumer of the map)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/scaffold/constitution.md#rules-to-skills-governance-map
    surface: new
  change: "new constitution section declaring the rules->skills map as core law: every DADAIA.md section maps to exactly one operating skill (two only when the map row justifies it), the JSON map is the single controlled source, and the lint is the enforcer"
- subject:
    kind: doc
    ref: dadaia_workspace/public/entities/rules-skills-map.json
    surface: new
  change: "new JSON map owned by dadaia-workspace (path settled in definition: entities/ or schemas/) — rows of {dadaia_section, skills[], justification}, versioned, with its JSON schema; seeded with the candidate rows from the 2026-08-23 scan"
- subject:
    kind: code
    ref: dadaia_workspace/public/scripts/lint-skill-collisions.py#DECLARED_OVERLAPS
  change: "extend this projection-time lint (or add a sibling run alongside it) to read the JSON map and fail when a DADAIA.md section has no mapped skill, a skill maps to no section, or two skills restate the same section's content; --self-test proves both directions"
- subject:
    kind: catalog
    ref: agentic-entities
  change: "the rules->skills map becomes a governed entity set next to personas/behaviors/rules: registry and panel Entities surface expose which skill operates which DADAIA.md section"
- subject:
    kind: doc
    ref: memory/product/agents/agentic-entities.md#The derivation law
  change: "derivation law gains the rule->skill mapping invariant (each DADAIA.md section -> one operating skill, duplication forbidden, lint-enforced)"
- subject:
    kind: doc
    ref: memory/architecture.md#Public assets
  change: "DADAIA.md section 9 and the public-assets architecture note point to the JSON map as the authority for which skill operates which rule section"
```

### core-skills-consolidation
- **Title:** core-skills-consolidation — fewer, representative core skills: dd-release-closure folded into dd-release-implement; the four AI-harness skills collapsed into one well-built skill with attachments; every core skill re-authored to the writing-for-agents pattern (short steps + disclosed reference)
- **Opened:** 2026-08-23
- **Status:** candidate
- **Description:** The official development-lifecycle skills of dadaia-workspace are **six**: `dd-backlog-definition` (how to register backlog, `specs/backlog`), `dd-release-definition` (pure SDD: SPEC/PLAN/TASKS), `dd-release-implement` (how to implement the release: implement, tests, gates, git, and — now — closure), `dd-bug-registration` (register bugs, `specs/bugs`), `dd-bug-fix` (fix registered bugs), `dd-audit-project` (audit a project and write the audit report, `specs/audits`). `dd-release-closure` is without doubt part of `dd-release-implement` and must be folded into it: implement defines how to implement a release, the gates for commit/push/PR, and the closing of the release. The AI skills `ai-harness-codex`, `ai-harness-claude-code`, `ai-context-engineering` and `harness-primitives` must become **ONE** well-made skill — a skill is a folder and may carry attachment files and reference links; optimize the content; do NOT rewrite Codex/Claude Code documentation inside it, link to it. Operator phrasing (2026-08-23): "we don't need this much skill slop." **Prerequisite done by the session:** cloned https://github.com/mattpocock/skills as spec context `mattpocock/skills` (the skills reference clone (`mattpocock/skills`)) to learn how a skill is built properly. **Learned pattern — acceptance guidance for every re-authored core skill:** `SKILL.md` is short (repo median 74 lines, max 140) — ordered steps each ending on a checkable completion criterion, plus in-file reference only when every branch needs it; everything else is disclosed to sibling files behind pointers (`REPORT-FORMAT.md`, `SKILL-MECHANICS.md`-style attachments); model-invoked vs user-invoked is an explicit choice (`disable-model-invocation: true` strips the description from agent reach); dependencies are operative "Call the Skill tool with \"<name>\"" instructions, never cross-folder links; single source of truth per meaning, no caching of what the environment answers; positive phrasing over prohibitions; leading words; prune no-ops and sediment. Reference: `mattpocock/skills/skills/productivity/writing-for-agents/SKILL.md` + `SKILL-MECHANICS.md`, `mattpocock/skills/.agents/invocation.md`. `dadaia-grill-me` is being uplifted right now by `ai-engineer` to that pattern (rounds over a design tree / frontier; facts are the agent's job, decisions the operator's) as the first worked example — the release must ratify/land it. Relates to `rules-skills-governance-map` (the consolidated skill set is what the map governs) and to `gitflow-contract-v2-consolidation` (`dd-release-implement` absorbs the git/gate rows by pointer to `dadaia-gitflow`). **Scope boundary:** core skills under `dadaia_workspace/public/skills/`; instance-private skills (godot-*, etc.) are out of scope. **Operator addendum (2026-08-23): same strategy as gitflow — this is now CORE of dadaia-workspace.** Every always-on rule lives as a section of `DADAIA.md` and is mapped to the skill that operates it. The consolidated skill set must therefore land with its map rows: each of the six lifecycle skills and the single AI-harness skill maps to exactly one `DADAIA.md` section (e.g. §1 Arm A/B ↔ the `dd-*` family rows; §2 "ai-engineer alone invokes…" ↔ the one AI skill), and no skill exists without a section nor a section without its skill. The map itself is `rules-skills-governance-map`; **this entry depends on it.** Open for the mandatory grill-me: the name of the consolidated AI skill folder; the exact SKILL.md length ceiling the lint enforces; whether `harness-primitives`' agent-wide literacy survives as the short top layer of the one skill or as a pointer from each agent.
- **Provenance:** operator request, 2026-08-23, same session as `spec-context-associated-repos`, `gitflow-contract-v2-consolidation` and `rules-skills-governance-map`; reference context `mattpocock/skills` (cloned this session as the worked pattern source); depends-on `rules-skills-governance-map` (the consolidated set lands with its section→skill map rows)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-release-implement/SKILL.md
    surface: new
  change: "absorb dd-release-closure in full (CLOSURE template, memory-update protocol, evidence triples, disposition sweep, archive move) and re-author to the writing-for-agents pattern: short ordered steps ending on checkable criteria, closure/gitflow detail disclosed to sibling attachment files, git/gate rows by pointer to dadaia-gitflow"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dd-release-closure/SKILL.md
    surface: new
  change: "retire — delete the folder; every pointer (DADAIA.md, dd-backlog-definition, dd-release-definition, dd-audit-project, dadaia-gitflow, agents, memory atoms) repointed to dd-release-implement"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/ai-harness/SKILL.md
    surface: new
  change: "new single consolidated AI-harness skill folder (name to settle in grill-me) replacing ai-harness-codex, ai-harness-claude-code, ai-context-engineering and harness-primitives: one short SKILL.md plus attachment files and links to the official Codex / Claude Code documentation, never a rewrite of it; the four source folders are retired"
- subject:
    kind: doc
    ref: dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md
    surface: new
  change: "ratify and land the ai-engineer uplift to the writing-for-agents pattern (rounds over a design tree / frontier, facts are the agent's job, decisions the operator's) as the first worked example; every remaining core skill under dadaia_workspace/public/skills/ is re-authored to the same pattern"
- subject:
    kind: code
    ref: dadaia_workspace/public/scripts/lint-skill-collisions.py#main
  change: "enforce the pattern at projection time: a maximum SKILL.md line count per core skill and no duplicated meaning across two skills; --self-test proves both directions; DECLARED_OVERLAPS loses the retired ai-harness-* family row"
- subject:
    kind: doc
    ref: memory/product/agents/agentic-entities.md#Registry
  change: "entities registry (dadaia_workspace/public/entities/registry.json) skill inventory and the projection manifest reflect the consolidated set: six dd-* lifecycle skills, one AI-harness skill, no dd-release-closure"
- subject:
    kind: doc
    ref: memory/product/distribution/public-asset-distribution.md#Usage flow
  change: "stage/install/doctor project the consolidated skill folders with their attachment files to every harness target (.claude/, .agents/, .codex/, .kimi-code/) and stop projecting the retired folders"
- subject:
    kind: doc
    ref: memory/product/agents/agent-orchestration.md#Operating Rules
  change: "DADAIA.md §2 line 'ai-engineer alone invokes the ai-harness-* and ai-context-engineering skills — every other agent uses harness-primitives' rewritten to name the one consolidated skill; DADAIA.md §9 skills row lists the six dd-* lifecycle skills and points to the consolidated set"
- subject:
    kind: doc
    ref: dadaia_workspace/public/data/DADAIA.md#§9 Where to look next
    surface: new
  change: "skills row rewritten as the map: declare the section->skill rows for the six lifecycle skills + the AI skill (each maps to exactly one DADAIA.md section; no skill without a section, no section without its skill), as governed by rules-skills-governance-map"
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
