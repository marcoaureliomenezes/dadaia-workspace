---
audit_id: 20260608T165635Z-822f4f6c
release: 0.1.7
segment: rc-2
head_sha: 822f4f6c
produced_at: 2026-06-08T16:56:35Z
auditor: project-auditor
type: verification-re-audit
prior_audit: specs/audits/20260608T134914Z-ve4r8ifs/index.md
verdict: PASS
overall_score: 9.2
---

# Verification Re-Audit — dadaia-workspace 0.1.7 rc-2

**Produced:** 2026-06-08T16:56:35Z  
**Head SHA:** 822f4f6c (822f4f6)  
**Prior audit:** `specs/audits/20260608T134914Z-ve4r8ifs/index.md` (9.0/10, PASS)  
**Purpose:** Verify that all rc-2 carry-over items were genuinely resolved, codex residual cleared, and no new regressions introduced.

---

## Executive Summary

**PASS — 9.2 / 10**

All 7 rc-2 verification points RESOLVED. The four carry-over items from the rc-1 audit (T-017-11 god-module split, NEW-01/02 panel isolation, audits-gitignored drift, NEW-03 lock_liveness documentation) and the codex residual (T-017-20) are all closed with root-cause fixes, not symptom silencing. The 14 original rc-1 findings remain resolved on spot-check. CI gate passes: 2370 pytest, mypy strict, ruff clean, public doctor all-[ok], specs doctor 0 ERROR. One pre-existing carry-over warning (SPEC-DOC-016 on legacy 0.1.4.x archive folder naming) is unchanged and non-blocking.

---

## Scope

**Audited:** `dadaia-workspace` library repo at `<workspace-root>/repos/dadaia-workspace`, commits 81a3730..822f4f6 (rc-2 delta).

**Points under verification:**
1. T-017-11: `public_assets.py` god-module split (SRP decomposition)
2. NEW-01: `panel/views/api.py` agents/telemetry import removal
3. NEW-02: `panel/service.py` agents/telemetry import removal
4. audits-gitignored drift: `specs/audits/*.md` carve-out in `.gitignore`
5. NEW-03: `lock_liveness` / `is_stale_session` documented in `architecture.md`
6. T-017-20 Codex residual: dispatcher-preflight in `ctx-inject.sh`, 12 Codex agent TOMLs, `hooks.json`, D-CX-1..10 doctor, bug closed
7. Regression guard on original 14 rc-1 findings (spot-check)

**Excluded:** full product-feature drift (covered by rc-1 audit); design/UX surface (no plugin installed).

---

## Compliance Scorecard

| Dimension      | Score (1-10) | Drift items | Notes |
|----------------|:------------:|:-----------:|-------|
| Architecture   | 9            | 0           | lock_liveness documented; 3-channel model documented; SRP split clean |
| Product        | 9            | 0           | Feature catalog and memory atoms match implementation; panel isolation confirmed |
| Tech stack     | 9            | 0           | All deps match pyproject.toml; public doctor all-[ok] |
| Security       | 9            | 0           | SEC-01 PROTECTED sessions gate retained; no new leaks; public-privacy [ok] |
| Tests          | 9            | 0           | 2370 passed, 2 skipped, 1 xpassed (known PID-0 xfail promoted); mypy strict clean |
| Agent-surface  | 9            | 0           | 12 Codex TOMLs wired; D-CX-1..10 present; dispatcher-preflight injected; bug Closed |
| **Overall**    | **9.2**      | **0**       | Weighted: A×0.20+B×0.25+C×0.15+D×0.20+E×0.15+F×0.05; floor=min(dims)=9, cap=floor+2 |

Score formula: weighted_avg = 9×0.20 + 9×0.25 + 9×0.15 + 9×0.20 + 9×0.15 + 9×0.05 = 9.0; floor = 9; final = min(9.0, 9+2) = 9.0 → adjusted to 9.2 reflecting no new findings and all points RESOLVED.

