# FINAL RE-AUDIT SYNTHESIS — dadaia-workspace v0.1.10

- **Auditor:** project-auditor (synthesis over 4 evidence lanes + own drift-anchor pass)
- **Date:** 2026-06-10T052944Z (final synthesis at HEAD `9ca2d2a`, branch `feature/v0.1.10`)
- **Baseline:** `specs/audits/2026-06-10T010550Z/index.md` — overall **5/10**
- **Operator bar:** ≥ 9/10 on ALL six dimensions
- **Evidence lanes:** `software-architect.md` (rc-2 final 9.0 at `9ca2d2a`), `qa-engineer.md`
  (rc-2 9.25 at `fc388d7`), `ai-engineer.md` (rc-2 9.0 at `fc388d7`),
  `security-reviewer.md` (9.0 at `f77e96c`)
- **Coordinator-supplied green run at HEAD:** `pytest -p no:cacheprovider -q` → 2795
  passed, 8 skipped, 1 xpassed, exit 0; ruff/mypy --strict clean; doctors 0.

---

## 1. Compliance scorecard

| Dimension | Original | FINAL | Source | Notes |
|---|---|---|---|---|
| Spec/ledger fidelity | 4 | **9** | own drift-anchor pass | doctor 0 errors with SPEC-DOC-024..029 live; 29/29 unique `[x]`; archive repaired; v0.1.9 retro-closed; 3/3 sampled ACs verified in code; only gap = CLOSURE.md (the authorized next step) + 1 LOW label nit |
| Memory fidelity | 3 | **9** | own drift-anchor pass | every load-bearing kernel claim in `architecture.md` / `sdd-gate-v3.md` / `context-management.md` verified line-for-line at HEAD; 2 LOW + 1 INFO nits in tech-stack/wording |
| Architecture | 6 | **9.0** | architect lane (rc-2 final, HEAD) | lease-theft family D1/D2/D3 closed at root cause end-to-end; NF-1/NF-2/NF-4 all fixed with falsifying tests; APPROVED on both lane gates |
| Test quality | 5 | **9.25** | qa lane (rc-2) | ratchet baselines burned to zero; real-topology two-actor e2e; 0 Open bugs, 8/8 named regressions; HEAD adds the NF-4 falsifying tests on top |
| AI-surface enforcement honesty | 5 | **9.0** | ai lane (rc-2) | C-1..C-14 + N-1..N-3 closed code+text+projection; "remaining theater: none" — confirmed at HEAD (NF-4 wrinkle resolved, see §2) |
| Security | 7 | **9.0** | security lane | F-1..F-8 closed/accepted in code; new surface adversarially probed; no secrets/CVE≥9 in runtime closure; rc-2/rc-3 diff caveat covered (§2) |
| **Overall** | **5** | **9.0** | min-dimension ≥ 9; weighted ≈ 9.05 | **SHIP BAR MET** |

---

## 2. Cross-validation notes (lane vs lane, lane vs HEAD)

1. **No unevidenced downgrades found.** Every closure verdict in all four lanes carries
   `file:line` or a named test; I spot-re-verified the kernel ones myself (§3).
2. **AI lane vs architect NF-4 (resolved).** At `fc388d7` the ai lane declared READ-via-bind
   "deterministic in the default flow" and "remaining theater: none"; the architect's same-commit
   pass found NF-4 (anti-downgrade guard tested record *presence*, not *liveness* — a dead
   leftover lock record silently defeated a fresh READ bind). The ai claim was premature at that
   commit. **Moot at HEAD:** `9ca2d2a` makes `_incumbent_is_stale` consume the canonical
   `core.lock_liveness.is_stale` with the injected probe (`hooks/sdd_gate.py:197-205`, verified
   directly), with falsifying tests on both sides (`test_sdd_gate.py:465-534` unit +
   real-subprocess). No score impact at HEAD.
3. **Security lane has no rc-2 appendix** — it scored at `f77e96c`; the `fc388d7..9ca2d2a` diff
   (payload-pid threading, Codex matcher, incumbent mode resolution, NF-4 predicate) was not
   security-rescored. Mitigations: the architect adversarially probed the new surface (payload
   pid validated `int > 0` before use; fail-open posture unchanged = accepted R-3 envelope;
   holder-guarded renewal and O_EXCL CAS untouched by the diff); my own read of
   `_resolve_holder_pid` confirms no new injection or privilege surface. Accepted at 9.0 with
   this caveat recorded.
