# Verification Audit — Specs, Memory & Constitution Lane

- **Auditor:** project-auditor (adversarial verification pass; no sub-agents — all evidence first-hand)
- **Target:** repos/dadaia-workspace @ feature/v0.1.10 (HEAD `429ed03`)
- **Date:** 2026-06-10T140553Z
- **Prior audits:** 2026-06-10T010550Z (spec/ledger 4/10, memory 4/10) → v0.1.10 remediation → 2026-06-10T052944Z (9.0, SHIP)
- **Mandate:** operator distrusts self-certification; every claim verified against disk and code. Read-only; only this report written.

**Scores:** Spec/ledger fidelity **9.0/10** · Memory fidelity **8.5/10** → **FAIL the ≥9-both bar by one dimension** (3 MEDIUM memory findings, all line-level fixable; no CRITICAL, no HIGH, no kernel regression).

---

## 1. Constitution truth table (§ by §, against code at HEAD)

| § | Claim cluster | Verdict | Evidence |
|---|---|---|---|
| §0 Identity | Declarative; root whitelist (9 entries incl. CLAUDE.md/prompt.md); `.dadaia/` subdirs | **TRUE** | Matches root AGENTS.md + tmp-file-guardrail rule; instance reality matches. No normative conflict found. |
| §1 SDD binding | Approval + task ownership required | **TRUE as discipline** | Correctly NOT claimed as mechanism here; §8 honesty clause carries the split. |
| §2 Public generic | No private names in public assets | **TRUE** | Spot-checked `public/` agents/skills/rules — generic. `public/scripts/__pycache__/` hygiene residue is acknowledged in backlog residual #7 (not a §2 violation). |
| §3 Memory = truth, Markdown only | `.html/.yaml/.yml` "must not be committed" | **TRUE** | `specs/memory/**` contains only `.md` + `catalog.json` + `.gitignore`. NOTE: §3 states this as *law* (discipline) — correct. The sdd-gate-v3 *memory atom* upgrades it to gate mechanism — false; see Memory finding M-1. |
| §4 Runtime parity honesty | Claude = real block; Codex = trusted-mode guardrail; opencode = advisory | **TRUE** | `infrastructure/runtime_config.py:66-99` (Claude PreToolUse write matcher + PostToolUse `*`), `:154-190` (Codex `^(apply_patch\|Edit\|Write)$` Pre, matcher-less PostToolUse). OpenCode advisory documented in `architecture.md` parity table + doctor `[unsupported]`. |
| §5 Source repo clean | No runtime projections at repo root | **TRUE** | `git status` clean; no `.dadaia/`, `.claude/` etc. at repo root. |
| §6 Layering | core imports nothing app-level; features no CLI; container composition | **TRUE (enforced)** | `setup.cfg` import-linter contracts (`features → infrastructure` ban :29, `features → subprocess` ban :60, `core → OS primitives` ban :80) + ignore-cap contract test. 7 `ignore_imports` debt acknowledged in `architecture.md` (ADR-1 transitional) + backlog `features-import-infrastructure-direct-debt.md`. |
| §7 Lifecycle matrix | 8 phases, owners, classes; audit output = committed MD in `specs/audits/<ts>-<session_id_8chars>/` | **TRUE except naming practice** | Phase/class/lease semantics all verified in §8 row below. **Practice violation:** the 4 most recent audit dirs (`2026-06-09T075056Z`, `2026-06-10T010550Z`, `2026-06-10T052944Z`, `2026-06-10T140553Z`) carry **no session-id discriminator and non-canonical timestamp form** — violating the §7/§8/§12.3 collision-safe naming law the constitution itself states. The law is fine; the auditor's own output drifted. Finding S-2. |
| §8 ADDITIVE/MUTATING + context-relative classifier | in-repo `specs/bugs\|backlog\|audits` ADDITIVE; in-repo no-class ⇒ MUTATING never UNGATED; `.dadaia/` classes root-only | **TRUE** | `gate_policy.py:50-59` (prefix tables), `:150-162` (`_context_relative`), `:165-193` (`classify_path` — in-repo unmatched → MUTATING :180; root tail preserved). |
| §8 lease record schema `{context, release, session_id, mode, pid, acquired_at, heartbeat, ttl}` | **TRUE** | `lease.py:232-252` (`_new_record`) — exact field set. |
| §8 TTL=120 + PID veto; dead/absent pid ⇒ TTL verdict | **TRUE** | `lease.py:88` (`LEASE_TTL_SECONDS = 120`); `core/lock_liveness.py:is_stale` ("TTL is the floor; PID is the veto"; probe only keeps an otherwise-stale record alive); probe injected at `hooks/sdd_gate.py:39-62`, never imported by features (`lease.py:63-72`). |
| §8 heartbeat: PostToolUse, sid from harness stdin payload, no env required; holder renews past TTL | **TRUE** | `hooks/sdd_post_gate.py:88-106` (renews every lease this sid holds, never first-ALIVE), `_common.py:102-116` (`resolve_session_id`: env override → stdin `session_id`); `lease.py:377-385` (holder-safe renew past TTL), `:353-364` (.ptr incumbent RENEW). |
| §8 acquire AND renew under O_EXCL CAS | **TRUE** | `lease.py:334` (acquire CAS), `:441` (renew_heartbeat inside the same sentinel CAS). |
| §8 stamped pid = long-lived harness pid | **TRUE** | `hooks/sdd_gate.py:65-96` (`_resolve_holder_pid`: payload `harness_pid/parent_pid/ppid` → `os.getppid()`), threaded via `gate_policy.evaluate(holder_pid=…)` :271-280 → `lease.acquire(pid=…)`. |
| §8 session mode channel: "env → session-record mode → default IMPLEMENTATION" | **PARTIAL — chain incomplete** | Code has a **4-step** chain: env → self-keyed session record → **context-incumbent pointer with liveness anti-downgrade guard** → IMPLEMENTATION (`hooks/sdd_gate.py:131-205`, NF-2/NF-4 rc-2 fixes). The constitution omits step 3 entirely (zero occurrences of "incumbent" in `constitution.md`), while `workspace-protocol` rule §1 and the sdd-gate-v3/architecture atoms state it. The constitution was rewritten in wave 6 (`da719cc`) **before** rc-2 (`fc388d7`) and never re-amended. An agent reading only the constitution would conclude a default `bind --mode read` cannot govern a harness session — i.e. it describes the pre-NF-2 broken world. Finding S-1 (MEDIUM). |
| §8 READ non-acquiring; bind default `read` | **TRUE** | `gate_policy.py:95,110-112,262-267` (READ blocked before any lease call); `cli/commands/context.py:295-301` (`--mode` default `"read"`), `:339` (`--release` required for lease-taking), `:368-377` (BOUND_ prefix mapping). |
| §8 reclaim-iff-stale / yield-iff-live-foreign; no rebind/relaunch/steal instruction | **TRUE** | `lease.py:265-282` (`_yield_message` — hard constraint honored: message names no manual ceremony); `gate_policy.py:281-288` (LockHeldError → BLOCK; any other lease error → fail-open ALLOW). READ block message `gate_policy.py:101-107` names a one-time operator bind, not a mid-flow relaunch — consistent with the forbidden-law carve-out as written. |
| §8 honesty clause (D-2): envelope = file-write tools only; gate reads no SPEC/PLAN/TASKS/markers | **TRUE** | `_common.py:30-40` (WRITE_TOOLS); `grep TASKS\|Aprovado\|'\[-\]'` over `hooks/*.py` + `gate_policy.py` → no functional reference (docstrings only). The honesty clause itself is the v0.1.10 fix for prior CONF-4 — verified honest. |
| §9 coordinator + dispatcher purity; ai-engineer carve-out | **TRUE as architecture/discipline** | Correctly framed: lease exclusivity is mechanical (gate blocks any second MUTATING session regardless of persona — `lease.acquire`), persona attribution is discipline. No persona claim of mechanism found. |
| §10 backlog process; PM sole owner | **TRUE as convention** | Consistent with `backlog-ownership` rule (which explicitly de-gates it — no contradiction: §10 asserts ownership, not gate enforcement; `specs/backlog/` is ADDITIVE in `gate_policy.py:50-54`). |
| §11 checkpoint-vs-gate terminology; spec-review QA-first ordering; 3 channels | **TRUE** | Terminology section reserves "gate" for sdd_gate + ci-preflight — matches code reality. 3-channel model consistent with AGENTS.md + handoff-emitter skill. No `specs/releases/<id>/evidence/` subtree exists (verified in archive). Channel-3 naming practice deviates (see §7 row / S-2). |
| §12 anti-slop | **TRUE in law; one live violation of 12.3** | "No fact in two sources": `product/index.md` and `catalog.json` are two generated views of atom frontmatter that now **disagree** (index stale at 2026-06-09, catalog regenerated 2026-06-10) — see Memory finding M-3. The law is right; the artifact pair violates it. |
| §13 memory canon | **TRUE** | All four areas exist; `quality-assurance.md` at top level ✓; product/ folder catalog with index + per-feature atoms ✓; forbidden-section scan over all 30 atoms: zero real `Changelog/History/Histórico/Versions` headings (matches in architecture.md/sdd-hotfix-track.md are descriptions of the rule / of a backlog-file section, not actual headings). |
| §14 roster | **TRUE** | `public/agents/` = exactly 12 files: 9 core + 3 plugin stubs. Stub exemption stated consistently with `plugin-scope` rule. Model assignments cross-checked (see memory §tech-stack row). |

