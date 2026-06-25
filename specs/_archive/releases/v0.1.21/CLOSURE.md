# Closure: Release — v0.1.21

> **Status:** Aprovado
> **Release ID:** v0.1.21
> **Owner:** product-engineer
> **Closed:** 2026-06-25

## Summary

v0.1.21 implements **WS-PI-4**: a Layer-1 **Ring-1** (pre-disk) SDD-gate extension for PI,
the analog of the Claude Code / Codex PreToolUse hook. Research against the installed
`pi` v0.79.3 extension API confirmed PI exposes a genuine pre-disk hook — an extension
registers `pi.on("tool_call", handler)` and returns `ToolCallEventResult { block?, reason? }`
("fired before a tool executes, can block"). This corrects the earlier-documented
assumption that PI's CLI had no pre-disk hook, and closes the last real PI implementation
gap.

The extension `dadaia_workspace/public/pi/extensions/dadaia-sdd-gate.ts` is a thin shim:
for `write`/`edit` it maps the PI tool name to the gate's canonical vocabulary
(`write→Write`, `edit→Edit`), extracts `event.input.path`, and delegates the allow/block
decision to the **same** Python `pre_gate` (root-whitelist → venv-guard → SDD) every other
harness uses — zero gate-logic duplication. It returns `{ block: true }` only on the
explicit `{"decision":"block"}` envelope and **fails open** on any error (the OpenCode
plugin pattern). It runs on PI's Node runtime via `node:child_process.spawnSync`, with venv
resolution POSIX → Windows → bare `python` (no bash dependency).

The two PI layers are kept distinct: **Layer-1 interactive `pi`** gains the post-trust
Ring-1; the **Layer-2 `PI_HEADLESS` worker** (`pi --mode json` headless) keeps Ring-2
(git-diff) + chokepoints. The constitution and memory were updated to state this honestly,
including the caveat that the extension's blocking is **active once the operator grants
`.pi/` trust** (the assets are post-trust executable TypeScript) — live efficacy is
verified on a trusted interactive run, the same upstream-owned trust seam as the
`pi --mode json` live test, not in offline CI.

## Tasks completed

| Task ID | Description | Commit |
|---------|-------------|--------|
| T-21-01 | Author SPEC/PLAN/TASKS | `b7fe1ee` |
| T-21-02 | Constitution §4/§8 PI rows → post-trust Ring-1 (caveat) | `b7fe1ee` |
| T-21-03 | Memory honesty: architecture / multi-platform-parity / lifecycle-foundation / agent-orchestration / sdd-gate-v3 (PI row added in closure) | `b7fe1ee` / `<closure>` |
| T-21-04 | `public/pi/extensions/dadaia-sdd-gate.ts` | `b7fe1ee` |
| T-21-05 | Projection wiring (`_PI_DIRS` += extensions; settings.json; SYSTEM.md) | `b7fe1ee` |
| T-21-06 | Projection + content contract test | `b7fe1ee` |
| T-21-07 | `pre_gate` mapped-payload enforcement test | `b7fe1ee` |
| T-21-08 | preflight + review ladder APPROVED | `<closure>` |
| T-21-09 | CLOSURE + verification recipe + archive + gated push + CI green | `<closure>` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Format + lint + strict-type + full tests | `dadaia ci preflight` | 4/4 PASS (ruff format/check; mypy --strict; pytest) |
| Memory atoms lint | `lint-memory-atoms.py` | 30 OK, 0 WARN, 0 ERROR |
| PI extension projection + privacy | `dadaia public doctor` | exit 0; `[ok] public-privacy`; `[ok] pi:extensions/dadaia-sdd-gate.ts` |
| SDD structural health | `dadaia specs doctor` | exit 0 |
| PI Ring-1 tests (mapping + enforcement + projection/content) | `pytest` | write slips / Write+FROZEN blocked / Write+ADDITIVE allowed; extension projects with invariants + no leak — pass |
| QA gate | qa-engineer APPROVE | honesty PASS, no over-claim; handoff on disk |
| Code review | code-reviewer APPROVE-WITH-NITS | API fidelity / delegation / honesty all PASS; sdd-gate-v3 PI row (MEDIUM) fixed in closure |
| Security verdict (push gate) | security-reviewer APPROVE | 0 findings; post-trust surface clean, no injection, fail-open; keyed to the pushed sha |
| GitHub Actions CI | CI for the closing tip | watched to green |

## Live-efficacy verification recipe (operator, networked + trusted)

Offline CI proves the Python decision + the projected artifact. To verify the `.ts`
actually loads and blocks under PI, run interactively in the workspace:

```bash
cd <workspace-root>            # the dir containing .dadaia/ and the projected .pi/
export ANTHROPIC_API_KEY=…     # PI is Anthropic-backed
pi --approve                   # grant .pi/ trust (loads .pi/extensions/dadaia-sdd-gate.ts)
# or force-load explicitly: pi --extension .pi/extensions/dadaia-sdd-gate.ts
# Then ask pi to edit a FROZEN path, e.g. "edit specs/_archive/<any>/SPEC.md":
#   expect the write to be BLOCKED with "[SDD GATE] … _archive …".
# Ask it to write specs/bugs/<x>.md (ADDITIVE): expect ALLOW.
```

A clean way to confirm load without spending tokens: `pi list` should show the extension
among installed/loaded sources after trust.

## Drifts

### pi-cli-exposes-pre-disk-hook (assumption corrected)

Prior memory/constitution stated PI's CLI exposed no pre-disk hook (Ring-1 deferred). The
installed pi v0.79.3 API (`core/extensions/types.d.ts:648,739,835`) disproves that: the
`tool_call` hook can block. All affected atoms + the constitution were corrected; the
Layer-1/Layer-2 distinction is now explicit (Layer-2 worker remains Ring-2). Also fixed a
pre-existing "WS-PI-3 deferred" staleness (it shipped v0.1.18) and added the missing PI row
to `sdd-gate-v3.md` (code-review MEDIUM). A fresh lint + doctor confirm zero residual drift.

## Memory updates

Atoms updated (all lint-clean): `architecture.md` (Layer-1 parity PI row + two-layer prose),
`product/agents/agent-orchestration.md` (dispatch honesty), `product/platform/
multi-platform-parity.md` (body + summary frontmatter), `product/sdd/lifecycle-foundation.md`
(WS-PI-3/4 no longer deferred; layer distinction), `product/sdd/sdd-gate-v3.md` (PI Layer-1
+ Layer-2 enforcement-matrix rows). `catalog.json` + `index.md` regenerated. `constitution.md`
§4/§8 updated (not memory-class). No atom created or deleted. The auto-memory
`project_pi_fourth_harness` atom records the WS-PI-4 milestone.

## Dispositions / deferred (recorded)

- **Live trusted-run verification** — operator step (recipe above); the upstream trust seam,
  same class as the `pi --mode json` live test.
- **`settings.json` `prompts` scalar vs pi's `prompts?: string[]`** — pre-existing (WS-PI-3),
  out of WS-PI-4 scope; flagged for a future PI-config-fidelity pass.
- **Block-detection substring match** in the `.ts` — intentional parity with the OpenCode
  plugin; safe (pre_gate emits the key only in the block envelope).
- WS-PI-6 (telemetry), RPC/SDK transports, OpenCode live worker — still deferred.

## Notes

No change to the Python gate policy, the lease model, the other harnesses, or any
dependency. The `.ts` reuses the existing Python `pre_gate` verbatim. WS-PI-4 was the last
open PI implementation gap; PI is now at Layer-1 enforcement parity (post-trust) with the
hook-capable harnesses.