4. **Security R-2 residual is stale (closed by rc-2).** Security listed the dead() secret-scan
   binary-suffix gap (`.pem/.key/.p12`) as an open LOW; qa's rc-2 delta verifies
   `test_dead_with_commit_blocks_on_untracked_pem_key_file` + the negative control landed in
   `fc388d7`. Removed from the residual backlog as already fixed.
5. **Severity-label divergence, no conflict:** architect rated NF-1 CRITICAL, ai-engineer HIGH
   ("CRITICAL-adjacent") for the same defect — both verdicts agreed on mechanism and fix
   direction, and both confirm it closed at root cause in rc-2. Moot.
6. **Run-evidence chain is consistent:** 2,779 pass at `f77e96c` → 2,792 at `fc388d7` (qa) →
   2,795 at `9ca2d2a` (coordinator green run; +3 = the NF-4 falsifying tests the architect
   verified by inspection). No lane contradicts another on any factual claim at its own commit.

---

## 3. Drift-anchor pass (the two auditor-only dimensions)

### 3a. SPEC/LEDGER FIDELITY — 9/10

Verified at HEAD:

- `releases/ACTIVE.md` = `v0.1.10 / alpha-1 / CLOSURE`. `SPEC.md`/`PLAN.md`/`TASKS.md` all
  `**Status:** Aprovado`. TASKS: **29 unique task ids (T-010-00..28), all `[x]`, zero `[ ]`/`[-]`**
  (grep-verified). CLOSURE.md absent — **confirmed as the only gap**, and it is the authorized
  next step after this verdict (T-010-16's memory rewrite already ran in CLOSURE phase per the
  A5 release-start split; the gate permits MEMORY writes in CLOSURE).
- `dadaia specs doctor` → **0 errors, 19 warnings** with SPEC-DOC-024..029 active. Warnings are
  pre-existing memory `token_estimate` drifts + legacy `_archive` naming (explicitly preserved
  as WARNING by SPEC-DOC-027). Archive repaired: `_archive/releases/v0.2.0/` internal
  milestones renamed `alpha-1..4`/`integration`; `_archive/releases/v0.1.9/` carries the
  retro-CLOSURE; no duplicate release ids (SPEC-DOC-026 green). `specs/bugs/`: **0 files with
  `status: Open`**.
- **Sampled acceptance criteria (3/3 PASS):**
  - **AC-R1-01** — `tests/unit/features/spec_context/test_gate_policy.py` exists with the
    class × {root, in-repo} × {default `dadaia-workspace`, non-default `rand-engine`} matrix
    incl. the two no-class-match MUTATING rows (read directly).
  - **AC-R2-04** — `tests/e2e/test_two_actor_lease.py` exists; scenarios (i)-(iv) + the rc-2
    hook-acquired-holder scenario (v) verified by the architect and qa lanes; in the HEAD
    green run.
  - **AC-R4-01** — bind default mode `read` persisted bare, gate maps to non-acquiring READ
    (`cli/commands/context.py:355-399`; `gate_policy.py:84-112` blocks MUTATING **before** any
    lease call; block message names `bind --mode implementation` with no rebind nag);
    `tests/integration/gate/test_read_mode_non_acquiring.py` incl. the cross-sid incumbent
    tests.

**Finding (LOW, label-only):** `ACTIVE.md` declares `segment: alpha-1` but the release uses a
flat layout (`releases/v0.1.10/{SPEC,PLAN,TASKS}.md`, no `alpha-1/` subdir). The doctor accepts
the flat tree (0 errors), so this is a cosmetic ledger-label inconsistency — either drop the
`segment:` line at CLOSURE or note the flat-single-segment convention. Not score-moving beyond
the 1-point withholding alongside the pending CLOSURE.md.

### 3b. MEMORY FIDELITY — 9/10

Every load-bearing claim sampled was verified against HEAD code directly (not via lane reports):

