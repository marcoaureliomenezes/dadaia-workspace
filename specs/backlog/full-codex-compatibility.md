# Backlog — Full Codex Compatibility

**ID:** FEAT-CODEX-COMPAT-100
**Priority:** CRITICAL
**Created:** 2026-06-07 (operator directive after Codex operability audit)
**Status:** OPEN — release candidate; not yet picked into SPEC/PLAN/TASKS.
**Owner:** project-manager owns this backlog item. product-engineer consumes it to author
SPEC/PLAN/TASKS after the mandatory release-definition grill.

**Source evidence:**
- Human-readable report:
  `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-07T152643Z-codex-operability-audit.html`
- Machine handoff:
  `.dadaia/handoff/dadaia-workspace/2026-06-07T152643Z-ai-engineer-codex-operability-audit.handoff.json`
- Official Codex docs checked 2026-06-07:
  `https://developers.openai.com/codex/subagents`,
  `https://developers.openai.com/codex/rules`,
  `https://developers.openai.com/codex/hooks`,
  `https://developers.openai.com/codex/skills`,
  `https://developers.openai.com/codex/config-advanced`.

---

## 1. Thesis

dadaia-workspace must be **100% first-class Codex compatible**: Claude Code, Codex, and
OpenCode may differ by runtime, but no Codex projection may be fake, stale, misleading, or
Claude-shaped. Codex must receive truthful custom agents, real command policy, working hooks,
valid skills, correct subagent/orchestration wording, and semantic doctor coverage that fails
before drift reaches an operator session.

This backlog item exists because the 2026-06-07 Codex audit found the projection pipeline is
present but semantically incomplete. `dadaia public doctor` reports `[ok]` while generated
Codex content still contains a critical broken skill reference and stale harness assumptions.

## 2. Non-negotiable compatibility definition

The release that picks this backlog item is complete only when all invariants below are true:

1. **Codex custom agents are valid and self-contained.**
   - Every `.codex/agents/*.toml` file parses as TOML.
   - Every configured agent in `.codex/config.toml` points to an existing TOML file.
   - Every skill name mentioned by generated Codex agent instructions resolves to either
     `.agents/skills/<name>/SKILL.md` or `.codex/skills/<name>/SKILL.md`.
   - No Codex agent mentions a non-existent skill such as `ai-harness-gpt-5.3-codex`.

2. **Codex model mapping is precise.**
   - Claude model identifiers in source frontmatter map to Codex model identifiers only in
     model fields or explicitly model-bearing prose.
   - The Codex transformer never rewrites semantic identifiers, skill names, file paths, or
     agent names merely because they contain `claude-`.

3. **Codex rules are honest.**
   - Official executable Codex command policy is generated as Starlark `.rules` files.
   - Markdown workflow/protocol docs are not projected in a way that pretends they are
     executable Codex Rules.
   - Sensitive commands (`git push`, `dadaia context dead`, `dadaia public install`,
     destructive shell operations) have explicit allow/prompt/forbid policy.

4. **Codex hooks are proven live.**
   - `.codex/hooks.json` is generated with supported event names and valid command output
     contracts.
   - A temp-workspace Codex smoke test proves `PreToolUse` blocks forbidden writes and allows
     valid additive writes.
   - `UserPromptSubmit` context injection returns Codex-compatible JSON and does not silently
     fail when no context is bound.

5. **Codex custom-agent config uses native boundaries.**
   - Activity class and role type drive supported Codex config such as `sandbox_mode`,
     reasoning effort, MCP server access, and skill config where applicable.
   - Review/audit agents are as mechanically read-only as Codex supports while still allowing
     report/handoff output.
   - Any remaining boundary that is advisory-only is documented as such.

6. **Codex orchestration matches the current runtime.**
   - Memory and personas distinguish two facts:
     (a) `.codex/workflows/*.workflow.md` are reference documents, not an automatic workflow
     executor;
     (b) Codex supports explicit subagent/custom-agent delegation when the operator or
     dispatcher asks for it.
   - Dispatch text uses real Codex concepts. It does not rely on fake tools, stale
     "reference-only" blanket wording, or awkward `tool_search` replacement text as product
     truth.

7. **No Claude-only path leaks into Codex personas.**
   - Generated Codex agent instructions do not point to `.claude/rules/...` as their governing
     protocol path.
   - Shared protocol references are harness-neutral or Codex-native.

