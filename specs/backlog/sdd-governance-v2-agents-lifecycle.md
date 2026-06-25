# EPIC — SDD Governance v2: specs taxonomy, agent roster, lifecycle gates (v0.1.15 candidate)

**ID:** FEAT-GOV-V2-01
**Reported:** 2026-06-12 (operator long-prompt `prompt.md` + grill session sess `fc45dd8c`;
refinement report: `.dadaia/reports/dadaia-workspace/project-manager/2026-06-12T023635Z-refine-specs.html`).
**Owner:** project-manager (curates) → product-engineer (release definition).
**Status:** CONSUMED — v0.1.15 delivered the Codex deterministic lifecycle foundation slice;
remaining governance-v2 roster/taxonomy/JSONL-bug scope must be picked by future backlog.
**Amends:** `deterministic-lifecycle-kernel-v0114.md` G6 (amended in place 2026-06-12 —
pre-push predicate now = security-APPROVE per push-cycle; alpha/rc trio model abolished).
**Touches (does not supersede):** `model-tier-efficiency-and-fast-tier-utilization.md`
(fast tier stays a separate P2 candidate; this entry re-tiers PM/ai-engineer and adds
researcher on sonnet).

---

## 1. Thesis

The SDD workspace graduates to governance v2: a canonical specs taxonomy with archive
flows for every artifact class, append-only event-sourced bug telemetry that feeds
root-cause analysis, a 10-agent roster with `project-manager` as a pure main-loop
coordinator and a new read-only `researcher`, and a single explicit gate ladder
(qa → commit, security → push, code-review → PR) that replaces the alpha-N/rc-N
segment model.

## 2. Grill decisions (2026-06-12, operator-confirmed — binding ADRs)

| ADR | Decision |
|---|---|
| 1 | **PM = main-loop persona, never spawned.** "project-manager conducts ALWAYS" is satisfied by the bound session adopting the PM persona on every prompt (rule + ctx-inject preflight), because the harness forbids nested subagent dispatch (constitution §9; audit 2026-06-10 ai-engineer.md). ALL fan-out happens from PM. `project-auditor` and `code-reviewer` obtain researcher support via the **PM relay**: they declare `research_requests` in their handoff; PM spawns researchers (max 5 parallel) and relays results back. |
| 2 | **Gate ladder replaces alpha-N/rc-N.** alpha-N abolished. qa-engineer gates every task-group commit; security-reviewer gates every push; each push = one **rc-N push-cycle**. The candidate→official boundary is the **operator's promotion decision** (not the push): promotion triggers code-review → PR → merge → deploy = official release → CLOSURE. Extension cycles after a push (more tasks → qa commits → security → push) increment rc-N. |
| 3 | **Bugs = event-sourced append-only JSONL.** Every line is an immutable event (`reported`, `resolved`, `superseded`, `deferred`, `rejected`, `archived`); a bug's status = its latest event by `bug_id`. No row is ever rewritten. Files named by date+hour, rotated at 1000 rows. |
| 4 | **Audit law = disposition-complete, not solve-all.** One audit report always generates a release. The first release after an audit must give EVERY finding an explicit disposition: `fixed` \| `superseded` (by a picked backlog item, recorded) \| `deferred`/`rejected` (written reason → backlog entry). The audit report is archived to `specs/audits/_archive/` only when all findings are dispositioned and the release is approved. Open bugs + open audits ALWAYS outrank plain backlog at release-definition pick. |
| 5 | **Models:** project-manager → `claude-fable-5`; ai-engineer → `claude-opus-4-8` (deliberate reversal of the v0.1.10 re-tier; role narrowed to research + backlog support); researcher (new) → `claude-sonnet-4-6`; PE/architect/qa/auditor stay fable-5; SE/security/code stay opus-4-8. Codex projections follow the existing registry mapping: fable-5 → `gpt-5.5`, opus-4-8 → `gpt-5.5`, sonnet-4-6 → `gpt-5.3-codex` (registry already correct — the work is **projection parity**, not registry change). Agent name stays `project-manager` ("project-coordinator" in the operator prompt = role description, not a rename). |
| 6 | **PM emits the research report.** "PM writes nothing" is scoped to **no specs, no production code**. Reports, handoffs, git operations (commit/push/PR — only PM does these), and spec-context management (`alive`/`dead`/`bind`) are coordinator duties. |
| 7 | **project-auditor owns the bug-trend audit** that gates bug archiving: clusters recurring root causes from the JSONL event history (researchers via PM relay), report → `specs/audits/`, findings get disposition-complete treatment (ADR-4); only then do `archived` events get appended and rotated files move to `specs/bugs/_archive/`. Trigger: operator request, or PM proposes when a 1000-row file rotates. |
| 8 | **Sequencing:** backlog written now (this file, ADDITIVE); release definition starts only after v0.1.13 closes. |
| 9 | **Kernel reconciliation:** `deterministic-lifecycle-kernel-v0114` keeps v0.1.14 with G6 amended to the new ladder; this governance release is **v0.1.15**. |