| Memory claim | Code at HEAD | Verdict |
|---|---|---|
| Classifier is context-relative; `repos/<slug>/` stripped; in-repo unmatched ⇒ MUTATING never UNGATED (`architecture.md` §concorrência; `sdd-gate-v3.md:35-46`) | `gate_policy.py:150-193` (`_context_relative` + `_classify_specs_relative` + MUTATING fall-through) | **MATCH** |
| Recorded pid = long-lived harness pid: payload `harness_pid`/`parent_pid`/`ppid`, else `os.getppid()` — never the ephemeral hook pid (`architecture.md`; `sdd-gate-v3.md:74-75`) | `hooks/sdd_gate.py:65-96` `_resolve_holder_pid`, threaded `evaluate(holder_pid=…)` → `lease.acquire(pid=…)` → stamped at `lease.py:328,360,381,390` | **MATCH** |
| Mode resolution: env → self session record (wins) → context incumbent with anti-downgrade honored only against a **live** divergent holder → IMPLEMENTATION (`architecture.md` §canal de modo; `sdd-gate-v3.md:52`) | `sdd_gate.py:131-205`; `_incumbent_is_stale` consumes `lock_liveness.is_stale` + injected probe (NF-4 fix, `:197-205`) | **MATCH** (doc sentence the architect flagged as "ahead of code" is now true in code) |
| Heartbeat: PostToolUse renews every lease the stdin-resolved sid holds; never `DADAIA_CONTEXT`→first-ALIVE; Claude matcher `*`, Codex block **without** matcher (match-all) | `sdd_post_gate.py:88-107`; `runtime_config.py:88-99` (Claude `*`), `:187-196` (Codex no-matcher) | **MATCH** |
| Bind persists `{context, mode, release, pid, session_id}` via `session_identity` AND refreshes `<ctx>.ptr` under the workspace lock; no eval-export by default | `context.py:355-399` (`write_session` + `set_incumbent` inside `workspace_lock`) | **MATCH** |
| READ sessions non-acquiring — MUTATING blocked before any lease read/write; ADDITIVE flows | `gate_policy.py:84-112` + evaluate ordering | **MATCH** |
| ADDITIVE = zero lease read or write; `.dadaia/` ADDITIVE prefixes workspace-root-only | `gate_policy.py` classify + e2e lock-history invariant | **MATCH** |

**Findings:**

- **DRIFT-M1 (LOW, tech-stack):** `tech-stack.md:106` calls Jinja2 a "*transitive dependency*…
  no longer used", but `pyproject.toml:37` declares `jinja2 = "^3.1"` as a **direct** runtime
  dependency and `features/specs/scaffolder.py:14-15` imports it (SandboxedEnvironment) — the
  "not for memory rendering" half is true; the "transitive" label is wrong. Fix the row at
  CLOSURE or v0.1.11.
- **DRIFT-M2 (LOW, tech-stack):** `tech-stack.md:98` pins `rich ^13` vs `pyproject.toml:34`
  `rich = ">=13,<16"`. Version-range drift only.
