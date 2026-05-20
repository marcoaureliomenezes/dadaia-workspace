# Tasks: Release — token-cost-bigbang-v1

> **Status:** Aprovado
> **Release ID:** token-cost-bigbang-v1
> **Owner:** product-engineer (authorship); ai-engineer + devops-engineer + product-engineer (implementação)
> **Phase:** TASKS → IMPLEMENTATION
> **SDD rule:** No máximo um `[-]` por owner por vez, exceto tasks com disjoint write sets explicitamente declarados.

---

## P2-B — Schema + validator (devops-engineer)

- [-] **T-20** — Update `dadaia_workspace/public/schemas/handoff-v1.schema.json` → v1.1. New required fields: `findings[].detail_md`, `findings[].fix_recommendation`, `scope`, `metrics`. Make `artifact.path` optional.
  - **Owner:** devops-engineer
  - **Write-allowlist:** `dadaia_workspace/public/schemas/`
  - **Done criterion:** `dadaia reports validate` accepts a v1.1 sidecar; schema file has `"$schema"` bumped to v1.1.
  - **Deps:** T-12

- [ ] **T-21** — Update `dadaia reports validate` CLI: accept v1.1, reject v1.0 with missing `detail_md` (warning) or missing `findings[]` (error).
  - **Owner:** devops-engineer
  - **Write-allowlist:** `dadaia_workspace/cli/`, `dadaia_workspace/features/`
  - **Done criterion:** `dadaia reports validate <v1.0-sidecar>` exits non-zero with clear error message.
  - **Deps:** T-20

- [ ] **T-22** — Add `dadaia reports lint <dir>` command: flags orphaned HTML (no sidecar), oversized HTML (> 30 KB), missing schema fields.
  - **Owner:** devops-engineer
  - **Write-allowlist:** `dadaia_workspace/cli/`, `dadaia_workspace/features/`
  - **Done criterion:** `dadaia reports lint .dadaia/reports/` runs without exception; flags at least one known orphan in the current `.dadaia/reports/` tree.
  - **Deps:** T-21

---

## P2-C — Agent rewrites (ai-engineer)

- [x] **T-30** — Model flip: rewrite `model:` frontmatter on 7 agents (`project-manager`, `project-auditor`, `product-engineer`, `software-architect`, `ai-engineer`, `game-designer`, `game-tester`) → `claude-sonnet-4-6`. Confirm `researcher` = `claude-haiku-4-5`.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/agents/`
  - **Done criterion:** `grep -l 'model: claude-opus' dadaia_workspace/public/agents/` returns empty for the 7 flipped agents; `researcher.md` confirmed `model: claude-haiku-4-5`.
  - **Deps:** T-12

- [-] **T-31** — Description trim: rewrite every agent's `description:` frontmatter field to ≤ 200 characters. Move long description content into the agent body if still relevant; delete otherwise.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/agents/`
  - **Done criterion:** No agent has `description:` length > 200 chars (verified via script).
  - **Deps:** T-30

- [ ] **T-32** — Template extraction: for every agent body > 350 lines, extract report templates to `docs/agent-knowledge/<agent>/templates/*.md`. Agent body keeps a one-liner pointer.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/agents/`, `docs/agent-knowledge/`
  - **Done criterion:** No agent body > 350 lines after extraction; affected agents reference `docs/agent-knowledge/<agent>/templates/` via one-liner.
  - **Deps:** T-31

- [ ] **T-33** — Shared workspace-protocol: create `dadaia_workspace/public/rules/workspace-protocol.md` containing SDD gate + context discovery + task lifecycle + report path. Factor out from each agent body.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/rules/`, `dadaia_workspace/public/agents/`
  - **Done criterion:** New `workspace-protocol.md` exists; each agent body references it instead of duplicating the protocol inline.
  - **Deps:** T-32

