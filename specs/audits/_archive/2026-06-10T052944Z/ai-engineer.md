# AI-Surface RE-AUDIT — dadaia-workspace (post v0.1.10)

- **Auditor:** ai-engineer (re-audit of the 2026-06-10T010550Z lane; same rubric)
- **Date:** 2026-06-10T052944Z
- **Source audited:** `dadaia_workspace/public/` + live hooks `dadaia_workspace/hooks/`,
  `features/spec_context/{gate_policy,lease,session_identity,lock_liveness via core}.py`,
  `infrastructure/runtime_config.py`, `cli/commands/context.py` — branch
  `feature/v0.1.10`, HEAD `f77e96c`
- **Instance cross-checked:** live `.claude/settings.json`, `.codex/hooks.json`, root
  `AGENTS.md`, `.claude/rules/`, `.claude/agents/ai-engineer.md` (diff vs source: identical)
- **Baseline:** `specs/audits/2026-06-10T010550Z/ai-engineer.md` (score 5/10)
- **AI-surface score: 8 / 10**

Scoring rationale: the rewrite closed all 14 baseline contradictions and the two
CRITICALs as documented. The classifier is now genuinely context-relative (live-probed:
in-repo bugs/backlog/audits → ADDITIVE, memory → MEMORY, `_archive` → FROZEN), the
surface text was relabeled into an explicit "deterministic enforcement vs agent
discipline" split that matches the code almost line-for-line, the Claude matchers obey
the product's own F2 law, and the heartbeat genuinely renews from the stdin session id
on every Claude PostToolUse. What blocks 9: the **no-steal pid veto is inert in
harness-real topology** (the lease records the ephemeral hook subprocess pid, which is
dead before any foreign probe runs — N-1), the surface re-overclaims it in ≥4 places,
the **Codex heartbeat matcher is still write-only** while the codex harness skill claims
`PostToolUse *` (N-2), and **`bind --mode` keying never links to the harness session id**
(N-3), making READ mode unreachable in harness-real flow. These are the same *genre* of
defect (claimed mechanism ≠ shipped mechanism) the baseline punished — narrower now, but
concentrated on the single lock the whole governance story leans on.

---

## 1. Refreshed determinism table (claim → mechanism → verdict)

