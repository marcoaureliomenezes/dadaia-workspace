# Closure: Release — v0.1.63 — Plugin Platform Completion (uninstall + full pack skill corpora)

> **Status:** Aprovado
> **Release ID:** v0.1.63
> **Owner:** product-engineer
> **Closed:** 2026-07-07
> **Branch:** `feature/v0.1.63` · **Base:** post-v0.1.62 `main` (`352969da` lineage) · **Merged:** `457e4e10` (PR #120, squash of `feature/v0.1.63`, 2026-07-07) · **Closure branch:** `chore/v0.1.63-closure`
> **Ship gates:** qa-engineer **APPROVED** (alpha ship-gate handoff `2026-07-07T203229Z` — the reviewer independently re-ran the AC-2 equivalence test AND the AC-8(d) sabotage, not just read the evidence blocks) · security-reviewer **APPROVED** (push-gate keyed to the pushed ref sha `71c36c4a`; uninstall path-traversal / CWE-22 posture verified — removal set strictly = staged-pack-tree enumeration) · CI green at merge (one e2e-panel job failed at **Chromium install**, infra flake exit 100; rerun green — see Drifts).
> **Mandate:** Third of the fixed four-release queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64 (Rulings 61-B / 63-A / 63-B). Consumes the two v0.1.60 closure backlog returns that complete the plugin platform.

## Summary

v0.1.63 completes the v0.1.60 plugin subsystem by retiring its two deliberate deferrals.
**`dadaia plugin uninstall <pack>`** is now the exact inverse of install: profile-scoped
restoration of the projected core stubs over the pack agent bodies, deletion of pack-only
skill/rule projections, never-silent `[drift-restored]`/`[drift-removed]` handling of
hand-edited projections, and a **files-first / ledger-last** ordering so an interrupted
uninstall never leaves a silent half-state. An install→uninstall cycle is proven equivalent
to a never-installed workspace — asserted both same-run A-vs-B and against the durable
v0.1.60 golden (b) baseline as an absolute anchor (Ruling 63-F), with direct `.codex`
stub-restore byte asserts. Enabling a pack is no longer a one-way door.

The second deferral — the ADR-5 minimal-viable-content ceiling — is retired by the **full
pack skill corpora**: three new skills per pack (frontend-design gains
`design-system-authoring`, `frontend-component-architecture`, `visual-review-protocol`;
devops gains `gitflow-release-engineering`, `container-build-and-deploy`,
`cicd-security-hardening`), taking each pack to a 4-skill roster under a hard ceiling BY
NAME (ADR-C1), authored by ai-engineer under the public-privacy law, with the ctx adapters
referenced-never-duplicated. The content-contract ceiling constants were amended as a
**deliberate recorded amendment** (the RED-first lever), and pack-agent `skills:` frontmatter
refs — previously invisible to `check_agent_skill_refs` — are now machine-checked through
`public doctor` (FR6, RED-first demonstrated). The plugin platform is complete for the
2-pack surface; no backlog returns.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-63-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-07 code read + mandatory release-definition grill (operator unavailable → §9 operator-overridable ADRs U1–U4, C1–C3); dual-review REJECT folded (QA63-1..3 + ARCH63-1 + ARCHX/QAX AMEND markers); PM Rulings 63-A/63-B/63-F; `Aprovado` after re-verify | `977593cf` (queue definition) · phase flip `3bfc9d48` |
| T-63-10 | W1 FR1/FR2/FR3 — `InstalledPlugins.with_removed` + `uninstall_plugin` (staged-tree enumeration, profile-scoped stub restore + pack-only deletion, drift lines, files-first/ledger-last) + CLI `uninstall`; AC-1..AC-5 RED-first (13 pre-fix failures) + upgraded AC-2 (golden (b) absolute anchor + `.codex` byte asserts, 3.16s ≤ 15s bracket) + AC-8(a)–(d) sabotages; branch-point collect pin 4772 (QAX-4) | `a23a63d1` |
| T-63-11 | W1 E2E — pipeline leg (h) install→uninstall→reinstall (re-installable state proven); 1.02s ≤ 12s bracket; 6 existing legs SURVIVE green | `65419397` |
| T-63-20 | W2 FR4 — 3 frontend-design skills + pack.json/frontmatter wiring + recorded ceiling amendment (`_PACK_SKILL`/`_EXPECTED_SKILLS` → per-pack `_PACK_SKILLS` roster map, frontend-design → 4) + recorded golden amendment (3 `[ok] stage:` lines × 2 doctor goldens) | `22e88227` |
| T-63-30 | W3 FR5 — 3 devops skills + wiring + roster-map APPEND (devops → 4) + AC-8(f) sabotage + recorded golden amendment (3 `[ok] stage:` lines × 2 doctor goldens) | `30561711` |
| T-63-40 | W4 FR6 — additive `_check_plugin_agent_skill_refs` in `codex_doctor.py` on the `check_agent_skill_refs` `[drift]` surface; AC-7 RED-first + full-sweep both packs + AC-8(e) sabotage; core-agent path byte-identical | `c273b33f` |
| T-63-50 | W5 ship — AC-9 full gates + live-instance propagation (`stage → doctor → install --target all → doctor`, `[ok] public-privacy`); frozen suite zero-diff; QA alpha ship-gate + security push-gate; push; CI watched green; PR #120; merge `457e4e10` | `71c36c4a` |
| T-63-60 | CLOSURE — this file + memory rebase (4 atoms edited, 1 assessed no-change) + disposition sweep + 2 backlog flips + candidates index update + archive handoff to PM | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).
Gate evidence captured at the ship tree (`71c36c4a`) and merged as PR #120 (`457e4e10`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-9 full suite green | unpiped `pytest` (real exit) | `4778 passed, 17 skipped, exit 0` — `71c36c4a` (branch-point pin 4772 collected at T-63-10; growth = this release's new tests) |
| AC-9 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 — `71c36c4a` |
| AC-9 types clean | `mypy --strict dadaia_workspace` | exit 0 — `71c36c4a` |
| AC-9 import contracts | `lint-imports --no-cache` | **9 kept / 0 broken**, ignore-cap arrows **36** — **== base pins** (uninstall adds no layer edge) — `71c36c4a` |
| AC-9 SDD + backlog doctors | `dadaia specs doctor` · `dadaia backlog doctor` | both exit 0 — T-63-50 evidence block |
| AC-1 uninstall CLI (RED-first) | `pytest tests/unit/cli/test_plugin_cli.py` + integration | RED: 13 pre-fix failures (`No such command 'uninstall'`, `with_removed` absent); GREEN post-fix; unknown pack → exit 2, stderr via `_norm_stderr`, empty stdout; known-not-installed → exit 0 `no change`, ledger byte-identical — `a23a63d1` |
| AC-2 never-installed equivalence (UPGRADED, Ruling 63-F) | `pytest tests/integration/test_plugin_uninstall.py` (`@pytest.mark.slow`) | same-run A == B (stub bodies, zero pack files, ledger clean, `plugin doctor` `[not-applicable]`, doctor runtime surface) PLUS absolute anchor vs the v0.1.60 golden (b) baseline (read-only reuse, zero regen) PLUS direct `.codex/agents/*.toml` byte-equal fresh stub render + zero pack rules (all-targets leg); measured **3.16s** ≤ ~15s bracket; golden (b) fixture byte-untouched, its own test green — `a23a63d1` |
| AC-3 idempotency + ordering + multi-pack | targeted tests in `test_plugin_uninstall.py` | double uninstall byte-stable no-op; simulated failure after file restore leaves ledger entry ⇒ `plugin doctor` still reports the pack; uninstalling `devops` leaves every `frontend-design` projection + doctor line intact — `a23a63d1` |
| AC-4 profile×uninstall (Ruling 13 symmetry) | claude-only-profile leg | install→uninstall touches only `.claude/` + `.agents/skills/`, never creates/deletes under `.codex/`; absent profile ⇒ all targets — `a23a63d1` |
| AC-5 drift never silent + repos disjoint | drift leg | hand-edited pack agent md + pack skill both restored/removed WITH one `[drift-restored]`/`[drift-removed]` line each; nothing under `repos/<slug>/` touched — `a23a63d1` |
| E2E re-installable state | `pytest tests/e2e/features/test_plugin_pipeline.py` leg (h) | install → uninstall (stubs restored, ledger dropped, `plugin doctor` [not-applicable], `public doctor` exit 0) → reinstall (real bodies + pack codex render land again); 1.02s ≤ ~12s; 6 existing legs green — `65419397` |
| AC-6 corpora enumerated + recorded ceiling amendment | `pytest tests/unit/infrastructure/test_plugin_content.py` | RED pre-amendment on each pack ("pack skill set drifted from the … ceiling: [+3 skills]"); roster map amended in the same commits as the skills (`22e88227` frontend-design → 4; `30561711` devops → 4); roster == pack.json == disk; frontmatter law; adapters referenced-not-inlined; privacy `[ok]` |
| AC-7 plugin-aware ref check (RED-first) | `pytest tests/unit/infrastructure/test_agent_skill_refs.py` | pre-fix a bogus pack-agent ref yields ZERO report lines (read fact 6 demonstrated); post-fix `[drift]` line through `public doctor`, non-zero exit; full-sweep green for BOTH packs — `c273b33f` |
| AC-8 mutation-sanity (a)–(f) | one-line sabotages per task line | (a) ledger-drop skip ⇒ AC-2 ledger assert FAILED; (b) skill-deletion skip ⇒ zero-pack-files FAILED; (c) stub-restore skip ⇒ stub-body FAILED; (d) unknown pack accepted ⇒ AC-1 exit-2 FAILED; (e) sweep early-return ⇒ 2 post-fix tests FAILED; (f) pack.json skill dropped, dir kept ⇒ roster contract FAILED — each captured then reverted; T-63-10/30/40 evidence blocks |
| Frozen v0.1.50 no-steal suite | `git diff` vs main on the lease/gate test files | **zero-diff** — `71c36c4a` |
| Self-hosting reconcile (live instance) | `dadaia public stage` → `public doctor` → `install --target all` → `public doctor` | all exit 0 incl. `[ok] public-privacy`; both packs' new skills staged to the instance — T-63-50 |
| QA ship gate (alpha boundary) | `dadaia reports validate <handoff>` | **APPROVED** — handoff `2026-07-07T203229Z`; reviewer independently re-ran the AC-2 equivalence test and the AC-8(d) sabotage |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** — keyed to pushed ref sha `71c36c4a`; uninstall CWE-22 posture verified (removal set strictly = staged-pack-tree enumeration; `repos/**` disjoint) |
| CI (PR #120) | GitHub Actions | green at merge `457e4e10`; one e2e-panel job failed at Chromium install (infra, exit 100), rerun green — see Drifts |

## Drifts

### e2e-panel-chromium-install-infra-flake (rerun green, no bug filed)

**Description:** One CI e2e-panel job failed during the **Chromium browser install step**
(Playwright browser download, exit 100) — before any test or product code executed. The
rerun of the same job at the same sha was green, and every other check passed.

**Resolution:** Adjudicated pure infrastructure (network/CDN transient in the browser
download, not a product path and not a test): no dadaia-workspace contract was violated, so
**no bug was filed** — the bug-registration guardrail covers product misbehavior, and a
package-download transient is neither. Distinct from the v0.1.62
`e2e-panel-harness-toggle-ci-flake` (that one is a test-level flake, filed LOW, still open,
not consumed here). Watch-CI-until-green honored: merge happened only with every job green.

**Memory updates:** none (an infra transient is not product truth).

### recorded-golden-amendment-six-stage-lines

**Description:** The 6 new pack skills change the staged-tree surface, so two doctor goldens
(`doctor_all_four_v0158.json` + `plugin_doctor_report_golden_b_v0160.json`) could not stay
byte-identical — each gained exactly **6 `[ok] stage:plugins/<pack>/skills/*/SKILL.md`
lines** (3 frontend-design at `22e88227`, 3 devops at `30561711`; regen via
`UPDATE_INSTALL_GOLDENS=1`).

**Resolution:** Handled as a **deliberate recorded amendment** per the T-60-11 precedent —
cited on the T-63-20/T-63-30 task lines with the exact line inventory, and the QA ship-gate
**verified the insertion is exactly those 6 stage lines per golden**: zero runtime-projection
lines added, so the never-installed-equivalence semantics of golden (b) are intact and the
AC-2 absolute anchor stayed read-only (fixture never regen'd for AC-2 itself). Not a silent
re-baseline.

**Memory updates:** none beyond the planned pass (goldens are test fixtures, not memory claims).

### tech-stack-plugin-inventory-rows-stale-at-rebase

**Description:** SPEC §8 expected `tech-stack.md` unchanged ("no new dependency, no model
change") — true for the stack itself. But at the CLOSURE rebase read, the §Plugin-inventory
rows still named the single v0.1.60 skill per pack ("+ skill
`browser-frontend-implementation`" / "+ skill `github-actions-cicd`") — false memory once
the 4-skill rosters shipped.

**Resolution:** Minimal truth edit to the two inventory rows (4-skill rosters named +
uninstall mention), nothing else touched. The SPEC's no-change expectation is recorded as
held for dependencies/tools and bent only for these two stale content rows — memory truth
outranks the prediction.

**Memory updates:** `specs/memory/tech-stack.md` (the two §Plugin-inventory rows +
frontmatter only).

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. All edits landed in this CLOSURE phase (MEMORY gate open), **rebased on the
v0.1.61 AND v0.1.62 closed states per Rulings 63-B + ARCH63-1** — each atom's current text
was read before editing and no sibling correction was reverted (verified: v0.1.61's
port-seam wording and 9-contract enforcement text preserved verbatim; v0.1.62's
containment/symlink posture and `core/role_atom_map.py` text untouched).
`release_origin: v0.1.63` + `last_updated: 2026-07-07` set on every edited atom.
**Catalog regen required** (PM follow-up: `dadaia memory catalog generate`) — tldr/summary
changed on `plugin-packs` and `public-asset-distribution`; regen accumulates the
v0.1.61/62 prior deltas per Ruling 63-B.

- `specs/memory/product/distribution/plugin-packs.md` — **primary.** The
  "Additive-only (no uninstall this release)" claim REMOVED from the summary; the
  "full skill corpora are the `plugin-pack-content-libraries` backlog return; uninstall is
  `plugin-uninstall`" Differentiator pointer retired (both delivered); 4-skill rosters BY
  NAME for both packs; uninstall as usage-flow step 6 (exact inverse, files-first/ledger-last,
  never-silent drift restore, never-installed equivalence, exit-0 no-op for
  known-not-installed) + Mermaid uninstall edge; pack-agent skill refs machine-checked. The
  v0.1.61-verified "PluginStore port + JsonPluginStore adapter" seam wording kept verbatim —
  **NOT restated/reworded** (v0.1.61's A-1 remit, per SPEC §8).
- `specs/memory/product/distribution/public-asset-distribution.md` — NEW "Plugin uninstall
  reconciliation" paragraph in the plugin-projection section (stub restoration as the same
  core-projection slice, pack-only deletion, files-first/ledger-last, drift lines,
  never-installed equivalence, `repos/**` disjoint from the `[foreign]` surface) + the FR6
  plugin-aware ref sweep on the `public doctor` path; summary gains "+ uninstall
  reconciliation". v0.1.61 pass-A truths and v0.1.62 containment/symlink text intact.
- `specs/memory/architecture.md` — cli roster line → `plugin install|uninstall|list|doctor`;
  `models/plugin_pack.py` line notes the `with_added`/`with_removed` pair; the public/
  plugin-projection paragraph gains the `uninstall_plugin` inverse and the
  `_check_plugin_agent_skill_refs` sweep in `infrastructure/codex_doctor.py`. Rebased on the
  v0.1.61 closed state: the port-seam sentence (contract #9, `container.build_plugin_store()`,
  executed-path spy) is preserved verbatim, not restated.
- `specs/memory/tech-stack.md` — **minimal edit, drift-recorded** (see Drifts): the two
  §Plugin-inventory rows updated to the 4-skill rosters + uninstall mention. No dependency,
  tool, or model change — the SPEC §8 no-change expectation held for the stack itself.
- `specs/memory/product/agents/agent-orchestration.md` — **no change: assessed.** Roster
  (9 core + 3 plugin), tiers (`tier: 3` / `model: claude-sonnet-4-6`), and the
  install-gated routing claims are all unchanged by this release and still true as written.

## Dispositions

Disposition sweep per the ADR-11 vocabulary — the two consumed backlog items (SPEC §6; both
anchors SURVIVE → dispositioned + archived at CLOSURE, no SHIP-time archival). **Bug debt:
none picked (pure-backlog set), none filed mid-release** (the CI Chromium flake was
adjudicated non-bug — see Drifts); no bug terminal events.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/plugin-uninstall.md` | backlog | `delivered` (`delivered_in: v0.1.63`) | FR1/FR2/FR3, `a23a63d1` + `65419397`; anchor `infrastructure/public_assets.py#install_plugin` SURVIVES (gained its inverse `uninstall_plugin`); flipped this closure; PM `git mv` → `specs/_archive/v0.1.63/consumed-backlog/` |
| `specs/backlog/plugin-pack-content-libraries.md` | backlog | `delivered` (`delivered_in: v0.1.63`) | FR4/FR5/FR6, `22e88227` + `30561711` + `c273b33f`; anchor `core/models/plugin_pack.py#PluginPack` SURVIVES (its `skills` tuples grew to 4 per pack); flipped this closure; PM `git mv` → `specs/_archive/v0.1.63/consumed-backlog/` |

**Consumed-backlog archive payload** (PM writes this as
`specs/_archive/v0.1.63/consumed-backlog/consumed_backlog.json` — PE does not write
`_archive`):

```json
{
  "release": "v0.1.63",
  "consumed": [
    {
      "slug": "plugin-uninstall",
      "shipped_anchors": [
        "dadaia_workspace/infrastructure/public_assets.py#install_plugin"
      ],
      "note": "DELIVERED — v0.1.63 (archived at CLOSURE, anchor survives — install_plugin gained its exact inverse). NEW `dadaia plugin uninstall <pack>` (cli/commands/plugin.py: descriptor validation before workspace resolution, unknown pack => BadParameter exit 2; known-not-installed => exit 0 no-change, ADR-U2) delegating to NEW uninstall_plugin in FileSystemPublicAssetManager: staged-pack-tree enumeration as the removal set; profile-scoped (ADR-U3, Ruling 13 symmetry — claude-only profile never touches .codex/); core-stub re-projection over each pack agent (claude md + codex stub render, the same core-projection slice); deletion of pack-only skill/rule projections + now-empty dirs; [drift-restored]/[drift-removed] never-silent lines for hand-edited projections (ADR-U1 — runtime projections are lib-owned); unstaged pack => ledger-only drop + non-silent line; FILES FIRST, LEDGER LAST (ADR-U4 — interrupted uninstall is never a silent half-state, plugin doctor stays ledger-driven); ledger drop via the pure idempotent InstalledPlugins.with_removed through the container-wired PluginStore port (A-1-agnostic clause honored — v0.1.61's build_plugin_store pattern adopted at rebase). Never-installed equivalence proven BOTH same-run A-vs-B AND against the durable v0.1.60 golden (b) absolute anchor (Ruling 63-F; read-only fixture reuse, zero regen) with direct .codex stub-restore byte asserts; e2e leg (h) proves the re-installable state (install -> uninstall -> reinstall). RED-first: 13 pre-fix failures; AC-8(a)-(d) sabotages captured then reverted. Ship PR #120, squash 457e4e10.",
      "commits": ["a23a63d1", "65419397"]
    },
    {
      "slug": "plugin-pack-content-libraries",
      "shipped_anchors": [
        "dadaia_workspace/core/models/plugin_pack.py#PluginPack"
      ],
      "note": "DELIVERED — v0.1.63 (archived at CLOSURE, anchor survives — each PluginPack's skills tuple grew 1 -> 4). Full pack skill corpora under the ADR-C1 hard ceiling BY NAME: frontend-design += design-system-authoring + frontend-component-architecture + visual-review-protocol; devops += gitflow-release-engineering + container-build-and-deploy + cicd-security-hardening (pack totals 4 + 4; ai-engineer sole author; public-privacy law, [ok] public-privacy; frontend-ctx/design-ctx adapters referenced BY NAME never inlined, duplication-marker asserts extended). Wiring: pack.json skills[] == roster == on-disk dirs; design-specialist frontmatter += design-system-authoring + visual-review-protocol, frontend-engineer += frontend-component-architecture, devops-engineer += all three. Ceiling constants amended as a DELIBERATE RECORDED AMENDMENT (ADR-C2, RED-first shown per pack): _PACK_SKILL/_EXPECTED_SKILLS -> per-pack _PACK_SKILLS roster map. FR6 closes the ref blind spot: additive _check_plugin_agent_skill_refs in infrastructure/codex_doctor.py sweeps pack-agent skills: refs against public/skills/ UNION the pack's own plugins/<pack>/skills/ on the check_agent_skill_refs [drift] surface through public doctor (RED-first: pre-fix a bogus pack ref yielded ZERO lines). Recorded golden amendment: exactly 6 [ok] stage: lines per doctor golden (QA-verified exact; zero runtime-projection lines — golden (b) equivalence semantics intact). AC-8(e)/(f) sabotages captured then reverted. Ship PR #120, squash 457e4e10.",
      "commits": ["22e88227", "30561711", "c273b33f"]
    }
  ]
}
```

## Backlog returns

**None.** The plugin platform is complete for the 2-pack surface (SPEC §6 anticipated zero
returns and none emerged): a third pack, pack versioning/upgrade semantics, or network
distribution would each be a fresh operator demand, not a return from this release.

## Cross-release closure order (Rulings 63-B + ARCH63-1)

This release closes **third** in the fixed queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64 —
after v0.1.61 (port-seam + 9-contract truths preserved) and v0.1.62 (containment/symlink +
handoff-v1.2 truths preserved), before v0.1.64. The later-closing sibling (v0.1.64, the
`tier:` rename release) REBASES the shared atoms — `plugin-packs.md`,
`public-asset-distribution.md`, `architecture.md`, `tech-stack.md` — on THIS closure's state
(never reverting the uninstall/corpora/ref-check truths landed here), and its `catalog.json`
regen accumulates this closure's tldr/summary deltas. PM owns the phase schedule;
`ACTIVE.md` is a single pointer.

## Archive decision

**MOVE** — `specs/releases/v0.1.63/` moves to `specs/_archive/releases/v0.1.63/` via `git mv`
(PM/operator; PE issues no git mutations and runs no shell). PM then executes, in order:

1. `git mv` the 2 delivered backlog files (`plugin-uninstall.md`,
   `plugin-pack-content-libraries.md`) → `specs/_archive/v0.1.63/consumed-backlog/` and
   write `consumed_backlog.json` there (payload above, verbatim);
2. `dadaia memory catalog generate` (required — tldr/summary changed on 2 product atoms;
   regen includes the v0.1.61/62 prior deltas);
3. `dadaia specs doctor` + `dadaia backlog doctor` (both must exit 0);
4. the release-dir `git mv specs/releases/v0.1.63 specs/_archive/releases/v0.1.63`;
5. advance `ACTIVE.md` → `release: v0.1.64`, `phase: DEFINITION` per the queue schedule.

**Order law honored: the memory rebase + this disposition sweep land BEFORE `ACTIVE.md`
leaves CLOSURE.**
