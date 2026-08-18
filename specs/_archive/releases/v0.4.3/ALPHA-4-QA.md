# ALPHA-4-QA.md — `alpha-4` (WS-C, the Codex fidelity boundary) segment QA gate

**Task:** T-043-37 · **Reviewer:** qa-engineer · **Segment range:** `5c7b7616` (alpha-3
close) `..` `02c129fe` (T-043-36, last alpha-4 commit) · **Reviewed at:** `fb80e181`
(reservation commit, `feature/0.4.3`) · **Reviewed:** 2026-08-17

**Verdict: APPROVED** — every `alpha-4` acceptance id (A22.1–A22.8) verified against the
live tree, PLAN §5's `alpha-4` exit criteria are met, live `dadaia certify --json`
exercises the installed `codex-cli 0.147.0` through the `codex-live-probe` check with
`"ok": true`, and the one in-segment Arm-B rider carries a complete
`reported`→`resolved` bug-ledger pair with zero open bugs at review time.

---

## 1. Scope and method

Task delta: T-043-32 (`4428593f`), T-043-33 (`da73d84e`), T-043-34 (`a9aa1215` +
in-segment Arm-B rider `8c50e1ca`), T-043-35 (`2a96e2ac`), T-043-36 (`02c129fe`). 11
commits total in `5c7b7616..02c129fe` (5 implementation commits, 5 `chore(tasks): start`
reservation commits, 1 Arm-B rider).

Every prior evidence artifact under `.dadaia/tmp/{ai-engineer,software-engineer}/20260817/`
(T-043-32 scoping note + V7 capture, T-043-33 compaction/law-once evidence, T-043-34
live-probe capture, T-043-36 V8 projection-isolation capture) is read directly by this
review, and every load-bearing claim is independently re-verified against the live tree
at HEAD rather than trusted from the prior session's prose. Where a claim is
re-confirmed live (grep, byte count, `diff`, `pytest`, `dadaia certify --json`), the
command and its live output are cited alongside the originating artifact.

---

## 2. Per-acceptance-id table

