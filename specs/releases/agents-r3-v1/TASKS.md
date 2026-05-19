# Tasks: Release — agents-r3-v1

> **Status:** Aprovado
> **Approved:** 2026-05-19
> **Release ID:** agents-r3-v1
> **Owner:** product-engineer
> **Created:** 2026-05-19
> **Phase:** TASKS
> **SPEC:** `specs/releases/agents-r3-v1/SPEC.md` (Aprovado).
> **PLAN:** `specs/releases/agents-r3-v1/PLAN.md` (Aprovado).
> **Total tasks:** 30 (`R3-01` through `R3-30`).

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE.
Maximum **one `[-]` per agent at a time**, except where a phase note declares
parallel-safe (disjoint write sets per PLAN §2). Declared parallel window:
**W1 = {P2 dispatcher updates, P3 workflow rewiring}** — both on `product-engineer`'s
queue post-P1.

Every public/ change MUST close with `dadaia public stage && install --target all && doctor`
(run by `devops-engineer` in P5; per-task local verify with `pytest` + `dadaia specs doctor`).

---

## Phase P0 — Foundation (state-recording; on disk)

- [x] R3-01 — Cut branch `release/agents-r3-v1` from `main` (post panel-r5-v1 archive) (`product-engineer`)
  - Touches: workspace branch state.
  - Acceptance: `git rev-parse --abbrev-ref HEAD` reports `release/agents-r3-v1`.
- [x] R3-02 — Set `specs/releases/ACTIVE.md` → `release: agents-r3-v1, phase: SPEC` then advance through `PLAN` → `TASKS` (`product-engineer`)
  - Touches: `specs/releases/ACTIVE.md`.
  - Acceptance: file content matches current phase at each transition.
- [x] R3-03 — Author SPEC.md as Aprovado (`product-engineer`)
  - Touches: `specs/releases/agents-r3-v1/SPEC.md`.
  - Acceptance: header contains `**Status:** Aprovado`.
- [x] R3-04 — Author PLAN.md as Aprovado (`product-engineer`)
  - Touches: `specs/releases/agents-r3-v1/PLAN.md`.
  - Acceptance: header contains `**Status:** Aprovado`.
- [x] R3-05 — Author TASKS.md as Aprovado (`product-engineer`)
  - Touches: `specs/releases/agents-r3-v1/TASKS.md` (this file).
  - Acceptance: header contains `**Status:** Aprovado`.

---

## Phase P1 — New agent personas + retire SE (serial after P0)

- [x] R3-06 — Author `software-engineer-python.md` persona (`product-engineer`)
  - Touches: `dadaia_workspace/public/agents/software-engineer-python.md`.
  - Preconditions: SPEC §5 boundary row 1; retired SE body available as base.
  - Done criterion: file present with frontmatter (`tier: 3`, `model: claude-sonnet-4-6`, `paths.write_allowlist` per SPEC §5, `skills`, `input_contract` with `requires_inputs` + `produces_outputs`, `tools`); body has Scope / Forbidden / Workflow protocol / Skills / Report contract sections; reader parses without raising.
- [x] R3-07 — Author `software-engineer-node.md` persona (`product-engineer`)
  - Touches: `dadaia_workspace/public/agents/software-engineer-node.md`.
  - Done criterion: same shape as R3-06; body explicitly excludes browser surfaces (frontend-engineer territory); security-conscious clauses (no `is_even`-style deps, OWASP-aware) present.
- [x] R3-08 — Author `data-engineer.md` persona (`product-engineer`)
  - Touches: `dadaia_workspace/public/agents/data-engineer.md`.
  - Done criterion: frontmatter + body; primary scope `repos/redacted-slug-explorer/**`; Databricks/Spark/Airflow/Kafka surfaces declared; data-format vocabulary (CSV/AVRO/JSON/Parquet/Delta/Iceberg) referenced; forbidden actions block excludes dashboards (data-analyst territory).
- [x] R3-09 — Author `data-analyst.md` persona (`product-engineer`)
  - Touches: `dadaia_workspace/public/agents/data-analyst.md`.
  - Done criterion: frontmatter + body; pairing with `design-specialist` for visual review documented; Playwright dashboard-eval pattern referenced; forbidden actions exclude pipeline authorship (data-engineer territory).
- [x] R3-10 — Author `ai-engineer.md` persona (`product-engineer`)
  - Touches: `dadaia_workspace/public/agents/ai-engineer.md`.
  - Done criterion: frontmatter sets `model: claude-opus-4-7` (NOT sonnet); `paths.write_allowlist` lists the 6 AI-entity globs from SPEC §5; body includes prompt-efficiency analysis protocol; forbidden actions block excludes Python/Node implementation and specs; explicit clause notes bootstrapping by `product-engineer` in r3 with `ai-engineer`-led maintenance deferred to a follow-up release.
