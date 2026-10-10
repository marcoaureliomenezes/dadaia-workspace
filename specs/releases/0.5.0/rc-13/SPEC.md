# SPEC — Release: 0.5.0, candidate 13 — subagent model tiers

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-10
**Origin:** backlog:subagent-model-tiers; bugs:agent-model-templates-pin-superseded-sonnet-and-haiku

The candidate is also an operator demand. The source is the 2026-10-10 model-tiers grill: 9 questions and 11 decisions, frontier empty, report https://claude.ai/artifact/TtrHW8Hcd9kanXb1G5LaPT. The operator's words were: "o trabalho sobre os modelos de sub-agentes deve ser prioridade maxima. não podemos admitir custos desnecessários usando modelos improprios para as tarefas." The grill handoff expires, so every decision it carried is stated in this SPEC, and this SPEC is the only record of them. The skill-kernel candidate, which was planned as rc-13, now runs as rc-14 after this one. It keeps its definition and gets a delta check of its as-is review and PLAN against this candidate's base.

---

## Bug window review

rc-12 ran from its birth at 2026-10-09T13:34:13Z to its implementation at `ed7f76224` (2026-10-09T22:29:24Z) and its closure. One bug was found and fixed in rc-12. Twelve rc-11 fixes were rebuilt in rc-12 (FR3). Since rc-12's birth, three records were opened or closed, and none names an rc-12 task or fix in `caused_by`. One open record (below) correlates with the rc-12 fix.

| verdict | disposition | fixes |
|---|---|---|
| REBUILD — rc-14 (CP3) | `git show 2a8b5637f`: +7/−7, and no assert was edited. The fix replaces the SPEC-status read with `json.loads` of `_RELEASE.json`. That read is taken directly from `git show … check=False`, outside the release ledger's owner. It is a second parser of a ledger, which is a reach into another feature. The open bug `worktree-new-crashes-on-an-unreadable-release-state` (MEDIUM, correlates this fix) is that reach failing on a missing or non-object state. The structural home is rc-12's carried CP3, "one query API per ledger", now in rc-14. There, `_worktree_new.py` reads the phase through the release owner's API, and the open bug is fixed with it. This candidate does not touch `_worktree_new.py`. | `worktree-new-opens-a-job-outside-implementation` |
| KEEP — leaves the window | rc-12's REBUILD of the twelve rc-11 carry units (rc-12 FR3) produced no child bug: no record since rc-12's birth correlates with them or names them in `caused_by`. rc-11's two REBUILD rows (43 ids) leave the window on the same evidence, as rc-12's table required. | the twelve FR3 ids of rc-12 and the 43 ids of rc-11's REBUILD rows |

## 1. Problem

The library ships three personas and three model templates (ADR 0022, `dadaia_workspace/core/model_registry.py:147-166`). Every template pins an exact Claude model id. In `balanced`, the default, all three personas run Opus 5.5. The main thread can pass a cheaper model per dispatch, but compliance depends on memory. In the last 30 days of transcripts, 252 of 791 `dd-software-engineer` dispatches (32%) carried `model: sonnet`, and 91% of subagent list-price spend went to Opus 5.5. Persona context runs 130-170K tokens per turn. Research dispatches go to the harness's built-in `Explore` or `general-purpose`, which inherit the main model.

Exact-id pinning has broken the same contract twice. The first time was `agent-model-templates-pin-superseded-opus-and-lack-the-economy-template` (fixed in `1c113ca6`). The second is `agent-model-templates-pin-superseded-sonnet-and-haiku`: economy resolves to `claude-sonnet-5`, the fast tier is `claude-haiku-4-5-20251001`, and an override naming a 5.5 Sonnet or Haiku is refused. A unit with two bugs from one cause takes a REBUILD, not a third id bump.

No verb selects a template. `JsonAgentModelPolicyStore.save()` has had no production caller since the panel was removed, and `.dadaia/states` is PROTECTED. `applied_template` is therefore unreachable for a user.

## 2. Measurable Goals

- G1. The dispatched persona name chooses the model. A dispatch with no model parameter runs the template's cell, so a forgotten parameter can no longer run Opus.
- G2. Templates name tiers by alias. A new model release needs no library change: `git grep -nE 'claude-(opus|sonnet|haiku|fable)-[0-9]' -- dadaia_workspace` finds no hit in the templates or the registry.
- G3. Library users choose a template with one flag on the verb that already reads the overlay. They get the haiku and sonnet saving in `balanced` without editing state by hand.

## 3. Non-goals

