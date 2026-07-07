# SPEC — v0.1.63 — Plugin Platform Completion (uninstall + full pack skill corpora)

**Status:** Aprovado
**Branch:** `feature/v0.1.63` (base: to be set by PM at implementation dispatch — see §0 sequencing)
**Origin:** PM dispatch 2026-07-07, theme "complete the v0.1.60 plugin subsystem". Consumes the two v0.1.60
closure backlog returns that finish the plugin platform: the ADR-2 additive-only deferral (`plugin-uninstall`)
and the ADR-5 minimal-viable-content ceiling (`plugin-pack-content-libraries`).
**Definition-time inspection** (product-engineer code read, 2026-07-07) — every claim below is a read fact from
the current post-v0.1.60 source (`cli/commands/plugin.py`, `infrastructure/public_assets.py:226-398`,
`core/models/plugin_pack.py`, `infrastructure/json_plugin_store.py`, `infrastructure/install_helpers.py:173-197`,
`infrastructure/codex_doctor.py:393-443`, `public/plugins/**`, `tests/**/test_plugin*.py`), not a restatement of
the backlog dossiers.
**Release-definition grill** (mandatory, from-backlog) run on the picked set before this SPEC — operator
unavailable mid-flow, so every code-unanswerable decision is pre-ruled in §9 as an **operator-overridable ADR**
(the v0.1.60 §9 precedent). Inspection-answered findings are recorded as read facts in §1.
**Consumes:** backlog `plugin-uninstall` (MEDIUM, 1 intent) + `plugin-pack-content-libraries` (MEDIUM, 1 intent).
**Bug debt at pick:** none in scope (PM picked a pure-backlog set). **Audit debt at pick:** the 2026-07-06
architecture audit is dispositioned by its own remediation track; finding A-1 interacts with this release only as
the §0 sequencing constraint below.

## 0. Sequencing notes (parallel definitions — binding)

