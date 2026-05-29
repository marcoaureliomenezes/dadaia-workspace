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

import { existsSync } from "node:fs"
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
    _input: unknown,
    output: { parts: Array<{ type?: string; text?: string }> },
  ): Promise<void> => {
    try {
      const ws = findWorkspaceRoot(process.cwd())
      if (!ws) return
      const script = join(ws, ".dadaia", "scripts", "ctx-inject.sh")
      if (!existsSync(script)) return
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