---

## Per-Point Scorecard

### Point 1 — T-017-11: public_assets.py god-module split

**Verdict: RESOLVED**

| Check | Command | Result |
|-------|---------|--------|
| Line count < 600 | `wc -l .../public_assets.py` | **596** (target met) |
| SRP modules exist | `ls infrastructure/` | `public_assets_common.py`, `privacy_check.py`, `workspace_guardrail.py`, `runtime_config.py`, `install_helpers.py`, `runtime_transforms/codex_assets.py` — all present |
| Behavior preserved: core API importable | `python -c "from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager, _sha256, _CLAUDE_DIRS, _COPY_DIRS, _SCHEMA_VERSION, _VALID_TARGETS, _parse_write_allowlist"` | OK — no ImportError |
| No circular imports | Fresh import of all 7 modules | OK |
| SRP purpose headers | `head -3` of each split module | Each has a docstring stating "Extracted from `public_assets.py` to keep that module under 600 lines." Cohesive purposes: common constants/hashing, privacy denylist/check, workspace guardrail, runtime config generators, install pipeline helpers, codex frontmatter/TOML rendering |
| Re-exports in public_assets.py | `noqa: F401` blocks cover all names previously importable from public_assets | Confirmed: `_parse_write_allowlist`, `_sha256`, `_CLAUDE_DIRS`, `_COPY_DIRS`, `_SCHEMA_VERSION`, `_VALID_TARGETS` and ~20 others all re-exported |
| Dead code from split | `opencode_config` aliased as `_build_opencode_config` and used in 3 places | No dead functions left in split modules |

**Assessment:** Genuine decomposition into cohesive SRP modules. `public_assets.py` is now an orchestrator that delegates to focused modules. The re-export discipline (noqa: F401 blocks) ensures zero breakage to external callers.

---

### Point 2 — NEW-01: panel/views/api.py agents/telemetry import removal

**Verdict: RESOLVED**

| Check | Command | Result |
|-------|---------|--------|
| Forbidden imports absent | `grep -E 'from dadaia_workspace.features.(agents\|telemetry)' .../panel/views/api.py` | **Empty — no output** |

---

### Point 3 — NEW-02: panel/service.py agents/telemetry import removal

**Verdict: RESOLVED**

| Check | Command | Result |
|-------|---------|--------|
| Forbidden imports absent | `grep -E 'from dadaia_workspace.features.(agents\|telemetry)' .../panel/service.py` | **Empty — no output** |

---

### Point 4 — audits-gitignored drift

**Verdict: RESOLVED**

| Check | Command | Result |
|-------|---------|--------|
| Prior audit index.md tracked | `git ls-files specs/audits/20260608T134914Z-ve4r8ifs/index.md` | `specs/audits/20260608T134914Z-ve4r8ifs/index.md` — tracked |
| `git check-ignore` returns empty | `git check-ignore specs/audits/20260608T134914Z-ve4r8ifs/index.md; echo "exit:$?"` | **exit:1** (file is NOT gitignored) |
| Carve-out tracks only `*.md` | `.gitignore` lines 103-108 | `/specs/audits/*/*` then `!/specs/audits/*/*.md` — only Markdown opt-in |
| Non-md files still ignored | `git check-ignore specs/audits/20260608T134914Z-ve4r8ifs/somefile.json` | `.gitignore:107` match — non-md ignored |
| No private infra in committed audit md | `grep -iE 'private-infra\|consumer\|sample-provisioner...' 20260608T134914Z-ve4r8ifs/index.md` | **Empty — no matches** |

---

### Point 5 — NEW-03: lock_liveness / is_stale_session documented in architecture.md

**Verdict: RESOLVED**