| id | Requirement (abridged) | Evidence | Verdict |
|---|---|---|---|
| A22.1 | Nine persona TOMLs shrink measurably against a re-measured byte baseline | V7 (`v0.4.3-T-043-32-v7-codex-byte-baseline.md`, `4428593f`) — 9 TOMLs, 127,594 B total, re-measured against the void 2026-08-15 figure (126,155 B, explicitly not quoted as current). V8 (`v0.4.3-T-043-33-compaction-and-law-once-evidence.md`, `da73d84e`) — 116,970 B total, **−10,624 B (−8.3%)**, every one of the 9 TOMLs shrank (none grew). Live re-verification: `wc -c <workspace-root>/.codex/agents/*.toml` → **116,970 total**, byte-identical to V8's recorded figure at current HEAD (`02c129fe`, T-043-36 touched no persona TOML) | PASS |
| A22.2 | Law loaded exactly once, executed-path evidence for parent **and** delegated custom agent | `v0.4.3-T-043-33-compaction-and-law-once-evidence.md` — investigation finding: the law reaches every Codex context via **native per-directory `AGENTS.md` discovery**, independent of `SessionStart`/`SubagentStart` hooks. Live executed-path proof (codex-cli 0.147.0, `codex exec --sandbox read-only`): parent session unprompted quoted the literal opening words of the projected root `AGENTS.md`; a delegated custom-agent subagent (`agent_type="software-engineer"`, non-forked) independently confirmed both its own compacted-persona identity and `AGENTS.md` visibility. A22.1's compaction removed the inline law restatement that had made it load twice, so it now loads exactly once (native `AGENTS.md`) for both. **Stated gap, disposed in §4 below.** | PASS |
| A22.3 | `codex_trust_boundary_info` carries version-qualified observations; no unqualified headless claim survives | Live re-verification: `infrastructure/codex_doctor.py:642` defines `_CODEX_HOOKS_LIVE_CERTIFIED_VERSION = "codex-cli 0.144.4"`; `:645` `_probe_installed_codex_version`; `:674` `codex_trust_boundary_info(*, version_probe=...)` degrades honestly (absent → UNVERIFIED; version ≠ certified → UNVERIFIED + rerun instruction; exact match → asserts the fire-in-both fact). Live `dadaia public doctor` confirms the honest-degrade branch fires for real at this HEAD: `[info] codex:trust-boundary — installed codex-cli 0.147.0 has not been live-certified... UNVERIFIED for this version — rerun dadaia certify` — exactly the documented behavior, not a stale unqualified claim | PASS |
| A22.4 | Certification probes exercise the installed Codex; static tests validate shape only | `v0.4.3-T-043-34-live-probe.md` — `_codex_live_probe_detail` wired as the `codex-live-probe` check inside `certify()`; a real `SubprocessCertificationProcess` (never a mock) invoked a real `codex --version` and `codex exec --sandbox read-only`. **Live re-run by this review**, `dadaia certify --json` → `"ok": true`, 12 checks, `codex-live-probe` — `PASS — codex-cli 0.147.0: live exec probe observed 'DADAIA-LIVE-PROBE-OK'`, confirming the check exercises the installed Codex binary at review time (command + full check list in §5) | PASS |
| A22.5 | `ENT-DERIVE-1` proves behavioral fidelity with mutation fixtures; each drift class blocks | `check_entities_derivation` gained 3 helpers (`_persona_content_drift`, `_behavior_content_drift`, `_behavior_module_ref_missing`) extending name/shape bijection to content-level drift (stub bodies, identity swaps, broken module references). Live re-run by this review: `pytest tests/unit/infrastructure/test_entities_derivation_behavioral.py tests/contract/test_codex_skill_ref_prefixes.py -q` → **17 passed** (10 + 7, matching the 6 drift-class fixtures + 4 pre-existing + a package-form/additive/clean-baseline/real-tree set); live `dadaia public doctor` still reports `entities-derivation: 9 Personas ↔ 9 core sub-agents; 5 Deterministic Behaviors derived for all entry harnesses [ok]` — unchanged text, real tree carries zero behavioral drift | PASS |
| A22.6 | Every `_CODEX_SKILL_REF_PREFIXES` entry corresponds to a real skill or a documented runtime-asset exception, derived from the inventory by a test | Live re-verification: `infrastructure/runtime_transforms/codex_assets.py:64` — `_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS: frozenset[str] = frozenset({"memory-ctx"})`, backed by the real `public/runtime/codex/memory-ctx/SKILL.md` runtime asset. `tests/contract/test_codex_skill_ref_prefixes.py` (bundled in the 17-pass re-run above) derives the whole tuple from the on-disk inventory and self-tests the detector against a fabricated phantom and an undocumented exception | PASS |
| A22.7 | `ai-harness-codex/SKILL.md` no longer documents a non-existent directory | Live re-verification: `grep -n "public/rules" dadaia_workspace/public/skills/ai-harness-codex/SKILL.md` → the only hit is the **negation** itself (line 112: "**There is no `public/rules/` directory in this workspace.**"), not the stale taxonomy claim; `ls dadaia_workspace/public/` confirms no `rules/` entry exists on disk. §9's interactive/headless framing reconciled to a version-qualified table (0.139.0 SUPERSEDED vs 0.144.4 live-certified). Repo-wide grep for `12 persona`/`12-persona`/`twelve persona` across `dadaia_workspace/public/**` → **zero hits** (live re-run by this review) | PASS |
| A22.8 | A byte-diff proves no non-Codex projection changed | `v0.4.3-T-043-36-v8-projection-isolation.md` — full sha256 inventory of 81 files across `.claude/**`, `.agents/**`, `.codex/**`, `.kimi-code/**`, and the root law/rule copies, captured before/after T-043-36's edit + reprojection. **Independently re-diffed by this review**: `diff <pre-capture> <post-capture>` → exactly 2 lines differ (`.agents/skills/ai-harness-codex/SKILL.md`, `.claude/skills/ai-harness-codex/SKILL.md` — the one canonical skill file's two harness-discovery mirrors; no Codex-specific rendering seam exists for skill bodies, unlike persona TOMLs). Every persona `.toml`, every hook, config, `.rules` file, the other 23 skills, all `.kimi-code/**` files, and the four law/rule copies are byte-identical. Reasoned classification: the two-line change is the intended single-source propagation of the one Codex-authoring skill this task edited, not drift into an unrelated non-Codex surface | PASS |

