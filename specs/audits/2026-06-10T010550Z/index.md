# Full-Workspace Audit Synthesis — dadaia-workspace

- **Synthesizer:** project-auditor (coordinating; Tier-1)
- **Date:** 2026-06-10T010550Z
- **Evidence lanes:** software-architect.md (6/10) · qa-engineer.md (5/10) · ai-engineer.md (5/10) · security-reviewer.md (7/10)
- **Mode:** AUDIT ONLY — no fixes. Every CONFIRMED entry was re-verified first-hand by the synthesizer (file:line) in addition to lane evidence.

---

## 1. Compliance Scorecard

| Dimension | Score (1-10) | Drift items | Notes |
|---|---|---|---|
| Spec fidelity (specs ↔ code) | **4** | F1, D-1/C-5, bug-closure claims, gate docstring (C-9), stale SPEC-pinning test (bug 19) | Three bug closures claim gate behavior the code inverts; the documented SDD gate (approval + `[-]` markers) is not implemented at all |
| Memory fidelity (memory ↔ code) | **4** | `architecture.md` ADDITIVE-unconditional + heartbeat-per-PreToolUse both false | Drift survived v0.1.9, a release whose sole objective was spec/memory fidelity |
| Architecture | **6** | F1, F2, F7, F10 | Library body sound (enforced layering, seams, 9/12 root-cause fix rate); the concurrency/identity keystone never built soundly |
| Test quality | **5** | 32 escapes: 14 no-test, 16 blind-green, 2 untestable | Craft high (slop ~8%, low mocks); environment fictional (single-context, hand-planted env vars) |
| AI-surface / enforcement honesty | **5** | 14 contradictions; ~70% of documented enforcement is discipline or theater | ADDITIVE/MEMORY/FROZEN gate classes unreachable in-repo; honest self-corrections exist but stale claims dominate |
| Security | **7** | 1 HIGH (same classifier kernel), 4 MEDIUM | Strong fundamentals (no shell=True, O_EXCL CAS, constant-time auth); closed security bugs mostly root-cause fixed |
| **Overall** | **5** | | weighted ≈ 5.2; floor 4 caps final at min(5.2, 4+2) = **5/10** |

Score floor rule: two dimensions at 4 → per drift-detection policy this is **moderate-to-significant drift; a dedicated remediation release is mandatory** (v0.1.10 exists — coverage verdict §6).

---

## 2. Confirmed-findings table (cross-lane convergence, synthesizer-verified)