**Constitution net verdict:** every load-bearing §8 kernel claim is implemented as written — the v0.1.10 rewrite is honest, including its own enforcement-scope limits. One substantive gap (S-1, mode-chain missing the rc-2 incumbent step) and one practice violation of its naming law (S-2).

---

## 2. Memory atom inventory & verdicts

30 atoms (3 core + `quality-assurance.md` + 26 product across agents/distribution/panel/philosophy/platform/sdd). Frontmatter: all 30 carry valid `memory-frontmatter-v1` (slug/title/category/tldr/summary/tags/agent_tier/token_estimate/last_updated/release_origin) — `dadaia specs doctor` 0 errors; all `tldr` ≤160 chars. Forbidden history sections: none. Current-truth-not-history: PASS across the set (release_origin in frontmatter only; bodies describe the present).

### Deep-verified atoms

| Atom | Verdict | Evidence |
|---|---|---|
| `architecture.md` | **TRUE in all spot-checks but one perms nit** | Verified against code: lease schema (`lease.py:243-252`), acquire decision tree 1-4 (`lease.py:351-402`), pid-veto + long-lived pid (`sdd_gate.py:65-96`), heartbeat renews-what-this-sid-holds (`sdd_post_gate.py:88-106`), **full 4-step mode chain incl. incumbent + anti-downgrade liveness** (`sdd_gate.py:131-205`) — post-rc-2 contract as CLOSURE promised. Hooks package = 6 modules ✓ (`wc -l hooks/*.py`). Rules folder = 8 files ✓. CLI subcommand list ✓ (21 dirs under `cli/commands/`). "Stores que não existem" ✓ (no Lock-3/semaphore on disk or in code). Mermaid blocks syntactically sound. **Nit (LOW, M-6):** "lock file: `0600`" — no code path chmods the lock *file*; `_lock_dir` attempts `0700` on the dir and the hook call path passes no `permission_setter` (`lease.py:121-142`, `_write_record:199-207`). Aspirational claim. |
| `product/sdd/sdd-gate-v3.md` | **2 findings (M-1, M-2)** | Class table, RULE READ chain, acquire tree, heartbeat, fail-open/fail-closed split, "what is NOT mechanism" — all verified TRUE at file:line. **M-1 (MEDIUM, theater):** RULE A claims "Formatos legados `.html`, `.yaml`, `.yml` → block sempre" as gate enforcement — **no format-based logic exists** in `gate_policy.py`, `sdd_gate.py`, or any hook (grep: zero hits; the only `.html/.yaml` constants in `spec_context/` are secret-scan suffixes, `service.py:69-88`). Constitution §3 correctly states this as committed-format *law*; the atom falsely promotes it to mechanism — in the section titled "o que o gate realmente enforça". **M-2 (MEDIUM, internal contradiction):** body (correct, post-rc-2) says Codex PostToolUse ships **without** matcher = match-all; the atom's own "Hook injection por runtime" table says Codex PostToolUse uses "mesmo write matcher" — the pre-N-2 broken state. Code truth: `runtime_config.py:187-190` (matcher omitted). The table row contradicts both the code and the atom's own body, and would re-teach the heartbeat-starvation bug. |
| `product/platform/context-management.md` | **1 finding (M-4, LOW)** | Bind semantics (default read, BOUND_ prefixes, `--release` required, `--print-env` escape) verified against `cli/commands/context.py:280-400` ✓. Lock table (L1/L2/TTL-lease) ✓. Mode table ✓. `dadaia lock steal` exists ✓ (`cli/commands/lock.py:38-60`, refuses live). **M-4:** §Propósito states the mode chain as "(env → session record → IMPLEMENTATION)" — omits the incumbent step that the same atom's frontmatter/summary and sdd-gate-v3 carry (same NF-2 lag as constitution S-1, one parenthetical). |
| `tech-stack.md` | **TRUE** | Deps vs `pyproject.toml` row-by-row ✓ (typer >=0.25/extras, rich >=13,<16, mistune >=3.0,<4.0 ≡ "~=3.0", jinja2 direct + scaffolder rationale, jsonschema, import-linter dev). Model tiers vs `public/agents/*.md` frontmatter ✓ (fable-5 ×5, opus-4-8 ×4, sonnet stubs ×3) and `core/model_registry.py:108-126` ✓. Closure nit-fixes (jinja2/rich) confirmed applied. Omission: `pytest-randomly` dev dep unlisted (INFO). |
| `quality-assurance.md` | **1 nit (M-5, LOW)** | Layer taxonomy and local-no-coverage policy match `ci.yml` job design. **M-5:** "CI runs 7 jobs" — the 7 named exist (lint, typecheck, unit-fast, contract-coverage, integration, e2e-python, e2e-panel) but the workflow has ~14 (importability-smoke, unit-fast-cross, contract-coverage-cross, repo-hygiene, pr-title, hotfix-branch-name, verdict-gate). Stale count since the v0.1.8 3-OS matrix; the cross-OS legs are correctly described in `cross-platform-portability.md`, so this is a count error, not missing knowledge. |
| `product/index.md` + `catalog.json` | **1 finding (M-3, MEDIUM)** | `catalog.json` fresh (generated 2026-06-10T06:15Z) and matches atom frontmatter ✓ (CAT-1 green). **M-3:** `index.md` (last touched 2026-06-09, pre-closure) is **stale**: its `sdd-gate-v3` row still reads "(v0.1.6): … <=175 lines" and `context-management` row still reads "bind exports DADAIA_SESSION_ID" — both contradict the current frontmatter, the catalog, and the code. Two generated views of one source now disagree (§12.3 violation). CLOSURE's "index.md / catalog.json — no change" is half-false: catalog WAS regenerated, index was not. Doctor CAT-1 checks only catalog slugs, so this drift is invisible to tooling. |