All 8 acceptance ids verify PASS with live-tree evidence re-confirmed by this review,
independent of the originating session's prose.

---

## 3. PLAN §5 `alpha-4` exit criteria

> `alpha-4` exits when: FR22 `[x]`; V7/V8 captured; `entities-derivation` `[ok]`; live
> certification evidence; `qa-engineer` review committed.

| Criterion | Status |
|---|---|
| FR22 `[x]` | T-043-32…36 all `[x]` in `TASKS.md` (confirmed: 5/5 `[x]` markers in the `alpha-4` block prior to this task) |
| V7 captured | `v0.4.3-T-043-32-v7-codex-byte-baseline.md` (127,594 B, 9 TOMLs) |
| V8 captured | `v0.4.3-T-043-36-v8-projection-isolation.md` (81-file sha256 inventory, 2 lines differ, re-diffed live by this review) |
| `entities-derivation` `[ok]` | Live `dadaia public doctor` → `[ok] entities-derivation: 9 Personas ↔ 9 core sub-agents; 5 Deterministic Behaviors derived for all entry harnesses (ENT-DERIVE-1)` |
| Live certification evidence | Live `dadaia certify --json` run by this review (§5) → `"ok": true`, `codex-live-probe` PASS against installed `codex-cli 0.147.0` |
| `qa-engineer` review committed | This document, committed alongside T-043-37's `[x]` flip |

**All exit criteria met.**

---

## 4. Disposition — the three items this review must judge explicitly

### 4.1 The T-043-33 stated gap: `ctx_inject` memory-bootstrap injection is `SessionStart`-only

**Verdict: record-only, does not block A22.2.**

A22.2's literal text is: *"The law is loaded exactly once in the effective Codex
context, with executed-path evidence for the parent session and a delegated custom
agent."* The acceptance id is scoped to **the law** (the canonical `DADAIA.md` /
`AGENTS.md` corpus). T-043-33's live executed-path evidence proves exactly that claim for
both the parent session and a delegated custom-agent subagent, via Codex's native
per-directory `AGENTS.md` discovery — a mechanism that does not depend on
`SessionStart`/`SubagentStart` hook wiring at all.

The gap T-043-33 names is a **different, narrower mechanism**: `ctx_inject`'s
dadaia-specific convenience injection (`tech-stack.md` verbatim + `catalog.json`),
delivered today only on `SessionStart` (parent session), with no `SubagentStart` wiring.
This is explicitly NOT the law — the `dadaia-step0-memory-bootstrap` skill itself
documents that a session lacking the automatic injection can still self-pull
`specs/memory/product/catalog.json` under its own judgment step, which is precisely what
this review's own memory-bootstrap step did. Fixing the `SubagentStart` wiring gap would
touch `runtime_config.py`'s `codex_hooks()` builder — outside T-043-33's declared write
set (`codex_assets.py` + the Codex projection).

Judged against SPEC wording and PLAN's exit criteria (A22.2 alone, not a broader
"delegated-agent parity" claim), the gap is **record-only** for CLOSURE's narrative, not
a blocker. It is not silently dropped: it is a legitimate, correctly-scoped observation
that names a real (lower-priority) seam gap. Routing: this is a `ctx_inject` hook-wiring
enhancement, not a bug (the tool does not violate a contract it promises — the
`dadaia-step0-memory-bootstrap` skill already documents the self-pull fallback for
exactly this case) and not a fresh FR22 scope item (A22.2 is satisfied on its own terms).
It is named here so `project-manager`'s intake report can decide whether to route it to
the backlog as a future convenience improvement; this review does not materialize it as
backlog demand itself.

### 4.2 The two rider bugs of this segment

**Correction, evidence-based: this review finds exactly ONE Arm-B rider bug in the
`alpha-4` window, not two.**