- [ ] **T-34** — Skill Tier-A/B split: migrate 22 Tier-B `SKILL.md` files to `docs/agent-knowledge/<agent>/<topic>.md`. Update owning agent body with new reference BEFORE deleting the `SKILL.md` source.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/skills/`, `docs/agent-knowledge/`, `dadaia_workspace/public/agents/`
  - **Done criterion:** 11 Tier-A skills remain in `public/skills/`; 22 Tier-B skills live under `docs/agent-knowledge/<agent>/`; owning agents updated.
  - **Deps:** T-33

- [ ] **T-35** — Legacy `software-engineer` sweep: `grep -rl 'subagent_type.*software-engineer\b' dadaia_workspace/public/ .claude/` → rewrite each occurrence to `-python` or `-node` per call site. Add lint rule in `dadaia public doctor` rejecting the legacy alias.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/`, `.claude/`
  - **Done criterion:** `grep -r 'subagent_type: software-engineer\b' dadaia_workspace/public/ .claude/` returns zero results; `dadaia public doctor` flags any reintroduction.
  - **Deps:** T-34

- [ ] **T-36** — Sidecar-first contract: rewrite every agent prompt so emission default is JSON sidecar v1.1 only. HTML emission requires explicit `--with-report` flag in dispatch prompt OR `next_handoff.agent == "human"`.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/agents/`
  - **Done criterion:** All 20 agents updated with sidecar-first emission language; 5 spot-checked dispatches confirm no surprise HTML.
  - **Deps:** T-20, T-35

- [ ] **T-37** — Dispatch-to-researcher playbooks: update `project-orchestration` SKILL.md with parallel-researcher fan-out pattern. Add standing instruction to `software-architect`, `project-auditor`, `code-reviewer`, `security-reviewer`, `devops-engineer` to dispatch researcher for evidence harvest.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/skills/`, `dadaia_workspace/public/agents/`
  - **Done criterion:** `project-orchestration/SKILL.md` documents fan-out pattern; 5 listed agents carry the standing instruction in body.
  - **Deps:** T-36

