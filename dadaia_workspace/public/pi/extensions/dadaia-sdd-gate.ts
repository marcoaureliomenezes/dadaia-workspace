// dadaia-sdd-gate.ts — PI (pi-coding-agent) Layer-1 SDD gate extension (WS-PI-4).
//
// Gives PI a real pre-disk (Ring-1) write gate, the analog of the Claude Code / Codex
// PreToolUse hook. PI exposes a genuine "fired before a tool executes, can block" hook:
// an extension registers `pi.on("tool_call", handler)` and the handler returns
// `{ block: true, reason }` to deny a tool call before it touches disk
// (verified against pi v0.79.3 `core/extensions/types.d.ts`).
//
// This is a THIN shim: it delegates the allow/block
// decision to the single cross-runtime source of truth — the Python governance hook
// `python -m dadaia_workspace.hooks.pre_gate` (root-whitelist → venv-guard → SDD gate,
// first-block-wins). Policy is NEVER re-derived in TypeScript. The Python hook delegates to
// `gate_policy.evaluate()` / `classify_path()`.
//
// PI's built-in write tools are `write` ({path, content}) and `edit` ({path, edits[]}).
// Their lowercase names are not in the Python gate's WRITE_TOOLS vocabulary, so the shim
// maps `write→Write` and `edit→Edit` — the canonical names — so the path classifier treats
// a PI write exactly like a Claude write. `event.input.path` is the target file.
//
// Trust boundary: `.pi/**` is post-trust executable TypeScript — pi loads and runs this
// only after the operator grants project trust. It is lib-originated (manifest-tracked),
// carries NO secrets and NO operator-local paths, and must never be hand-edited in place
// (edit the source under `dadaia_workspace/public/pi/extensions/`, then re-project).
//
// Fail-open: any internal error (missing interpreter, spawn failure, parse error) ALLOWS
// the tool — never block a legitimate edit by crashing. Only the explicit
// `{"decision":"block"}` envelope from the Python hook blocks. This matches the gate's own
// fail-open contract.
//
// Runs on PI's Node runtime via `node:child_process.spawnSync` (not Bun).
//
// Entry-harness signal (v0.1.64 FR4; ARCH64-2 security posture). PI exposes no native
// session env var, so at factory load this extension pins the dadaia-owned entry signal
// `DADAIA_ENTRY_HARNESS = "pi"` — ONLY when unset (an operator pin always wins). PI tool
// subprocesses (bash -> `dadaia lifecycle ...`) inherit it, so the lifecycle CLI's
// `--harness auto` default resolves `pi`. Post-trust semantics: pre-trust (extension not
// loaded) there is NO signal and the auto-default stays `fake`. The pin carries no
// secrets and no operator-local paths (public-privacy law). ARCH64-2 posture: the pin is
// SESSION-WIDE and CREDIT-AFFECTING — every child process of the PI session inherits it,
// and an auto-defaulted `pi` worker spends real credits. The guardrails are structural:
// (1) set-only-when-unset (an operator pin always wins); (2) the FR3 loud echo guards
// EVERY real-worker auto-default (never silent); (3) the signal is NEVER derived from
// telemetry (no session-file/mtime heuristics — the pin is this extension's explicit,
// post-trust act).
//
// PI presence parity (v0.1.76 T-4, FR5, NO-LOCKS DOCTRINE). PI exposes NO native
// per-session identifier anywhere in its extension surface (verified against pi v0.79.3
// `core/extensions/types.d.ts`: neither `ExtensionContext` nor any event carries a
// session id) — every PreToolUse invocation from this shim used to omit `session_id`
// from the stdin payload entirely, so the Python gate's `resolve_session_id` fell
// through to its `default="anon-session"` param on every single PI write. FR5 kills the
// "PI anon-session dual-writer" bug at the root: this module mints ONE stable,
// process-lifetime session id at factory load (`crypto.randomUUID()`, prefixed
// `pi-session-`), sends it as the payload `session_id` field on every `tool_call`
// (pre-tool) AND — this is the new wiring — on every `tool_result` (post-tool, PI's
// genuine after-a-tool-executes event, `pi.on("tool_result", ...)`), invoking
// `python -m dadaia_workspace.hooks.sdd_post_gate` exactly the way Claude/Codex's
// PostToolUse hook renews presence after every tool call (`infrastructure/
// runtime_config.py`'s `PostToolUse` wiring, match-all). `hooks/sdd_gate.py`'s
// `anon-session` guard (FR5, `_ANON_SESSION_ID`) still applies as defense-in-depth for
// any harness that genuinely cannot resolve an id — with this fix PI is no longer one
// of them. The long-lived pid sent alongside is `process.pid`: PI's own process, which
// outlives every spawned `python -m ...` child for the whole session (mirrors NF-1 in
// the Python gate: never record an ephemeral child's own pid).

import { randomUUID } from "node:crypto";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

// PI built-in file-write tools → the Python gate's canonical WRITE_TOOLS vocabulary.
// Mapping (not passthrough) keeps the Python vocabulary stable: the classifier sees
// "Write"/"Edit" and applies the identical path-class × presence × phase × mode policy.
const TOOL_NAME_MAP: Record<string, string> = {
  write: "Write",
  edit: "Edit",
};

