# Workspace Sanitization

Strict control over what may exist in the workspace **root** and inside **`.dadaia/`**, enforced
deterministically (hooks + `dadaia doctor` + `AGENTS.md`) for prevention, and by scheduled
routines for correction. No crap, no slop, no agent-generated junk polluting the workspace.

Status: DELIVERED — v0.1.15 adds lifecycle-owned slop policy, hygiene status/cleanup, snapshots, and high-volume performance evidence on top of the earlier v0.1.6/v0.2.1 root-control work; remaining residuals tracked in specs/backlog/candidates.md.

Newest first.

---

## The Law — root whitelist

The workspace **root** may contain **only**:

- Directories: `.agents/`, `.claude/`, `.codex/`, `.dadaia/`, `.opencode/`, `repos/`
- File: `AGENTS.md`

**Single exception:** files or directories created by the human operator are always allowed and
**must never be auto-deleted** (e.g. `prompt.md`, `sessions-tab-1280.png`). Everything else at root
is forbidden. If a legitimate process regenerates an artifact, it must be redirected into a
canonical `.dadaia/<subdir>` — never left loose at root.

### Origin investigation (drives delete-vs-relocate)

Every currently-polluting artifact, why it exists, whether it regenerates, and the decision:

| Artifact | Origin | Regenerated? | Decision |
|---|---|---|---|
| `AGENTS.md` | `dadaia public install` from `public/data/AGENTS.md` | yes | **Keep** (whitelisted) |
| `.mcp.json` | Claude/MCP config read at project root; points to `.dadaia/.venv/bin/uvx` | static | **Investigate relocation** into `.dadaia/mcps/`; if tool hard-requires root, document as explicit exception |
| `opencode.json` | opencode config read at root; lists `AGENTS.md` + `CLAUDE.md` + per-repo AGENTS | static | **Investigate relocation**; opencode reads root → exception or relocate per opencode config support |
| `CLAUDE.md` | stub that points to `AGENTS.md`; referenced by `opencode.json` instructions | maybe | **Fold into AGENTS.md / remove**; first drop the `opencode.json` reference |
| `scripts/install-ccusage-alias.sh` | operator utility script | static | **Relocate** -> `.dadaia/scripts/` |
| `.playwright-mcp/` | Playwright MCP server default output dir | yes per run | **Redirect** MCP output -> `.dadaia/mcps/playwright/`; delete stray |
| `.ruff_cache/` | ruff lint cache | yes when ruff runs at root | **Redirect/disable** (`--no-cache` or `cache-dir` under `.dadaia/`); delete |
| `.pytest_cache/` | pytest cache | yes when pytest runs at root | **Redirect/disable** (`-p no:cacheprovider` / `cache_dir`); delete |
| `.coverage` | coverage.py data file | yes when coverage runs at root | **Redirect** (`COVERAGE_FILE` under `.dadaia/`); delete |
| `.gitignore` | git ignore at root | static (operator) | **Operator-owned** — keep; review entries (open question) |

---

## SANITIZE-01 — Strict root whitelist + deterministic hook (HIGH)

