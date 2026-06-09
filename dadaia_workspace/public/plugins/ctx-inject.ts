// ctx-inject.ts — injects workspace context into each new user message (OpenCode).
//
// ADR-7 (T-018-19): this plugin no longer shells out to `bash ctx-inject.sh`. It invokes
// the Python governance hook `python -m dadaia_workspace.hooks.ctx_inject` directly, with
// the venv binary resolved with NO bash dependency:
//   .dadaia/.venv/bin/python  →  .dadaia/.venv/Scripts/python.exe  →  bare `python`
//
// Output contract (DADAIA_HOOK_OUTPUT / DADAIA_HOOK_EVENT):
//   The Python hook emits the `hookSpecificOutput.additionalContext` envelope ONLY when
//   DADAIA_HOOK_OUTPUT is in {codex-json, json}; otherwise it writes the RAW payload to
//   stdout. OpenCode's `chat.message` hook injects context by MUTATING `output.parts`
//   (it cannot return a hookSpecificOutput envelope the way Claude Code / Codex stdout
//   hooks do), so this plugin uses the RAW output path: it does NOT set DADAIA_HOOK_OUTPUT
//   and appends the raw payload to the last text part. The SessionStart/UserPromptSubmit
//   split that Claude Code / Codex express via two hook registrations collapses to the
//   single OpenCode `chat.message` event; once-per-session idempotence is enforced by the
//   shared sentinel (see below), exactly as the Codex SessionStart-once contract intends.
//
//   DADAIA_HOOK_EVENT is passed through Bun's cross-platform `.env({...})` (Bun spawns the
//   subprocess directly — no bash, works on Windows). It only labels the envelope, which
//   the raw OpenCode path does not emit, so it is informational here. Because OpenCode
//   never depends on the envelope, the Bun-runtime Windows subprocess env-passing sub-part
//   flagged as potentially-deferrable in ADR-7 is NOT on the OpenCode critical path: the
//   raw-stdout read path needs no env propagation to function, so OpenCode-on-Windows hook
//   governance is NOT ungoverned for this plugin. The non-deferrable part (bash-free venv
//   Python resolution) ships here.
//
// Fail-open: any error skips injection and never breaks the chat.
//
// First-message-only guard (mirrors ctx-inject.sh and the Python hook sentinel):
// sentinel at .dadaia/tmp/ctx-inject-fired-<sessionID>. The Python hook ALSO writes this
// byte-identical sentinel; both layers agree on the same path and cannot diverge. On the
// first message the sentinel does not exist → invoke the hook (emits the full payload and
// creates the sentinel). On later messages the TS layer short-circuits on the sentinel and
// never re-invokes the hook — the payload is never re-appended.
//
// NOTE for devops-engineer (OQ-1 / OQ-2): confirm `input.sessionID` is the correct, stable
// session identifier in the deployed OpenCode version. If absent/unreliable, the PID-based
// fallback below (matching the shell script's $$ fallback) keeps both layers in sync.

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

// Resolve the workspace venv Python binary with NO bash dependency (ADR-7, non-deferrable).
// Priority: POSIX venv → Windows venv → bare `python`. Mirrors `runtime_config._python_bin`.
function resolvePythonBin(ws: string): string {
  const posix = join(ws, ".dadaia", ".venv", "bin", "python")
  if (existsSync(posix)) return posix
  const windows = join(ws, ".dadaia", ".venv", "Scripts", "python.exe")
  if (existsSync(windows)) return windows
  return "python"
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
      // Prefer input.sessionID (OpenCode plugin API); fall back to process.pid (matches the
      // PID fallback in ctx-inject.sh / the Python hook's session-id resolution).
      const sessionId = (input.sessionID ?? String(process.pid)).replace(/[^a-zA-Z0-9_-]/g, "_")
      const tmpDir = join(ws, ".dadaia", "tmp")
      const sentinel = join(tmpDir, `ctx-inject-fired-${sessionId}`)

      if (existsSync(sentinel)) {
        // Memory block already injected this session — skip to avoid re-paying ~5K tokens.
        return
      }

      const python = resolvePythonBin(ws)

      // Create the sentinel in the TS layer before invoking the hook so concurrent calls
      // from rapid message submission cannot double-inject. The Python hook also creates
      // the same byte-identical sentinel independently — both creating it is idempotent.
      mkdirSync(tmpDir, { recursive: true })
      writeFileSync(sentinel, "")

      // Invoke the Python hook directly (no bash), from the workspace root. RAW output path:
      // DADAIA_HOOK_OUTPUT is intentionally NOT set so the hook writes the raw payload to
      // stdout (OpenCode mutates output.parts; it does not consume the JSON envelope).
      // DADAIA_HOOK_EVENT is passed via Bun's cross-platform .env() to preserve the env
      // contract; the session id is forwarded so the Python hook's sentinel matches ours.
      const result = await $`${python} -m dadaia_workspace.hooks.ctx_inject < ${new Response("")}`
        .cwd(ws)
        .env({
          ...process.env,
          DADAIA_HOOK_EVENT: "UserPromptSubmit",
          DADAIA_SESSION_ID: sessionId,
        })
        .quiet()
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
