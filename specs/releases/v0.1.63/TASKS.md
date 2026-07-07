# TASKS — v0.1.63 — Plugin Platform Completion (uninstall + full pack skill corpora)

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. At most one `[-]` at a time; W2 (T-63-20) and W3 (T-63-30)
have **disjoint write sets** (`public/plugins/frontend-design/**` vs `public/plugins/devops/**` — parallel `[-]`
permitted for that pair ONLY, and only if their `test_plugin_content.py` amendments are serialized: T-63-20
lands the per-pack roster-map refactor, T-63-30 only appends its pack's entries). No implementation task stages
`specs/backlog/**` (dispositioned at CLOSURE — T-63-60). Every sabotage (AC-8) is captured on its task line:
command + failing test + revert. Rebase-and-reverify note (SPEC §0) applies to every task.

## W0 — definition

- [x] T-63-01 SPEC/PLAN/TASKS authored from the 2026-07-07 code read (no-inverse `install_plugin`; `copy_file`
  reconciliation law answers restore-vs-foreign; staged-tree walk = removal set; ledger-driven plugin doctor ⇒
  equivalence AC; `check_agent_skill_refs` blind to pack agents; `test_plugin_content.py` ceiling constants =
  the RED-first lever; disjoint pack surfaces). Mandatory release-definition grill run on the picked set —
  operator unavailable ⇒ §9 operator-overridable ADRs U1–U4 + C1–C3. A-1 sequencing clause (SPEC §0.1) written
  into FR2/Non-goals/§8. **Marker normalized to `[x]` (QA63-3 — the definition set IS authored, matching the
  siblings).** <!-- AMEND:QA63-3 --> **Dual-review fold (2026-07-07, REJECT):** QA63-1..3 + ARCH63-1 +
  ARCHX/QAX folded with `<!-- AMEND:… -->` markers; PM Rulings 63-A/63-B/63-F in SPEC §0 (fixed order
  v0.1.61→62→63→64, v0.1.61 named in the W1 rebase clause; generalized shared-atom merge order; AC-2 absolute
  golden (b) anchor + `.codex` byte asserts). `Aprovado` after re-verify; definition commit.
  Owner: product-engineer (orchestrated).

## W1 — FR1/FR2/FR3 uninstall machinery

- [-] T-63-10 `with_removed` + `uninstall_plugin` + CLI `uninstall`. Owner: software-engineer. Write set:
  `core/models/plugin_pack.py`, `infrastructure/public_assets.py` (plugin block), `cli/commands/plugin.py`,
  `tests/unit/core/test_plugin_pack.py`, `tests/unit/cli/test_plugin_cli.py`, NEW
  `tests/integration/test_plugin_uninstall.py`. Preconditions: SPEC/PLAN/TASKS `Aprovado`; **v0.1.61 landed
  (fixed order — Ruling 63-A): rebase onto its `plugin.py`/`public_assets.py` state, adopt its
  store-construction pattern, re-run the suite post-rebase** <!-- AMEND:ARCHX-1 -->; base commit resolved
  (record lint-imports kept/ignore-cap counts at base; **pin the branch-point `pytest --collect-only -q` count
  in this task's fate ledger — QAX-4** <!-- AMEND:QAX-4 -->). Checklist:
  - `InstalledPlugins.with_removed(name)` — pure, idempotent (absent name ⇒ `self`); unit cases.
  - `uninstall_plugin(workspace_root, pack_name)`: staged-tree enumeration; profile-scoped (ADR-U3, same
    `_profile_harnesses` seam); core-stub re-projection over pack agents (claude md + codex stub render);
    delete pack-only skill/rule projections + now-empty dirs; `[drift-restored]`/`[drift-removed]` per
    hand-edited file (ADR-U1); unstaged pack ⇒ ledger-only + non-silent line; **files first, ledger last**
    (ADR-U4); ledger via the same store-construction pattern as `install_plugin` at base (A-1-agnostic — NO
    import of `core/protocols/plugin_store.py`).
  - CLI `uninstall <pack>`: descriptor validation before workspace resolution (unknown ⇒ `BadParameter` exit 2,
    stderr via `_norm_stderr` before asserts, empty stdout); known-not-installed ⇒ exit 0 `no change` (ADR-U2);
    success prints restored agents.
  - Tests, RED-first (pre-fix the `uninstall` verb does not exist): AC-1 CLI surface; **AC-2 never-installed
    equivalence — UPGRADED (Ruling 63-F / QA63-1)** <!-- AMEND:QA63-1 -->: same-run A-vs-B (stub bodies
    restored, zero pack files under `.agents/skills/`, ledger clean, `plugin doctor` `[not-applicable]`,
    `public_assets.doctor()` runtime surface A == B) **PLUS (i) the absolute anchor — side B's post-uninstall
    surface also compared against the durable v0.1.60 golden (b) never-installed baseline (read-only reuse,
    ZERO regen), and (ii) direct byte asserts in the absent-profile all-targets leg:
    `.codex/agents/{frontend-engineer,design-specialist}.toml` == the fresh core-stub render, zero pack rule
    projections remain**; the equivalence test carries `@pytest.mark.slow` + a ≤ ~15s bracket (QA63-2, two
    workspaces in one test) <!-- AMEND:QA63-2 -->; golden (b) fixture UNTOUCHED and its own test green;
    AC-3 double-uninstall no-op + files-before-ledger observable + multi-pack isolation (uninstall `devops`
    leaves `frontend-design` intact); AC-4 claude-only profile never touches `.codex/`; AC-5 drift lines
    emitted + `repos/**` untouched.
  - **Mutation-sanity NOW:** AC-8(a) skip ledger drop ⇒ AC-2 ledger assert FAILS; AC-8(b) skip skill deletion ⇒
    AC-2 zero-pack-files FAILS; AC-8(c) skip stub restore ⇒ AC-2 stub-body FAILS; AC-8(d) accept unknown pack ⇒
    AC-1 exit-2 FAILS. Each captured then reverted.
  - Fate ledger: `test_plugin_pack.py`/`test_plugin_cli.py` EXTENDED (existing cases survive byte-identical);
    `test_plugin_install_residue.py` ASSESSED (amend-with-rationale only if it pins no-removal);
    `test_json_plugin_store.py`, `test_plugin_projection.py`, goldens SURVIVE untouched.
  - Done: all W1 tests green; full gates green; conventional commits per marker protocol.
  - Parallelism: none (single owner, shared machinery files).

- [-] T-63-11 E2E pipeline leg. Owner: software-engineer. Write set:
  `tests/e2e/features/test_plugin_pipeline.py`. Precondition: T-63-10 `[x]`. Extend the existing pipeline with
  install→uninstall→**reinstall** (reinstall lands the real bodies again — proves uninstall leaves a
  re-installable state). **Wall-time bracket (QA63-2 — concrete, not "within budget"):** <!-- AMEND:QA63-2 -->
  the new leg is `@pytest.mark.slow` with a stated per-test bracket ≤ ~12s (the v0.1.60 module ran ~7.7s;
  one extra uninstall+reinstall cycle stays inside ~12s — measure and record the actual on this line).
  Existing legs SURVIVE. Done: e2e green, bracket recorded.

## W2 — FR4 frontend-design skill corpus

- [ ] T-63-20 Three frontend-design skills + wiring + recorded ceiling amendment. Owner: ai-engineer. Write set:
  `public/plugins/frontend-design/skills/{design-system-authoring,frontend-component-architecture,visual-review-protocol}/SKILL.md`
  (NEW), `public/plugins/frontend-design/pack.json`,
  `public/plugins/frontend-design/agents/{design-specialist,frontend-engineer}.md` (frontmatter `skills:` only),
  `tests/unit/infrastructure/test_plugin_content.py`. Precondition: T-63-10 `[x]`. Checklist:
  - Author the three SKILL.md bodies (generic, public-privacy law; frontmatter `name` == dir slug +
    `description`); `visual-review-protocol` references `design-ctx`/`frontend-ctx` BY NAME — the existing
    emit-block-marker duplication asserts extend to it; `design-system-authoring` cross-references
    `browser-frontend-implementation` (producer/consumer split), never duplicates its checklist.
  - Wire pack.json `skills[]` → 4; `design-specialist` frontmatter gains `design-system-authoring` +
    `visual-review-protocol`; `frontend-engineer` gains `frontend-component-architecture`.
  - **Recorded amendment (RED-first evidence):** run `test_exactly_the_two_named_skills_ship_per_pack` RED
    against the new skills, then refactor `_PACK_SKILL`/`_EXPECTED_SKILLS` into a per-pack roster map admitting
    exactly this pack's 4; cite the roster diff on this line at completion.
  - Done: AC-6 asserts green for this pack; `[ok] public-privacy`; full gates green.
  - Parallelism: disjoint with T-63-30 EXCEPT `test_plugin_content.py` — this task lands the roster-map refactor
    first; T-63-30 may only append after.

## W3 — FR5 devops skill corpus

- [ ] T-63-30 Three devops skills + wiring + roster append. Owner: ai-engineer. Write set:
  `public/plugins/devops/skills/{gitflow-release-engineering,container-build-and-deploy,cicd-security-hardening}/SKILL.md`
  (NEW), `public/plugins/devops/pack.json`, `public/plugins/devops/agents/devops-engineer.md` (frontmatter
  `skills:` only), `tests/unit/infrastructure/test_plugin_content.py` (roster-map APPEND only). Preconditions:
  T-63-10 `[x]`; T-63-20's roster-map refactor landed (or run sequentially after T-63-20). Checklist:
  - Author the three SKILL.md bodies (generic; frontmatter law; `cicd-security-hardening` grounded in SHA-pin /
    least-privilege / secret-hygiene practice — content stays generic, no repo-specific names).
  - Wire pack.json `skills[]` → 4; `devops-engineer` frontmatter gains all three.
  - Roster map append for devops (recorded, RED-first shown).
  - **Mutation-sanity:** AC-8(f) drop a skill from pack.json keeping its dir ⇒ roster contract FAILS → revert.
  - Done: AC-6 green for this pack; `[ok] public-privacy`; full gates green.
  - Parallelism: see T-63-20 note.

## W4 — FR6 plugin-aware skill-ref integrity

- [ ] T-63-40 Extend the ref check to pack agents. Owner: software-engineer. Write set:
  `infrastructure/codex_doctor.py` (or a sibling checker per ADR-C3), `infrastructure/public_assets.py` /
  `cli/commands/public.py` call-site wiring if needed, NEW/extended tests in
  `tests/unit/infrastructure/` (+ `test_plugin_content.py` full-sweep assert). Preconditions: T-63-20 + T-63-30
  `[x]` (rosters final). Checklist:
  - Sweep `public/plugins/<pack>/agents/*.md`: every `skills:` ref resolves against `public/skills/` ∪ that
    pack's `plugins/<pack>/skills/`; `[drift]` prefix; flows through the existing `public doctor` ref-drift
    handling (`public.py:47-50`, non-zero on drift).
  - **RED-first:** demonstrate pre-fix a bogus pack-agent ref yields zero report lines; post-fix `[drift]`.
  - Full-sweep contract: all pack-agent refs for BOTH packs resolve (W2/W3 wiring proven doctor-side).
  - **Mutation-sanity:** AC-8(e) make the sweep ignore pack agents ⇒ AC-7 post-fix test FAILS → revert.
  - Fate ledger: existing core-agent `check_agent_skill_refs` cases SURVIVE byte-identical (additive sweep).
  - Done: AC-7 green; full gates green.

## W5 — ship

- [ ] T-63-50 Ship gates + live-instance propagation. Owner: software-engineer (devops-engineer if pack
  installed; else PM surfaces commands). Preconditions: T-63-10..40 `[x]`. Checklist: AC-9 full gates (ruff
  format/check, mypy --strict, unpiped pytest, lint-imports kept/ignore-cap == base counts, specs doctor exit 0,
  backlog doctor exit 0); `dadaia public stage` → `public doctor` → `public install --target all` → confirming
  `public doctor` (`[ok] public-privacy`, exit 0); frozen no-steal suite zero-diff; qa-engineer alpha review;
  security-reviewer APPROVE handoff per push cycle (`metrics.commit_sha`). Done-evidence: command outputs +
  SHAs recorded for CLOSURE Validations.

## CLOSURE

- [ ] T-63-60 CLOSURE.md (summary, tasks+SHAs, validations triples, drifts, memory updates, dispositions,
  archive decision). Owner: product-engineer. Dispositions: `specs/backlog/plugin-uninstall.md` +
  `specs/backlog/plugin-pack-content-libraries.md` → `DELIVERED — v0.1.63`. Memory per SPEC §8: plugin-packs
  atom primary edit (uninstall + rosters; REMOVE "Additive-only"; do NOT restate the PluginStore-port seam —
  v0.1.61's A-1 remit). **Coordination clause EXTENDED (ARCH63-1) + merge order (Ruling 63-B):**
  <!-- AMEND:ARCH63-1 --> <!-- AMEND:ARCHX-2 --> this release closes after v0.1.61/62, before v0.1.64 —
  REBASE `plugin-packs.md`, `public-asset-distribution.md`, AND `architecture.md` on the siblings' closed
  state (never revert their corrections); catalog regen includes all prior tldr/summary deltas.
  public-asset-distribution atom; architecture.md module-map lines; tech-stack no-change reason; catalog regen
  (`dadaia memory catalog generate`) BEFORE ACTIVE.md moves off CLOSURE. Archive: `git mv` to
  `specs/_archive/releases/v0.1.63/`.