### Remaining 24 atoms (scan-level)

Frontmatter valid, structure consistent (Propósito/Fluxo/Trigger/Diferencial/Estado runtime/Dependências present in product atoms), no history sections, no duplication beyond intended summaries-pointing-at-§ (atoms cite constitution rather than restate — anti-slop §12.3 honored). No orphan atom describing removed behavior found (the "stores que não existem" anti-resurrection blocks are deliberate). Information distribution is sensible: gate mechanics in sdd-gate-v3, bind/lease lifecycle in context-management, kernel synthesis in architecture, QA in quality-assurance — no misplaced facts found beyond M-5's stale count.

---

## 3. Specs structure & format assessment

| Artifact | Verdict | Evidence |
|---|---|---|
| `releases/ACTIVE.md` | **VALID** | `release: none` / `phase: none`; no live release dir; matches the archive move commit `5be4f01` ("same commit" claim verified by commit content). |
| `_archive/releases/` layout | **COMPLETE, flat for v0.1.9/v0.1.10** | Both carry SPEC/PLAN/TASKS/CLOSURE, all `**Status:** Aprovado`. v0.2.0 internal milestone collision repaired: `{v0.1.6..v0.1.9}` subdirs → `alpha-1..4` (`da719cc`), root-level `0.1.x` → `v0.1.x`; each alpha-N SPEC retains its original milestone id + "Milestone within: v0.2.0" header, so archaeology is recoverable. |
| v0.1.10 CLOSURE evidence triples | **11/11 commits + all named tests verified** | Commits `a1f331f 4acecdf 9611f43 87b333b 09c919e da719cc c7391a0 5374495 fc388d7 9ca2d2a f77e96c` all exist. Named regressions all exist on disk: `test_hook_acquired_holder_no_steal_while_driver_alive_then_takeover`, `test_lease_theft_incident_in_repo_additive_does_not_steal` (:138), `test_lease_theft_dual_session_foreign_mutating_still_blocks_live_holder` (:199), `test_holder_busy_foreign_additive_allowed_and_never_named` (:219), `test_resolve_mode_falls_back_to_context_incumbent` (:391), `test_codex_posttooluse_heartbeat_fires_on_all_tools` (:1689), `test_context_bind_no_mode_exits_zero_default_read` (:239), plus `test_pre_push_gate_venv_probe.py`, `test_session_store_ownership.py`, `test_model_registry_doctor.py`, `test_no_pollution.py` files. Cited handoff `2026-06-10T024848Z-software-engineer-t-010-03-…` exists. rc-2 section is an exemplary honesty ledger (work outside TASKS.md disclosed with its own table). |
| CLOSURE inaccuracies | **2 LOW** | **S-3:** R6 row + commit message claim a "mapping README" for the archive renames — **no README exists anywhere under `specs/_archive/`** (`find` empty; `git show da719cc --name-status` adds none). Mapping is recoverable from milestone headers, but the named evidence artifact is missing. **S-4:** "per-task evidence is the task's handoff JSON (filenames carry the task id)" — only 10 distinct `t-010-NN` handoffs exist for 29 tasks (waves shared handoffs); over-claims granularity. |
| `specs/bugs/` (38 files) | **Coherent; format inconsistent (S-5, LOW)** | All 38 have frontmatter with name/status/severity. Exactly one Open: `ci-preflight-checks-hardcode-poetry-run` — **legitimately open** (filed at HEAD `429ed03`, after closure; well-formed per the guardrail template; targets v0.1.11; CLOSURE's "0 Open at closure" remains true). Sampled Closed bugs reference real resolutions; v0.1.10-era named regressions all exist. **Format debt:** 4 distinct done-tokens across the corpus (`Closed`/`Resolved`/`resolved`/`Fixed`) and severity casing chaos (`High`/`HIGH`/`Critical / Blocker`) vs the guardrail's canonical `Open\|Closed` + upper-case severities; legacy bug `gate-cross-context-lock-contamination` (Closed 0.1.7) names regression `test_no_cross_context_lease_contamination` which **no longer exists** (retired with the bash gate; protection now lives in `test_classifier_reroot_matrix.py` — behavior covered, record stale). |
| `specs/backlog/` | **WELL-FORMED** | `v0.1.11-audit-residuals.md`: Status CANDIDATE, 10 ranked residuals traceable to re-audit §5, indexed from `candidates.md:15` ✓. Honest scope notes (already-fixed items excluded explicitly). |
| Pattern consistency | **Releases/CLOSUREs: yes. Bugs: no (legacy half).** | v0.1.9 + v0.1.10 CLOSUREs share the template (Summary/Tasks/Validations/Drifts/Memory updates/Backlog returns/Archive decision) with evidence triples. Bug corpus splits into guardrail-era (canonical) and pre-guardrail (free-form) — see S-5. |

---

## 4. Doctor warnings interpretation (19 WARN, 0 ERROR)

| Group | Count | Real debt? |
|---|---|---|
| `token_estimate` drift (context-management 24%, cross-platform-portability 63%, workspace-init 33%) | 3 atoms | **Yes, minor but operator-relevant:** these estimates feed agents' self-pull token budgeting; a 63% understatement misleads context planning. Already captured in backlog residual #10 ("token_estimate WARN cleanup"). |
| Unknown headings vs curated allowlist (cross-platform-portability ×5, multi-platform-parity ×1, sdd-gate-v3 ×1) | 7 warns / 3 atoms | **Cosmetic-to-low:** the headings are legitimate content; the `lint-memory-atoms.py` allowlist lags atom evolution. NOT explicitly listed in residual #10 — worth folding in, else the WARN noise normalizes ignoring the linter. |
| SPEC-DOC-027 legacy archive names (`ctx-inject-v2-drift-fix-v1`, `memory-markdown-source-v1`, `v0.1.4.1`..`v0.1.4.6`, `v0.1.4.3-report-retention`) | 9 | **Accepted legacy, explicitly preserved-until-renamed** by the invariant's own wording; in residual #10. Pre-semver history; renaming would cost archaeology for zero behavior. Fine to carry. |

None of the 19 hides an error-class problem. The one warning class the operator should actually care about is token_estimate drift (budget honesty).

---

## 5. Prior-finding verification table (2026-06-10T010550Z, spec/ledger + memory dimensions)

| Prior finding | Verdict today | Evidence |
|---|---|---|
| DRIFT-1 (CRIT, memory): architecture.md ADDITIVE-unconditional false in-repo | **SOLVED** | Classifier context-relative (`gate_policy.py:165-180`); in-repo `specs/bugs` ADDITIVE with zero lease I/O; regression `test_lease_theft_incident_in_repo_additive_does_not_steal` exists; atom rewritten to the true contract. |
| DRIFT-2 (HIGH, memory): "heartbeat a cada PreToolUse" false / post-gate no-op | **SOLVED** | `sdd_post_gate.py` resolves sid from stdin payload, renews all held leases (:88-106); Claude matcher `*`, Codex matcher-less (`runtime_config.py:99,187-190`); atom + constitution describe the real path. Residual: M-2 stale table row in sdd-gate-v3. |
| DRIFT-3 (HIGH, constitution): ADDITIVE-never-lease false in-repo | **SOLVED** | Same kernel; constitution §8 now states the context-relative re-root explicitly and truthfully. |
| DRIFT-4 (HIGH, rules/skills): gate claimed to read Aprovado/markers | **SOLVED** | Constitution §8 honesty clause; AGENTS.md "Agent discipline (not hook-enforced)"; `dadaia-task-manager` SKILL.md:25-26 + :111-129 explicit "markers are discipline, not a hook check"; grep over hooks confirms zero marker logic. |
| DRIFT-5 (HIGH, spec): ACTIVE.md stale phase, no v0.1.9 CLOSURE | **SOLVED** | v0.1.9 retro-CLOSURE exists and is Aprovado; v0.1.10 closed + archived; ACTIVE `none/none`. |
| DRIFT-6 (MED): gate_policy docstring named the bash gate as enforced | **SOLVED** | `gate_policy.py:1-10` names the Python hook package; bash quartet absent from `public/scripts/` (only `pre-push-ci-gate.sh` remains, as documented). |
| DRIFT-7 (MED): stale parity test pinning bash gate | **SOLVED** | Bug Closed with `superseded_by: v0.1.8` recorded; test now asserts plugin projection (`test_opencode_parity_hardening.py::test_sdd_gate_plugin_projected`). |
| CONF-5/§4 ledger (archive id collision, no state-transition invariants) | **SOLVED** | v0.2.0 internals → alpha-N (`da719cc`); SPEC-DOC-024/026/027/028/029 live in `features/specs/doctor.py`; doctor 0 errors. Residual: claimed "mapping README" missing (S-3). |
| CONF-9 (MED): duplicated hand-maintained truth drifts | **MOSTLY SOLVED, one new instance** | Model registry single-source + key-equality contract ✓. But index.md vs catalog.json (M-3) is a fresh instance of exactly this class — generated-pair without a freshness contract. |

All nine prior spec/memory-lane findings are genuinely remediated at root cause; none reopened. The residuals found in this pass are new, smaller, and mostly rc-2-lag artifacts.

---

## 6. Scores

### Spec/ledger fidelity: 9.0/10

Base 10, deductions:
- **−0.5 S-1 (MEDIUM):** constitution §8 mode-resolution chain omits the context-incumbent step (rc-2 NF-2) — contradicts code (`sdd_gate.py:131-205`), the workspace-protocol rule, and two memory atoms; describes the pre-fix world for the bind-read flow.
- **−0.25 S-2 (LOW):** §7/§8/§12.3 audit-dir collision-safe naming law violated by all four most recent audit directories, including the two produced by the v0.1.10 cycle itself.
- **−0.25 S-3/S-4/S-5 (LOW, aggregated):** CLOSURE names a "mapping README" that doesn't exist; "per-task handoff" over-claim (10/29 task-id handoffs); bug-corpus status/severity token inconsistency + one Closed-CRITICAL bug naming a deleted regression test.

### Memory fidelity: 8.5/10

Base 10, deductions:
- **−0.5 M-1 (MEDIUM, theater):** sdd-gate-v3.md claims the gate blocks `.html/.yaml/.yml` memory writes "sempre" — no such mechanism exists anywhere in the gate. A false deterministic-enforcement claim surviving in the atom rewritten for honesty.
- **−0.5 M-2 (MEDIUM, contradiction):** sdd-gate-v3.md hook-injection table says Codex PostToolUse uses the write matcher — contradicts `runtime_config.py:187-190`, the atom's own body, and re-documents the N-2 heartbeat-starvation bug.
- **−0.5 M-3 (MEDIUM, stale generated view):** product/index.md two cycles stale vs catalog.json/frontmatter ("v0.1.6 … <=175 lines", "bind exports DADAIA_SESSION_ID"); CLOSURE's "index.md/catalog.json — no change" half-false; invisible to CAT-1.
- **0 net for M-4/M-5/M-6 (LOW; absorbed in the above band):** context-management one-parenthetical mode-chain omission; QA "7 jobs" undercount; "lock file 0600" aspirational.

**Verdict vs operator bar (both ≥9): FAIL — memory at 8.5.** No CRITICAL/HIGH anywhere; the 9.0 re-audit was not fabricated — the kernel and ledger claims it certified are real. The gap is three line-level memory defects of exactly the classes (theater, self-contradiction, duplicated-truth drift) this workspace has declared war on.

---

## 7. Residual actions ranked

1. **(M-1)** Delete or re-attribute the legacy-format sentence in `specs/memory/product/sdd/sdd-gate-v3.md` RULE A: either state it as committed-format law (constitution §3 / doctor LINT-1), or implement the format check in `gate_policy` — never claim it as live gate mechanism. Owner: product-engineer (memory, DEFINITION/CLOSURE) or fold into v0.1.11.
2. **(M-2)** Fix the sdd-gate-v3.md "Hook injection por runtime" table: Codex PostToolUse row → matcher-less match-all. Owner: product-engineer.
3. **(M-3)** Regenerate `specs/memory/product/index.md` from frontmatter (same generator as catalog.json) and extend CAT-1 (or the generator) to cover index.md freshness so the pair can never silently diverge again. Owner: product-engineer + software-engineer (doctor check).
4. **(S-1)** Amend constitution §8 "Session mode channel" to the 4-step chain (env → self record → live-checked context incumbent → IMPLEMENTATION). Requires operator confirmation per the §0/§8 rewrite precedent. Owner: product-engineer.
5. **(S-2)** Either enforce the `<ts>-<session_id_8chars>` audit-dir convention (doctor WARN on non-conforming new dirs) or relax the law to match the ISO-stamp practice — currently law and practice disagree. Owner: product-engineer (law) / software-engineer (check).
6. **(S-5)** Normalize bug frontmatter tokens (one pass: `Fixed/Resolved/resolved` → `Closed`; severities upper-case); update the stale regression pointer in `gate-cross-context-lock-contamination.md` to the live matrix tests. ADDITIVE writes, any agent. 
7. **(S-3)** Add the promised archive mapping README under `specs/_archive/releases/v0.2.0/` (4 lines: alpha-N ↔ original milestone id) or strike the claim from the CLOSURE validation row. Note: CLOSURE itself is FROZEN-adjacent once archived — prefer adding the README.
8. **(M-5/M-6/M-4 + doctor WARNs)** Fold into backlog residual #10: QA atom job count, lock-file 0600 wording, context-management parenthetical, token_estimate refresh, heading-allowlist sync.

— end of report —