// Minimal structural types for the fields this gate reads (verified against pi v0.79.3
// `core/extensions/types.d.ts`). Kept local so the extension has no hard import-resolution
// dependency on the pi package at load time.
interface ToolCallEvent {
  toolName: string;
  input: Record<string, unknown>;
}
interface ToolResultEvent {
  toolName: string;
  input: Record<string, unknown>;
}
interface ExtensionContext {
  cwd: string;
}
interface ToolCallEventResult {
  block?: boolean;
  reason?: string;
}
interface ExtensionAPI {
  on(
    event: "tool_call",
    handler: (
      event: ToolCallEvent,
      ctx: ExtensionContext,
    ) => Promise<ToolCallEventResult | void> | ToolCallEventResult | void,
  ): void;
  // Fired AFTER a tool executes (pi v0.79.3 `core/extensions/types.d.ts`,
  // `ToolResultEvent` / `ExtensionAPI.on("tool_result", ...)`) — PI's genuine
  // post-tool-execution event, the analog of Claude/Codex's PostToolUse hook. FR5 wires
  // this to renew this session's advisory presence record after every tool call.
  on(
    event: "tool_result",
    handler: (event: ToolResultEvent, ctx: ExtensionContext) => Promise<void> | void,
  ): void;
}

// Walk up from `start` to the workspace root (the dir containing `.dadaia/`).
function findWorkspaceRoot(start: string): string | null {
  let dir = start;
  for (;;) {
    if (existsSync(join(dir, ".dadaia"))) return dir;
    const parent = join(dir, "..");
    if (parent === dir) return null;
    dir = parent;
  }
}

// Resolve the workspace venv Python with NO bash dependency. Priority: POSIX venv →
// Windows venv → bare `python`. Mirrors `public/plugins/sdd-gate.ts` and the Python
// `_common.default_python_bin` / `runtime_config._python_bin`.
function resolvePythonBin(ws: string): string {
  const posix = join(ws, ".dadaia", ".venv", "bin", "python");
  if (existsSync(posix)) return posix;
  const windows = join(ws, ".dadaia", ".venv", "Scripts", "python.exe");
  if (existsSync(windows)) return windows;
  return "python";
}

const factory = (pi: ExtensionAPI): void => {
  // Entry-harness pin (v0.1.64 FR4) — guarded: set-only-when-unset, so an operator's
  // explicit DADAIA_ENTRY_HARNESS always wins. See the ARCH64-2 posture in the header.
  if (!process.env.DADAIA_ENTRY_HARNESS) {
    process.env.DADAIA_ENTRY_HARNESS = "pi";
  }

  // FR5: one stable session id for this PI process's whole lifetime — minted ONCE at
  // factory load, never regenerated per tool call. Sanitized shape matches the Python
  // gate's session-id allowlist (`[A-Za-z0-9_-]+`, see `core.session_env.
  // sanitize_session_id`): `randomUUID()` output is already hyphen/hex-only.
  const sessionId = `pi-session-${randomUUID()}`;

  pi.on("tool_call", (event, ctx): ToolCallEventResult | void => {
    try {
      const mapped = TOOL_NAME_MAP[event.toolName];
      if (!mapped) return; // not a file-write tool → out of scope (Bash etc. → chokepoints)
      const filePath = typeof event.input?.path === "string" ? event.input.path : "";
      if (!filePath) return;

      const ws = findWorkspaceRoot(ctx.cwd || process.cwd());
      if (!ws) return; // not inside a dadaia workspace → nothing to gate

      const python = resolvePythonBin(ws);
      // The same JSON stdin contract the Python gate parses (tool_name + tool_input.file_path
      // + session_id — FR5: the stable per-process id minted above, never omitted).
      const payload = JSON.stringify({
        tool_name: mapped,
        tool_input: { file_path: filePath },
        session_id: sessionId,
      });
      // Invoke the merged Python gate directly (no bash). Run from the workspace root so
      // the hook's workspace-resolver and relative-path handling behave identically to
      // the Claude/Codex PreToolUse hook.
      const result = spawnSync(python, ["-m", "dadaia_workspace.hooks.pre_gate"], {
        cwd: ws,
        input: payload,
        encoding: "utf-8",
      });
      const stdout = result.stdout ?? "";
      if (stdout.includes('"decision":"block"') || stdout.includes('"decision": "block"')) {
        let reason = "SDD gate blocked this write.";
        try {
          const parsed = JSON.parse(stdout.trim());
          if (parsed?.reason) reason = String(parsed.reason);
        } catch {
          // keep default reason
        }
        return { block: true, reason: `[SDD GATE] ${reason}` };
      }
      return; // allow
    } catch {
      return; // fail-open: never block a legitimate edit by crashing
    }
  });

  // FR5 (v0.1.76 T-4): post-tool presence renewal — the PI analog of Claude/Codex's
  // match-all PostToolUse → sdd_post_gate wiring. Fires after EVERY tool (not just
  // writes — mirrors the Python-side hook's own unconditional renewal), so a long
  // read/grep/bash-only stretch still keeps this session's presence record fresh.
  // Best-effort / fail-open by construction: `sdd_post_gate` itself never blocks (exits
  // 0 unconditionally) and this handler never returns a result the runner could act on.
  pi.on("tool_result", (_event, ctx): void => {
    try {
      const ws = findWorkspaceRoot(ctx.cwd || process.cwd());
      if (!ws) return; // not inside a dadaia workspace → nothing to renew

      const python = resolvePythonBin(ws);
      const payload = JSON.stringify({ session_id: sessionId });
      spawnSync(python, ["-m", "dadaia_workspace.hooks.sdd_post_gate"], {
        cwd: ws,
        input: payload,
        encoding: "utf-8",
      });
    } catch {
      // fail-open: a renewal failure must never surface to the tool result or the user.
    }
  });
};

export default factory;
