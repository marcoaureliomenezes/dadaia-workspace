# SPEC: v0.1.21 — WS-PI-4: PI Layer-1 Ring-1 SDD-gate extension

**Status:** Aprovado
**Release ID:** v0.1.21
**Owner:** product-engineer
**Created:** 2026-06-25
**Branch:** `feature/pi-operational-v1` (continues the unmerged stack)

## 1. Problem

PI is the fourth Layer-1 entry harness, but until now it had **no pre-disk (Ring-1)
write gate** — its Layer-1 posture was "advisory + git-chokepoint-protected" (constitution
§8), unlike Claude Code / Codex (interactive) which run the merged Python `pre_gate`
PreToolUse hook and can block a write before it touches disk. WS-PI-4 (deferred since the
pi-fourth-harness work) closes that gap.

Research against the **installed `pi` v0.79.3** extension API (`@earendil-works/
pi-coding-agent/dist/core/extensions/types.d.ts`) confirms PI exposes a genuine pre-disk
hook: an extension registers `pi.on("tool_call", handler)` and the handler returns
`ToolCallEventResult { block?: boolean; reason?: string }` — "Fired before a tool
executes. Can block." This is the exact analog of Claude's PreToolUse deny. (This corrects
the earlier-documented assumption that PI's CLI exposed no pre-disk hook.)

## 2. Scope

### A. The extension (NEW projected executable asset)
- `dadaia_workspace/public/pi/extensions/dadaia-sdd-gate.ts` — an `ExtensionFactory`
  (`(pi) => pi.on("tool_call", handler)`) that, for the `write` and `edit` built-in tools,
  extracts `event.input.path`, maps the PI tool name to the gate's canonical vocabulary
  (`write→Write`, `edit→Edit`), and delegates the allow/block decision to the **same**
  Python governance hook every other harness uses — `python -m
  dadaia_workspace.hooks.pre_gate` (root-whitelist → venv-guard → SDD) — over the same
  JSON stdin contract (`{tool_name, tool_input:{file_path}}`). It returns
  `{ block: true, reason }` only on the explicit `{"decision":"block"}` envelope; any
  internal error (no interpreter, spawn failure, parse miss) **fails open** (allow). The
  Python venv binary is resolved with no bash dependency (POSIX venv → Windows venv →
  bare `python`), mirroring `public/plugins/sdd-gate.ts`. Runs on Node (PI's runtime) via
  `node:child_process.spawnSync` — not Bun. NO gate-logic duplication: policy lives only
  in Python.

### B. Projection wiring
- `public_assets_common.py` `_PI_DIRS` += `"extensions"` (the `--only` filter + iteration).
- `public/pi/settings.json` += `"extensions": [".pi/extensions/dadaia-sdd-gate.ts"]` so PI
  loads the extension; the explicit `pi --extension .pi/extensions/dadaia-sdd-gate.ts`
  invocation is the guaranteed fallback (pi `--help`: "explicit -e paths still work").
- The `copy_tree`-based `_install_pi` projects the new file automatically; `dadaia public
  doctor` source↔staging↔projection covers it with no per-file change.

### C. Honesty updates (constitution + memory)
- Constitution §4 / §8 PI rows: PI now ships a Layer-1 Ring-1 SDD-gate extension that
  blocks write/edit pre-disk via the Python `pre_gate`. State the one honest caveat: the
  extension is **post-trust executable** — its blocking is active once the operator grants
  `.pi/` trust and pi's `tool_call` hook fires; live efficacy is verified on a trusted
  interactive run (the same upstream-owned trust seam as the `pi --mode json` live test),
  not in offline CI.
- Memory atoms updated to match: `architecture.md` (Layer-1 parity table PI row),
  `multi-platform-parity.md`, `lifecycle-foundation.md` (WS-PI-4 no longer deferred),
  `product/sdd/sdd-gate-v3.md` if it enumerates the PreToolUse-capable harnesses.

### D. Tests
- A projection + content contract test (Python, integration) asserting the projected
  `.pi/extensions/dadaia-sdd-gate.ts` exists, `settings.json` lists it, and the extension
  body carries its invariants: the `tool_call` registration, the `write→Write`/`edit→Edit`
  mapping, the `pre_gate` invocation, the `"decision":"block"` check, fail-open, and the
  venv-resolution order — with NO operator-local path or secret.
- A Python gate test proving the canonical mapped payload is enforced: a PI-style write to
  a FROZEN/PROTECTED path (sent as `tool_name:"Write"`) is BLOCKed by `pre_gate`, and an
  ADDITIVE path is allowed (closes the loop that PI's mapped names hit the real gate).

Out of scope (recorded): the live interactive trusted-run verification (operator,
networked — provide a recipe); a TS unit-test harness (parity with the un-unit-tested
OpenCode `.ts` plugin — validated by the Python content/projection test); gating PI `bash`
(file-write Ring-1 is the WS-PI-4 boundary; Bash stays chokepoint-governed as designed).

## 3. Acceptance criteria

1. `dadaia public doctor` exit 0, `[ok] public-privacy`, `[ok] pi:extensions/dadaia-sdd-gate.ts`.
2. `dadaia ci preflight` green (the `.ts` is a projected asset; Python suite + new tests pass).
3. `dadaia specs doctor` exit 0.
4. The extension delegates to `pre_gate` (no duplicated policy) and fails open.
5. Constitution + memory honestly describe PI's new Layer-1 Ring-1 posture **with** the
   post-trust caveat; zero new drift (drift re-check).
6. Full review ladder (QA + code-review + security) APPROVED; gated push; CI green.

## 4. Non-goals

No change to the Python gate policy, the lease model, or the other harnesses. No new
dependency. The `.ts` reuses the existing Python `pre_gate` verbatim.
