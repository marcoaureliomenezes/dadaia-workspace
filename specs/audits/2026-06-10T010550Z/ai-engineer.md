# AI-Surface Audit — dadaia-workspace

- **Auditor:** ai-engineer (5-agent full-workspace audit; synthesis by project-auditor)
- **Date:** 2026-06-10T010550Z
- **Source of truth audited:** `repos/dadaia-workspace/dadaia_workspace/public/` (agents, skills, rules, workflows, data/AGENTS.md, scripts, plugins) + the live hook implementations in `dadaia_workspace/hooks/` and `features/spec_context/gate_policy.py` / `lease.py` (the actual enforcement the surface describes)
- **Instance cross-checked:** `.claude/settings.json`, `.codex/hooks.json`, `.dadaia/tmp/` sentinels, `.dadaia/sessions/`
- **AI-surface score: 5 / 10**

Scoring rationale: text quality is high-polish, mostly tables, with several genuinely
honest self-corrections (workspace-protocol §6 admits the allowlist is unenforced; the
ctx-inject dispatcher preflight truthfully states workflows are not auto-spawned; both
workflow files carry honesty notes). But the central audit question — "is claimed
enforcement deterministic?" — fails for most of the claims: the gate's classifier
makes its ADDITIVE/MEMORY/FROZEN classes unreachable in any law-abiding workspace,
the lease liveness model is unsound, three documented enforcement mechanisms are
theater, and the surface restates the same laws divergently across ≥5 files with
visible drift.

---

## 1. Determinism table (claimed enforcement → actual mechanism → verdict)

