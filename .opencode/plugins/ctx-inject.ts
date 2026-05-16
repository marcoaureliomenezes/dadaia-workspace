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
  "chat.message": async (message: { role: string; content: string | unknown[] }) => {
    if (typeof message.content !== "string") return { message }
    try {
      const ws = findWorkspaceRoot(process.cwd())
      if (!ws) return { message }
      const script = join(ws, ".dadaia", "scripts", "ctx-inject.sh")
      if (!existsSync(script)) return { message }
      const result = await $`bash ${script}`.quiet()
      const injection = result.stdout.toString().trim()
      if (!injection) return { message }
      return {
        message: {
          ...message,
          content: `${message.content}\n\n${injection}`,
        },
      }
    } catch {
      return { message }
    }
  },
})