Searching `specs/bugs/bugs.jsonl` for every event timestamped inside the `alpha-4` window
(after the alpha-3 close commit `1ac8e0ea`, 2026-08-17T20:27:18Z, through `02c129fe`)
finds a single bug id: `t043-33-absolute-path-leaked-into-tasks-md`. TASKS.md's own
`alpha-4` block names exactly one Arm-B rider (T-043-34's entry: "Arm-B in-segment rider
(escalate-at-discovery, precedent `03bc12d3`)"), no second rider is named anywhere in the
`alpha-4` task block or PLAN's execution-order diagram. (The
`ruff-0-16-2-markdown-python-fence-format-drift` bug, reported/resolved at 20:09:20Z/
20:24:17Z — before the 20:27:18Z alpha-3 close — belongs to `alpha-3` and is already
accounted for in `ALPHA-3-QA.md`'s rider table; it is not an `alpha-4` rider.)

The single rider's ledger pair:

| Rider commit | Bug id | `reported` | `resolved` |
|---|---|---|---|
| `8c50e1ca` | `t043-33-absolute-path-leaked-into-tasks-md` | 2026-08-17T21:20:52Z | 2026-08-17T21:22:18Z |

Confirmed by direct read of `specs/bugs/bugs.jsonl` (lines 905–906): the `reported` event
names the symptom (a live-Codex transcript in T-043-33's TASKS.md evidence paragraph
reproducing the operator's absolute local workspace path, caught by
`test_repo_self_scan.py`), and the `resolved` event records the fix (masked to
`<workspace-root>` with an inline redaction note) plus reproducing-test evidence (RED
before with 1 unexpected hit, GREEN after; full self-scan suite 5 passed / 0 failed). Live
`dadaia bugs status` at review time (§5): **`[ok] 0 open bug(s)`.**

### 4.3 The stale `specs/memory/product/harness/harness-codex.md` framing (flagged by T-043-36)

**Verdict: correctly routed to the `rc-1` CLOSURE memory window; named UNVERIFIED-by-design, matching `ALPHA-3-QA.md`'s precedent for A21.5/A21.6.**

Live re-verification: `specs/memory/product/harness/harness-codex.md:33-34` still reads
*"Headless asymmetry (honesty): `codex exec` fires NO hooks (upstream codex-cli defect,
live-verified)"* — the stale, unqualified 0.139.0-era claim, contradicting the
version-qualified 0.144.4-live-certified fact this segment established in
`codex_doctor.py`, the `ai-harness-codex` skill, and the three academy lessons (all
confirmed edited in §2's A22.7 row). T-043-36's own evidence explicitly flags this atom
and explicitly does **not** edit it, citing SPEC's memory-ownership table, which routes
this atom's harness-codex update to CLOSURE, owned by `product-engineer`.

`specs/memory/` is MEMORY-class, writable only in `DEFINITION` and `CLOSURE` phase per
`DADAIA.md` §3 / the SDD gate. This release's `ACTIVE.md` records `phase: IMPLEMENTATION`
— no agent, including `ai-engineer` in T-043-36, could have edited this atom inside
`alpha-4` without violating the phase gate. This is the exact same posture
`ALPHA-3-QA.md` §2 applied to A21.5/A21.6 (CLOSURE-phase memory work correctly deferred,
named UNVERIFIED rather than silently passed). Applying that precedent here: **the
harness-codex.md staleness is UNVERIFIED-by-design at this segment boundary**, not a gap
in `alpha-4`'s execution, and it is not a new acceptance id this review invents — it is
carried forward as an explicit CLOSURE input alongside A13.3/A18.6/A20.2/A21.5/A21.6's
memory-window backlog.

---

## 5. Suite, doctor and certification run (live, this session)

All commands run against `feature/0.4.3`; the suite/doctor commands ran at the pre-existing
tip `02c129fe`, this review's own reservation commit `fb80e181` touches only `TASKS.md`,
no source:

| Check | Command | Result |
|---|---|---|
| Full suite | `pytest -p no:cacheprovider -m 'not quarantine' -n auto` | **2471 passed, 3 skipped, 0 failed** (48.88s) — identical to T-043-36's recorded baseline (doc-only change since T-043-35, no test added/removed) |
| CI preflight | `dadaia ci preflight` | **5/5 PASS** — `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest` |
| Workspace doctor | `dadaia doctor` | **All invariants OK — workspace is healthy** |
| Specs doctor | `dadaia specs doctor --context dadaia-workspace` | **0 errors, 5 warnings** — 1 `LINT-1` heading-allowlist warning family (pre-existing, deferred to T-043-51/A13.3) + 2 `SPEC-DOC-027` legacy release-dir names (pre-existing, unrelated) + 2 `SPEC-DOC-036` un-disposed archived-audit warnings (pre-existing, unrelated) — none newly introduced by `alpha-4`, identical set to `ALPHA-3-QA.md`'s record |
| Public doctor | `dadaia public doctor` | 0 `[error]` lines; **`[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution`**; one `[info] codex:trust-boundary` line — installed `codex-cli 0.147.0` UNVERIFIED for hook-fire behavior (last certified 0.144.4), exactly A22.3's documented honest-degrade branch firing for real, not a defect |
| Backlog doctor | `dadaia backlog doctor` | **backlog doctor: clean.** |
| Certification (A22.4, live) | `dadaia certify --json` | **`"ok": true`, 12/12 checks PASS**, including `codex-live-probe — codex-cli 0.147.0: live exec probe observed 'DADAIA-LIVE-PROBE-OK'` — the disposable-workspace certification journey genuinely invoked the installed Codex CLI end to end |
| A22.5/A22.6 regression (targeted) | `pytest tests/unit/infrastructure/test_entities_derivation_behavioral.py tests/contract/test_codex_skill_ref_prefixes.py -q` | **17 passed** |
| A22.1 byte baseline (targeted) | `wc -c <workspace-root>/.codex/agents/*.toml` | **116,970 total** — matches V8 exactly |
| A22.8 isolation (targeted) | `diff` of the T-043-36 pre/post 81-file sha256 captures | **2 lines differ**, matches the recorded evidence exactly |

The certification `codex-live-probe` check is the CERTIFICATION evidence PLAN §5 requires
for `alpha-4`'s exit — run live by this review against the installed Codex CLI
(`codex-cli 0.147.0`), not re-quoted from the implementer's prior session.

---

## 6. Findings

No CRITICAL, HIGH, or MEDIUM findings. No LOW findings requiring intake.

**INFO (record-only, already covered by design, not repeated in intake):**
- §4.1 — the `ctx_inject` `SubagentStart` wiring gap is a legitimate, correctly-scoped
  observation, judged not to block A22.2 (see reasoning above); named for
  `project-manager`'s intake report to decide whether it becomes future backlog demand.
- §4.2 — the operator's framing named "two rider bugs"; this review's evidence-based
  count is one. Corrected here rather than silently repeated, per the evidence-based
  verdict this artifact is required to give.
- §4.3 — the `harness-codex.md` staleness is UNVERIFIED-by-design at this segment
  boundary (MEMORY-class, CLOSURE-phase work), carried forward to CLOSURE alongside the
  other memory-window items already tracked by `ALPHA-3-QA.md` and this release's own
  memory-ownership table.

---

## 7. Verdict

**APPROVED.** All 8 `alpha-4` acceptance ids (A22.1–A22.8) PASS with live-tree evidence,
independently re-verified by this review rather than re-quoted from the implementer's own
session. PLAN §5's `alpha-4` exit criteria are fully met, including the CERTIFICATION
evidence requirement: a live `dadaia certify --json` run by this review shows `"ok":
true` with the `codex-live-probe` check genuinely exercising the installed `codex-cli
0.147.0`. The single in-segment Arm-B rider is closed with a complete bug-ledger pair;
`dadaia bugs status` shows zero open bugs at review time (the operator's "two rider bugs"
framing is corrected to one, with evidence). The T-043-33 stated gap
(`ctx_inject`'s `SubagentStart`-only convenience injection) does not block A22.2 — the law
itself is proven to load once for both parent and delegated sessions via native
`AGENTS.md` discovery. The `harness-codex.md` staleness is correctly deferred to the
`rc-1` CLOSURE memory window, named UNVERIFIED-by-design per the same precedent
`ALPHA-3-QA.md` set for A21.5/A21.6. The full gating suite, `dadaia ci preflight`,
`dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor`, and `dadaia backlog
doctor` are all green. `alpha-4` is cleared to close.