| # | Claimed enforcement | Where claimed | Actual mechanism (code) | Verdict |
|---|---|---|---|---|
| D-1 | SDD gate: "Production edits require an active approved release… SPEC/PLAN/TASKS `**Status:** Aprovado`… task reserved `[-]`" | `public/data/AGENTS.md` §"SDD Gate"; `dadaia-task-manager/SKILL.md` ("O gate v3 procura tasks `[-]` recursivamente…"; "a presença de pelo menos uma task `[-]` … libera o gate") | `hooks/sdd_gate.py` + `gate_policy.evaluate()` check **none of this**. No read of SPEC/PLAN/TASKS status, no `[-]` marker grep, no release-approval check. Only: path class → lease / memory-phase / frozen / protected. Neither the Python hooks nor `public/scripts/sdd-spec-gate.sh` reference TASKS.md at all. | **THEATER** (the approval/marker portion). Status + marker discipline is persona-discipline only. |
| D-2 | Single-session lease (the "only deterministic lock") | `backlog-ownership.md`; `workspace-protocol.md` §6; `lease.py` docstring; ctx-inject preflight | O_EXCL CAS acquire is real (`lease.py:acquire`), PATH-first ctx slug fixed (sdd_gate.py:44-63). BUT liveness = 120s TTL renewed **only** when the gate evaluates a MUTATING Edit/Write (`gate_policy.py:147`); the dedicated heartbeat hook `sdd_post_gate.py:38` no-ops unless `DADAIA_SESSION_ID` env is set — **it is not set in real harness sessions** (verified live: env empty, hook silent). A holder running reads/tests >120s goes stale → foreign `acquire` silently TAKEOVERs (`lease.py:352-353`). Matches the reproduced lease-theft CRITICAL. | **WEAKLY DETERMINISTIC / UNSOUND** — deterministic acquire, theft-prone liveness. |
| D-3 | ADDITIVE never-blocked paths (bugs/backlog/audits "never gate-blocked", "no excuse to defer") | `bug-registration-guardrail.md`; `backlog-ownership.md`; root AGENTS.md | `gate_policy.py:37-44` ADDITIVE prefixes are **workspace-root-relative** (`specs/bugs/`…); `classify_path` (line 94) matches `repos/` **first** for any in-repo path. The same rules mandate bugs go to `repos/dadaia-workspace/specs/bugs/` → classified **MUTATING**, lease required. Worse: the root-whitelist law forbids a root-level `specs/` dir entirely, so the `specs/*` ADDITIVE/MEMORY/FROZEN branches are **unreachable in any compliant workspace**. | **THEATER** for the documented (in-repo) bug/backlog/audit locations. |
| D-4 | Memory phase-lock ("write-locked except product-engineer in DEFINITION/CLOSURE") | `workspace-protocol.md:45`; root AGENTS.md §Memory; `dadaia-step0-memory-bootstrap:97` | Same root-relativity defect: `specs/memory/` prefix (`gate_policy.py:45,90`) never matches `repos/<slug>/specs/memory/…` — those writes are plain MUTATING-lease, no phase check. The phase gate code (`gate_policy.py:137-143`) is dead for every real (in-repo) context. | **THEATER** for in-repo specs (the only legal location). |
| D-5 | FROZEN `specs/_archive/` read-only | gate header comments; specs rules | `gate_policy.py:46,92` — same unreachable-prefix defect. | **THEATER** in-repo. |
| D-6 | PROTECTED `.dadaia/sessions/` fail-closed (SEC-01) | `gate_policy.py:14-18`; lease docs | Real and evaluated first (`gate_policy.py:128-129`, `sdd_gate.py:108-120`). Workspace-root path so prefix actually matches. But: only fires on Edit/Write/apply_patch — `_common.WRITE_TOOLS` excludes `Bash`, so `bash -c 'echo x > .dadaia/sessions/runtime/ctx.ptr'` bypasses it. ctx_inject.py:99-108 itself writes `.ptr` files outside the gate. | **DETERMINISTIC-NARROW** (file-tools only; Bash bypass; no doctor backstop cited for forgery). |
| D-7 | Root-whitelist law "enforced deterministically by the root-whitelist-gate.sh PreToolUse hook" | root AGENTS.md §"Workspace Root Law"; `tmp-file-guardrail.md` | `hooks/root_whitelist.py` — real, blocks new direct root children not in the 9-entry whitelist, honors `root_exceptions.txt`. Fires only on Write/Edit-family tools (line 67); any Bash-side `touch`/`npm init` at root bypasses it. Subdirectory writes unguarded (by design). | **DETERMINISTIC-NARROW** (Edit/Write only; Bash bypass). |
| D-8 | tmp-file guardrail ("Enforcement: Before writing… STOP and redirect") | `tmp-file-guardrail.md` §Enforcement | **No hook exists** that checks temp-file landing zones. Nothing blocks a `.png` written into `repos/` or a stray script in `specs/`. Root-whitelist covers only root-level entries. | **DISCIPLINE** only, despite a section literally titled "Enforcement". |
| D-9 | ctx-inject context injection, once per session | `ctx_inject.py` docstring; runtime_config comments | Real and correct: session-keyed sentinel `.dadaia/tmp/ctx-inject-fired-<sid>` guards the entire payload (`ctx_inject.py:152-163`); sentinels verified present on the live instance. Payload ≈ **33.5 KB** (tech-stack.md 8.4 KB + raw `catalog.json` 25.1 KB) + preflight — per **session**, not per prompt, in the current Python port. | **DETERMINISTIC** — works as documented. See §4 for size/bloat findings. |
| D-10 | `bind --mode` write/read session modes | `cli/commands/context.py:262-344` (`eval $(dadaia context bind … --mode …)`) | `DADAIA_MODE` reaches the hook only if the harness process inherited the eval'd shell env; even then `sdd_gate.py:127` passes it to `lease._new_record` where it is **stored as metadata and never read by any decision** (no branch in `gate_policy.evaluate` or `lease.acquire` consults `mode`). | **THEATER** — confirmed: mode is a label, not a control. |
| D-11 | Per-persona `paths.write_allowlist` | persona frontmatter; `ai-harness-claude-code` SKILL §7 F8: "The write-allowlist is enforced by dadaia's PreToolUse gate" | No hook reads any persona frontmatter; no harness can assert persona identity to a hook. `workspace-protocol.md` §6 says so honestly ("RULE-D … removed in 0.1.7 rc-3 … fail-open and never fired"). | **DISCIPLINE** — and F8 in the harness skill is a **false claim** (contradiction C-2). |
| D-12 | Heartbeat hook (PostToolUse) keeps session alive | `sdd_post_gate.py` docstring ("keep the active session alive") | Requires `DADAIA_SESSION_ID` env (`sdd_post_gate.py:38`); harnesses do not export it; it does not fall back to the stdin `session_id` the way `sdd_gate` does (`resolve_session_id` is available in `_common` but unused here). Verified: no `DADAIA_*` env in the live session → hook is a permanent no-op. | **THEATER** in practice (works only in a hand-exported shell). |
| D-13 | Pre-push CI gate ("Never push red") | `release-governance.md`; `public/scripts/pre-push-ci-gate.sh` | Real git pre-push hook (kept as .sh deliberately; documented in `hooks/__init__.py`). Deterministic where installed. | **DETERMINISTIC** (installation-dependent). |