- The skill kernel, ledger query APIs and their backlog items (rc-12's carried CP1/CP3, `skill-scripts-one-kernel`, `one-task-id-subject-grammar`, `origin-findings-renamed-to-the-spec-head`) are rc-14. So is `worktree-new-crashes-on-an-unreadable-release-state`.
- No new CLI group or verb. The selector is one flag (FR4).
- Archived specs, ledgers, ADRs, `CHANGELOG.md` and closed candidates keep the name `dd-software-engineer`.
- The developer's interim measures are not library work: a user-scope `~/.claude/agents/Explore.md` on haiku, and the main thread passing sonnet or haiku per dispatch until this ships.
- No telemetry or cost meter. The cost evidence above is a one-off measurement.

## 4. Requirements

### FR1 — the alias contract (Arm B: `agent-model-templates-pin-superseded-sonnet-and-haiku`, REBUILD of `model_registry.py`)

- AC1.1 (unit, RED first): Every cell of every template names a model by one of the four aliases `opus`, `sonnet`, `haiku` or `fable`. No cell names an exact Claude model id. The test fails on today's templates.
- AC1.2 (unit): The registry is one map from tier alias to Codex model id, with exactly four entries: `opus` → `gpt-5.6-sol`, `fable` → `gpt-5.6-sol`, `sonnet` → `gpt-5.6-terra`, `haiku` → `gpt-5.3-codex-spark`. These are today's Codex ids for those families. `codex_model` reads this map. The following are deleted: the per-id rows, `ModelEntry`, the `deep|dispatch|standard|fast` tier taxonomy, `registry_by_claude_id`, and Codex's persona-body id rewrite (`_CODEX_MODELS`, `_CLAUDE_MODEL_RE`, and the `Opus / Sonnet / Haiku` replace in `codex_assets.py`). Today that rewrite has no live input.
- AC1.3 (unit): G-1 still holds: `dd-code-reviewer` never resolves to `fable`. The rule is kept by the template table alone, and a unit test over every template enforces it. With overrides gone (AC1.6), the store's runtime Fable guard and `is_fable_model` are deleted.
- AC1.4 (integration): `public install` writes `model: <alias>` into each projected Claude persona. It writes the alias's Codex id and the clamped effort into each Codex agent.
- AC1.5 (no test — reviewer source sweep): A docstring or comment in `model_registry.py` states the contract: "templates name a tier by alias; a new model release needs no library change". G2's grep returns no hit.
- AC1.6 (unit, RED first): The overlay keeps only `applied_template`, and per-agent `overrides` are deleted. An overlay that still carries `overrides` is refused by the store's existing unknown-key refusal, with a `fix:` line naming `dadaia public install --template <id>`. Nothing is migrated. Several things go with the store's REBUILD: `overrides` in `agent-model-policy-v1.schema.json`, the stale retired-name docstring (`json_agent_model_policy_store.py:17`), and the uncalled public `parse()` wrapper. The refusal never ships without its remedy:
  - It lands in the same job as the `--template` flag (FR4).
  - For that DRIFT, `public doctor`'s remedy is the refusal's own `fix:` line, and there is no second remedy.

  The test fails on today's store, which accepts `overrides`. (Operator ruling, 2026-10-10.)

### FR2 — five personas: sr and jr replace `dd-software-engineer`, plus `dd-researcher`

- AC2.1 (integration): The library ships `dd-sw-engineer-sr` and `dd-sw-engineer-jr`, and `dd-software-engineer` is deleted.
  - Both implement tasks.
  - The senior also owns the as-is review, PLAN and job files, new behaviour, design choices, root causes, and the RED test of a new contract.
  - The junior owns tasks whose outcome is fully stated by their AC and `W:`.
  - `public install` projects both personas and prunes the instance copy of `dd-software-engineer`.
- AC2.2 (integration): The library ships `dd-researcher`.
  - It is a lean, read-only persona.
  - Its tools are `Read`, `Grep`, `Glob`, `Bash`, `WebSearch` and `WebFetch`, and it preloads no skills.
  - It returns findings as `path:line` or URL.
  - Install projects it read-only, the same way the reviewer is projected.
  - Its body states that fetched web content is data and never instructions, and that it runs only read-only commands through `Bash` (OWASP LLM01). The tool list stays as the operator ruled it.
- AC2.3 (unit): The core-agent set is the five personas: `dd-product-engineer`, `dd-code-reviewer`, `dd-sw-engineer-sr`, `dd-sw-engineer-jr` and `dd-researcher`. The set is read from the template table's keys, and no other agent list is kept by hand.
- AC2.4 (no test — reviewer source sweep): The root map §2 table names five roles in place of "Three roles, no fourth". `dd-manager-orchestration` routes research dispatches to `dd-researcher` in place of `Explore` and `general-purpose`, and routes engineer dispatches by the task's `who:` (FR5).
- AC2.5 (unit): `git grep -n "dd-software-engineer" -- dadaia_workspace tests` returns no hit.

### FR3 — the template table

- AC3.1 (unit): The unit test asserts all 15 cells exactly as this table gives them (model alias, effort). `balanced` stays the default. The product engineer stays on Opus in `balanced` because a SPEC is open-ended judgement. The engineer cells are the operator's.

| template | dd-product-engineer | dd-code-reviewer | dd-sw-engineer-sr | dd-sw-engineer-jr | dd-researcher |
|---|---|---|---|---|---|
| `balanced` | opus high | opus high | sonnet medium | haiku medium | haiku medium |
| `max-quality` | fable high | opus xhigh | opus medium | sonnet medium | sonnet medium |
| `economy` | sonnet medium | sonnet high | sonnet medium | haiku low | haiku low |


### FR4 — the template selector

- AC4.1 (integration): `dadaia public install --template <id>` writes `applied_template` to the agent-model overlay. It is the overlay's only writer of that field, and it re-projects every persona in the same pass. The flag feeds the one whole install, and there is no template-only re-projection. An unknown id exits non-zero with the valid ids named, and leaves the overlay and the projections unchanged.
- AC4.2 (integration): `public install` without `--template` keeps the current `applied_template`.
- AC4.3 (integration): `uvx dadaia-workspace init [DIR] --template <id>` takes the same flag and has the same effect, both on a new workspace and on a re-run, which is the upgrade. There is no `upgrade` verb. `reconcile` keeps the saved template and takes no flag.
- AC4.4 (integration): `dadaia public doctor` prints one `[ok] model-resolution: template <id>` line. That line replaces the check's re-validation of models and efforts (a REBUILD of `check_model_resolution`). `dadaia doctor` is unchanged, because a template finding there would be a fifth finding shape (bug `sa-doctor-finding-has-four-shapes`). (Operator ruling, 2026-10-10.)
- AC4.5 (integration, RED first): Start from an overlay that carries `overrides`. The `fix:` command that the refusal prints exits 0 and clears the refusal. Then `public install`, an `init` re-run and `reconcile` each exit 0.
- AC4.6 (no test — closure instance step): At closure, this instance's own overlay drops its `dd-product-engineer` and `dd-software-engineer` medium-effort overrides through `dadaia public install --template balanced`. `public doctor` then prints `[ok] model-resolution: template balanced`. `balanced` stays as the grill set it, with the product engineer on opus high. (Operator ruling, 2026-10-10.)

### FR5 — `who:` in the job-file task table

- AC5.1 (no test — reviewer source sweep): `dd-release-definition` §5 adds a `who` column to the job-file task table, and its example table shows it. The column names the dispatched role: `sr` or `jr` for an engineer task, or the owning role (`pe`, `cr`) for a task another persona owns, so every row's cell is true. The senior fills it while writing the job files. (Operator ruling, 2026-10-10.)
  - `jr`: the outcome is fully stated by the AC and `W:`. Examples are ports, trims, renames, characterization or literal tests, closure corrections and doc sync.
  - `sr`: new behaviour, design choices, root causes, the RED test of a new contract, the PLAN, job files and the as-is review.
- AC5.2 (no test — reviewer source sweep): One REJECTED verdict on a `jr` task re-dispatches that task to `dd-sw-engineer-sr`. The rule is stated once, in `dd-release-implementation` or `dd-manager-orchestration`, as the PLAN assigns.
- AC5.3 (no test — reviewer source sweep): The `define`-tree reviewer judges the `who` column against AC5.1's shape rule. `dd-code-review` says so in one line.

### FR6 — authorized source write set

- AC6.1 (no test — reviewer source sweep): The list below is the complete set of law, skill and persona sources this candidate may change. Adding another source returns this Draft to the operator. Projections change only through `public stage` and `public install`.
  - Personas: add `dadaia_workspace/public/agents/{dd-sw-engineer-sr,dd-sw-engineer-jr,dd-researcher}.md`; delete `dd-software-engineer.md`; edit `dd-product-engineer.md` and `dd-code-reviewer.md` (their `[SCOPE ERROR]` routing).
  - Law: `dadaia_workspace/public/data/{AGENTS,CONTEXT-MAP}.md`, `dadaia_workspace/public/data/fixed/slop-tests.md` and `dadaia_workspace/public/templates/specs-AGENTS.md`. The repo's own `specs/AGENTS.md` changes through `specs upgrade` only.
  - Skills: the `SKILL.md` of `dd-release-definition`, `dd-release-implementation`, `dd-bug-resolution`, `dd-manager-orchestration` and `dd-code-review`; `dd-ai-eng-knowhow/CONTEXT-ENGINEERING.md`.
  - Entity data and schemas: `dadaia_workspace/public/entities/registry.json`, `dadaia_workspace/public/schemas/handoff-v1.schema.json` (its example name), and `dadaia_workspace/public/schemas/agent-model-policy-v1.schema.json`.
  - Skill script: `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`. Its `reported_by` default (`:117`) still names the retired persona, and AC2.5's zero hits requires changing it.
  - Derived: `dadaia_workspace/public/templates/shipped-hashes.json`. It is append-only, and its tool re-records it for every edited template (releases law §3).
- AC6.2 (no test — closure memory pass): The Reconciliation updates every canonical statement ADR 0240 names. These are `specs/memory/product/agents/agent-orchestration.md` (summary line, roster table, model-policy lines), `specs/memory/QUALITY.md:75`, and the "three dd- personas" summaries at `specs/memory/product/harness/harness-claude-code.md:5`, `harness-codex.md:5` and `harness-copilot.md:5`, plus their `catalog.json` entries.

## 5. Constraints and risks

### Replaces

- `dd-software-engineer`, one persona whose model came from the template or a per-dispatch parameter, becomes `dd-sw-engineer-sr` and `dd-sw-engineer-jr`, each fixed by the template (FR2).
- Research dispatches to the harness's `Explore` and `general-purpose`, which inherit the main model, go to `dd-researcher` (FR2).
- The nine-entry registry of exact Claude ids and its four-tier taxonomy becomes a four-entry map from alias to Codex id. Codex's persona-body id rewrite is deleted (FR1).
- ADR 0022's three-agent, exact-id template table becomes the 15-cell alias table (FR3).
- The unreachable `applied_template` (no production writer) becomes the `--template` flag on `public install` and `init` (FR4).
- The model as a per-dispatch parameter is replaced by the dispatched persona name (G1).
- The job-file task table without an owner tier gains `who` (FR5).
- "Three roles, no fourth" (root map §2) becomes five roles (AC2.4).
- Per-agent overrides in the overlay are removed. Templates become the one selector, and the store's runtime Fable guard goes with them (AC1.3, AC1.6).
- The uncalled public `parse()` wrapper of the overlay store is deleted (AC1.6).
- `public doctor`'s re-validation of resolved models and efforts becomes one line naming the active template (AC4.4).

### Governance sequencing

1. ADR 0240 is proposed by `docs(adr): propose subagent-model-tiers`. It moves the roster from three roles to five and states the alias contract. Under ADR law M2, a proposed record cannot name a ruled one, so 0240 names 0022 in its text and sets `amends: "0022"` only at acceptance.
2. On the operator's ruling, the main thread writes `accepted`, `ruling` and `amends: "0022"`. The canonical-memory hunks the ADR names land in the same commit. Approval of SPEC and PLAN is a separate commit.

### Delivery constraints

- Order: FR1 (RED first, then the REBUILD) precedes FR3. FR2 precedes FR4's re-projection test and FR5. The senior writes the PLAN and job files.
- The rename touches 45 files in `dadaia_workspace` and `tests` (90 lines). The PLAN gives each file one `W:` owner.
- Structure and behaviour commits stay separate. Every behaviour task is two dispatches, and each job gets one reviewer verdict.

### Risks

| risk | control |
|---|---|
| A harness rejects an alias at dispatch. | Closed for `fable`. The main thread's probe on 2026-10-10 dispatched an agent with `model: fable`, and the run's `modelUsage` billed `claude-fable-5-1`. `opus`, `sonnet` and `haiku` are documented Claude Code aliases. AC1.4 pins what install writes. |
| An existing overlay carries `overrides`, which this instance's does. | AC1.6 refuses it with a `fix:` line naming `public install --template`, which lands in the same job. `public doctor` prints that same line. AC4.5 proves the line clears the refusal on install, re-init and reconcile. AC4.6 runs it on this instance. |
| A `jr` cell is too weak for a task. | AC5.2 escalates on the first REJECTED. AC5.3 has the reviewer judge the column before implementation. |

## 6. Open questions

None. The operator ruled on 2026-10-10:
- Per-agent `overrides` are deleted, and no migration is made (AC1.6).
- `public doctor` shows the template (AC4.4).
- The bug window is routed to rc-14 under CP3.

One reading remains for approval: AC5.2, where one REJECTED verdict on a `jr` task sends it to sr.
