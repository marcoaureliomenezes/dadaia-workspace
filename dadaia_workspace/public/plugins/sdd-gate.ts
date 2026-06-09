// sdd-gate.ts — OpenCode SDD gate plugin (FR-OC-3 / ADR-OC-2; ADR-7 Python migration).
//
// Mirrors the Claude Code / Codex PreToolUse hook: intercepts write-like tool calls and
// delegates the allow/block decision to the Python governance hook
// `python -m dadaia_workspace.hooks.sdd_gate` — the single cross-runtime source of truth
// for SDD enforcement (Claude Code, Codex, OpenCode). The Python hook itself delegates to
// `gate_policy.evaluate()` / `gate_policy.classify_path()`, so policy is never re-derived.
//
// ADR-7 (T-018-19): this plugin no longer shells out to `bash <script>.sh`. The Python
// venv binary is resolved with NO bash dependency:
//   .dadaia/.venv/bin/python  →  .dadaia/.venv/Scripts/python.exe  →  bare `python`
// and the hook is invoked directly as `<python> -m dadaia_workspace.hooks.sdd_gate`.
//
// Hook event: `tool.execute.before` — (input, output: { args }) => Promise<void>.
// Throwing inside the hook aborts the tool call, which is how a block is enforced.
//
// Fail-open: any internal error (missing interpreter, spawn failure, parse error) ALLOWS
// the tool — never block a legitimate edit by crashing. This matches the Python hook's own
// fail-open contract (only an explicit `{"decision":"block"}` envelope blocks). The only
// thrown error is the deliberate SDD block.

import { existsSync } from "node:fs"
import { join } from "node:path"
import { $ } from "bun"

// OpenCode built-in write/exec tool names plus defensive aliases for naming variations
// across runtime versions (write_file/edit_file/apply_patch).
const WRITE_TOOLS = new Set([
  "write",
  "edit",
  "patch",
  "write_file",
  "edit_file",
  "apply_patch",
])

function findWorkspaceRoot(start: string): string | null {
  let dir = start
  for (;;) {
    if (existsSync(join(dir, ".dadaia"))) return dir
    const parent = join(dir, "..")
    if (parent === dir) return null
    dir = parent
  }
}

// Resolve the workspace venv Python binary with NO bash dependency (ADR-7, non-deferrable).
// Priority: POSIX venv → Windows venv → bare `python` (relies on PATH). Mirrors
// `runtime_config._python_bin` / `_common.default_python_bin`.
function resolvePythonBin(ws: string): string {
  const posix = join(ws, ".dadaia", ".venv", "bin", "python")
  if (existsSync(posix)) return posix
  const windows = join(ws, ".dadaia", ".venv", "Scripts", "python.exe")
  if (existsSync(windows)) return windows
  return "python"
}

export default async () => ({
  "tool.execute.before": async (
    input: { tool: string },
    output: { args: Record<string, unknown> },
  ): Promise<void> => {
    try {
      if (!WRITE_TOOLS.has(input.tool)) return
      const args = output?.args ?? {}
      const filePath =
        (args.filePath as string) ||
        (args.path as string) ||
        (args.file_path as string) ||
        ""
      if (!filePath) return
      const ws = findWorkspaceRoot(process.cwd())
      if (!ws) return
      const python = resolvePythonBin(ws)
      // Same JSON stdin contract the Python gate parses: tool_name + tool_input.file_path.
      const payload = JSON.stringify({
        tool_name: input.tool,
        tool_input: { file_path: filePath },
      })
      // Invoke the Python hook directly (no bash). The payload is fed on stdin via Bun's
      // shell stdin redirection from a string. Run from the workspace root so the hook's
      // workspace-resolver and relative-path handling behave identically to Claude/Codex.
      const result = await $`${python} -m dadaia_workspace.hooks.sdd_gate < ${new Response(payload)}`
        .cwd(ws)
        .quiet()
      const stdout = result.stdout.toString()
      if (stdout.includes('"decision":"block"') || stdout.includes('"decision": "block"')) {
        let reason = "SDD gate blocked this write."
        try {
          const parsed = JSON.parse(stdout.trim())
          if (parsed?.reason) reason = parsed.reason as string
        } catch {
          // keep default reason
        }
        throw new Error(`[SDD GATE] ${reason}`)
      }
    } catch (err) {
      // Re-throw the deliberate block; swallow everything else (fail-open).
      if (err instanceof Error && err.message.startsWith("[SDD GATE]")) throw err
      return
    }
  },
})