- [x] R3-11 — Archive `software-engineer.md` (`product-engineer`)
  - Touches: `git mv dadaia_workspace/public/agents/software-engineer.md specs/_archive/legacy-agents/<UTC>/software-engineer.md`.
  - Done criterion: `ls dadaia_workspace/public/agents/*.md | wc -l` → `20`; archived file reachable; commit message references R3-11.

---

## Phase P2 — Dispatchers + Decision Authority Matrix (W1, parallel-safe with P3 — disjoint write sets)

- [x] R3-12 — Update `project-manager.md` dispatch list (`product-engineer`)
  - Touches: `dadaia_workspace/public/agents/project-manager.md`.
  - Preconditions: P1 complete (5 new persona files exist).
  - Done criterion: dispatch line drops `software-engineer`; lists `software-engineer-python`, `software-engineer-node`, `data-engineer`, `data-analyst`, `ai-engineer` in the appropriate dispatch group; prose mentions of bare `software-engineer` rewritten or removed.
  - Acceptance grep: `grep -nE '\bsoftware-engineer\b' dadaia_workspace/public/agents/project-manager.md | grep -v 'software-engineer-python\|software-engineer-node'` → empty.
- [ ] R3-13 — Update `project-auditor.md` evidence list (`product-engineer`)
  - Touches: `dadaia_workspace/public/agents/project-auditor.md`.
  - Done criterion: evidence list extended to include `data-engineer` (data-drift evidence) and `ai-engineer` (prompt-efficiency evidence); same zero-bare-SE grep acceptance as R3-12.
- [ ] R3-14 — Replace Decision Authority Matrix Python/Node row with 5 new rows (`product-engineer`)
  - Touches: `dadaia_workspace/public/skills/project-orchestration/SKILL.md`.
  - Done criterion: legacy `Python/Node implementation` row removed (grep `-c` → 0); 5 new rows present in the order declared in SPEC §FR5 (Python, Node, Data, BI, AI); leaf-agents-inventory table (line ~22 of same file) also updated.

## Phase P3 — Workflow rewiring (W1, parallel-safe with P2 — disjoint write sets)

- [ ] R3-15 — Audit `cross-cutting-feature.workflow.md` for bare-SE references (`product-engineer`)
  - Touches: `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md` (read; edit only if grep is non-empty).
  - Done criterion: `grep -nE '\bsoftware-engineer\b' dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md | grep -v 'software-engineer-python\|software-engineer-node'` → empty. If non-empty at task start, replace bare references with suffixed forms or the appropriate paired specialist (frontend-engineer/backend-engineer). Audit outcome recorded in CLOSURE Drifts section.
- [ ] R3-16 — Rewire `hotfix-release.workflow.md` (`product-engineer`)
  - Touches: `dadaia_workspace/public/workflows/hotfix-release.workflow.md`.
  - Done criterion: line ~22 `default: software-engineer` → `default: software-engineer-python`; line ~23 description enum updated to include `software-engineer-python`, `software-engineer-node`, `data-engineer`, `data-analyst`, `ai-engineer` (plus existing `frontend-engineer`, `backend-engineer`, `game-developer`) and drops bare `software-engineer`. Acceptance grep: `grep -rn '\bsoftware-engineer\b' dadaia_workspace/public/workflows/` → ZERO matches.

---

## Phase P4 — Tests + `data/AGENTS.md` + optional script (serial after P3)

- [ ] R3-17 — Update `tests/unit/features/agents/test_reader.py` count + parse assertions (`software-engineer-python`)
  - Touches: `tests/unit/features/agents/test_reader.py`.
  - Preconditions: P1 + P2 + P3 complete.
  - Done criterion: count assertion 16 → 20; each new persona file is parsed and asserted (`tier == 3`, `paths.write_allowlist` non-empty, `model` set, `skills` non-empty); `pytest -q tests/unit/features/agents/test_reader.py` exits 0.
- [ ] R3-18 — Update `tests/unit/features/panel/test_api_agents.py` card-count + tier-count assertions (`software-engineer-python`)
  - Touches: `tests/unit/features/panel/test_api_agents.py`.
  - Done criterion: card-count assertion 16 → 20; tier-count assertions `T1=2, T2=1, T3=17`; `pytest -q tests/unit/features/panel/test_api_agents.py` exits 0.
- [ ] R3-19 — Add fixture stubs for the 5 new personas (`software-engineer-python`)
  - Touches: `tests/unit/features/agents/fixtures/`.
  - Done criterion: 5 minimal frontmatter fixtures added (one per new persona) only if a test requires an isolated fixture; if all tests pass without isolated fixtures, this task is closed with a one-line note "no isolated fixtures required" and zero file changes.
- [ ] R3-20 — Add path-scope gate unit tests for new allowlists (`software-engineer-python`)
  - Touches: `tests/unit/gate/test_path_scope.py` (extend) or new file under `tests/unit/gate/`.
  - Done criterion: `ai-engineer` → `dadaia_workspace/cli/main.py` rejected with `[PATH SCOPE ERROR]`; `software-engineer-python` → same path accepted; tests exit 0.