## 3. Workstreams

### W-A — Specs taxonomy + gate path classes

- Create `specs/backlog/_archive/` and `specs/audits/_archive/` (workspace + scaffold
  templates + consumer-onboarding path).
- Gate change (`features/spec_context/gate_policy.py`): classify
  `specs/backlog/_archive/` and `specs/audits/_archive/` (and `specs/bugs/_archive/`)
  as **FROZEN** for file-write tools — today the ordered ADDITIVE prefix match makes
  them silently writable. Archive moves are performed via Bash (`git mv`) by the
  archive flows, outside the gate envelope, as with `specs/_archive/` today.
- Backlog archive flow: when a backlog entry is consumed by a closed release, CLOSURE
  moves it to `specs/backlog/_archive/` (replaces today's keep-in-place re-status
  convention; historical entries migrate once).
- Audit archive flow per ADR-4.
- Doctor: new invariants — `_archive` dirs exist per class; consumed-but-unarchived
  backlog detection (supersedes the SPEC-DOC-031 wording); audit-without-disposition
  detection (an archived audit must reference its disposing release).

### W-B — Bugs: event-sourced JSONL

- **Format:** `specs/bugs/<YYYYMMDDTHH>Z.jsonl`; append-only; rotate when the active
  file reaches 1000 lines (next append opens a new date-hour file).
- **Event schema** (JSON Schema shipped under `.dadaia/agentic/schemas/` source):
  required `bug_id` (slug), `event` (reported|resolved|superseded|deferred|rejected|archived),
  `ts` (UTC ISO), `reported_by` (agent persona). `reported` events also carry: `title`,
  `severity` (LOW|MEDIUM|HIGH|CRITICAL), `surface` (command/feature), `component`
  (module path), `context` (repo slug), `tags[]`, `symptom`, `repro`, `expected`,
  `notes` (redacted). `resolved` carries `release`; `superseded` carries
  `superseded_by`; `deferred`/`rejected` carry `reason`. These are the filter/
  association fields the operator required.
- **CLI:** minimal `dadaia bugs` group — `append` (schema-validated, rotation-aware),
  `status` (fold events → current per-bug status), `stats` (counts by component/
  surface/severity/root-cause tag, feeding the bug-trend audit). Doctor SPEC-DOC-026
  is rewritten from markdown-frontmatter validation to JSONL schema + rotation +
  event-coherence validation (e.g. `resolved` without prior `reported` = error).
- **Migration:** one-time converter — existing `specs/bugs/*.md`: open bugs →
  `reported` events (fields mapped from frontmatter); closed/superseded bugs →
  full event history reconstructed (`reported`+terminal event) and the md files moved
  to `specs/bugs/_archive/`. Applies to the library repo (~31 files) and is shipped
  as a `dadaia specs upgrade` step for consumer workspaces.
- **Law:** rewrite `bug-registration-guardrail` rule (format section) for JSONL
  events; bug registration stays ADDITIVE for every agent; when the operator reports
  a bug verbally, PM dispatches product-engineer to append it.
