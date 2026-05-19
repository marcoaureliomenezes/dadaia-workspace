# Plan: Release — agents-r3-v1

> **Status:** Aprovado
> **Approved:** 2026-05-19
> **Approved-by:** operator (design pre-approved in dispatch brief)
> **Release ID:** agents-r3-v1
> **Owner:** product-engineer
> **Created:** 2026-05-19
> **Phase:** PLAN
> **SPEC:** `specs/releases/agents-r3-v1/SPEC.md` (Aprovado).
> **Predecessor plan:** `agents-r2-v1` PLAN (reused patterns: path-scope gate inheritance,
> doctor checkpoint cleanup, fixture-count updates, `git mv` archive flow).

## 1. Phase pipeline — P0..P6

Each phase: **PN — title.** *owner.* Deliverables / Acceptance / Deps.

### P0 — Foundation (state-recording; already on disk)

*Owner:* `product-engineer`.

Deliverables: branch `release/agents-r3-v1` cut from `main` at the panel-r5-v1 archive
tip; `specs/releases/ACTIVE.md` set to `release: agents-r3-v1, phase: SPEC`; SPEC.md +
PLAN.md + TASKS.md authored as Aprovado (this artifact).

Acceptance: all three documents on disk with `**Status:** Aprovado` headers. ACTIVE.md
phase advances `SPEC` → `PLAN` → `TASKS` as each artifact lands.

Dependencies: panel-r5-v1 CLOSED and ARCHIVED.

### P1 — New agent personas authored (Foundation → Personas)

*Owner:* `product-engineer`.

Deliverables:

- `dadaia_workspace/public/agents/software-engineer-python.md` — full persona, frontmatter
  with tier=3, model=`claude-sonnet-4-6`, `paths.write_allowlist` per SPEC §5 row 1,
  `skills`, `input_contract` (`requires_inputs` + `produces_outputs`), `tools` list, plus
  body (Scope / Forbidden / Workflow protocol / Skills / Report contract). Body adapts
  the Python sections of the retired SE persona.
- `dadaia_workspace/public/agents/software-engineer-node.md` — analogous; Node sections
  of the retired SE persona; explicit boundary with `frontend-engineer` (no browser
  surfaces) and `security-reviewer` (no `is_even`-style deps, OWASP-aware).
- `dadaia_workspace/public/agents/data-engineer.md` — new persona; primary scope
  `repos/redacted-slug-explorer/**`, cross-project on data demand; Databricks DAB / Spark /
  Airflow / Kafka surface.
- `dadaia_workspace/public/agents/data-analyst.md` — new persona; pairs with
  `design-specialist` for dashboard visual review (same pattern as
  `frontend-engineer` ↔ `design-specialist`).
- `dadaia_workspace/public/agents/ai-engineer.md` — new persona; **model
  `claude-opus-4-7`**; exclusive write authority on AI-entity surface
  (`public/{skills,rules,workflows,commands,agents,hooks}/**`); body includes
  prompt-efficiency analysis protocol and a forbidden-actions block ruling out Python/
  Node implementation.
- `git mv dadaia_workspace/public/agents/software-engineer.md
       specs/_archive/legacy-agents/<UTC>/software-engineer.md`.

Acceptance: `ls dadaia_workspace/public/agents/*.md | wc -l` → `20`; archived file
reachable under `specs/_archive/legacy-agents/<UTC>/software-engineer.md`; each new file
parses with the existing frontmatter reader (`dadaia_workspace/features/agents/reader.py`)
without raising.

Dependencies: P0.

### P2 — Dispatcher updates + Decision Authority Matrix

*Owner:* `product-engineer`.

Deliverables:

- Edit `dadaia_workspace/public/agents/project-manager.md` — drop `software-engineer`
  from the dispatch list; insert the five new agents into the appropriate group; rewrite
  prose mentions of bare `software-engineer` to suffixed forms or generic phrasing.
- Edit `dadaia_workspace/public/agents/project-auditor.md` — extend evidence list to
  include `data-engineer` and `ai-engineer`; update any bare-SE prose.
- Edit `dadaia_workspace/public/skills/project-orchestration/SKILL.md` — replace the
  legacy `Python/Node implementation` row in the Decision Authority Matrix with the 5
  new rows from SPEC §FR5; update the leaf inventory table accordingly.

Acceptance:

- `grep -nE '\bsoftware-engineer\b' dadaia_workspace/public/agents/project-manager.md
   | grep -v 'software-engineer-python\|software-engineer-node'` → empty.
- Same grep against `project-auditor.md` → empty.
- `grep -c 'Python/Node implementation' dadaia_workspace/public/skills/project-orchestration/SKILL.md` → `0`.
- 5 new matrix rows present in declared order.

Dependencies: P1.

### P3 — Workflow rewiring (rewire-only, no new files)

*Owner:* `product-engineer`.

Deliverables:

- Audit + (likely no-op) edit `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md`
  — current grep shows zero bare-SE references; record audit outcome in CLOSURE.
- Edit `dadaia_workspace/public/workflows/hotfix-release.workflow.md` — replace
  `default: software-engineer` (line ~22) with `default: software-engineer-python`
  (conservative Python-leaning default; dispatcher overrides per fix-path); update the
  description enum at line ~23 to list the 5 new agents (`software-engineer-python`,
  `software-engineer-node`, `data-engineer`, `data-analyst`, `ai-engineer`) plus
  `frontend-engineer`, `backend-engineer`, `game-developer`, and DROP bare
  `software-engineer`.

Acceptance: `grep -rn '\bsoftware-engineer\b' dadaia_workspace/public/workflows/`
returns ZERO matches.

Dependencies: P0 (independent of P1/P2 for read-only audit; edits run after P2 for
single-PR coherence).

### P4 — Tests + `data/AGENTS.md` + optional topology script

*Owner:* `software-engineer-python` (the very first work from the newly-authored agent;
limited to Python/test surfaces only).

Deliverables:

- `tests/unit/features/agents/test_reader.py` — count assertion 16 → 20; new assertions
  for the 5 new personas.
- `tests/unit/features/agents/fixtures/` — add fixture stubs for the 5 new agent shapes
  only if tests require isolated fixtures (decide during P4; default = read live).
- `tests/unit/features/panel/test_api_agents.py` — count 16 → 20; tier counts
  `T1=2, T2=1, T3=17`.
- `dadaia_workspace/public/data/AGENTS.md` — rewrite for 20-agent inventory; preserve
  ≤ 280-line invariant; preserve forbidden-strings clean state.
- Optional `scripts/check_agent_topology.py` per SPEC FR9.

Acceptance: `pytest -q tests/unit/features/agents/` and
`pytest -q tests/unit/features/panel/test_api_agents.py` green;
`wc -l dadaia_workspace/public/data/AGENTS.md` ≤ 280;
forbidden-strings grep exits 1; optional script (if landed) exits 0 against current tree.

Dependencies: P1, P2, P3.

### P5 — Doctor checkpoint + projection cleanup + pytest sweep

*Owner:* `devops-engineer`.

Deliverables:

- `dadaia public stage && dadaia public install --target all` — propagate the 5 new
  persona files into every projection (`.agents/`, `.claude/`, `.codex/`, `.opencode/`)
  and remove the stale `software-engineer` projection across the same surfaces (R4
  cleanup pattern, agents-r2-v1 P8 lineage).
- `dadaia public doctor` — verify all `[ok]`, zero drift.
- `dadaia specs doctor` — verify `0 errors / 0 warnings` (pre-CLOSURE check; memory
  edits land in P6).
- `pytest -q tests/` — full sweep; everything green.

Acceptance: C7 (public doctor green) + intermediate C8 (specs doctor green pre-memory
updates) + pytest sweep green. Evidence captured as commit SHA + stdout snippets.

Dependencies: P4.

### P6 — CLOSURE

*Owner:* `product-engineer`.

Deliverables:

- Flip `specs/releases/ACTIVE.md` phase → `CLOSURE`.
- Write `specs/releases/agents-r3-v1/CLOSURE.md` with sections Summary / Tasks completed
  / Validations / Drifts / Memory updates / Backlog returns / Archive decision per the
  `dadaia-release-closure` skill template.
- Update the 3 memory atoms per SPEC §FR10:
  `specs/memory/product/agent-orchestration.html`,
  `specs/memory/architecture.html`,
  `specs/memory/product/index.html`.
- Update `specs/backlog/candidates.md` — record the `codex-agent-orchestration-parity-v1`
  count update (16 → 20).
- Final `dadaia specs doctor` (`0/0`).
- `git mv specs/releases/agents-r3-v1 specs/_archive/releases/agents-r3-v1`.
- Reset `specs/releases/ACTIVE.md` (`release: none` or next release).

Acceptance: C8 + C9 + C10 + final specs-doctor green + archive in place + ACTIVE reset.

Dependencies: P5.

---

## 2. Parallel-safe windows

**Default: serial.** The release's tight inter-file coupling (one persona edit cascades
into PM + auditor + matrix + tests + AGENTS.md) keeps the default serial.

**Declared parallel window: W1 = {P2 dispatcher updates, P3 workflow rewiring}.** Both
sit on `product-engineer`'s queue after P1 lands. Their write sets are disjoint:

- P2 touches `public/agents/project-manager.md`, `public/agents/project-auditor.md`,
  `public/skills/project-orchestration/SKILL.md`.
- P3 touches `public/workflows/cross-cutting-feature.workflow.md`,
  `public/workflows/hotfix-release.workflow.md`.