1. **A-1 independence (MANDATORY).** The 2026-07-06 architecture-lane audit finding **A-1** (MEDIUM): the
   `PluginStore` port (`core/protocols/plugin_store.py`) has **zero importers** — both consumers construct
   `JsonPluginStore()` directly (`cli/commands/plugin.py:26,81`; `infrastructure/public_assets.py:50`), and
   `container.py` has no plugin factory. **v0.1.61 (defined in parallel) will either wire the port through the
   container or delete it. This SPEC does NOT depend on which way A-1 goes:** FR1/FR2 specify uninstall in terms
   of *the ledger contract* (`installed_plugins.json`, schema v1, read/written through **the same
   store-construction pattern `install_plugin` uses at this release's base commit** — direct `JsonPluginStore()`
   today; the container-wired port if v0.1.61 wired it; still direct if v0.1.61 deleted the port). This release
   **neither adds an import of `core/protocols/plugin_store.py` nor deletes it**, and its CLOSURE memory edits do
   not restate the port-seam claim (that memory correction is v0.1.61's A-1 remit — see §8).
2. **Parallel-definition overlap (Ruling 63-A — RULING A: ARCHX-1 + QAX-1).** <!-- AMEND:ARCHX-1 --> This
   release's write surface is `cli/commands/plugin.py`, `infrastructure/public_assets.py` (plugin block),
   `core/models/plugin_pack.py`, `public/plugins/**`, `infrastructure/codex_doctor.py` (FR6), + tests.
   **`cli/commands/plugin.py` + `infrastructure/public_assets.py` are written by v0.1.61 W2 FIRST (the A-1 port
   wiring), THEN this release's W1** — the rebase-and-reverify clause names **v0.1.61 explicitly**: W1 rebases
   onto v0.1.61's landed state, re-runs its suite, and adopts whichever store-construction pattern v0.1.61 left
   (§0.1). The 3 plugin agent bodies (`skills:` frontmatter, W2/W3) are also written by v0.1.62 W3 (handoff
   instructions — lands BEFORE this release) and v0.1.64 W3 (`tier:` rename — lands AFTER) — same rebase
   discipline. The FRs are written against contracts, not line numbers.
3. **Implementation order is FIXED by PM ruling (2026-07-07): v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64.**
   <!-- AMEND:QAX-1 --> Any undeclared collision discovered mid-wave is a STOP-and-rescope to PM.
4. **CLOSURE sequencing (Ruling 63-B — RULING B: ARCHX-2 + QAX-2).** <!-- AMEND:ARCHX-2 --> CLOSURE follows the
   same release order; §8 carries the generalized shared-atom merge-order clause. `ACTIVE.md` is a single
   pointer — the four releases never hold DEFINITION/CLOSURE phases concurrently; PM owns the phase schedule.
5. **Sibling note (ARCHX-3):** <!-- AMEND:ARCHX-3 --> v0.1.62 ships before this release — agent handoffs emitted
   during this release's implementation/closure phases carry `handoff-v1.2` + `self_pull.refs` per the updated
   instruction surfaces.
6. **Dual-review fold (2026-07-07, REJECT — QA63-1 HIGH, QA63-2/3 LOW; ARCH63-1 MEDIUM):** folded in place with
   `<!-- AMEND:… -->` markers — Ruling 63-F (RULING F) upgrades the AC-2 equivalence spine (absolute v0.1.60
   golden (b) anchor for side B + direct `.codex` stub-restore byte asserts in the all-targets leg); ARCH63-1
   extends the §8 coordination clause to `public-asset-distribution.md` + `architecture.md`; QA63-2 wall-time
   brackets + `@pytest.mark.slow`; QA63-3 W0 marker normalized to `[x]`.

## 1. Problem

v0.1.60 shipped the plugin **machinery** with two deliberate deferrals now due:

- **No uninstall (Ruling ADR-2, additive-only).** Once `dadaia plugin install <pack>` runs, there is no way to
  disable the pack except hand-editing `.dadaia/states/installed_plugins.json` and re-running core
  `public install` — exactly the class of hand-surgery the projection subsystem exists to eliminate.
- **Minimal-viable content only (Ruling ADR-5 / Ruling 12 hard ceiling).** Each pack ships exactly ONE skill
  (`browser-frontend-implementation`, `github-actions-cicd`); the full frontend-design and devops skill corpora
  were deferred as an unbounded authoring surface.

**Read facts (source, 2026-07-07):**

1. **`install_plugin` has no inverse.** `public_assets.py:328` records the ledger via `with_added` then projects;
   `InstalledPlugins` (`plugin_pack.py:99-129`) has `with_added` only — no `with_removed`. No `uninstall` string
   exists anywhere in the plugin subsystem.
2. **The projection layer's standing reconciliation law.** `copy_file`/`write_generated`
   (`install_helpers.py:173-197`) overwrite the destination whenever hashes differ (skip only on identical
   bytes) — a hand-edited runtime projection is already reconciled by any plain install. The v0.1.60 FR9
   `[foreign]` provenance gate protects **consumer-owned** `repos/<slug>/AGENTS.md` only; runtime projections
   (`.claude/`, `.codex/`, `.agents/`) are lib-owned, never legitimately hand-edited (dev-guardrail rule §1).
   This answers the backlog's "restore vs `[foreign]`" question by inspection — see ADR-U1.
3. **The removal/restore set is already enumerable.** `_project_installed_plugins` (`public_assets.py:288`) and
   `_doctor_installed_plugins` (`public_assets.py:352`) both walk the staged tree
   `.dadaia/agentic/plugins/<pack>/{agents,skills,rules}` — the same walk yields uninstall's target set. When a
   pack is not staged, `install_plugin` already degrades to ledger-only; uninstall mirrors that (ledger-only drop).
4. **Codex restore path exists.** Pack install renders `.codex/agents/<name>.toml` from the pack md
   (`_render_codex_pack_agent`); the core stub projection is the core install loop's job. Restoring a stub =
   re-running the core projection slice for the affected agent names (the stub carries no `model:` ⇒ codex falls
   back to default effort — exactly the pre-install state).
5. **Plugin doctor is ledger-driven.** `_doctor_installed_plugins` iterates ledger packs only — after a ledger
   drop the pack's doctor lines vanish, so cleanliness depends on actually removing/restoring the projected
   files; otherwise stale real bodies linger **silently**. Hence the never-installed-equivalence AC (AC-2).
6. **Pack agent skill refs are UNCHECKED today.** `check_agent_skill_refs` (`codex_doctor.py:393`) scans only
   `public/agents/*.md` against `public/skills/` — the pack agents' `skills:` frontmatter (which already
   references `browser-frontend-implementation` etc.) is invisible to it. Growing the corpora without closing
   this gap lets refs rot undetected. FR6 closes it.
