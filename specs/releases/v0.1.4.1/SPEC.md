# SPEC: v0.1.4.1 — agent-architecture-hardening

**Status:** Aprovado
**Release ID:** v0.1.4.1
**Owner:** product-engineer
**Created:** 2026-06-03

---

## 1. Objective

Consolidate and fix a set of outstanding architecture and tooling defects
discovered across the v0.1.x line before any new version is published. This is
a staging/consolidation release: pyproject.toml stays at `0.1.4`; no PyPI
publish is performed. The operator decides the published version after
consolidation is declared done (see §2 Versioning model).

The work falls into five categories:

1. Merge the held security hardening branch (`hardening/panel-auth-review`).
2. Fix the SDD spec-gate context-resolution chain that silently no-ops when
   `primary_context.json` is absent.
3. Purge all references to the retired `dadaia context activate` verb and
   `primary_context.json` from shipped assets.
4. Fix the handoff schema drift between the `dadaia-handoff-emitter` skill and
   the `handoff-v1.schema.json` source of truth.
5. Fix broken references, write_allowlist over-scope, stale skill/rule content,
   language uniformity across persona files, and the one-[-]-per-owner gate
   pre-check.

## 2. Versioning model

- **pyproject.toml version stays `0.1.4`** during this consolidation. No file
  bump is performed in this release.
- **No PyPI publish** during consolidation. `0.1.4.1` is an internal staging
  tag only.
- **Decision deferred to operator:** when consolidation is done, the operator
  chooses one of two publish paths:
  - `0.1.4.1` — valid PEP 440 post-release notation; four-segment; deviates
    from strict SemVer (`^0.1.4.1` range semantics differ across tooling).
  - `0.1.5` — SemVer-clean MINOR bump; best choice if any breaking change was
    introduced; requires a one-line `pyproject.toml` edit at publish time.
- **Published v0.1.4 is immutable.** The bugs it shipped with are its record;
  fixes appear in the next deliberate publish.

## 3. Relationship to v0.1.4

`v0.1.4` (test-suite-architecture) is the last published release, currently in
`IMPLEMENTATION` phase (all tasks `[x]`). This release — `v0.1.4.1` — is a
separate consolidation track that lives alongside it and does not modify
`specs/releases/v0.1.4/` in any way.

## 4. Operator-confirmed decisions (AC-CONS-*)

The following decisions are baked in as acceptance criteria and must not be
reopened during implementation:

**AC-CONS-1 — Language uniformity.** All agent persona files and the canonical
`AGENTS.md` must use clear, direct, objective English. Two files currently
contain embedded Portuguese-language rule/scope blocks: `project-auditor.md`
and `design-specialist.md`. These blocks must be converted to English. The
canonical `AGENTS.md` default language is English.

**AC-CONS-2 — Handoff schema authoritative; no prefix.** The authoritative
source is `dadaia_workspace/public/schemas/handoff-v1.schema.json`. The schema
pattern `^[a-f0-9]{64}$` requires a bare 64-hex digest — no `sha256:` prefix.
The `dadaia-handoff-emitter` skill currently instructs agents to prepend
`sha256:`, which causes schema validation failures. That instruction and the
companion guardrail line ("Never omit the sha256: prefix") must be deleted from
the skill.

**AC-CONS-3 — devops write_allowlist tightened; generic agent principle.**
`devops-engineer.md` `paths.write_allowlist` currently includes
`dadaia_workspace/**` — far too broad; devops must not write library Python
source. Correct scope: `dadaia_workspace/public/**`. Cross-cutting principle:
agent personas must contain no consumer-specific paths, names, or inline
domain knowledge. Any such content found in `public/agents/` or `public/rules/`
during hardening must be removed or moved to a consumer overlay.

**AC-CONS-4 — No version bump until operator approves.** No change to
`pyproject.toml`'s `version` field is made in this release. See §2.

## 5. Product requirements

### PR-AUTH: Panel bearer-auth hardening (branch merge)

Branch `hardening/panel-auth-review` (commit `58aff97`) contains security
hardening already reviewed and ready. The commit covers:

- F-01: Token refresh on every `GET /api/*` bearer request.
- F-02: `Authorization` header scrubbed from response objects before logging.
- F-03: Scaffolder uses Jinja2 `SandboxedEnvironment` instead of plain
  `Environment` to prevent template injection.
- F-04: Bearer token minimum length enforced (≥ 32 characters).
- F-05: `git clone` URL guard — rejects non-http(s) and non-ssh schemes.

The branch must be merged into main with no functional changes beyond what was
reviewed.

### PR-GATE: sdd-spec-gate.sh context resolution

The gate resolves `PRIMARY_SPECS` via `primary_context.json`, which was deleted
in v2 (`dadaia migrate`). When the file is absent (the current state in all
v2 workspaces), the variable stays empty, RULE C silently exits 0 (fail-open),
and the gate provides zero production protection.

The correct resolution chain (from highest to lowest priority):

1. `DADAIA_CONTEXT` env var → `$WS/repos/$DADAIA_CONTEXT/specs`
2. `spec_contexts.json` — the single `state: "ALIVE"` entry with
   `is_primary: true` (v2 schema), or if none, the first `ALIVE` entry.
3. Session file `$WS/.dadaia/sessions/$DADAIA_SESSION_ID.json` → `context`
   field → derive `$WS/repos/<context>/specs`.
4. Fail-open if still unresolved (same as today), but log a meaningful warning.

The gate must also check that `PRIMARY_SPECS` is a real directory before
advancing past RULE C. If the resolved path does not exist, block with a clear
orientation message.

### PR-REFS: Retire `dadaia context activate` and `primary_context.json`

Five shipped files still reference these retired constructs:

| File | What must change |
|------|-----------------|
| `public/skills/dadaia-workspace-spec-navigator.md` | Replace `primary_context.json` lookup with `spec_contexts.json` lookup |
| `public/skills/dadaia-step0-memory-bootstrap.md` | Same — the "precondition" block references `primary_context.json` |
| `public/skills/dadaia-task-manager.md` | "Case (b)" resolution step references `dadaia context show` and `primary_context.json` |
| `public/rules/workspace-protocol.md` | §2 Context discovery references `primary_context.json` |
| `public/data/AGENTS.md` | Any mention of `dadaia context activate` or `primary_context.json` |

Replacement text in all cases: resolve context from `DADAIA_CONTEXT` env var,
then `spec_contexts.json` ALIVE+primary entry, then session file.

### PR-HANDOFF: Fix dadaia-handoff-emitter skill schema drift

The skill at `public/skills/dadaia-handoff-emitter.md` documents:

- `artifact.content_hash` as `sha256:<hex>` (with prefix).
- A guardrail: "Never omit the `sha256:` prefix from `artifact.content_hash`."

The schema at `public/schemas/handoff-v1.schema.json` requires `^[a-f0-9]{64}$`
— bare hex, no prefix. Every sidecar emitted following the current skill
instruction will fail schema validation.

Fix: update the skill to use bare 64-hex, delete the guardrail line about the
prefix, and update the example JSON in the skill to show a bare hash.

### PR-REFS2: Broken references and stale content

| Item | Location | Fix |
|------|----------|-----|
| Broken skill ref `dadaia-workspace-spec-reviewer` | `project-auditor.md` skills list | Replace with `dadaia-workspace-spec-navigator` (the real skill) |
| Broken skill ref `drift-detection` | `project-auditor.md` skills list | Replace with inline description or remove (no such skill file) |
| Portuguese-language scope blocks | `project-auditor.md`, `design-specialist.md` | Convert to English (AC-CONS-1) |
| `devops-engineer.md` write_allowlist `dadaia_workspace/**` | frontmatter | Tighten to `dadaia_workspace/public/**` (AC-CONS-3) |

### PR-GATE2: Gate hardening — RULE F tmp pre-check and one-[-]-per-owner

Three small gate hardening items:

1. **RULE F — tmp pre-check:** Before checking for a `[-]` task (RULE C), if
   the target path is under `.dadaia/tmp/<agent>/`, allow unconditionally and
   exit 0. Currently the gate may fall through to the IS_PROD check and fail on
   tmp paths if they happen to be under a production-gated directory.