| # | Claim (current surface text) | Actual mechanism (code, HEAD f77e96c) | Verdict |
|---|---|---|---|
| D-1 | SDD gate = "path-class × lease × phase × mode on file-write tools; the hook reads no SDD artifacts; markers/Status are discipline" (`workspace-protocol.md:11-30`; `data/AGENTS.md` §SDD Gate; `dadaia-task-manager` honesty note) | `hooks/sdd_gate.py:135-208` → `gate_policy.evaluate()` (gate_policy.py:196-271): PROTECTED fail-closed first, ADDITIVE/UNGATED allow, FROZEN block, MEMORY phase-checked via `ACTIVE.md` `phase:` (sdd_gate.py:123-132,181), READ-mode non-acquiring block (gate_policy.py:257-258), MUTATING → `lease.acquire`. No TASKS/SPEC/marker reads — exactly as now documented. | **DETERMINISTIC & TRUTHFULLY DOCUMENTED.** The claim is now exactly true; the old marker-gate fiction is purged (task-manager rewritten, `[SDD HARD STOP]` relabeled as discipline). |
| D-2 | Lease: "heartbeat renews on every PostToolUse (harness-native sid from stdin); a holder whose pid is still running is never stolen" (`workspace-protocol.md:17-19`; `data/AGENTS.md`; `lease.py:16-27`) | Heartbeat: `sdd_post_gate.py:167-189` resolves sid via `_common.resolve_session_id` (stdin fallback, `_common.py:102-116`), renews every lease the sid holds by scanning lock files (`:73-107`) — the env-gated no-op and the first-ALIVE contamination path are gone. Claude wiring fires it on `*` (live `.claude/settings.json`, `runtime_config.py:88-100`). Pid veto: `lock_liveness.is_stale` honors `pid_probe` on the TTL-stale branch; `lease.acquire:387-402` yields on live-foreign. **BUT** the recorded pid defaults to `os.getpid()` of the *acquiring process* (`lease.py:328`), and `gate_policy.py:262` passes no pid — in production the acquirer is the `python -m …sdd_gate` hook subprocess, dead milliseconds later. | **SOUND on Claude for renewal; UNSOUND no-steal half (N-1).** Starvation between tools is fixed on Claude; theft remains possible during any single >120 s tool call (the original long-pytest incident shape) because the veto probes a dead pid. Codex: renewal still write-only (N-2). |
| D-3 | ADDITIVE in-repo: "the gate's path classifier resolves `specs/bugs/` (root **and** inside any `repos/<slug>/`) to ADDITIVE — never blocked, never takes a lease" (`data/AGENTS.md` §Bug Registration; `bug-registration-guardrail.md:29-31`) | `gate_policy.classify_path:165-193` re-roots the `specs/` taxonomy on the `repos/<slug>/` remainder (`_context_relative`, `:150-162`); unmatched in-repo remainder ⇒ MUTATING, never UNGATED. Live-probed: `repos/x/specs/bugs/b.md → ADDITIVE`, backlog/audits likewise. | **DETERMINISTIC — fixed.** Baseline CRITICAL closed. |
| D-4 | MEMORY phase-lock in-repo: "phase half enforced deterministically (root and in-repo); the who half is discipline" (`workspace-protocol.md:60`) | `repos/x/specs/memory/m.md → MEMORY` (live probe); phase read from the *context's* `releases/ACTIVE.md` (sdd_gate.py:180-181); `_MEMORY_WRITE_PHASES = {DEFINITION, CLOSURE}` (gate_policy.py:82,245-251). Persona-blindness now stated, not hidden. | **DETERMINISTIC (phase half), honestly split — fixed.** |
| D-5 | FROZEN `specs/_archive/` read-only, in-repo | `repos/x/specs/_archive/z.md → FROZEN` (live probe) → RULE B block (gate_policy.py:242-243). | **DETERMINISTIC — fixed.** |
| D-6 | PROTECTED `.dadaia/sessions/` fail-closed; Bash writes "outside this determinism envelope (Decision D-2); doctor coherence checks are the backstop" | Evaluated first, blocks unconditionally (gate_policy.py:236-237; sdd_gate.py:164-177). Bash bypass now *documented* as out-of-scope (D-2) in `data/AGENTS.md:152-154`, `workspace-protocol.md:21-22`, `tmp-file-guardrail.md:59-61`. Backstop is real: `features/specs/doctor.py:451,1167` SPEC-DOC-029 lease↔session coherence via `session_identity.coherence`. | **DETERMINISTIC-NARROW, now honestly labeled with a real named backstop.** "Deterministically/unconditionally" overclaim language is gone. |
| D-7 | Root whitelist: "enforced for file-write tools by the `dadaia_workspace.hooks.root_whitelist` PreToolUse hook (Python). Bash-side writes are outside the hook's envelope (Decision D-2)" (`tmp-file-guardrail.md:59-61`) | `hooks/root_whitelist.py` — 9-entry whitelist, parent-is-root scope, `root_exceptions.txt` fnmatch. Stale `root-whitelist-gate.sh` references purged from source AND live projections. | **DETERMINISTIC-NARROW, truthfully labeled — fixed.** |
| D-8 | tmp-file guardrail | Still no landing-zone hook — but the rule now self-identifies the hook's narrow envelope and itself as discipline for the rest. | **DISCIPLINE, now labeled as such — fixed.** |
| D-9 | ctx-inject once-per-session | `ctx_inject.py:151-163` sentinel unchanged; payload = preflight + tech-stack (9.1 KB) + raw `catalog.json` (25.6 KB) ≈ **34.7 KB once per session**. | **DETERMINISTIC.** Bloat unchanged (raw catalog incl. `summary` fields; tldr-digest recommendation still open). |
| D-10 | `bind --mode`: "bind persists the mode in the session record; the gate reads it without any env var (the harness-real path)" (SPEC FR-R4-02; `context.py:310-325`; gate `_resolve_mode`) | Gate side real: `sdd_gate._resolve_mode:96-120` (env → session record → IMPLEMENTATION default); `gate_policy.py:95-112,257-258` blocks READ before any lease write. CLI side: `context.py:364` **always mints a fresh `sess_<uuid8>`** and keys the record by it; it never attempts the harness-native sid the SPEC promises ("keyed by the harness-native session id when resolvable"). The hook resolves the *harness* sid → record not found → default IMPLEMENTATION. | **HALF-FIXED (N-3).** Mechanism exists and is tested at the gate, but the key linkage is broken in harness-real flow: READ enforcement is reachable only via the legacy `--print-env`+eval env path. Fail-open direction (no freeze risk), but FR-R4-02's headline is not yet true. |
| D-11 | Per-persona `paths.write_allowlist` = convention, not enforced | `workspace-protocol.md:62-63` honest; **F8 in `ai-harness-claude-code` rewritten**: "NOTHING enforces the per-persona write-allowlist… the gate enforces path-class × lease × phase × mode, persona-blind." | **DISCIPLINE, consistently labeled — C-2 fixed.** |
| D-12 | PostToolUse heartbeat | See D-2. Claude: real (`*` matcher, stdin sid, holder-scan renewal). Codex: matcher `^(apply_patch|Edit|Write)$` (`runtime_config.py:152,183`; live `.codex/hooks.json`) — fires on writes only. | **DETERMINISTIC on Claude; RESIDUAL on Codex (N-2).** |
| D-13 | Pre-push CI gate | `public/scripts/pre-push-ci-gate.sh` retained, sole deliberate shell asset (gate_policy.py:8-10). | **DETERMINISTIC (installation-dependent) — unchanged.** |