**Cross-cutting bypass (applies to D-1..D-7):** both PreToolUse gates fire only on
`Edit|Write|apply_patch`-family tools (`_common.py:30`, `.codex/hooks.json` matcher,
runtime_config write_matcher). Every file mutation performed through `Bash` bypasses
the SDD gate, the root whitelist, and the PROTECTED fail-closed path. The
`ai-harness-claude-code` skill admits "PreToolUse is a guardrail, not a hard boundary"
— but the root AGENTS.md word "deterministically" and the SEC-01 "blocked
unconditionally" language overstate it.

---

## 2. Contradiction list

| # | Contradiction | Locations | Severity |
|---|---|---|---|
| C-1 | "Bug files are ADDITIVE (never gate-blocked)" vs in-repo bug writes classified MUTATING (lease-gated) | `public/rules/bug-registration-guardrail.md` ("Bug files are **ADDITIVE** — the SDD gate does not block them") + root AGENTS.md §Bug Registration vs `gate_policy.py:37-44,94` | CRITICAL — rule promises gate behavior the code inverts; this is the D1 lease-theft trigger family |
| C-2 | Write-allowlist enforcement: "enforced by dadaia's PreToolUse gate" vs "NOT gate-enforced (RULE-D removed 0.1.7 rc-3)" | `public/skills/ai-harness-claude-code/SKILL.md` §7 (F8 callout) vs `public/rules/workspace-protocol.md:46-48` §6 and `ai-context-engineering/SKILL.md` §5 ("NOT gate-enforced as of 0.1.7 rc-3") | HIGH — the compiled harness protocol (restricted to ai-engineer, the authority on this exact question) carries the stale claim |
| C-3 | Workflow inventory: "No workflow-file rows ship in the default installation; release-ship and audit-fanout are added in v0.1.9 and listed here once their files exist" vs "exactly 2 workflows in the default installation" — and both files exist | `public/agents/project-manager.md:120-121` vs `public/skills/project-orchestration/SKILL.md:39-46` + `public/workflows/*.workflow.md` (present) | MEDIUM — PM's own router table denies assets it owns |
| C-4 | Memory write phases: "CLOSURE phase" only vs "DEFINITION and CLOSURE phases" | `public/skills/dadaia-workspace-spec-navigator/SKILL.md:80-81` vs `workspace-protocol.md:45`, `dadaia-step0-memory-bootstrap/SKILL.md:96-97`, root AGENTS.md §Memory | MEDIUM — same law, three phrasings, one wrong |
| C-5 | Gate checks task markers: "O gate v3 procura tasks `[-]` recursivamente… a presença de pelo menos uma task `[-]` … libera o gate" vs gate code that never reads TASKS.md | `public/skills/dadaia-task-manager/SKILL.md` §"Onde TASKS.md vive" and §"O gate me bloqueou" vs `hooks/sdd_gate.py` + `gate_policy.py` + `public/scripts/sdd-spec-gate.sh` (zero TASKS.md references) | HIGH — the most-loaded implementer skill describes a gate generation that no longer exists |
| C-6 | Report contract inside one persona: "After completing a task, write an HTML report to…" (mandatory) vs "handoff-first; HTML only on `--with-report` or next_handoff.agent == human" | `public/agents/ai-engineer.md:351` vs `:367`; same pattern in other personas ("Reports are HTML files" header blockquote vs the §4 pointer) | MEDIUM — every persona opens with an HTML-report mandate its own footnote rescinds |
| C-7 | Handoff emitter requires an HTML report ("Never emit a handoff for a report that does not yet exist on disk"; Step 1 = sha256 of the HTML) vs protocol default of handoff-only emission (no HTML) | `public/skills/dadaia-handoff-emitter/SKILL.md` §Guardrails + 3-step protocol vs `workspace-protocol.md` §4 | HIGH — the default path (handoff without HTML) is unexecutable under the emitter skill's own rules; `artifact.content_hash` of a nonexistent file is undefined |
| C-8 | Model-tier tables cannot produce the fleet's actual tiers: tables list only opus-4-8 / sonnet-4-6 / haiku; 5 of 9 core personas are `model: claude-fable-5`, zero are sonnet or haiku; haiku id inconsistent ("claude-haiku (when supported)" vs "claude-haiku-4-5") | `public/agents/ai-engineer.md:198-200` vs `public/skills/ai-context-engineering/SKILL.md:264-266` vs `grep '^model:' public/agents/*.md` | MEDIUM — tier-selection protocol is the surface's own cost-governance law and is stale (known model-catalog-drift bug family) |
| C-9 | "The enforced gate is `public/scripts/sdd-spec-gate.sh` (bash…)" vs "the bash governance hooks are dead on stock Windows… reimplemented here as a Python package the harness invokes directly" + live wiring invoking `python -m dadaia_workspace.hooks.*` | `features/spec_context/gate_policy.py:3-8` vs `hooks/__init__.py:1-8`, `.claude/settings.json`, `.codex/hooks.json` | MEDIUM — the executable-spec module misidentifies which artifact enforces |
| C-10 | Leaf-agent dispatch: orchestration table's "Dispatches to" column (product-engineer→software-architect, software-engineer→qa-engineer, ai-engineer→security-reviewer/code-reviewer, security-reviewer→implementer) vs "a sub-agent never dispatches another" and the runtime fact that subagents cannot nest-dispatch | `public/skills/project-orchestration/SKILL.md:21-31` vs `public/agents/project-manager.md:140`; runtime constraint confirmed across releases (v0.1.7/v0.1.9 evidence) | HIGH — promises orchestration the harness cannot execute (see §3) |
| C-11 | Hook ownership: ai-engineer claims "Hook + gate scripts under `dadaia_workspace/public/scripts/` (shell/Python)" and "Hooks execute with the workspace's permission; treat any new hook as privileged-code review" — but the live hooks are `dadaia_workspace/hooks/*.py` production Python, which ai-engineer is forbidden to write ("never write Python") | `public/agents/ai-engineer.md` §Scope + §Security vs `hooks/__init__.py`, live wiring | HIGH — the actual enforcement surface has no owner in the AI surface's ownership model; the assets ai-engineer owns (`public/scripts/*.sh`) are the dead pair of a dual implementation |
| C-12 | Generated Claude hook wiring uses `"matcher": ""` (fires on every tool, incl. Read/Grep/Glob) vs the F2 law in the product's own harness skill: "Scope write-gates to `Edit|Write|MultiEdit|NotebookEdit`… an empty matcher fires on every tool — not a safe default" | `infrastructure/runtime_config.py:62-99` + live `.claude/settings.json` vs `public/skills/ai-harness-claude-code/SKILL.md` §5 F2; Codex side (`runtime_config.py:138`) is correctly scoped | HIGH — the product violates its own compiled protocol on one of two harnesses; cost = 2 Python interpreter startups per tool call (PreToolUse) + 1 (PostToolUse) on every Read/Grep/Bash |
| C-13 | Root AGENTS.md operating default "Language: … default to English" vs `dadaia-task-manager/SKILL.md` body substantially in Portuguese (loaded by every implementer on every task cycle) | `public/data/AGENTS.md` §Operating Defaults vs `public/skills/dadaia-task-manager/SKILL.md` | LOW — also a consistency invariant (I-fleet) violation; the PT→EN purge (v0.1.4.1) missed it |
| C-14 | "an idle-but-alive holder renews its heartbeat on every PreToolUse" vs renewal only occurring on MUTATING-classified Edit/Write evaluations (and the PostToolUse heartbeat being env-gated to a no-op) | `lease.py:18-19` docstring vs `gate_policy.py:145-156` + `sdd_post_gate.py:38` | HIGH — the docstring describes the liveness model the theft bug disproves |