8. **Doctor prevents recurrence.**
   - `dadaia public doctor` fails on all defects listed above.
   - Tests cover generated Codex TOML, hooks, rules, skill references, model mapping, and
     stale harness path leaks.
   - CI runs the Codex compatibility checks without requiring operator-local private state.

## 3. Picked workstreams

### CX-1 — Fix Codex agent semantic projection

**Owner:** software-engineer for Python projector/tests; ai-engineer reviews AI-surface intent.

**Acceptance:**
- Replace broad `claude-*` body rewriting in `runtime_transforms/codex.py`.
- Add golden tests for `ai-harness-claude-code`, model tables, skill names, file paths, and
  agent names.
- Regenerate Codex agents; `ai-engineer.toml` references the real `ai-harness-claude-code`
  skill.

### CX-2 — Codex-native command Rules

**Owner:** ai-engineer for rule design; software-engineer for generator/doctor/test support;
security-reviewer for command policy review.

**Acceptance:**
- Generate official Starlark `.rules` files for Codex command policy.
- Decide whether Markdown protocol docs move out of `.codex/rules` or remain only with a name
  that cannot be confused with executable Rules.
- Validate generated rules with Codex's command-policy checker where available.

### CX-3 — Codex hook live smoke test

**Owner:** software-engineer + qa-engineer.

**Acceptance:**
- Temp workspace launches a trusted Codex session or Codex-compatible test harness.
- Forbidden root write is blocked by `root-whitelist-gate.sh`.
- Production write without approved task is blocked by `sdd-spec-gate.sh`.
- Additive report/handoff write is allowed.
- `ctx-inject.sh` emits valid Codex JSON.

### CX-4 — Codex custom-agent config mapping

**Owner:** ai-engineer for role policy; software-engineer for TOML generator.

**Acceptance:**
- Map dadaia activity classes to supported Codex custom-agent config.
- Review/audit agents receive read-only or least-privilege config where feasible.
- Implementers and dispatchers receive intentional sandbox/reasoning settings.
- Generated TOML remains portable and contains no provider/auth/telemetry configuration.

### CX-5 — Codex subagent/orchestration truth update

**Owner:** product-engineer for memory/SPEC truth; ai-engineer for persona/workflow wording.

**Acceptance:**
- Memory states that Codex custom agents/subagents are real when explicitly invoked, while
  workflow files themselves are reference docs.
- Dispatcher personas use Codex-native wording for explicit custom-agent delegation.
- Tests forbid obsolete blanket "Codex reference-only" wording where it contradicts current
  Codex docs.

### CX-6 — Harness-neutral protocol references

**Owner:** ai-engineer.

**Acceptance:**
- Generated Codex agents do not reference `.claude/rules/...`.
- Shared protocol references point to `AGENTS.md`, `.codex` protocol docs, or a neutral
  "workspace protocol" phrase.
- Doctor fails if `.codex/agents/*.toml` contains stale Claude-only governance paths.

### CX-7 — Semantic doctor and CI gate

**Owner:** software-engineer + qa-engineer.

**Acceptance:**
- `dadaia public doctor` checks Codex semantic referential integrity.
- CI/test suite fails on non-existent skill references, missing TOML files, stale harness
  paths, fake rule files, unsupported config keys, and unvalidated hook contracts.
- A fresh temp workspace can run `public stage`, `public install --target all`, `public doctor`,
  and the Codex compatibility smoke checks cleanly.

## 4. Out of scope

- OpenCode deep parity beyond ensuring this release does not regress OpenCode projections.
- Claude Code persona redesign except where needed to author harness-neutral source text.
- Product feature work unrelated to Codex compatibility.
- Publishing a package or deploying externally. Ship/publish remains operator-gated.

## 5. Release-definition notes

This should be a dedicated release, not folded casually into unrelated cleanup. It touches
projector code, public AI surface, official Codex behavior, memory truth, doctor checks, and
test infrastructure. The release should start with a focused grill session confirming the
three decisions from the audit:

1. Reserve `.codex/rules` for official `.rules` only, or rename Markdown protocol projection.
2. Promote explicit Codex subagent/custom-agent delegation to first-class behavior, while
   keeping workflow files reference-only.
3. Define which roles receive Codex-native read-only/least-privilege custom-agent settings.

No implementation starts until SPEC/PLAN/TASKS are approved.