**Reported:** 2026-06-04 (operator: "THEY COULD NEVER BE CREATED... IN THE ROOT FOLDER CAN ONLY HAVE
THE FOLLOWING FOLDERS", "we must behave explicitly about that in the AGENTS.md", "enforce even with
hooks in order to this to be deterministic").

**Surface:** Workspace root. Agents repeatedly create non-whitelisted files/dirs at root.

### Symptoms
- Root is polluted with `.playwright-mcp/`, `.ruff_cache/`, `.pytest_cache/`, `.coverage`,
  `scripts/`, `CLAUDE.md`, and tool configs with no canonical home.
- The current `public/rules/tmp-file-guardrail.md` root whitelist **wrongly permits**
  `CLAUDE.md`, `opencode.json`, `.mcp.json`, and `scripts/` — exactly the artifacts now declared
  forbidden. The rule and the law disagree.

### Root cause
- No deterministic gate. The only guardrail is a soft, advisory rule with an over-permissive
  whitelist; agents ignore or contradict it.
- No origin tagging, so the system can't distinguish operator-created files (allowed) from
  agent-generated junk (forbidden).

### Suggested fix direction
- Codify the law (six dirs + `AGENTS.md` + operator exception) as the single source of truth.
- **Tighten / override `tmp-file-guardrail.md`** so its root whitelist matches the law exactly.
- Add a **pre-write / post-tool hook** that blocks creation of any non-whitelisted root entry and
  surfaces a deterministic violation report.
- **Origin tagging:** maintain an operator-allowlist (or detect human authorship) so files like
  `prompt.md` / `sessions-tab-1280.png` are never blocked or deleted.

---

## SANITIZE-02 — Relocate / delete current root crap (HIGH)

**Reported:** 2026-06-04 (operator: "you have to understand why they were created there, what you
should do to delete them... If they are even needed... they must live on .dadaia/{something}").

**Surface:** Workspace root cleanup.

### Symptoms
- Stray caches and outputs at root: `.playwright-mcp/`, `.ruff_cache/`, `.pytest_cache/`,
  `.coverage`. Loose `scripts/`. Stub `CLAUDE.md`. Tool configs with no canonical placement.

### Root cause
- Tools run from root with default cache/output locations; nobody redirects them into `.dadaia/`.

### Suggested fix direction
- Execute the **origin table** above:
  - Delete regenerated caches after redirecting each tool (ruff `cache-dir`, pytest `cache_dir` /
    `-p no:cacheprovider`, `COVERAGE_FILE`).
  - Redirect Playwright MCP output to `.dadaia/mcps/playwright/`.
  - Relocate `scripts/` -> `.dadaia/scripts/`.
  - Resolve the tool-config tension for `.mcp.json` / `opencode.json` / `CLAUDE.md` (relocate where
    supported; otherwise a tiny documented exception list).
- Never delete operator-created files.

---

## SANITIZE-03 — Canonical internal `.dadaia/` layout (MEDIUM)

**Reported:** 2026-06-04 (operator: "IF MCPs always generate a directory, we must try to control
for the goal that this folder always appears on .dadaia/mcps. Not totally disorganized as it is
now"; "strict control on what you are creating inside of dadaia").

**Surface:** `.dadaia/` internal structure.

### Symptoms
- `.dadaia/` accumulates ad-hoc top-level subdirs; no enforced canonical map. MCP servers, scripts,
  and tool outputs land wherever the tool defaults.

### Root cause
- `.dadaia/` has durable + ephemeral zones but no enforced whitelist of allowed subdirs.

### Suggested fix direction
- Define and enforce a canonical map, e.g.:
  - `.dadaia/mcps/<server>/` — MCP server working/output dirs (e.g. `playwright/`).
  - `.dadaia/scripts/` — operator/utility scripts.
  - `.dadaia/tmp/<agent>/<YYYYMMDD>/` — ephemeral agent files.
  - `.dadaia/reports/` — durable reports.
  - `.dadaia/dev-report/` — dev reports.
  - `.dadaia/states/` — workspace state.
- Forbid ad-hoc top-level dirs inside `.dadaia/`; route tool outputs into their canonical homes.

---

## SANITIZE-04 — Corrective scheduled cleanup routines (MEDIUM)

**Reported:** 2026-06-04 (operator: "we must also have corrective routines that will clean the
workspace regularly. In a daily basis, maybe two days basis"; "lots of shit files are generated and
they have no value in the next 10 seconds").

**Surface:** Scheduled maintenance of ephemeral zones.

### Symptoms
- Prevention alone leaks: ephemeral files accumulate in `.dadaia/tmp/**`, `.dadaia/reports/**`,
  `.dadaia/dev-report/**` and are never reclaimed.

### Root cause
- No retention policy or scheduled reclamation; cleanup is manual and inconsistent.

### Suggested fix direction
- Declarative retention policy + a `dadaia clean` (or equivalent) command with **dry-run** default.
- Schedule daily (and/or 2-day) rotation/cleanup of `.dadaia/tmp/**`, aged `.dadaia/reports/**`,
  `.dadaia/dev-report/**` (systemd timer / cron / external scheduler).
- Safe-delete rules: never touch operator-created files; honor per-zone TTLs; log every reclaim.
- Builds on the existing cleanup-strategy backlog.

---

## SANITIZE-05 — `dadaia doctor` invariants + AGENTS.md codification (MEDIUM)

**Reported:** 2026-06-04 (operator: "we must behave explicitly about that in the AGENTS.md";
"keep a sanitization of our workspace in all points of view in the root directory, in the .dadaia
directory, in the .dadaia/reports directory and .dadaia/dev-report directory").

**Surface:** `dadaia doctor` + root `AGENTS.md` (and `public/data/AGENTS.md` source).

### Symptoms
- No automated check asserts the root whitelist or the `.dadaia/` canonical layout; drift is
  invisible until someone notices the mess.

### Root cause
- Sanitization rules are not encoded as machine-checkable invariants, and `AGENTS.md` does not state
  the strict law explicitly.

### Suggested fix direction
- Add `ROOT-*` invariants to `dadaia doctor`:
  - `ROOT-1` only whitelisted entries at root (six dirs + `AGENTS.md` + operator-tagged files).
  - `ROOT-2` no forbidden caches/outputs at root (`.ruff_cache`, `.pytest_cache`, `.coverage`,
    `.playwright-mcp`, etc.).
  - `ROOT-3` tool configs live in their canonical homes (or the documented exception list).
  - `ROOT-4` `.dadaia/` contains only canonical top-level subdirs (SANITIZE-03 map).
- Codify the law + exceptions explicitly in root `AGENTS.md` and ship it from
  `public/data/AGENTS.md`.
- Drift detection with actionable auto-fix suggestions.

---

## Open questions for operator

1. `.gitignore` at root — keep as operator-owned (current entries only ignore `.dadaia/tmp/`), or
   relocate / expand it?
2. For `.mcp.json` / `opencode.json` / `CLAUDE.md`: if a tool genuinely requires its config at root,
   prefer (a) a tiny documented exception list, or (b) hard relocation into `.dadaia/` even if it
   needs symlinks/config overrides?

---

## SANITIZE-02 research findings (T-SANI-02, 2026-06-04)

See full research: `specs/releases/v0.1.4.4/RESEARCH-configs.md`

**`.mcp.json`** — Claude Code reads `.mcp.json` ONLY from project root. No alternate path
supported. Verdict: **must stay at root**. Added to `root_exceptions.txt`.
Operator action item: migrate `mcpServers` into `.claude/settings.json` to eventually remove it.

**`opencode.json`** — opencode reads config ONLY from project root (`opencode.json`). No
`--config` flag, no `OPENCODE_CONFIG` env var. Cannot be relocated. Verdict: **must stay at
root**. Added to `root_exceptions.txt`.

**`CLAUDE.md`** — Claude Code loads project instructions from `CLAUDE.md` at root. Cannot be
renamed or relocated. Current content is a one-line stub (`# See AGENTS.md...`). Verdict:
**must stay at root**. Added to `root_exceptions.txt`.

**Actions taken:**
- Deleted regenerated caches: `.coverage`, `.hypothesis`, `.mypy_cache`, `.playwright-mcp`,
  `.pytest_cache`, `.ruff_cache`.
- Moved `scripts/install-ccusage-alias.sh` → `.dadaia/scripts/`; deleted root `scripts/`.
- Moved root `reports/` security-audit docs → `.dadaia/reports/security-audits/`; deleted root `reports/`.
- Created `.dadaia/states/root_exceptions.txt` with operator-created files and documented
  tool-config exceptions.
- `dadaia doctor` ROOT-1/ROOT-2/ROOT-3 clean after these actions.

---

## PM correction note (2026-06-07, operator overrule — PICKED for 0.1.6)

**Decision: PICKED for 0.1.6.** The operator OVERRULED the earlier deferral recommendations:
0.1.6 now includes **EVERYTHING** — all open bugs and all live backlog items; nothing is
deferred. The workspace-sanitization (root whitelist + `.dadaia/` hygiene, hooks + doctor +
scheduled correction) is now **IN 0.1.6**. product-engineer consumes it for the 0.1.6 SPEC
after the mandatory release-definition grill. **Status: PICKED for 0.1.6.**