---

## 3. Agent cooperation model — what the harness can actually execute

**Honest parts (credit where due):**
- ctx-inject dispatcher preflight (`hooks/ctx_inject.py:31-52`) explicitly states:
  "this harness does NOT auto-spawn subagents from static .codex/.claude workflow
  files. Workflow files are reference docs; explicit dispatcher/operator fan-out is
  required." This is correct and is injected every session.
- Both workflow files carry honesty notes in their descriptions ("Claude Code and
  Codex do not auto-load workflow files at runtime").
- `project-manager.md:71-75` "A-2 enforcement (honest)" correctly states sub-agent
  topology is a convention the gate cannot see.
- `ai-harness-codex/SKILL.md` §5 correctly states declarative topology does not
  auto-execute.

**Broken promises:**
1. **Nest-dispatch in the inventory table** (C-10). `project-orchestration:21-31`
   gives every leaf a "Dispatches to" target. Subagents do not get the Agent tool
   and cannot nest-dispatch (operationally confirmed in v0.1.7/v0.1.9: "subagents
   can't nest-dispatch; coordinator-driven"). The column describes a handoff-routing
   *intent*, but reads as executable dispatch. "Leaf specialists do not chain further
   dispatch unless the operator explicitly approves it" (`project-orchestration:53-54`)
   implies a capability that does not exist at any approval level when the leaf runs
   as a subagent.
2. **PM-as-subagent ambiguity.** The whole model (PM holds the lease, dispatches
   PE/SE as sub-agents) only works when project-manager runs as the **top-level
   session agent**. Nothing in `project-manager.md` or `project-orchestration` states
   this precondition; a PM dispatched via the Agent tool by a default session is a
   subagent and cannot dispatch anyone. The model is executable, but only in one
   topology that the text never names.
3. **Review fan-out mechanics.** §2 "Review/QA Fan-Out" has PM dispatch validators
   and route rework loops across multiple agents and commits — a multi-turn,
   multi-session choreography. Within one session this works (PM top-level,
   sequential Agent calls); the text's "the rework loop continues until every
   required validator approves the same implementation commit" spans sessions with
   no state carrier other than handoff JSONs, which nothing re-reads automatically.
   Discipline, not mechanism — acceptable, but should be labeled as such the way A-2 is.
4. **Persona frontmatter is decorative to the runtime.** `tier`, `activity_class`,
   `lease_relationship`, `gate_role`, `input_contract`, `paths.write_allowlist` are
   dadaia conventions ignored by both harnesses (correctly documented in F8's first
   half). They are read by tooling/tests only. Fine — but C-2's false enforcement
   claim makes a reader believe otherwise.

---

## 4. Context injection (ctx-inject) — measured

| Property | Finding |
|---|---|
| What is injected | `[<context>]` line + 22-line dispatcher preflight + `tech-stack.md` verbatim + `product/catalog.json` **raw JSON** verbatim |
| Size (live instance, dadaia-workspace ctx) | tech-stack.md 8,410 B + catalog.json 25,106 B ≈ **33.5 KB ≈ 8–9k tokens** |
| Frequency | Once per logical session — sentinel `.dadaia/tmp/ctx-inject-fired-<sid>` guards the entire payload (`ctx_inject.py:152-163`); verified working (sentinels on disk). The "~34KB per prompt" failure mode is fixed in the current Python port; Claude wiring still *invokes* the hook every prompt (matcher-less UserPromptSubmit) but it no-ops after the first. |
| Dedup correctness | Session-id resolution: env overrides → stdin `session_id` → `"workspace"`. Falls to a shared `"workspace"` sentinel when no id is resolvable — two id-less sessions would dedup against each other (first wins, second gets **nothing**). Sentinels are never GC'd and live in `.dadaia/tmp/` where retention policies may delete them mid-session (re-injection, benign) — both edges minor. |
| Context resolution | `DADAIA_CONTEXT` env → first-ALIVE in `spec_contexts.json` (`ctx_inject.py:64-77`). Correct per protocol; no nag/halt (good). First-ALIVE ordering is registry-order dependent — same family as the resolved gate-cross-context bug, here harmless (injection only). |
| Bloat finding | `catalog.json` is injected as **raw machine JSON** (25 KB, ~75% of payload) including full `summary` fields, when the step0 skill tells agents to use `tldr` for first-pass and self-pull atoms on demand. Injecting a tldr-only digest would cut the session bootstrap by ~60–70%. The hook also duplicates what `dadaia-step0-memory-bootstrap` instructs agents to self-pull — double-loading for any agent that follows the skill literally after injection (the skill's precondition check mitigates, when followed). |
| Side effect | `ctx_inject.py:99-108` writes `.dadaia/sessions/runtime/<session_id>.ptr` — a hook writing into the PROTECTED prefix that the SDD gate fail-closes for agents. Legitimate (hooks ≠ tool writes) but undocumented in the PROTECTED story, and it writes `<session>.ptr` while the lease consumes `<ctx>.ptr` — two pointer namespaces in one directory, neither cross-referenced. |

---

## 5. Slop / bloat / hygiene list

| # | Item | Location | Note |
|---|---|---|---|
| S-1 | `__pycache__/` with `.pyc` files inside canonical public source | `public/scripts/__pycache__/*.cpython-312.pyc` | Violates the workspace's own repo-cleanliness law inside the asset tree that ships to all consumers |
| S-2 | Dead dual implementation: 4 shell hooks retained as "behavior-for-behavior ports" requiring hand-maintained byte-parity ("block reason byte-identical… parity contract T-018-15/16") while only the Python side is wired | `public/scripts/{sdd-spec-gate,sdd-post-gate,root-whitelist-gate,ctx-inject}.sh` vs `dadaia_workspace/hooks/` | 600 shell lines of unexecuted-on-this-instance policy that MUST mirror the Python or silently lie; gate_policy.py:3 already drifted (C-9) |
| S-3 | Same law restated in N files: root whitelist table (root AGENTS.md §Root Law + tmp-file-guardrail §whitelist, near-verbatim duplicate incl. the table); repo-cleanliness forbidden-dirs table (root AGENTS.md + tmp-file-guardrail, duplicated verbatim); SDD gate/marker law (root AGENTS.md, workspace-protocol §1/§3, dadaia-task-manager, dadaia-workspace-spec-navigator §5, release-governance, project-orchestration §Forbidden) | rules/ + data/AGENTS.md | The drift in C-4/C-5 is the predicted failure of exactly this duplication; the surface's own `ai-context-engineering` §1 names this smell |
| S-4 | `dadaia-task-manager` body in Portuguese | `public/skills/dadaia-task-manager/SKILL.md` | C-13; highest-frequency implementer skill |
| S-5 | Always-on rule mass: 8 rules ≈ 365 lines load every session for every agent; `dadaia-workspace-dev-guardrail` (81 lines) is relevant only when editing lib assets — candidate for `paths:` scoping per the surface's own F1 law; `bug-registration-guardrail` (66 lines) could be ~25 with its tables kept | `public/rules/` | The product's own F1/F3 guidance applied to itself |
| S-6 | `product-engineer.md` at 539 lines is 3× the persona median and ~2.7× the PM persona; contains inlined protocol that `dadaia-release-definition` / `dadaia-release-closure` skills already carry | `public/agents/*.md` | Token-economy violation per the surface's own §1 (depth belongs in skills) |
| S-7 | Persona header blockquote "Reports are HTML files…" contradicting handoff-first (C-6) repeated across personas — N copies of a stale mandate | `public/agents/*.md` line ~57 | Fleet-wide single-line fix |
| S-8 | `repos.xlsx` binary in public data assets | `public/data/repos.xlsx` | Opaque binary in a privacy-gated public tree; not auditable by the privacy gate's text scanners |
| S-9 | Schema file named `handoff-v1.schema.json` whose `$id` is `handoff-v1.1`; emitter says literal "Always handoff-v1.1" while enum admits both | `public/schemas/handoff-v1.schema.json:3,12` | Minor naming confusion |
| S-10 | PM persona "Playbook routers" table partially restates `project-orchestration` playbooks it explicitly says it won't restate ("do not restate it here" — then 8 router rows + per-playbook entry agents duplicated) | `project-manager.md:116-140` vs `project-orchestration:226-296` | Mild; drift already visible (C-3) |
| S-11 | `ctx-inject` sentinel files accumulate unbounded in `.dadaia/tmp/` (no GC) | live `.dadaia/tmp/` (5+ sentinels) | Cosmetic |

---

## 6. Top 5 systemic defects

1. **Root-relative classifier makes most gate classes unreachable (D-3/D-4/D-5, C-1).**
   `gate_policy.classify_path` prefixes (`specs/bugs/`, `specs/memory/`,
   `specs/_archive/`, `specs/backlog/`, `specs/audits/`) are workspace-root-relative,
   but the root-whitelist law forbids a root `specs/` dir — so in every compliant
   workspace these classes never match and **everything under `repos/` is uniform
   MUTATING-lease**. "Bugs are never gate-blocked", the memory phase-lock, and the
   archive freeze are all theater for the documented in-repo locations. One defect,
   three broken promises, and the trigger of the live lease-theft reproduction.

2. **Lease liveness is unsound (D-2, D-12, C-14).** The only deterministic lock's
   liveness rests on a heartbeat that (a) as a PostToolUse hook no-ops without an
   env var no harness sets, and (b) via the gate renews only on MUTATING Edit/Write.
   Any holder doing >120s of reads/tests/Bash goes "stale" and a foreign session
   silently TAKEOVERs. The lease docstring claims renewal "on every PreToolUse" —
   false. The single lock the whole governance story leans on can be stolen from a
   live session.

3. **Documented enforcement ≠ implemented enforcement, in the agents' own
   instruction set (D-1, D-10, D-11; C-2, C-5).** The gate checks no SPEC/PLAN/TASKS
   status and no `[-]` markers; `bind --mode` is metadata never consulted; the
   write-allowlist is unenforced yet the ai-engineer-restricted harness skill (F8)
   claims the gate enforces it; the most-loaded implementer skill describes a
   marker-grepping gate that no longer exists. Agents are being trained on a
   security model that is ~70% discipline labeled as mechanism.

4. **Bash bypass with no backstop (cross-cutting).** All PreToolUse enforcement —
   including the SOLE fail-closed PROTECTED path guarding lease identity — keys on
   Edit/Write/apply_patch tool names. Every `Bash` file write bypasses every gate.
   The harness skill knows ("guardrail, not a hard boundary") but root AGENTS.md
   says "enforced deterministically" and SEC-01 says "blocked unconditionally", and
   no doctor backstop for `.ptr` forgery is wired or referenced.

5. **The surface violates its own compiled protocols and drifts where it
   duplicates (C-3, C-4, C-6/C-7, C-8, C-12, S-2, S-3).** Generated Claude wiring
   uses the empty matcher its own F2 law forbids; tier tables cannot produce the
   fleet's actual `claude-fable-5` assignments; the handoff-emitter's mandatory
   HTML-hash protocol is unexecutable under the handoff-first default; dual
   shell/Python hook implementations demand hand-kept byte parity and have already
   drifted; the same laws restated in ≥5 files disagree on phases, inventories, and
   gate behavior. The meta-irony: `ai-context-engineering` §1/§5 correctly names
   every one of these failure modes as the thing to never do.

---

## 7. Severity roll-up

| Severity | Count | IDs |
|---|---|---|
| CRITICAL | 2 | C-1/D-3 (classifier vs ADDITIVE promise), D-2/D-12 (lease theft via dead heartbeat) |
| HIGH | 8 | C-2, C-5, C-7, C-10, C-11, C-12, C-14, Bash-bypass (cross-cutting) |
| MEDIUM | 7 | C-3, C-4, C-6, C-8, C-9, D-7/D-8 overstated enforcement language, S-2 |
| LOW | 6 | C-13, S-1, S-4, S-8, S-9, S-11 |

**Contradiction count: 14** (C-1..C-14).

## 8. What is genuinely good (so synthesis keeps proportion)

- ctx-inject once-per-session dedup works and is verified live; the dispatcher
  preflight and workflow honesty notes are exemplary truthful-surface writing.
- `workspace-protocol` §6 and `backlog-ownership` honestly de-claim removed
  enforcement ("a lock with no key") — the surface CAN self-correct.
- PROTECTED fail-closed ordering, PATH-first ctx slug, O_EXCL CAS acquire, and the
  fail-open posture (never deadlock the flow) are correctly implemented per their
  contracts within the Edit/Write envelope.
- The persona fleet is structurally uniform (frontmatter schema, scope tables,
  `[SCOPE ERROR]` blocks) and the three ai-engineer skills are genuinely compiled
  protocol, not doc transcription — they just need their stale claims (F8, tier
  table) fixed and their own laws applied to the generator (matcher) and the rules
  tree (scoping, dedup).

— end of report —