Both share zero target paths and share zero downstream contracts (P2 = dispatch graph;
P3 = workflow content). They MAY run in parallel if two `[-]` markers are declared
together in TASKS.md under the P2/P3 sections with the explicit
"parallel-safe — disjoint write sets" annotation. If only one operator-agent is active,
run them serially in the P2 → P3 order documented above.

All other phases (P0 → P1, P3 → P4, P4 → P5, P5 → P6) are **strictly serial**.

---

## 3. Risk mitigations

| Risk | Mitigation | Owner |
|---|---|---|
| Drift between 5 surfaces (personas, PM, auditor, matrix, tests, AGENTS.md) | (a) Optional `scripts/check_agent_topology.py` (FR9) acts as a single-source-of-truth validator; (b) P5 doctor checkpoint catches projection drift; (c) C2 zero-bare-SE grep catches missed prose edits. | `product-engineer` (authors), `devops-engineer` (P5 checkpoint) |
| Stale `software-engineer.md` projection lingering in `.agents/`, `.claude/`, `.codex/`, `.opencode/` after retirement | R4 cleanup pattern from agents-r2-v1 P8: `dadaia public stage && install --target all --force && doctor`; investigate any leftover files surfaced by doctor and remove manually if `--force` does not clean them. | `devops-engineer` |
| `cross-cutting-feature.workflow.md` already clean — risk that the audit task is mistakenly skipped | P3 task is structured as an explicit grep-then-document step, not a blind edit. The grep is recorded in CLOSURE Validations table even when zero matches → audit is a deliverable, not an optional check. | `product-engineer` |
| `ai-engineer` opus model assignment increases token cost | Bounded by invocation rarity (only AI-entity surface edits trigger it). Decision accepted by operator; no mitigation beyond cost monitoring in CLOSURE backlog notes if usage spikes. | `product-engineer` |
| Recursive scope: `ai-engineer` would author its own persona | Q4 hard-locks P1 authoring to `product-engineer`. `ai-engineer.md`'s body includes the explicit clause "this persona was bootstrapped by `product-engineer` in release `agents-r3-v1`; future maintenance transitions to `ai-engineer` in a follow-up release". | `product-engineer` |
| `codex-agent-orchestration-parity-v1` backlog candidate's "16 agents" assumption becomes stale | Recorded as CLOSURE backlog return; the next release that touches codex parity must re-read the entry and update wording to 20 agents before opening its own SPEC. | `product-engineer` (CLOSURE notes) |

---

## 4. Verification checkpoints

The 10 checkpoints from SPEC §3 restated as actionable commands:

1. **C1 — Count assertion.**
   `ls dadaia_workspace/public/agents/*.md | wc -l` → `20`.
2. **C2 — No bare SE references.**
   `grep -rn '\bsoftware-engineer\b' dadaia_workspace/public/{agents,skills,workflows,commands,rules}
      | grep -v 'software-engineer-python\|software-engineer-node\|legacy\|archived'`
   exit 1 (no matches).
3. **C3 — Frontmatter parse green.**
   `.dadaia/.venv/bin/pytest -q tests/unit/features/agents/` exits 0.
4. **C4 — Panel API count.**
   `.dadaia/.venv/bin/pytest -q tests/unit/features/panel/test_api_agents.py` exits 0;
   /api/agents returns 20 cards with tier counts `T1=2, T2=1, T3=17`.
5. **C5 — Path-scope gate honours new allowlists.**
   Unit test simulating `ai-engineer` writing `dadaia_workspace/cli/main.py` returns
   `[PATH SCOPE ERROR]`; complement test for `software-engineer-python` at same path
   succeeds. Encoded in `tests/unit/gate/test_path_scope.py` (extension of agents-r2-v1
   test file) or a new test file under `tests/unit/gate/`.
6. **C6 — Decision Authority Matrix delta.**
   `grep -c 'Python/Node implementation' dadaia_workspace/public/skills/project-orchestration/SKILL.md` → `0`;
   manual table inspection confirms 5 new rows in operator-declared order.
7. **C7 — `dadaia public doctor` green.**
   `.dadaia/.venv/bin/dadaia public doctor` exits 0, all `[ok]`, zero drift; no stale
   `software-engineer` projection files in any of the 4 projection roots.
8. **C8 — `dadaia specs doctor` green.**
   `.dadaia/.venv/bin/dadaia specs doctor` exits 0, `0 errors / 0 warnings`. Run twice:
   once pre-P6 memory updates, once post-P6 memory updates.
9. **C9 — Live panel smoke.**
   Operator launches `dadaia panel`; agents tab renders 20 cards with tier accents
   T1 red, T2 amber, T3 neutral. Evidence: screenshot under
   `specs/assets/agents-r3-v1/panel-20-agents.png`.
10. **C10 — Operator review of personas.**
    Operator reads the 5 new persona files end-to-end; explicit OK recorded in CLOSURE
    alongside the other C1–C9 entries.

---

**Status:** Aprovado