7. **The Ruling-12 ceiling is machine-enforced and will go RED.**
   `tests/unit/infrastructure/test_plugin_content.py::_PACK_SKILL/_EXPECTED_SKILLS` hard-pins exactly the two
   v0.1.60 skills (`test_exactly_the_two_named_skills_ship_per_pack`). The first new skill fails it — that IS the
   RED-first lever; amending the ceiling constants to the new enumerated roster is a **deliberate recorded
   amendment**, never a silent regen (AC-6).
8. **Pack surfaces are disjoint.** Agents and skills are disjoint across the two packs (pack.json read) — no
   shared-file hazard on single-pack uninstall; kept as a contract invariant (AC-4).

## 2. Goals

1. **`dadaia plugin uninstall <pack>`** — the exact inverse of `install_plugin`: ledger removal + profile-scoped
   restoration of the projected core stubs over the pack agent bodies + removal of pack-only projections
   (skills/rules), idempotent, `plugin doctor`- and `public doctor`-clean afterwards.
2. **Never-installed equivalence:** an install→uninstall cycle leaves the workspace's runtime surface equivalent
   to one that never installed the pack (the durable v0.1.60 golden (b) baseline stays untouched and green).
3. **Full pack skill corpora BY NAME with a hard ceiling** (ADR-C1): 3 new skills per pack (pack totals: 4 + 4),
   authored by `ai-engineer` under the public-privacy law, wired into `pack.json` + the pack agents' frontmatter,
   referencing (never duplicating) the codex `frontend-ctx`/`design-ctx` adapters.
4. **Skill-ref integrity for the plugin surface:** pack agent `skills:` refs become machine-checked (FR6), and
   the v0.1.60 content contract tests are extended, not bypassed (ADR-C2).

## 3. Functional requirements

### FR1 — `dadaia plugin uninstall <pack>` CLI

- NEW `uninstall` command in `cli/commands/plugin.py`: validates *pack* against the in-package descriptors
  **before** workspace resolution (unknown pack → Click `BadParameter`, exit 2, message on stderr, empty stdout —
  mirrors `install`; stderr asserts normalized via the shared `_norm_stderr`-style helper, v0.1.57 QA-atom law).
- **Known pack, not installed → idempotent no-op, exit 0** with a `no change` message (the inverse of install's
  "already installed — no change") — ADR-U2.
- On success: prints the pack + restored agents; delegates all work to FR2's `uninstall_plugin`.

### FR2 — `uninstall_plugin` in `FileSystemPublicAssetManager` (the inverse of `install_plugin`)

- NEW `uninstall_plugin(workspace_root, pack_name) -> list[str]` in `infrastructure/public_assets.py`, plus the
  pure `InstalledPlugins.with_removed(name)` in `core/models/plugin_pack.py` (mirrors `with_added`; idempotent).
- **Ledger:** drop *pack_name* from `installed_plugins.json` through the same store-construction pattern
  `install_plugin` uses at the base commit (§0.1 — A-1-agnostic). Removing an absent name is a no-op.
- **Restore + remove (profile-scoped, Ruling 13 symmetry — ADR-U3).** Enumerating the staged pack tree
  (`.dadaia/agentic/plugins/<pack>/`), for each harness in the active profile (absent profile ⇒ all targets):
  - each pack **agent**: re-project the **core stub** over the pack body (`.claude/agents/<name>.md` back to the
    `[PLUGIN REQUIRED]` stub; `.codex/agents/<name>.toml` back to the stub render) — the same core-projection
    slice `public install` runs;
  - each pack **skill/rule** projection (no core counterpart): **delete** the projected file (and now-empty skill
    dirs) from `.agents/skills/` / `.claude/rules/`.
