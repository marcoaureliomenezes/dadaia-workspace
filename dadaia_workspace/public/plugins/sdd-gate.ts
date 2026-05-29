// sdd-gate.ts — OpenCode SDD gate plugin (FR-OC-3 / ADR-OC-2).
//
// Mirrors the Claude Code PreToolUse hook: intercepts write-like tool calls and delegates
// the allow/block decision to .dadaia/scripts/sdd-spec-gate.sh — the single source of truth
// for SDD enforcement across runtimes (Claude Code, Codex, OpenCode).
//
// Hook event: `tool.execute.before` — verified 2026-05-29 against the @opencode-ai/plugin
// type defs (Hooks["tool.execute.before"]: (input, output: { args }) => Promise<void>) and
// https://opencode.ai/docs/plugins/ (OpenCode 1.14.x). Throwing inside the hook aborts the
// tool call, which is how a block is enforced.
//
// Fail-open: any internal error (missing script, spawn failure, parse error) ALLOWS the tool
// — never block a legitimate edit by crashing. This matches the bash gate's own fail-open
// contract. The only thrown error is the deliberate SDD block.

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
      const script = join(ws, ".dadaia", "scripts", "sdd-spec-gate.sh")
      if (!existsSync(script)) return
      // Same JSON stdin contract the bash gate parses: tool_name + tool_input.file_path.
      const payload = JSON.stringify({
        tool_name: input.tool,
        tool_input: { file_path: filePath },
      })
      const result = await $`echo ${payload} | bash ${script}`.quiet()
      const stdout = result.stdout.toString()
      if (stdout.includes('"decision":"block"')) {
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