- [ ] R3-21 — Rewrite `dadaia_workspace/public/data/AGENTS.md` for 20-agent inventory (`product-engineer`)
  - Touches: `dadaia_workspace/public/data/AGENTS.md`.
  - Preconditions: P1 + P2 complete.
  - Done criterion: agent-inventory table lists 20 rows (model + tier + one-line scope); `wc -l` ≤ 280; forbidden-strings grep (`grep -iE 'Hostinger|redacted-infra|redacted-infra|Traefik' dadaia_workspace/public/data/AGENTS.md`) exits 1.
- [ ] R3-22 — Optional: author `scripts/check_agent_topology.py` (`software-engineer-python`)
  - Touches: `scripts/check_agent_topology.py`.
  - Done criterion: script asserts exactly 20 persona files, no orphan dispatch references in PM body, all five new agents named in auditor evidence list, no orphan agent names in matrix; exits 0 on current tree; exits non-zero when an agent is deleted (smoke-tested manually).
  - Note: If P5 doctor checkpoint passes cleanly without the script, this task may close with a documentation note deferring the script to backlog.

---

## Phase P5 — Doctor checkpoint + projection cleanup + pytest sweep (serial after P4)

- [ ] R3-23 — `dadaia public stage` + `install --target all` propagation (`devops-engineer`)
  - Touches: `.agents/`, `.claude/`, `.codex/`, `.opencode/` projections (lib-managed; never hand-edited).
  - Done criterion: 5 new persona files projected into all four projection roots; commands exit 0.
- [ ] R3-24 — Clean stale `software-engineer` projection across all targets (`devops-engineer`)
  - Touches: residual `software-engineer.md` files under `.agents/`, `.claude/`, `.codex/`, `.opencode/`.
  - Done criterion: if `dadaia public install --target all` leaves stale projections, run `dadaia public install --target all --force` (operator + devops-engineer authorised — R4 cleanup pattern); afterwards no `software-engineer.md` projection remains anywhere. Verify: `find .agents .claude .codex .opencode -name 'software-engineer.md' 2>/dev/null` returns nothing.
- [ ] R3-25 — `dadaia public doctor` green (`devops-engineer`)
  - Touches: read-only.
  - Done criterion: command exits 0; all rows `[ok]`; no drift line.
- [ ] R3-26 — `dadaia specs doctor` pre-CLOSURE green (`devops-engineer`)
  - Touches: read-only.
  - Done criterion: command exits 0, `0 errors / 0 warnings`.
- [ ] R3-27 — Full `pytest -q tests/` sweep (`devops-engineer`)
  - Touches: read-only.
  - Done criterion: `.dadaia/.venv/bin/pytest -q tests/` exits 0; no skips for the 5 new personas.

---

## Phase P6 — CLOSURE (serial after P5)

- [ ] R3-28 — Author `CLOSURE.md` with full evidence triples (`product-engineer`)
  - Touches: `specs/releases/agents-r3-v1/CLOSURE.md`; `specs/releases/ACTIVE.md` flipped phase → `CLOSURE` before write.
  - Preconditions: P5 complete; all P0–P4 tasks `[x] DONE`.
  - Done criterion: file present with sections Summary / Tasks completed / Validations / Drifts / Memory updates / Backlog returns / Archive decision per `dadaia-release-closure` skill template; Validations table contains a row per acceptance criterion C1–C10 with command + evidence (SHA, stdout snippet, or report path); header `**Status:** Aprovado`.
- [ ] R3-29 — Update the 3 memory atoms (`product-engineer`)
  - Touches: `specs/memory/product/agent-orchestration.html`, `specs/memory/architecture.html`, `specs/memory/product/index.html`.
  - Preconditions: ACTIVE.md phase = `CLOSURE` (gate enforces).
  - Done criterion: agent-orchestration HTML reflects 20-agent topology, Python/Node split, AI-entity authority paragraph, data + BI surfaces; architecture HTML reflects refreshed agent-topology layer + Decision Authority Matrix rows; product/index HTML adds data + BI + AI capability bullets; no forbidden sections (Changelog/History/Histórico/Versions) anywhere; `dadaia specs doctor` final run `0/0`.
- [ ] R3-30 — Update backlog candidate + archive release + reset ACTIVE.md (`product-engineer`)
  - Touches: `specs/backlog/candidates.md`; `git mv specs/releases/agents-r3-v1 specs/_archive/releases/agents-r3-v1`; `specs/releases/ACTIVE.md` reset (`release: none` or next release per operator).
  - Done criterion: `codex-agent-orchestration-parity-v1` candidate entry updated from "16 canonical agents" → "20 canonical agents" with a note "post-agents-r3-v1 closure"; release directory moved under `_archive/`; ACTIVE.md reset; final `dadaia specs doctor` exits 0; commit chain recorded in CLOSURE Tasks-completed table.

---

**Status:** Aprovado
