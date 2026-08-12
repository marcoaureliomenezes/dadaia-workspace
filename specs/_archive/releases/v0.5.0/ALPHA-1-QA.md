# QA `alpha-1` review — T-50-19

> **Verdict:** REJECTED — one SPEC §6 sweep check fails (`ruff check`, 1 pre-existing
> violation in this release's own diff). The four-profile live rung matrix and every
> other sweep check are green. T-50-19 stays `[-]`; do not flip to `[x]` until
> `software-engineer` fixes the one-line finding below and this review is re-run.

**Date:** 2026-08-12T00:02:06Z
**Commit tested:** `568dccb2b48000c0eba42cf5d69b9bf5344dcc14` (`chore(tasks): start T-50-19`,
branch `feature/v0.5.0`)
**Instance:** live self-hosting workspace at the workspace root (redacted absolute
paths below as `<ws>`).

## 1. Live-instance rung matrix (FR1) — 16/16 PASS

Driven as real subprocesses against the LIVE instance (not fixtures), the way
`tests/fixtures/harness_env.py` drives them in the suite — `python -m
dadaia_workspace.hooks.<module>` for Claude/plain-shell/bare-cwd, and the REAL
installed kimi shims (`~/.kimi-code/hooks/dadaia-kimi-*.sh`) for the kimi profile.
Driver script (evidence, not committed — scratch): `.dadaia/tmp/qa-engineer/20260811/
t50_19_rung_matrix.py` + `.results.json`.

| # | Case | Result |
|---|---|---|
| P1.1 | Claude session binds (`dadaia context bind`, mode=implementation) | PASS |
| P1.2 | ctx_inject fires (fresh sentinel → full `[dadaia-workspace]` bootstrap) | PASS |
| P1.3 | gate resolves bind mode (MUTATING write → ALLOW, presence recorded) | PASS |
| P1.4 | heartbeat carries context (`sdd_post_gate` + `context heartbeat` → `context=dadaia-workspace`) | PASS |
| P2.1 | kimi ctx-inject shim fires with `DADAIA_CONTEXT` exported, no native session id | PASS |
| P2.2 | kimi pre-gate shim resolves mode via rung 1, MUTATING write ALLOWed, presence recorded | PASS |
| P2.3 | kimi post-gate shim heartbeat renews the presence record (`last_seen_at` advances) | PASS |
| P2.4 | kimi post-compact shim stamps `ctx-compact-<sid>` + re-emits bootstrap; next prompt re-injects once, then falls silent (`CONSUMER_VALIDATION_RECIPE.md` R-08) | PASS |
| P3.1 | plain shell: `dadaia context show --json` resolves via `DADAIA_CONTEXT` (rung 1) | PASS |
| P3.2 | plain shell: MUTATING write with no harness id, `DADAIA_CONTEXT` set → ALLOW, attributed | PASS |
| P3.3 | plain shell: `dadaia context heartbeat` resolves the session (`context=dadaia-workspace`) | PASS |
| P4.1 | bare `repos/dadaia-workspace/` cwd, no env at all: `context show --json` resolves via rung 3 | PASS |
| P4.2 | bare cwd, no env at all: MUTATING write outside `repos/` resolves via rung 3 (cwd's repo) | PASS |
| X1 | gate-attribution: write into `repos/consumer-repo-b/...` with `DADAIA_CONTEXT=dadaia-workspace` → attributed `consumer-repo-b` (rung 0 path-first beats rung 1) | PASS |
| X2 | no-repo write, no `DADAIA_CONTEXT`, this session's own live record → resolves rung 2 | PASS |
| X3 | `dadaia context bind` warns iff neither harness id nor `DADAIA_CONTEXT` is present; silent with `DADAIA_CONTEXT` set | PASS |

All synthetic session/presence/sentinel files this run created were cleaned up after
each case; no production file was written (the gate hook only classifies the target
PATH string — it never performs the file I/O itself). `git status` on the repo shows
no residue beyond this review file and the earlier `[-]` reservation commit.

## 2. SPEC §6 sweep

Run from `<ws>/repos/dadaia-workspace`, venv `<ws>/.dadaia/.venv/bin`.

| Check | Result | Evidence |
|---|---|---|
| `ruff format --check dadaia_workspace/ tests/` (ruff 0.16.2 pinned binary) | PASS | `758 files already formatted` |
| `ruff check dadaia_workspace/ tests/` (ruff 0.16.2 pinned binary) | **FAIL** | `Found 1 error.` — see §3 |
| `mypy --strict dadaia_workspace/` | PASS | `Success: no issues found in 261 source files` |
| `lint-imports --config setup.cfg --no-cache` | PASS | `Contracts: 9 kept, 0 broken.` (incl. the new `only cli._specs_resolution and container may import core.specs_resolver` seam contract) |
| `pytest -p no:cacheprovider -q tests/unit/hooks/ tests/unit/core/` (spot-run; full suite already green this hour — 2072 passed) | PASS | `333 passed in 282.93s` |
| `dadaia doctor` | PASS (after `--fix`) | First run found stray root-level `.playwright-mcp/` (unrelated MCP tool residue, empty, ~5h old — not from this task's write set) + 54 expired session-graveyard files; `--fix` cleared both; re-run: `All invariants OK — workspace is healthy.` |
| `dadaia specs doctor` (this context) | PASS | `[ok] overall: 0 error(s), 6 warning(s)` — warnings are pre-existing memory `token_estimate` drift, unrelated to FR1/FR2/FR3/FR4 |
| `dadaia public doctor` | PASS | `[ok] public-privacy`, `[ok] entities-derivation`, no drift on any of the 4 projected law files |
| `dadaia certify --json` (disposable scratch dir) | PASS on retry (**flaky first attempt**) | See §4 |

## 3. Ruff check finding (blocks this alpha-1 pass)

```
UP037 [*] Remove quotes from type annotation
 --> tests/fixtures/harness_env.py:385:10
    |
383 |     *,
384 |     timeout: float = 30.0,
385 |     cwd: "Path | str | None" = None,
    |          ^^^^^^^^^^^^^^^^^^^
386 | ) -> HookResult:
    |
help: Remove quotes
Found 1 error. [*] 1 fixable with the `--fix` option.
```

Reproduced identically on both the pinned ruff 0.16.2 binary and this venv's ruff
0.15.20 — not a version-drift false positive. `git blame` traces the offending line to
commit `45e91b75e` (`feat(T-50-02): sdd_gate._context_slug delegates to the single
resolution authority`, 2026-08-11), inside this release's own diff — not pre-existing
baseline debt. `tests/fixtures/harness_env.py` is shared test infrastructure owned by
`software-engineer`, outside qa-engineer's write scope (E2E tests and reports only); QA
does not fix it. **Fix recommendation:** drop the quotes around the `cwd` parameter's
type annotation (the module already carries `from __future__ import annotations`, so
the quoted forward reference is unnecessary) — a one-line, mechanical, `ruff --fix`-safe
change — then re-run this sweep.

## 4. `dadaia certify --json` — flaky first attempt, PASS on retry

**Run 1** (system load average 21–25 on an 8-core host at the time — Chrome, a Kafka
broker, Steam, and 5 concurrent `claude`/`kimi` agent sessions with active Playwright
runs were observed via `ps aux`/`uptime`): `"ok": false`, 10/11 PASS —
`workspace-init-all-harnesses` FAILed with `"process did not exit within 180s"` (the
check's own internal `dadaia init --harness all` subprocess timeout inside its scratch
workspace; unrelated to FR1 — the SPEC records "certify needs no code change" and the
check's own harness-id scrubbing/`CODEX_THREAD_ID` injection is unchanged).

**Run 2** (moments later, load average 18–22): `"ok": true`, **11/11 PASS**, including
`workspace-init-all-harnesses`. All 11 checks: `capability-contract`,
`exact-version-reconciliation`, `specs-scaffold-and-doctor`,
`context-empty-remote-baseline`, `context-list-show-json`, `context-bind-heartbeat`,
`context-specs-doctor`, `reports-handoff-validation`, `panel-and-server-registry`,
`context-dead-alive-delete-roundtrip`, `workspace-init-all-harnesses`.

Verdict: an environment-load flake on this heavily-contended shared host, not a
regression — confirmed by the deterministic PASS on immediate retry with no code
change in between. Evidence: `.dadaia/tmp/qa-engineer/20260811/certify-scratch/
certify-out.json` (run 1, `ok:false`) and `certify-out2.json` (run 2, `ok:true`).

## 5. Security/privacy leakage note

No new leakage surface observed. This session performed read-only probing plus
synthetic session/presence records it deleted immediately after use; no secrets, tokens,
or credentials were read, generated, or logged. The one root-hygiene finding cleared by
`dadaia doctor --fix` (`stray .playwright-mcp/`) was an empty directory with no
contents — no data exposure. No dependency was added. No consumer-specific data was
touched (the consumer-repo-b gate-attribution probe never wrote a real file — the gate only
classifies the target path string).

## 6. Disposition

T-50-19 stays `[-]`. Next action: `software-engineer` applies the one-line `ruff --fix`
in `tests/fixtures/harness_env.py:385`, pushes the fix on `feature/v0.5.0`, and
`qa-engineer` re-runs this sweep (rung matrix does not need to be re-run — it is
independent of the ruff finding) before flipping `[-]` → `[x]`.

## 7. Addendum — 2026-08-12T00:12:33Z — verdict updated to PASS

`software-engineer` fixed the §3 finding in commit `77d37aee1937e90b49ea4bb8a1f2b7a1fba881c8`
(`fix(T-50-02): drop redundant quotes from cwd annotation (UP037, QA alpha-1 finding)`) —
the one-line de-quote of `tests/fixtures/harness_env.py:385`, per the recommendation
above. Re-verified the previously-failing check only (the rung matrix in §1 is
independent of this finding and was not re-run):

```
$ ruff check dadaia_workspace/ tests/    # ruff 0.16.2, pinned binary
All checks passed!
$ ruff format --check dadaia_workspace/ tests/    # ruff 0.16.2, pinned binary
758 files already formatted
```

Both exit 0. Combined with §1 (16/16 rung-matrix PASS) and the rest of §2 (8/9 already
PASS before this fix, `mypy --strict`/`lint-imports`/spot `pytest`/`dadaia doctor`/
`dadaia specs doctor`/`dadaia public doctor`/`dadaia certify --json` unaffected by a
test-fixture-only change), **all SPEC v0.5.0 §6 acceptance criteria for T-50-19 are now
met.**

**Updated verdict: APPROVE / PASS.** T-50-19 flips `[-]` → `[x]` at commit
`77d37aee1937e90b49ea4bb8a1f2b7a1fba881c8`. The REJECTED verdict and finding in the
header and §3 above are preserved verbatim as the historical record of what blocked the
first pass and how it was resolved — this addendum does not rewrite them.