2. **One-[-]-per-owner count:** After resolving the active TASKS.md, grep for
   the count of `[-]` markers. If count > 1 and the TASKS.md does not declare
   a `parallel_tasks: true` header, emit a warning to the gate log (not a
   block — fail-open on this check).

### PR-DEBLOAT: De-bloat, stale cleanup, ai-engineer self-edit guard

1. Remove any `public/agents/` or `public/rules/` content that names a
   consumer-specific project, hostname, or private path (AC-CONS-3).
2. Add a guard in `ai-engineer.md` that blocks the agent from editing
   `dadaia_workspace/` Python source (it should only own
   `dadaia_workspace/public/`). The write_allowlist should reflect this.
3. Clean up any stale skill references in agent frontmatter that point to
   non-existent skill files (beyond those named in PR-REFS2).

## 6. Architecture deltas

None. This release touches only:

- `dadaia_workspace/public/` — scripts, agents, skills, rules, data assets.
- No Python source changes except for the gate script which lives in `public/scripts/`.

## 7. Tech-stack deltas

None. No new dependencies.

## 8. Security / operations deltas

Panel bearer-auth hardening (PR-AUTH) is a security improvement. It is
already reviewed and committed on the held branch; this release merges it.

## 9. Memory files affected at closure

- `specs/memory/architecture.md` — update gate section if RULE F or one-[-]-
  per-owner count changes observable gate behavior.
- `specs/memory/tech-stack.md` — no changes anticipated.
- Feature atoms (on-demand): `specs/memory/product/sdd-gate-v3.md` if gate
  behavior changes materially.

Exact list confirmed during CLOSURE based on what actually shipped.

## 10. Acceptance criteria

**AC-AUTH-01** — Merge commit for `hardening/panel-auth-review` is in main.
No new test failures introduced.

**AC-GATE-01** — `sdd-spec-gate.sh` resolves `PRIMARY_SPECS` via the correct
4-step chain. When `primary_context.json` is absent and `DADAIA_CONTEXT` is
unset, the gate falls back to `spec_contexts.json` ALIVE entry instead of
silently no-oping.

**AC-REFS-01** — Zero occurrences of `primary_context.json` or
`dadaia context activate` in `public/skills/`, `public/rules/`, and
`public/data/AGENTS.md`.

**AC-HANDOFF-01** — `public/skills/dadaia-handoff-emitter.md` documents bare
64-hex only; the line "Never omit the sha256: prefix" is absent. All example
JSON in the skill shows a bare hash without prefix.

**AC-HANDOFF-02** — `dadaia reports validate` exits 0 on a freshly-emitted
sidecar from a sample run, confirming the schema round-trip is clean.

**AC-REFS2-01** — `project-auditor.md` skills list contains no broken skill
references (`dadaia-workspace-spec-reviewer` removed, `drift-detection`
removed). Persona bodies of `project-auditor.md` and `design-specialist.md`
contain no Portuguese-language embedded rule blocks.

**AC-DEVOPS-01** — `devops-engineer.md` write_allowlist contains
`dadaia_workspace/public/**` and not `dadaia_workspace/**`.

**AC-GATE2-01** — RULE F exists in `sdd-spec-gate.sh`: `.dadaia/tmp/<agent>/`
paths exit 0 before the IS_PROD check.

**AC-GATE2-02** — Gate log warning is emitted when more than one `[-]` marker
exists in a TASKS.md (warn-only, not block).

**AC-DEBLOAT-01** — `ai-engineer.md` write_allowlist does not include raw
Python source paths; it covers only `dadaia_workspace/public/**` and report
paths.

**AC-CONS-1, AC-CONS-2, AC-CONS-3, AC-CONS-4** — As stated in §4.

**AC-VERIFY-01** — After all tasks `[x]`:
```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor        # exit 0
dadaia specs doctor         # exit 0
poetry run pytest -q -m "unit and not slow" tests/unit
```
All commands exit 0.

## 11. Out of scope

- No Python source changes beyond `public/scripts/sdd-spec-gate.sh`.
- No new features or CLI commands.
- No pyproject.toml version bump.
- No PyPI publish.
- No changes to `specs/releases/v0.1.4/`.
- No test taxonomy changes (those shipped in v0.1.4).
- No memory atom rewrites beyond gate behavior deltas.