- [ ] **T-38** — Operator-facing report logic: codify in `project-manager` dispatcher playbook the question "HTML or sidecar?" before emitting. If report > 30 KB, agent splits into multi-HTML with `index.html`.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/agents/`
  - **Done criterion:** `project-manager.md` body contains the HTML/sidecar prompt + multi-HTML split rule; spot-check confirms dispatcher asks before emitting.
  - **Deps:** T-37

- [ ] **T-39** — D-20 enforcement (frontend-design plugin scope): (a) create `dadaia_workspace/public/rules/plugin-scope.md` with `[PLUGIN SCOPE ERROR]` refusal pattern mirroring `game-developer-scope.md`; (b) add allow-list line to `frontend-engineer.md` and `design-specialist.md` body declaring `Plugins authorised: frontend-design, playwright (this agent only — see plugin-scope rule).`; (c) request devops-engineer to stage + install + verify via `dadaia public doctor` green.
  - **Owner:** ai-engineer
  - **Write-allowlist:** `dadaia_workspace/public/rules/`, `dadaia_workspace/public/agents/`
  - **Done criterion:** `plugin-scope.md` exists with refusal pattern; both authorised agents carry allow-list line; doctor green after install.
  - **Deps:** T-37

---

## P2-D — Workflows + projection (devops-engineer + product-engineer)

- [ ] **T-40** — Workflows YAML: update all 7 workflow files. Each stage declares `consumes: [path-to-upstream-sidecar.json]` (not HTML). The 4 read-heavy workflows (`audit-cycle`, `code-review-fan-out`, `cross-cutting-feature`, `spec-refinement`) get dispatch-to-researcher injected.
  - **Owner:** devops-engineer
  - **Write-allowlist:** `dadaia_workspace/public/workflows/`
  - **Done criterion:** All 7 workflows declare `consumes:` with sidecar paths; 4 read-heavy workflows carry dispatch-to-researcher stages.
  - **Deps:** T-37

- [ ] **T-41** — Re-architect `dadaia public install`: emit single `AGENTS.md` as canonical at workspace root; `CLAUDE.md` becomes 1-line stub (`@AGENTS.md` include). Skills live in `.agents/skills/` with symlinks at `.claude/skills/`, `.codex/skills/`, `.opencode/skills/`.
  - **Owner:** devops-engineer
  - **Write-allowlist:** `dadaia_workspace/infrastructure/`
  - **Done criterion:** `public_assets.py` updated; clean workspace install yields canonical `AGENTS.md` + 1-line `CLAUDE.md` stub + symlinked skills tree.
  - **Deps:** T-34

- [ ] **T-42** — Run `dadaia public stage && dadaia public install --target all` in a clean workspace clone. Verify `dadaia public doctor` reports all entries `[ok]`.
  - **Owner:** devops-engineer
  - **Write-allowlist:** none (verification only)
  - **Done criterion:** `dadaia public doctor` exits 0 with every entry `[ok]`; stdout snippet captured for CLOSURE evidence.
  - **Deps:** T-41

- [ ] **T-43** — CLOSURE phase only: update `specs/constitution.md` with ADRs X1..X7. Render/update memory atoms (`specs/memory/architecture.html`, `specs/memory/tech-stack.html`, `specs/memory/product/agent-orchestration.html`, `specs/memory/product/index.html` if catalog changed).
  - **Owner:** product-engineer
  - **Write-allowlist:** `specs/constitution.md`, `specs/memory/`
  - **Done criterion:** Constitution carries ADRs X1..X7; memory atoms reflect post-release state atomically (no Changelog/History sections); `dadaia specs doctor` green.
  - **Deps:** T-42, all P2-C tasks (T-30..T-39)

---

## P3 — Validation gate (operator + project-auditor, 7-day window post-CLOSURE)

- [ ] **T-50** — Run `npx ccusage@latest claude daily | tail -7`. Compare to T-03 baseline.
  - **Owner:** operator
  - **Write-allowlist:** none (measurement only)
  - **Done criterion:** Average daily cost ≤ $25 over the 7-day window; stdout captured as CLOSURE evidence.
  - **Deps:** T-43

- [ ] **T-51** — Re-run the per-session `cache_read / msg` script from audit §1.
  - **Owner:** operator
  - **Write-allowlist:** none (measurement only)
  - **Done criterion:** `cache_read / msg ≤ 80 K` (falsifies audit §8 P-02); script output captured.
  - **Deps:** T-43

- [ ] **T-52** — Spot-check 5 dispatches: confirm researcher fan-out happening; sidecars carry `detail_md`; no HTML emitted unless explicitly requested.
  - **Owner:** operator + project-auditor
  - **Write-allowlist:** none (audit only)
  - **Done criterion:** 0 surprise HTML reports across 5 dispatches; researcher fan-out visible in at least 2 of the 5.
  - **Deps:** T-43

- [ ] **T-53** — Run `dadaia reports lint .dadaia/reports/`.
  - **Owner:** operator
  - **Write-allowlist:** none (lint only)
  - **Done criterion:** Lint clean: 0 orphaned HTMLs, 0 oversized HTMLs; stdout captured.
  - **Deps:** T-43

- [ ] **T-54** — Sub-agent dispatch ratio.
  - **Owner:** operator
  - **Write-allowlist:** none (measurement only)
  - **Done criterion:** ≥ 8 dispatches/session average across the 7-day window.
  - **Deps:** T-43

---

## Notes on parallelism

- **P2-B (T-20..T-22) and P2-C (T-30..T-39) may run in parallel** because their write
  sets are disjoint (`public/schemas/` + `cli/` + `features/` vs `public/agents/` +
  `public/skills/` + `public/rules/` + `docs/agent-knowledge/`). The owners are also
  distinct (devops-engineer vs ai-engineer).
- **Within P2-C the sequence T-30 → T-31 → T-32 → T-33 → T-34 → T-35 → T-36 → T-37 →
  T-38 is strictly serial** (each task assumes the prior one is `[x]` DONE). T-39 may
  run in parallel with T-38 once T-37 is `[x]` DONE because they touch different files.
- **P2-D (T-40..T-43)** is sequential after P2-B + P2-C converge. T-43 is the CLOSURE-
  phase memory write — gate-locked.
- **P3 (T-50..T-54)** runs post-CLOSURE/ARCHIVED, not inside the IMPLEMENTATION phase.
  Operator + project-auditor own this gate.