- **Bug-trend audit workflow** (ADR-7): definition lives in the project-auditor
  persona + a skill section; output is a normal audit (so ADR-4 disposition law
  applies); archive step appends `archived` events + `git mv`s rotated files.

### W-C — Agent roster (9 → 10) + persona rewrites

- **New `researcher` persona** (restored, redesigned): model `claude-sonnet-4-6`;
  read-only tools (Read, Glob, Grep — no Write/Edit/Bash); spawned ONLY by PM
  (directly in Research lifecycle, or as relay fulfillment for project-auditor /
  code-reviewer `research_requests`); max 5 parallel; emits structured findings
  handoffs only. Constitution §14 roster becomes 10 core agents; plugin trio
  unchanged.
- **project-manager:** pure coordinator rewrite — main-loop persona (never spawned,
  ADR-1); identifies which of the 6 lifecycles a prompt targets (asks via grill-me
  when ambiguous); writes NO specs and NO code; sole performer of git push/PR and
  spec-context management; sole committer at gate approvals; conflict resolver in
  reviews (decides; worst case grills the operator); deadlock/race avoidance is its
  core technical duty; model → `claude-fable-5`.
- **product-engineer:** becomes owner + writer of `specs/backlog/**` (removes
  "consume PM-created backlog; you do not author backlog"); owner of every specs
  folder EXCEPT `specs/audits/` (auditor's output) and `specs/bugs/` append rights
  (any agent); constitution custody; always checks existing backlog before writing
  to avoid duplicates; memory update after release unchanged (§13).
- **project-auditor:** spawned by PM (no longer top-level Tier-1 self-dispatcher);
  loses direct Agent tool (nested dispatch impossible) — researcher needs go through
  the PM relay; writes ONLY `specs/audits/` reports + handoffs; gains the bug-trend
  audit duty (ADR-7).
- **ai-engineer:** narrowed to backlog-definition + research support (harness/
  Claude-Code/Codex/OpenCode behavior analysis: hooks, rules, skills, agents);
  model → `claude-opus-4-8` (ADR-5).
- **software-engineer:** sole implementer (code + tests); never implements outside
  specs; reviews TASKS for clarity BEFORE implementation starts (new release-definition
  step) and may REJECT unclear tasks back to PE via PM.
- **qa-engineer:** release-definition reviewer (test-architecture clarity of
  SPEC/PLAN, alignment with `quality-assurance.md`) + per-task-group commit gate
  (anti-slop implementation/test review, spec-vs-implemented drift measurement).
- **security-reviewer:** backlog/release-definition consult + the push gate
  (full-release security review, OWASP Top 10, leak scan, Dependabot zero-tolerance).
- **code-reviewer:** the PR/promotion gate — reviews the pushed release candidate
  against release definition + memory + diffs; researcher support via PM relay;
  Dependabot review duty.
- **Rules:** rewrite `backlog-ownership` (PE writes, PM curates pick/priority);
  update `release-governance` (W-D); update `workspace-protocol`; update the
  dispatcher-preflight text (PM-persona adoption, ADR-1).
- **Projection parity (operator-explicit):** all persona changes + the new researcher
  must project to **Claude, Codex, and OpenCode** (`dadaia public stage && install
  --target all && public doctor` exit 0). Codex models via the existing registry:
  fable-5/opus-4-8 → `gpt-5.5`, sonnet-4-6 → `gpt-5.3-codex`.

### W-D — Lifecycle law (constitution §7/§9/§10/§11 + rules)

- **Six lifecycles**, PM-coordinated, with the agent matrix the operator fixed:
  1. *Bug registration* — any agent appends; operator-reported → PE appends.
  2. *Backlog definition* — software-architect ALWAYS; ai-engineer/qa/SE/PE/security
     optional (PM decides); PE writes the backlog entry from the specialists'
     handoffs.
  3. *Release definition* — PE writes SPEC+PLAN (reading memory, constitution, open
     bugs/audits/backlog — bugs+audits first, ADR-4); software-architect + qa-engineer
     review (implementation + test architecture must be explicit; may evolve
     `architecture.md`/`quality-assurance.md`); after approval PE writes TASKS;
     software-engineer reviews TASKS for clarity; PM resolves review conflicts
     (decides, or grills the operator); definition ends with a commit.
  4. *Implementation + review* — SE implements task-groups; qa gates each group →
     PM commits + marks tasks done; all tasks done → security gate → PM pushes
     (= rc-N); operator may extend (new cycle) or promote: code-review gate → PM
     opens PR → merge → deploy → official release → CLOSURE (ADR-2).
  5. *Audit* — PM spawns project-auditor; researcher via relay; report →
     `specs/audits/`; always generates a release with disposition-complete treatment
     (ADR-4).
  6. *Research* — PM grills the demand, spawns researchers (≤5 parallel) +
     optional specialists; PM synthesizes and emits the report itself (ADR-6).
- **Gate ladder law** (replaces release-governance §"Release maturity"): qa → commit,
  security → push, code-review → PR; rc-N = push-cycles; promotion = operator
  decision. Supersedes the trio-at-rc-end law; coherent with kernel W1/G6-as-amended
  (the pre-push hook enforces the security-APPROVE half deterministically; v0.1.15
  writes the full law).
- **Mandatory grill** at intake stays (PM runs `dadaia-grill-me` on ambiguity, and
  always before a release definition).
- **Handoff schema:** add `research_requests[]` (ADR-1 relay) to
  `handoff-v1.schema.json` (or rev to v2 if additive change is not possible).

### W-E — Verification + docs

- pytest suites for: gate FROZEN sub-classes, bugs JSONL append/rotation/fold/
  migration, doctor invariants, handoff schema.
- `dadaia specs doctor` + `dadaia public doctor` exit 0 on the library instance after
  projection; panel renders bug stats (panel work minimal — reuse existing file
  browse; full bug-analytics UI is NOT in scope).
- Academy/docs touch only where law files are quoted (no new module in scope).

## 4. Acceptance seeds

1. **Roster:** `.claude/agents/researcher.md` + `.codex/agents/researcher.toml` +
   OpenCode projection exist post-install; researcher has read-only tools and
   sonnet-4-6/gpt-5.3-codex; PM=fable-5, ai-engineer=opus-4-8 across all three
   runtimes; `public doctor` exit 0.
2. **Relay e2e:** PM dispatches project-auditor; auditor handoff carries
   `research_requests`; PM spawns researchers and relays; audit report lands in
   `specs/audits/` referencing the researcher findings.
3. **Bugs:** appending the 1001st event opens a new date-hour file; `dadaia bugs
   status` folds events correctly (reported→resolved); doctor flags a `resolved`
   event with no prior `reported`; migration converts the library's md bugs with
   zero loss (every old bug queryable by `bug_id`).
4. **Gate:** file-tool write into `specs/backlog/_archive/` or
   `specs/audits/_archive/` → blocked FROZEN; `specs/bugs/*.jsonl` append → ADDITIVE
   allow.
5. **Ladder:** a release walked end-to-end under the new law — task-group commits
   each carrying a qa APPROVE handoff; push preceded by security APPROVE; PR preceded
   by code-review APPROVE; promotion recorded; CLOSURE archives the consumed backlog
   entry to `specs/backlog/_archive/` and the audit (if any) to
   `specs/audits/_archive/`.
6. **Law coherence:** constitution §7/§9/§10/§11/§13/§14, `backlog-ownership`,
   `release-governance`, `workspace-protocol`, `bug-registration-guardrail`,
   dispatcher preflight, and the PM/PE/auditor/ai-engineer/researcher personas all
   updated in the SAME release — zero doc-drift window; no remaining text says
   "alpha-N", "PM writes backlog", or "trio at rc end".

## 5. Out of scope (explicit)

- Fast-tier (haiku) assignments — stays in
  `model-tier-efficiency-and-fast-tier-utilization.md`.
- Kernel chokepoint hooks themselves — v0.1.14 (`deterministic-lifecycle-kernel-v0114`).
- Plugin packs (frontend/design/devops) — unchanged stubs.
- Panel bug-analytics UI beyond minimal stats rendering.
- OpenCode enforcement depth (per kernel ADR-G3 posture).