- **Drift semantics (ADR-U1):** a drifted (hand-edited) projected pack file is restored/removed anyway — the
  runtime projection surface is lib-owned (read fact 2) — but **never silently**: each such file emits a
  `[drift-restored]`/`[drift-removed]` output line before action.
- **Unstaged pack:** ledger-only drop + a non-silent `[skip]`-class line (mirror of install's degrade).
- **Ordering for doctor-cleanliness:** files first, ledger last — an interrupted uninstall leaves the ledger
  entry present so `plugin doctor` still surfaces the pack's file state (never a silent half-state).
- Idempotent end-to-end: a second `uninstall` of the same pack changes nothing (all `[skip]`/no-op lines).

### FR3 — Never-installed equivalence + doctor cleanliness (the acceptance spine)

- After `install <pack>` → `uninstall <pack>` in the same workspace: `installed_plugins.json` no longer lists the
  pack; the projected agent files carry the **stub** bodies; **zero** pack-only projected files remain;
  `dadaia plugin doctor` reports `[not-applicable] no plugin packs installed` (when no other pack is installed);
  `public doctor`'s runtime surface is **equivalent to a never-installed workspace computed in the same test
  run** (self-relative comparison) **AND anchored absolutely (Ruling 63-F / QA63-1): side B's post-uninstall
  doctor/runtime surface is ALSO compared against the durable v0.1.60 golden (b) never-installed baseline —
  read-only reuse of the existing fixture, zero regen** — the same-run A-vs-B comparison alone cannot catch a
  residue class both sides are equally blind to (read fact 5: plugin doctor goes ledger-blind after the drop).
  <!-- AMEND:QA63-1 --> **Direct byte asserts in the absent-profile (all-targets) leg:**
  `.codex/agents/{frontend-engineer,design-specialist}.toml` byte-equal the fresh core-stub render, and zero
  pack rule projections remain (not only `.claude/` stub bodies + `.agents/skills/`). Asserted by AC-2.
- Multi-pack isolation: with both packs installed, uninstalling one leaves the other's projections and doctor
  lines fully intact (read fact 8).

### FR4 — `frontend-design` skill corpus (ai-engineer; enumerated, hard ceiling)

Exactly **three** new skills under `public/plugins/frontend-design/skills/<slug>/SKILL.md` (ADR-C1):

1. **`design-system-authoring`** (primary consumer: `design-specialist`) — design tokens, type/space/color
   scales, component-spec authoring, visual-language definition; the *producer* side of the token-fidelity
   contract that `browser-frontend-implementation` consumes (cross-reference it, never duplicate its checklist).
2. **`frontend-component-architecture`** (primary consumer: `frontend-engineer`) — React-and-other-framework
   component composition, state management, hooks/effects discipline, rendering performance, framework hygiene
   (deepens the agent-body domain: "HTML/CSS/JS/TS/React and other component frameworks").
3. **`visual-review-protocol`** (primary consumer: `design-specialist`) — the screenshot-evidence review loop,
   viewport/responsive matrix, regression comparison, verdict criteria; **references** the codex `design-ctx`
   (and where relevant `frontend-ctx`) adapters by name, never inlines their emit blocks (the v0.1.60
   reference-not-duplicate law, contract-tested).

### FR5 — `devops` skill corpus (ai-engineer; enumerated, hard ceiling)

Exactly **three** new skills under `public/plugins/devops/skills/<slug>/SKILL.md` (ADR-C1):

1. **`gitflow-release-engineering`** — branch model, PR/merge discipline, versioning/tagging, release/deploy
   gates (the agent-body "gitflow + release/deploy gates" domain).
2. **`container-build-and-deploy`** — Dockerfile/compose authoring, image hygiene, deploy config (grounded in
   the agent's write allowlist: `Dockerfile`, `docker-compose*.yml`, `deploy/**`).
3. **`cicd-security-hardening`** — SHA-pinned actions, least-privilege workflow permissions/tokens, secret
   hygiene, supply-chain posture (grounded in the repo's own CI practice — SHA pins are an audited invariant).

**Both corpora:** generic content only (public-privacy law, `[ok] public-privacy` holds); zero new rules; zero
new agents; each SKILL.md carries `name`/`description` frontmatter matching its dir slug.

### FR6 — Pack wiring + plugin-aware skill-ref integrity

- **Wiring:** each pack's `pack.json` `skills[]` lists exactly its enumerated roster (4 entries per pack); each
  new skill is added to the `skills:` frontmatter of the pack agent(s) that consume it (`design-system-authoring`
  + `visual-review-protocol` → `design-specialist`; `frontend-component-architecture` → `frontend-engineer`;
  all three devops skills → `devops-engineer`).
- **Ref check (closes read fact 6):** extend the skill-ref integrity surface so pack agent `skills:` frontmatter
  refs resolve against `public/skills/` **∪ the pack's own `public/plugins/<pack>/skills/`** — either by
  extending `check_agent_skill_refs` with a plugin-aware sweep or a sibling checker on the same `[drift]` prefix,
  reported through the same `public doctor` path. RED-first: pre-fix, a bogus ref in a pack agent goes
  undetected; post-fix it is a `[drift]` line.
- **Contract-test extension (ADR-C2):** `test_plugin_content.py`'s ceiling constants are amended to the new
  roster as a **deliberate recorded amendment** (read fact 7), and the content contract generalizes: per-pack
  roster == `pack.json` `skills[]` == on-disk skill dirs; every pack-agent `skills:` ref resolves; frontmatter
  law per skill; adapters referenced-not-duplicated; privacy `[ok]`.

## 4. Non-goals

- **No PluginStore-port fate decision** — wire-vs-delete is v0.1.61's A-1 remit (§0.1). This release neither
  imports nor deletes `core/protocols/plugin_store.py`.
- **No new rules, no new agents, no roster change** (still 9 core + 3 plugin), no constitution amendment.
- **No pack removal from the package** — uninstall disables a pack *in a workspace*; the in-package pack and the
  staged `.dadaia/agentic/plugins/` tree remain (staging is `_COPY_DIRS`-driven and pack-agnostic).
- **No network distribution, no third pack, no pack versioning/upgrade semantics** (descriptor schema stays v1).
- **No harness-profile changes** — uninstall consumes `_profile_harnesses` as-is (Ruling 13 symmetry).
- **No Layer-2 / model / registry change**; plugin agents stay `tier: 3` + `model: claude-sonnet-4-6`.
- **No lease/gate/spec_context change** — the v0.1.50 frozen no-steal suite is expected **zero-diff**.

## 5. Acceptance criteria

- **AC-1 (uninstall CLI — RED-first):** `dadaia plugin uninstall frontend-design` after an install removes the
  pack from `installed_plugins.json` and prints the restored agents; `uninstall bogus` → exit 2, stderr names the
  pack (asserted after `_norm_stderr` normalization), empty stdout; `uninstall devops` when devops was never
  installed → exit 0 + `no change` message, ledger byte-identical. RED-first: pre-fix there is no `uninstall`
  command (exit 2 on the verb itself).
- **AC-2 (never-installed equivalence — the spine; UPGRADED per Ruling 63-F / QA63-1):** <!-- AMEND:QA63-1 -->
  in one `tmp_path` run: workspace A = fresh install (no pack); workspace B = fresh install → `plugin install
  frontend-design` → `plugin uninstall frontend-design`. Assert B's
  `.claude/agents/{frontend-engineer,design-specialist}.md` carry the stub body (`[PLUGIN REQUIRED]`, not the
  pack body), **B's `.codex/agents/{frontend-engineer,design-specialist}.toml` byte-equal the fresh core-stub
  render and zero pack rule projections remain (direct asserts, absent-profile all-targets leg)**, B has
  **zero** files under `.agents/skills/` from the pack roster, B's `installed_plugins.json` lists no pack,
  `plugin doctor` → `[not-applicable]`, and B's `public_assets.doctor()` runtime surface is asserted BOTH ways:
  (i) == A's (same-run self-relative), AND (ii) == the **durable v0.1.60 golden (b) never-installed baseline**
  (absolute anchor; read-only fixture reuse, zero regen — catches residue classes the same-run comparison is
  double-blind to). The golden (b) fixture is untouched and its own test stays green. **Wall-time (QA63-2):**
  the equivalence test builds two workspaces — mark `@pytest.mark.slow`, bracket **≤ ~15s** (2× the v0.1.58
  ~6s single-workspace precedent + margin). <!-- AMEND:QA63-2 -->
- **AC-3 (idempotency + ordering + multi-pack):** double `uninstall` is a no-op (ledger + files byte-stable);
  with both packs installed, uninstalling `devops` leaves every `frontend-design` projection and doctor line
  intact; files-before-ledger ordering is observable (a simulated failure after file restore leaves the ledger
  entry ⇒ `plugin doctor` still reports the pack — non-silent half-state).
- **AC-4 (profile×uninstall — Ruling 13 symmetry):** in a claude-only-profile workspace,
  install→uninstall touches only `.claude/` + `.agents/skills/` (never creates or deletes under `.codex/`);
  absent profile ⇒ all targets. Out-of-profile residue remains surfaced by the v0.1.58 A3 never-silent law
  (no new doctor split).
- **AC-5 (drift never silent):** hand-edit a projected pack agent md and a projected pack skill, then
  `uninstall` → both are restored/removed AND the output carries a `[drift-restored]`/`[drift-removed]` line per
  file; nothing under `repos/<slug>/` is ever touched by uninstall (the FR9 `[foreign]` surface is disjoint).
- **AC-6 (corpora enumerated + ceiling recorded):** exactly the 8 skills exist across `public/plugins/*/skills/`
  (the 2 v0.1.60 skills + the 6 named in FR4/FR5, no more); each pack's `pack.json` `skills[]` == its roster;
  every pack-agent `skills:` ref resolves (FR6 check green); the amended `test_plugin_content.py` ceiling
  constants are updated in the same commit as the skills they admit (deliberate recorded amendment, cited on the
  task line); `[ok] public-privacy` holds; `frontend-ctx`/`design-ctx` referenced, never inlined (the existing
  duplication-marker asserts extend to the new skills).
- **AC-7 (plugin-aware ref check — RED-first):** pre-fix, a pack agent `skills:` entry naming a non-existent
  skill produces zero report lines (read fact 6, demonstrated); post-fix it produces a `[drift]` line through the
  `public doctor` path and the doctor exits non-zero per the existing ref-drift handling
  (`cli/commands/public.py:47-50`).
- **AC-8 (mutation-sanity — sabotage → FAIL → revert, per new test):** (a) make `uninstall` skip the ledger drop
  ⇒ AC-2 ledger assert FAILS; (b) make it skip skill deletion ⇒ AC-2 zero-pack-files assert FAILS; (c) make it
  skip stub restore ⇒ AC-2 stub-body assert FAILS; (d) accept an unknown pack ⇒ AC-1 exit-2 test FAILS; (e) make
  the FR6 check ignore pack agents ⇒ AC-7 post-fix test FAILS; (f) drop a skill from `pack.json` while keeping
  its dir ⇒ AC-6 roster contract FAILS. Each captured on its task line, then reverted.
- **AC-9 (full gates + ship):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, full unpiped
  `pytest`, `lint-imports --no-cache` (kept-contract count and ignore-cap **unchanged** — uninstall adds no new
  layer edge; note the exact counts are re-read at implementation time, §0.2), `dadaia specs doctor` exit 0,
  `dadaia backlog doctor` exit 0; ship wave: `dadaia public stage` → `public doctor` → `public install --target
  all` → confirming `public doctor` (`[ok] public-privacy`, exit 0). Frozen no-steal suite zero-diff. *(PE runs
  no shell — commands surfaced to PM/operator or devops dispatch.)*
- **AC-10 (fate ledger, per wave — v0.1.60 plugin suites enumerated):** every wave records concrete files +
  fates; the v0.1.60 plugin test suites are adjudicated explicitly — see PLAN §Fate ledger. No implementation
  wave stages `specs/backlog/**` (dispositioned at CLOSURE).

## 6. Consumed backlog

| Item | Kind | Priority | Consumed → FR | Anchor fate |
|---|---|---|---|---|
| `plugin-uninstall` | backlog (candidate) | MEDIUM | uninstall CLI → FR1; `uninstall_plugin` inverse + drift semantics → FR2; doctor-clean equivalence → FR3 | Anchor `public_assets.py#install_plugin` SURVIVES (gains its inverse) → **CLOSURE** `DELIVERED — v0.1.63` |
| `plugin-pack-content-libraries` | backlog (candidate) | MEDIUM | frontend-design corpus → FR4; devops corpus → FR5; wiring + ref integrity → FR6 | Anchor `core/models/plugin_pack.py#PluginPack` SURVIVES (its `skills` tuples grow) → **CLOSURE** `DELIVERED — v0.1.63` |

Both anchors survive → dispositioned + archived at CLOSURE; no SHIP-time archival. Discipline: **no
`specs/backlog/**` staged in implementation waves** (AC-10). Backlog returns anticipated: none (the plugin
platform is complete for the 2-pack surface; a third pack or pack-versioning would be a fresh demand).

## 7. Risks

- **Parallel-release collision on `plugin.py`/`public_assets.py` (§0).** v0.1.61's A-1 remediation may touch the
  same files. Mitigation: FR2's A-1-agnostic store-construction clause; rebase + re-verify at implementation.
- **Uninstall deletes the wrong thing.** A path bug could delete non-pack skills from `.agents/skills/`.
  Mitigation: the removal set is enumerated from the staged pack tree only (read fact 3); AC-2/AC-3 assert other
  packs + core skills intact; AC-5 asserts `repos/**` untouched.
- **Silent half-state on interrupted uninstall.** Mitigation: files-before-ledger ordering (FR2) + AC-3.
- **Corpus ballooning / slop.** Six new skills is real authoring surface. Mitigation: hard ceiling BY NAME
  (ADR-C1), ceiling machine-enforced by the amended contract constants, reference-not-duplicate law
  contract-tested, ai-engineer as sole content author.
- **Public-privacy leak in new content.** Mitigation: `[ok] public-privacy` in AC-6/AC-9; generic-only law.
- **Ceiling-constant amendment misread as slop-regen.** Mitigation: the amendment is cited on the task line with
  the roster diff (AC-6), mirroring the v0.1.60 T-60-11 golden-amendment precedent.

## 8. Memory files affected at CLOSURE

- `specs/memory/product/distribution/plugin-packs.md` — **primary edit.** Uninstall verb + ledger removal +
  stub restoration + never-installed equivalence; the "Additive-only (no uninstall this release)" claim is
  REMOVED; the skill rosters (4 + 4, by name). **Do NOT restate the PluginStore-port seam claim** — its
  correction is v0.1.61's A-1 remit. **Coordination clause (EXTENDED per ARCH63-1 — it covers ALL THREE shared
  atoms, not plugin-packs alone):** <!-- AMEND:ARCH63-1 --> for `plugin-packs.md`,
  `public-asset-distribution.md`, AND `architecture.md`, the later-closing release REBASES the atom on the
  sibling's closed state and reconciles the final wording (coordinate via PM); this release never reverts
  v0.1.61's or v0.1.62's closed corrections. `summary` changes ⇒ regen `catalog.json`
  (`dadaia memory catalog generate`; tldr length cap).
- `specs/memory/product/distribution/public-asset-distribution.md` — **edit.** "plugin-pack projection with
  installed-plugins ledger + core-install precedence" gains the uninstall inverse. Shared with v0.1.61 (pass A)
  + v0.1.62 (containment/symlink posture) — rebase per the coordination clause above. <!-- AMEND:ARCH63-1 -->
- `specs/memory/architecture.md` — **edit.** `cli/commands/plugin.py` gains `uninstall`; `public_assets` gains
  `uninstall_plugin`; the FR6 ref-check surface. Leave the port-seam sentence to v0.1.61 (§0.1); rebase on
  v0.1.61's closed architecture edits (contract #9 + `build_plugin_store`) — never revert them.
  <!-- AMEND:ARCH63-1 -->
- `specs/memory/product/agents/agent-orchestration.md` — **assess** (likely no change: roster/tier unchanged).
- `specs/memory/tech-stack.md` — no change expected (no new dependency, no model change); state the reason.
- **Shared-atom merge order (Ruling 63-B / RULING B — ARCHX-2 + QAX-2, generalized from the plugin-packs
  clause to the full set):** <!-- AMEND:ARCHX-2 --> PM sequences CLOSURE in the fixed release order (this
  release closes after v0.1.61/62, before v0.1.64); the later-closing release REBASES each shared atom on the
  sibling's closed state (never reverts a sibling's correction); every `catalog.json` regen includes all prior
  tldr/summary deltas.

## 9. Definition rulings (grill, operator-unavailable — OPERATOR-OVERRIDABLE)

- **ADR-U1 — Drifted projected pack files: RESTORE/REMOVE, never silently; no refuse, no `--force` gate.**
  Grounded in read fact 2: runtime projections are lib-owned and the standing `copy_file` law already reconciles
  divergent projections on every plain install; `[foreign]` protection is for consumer-owned files
  (`repos/<slug>/AGENTS.md`), a disjoint surface. Uninstall therefore proceeds and emits a
  `[drift-restored]`/`[drift-removed]` line per affected file (never-silent, A3-style). **Override:**
  refuse-on-drift with a `--force` escape hatch.
- **ADR-U2 — Uninstall of a known-but-not-installed pack = idempotent no-op, exit 0** (`no change` message —
  the exact inverse of install's already-installed no-op); an **unknown** pack name = Click `BadParameter`,
  exit 2, validated before workspace resolution (mirrors install). **Override:** exit 2 for not-installed.
- **ADR-U3 — Uninstall is profile-scoped EXACTLY like install (Ruling 13 symmetry).** Restore/remove only within
  the active harness profile; out-of-profile residue stays governed by the existing v0.1.58 A3 never-silent
  doctor law (no new cleanup path, no doctor split). **Override:** existence-driven cleanup across all targets
  regardless of profile.
- **ADR-U4 — Files-before-ledger ordering.** The ledger entry is dropped LAST so an interrupted uninstall is
  never a silent half-state (`plugin doctor` remains ledger-driven, read fact 5). **Override:** ledger-first +
  a reconciliation sweep.
- **ADR-C1 — Skill corpus BY NAME with a hard ceiling: exactly 3 new skills per pack** (FR4/FR5 rosters; pack
  totals 4 + 4), zero new rules, zero new agents. Grounded in the stub agent domains (frontmatter descriptions +
  write allowlists) and the existing ctx adapters (referenced, never duplicated). Mirrors the Ruling-12
  enumerate-with-ceiling method that kept v0.1.60 shippable. **Override:** operator edits the roster (add/remove/
  rename any entry) or changes the ceiling.
- **ADR-C2 — Contract tests: YES — extend, never bypass.** `test_plugin_content.py` remains the content law; its
  ceiling constants are amended to the new roster as a deliberate recorded amendment (the RED-first lever, read
  fact 7), and the contract generalizes per-pack (roster == pack.json == disk; refs resolve; frontmatter law;
  adapters not inlined; privacy). **Override:** freeze the old constants and fork a new content-test module.
- **ADR-C3 — Ref-integrity placement:** the plugin-aware skill-ref check rides the existing
  `check_agent_skill_refs` `[drift]`-prefix surface through `public doctor` (read fact 6 gap), not a new doctor
  command. **Override:** fold into `dadaia plugin doctor` instead.
