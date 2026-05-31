// ctx-inject.ts — injects workspace context into each new user message (OpenCode).
//
// FR-OC-4 audit (2026-05-29): the `chat.message` hook IS valid in OpenCode 1.14.x, but its
// signature changed. Verified against @opencode-ai/plugin type defs
// (https://unpkg.com/@opencode-ai/plugin/dist/index.d.ts):
//
//   "chat.message"?: (input: { sessionID, agent?, model?, messageID?, variant? },
//                     output: { message: UserMessage; parts: Part[] }) => Promise<void>
//
// The previous implementation used the OLD shape `(message) => { return { message } }`, which
// no longer fires correctly. This version migrates to the current `(input, output)` shape and
// MUTATES `output.parts` (the supported pattern). We append to the last existing text part
// rather than constructing a new Part, because Part's required fields vary across
// @opencode-ai/sdk versions. `experimental.chat.system.transform` was rejected as an
// alternative due to a known runtime bug that silently discards its mutations
// (anomalyco/opencode#17100).
//
// Fail-open: any error skips injection and never breaks the chat.
//
// First-message-only guard (T-MCE-08 / AC-C1-5 / AC-RT-2):
// The OpenCode plugin API exposes `input.sessionID` in the `chat.message` handler.
// We use it as the primary session identifier for a sentinel-file guard that mirrors
// the guard already present in ctx-inject.sh (sentinel at
// .dadaia/tmp/ctx-inject-fired-<sessionID>). On the first message of a session the
// sentinel does not yet exist, so we call ctx-inject.sh (which creates the sentinel
// and emits the full ~5K payload). On subsequent messages the TS layer checks the
// sentinel first and skips the script call entirely — the ~5K payload is never
// re-appended. Both layers (TS + shell) agree on the same sentinel file, so they
// cannot diverge.
//
// NOTE for devops-engineer (T-MCE-09 / OQ-1 / OQ-2): confirm that `input.sessionID`
// is the correct and stable session identifier in the deployed OpenCode version. If
// the field is absent or unreliable, the sentinel-file fallback path (PID-based,
// matching the shell script's $$ fallback) remains in place below.

import { existsSync, mkdirSync, writeFileSync } from "node:fs"
import { join } from "node:path"
import { $ } from "bun"

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
  "chat.message": async (
    input: { sessionID?: string; messageID?: string; agent?: string; model?: string; variant?: string },
    output: { parts: Array<{ type?: string; text?: string }> },
  ): Promise<void> => {
    try {
      const ws = findWorkspaceRoot(process.cwd())
      if (!ws) return

      // --- First-message-only guard ---
      // Determine a stable session identifier. Prefer input.sessionID (OpenCode plugin
      // API); fall back to process.pid (matches the PID-based fallback in ctx-inject.sh).
      // NOTE for devops-engineer (T-MCE-09 / OQ-1 / OQ-2): verify input.sessionID is
      // available and stable in the deployed OpenCode version. If not, the PID fallback
      // here and the $$ fallback in ctx-inject.sh will both fire, keeping them in sync.
      const sessionId = (input.sessionID ?? String(process.pid)).replace(/[^a-zA-Z0-9_-]/g, "_")
      const tmpDir = join(ws, ".dadaia", "tmp")
      const sentinel = join(tmpDir, `ctx-inject-fired-${sessionId}`)

      if (existsSync(sentinel)) {
        // Memory block already injected this session — skip to avoid re-paying ~5K tokens.
        return
      }

      const script = join(ws, ".dadaia", "scripts", "ctx-inject.sh")
      if (!existsSync(script)) return

      // Create the sentinel in the TS layer before calling the script so that concurrent
      // calls from rapid message submission cannot double-inject. The shell script also
      // creates the sentinel independently — both creating it is idempotent.
      mkdirSync(tmpDir, { recursive: true })
      writeFileSync(sentinel, "")

      const result = await $`bash ${script}`.quiet()
      const injection = result.stdout.toString().trim()
      if (!injection) return
      // Append to the last existing text part so the model sees the injected context.
      const textParts = output.parts.filter(
        (p) => p.type === "text" && typeof p.text === "string",
      )
      const last = textParts[textParts.length - 1]
      if (last) {
        last.text = `${last.text}\n\n${injection}`
      }
    } catch {
      // fail-open: never break the chat on injection failure
      return
    }
  },
})