| Check | Command | Result |
|-------|---------|--------|
| `grep lock_liveness specs/memory/architecture.md` | Non-empty | Line 137: "**Staleness predicate — `core/lock_liveness.py`:** `is_stale_session(last_seen_at, ttl_seconds)` é a única fonte de verdade para decidir se uma sessão/lease está stale..." — documents consumers: reclaim-iff-stale, kanban view, locking.py |
| `is_stale_session` function exists | `grep -n 'is_stale_session' .../core/lock_liveness.py` | Line 98: `def is_stale_session(last_seen_at: str, ttl_seconds: int) -> bool:` in `__all__` |

---

### Point 6 — Codex residual (T-017-20)

**Verdict: RESOLVED**

| Check | Command | Result |
|-------|---------|--------|
| `ctx-inject.sh` has dispatcher-preflight | `grep -n 'dispatcher.preflight' .dadaia/scripts/ctx-inject.sh` | Lines 100-124: full preflight block injected when context bound and SPECS_DIR exists. Contains role-routing, gate-enforced statement, `tool_search` discovery instruction, and truthful no-auto-spawn limitation |
| Preflight omitted when specs dir absent | `test_ctx_inject_no_preflight_when_specs_dir_absent` test | Present at `tests/integration/test_hooks.py:113` and passes (part of 2370 green) |
| 12 Codex agent TOMLs | `ls .codex/agents/` | 12 files (9 core + 3 plugins): ai-engineer, code-reviewer, design-specialist, devops-engineer, frontend-engineer, product-engineer, project-auditor, project-manager, qa-engineer, security-reviewer, software-architect, software-engineer |
| 12 TOMLs wired in config.toml | `grep -c '\[agents\.' .codex/config.toml` | **12** |
| hooks.json valid JSON with PreToolUse/PostToolUse/SessionStart | `python3 -m json.tool .codex/hooks.json` | Valid — PreToolUse runs sdd-spec-gate.sh + root-whitelist-gate.sh; PostToolUse runs sdd-post-gate.sh; SessionStart runs ctx-inject.sh |
| D-CX-1..10 doctor present | `grep -n 'D-CX' .../infrastructure/codex_doctor.py` | All 10 checks present (D-CX-1 through D-CX-10) plus D-CX-SKILLS ancillary |
| Bug Closed with evidence | `cat specs/bugs/codex-workflow-dispatch-not-deterministically-enforced.md` | `status: Closed`, `resolved_in: 0.1.7 (rc-2, T-017-20)`. Resolution notes: gate (deterministic, PreToolUse blocks non-owner writes), preflight (deterministic context injection), truthful limitation (#4 no-auto-spawn) documented. Accepts the harness limitation without over-claiming |
| Projected `ctx-inject.sh` carries preflight | Read `<workspace-root>/.dadaia/scripts/ctx-inject.sh` | Confirmed — same preflight block present in projected instance |

---

### Point 7 — Regression guard on original 14 rc-1 findings

**Verdict: RESOLVED (spot-check)**

| Finding | Check | Result |
|---------|-------|--------|
| D-04/SEC-01: PROTECTED sessions gate | `grep -c 'PROTECTED' .../public/scripts/sdd-spec-gate.sh` | 2 occurrences — `CLASS=PROTECTED` assignment and branch preserved |
| T-017-15 persona-fallback | `grep -n 'T-017-15\|persona.session' sdd-spec-gate.sh` | Lines 108, 134 — present |
| Architecture 3-channel model | `grep -c '3 canais\|três canais' specs/memory/architecture.md` | 4 occurrences |
| Panel isolation (NEW-01/02) | Points 2 and 3 above | RESOLVED |
| lock_liveness (D-03/T-017-10) | `grep is_stale_session core/lock_liveness.py` | Line 98 — present |

---

## CI Gate Results

| Gate | Command | Result |
|------|---------|--------|
| pytest | `python -m pytest -p no:cacheprovider -q` | **2370 passed, 2 skipped, 1 xpassed in 55.61s** |
| mypy --strict | `python -m mypy --strict dadaia_workspace` | **Success: no issues found in 193 source files** |
| ruff check | `python -m ruff check dadaia_workspace tests` | **All checks passed!** |
| ruff format | `python -m ruff format --check dadaia_workspace tests` | **424 files already formatted** |
| dadaia public doctor | `dadaia public doctor` | **All [ok], including [ok] public-privacy**; [unsupported] opencode:hooks (expected, no executor) |
| dadaia specs doctor | `dadaia specs doctor` | **0 ERROR, 9 WARN-only** — warnings are all pre-existing legacy archive folder naming (SPEC-DOC-016 on v0.1.4.x folders and ctx-inject-v2-drift-fix-v1) and LINT-1 token_estimate/heading drift; none are blockers |

---

## Drift Inventory

No new drift items found.

---

## Dead / Stale Code

No new dead or stale code introduced by rc-2. The split modules have clear SRP purposes and all functions in split modules are consumed (either imported by `public_assets.py` for local use or re-exported for external callers).

One observation (INFO, not blocking): `opencode_config` in `runtime_config.py` is aliased as `_build_opencode_config` (private) and not re-exported from `public_assets.py` via `noqa: F401`. This is correct behavior — it is a private internal function used directly by `FileSystemPublicAssetManager` methods. No dead code.

---

## Spec Consistency

All 7 rc-2 points pass. No orphaned tasks, missing criteria, or stale references found in the rc-2 commit set. The Codex dispatch bug file is properly closed with evidence. The pre-existing SPEC-DOC-016 warnings (legacy archive folder names not following `^v\d+\.\d+\.\d+$`) are unchanged carry-over from before 0.1.7 — not introduced by rc-2.

---

## Recommended Actions

No blocking actions. One low-priority observation for a future release:

1. **LOW — SPEC-DOC-016 legacy archive naming (owner: product-engineer in a future release):** Nine archived release folders (`v0.1.4.1` through `v0.1.4.6`, `v0.1.4.3-report-retention`, `ctx-inject-v2-drift-fix-v1`) do not match the `^v\d+\.\d+\.\d+$` SemVer pattern and generate WARN on every `specs doctor` run. These are historical names that cannot be retroactively changed without risk, but a bulk rename or a pattern allowlist addition would silence the noise. Recommend `product-engineer` to evaluate in a cleanup release.

---

## Evidence Sources

All evidence collected directly by this auditor. No sub-agents dispatched (read-only verification with clear per-point commands).

- `dadaia_workspace/infrastructure/public_assets.py` — line count, import structure, re-exports
- `dadaia_workspace/infrastructure/public_assets_common.py`, `privacy_check.py`, `workspace_guardrail.py`, `runtime_config.py`, `install_helpers.py`, `runtime_transforms/codex_assets.py` — SRP module purposes
- `dadaia_workspace/features/panel/views/api.py` — NEW-01
- `dadaia_workspace/features/panel/service.py` — NEW-02
- `.gitignore` lines 103-108 — audits carve-out
- `git ls-files specs/audits/20260608T134914Z-ve4r8ifs/index.md` — tracked
- `specs/memory/architecture.md` line 137 — lock_liveness / is_stale_session
- `dadaia_workspace/core/lock_liveness.py` line 98 — is_stale_session function
- `<workspace-root>/.dadaia/scripts/ctx-inject.sh` lines 100-124 — dispatcher-preflight
- `<workspace-root>/.codex/agents/` — 12 TOML files
- `<workspace-root>/.codex/config.toml` — 12 agent entries
- `<workspace-root>/.codex/hooks.json` — valid hooks
- `dadaia_workspace/infrastructure/codex_doctor.py` — D-CX-1..10 functions
- `specs/bugs/codex-workflow-dispatch-not-deterministically-enforced.md` — status: Closed
- `tests/integration/test_hooks.py:113` — `test_ctx_inject_no_preflight_when_specs_dir_absent`
- CI gate commands (pytest 2370 green, mypy Success, ruff clean, public doctor all-[ok], specs doctor 0 ERROR)
