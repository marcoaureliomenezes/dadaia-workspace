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

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

// PI built-in file-write tools → the Python gate's canonical WRITE_TOOLS vocabulary.
// Mapping (not passthrough) keeps the Python vocabulary stable: the classifier sees
// "Write"/"Edit" and applies the identical path-class × lease × phase × mode policy.
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
  pi.on("tool_call", (event, ctx): ToolCallEventResult | void => {
    try {
      const mapped = TOOL_NAME_MAP[event.toolName];
      if (!mapped) return; // not a file-write tool → out of scope (Bash etc. → chokepoints)
      const filePath = typeof event.input?.path === "string" ? event.input.path : "";
      if (!filePath) return;

      const ws = findWorkspaceRoot(ctx.cwd || process.cwd());
      if (!ws) return; // not inside a dadaia workspace → nothing to gate

      const python = resolvePythonBin(ws);
      // The same JSON stdin contract the Python gate parses (tool_name + tool_input.file_path).
      const payload = JSON.stringify({
        tool_name: mapped,
        tool_input: { file_path: filePath },
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
};

export default factory;