| ID | Sev | Finding | Lanes converging | Kernel evidence (synthesizer re-verified) |
|---|---|---|---|---|
| CONF-1 | **CRITICAL** | Root-relative gate classifier: ADDITIVE/MEMORY/FROZEN prefixes match workspace-root only; `repos/` matches MUTATING first → in-repo bugs/backlog/audits acquire/steal the lease, in-repo memory bypasses the PE phase-lock, in-repo `_archive` is writable. **ALL FOUR lanes hit this independently** (arch F1, qa 17-D1, ai D-3/D-4/D-5+C-1, sec F-1 with empirical probe) | 4/4 | `features/spec_context/gate_policy.py:37-46` (prefixes), `:94` (`repos/` → MUTATING). Root-whitelist law forbids a root `specs/`, so the classes are unreachable in any compliant workspace |
| CONF-2 | **CRITICAL** | Lease liveness = write-recency TTL only; the dedicated heartbeat hook is a permanent no-op (env var no harness sets); docstring claims renewal "on every PreToolUse" — false. A live holder in any >120s Bash/pytest is stolen from (reproduced in production 2026-06-10). The PID-liveness fix learned in v0.1.5 rc-2 was discarded in the v0.1.6 lease rewrite | 3/4 (arch F2, qa 17-D2/D3, ai D-2/D-12/C-14) | `lease.py:16-19` ("Liveness is TTL-only… renews… on every PreToolUse" — second half false); `hooks/sdd_post_gate.py:38` (`DADAIA_SESSION_ID` env-gated, no stdin fallback); renewal occurs only inside `gate_policy.evaluate:147` for MUTATING Edit/Write |
| CONF-3 | **HIGH** | No trusted harness→gate identity/mode channel: `bind --mode` is metadata never consulted by any decision; `DADAIA_MODE` defaults to IMPLEMENTATION in the hook env; persona/session env vars never propagate to hook processes. Root of the persona-lock (keyless), cross-context, and read-session-steals-lease families | 3/4 (arch F3, ai D-10/D-11, qa #2/#5/#17-D3) | `hooks/sdd_gate.py:127` (`os.environ.get("DADAIA_MODE", "IMPLEMENTATION")`); no branch in `gate_policy.evaluate` or `lease.acquire` reads `mode` |
| CONF-4 | **HIGH** | Documented SDD gate ≠ implemented gate: the gate checks NO SPEC/PLAN/TASKS status and NO `[-]` markers — zero functional references to `TASKS`, `Aprovado`, or `[-]` in any hook or `gate_policy.py` (and 0 in `sdd-spec-gate.sh`). The approval/marker law agents are trained on is persona discipline labeled as mechanism | 1/4 lane (ai D-1/C-5) + synthesizer grep CONFIRMS | `grep -rn 'TASKS\|Aprovado\|\[-\]' dadaia_workspace/hooks/*.py …gate_policy.py` → 1 docstring mention only (`ctx_inject.py:35`) |
| CONF-5 | **HIGH** | SDD ledger internally inconsistent (full verdict §4): ACTIVE.md phase=SPEC vs 19/19 `[x]` Aprovado tasks, no CLOSURE.md, v0.1.10 authored while ACTIVE points at v0.1.9, archive release-id collision | arch F6 + synthesizer verified | `specs/releases/ACTIVE.md` vs `specs/releases/v0.1.9/alpha-1/TASKS.md`; `specs/_archive/releases/v0.2.0/{v0.1.6,v0.1.7,v0.1.8,v0.1.9}/` vs real releases of the same ids |
| CONF-6 | **HIGH** | Test environment is fictional: 16 of 32 bugs escaped past green tests blind along multi-context/multi-session/real-harness-env axes; tests `setenv` channels production never has (DADAIA_SESSION_ID, persona vars); drift-ratifying assertion pairs still Open (MODEL_MAP vs PRICING_TABLE; stale `sdd-spec-gate.sh` parity test) | qa (primary) + ai D-12 + arch F2 corroborate the env claims | qa escape matrix; `tests/unit/gate/test_post_gate_heartbeat.py:79`; `test_lease_property.py:74` (root-only ADDITIVE paths) |
| CONF-7 | **MEDIUM** | Bash bypass: all PreToolUse enforcement (incl. the sole fail-closed PROTECTED class) keys on Edit/Write/apply_patch; any `Bash` file write bypasses every gate. Posture is documented fail-open, but root AGENTS.md "deterministically" and SEC-01 "unconditionally" overstate it | ai (cross-cutting) + sec F-8 | `hooks/_common.py:30` WRITE_TOOLS; sec hook-trust assessment (non-destructive failure mode — permissive only) |
| CONF-8 | **MEDIUM** | `context dead()` auto-stages and pushes all untracked non-gitignored files, no review/secret-scan — known historical leak vector, still present | sec F-5 (+ operator memory) | `features/spec_context/service.py:292-302` |
| CONF-9 | **MEDIUM** | Duplicated hand-maintained truth with no reconciliation at authoring time: laws restated in ≥5 files drift (memory phases, workflow inventory, HTML-vs-handoff mandates, model-tier tables, MODEL_MAP/PRICING) | arch cluster F + ai C-3/C-4/C-6/C-7/C-8 + qa defect 4 | per-lane citations |

### Lane-conflict rulings (synthesizer adjudication)

| Item | Conflict | Ruling |
|---|---|---|
| **arch F5** ("the constitution's normative vision doc `docs/01_medium_codex.md` does not exist; docs/ absent") | Contradicted by disk | **REFUTED.** `docs/01_medium_codex.md` exists and is **git-tracked** (`git ls-files docs/` confirms); `docs/00_medium_mine.md` is deliberately gitignored. The constitution pointer is valid. Architect lane error (likely globbed from the wrong root). Remove F5 from remediation. |
| sec F-1 severity HIGH vs project bug CRITICAL | Dimension framing | **Both stand.** Security dimension HIGH (mutual-exclusion bypass), product availability/correctness dimension CRITICAL. CONF-1 carries CRITICAL. |
| qa "tests are lying" vs qa "craft is good" | None — nuance | Adopted verbatim into the verdict (§5): volume honest, environment fictional. |

---

## 3. Drift findings (memory/constitution ↔ code, synthesizer's anchor pass)

| ID | Dim | Sev | Claim (spec evidence) | Actual (code evidence) |
|---|---|---|---|---|
| DRIFT-1 | Memory | CRITICAL | `specs/memory/architecture.md` §"Modelo de concorrência": "writes targets são `specs/backlog/**`, `specs/bugs/**`, `specs/audits/**`… Nenhum lease é requerido… Gate permite incondicionalmente para esses paths" | `gate_policy.py:94` — every in-repo `repos/<slug>/specs/bugs|backlog|audits` path is MUTATING and lease-acquiring (CONF-1) |
| DRIFT-2 | Memory | HIGH | `architecture.md` lease section: "Heartbeat renovado a cada PreToolUse" | Renewal only on MUTATING Edit/Write via `gate_policy.evaluate:147`; PostToolUse heartbeat permanently no-ops (`sdd_post_gate.py:38`) (CONF-2) |
| DRIFT-3 | Constitution | HIGH | constitution §"lifecycle phases": "ADDITIVE phases run in parallel and never take a lease: backlog definition, bug filing, research, audit…" | Same kernel as DRIFT-1 — false for every real (in-repo) Spec Context |
| DRIFT-4 | Spec/rules | HIGH | root AGENTS.md §SDD Gate + `dadaia-task-manager` skill: gate requires `**Status:** Aprovado` + `[-]` reservation ("a presença de… task `[-]` … libera o gate") | Gate code contains zero status/marker logic (CONF-4); the most-loaded implementer skill describes a gate generation that does not exist |
| DRIFT-5 | Spec | HIGH | `ACTIVE.md`: `release: v0.1.9 / segment: alpha-1 / phase: SPEC` | 19/19 tasks `[x]`, SPEC/PLAN/TASKS all Aprovado, implementation complete, no CLOSURE.md — phase never advanced (CONF-5) |
| DRIFT-6 | Spec | MEDIUM | `gate_policy.py:3-8` docstring: "The enforced gate is `public/scripts/sdd-spec-gate.sh` (bash…)" | Live wiring invokes `python -m dadaia_workspace.hooks.*` (v0.1.8); the bash pair is the dead half of a hand-parity dual implementation |
| DRIFT-7 | Memory/tests | MEDIUM | Approved v0.1.8 SPEC retires bash hooks | `tests/e2e/features/test_opencode_parity_hardening.py` still asserts `sdd-spec-gate.sh` (bug 19, Open) — a test pinning the retired spec |
| DRIFT-8 | Constitution | LOW→REFUTED | §preamble pointer to `docs/01_medium_codex.md` | File exists and is tracked — no drift (arch F5 refuted) |

---

## 4. Ledger verdict

**INTERNALLY INCONSISTENT — four simultaneous lies, one collision:**

1. `ACTIVE.md` says `phase: SPEC` for v0.1.9 alpha-1; the segment's TASKS.md has all 19 tasks `[x]` with `**Status:** Aprovado` across SPEC/PLAN/TASKS → the phase field was never advanced through IMPLEMENTATION. The gate feeds RULE A (memory-phase legality) from this field, so the stale phase silently changes memory-write legality.
2. No `CLOSURE.md` for v0.1.9 — implemented but never closed; memory was therefore never reconciled by closure (DRIFT-1/2 are partially a consequence).
3. v0.1.10 SPEC/PLAN/TASKS exist (`**Status:** Em revisão`) while ACTIVE still points at v0.1.9 — a second release authored before the first's closure; tolerable as authoring-ahead, but combined with (1)+(2) the ledger cannot answer "what is the current release state".
4. Release-id collision in the archive: `specs/_archive/releases/v0.2.0/` contains internal milestones named `v0.1.6, v0.1.7, v0.1.8, v0.1.9` — the same ids as real (archived or active) releases. Archive archaeology is ambiguous; this is precisely how the v0.1.5 PID-liveness lesson got lost (CONF-2).
5. No doctor invariant validates phase-vs-markers consistency or release-id uniqueness — the SDD machine gates writes but never validates its own state transitions.

---

## 5. Verdict on the operator's two questions

**"Lots of tests but no quality — someone is lying to me."**
Half right, and the lying is real but not where it usually is. Nobody padded the suite: slop ≈ 8%, mock density exceptionally low, gate tests are real black-box subprocesses, conftest hygiene is exemplary. The lies are two, both systemic:
(a) **The test suite certifies a fictional world** — single context, single session, env vars hand-planted that no harness provides. 16 of 32 bugs escaped past *green* tests; both CRITICALs of this cycle live exactly in the untested axes (multi-session interleaving, real hook env). The tests answer "does the state machine I imagined work" instead of "does the product work where it runs".
(b) **The documentation lies about enforcement** — ~70% of claimed deterministic enforcement is discipline or theater: the gate checks no approvals and no markers (CONF-4), three gate classes are unreachable in-repo (CONF-1), `bind --mode` is a label (CONF-3), the heartbeat is a no-op (CONF-2). Agents and the operator were both planning against a security model that does not exist.

**"Was this architected badly by a weaker model?"**
**No for the body, yes for one keystone.** The Python library at large is competently architected — enforced import-linter layering, composition root, platform seam, ProcessRunner port, 9 of 12 sampled closed bugs fixed at true root cause with named regression tests. That is not weak-model slop. The rot is concentrated in exactly one foundation: the **concurrency/identity kernel** (path classifier + lease liveness + harness→gate identity channel), which was never implemented soundly, whose one learned fix (PID liveness, v0.1.5 rc-2) was discarded in a rewrite, and on which four generations of lock bugs were then symptom-patched one layer up. Every lane independently landed on this same kernel. Fix the kernel and the bug-family tree (8+ bugs) collapses; keep patching above it and v0.1.10 becomes the fifth symptom pass.

---

## 6. Remediation priority (dependency-ordered) + v0.1.10 coverage verdict

| # | Action | Depends on | v0.1.10 (Em revisão) coverage |
|---|---|---|---|
| R1 | **Classifier re-root**: classify on the context-relative path (strip `repos/<slug>/`); matrix tests every class × {workspace-root, in-repo}. Explicitly restore MEMORY phase-lock and FROZEN semantics in-repo, not just ADDITIVE | — (kernel) | **WS-1 covers D1 (ADDITIVE)** — MUST be extended to MEMORY/FROZEN + matrix tests (arch F1 extension) |
| R2 | **Lease liveness**: heartbeat on every PostToolUse keyed by harness-native session id (stdin fallback in `sdd_post_gate`, like `sdd_gate`); consult the existing `has_os_kill_liveness` platform-seam process probe before TAKEOVER; fix the false `lease.py` docstring | R3 helpful, not blocking | **WS-2 is the correct direction** — MUST add the platform-seam liveness probe and the heartbeat-key fix, not TTL tuning |
| R3 | **Session-identity consolidation**: one CLI-owned module for `<ctx>.ptr` / `<session>.ptr` / `sessions/<id>.json` (arch F7) — the substrate of the whole bug family | — | **WS-3 design** — fold F7 in explicitly |
| R4 | **Mode/identity channel**: persist `bind --mode` in CLI-owned session state read by the gate; missing/READ ⇒ non-acquiring (block MUTATING instead of stealing) | R3 | **NOT covered** — extension required (arch F3, ai D-10) |
| R5 | **Test-strategy kernel** (acceptance criteria for R1-R4): harness-env fixture contract (`claude_hook_env()`/`codex_hook_env()` containing ONLY what harnesses provide), two-actor concurrency pattern generalized from `test_two_process_denial.py`, fixture matrix {1,2 contexts}×{default,non-default slug}×{seeded,empty} | R1-R4 land with these | **NOT covered as criteria** — extension required (qa defects 1-3; covers 11 of 16 blind escapes) |
| R6 | **Ledger + doc truth**: advance/correct ACTIVE.md; author v0.1.9 CLOSURE; rewrite `architecture.md` concurrency section + constitution ADDITIVE claims to verified behavior; fix C-2/C-5/C-7 stale enforcement claims; doctor invariants (phase-vs-markers, unique release ids, constitution file refs) | R1, R2 (document the *fixed* contract, not the broken one) | **Partially** — arch review-gate: REJECT any v0.1.10 closure that fixes code without rewriting memory/constitution (F4) |
| R7 | **Security tail**: `dead()` requires clean tree or explicit `--commit` + secret scan (sec F-5); privacy gate ships an in-package baseline denylist (F-2); loopback auth (F-3); bash-gate `realpath` or demote the dead bash pair (F-4 + S-2); bump dev `poetry`/`dulwich` pins (F-6) | independent | **NOT covered** — fold F-5/F-2 minimum into v0.1.10 or next |
| R8 | **Anti-drift pattern**: consistency-contract-at-introduction policy (cross-table key equality, residue greps); cap the import-linter ignore list (F10); dedupe restated laws (S-3) | R6 | Backlog |

**v0.1.10 verdict: PARTIAL — right root causes, insufficient breadth.** WS-1/2/3 name the correct kernel (first release ever to do so), but as specified it would still ship with: MEMORY/FROZEN classes dead (R1 ext), a heartbeat that no-ops in real harnesses (R2 ext), mode theater intact (R4), no harness-fidelity test tier to prove any of it (R5), and memory/constitution still describing the old world (R6). **Recommend: extend the v0.1.10 SPEC (it is Em revisão — still amendable) with R1-ext/R2-ext/R4/R5-as-acceptance-criteria/R6 before approval**, via project-manager → product-engineer. Without the extensions it will be the fifth symptom pass on this family.

---

## 7. Dead / stale code (consolidated)

| Item | Evidence | Lane |
|---|---|---|
| MEMORY/FROZEN/in-repo-ADDITIVE gate branches — dead for every real context | `gate_policy.py:90-93,137-143` unreachable in compliant workspaces | arch/ai/sec |
| `sdd_post_gate` heartbeat — permanent no-op in all harnesses | `sdd_post_gate.py:38` | arch/ai/qa |
| Bash hook quartet — unexecuted dual implementation requiring hand byte-parity, already drifted | `public/scripts/{sdd-spec-gate,sdd-post-gate,root-whitelist-gate,ctx-inject}.sh` (S-2, C-9) | ai/arch |
| `mode` field in lease record — written, never read | `sdd_gate.py:127` → `lease._new_record` | ai/arch |
| `__pycache__/` inside canonical public assets | `public/scripts/__pycache__/*.pyc` (S-1) | ai |
| Stale parity test pinning retired bash gate | `tests/e2e/features/test_opencode_parity_hardening.py` (bug 19, Open) | qa |
| `tests/e2e/node_modules/` in-tree | gray-zone vs repo-cleanliness law | qa |

## 8. Evidence sources

- `specs/audits/2026-06-10T010550Z/software-architect.md` — architecture, bug-cluster map, 12 closed-bug verdicts
- `specs/audits/2026-06-10T010550Z/qa-engineer.md` — 32-bug escape matrix, pyramid, slop scan
- `specs/audits/2026-06-10T010550Z/ai-engineer.md` — determinism table D-1..D-13, contradictions C-1..C-14
- `specs/audits/2026-06-10T010550Z/security-reviewer.md` — findings F-1..F-8, pip-audit, closed-bug verification
- Synthesizer first-hand: `gate_policy.py:37-98,123-156`; `lease.py:1-30`; `hooks/sdd_gate.py:127`; `hooks/sdd_post_gate.py:9,38`; `specs/releases/ACTIVE.md`; `specs/releases/v0.1.9/alpha-1/{SPEC,PLAN,TASKS}.md`; `specs/releases/v0.1.10/{SPEC,PLAN,TASKS}.md`; `specs/_archive/releases/v0.2.0/`; `specs/memory/architecture.md` concurrency section; `specs/constitution.md` preamble + §lifecycle; `git ls-files docs/`; grep for TASKS/Aprovado/`[-]` across hooks + gate

— end of synthesis —