---

## 2. C-1..C-14 closure ledger

| # | Baseline contradiction | Status | Evidence |
|---|---|---|---|
| C-1 | "Bugs ADDITIVE" vs in-repo MUTATING | **FIXED** | Classifier re-root (gate_policy.py:150-193, live-probed); rule text now cites the v0.1.10 context-relative classifier (`bug-registration-guardrail.md:29-31`) |
| C-2 | F8 false "gate enforces allowlist" | **FIXED** | `ai-harness-claude-code` §7 F8 rewritten to "NOTHING enforces…, persona-blind" |
| C-3 | PM workflow-inventory denial | **FIXED** | `project-manager.md:120` "Exactly 2 workflow files ship in the default installation" |
| C-4 | Memory phases "CLOSURE only" | **FIXED** | `dadaia-workspace-spec-navigator/SKILL.md:81` "DEFINITION and CLOSURE phases (constitution §13)" |
| C-5 | Marker-grepping gate fiction in task-manager | **FIXED** | Skill rewritten in English with the "Honesty note — markers are discipline, not a hook check" + kernel-true recovery section (READ/MEMORY/FROZEN/PROTECTED/live-foreign) |
| C-6 | HTML-mandate header vs handoff-first | **FIXED** | Persona header blockquote now "Reports follow the `workspace-protocol` rule §4 (handoff-first)…" (`agents/ai-engineer.md:66`); fleet grep for the old blockquote: 0 hits |
| C-7 | Emitter required HTML for every handoff | **FIXED** | `dadaia-handoff-emitter` is dual-mode; `artifact.path`/`content_hash` only in report mode; schema requires only `artifact.type` |
| C-8 | Tier tables can't produce the fleet | **FIXED** | Tables now registry-derived (`core/model_registry.py`): deep=claude-fable-5 / dispatch=claude-opus-4-8 / plugin=sonnet-4-6 / fast=haiku-4-5-20251001; fleet = 5×fable-5 + 4×opus-4-8, both producible |
| C-9 | gate_policy claimed bash gate enforces | **FIXED** | gate_policy.py:3-10 names the Python hook package; "legacy bash hook quartet was retired in v0.1.10 (Decision D-1)"; stale `.sh` refs purged from rules/AGENTS.md (only historical comments in `plugins/ctx-inject.ts` remain) |
| C-10 | "Dispatches to" implied nest-dispatch | **FIXED** | `project-orchestration:21-25` "handoff routing, not executable dispatch… a dispatched sub-agent cannot spawn another agent in either harness, at any approval level"; PM-top-level-only precondition now explicit |
| C-11 | Live hooks unowned in the ownership model | **FIXED** (minor residual) | `ai-harness-codex` §9: "the hooks are production Python owned by software-engineer". Residual: ai-engineer persona scope still advertises "hook + gate scripts under `public/scripts/` (shell/Python)" though the only gate-adjacent asset left there is `pre-push-ci-gate.sh` (cosmetic) |
| C-12 | Empty Claude matcher vs F2 law | **FIXED** | `runtime_config.py:50-59,74,85,99` + live settings.json: PreToolUse `Edit\|Write\|MultiEdit\|NotebookEdit`, PostToolUse explicit `*`, only the tool-less UserPromptSubmit keeps `""` (correct) |
| C-13 | Portuguese task-manager body | **FIXED** | Skill body fully English |
| C-14 | Lease docstring liveness fiction | **FIXED on Claude** | lease.py:25-27 now matches the Claude wiring; the Codex residual is re-filed as N-2 (the docstring's "every PostToolUse" is event-true but the Codex event only fires on writes) |

**14/14 closed as written.** Residuals from C-11 (cosmetic) and C-14 (Codex) carried into the new findings below.

---

## 3. NEW findings (text vs code at HEAD)

| # | Finding | Evidence | Severity |
|---|---|---|---|
| N-1 | **Pid-veto records the ephemeral hook pid — the no-steal half is inert in harness-real flow.** `lease.acquire` defaults `pid = os.getpid()` (lease.py:328) and `gate_policy.evaluate` passes none (gate_policy.py:262); in production the acquirer is the `python -m dadaia_workspace.hooks.sdd_gate` subprocess, which exits immediately. `renew_heartbeat` never refreshes `pid` (lease.py:449-455). So when a foreign session probes a TTL-stale record, the recorded pid is dead → plain TTL verdict → TAKEOVER. The live-session-theft window is narrowed (Claude renews after every tool) but NOT closed: any single tool call >120 s — exactly the reproduced long-pytest incident — is stealable. The e2e proof (`tests/e2e/test_two_actor_lease.py:85-89`) has the holder acquire *in-process* and stay alive, a topology production never exhibits, so AC-R2-04(i)/(ii) are proven for the wrong process model. Surface overclaims it in ≥4 places: `data/AGENTS.md` ("pid demonstrably alive — is never stolen"), `workspace-protocol.md:18`, `lease.py:16-27`, `dadaia-workspace-manager:92,201`. Fix direction: record the hook's parent pid (`os.getppid()` = the harness process) or thread a long-lived pid from the session record. | code+test | **HIGH** (CRITICAL-adjacent: re-opens a narrowed form of the lease-theft CRITICAL) |
| N-2 | **Codex heartbeat matcher is write-only; the codex harness skill claims `PostToolUse *`.** `runtime_config.codex_hooks` puts `^(apply_patch|Edit|Write)$` on PostToolUse (runtime_config.py:152,181-194; confirmed in live `.codex/hooks.json`), so a Codex holder doing >120 s of reads/Bash never renews — the starvation D2 was supposed to kill survives on one of two active harnesses, compounded by N-1 (no working pid backstop). `ai-harness-codex/SKILL.md:321` states the live shape as "`PostToolUse * → …sdd_post_gate` (must fire on every tool, so its matcher stays broad)" — false for the generated Codex config. T-010-18/AC-R6-05 fixed only the Claude generator. | code+skill | **HIGH** (text-vs-code contradiction + real residual) |
| N-3 | **`bind --mode` session-id linkage broken (SPEC deviation).** SPEC WS-R4 fix text: record "keyed by the harness-native session id when resolvable, else by the bind-created session id". `context.py:364` always mints `sess_<uuid4hex8>` and never attempts harness-native resolution; the gate resolves the *harness* sid (stdin/env) → `read_session` misses → mode defaults IMPLEMENTATION. Net: `--mode read` (and the documented "operator binds implementation mode once" path in the task-manager skill / READ block message) has no effect on a real harness session unless the operator uses the legacy `--print-env` + `eval` env flow. Fail-open direction (no freeze), but FR-R4-02's "harness-real path" is not yet real. | code vs SPEC.md:182-201 | **MEDIUM** |
| N-4 | `workspace-protocol.md:19` / lease docstring say the heartbeat renews "on every PostToolUse" without the Codex qualifier — true per-event, misleading per-harness (subsumed by N-2). | text | LOW |
| N-5 | Hygiene carry-overs: `public/scripts/__pycache__/*.pyc` still shipped in canonical source (baseline S-1); `public/data/repos.xlsx` opaque binary (S-8); ctx-inject still injects raw 25.6 KB `catalog.json` incl. full `summary` fields (~75 % of the 34.7 KB bootstrap; tldr-digest recommendation unaddressed); ctx-inject sentinels still un-GC'd. | fs | LOW |

No other new text-vs-code contradictions found: persona fleet projections byte-identical to source (`diff` exit 0), root AGENTS.md / rules projections match staged source, registry tier tables match `core/model_registry.py`, handoff schema `$id` now `handoff-v1.1` matching the emitter literal (v1 kept in enum for back-compat reads).

---

## 4. What is genuinely good (kept proportion)

- The **"deterministic enforcement vs agent discipline" split** is now the organizing
  frame of `data/AGENTS.md` §SDD Gate, `workspace-protocol` §1, and the task-manager
  skill — the exact remediation the baseline demanded, executed fleet-wide without a
  single stale duplicate found in source or live projection.
- The classifier re-root is real, live-verified, and the dead-class CRITICAL is gone;
  PROTECTED ordering, PATH-first slug, O_EXCL CAS, holder-safe renewal, and the
  CAS-wrapped `renew_heartbeat` (closing the renewal-vs-takeover interleave) are all
  correct in code.
- The harness skills practice what they preach on Claude (F2 matchers fixed in the
  generator *and* live), F8 is now the honest authority, and the doctor backstop the
  text cites (SPEC-DOC-029) actually exists.

---

## 5. Score and the path to 9

**8 / 10.** The surface is now ~90 % mechanism-true and the two baseline CRITICALs are
closed as specified. Blocking 9: (a) N-1 — the no-steal invariant is overclaimed again
on the single lock everything leans on, with the theft window of the original incident
shape still open; (b) N-2 — Codex renewal parity + the false `PostToolUse *` claim in
the ai-engineer-restricted codex skill; (c) N-3 — FR-R4-02's harness-real READ path is
not yet real. All three are small, well-localized fixes (record `getppid`/long-lived
pid + relabel four text sites; broaden one Codex matcher + one skill line; resolve
harness sid in `bind`). Bugs filed: `lease-pid-veto-records-ephemeral-hook-pid.md`,
`codex-posttooluse-heartbeat-matcher-write-only.md`,
`bind-mode-session-record-keyed-by-cli-sid.md` (specs/bugs/).

— end of report —

---

## rc-2 delta (re-score after fc388d7, branch feature/v0.1.10)

Adversarial re-verification of the three blockers, at commit `fc388d7`.

### Blocker verdicts

| # | Verdict | Evidence |
|---|---|---|
| N-1 | **FIXED.** | Code: `hooks/sdd_gate.py::_resolve_holder_pid` (payload `harness_pid`/`parent_pid`/`ppid` → `os.getppid()` fallback) threaded as `holder_pid` through `gate_policy.evaluate(…, holder_pid=…)` → `lease.acquire(pid=…)`. The ephemeral-hook-pid default survives only for in-process callers. Test: `tests/e2e/test_two_actor_lease.py::test_hook_acquired_holder_no_steal_while_driver_alive_then_takeover` proves the **correct topology** — a real driver process spawns the real `python -m …sdd_gate` subprocess, asserts `rec["pid"] == driver_pid` (not the hook child), foreign MUTATING acquire YIELDED past TTL while the driver lives, TAKEOVER only after the driver is reaped. Suite re-run: 6 passed. Text: all 4 flagged sites relabeled accurately — `workspace-protocol.md:18-20`, `data/AGENTS.md:148-149` ("hook payload pid when present, else the hook's parent process"), `dadaia-workspace-manager:93-100,110-113,206`, `dadaia-task-manager:117`; `lease.py:16-27` docstring now describes the injected-probe veto truthfully. |
| N-2 | **FIXED.** | `runtime_config.codex_hooks` PostToolUse block carries **no matcher** (Codex's canonical match-all; comment cites N-2 explicitly); the write-matcher remains only on PreToolUse. Live `.codex/hooks.json` confirmed: PostToolUse entry has no `matcher` key. `ai-harness-codex/SKILL.md:321` rewritten to "matcher **omitted** — Codex's canonical match-all form". No leftover `apply_patch\|Edit\|Write`-on-heartbeat claims anywhere in `public/`. |
| N-3 | **FIXED.** | `sdd_gate._resolve_mode` is now env → session record (harness sid; wins) → **context incumbent pointer** (`sessions/runtime/<ctx>.ptr`) with an anti-downgrade guard (`_incumbent_is_stale`: a live lease naming a different sid voids a stale read-bind) → IMPLEMENTATION default. `context.py` bind refreshes the incumbent pointer (`session_identity.set_incumbent`), so the bind binds the CONTEXT, not a throwaway sid. READ is reachable in the default flow with **no env var and a different harness sid**: `tests/integration/gate/test_read_mode_non_acquiring.py::test_cross_sid_read_bind_blocks_mutating_via_incumbent` (+ ADDITIVE-allows twin) drives the real hook subprocess via `claude_hook_env`; `tests/contract/cli/test_cli_context.py::test_context_bind_refreshes_context_incumbent_pointer` covers the CLI half. 38 passed. Manager-skill text (`dadaia-workspace-manager:43-47,85`) describes the incumbent mechanism and demotes `--print-env` to legacy. |

### Projection / memory consistency

- Source↔projection spot-check (3 touched files): `workspace-protocol.md`, `data/AGENTS.md`→root `AGENTS.md`, `ai-harness-codex/SKILL.md` — `diff` exit 0. `dadaia public doctor` clean incl. `[ok] public-privacy`.
- `specs/memory/product/sdd/sdd-gate-v3.md` and `specs/memory/architecture.md` both carry the rc-2 mechanisms verbatim-correctly: `_resolve_holder_pid` payload→getppid, Codex omitted-matcher = match-all, 4-step mode resolution incl. incumbent + anti-downgrade.
- Stale-wording grep (`ephemeral`/`inert`/old precedence): only benign unrelated hits (tmp-file "ephemeral files"). No new contradictions introduced.
- All three filed bugs closed/resolved with regression pointers.

### Residuals (none blocking)

- **LOW (new, noted):** `getppid()` = harness holds when the harness execs the hook command as a simple command (bash/dash `-c` exec-optimize; the emitted command is pipe-free). If a harness ever wraps hooks in a non-exec shell, the recorded pid is the dead wrapper → graceful degradation to TTL-only (pre-fix behavior, fail-open toward takeover, never freeze). The forward-compatible payload-pid path is the escape hatch. Worth one sentence in the sdd-gate atom someday; not an overclaim today since the text says "the hook's parent process".
- **LOW carry-overs (N-5, unaddressed as expected):** `public/scripts/__pycache__/*.pyc` still shipped; `public/data/repos.xlsx` opaque binary; ctx-inject raw 25.6 KB catalog bootstrap; sentinel GC.

### Final determinism table (claim → verdict)

| Gate | Verdict |
|---|---|
| Path-class × lease × phase × mode (D-1, D-3..D-5) | **Deterministic**, truthfully documented |
| Lease no-steal (pid veto) (D-2/N-1) | **Deterministic** — long-lived pid recorded, real-topology e2e proof |
| Heartbeat renewal (D-12/N-2) | **Deterministic on both harnesses** (Claude `*`, Codex omitted-matcher) |
| READ-mode via bind (D-10/N-3) | **Deterministic** in the default flow (incumbent ptr + anti-downgrade) |
| PROTECTED / root whitelist (D-6/D-7) | Deterministic-narrow, honestly labeled (Bash envelope = documented D-2 decision, doctor SPEC-DOC-029 backstop) |
| Markers / allowlists / tmp guardrail (D-8, D-11) | Discipline — **labeled as discipline** everywhere |
| ctx-inject (D-9), pre-push gate (D-13) | Deterministic (bloat/installation-dependence noted) |

**Remaining theater: none.** Every mechanism the surface claims is now the shipped mechanism; every discipline-only surface self-identifies as discipline. What remains is labeled residual (hygiene LOWs + the shell-exec caveat), not theater.

### NEW SCORE: 9 / 10

All three blockers closed code+text+projection with falsifying tests in the correct process topology. Withheld from 10 by the LOW residuals: ctx-inject bootstrap bloat, shipped `__pycache__`/opaque binary in canonical source, and the untested-in-live-harness getppid shell-exec assumption.

— end of rc-2 delta —