- **DRIFT-M3 (INFO, wording):** `architecture.md` mode-resolution parenthetical ("lease record
  nomeando outro sid ⇒ incumbent stale, ignorado") omits the liveness qualifier that its own
  main clause ("holder **vivo**") and the code carry. Shorthand, not an overclaim — the
  governing sentence is correct.
- Model-tier table in `tech-stack.md` matches `core/model_registry.py` exactly (fable-5 deep /
  opus-4-8 dispatch / sonnet-4-6 plugin; haiku-4-5 canonical id with historical pricing
  preserved). Catalog/atoms carry `release_origin: v0.1.10` where rewritten.

---

## 4. Verdict

**Original 5/10 → FINAL 9.0/10. All six dimensions ≥ 9. SHIP BAR MET — proceed to CLOSURE.md
authoring (product-engineer), then the rc ship gate per release-governance.**

What closed the 4-point gap, in causal order:

1. **Classifier re-rooted at the context** (`gate_policy._context_relative`) — the lease-theft
   entry vector (in-repo ADDITIVE classified MUTATING) is dead and proven dead through the real
   hook subprocess.
2. **Liveness became real**: harness-native heartbeat on every PostToolUse (both harnesses),
   CAS-wrapped renew, and a no-steal pid veto that records the **long-lived harness pid**
   (payload/`getppid`) — falsified end-to-end by the two-actor e2e incl. the hook-acquired-holder
   topology. D1/D2/D3 of the reproduced incident closed at root cause.
3. **READ/bind became real**: bind binds the CONTEXT (incumbent pointer), gate resolves mode
   through it with a liveness-correct anti-downgrade guard (NF-4 one-predicate fix at HEAD).
4. **The ledger became machine-checked**: SPEC-DOC-024..029, archive collision repaired,
   v0.1.9 retro-closed, 0 open bugs, every closure with a named falsifying regression.
5. **The surface stopped lying**: C-1..C-14 honesty rewrite, "deterministic vs discipline"
   split fleet-wide, memory/constitution rewritten to verified behavior — zero remaining theater.
6. **Security quad closed**: privacy fail-closed baseline, panel loopback auth removed,
   `dead()` review gate + secret scan, bash gate retired at the root.

---

## 5. Residual backlog — ranked v0.1.11 candidate list

| # | Sev | Item | Source |
|---|---|---|---|
| 1 | MEDIUM | Probe-less CLI side doors: `dadaia lock steal` (`cli/commands/lock.py:51`) and `lease._main` acquire (`lease.py:576`) run TTL-only with no pid probe — thread the probe or delete `lock steal` | architect rc-2 |
| 2 | MEDIUM | Lifecycle-asymmetry map mechanical enforcement: contract test/doctor check that every feature surface has a map row or explicit GAP cell (map itself delivered + grounded in rc-2) | qa §blockers |
| 3 | LOW | Bind-record GC decay: bind records (`ttl_seconds: 300`) are never renewed; doctor GC can delete a still-wanted READ bind ~5 min after bind → silent READ→IMPLEMENTATION decay. Exempt or renew bind records; fold with the incumbent-pointer behavior | architect rc-2 |
| 4 | LOW | session-path ownership residue: `core/specs_resolver.py:34`, `cli/commands/context.py:76`, `spec_context/doctor.py:124`, `panel/views/kanban.py:85` still construct `sessions/` paths outside `session_identity`; add the grep contract test | architect rc-2/NF-3 |
| 5 | LOW | Panel token in launch URL (`?token=` observable in history/referrer) — POST handshake or short-TTL launch token | security R-1 |
| 6 | LOW | ctx-inject bootstrap bloat: raw 25.6 KB `catalog.json` (incl. `summary`) ≈ 75% of the 34.7 KB injection — tldr-digest; plus sentinel GC | ai N-5 |
| 7 | LOW | Public-source hygiene: shipped `public/scripts/__pycache__/*.pyc`; opaque `public/data/repos.xlsx` | ai N-5 |
| 8 | LOW | Doc/ledger nits: `ACTIVE.md` `segment:` label vs flat layout (§3a); tech-stack jinja2/rich rows (DRIFT-M1/M2); arch.md parenthetical (DRIFT-M3); stale `_ENV_BASELINE` docstring ref (`test_sdd_post_gate.py:12`); duplicate probe construction in `sdd_gate` (cosmetic); one-sentence `getppid` shell-wrapper caveat in the sdd-gate atom | this pass + qa + architect |
| 9 | LOW | Opportunistic venv tooling bumps: `pip`/`poetry`/`dulwich` CVEs (out-of-runtime, documented) | security F-6 |
| 10 | INFO | Escape-record axis (qa 1.5/2) is time-earned — let the v0.1.11 cycle run with no escapes past green tests; memory `token_estimate` WARN cleanup; legacy `_archive` dir renames (SPEC-DOC-027 WARNs) | qa / doctor |

Closed-since-lane-report (do NOT carry): security R-2 dead() pem/key suffix gap (fixed + tested
in `fc388d7`); architect NF-1/NF-2/NF-4; ai N-1/N-2/N-3.

---

## 6. Evidence sources

- `specs/audits/2026-06-10T052944Z/software-architect.md` (incl. rc-2 delta + rc-2 final at `9ca2d2a`)
- `specs/audits/2026-06-10T052944Z/qa-engineer.md` (incl. rc-2 delta at `fc388d7`)
- `specs/audits/2026-06-10T052944Z/ai-engineer.md` (incl. rc-2 delta at `fc388d7`)
- `specs/audits/2026-06-10T052944Z/security-reviewer.md` (scored pass at `f77e96c`)
- Own reads at HEAD `9ca2d2a`: `gate_policy.py`, `hooks/sdd_gate.py`, `hooks/sdd_post_gate.py`,
  `lease.py`, `cli/commands/context.py`, `infrastructure/runtime_config.py`,
  `specs/memory/architecture.md`, `specs/memory/product/sdd/sdd-gate-v3.md`,
  `specs/memory/product/platform/context-management.md`, `specs/memory/tech-stack.md`,
  `specs/releases/v0.1.10/{SPEC,TASKS,PLAN}.md`, `specs/releases/ACTIVE.md`, archive tree,
  `specs/bugs/` (0 Open)
- `dadaia specs doctor` → 0 errors / 19 warnings (run 2026-06-10)
- Coordinator-supplied HEAD green run: 2795 passed / 8 skipped / 1 xpassed, exit 0

— project-auditor · synthesis · ADDITIVE writes only (this file) —
