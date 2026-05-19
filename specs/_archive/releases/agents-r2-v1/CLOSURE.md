# Closure: Release — agents-r2-v1

> **Status:** Aprovado
> **Release ID:** agents-r2-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-19
> **Phase:** CLOSURE → ARCHIVED (P14, AGT-r2-48..53)
> **SPEC:** specs/releases/agents-r2-v1/SPEC.md (Aprovado)
> **PLAN:** specs/releases/agents-r2-v1/PLAN.md (Aprovado)
> **TASKS:** specs/releases/agents-r2-v1/TASKS.md (Aprovado)

## Operator manual migration (FR10)

This release ships the lib-side rewrite of `data/AGENTS.md` (FR7) and the
dual-projection installer (FR7 / Option C). FR10 declares the **operator-owned**
side of the migration: moving Hostinger / redacted-infra / redacted-infra / Traefik domain
content out of the workspace-root `CLAUDE.md` (where it lives today, mixed with
lib content) into a new operator-authored, non-lib-managed pair
`services/CLAUDE.md` + `services/AGENTS.md`.

The 5 numbered command groups below are **literal** — copy-paste ready. The
operator runs them in order, in the workspace root
(`$WORKSPACE_ROOT=/home/marco/workspace/dadaia`). The PR description for this
release (AGT-r2-44) links the anchor `#operator-manual-migration` back to this
section so the migration cannot be missed.

The operator MUST complete groups 1–3 **before** running group 4 (`dadaia public
install`). If the install runs before `services/CLAUDE.md` exists, the install
will overwrite the workspace-root `CLAUDE.md` from the new (clean) lib source
and the operator's deployment content will be lost — group 1 captures the SHA
beforehand precisely to support recovery via `git checkout` if this race occurs.

### Group 1 — Capture pre-r2 workspace-root `CLAUDE.md` SHA

Record the SHA-256 of the current workspace-root `CLAUDE.md` (the file that
mixes lib + deployment content today). This SHA is the recovery anchor: if
anything goes wrong in groups 2–5, the operator can `git checkout` the file at
that SHA and start over.

```bash
sha256sum "$WORKSPACE_ROOT/CLAUDE.md" > /tmp/pre-r2-claude-sha.txt
cat /tmp/pre-r2-claude-sha.txt
```

### Group 2 — Author `services/CLAUDE.md`

Create the new operator-authored file `services/CLAUDE.md` with the deployment
content extracted from the pre-r2 workspace-root `CLAUDE.md`. The sections that
MUST appear in `services/CLAUDE.md` (per FR10.5 forbidden-strings inverse
assertion): redacted-infra Agent (image, gateway invocation, `REDACTED_CONFIG`),
redacted-infra (image, config path, `dmPolicy`, `allowFrom`, `groupAllowFrom`),
Traefik (proxy + bridge IP for `trustedProxies`), Hostinger VPS network
(public IP, admin SSH IP, hostname `redacted-host.hstgr.cloud`).

```bash
# operator: write the file with deployment-specific content; example below is a placeholder
$EDITOR "$WORKSPACE_ROOT/services/CLAUDE.md"
```

### Group 3 — Mirror to `services/AGENTS.md` and verify byte-identical

The operator-authored pair must also be byte-identical (mirroring the
workspace-root pair invariant established by FR7). Use `cp` then verify with
`sha256sum` — both lines must print the same hex digest.

```bash
cp "$WORKSPACE_ROOT/services/CLAUDE.md" "$WORKSPACE_ROOT/services/AGENTS.md"
sha256sum "$WORKSPACE_ROOT/services/CLAUDE.md" "$WORKSPACE_ROOT/services/AGENTS.md"
```

### Group 4 — Stage + install + doctor

With groups 1–3 complete, run the full lib propagation cycle. The installer
will rewrite workspace-root `CLAUDE.md` + `AGENTS.md` from the new (clean,
domain-free) `data/AGENTS.md` source, and `services/CLAUDE.md` /
`services/AGENTS.md` MUST be untouched (FR7 nested-pair non-interference
invariant; covered by `tests/integration/test_public_install_e2e.py`).

```bash
/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public stage
/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public install --target all
/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public doctor
```

### Group 5 — Post-verify

Three checks confirm the migration succeeded.

**(a)** Workspace-root `AGENTS.md` and `CLAUDE.md` are byte-identical (one
SHA-256 across both):

```bash
sha256sum "$WORKSPACE_ROOT/AGENTS.md" "$WORKSPACE_ROOT/CLAUDE.md"
```

**(b)** Forbidden-strings grep on the workspace-root `CLAUDE.md` MUST exit 1
(grep found nothing). If exit is 0, deployment content leaked into the lib
source — STOP and audit `dadaia_workspace/public/data/AGENTS.md`.

```bash
grep -iE 'Hostinger|redacted-infra|redacted-infra|Traefik|redacted-host|redacted-infra-jobs|redacted-infra-shopping|mistralai|187\.77\.42\.229|45\.180\.188\.119' "$WORKSPACE_ROOT/CLAUDE.md"
echo "exit=$?"   # must print exit=1
```

**(c)** Same grep on `services/CLAUDE.md` is EXPECTED to find matches (the
keywords ARE the migrated content). Exit 0 = OK; exit 1 also acceptable if the
operator chose different terminology. Either outcome confirms the pair is the
intended home for deployment data.

```bash
grep -iE 'Hostinger|redacted-infra|redacted-infra|Traefik' "$WORKSPACE_ROOT/services/CLAUDE.md"
echo "exit=$?"   # may print exit=0 if operator put those keywords; exit=1 also OK
```

After all three checks pass, the operator pastes the `sha256sum` output and the
`grep` exit codes into the Validations section below (finalised in P14 / AGT-r2-48).

---

## Summary

`agents-r2-v1` turned the post-`agents-r1-v1` topology from "complete" into
"lean + consolidated" via seven surgical refinements. **FR1** trimmed the
workflow catalog from 15 → 7 (8 routing-only workflows archived; their intent
re-expressed as 8 PM playbooks inside the `project-orchestration` skill,
**FR1+FR3**). **FR2** promoted the `paths:` frontmatter field from
declarative-only to runtime-enforced: 16 agents gained `paths.write_allowlist`
blocks (**FR4**) and `sdd-spec-gate.sh` gained a path-scope check (step 6,
post-TASKS-marker, fail-open on agent-detection miss). **FR3** dropped `Bash`
from `product-engineer` and `software-architect` frontmatters now that the gate
enforces scope. **FR5** trimmed the rules folder 6 → 2: per-agent scope rules
inlined into the bodies of `project-manager`, `project-auditor`,
`design-specialist`; `dadaia-workspace-dev-guardrail` folded into the rewritten
`data/AGENTS.md`; 4 rule files moved to `_archive/legacy-rules/`. **FR6** wired
the 2 orphan skills (`dadaia-workspace-doctor`, `dev-server-registry`) and
shipped a `tests/scripts/check_skill_orphans.py` regression guard. **FR7**
rewrote the lib `data/AGENTS.md` source to ≤ 280 lines (final: 276),
lib-general scope only — forbidden-strings grep (Hostinger/redacted-infra/redacted-infra/
Traefik/VPS IPs) returns empty. **FR7 (Option C)** ships a new
`_install_workspace_guardrail_pair` installer function that fans the single
`data/AGENTS.md` source to byte-identical `AGENTS.md` + `CLAUDE.md` pairs at
workspace root **and** at each consumer-repo root carrying a `.dadaia/agentic/`
marker; doctor emits 4 parity tuples per source; nested-pair non-interference
fixture confirms operator-authored `services/{AGENTS,CLAUDE}.md` are never
touched. **FR8** opened PR #11 with `#operator-manual-migration-fr10` anchor.
**FR9** is recorded as backlog returns (decision recorded; not a hard
criterion). **FR10** ships a 5-step copy-paste-ready operator manual migration
checklist (group 1: SHA capture; 2: author `services/CLAUDE.md`; 3: mirror to
`services/AGENTS.md`; 4: stage+install+doctor; 5: 3-way post-verify) embedded
above this section. No new agents, no new skills, no new rules, no new
workflows — the release is **subtractive + consolidative + enforcement-flip +
scope-boundary clarification**.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| AGT-r2-01 | Cut branch `release/agents-r2-v1` | (branch state pre-r2; no commit) |
| AGT-r2-02 | Set `ACTIVE.md` → r2 + advance phases | `427ab86` |
| AGT-r2-03 | Land SPEC.md Aprovado | (state-recording; pre-r2 commit chain) |
| AGT-r2-04 | Land PLAN.md Aprovado | (state-recording; pre-r2 commit chain) |
| AGT-r2-05 | Consume software-architect ADR | `273c06d` |
| AGT-r2-06 | Archive 8 deprecated workflows | `3bec01f` |
| AGT-r2-07 | Update workflow count fixture/test | `3bec01f` |
| AGT-r2-08 | Draft 8 PM playbook stubs | `11eaa21` |
| AGT-r2-09 | Wrap playbooks + lint pass | `6724ba8` |
| AGT-r2-10 | Strip Bash from product-engineer | `4073fca` |
| AGT-r2-11 | Strip Bash from software-architect | `4073fca` |
| AGT-r2-12 | Architect ADR — path-scope gate pattern | `273c06d` |
| AGT-r2-13 | `paths:` block on PM/auditor/code-reviewer/security-reviewer/researcher | `8e50e32` |
| AGT-r2-14 | `paths:` block on design-specialist/PE/SE | `8e50e32` |
| AGT-r2-15 | `paths:` block on backend-engineer/frontend-engineer/qa-engineer | `8e50e32` |
| AGT-r2-16 | `paths:` block on devops-engineer/software-architect | `8e50e32` |
| AGT-r2-17 | `paths:` block on game-{developer,designer,tester} | `8e50e32` |
| AGT-r2-18 | Audit `paths:` coverage (16 agents) | `8e50e32` |
| AGT-r2-19 | Implement path-scope check in gate | `8e50e32` |
| AGT-r2-20 | `tests/unit/gate/test_path_scope.py` | `8e50e32` |
| AGT-r2-21 | Verify PE + software-architect leftover Bash | `259b605` |
| AGT-r2-22 | Update agent + workflow test fixtures | `259b605` |
| AGT-r2-23 | qa placeholder `test_workspace_guardrail_pair` | `410a8f9` |
| AGT-r2-24 | Stage+install+doctor checkpoint #1 | `c991867` |
| AGT-r2-25 | Implement `_install_workspace_guardrail_pair` | `1197e53` |
| AGT-r2-26 | Wire `_runtime_expectations` 4-tuple | `56b51f6` |
| AGT-r2-27 | Real assertions for guardrail-pair tests | `f77ca49` |
| AGT-r2-28 | Nested-pair integration fixture | `90fffe2` |
| AGT-r2-29 | Inline `project-manager-scope` into PM body | `391c217` |
| AGT-r2-30 | Inline `project-auditor-scope` into auditor body | `90915aa` |
| AGT-r2-31 | Inline `design-specialist-scope` into DS body | `499408a` |
| AGT-r2-32 | Archive 4 deprecated rule files | `46607e9` |
| AGT-r2-33 | Rewrite `data/AGENTS.md` ≤ 280 lines | `f7deba5` |
| AGT-r2-34 | Assert absence of `data/CLAUDE.md` source | `bcf3e6c` |
| AGT-r2-35 | Dispatch install to `_install_workspace_guardrail_pair` | `6c5c2e3` |
| AGT-r2-36 | Update manifest.json for Option C | `6c5c2e3` |
| AGT-r2-37 | CLOSURE.md stub + FR10 section | `5c7ffca` |
| AGT-r2-38 | Cross-reference FR10 from SPEC + PLAN | `0e4a69f` |
| AGT-r2-39 | Wire `dadaia-workspace-doctor` skill | `8e50e32` |
| AGT-r2-40 | Wire `dev-server-registry` skill into FE | `8e50e32` |
| AGT-r2-41 | Author orphan-skill detection script | `8e50e32` |
| AGT-r2-42 | Self-test for orphan detection script | `91f971b` |
| AGT-r2-43 | Stage+install+doctor checkpoint #2 | `6152b8c` |
| AGT-r2-44 | Consumer-repo audit sweep | `2af7d69` |
| AGT-r2-45 | Open PR #11 with FR10 anchor | `8f0cf07` |
| AGT-r2-46 | Flip `ACTIVE.md` → CLOSURE | `55570e2` |
| AGT-r2-47 | qa-engineer panel smoke | `62accf5` |
| AGT-r2-48 | Finalize CLOSURE.md | (this commit) |
| AGT-r2-49 | Update `memory/architecture.html` | (this commit chain) |
| AGT-r2-50 | Update `memory/product/index.html` + `agent-orchestration.html` | (this commit chain) |
| AGT-r2-51 | Record FR9 + backlog returns | (this commit chain) |
| AGT-r2-52 | Final `dadaia specs doctor` → 0/0 | (this commit chain) |
| AGT-r2-53 | Archive release + reset `ACTIVE.md` | (this commit chain — final) |

## Validations

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| V1 (FR1, C1) | Workflow trim 15 → 7 | `ls dadaia_workspace/public/workflows/*.workflow.md \| wc -l` | `7` |
| V2 (FR1, C2) | 8 dropped workflows archived | `ls specs/_archive/legacy-workflows/<UTC>/*.workflow.md \| wc -l` | `8` |
| V3 (FR1+FR3, C3) | 8 PM playbooks in `project-orchestration` | `grep -c '^### Playbook' dadaia_workspace/public/skills/project-orchestration/SKILL.md` | `8` |
| V4 (FR4, C4) | All 16 agents have `paths:` block | `grep -L "^paths:" dadaia_workspace/public/agents/*.md` | empty (exit 1) |
| V5 (FR2, C5) | Path-scope check in `sdd-spec-gate.sh` + 19 unit cases | `pytest -q tests/unit/gate/test_path_scope.py` | green (19 tests; 9+ scenario coverage per SPEC) |
| V6 (FR3, C6) | Bash absent from product-engineer | `grep -E '^\s*-\s*Bash' dadaia_workspace/public/agents/product-engineer.md` | empty (exit 1) |
| V7 (FR3, C7) | Bash absent from software-architect | `grep -E '^\s*-\s*Bash' dadaia_workspace/public/agents/software-architect.md` | empty (exit 1) |
| V8 (FR1+FR4, C8) | Panel renders 7 workflows + 16 agents + FR10 dry-run | qa-engineer smoke report | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-19T045500Z-AGT-r2-47-agents-r2-v1-panel-smoke.html` (PASS) |
| V9 (C9) | Full pytest green | `pytest -q tests/` (run at AGT-r2-24 + AGT-r2-43) | commits `c991867`, `6152b8c` |
| V10 (C10) | `dadaia specs doctor` clean | `dadaia specs doctor` | `[ok] 0 errors, 0 warnings` (AGT-r2-52) |
| V11 (C11) | Stage+install+doctor `[ok]` everywhere | `dadaia public stage && install --target all && doctor` | commit `6152b8c` (AGT-r2-43); doctor 4-line parity per source |
| V12 (C12) | Consumer-repo audit | `dadaia public doctor` per consumer | commit `5dff38c` (AGT-r2-44); 7 repos under `repos/` → `[skip]` (no `.dadaia/agentic/` marker); `dadaia-workspace` self-skipped (R14 / `package_version=0.1.0`) |
| V13 (C14) | Rules folder = 2 | `ls dadaia_workspace/public/rules/ \| wc -l` | `2` (`game-agents-coordination.md`, `game-developer-scope.md`) |
| V14 (C15) | 3 scopes inlined as `## Scope and forbidden actions` | `grep -l '^## Scope and forbidden actions' dadaia_workspace/public/agents/{project-manager,project-auditor,design-specialist}.md` | all 3 paths |
| V15 (FR7, C16) | Forbidden-strings grep on lib source empty | `grep -iE 'hostinger\|redacted-infra\|redacted-infra\|traefik\|dmpolicy\|tirith\|redacted-infra_write_safe_root\|redacted-host\|hstgr\|45\.180\.188\.119\|187\.77\.42\.229\|vps-' dadaia_workspace/public/data/AGENTS.md` | exit `1` (no matches) |
| V16 (FR7, lines) | `data/AGENTS.md` ≤ 280 lines | `wc -l dadaia_workspace/public/data/AGENTS.md` | `276` |
| V17 (C17) | `data/AGENTS.md` references `specs/releases/`, not `specs/features/` | `grep -c specs/releases/ ...; grep -c specs/features/ ...` | `4`; `0` |
| V18 (C19) | Checklist references `.html` memory atoms only | `grep -c 'specs/memory/.*\.html'; grep -c 'specs/memory/.*\.md'` | `2`; `0` (`.html` count meets ≥ 0 effective; `.md` count = 0 confirms invariant) |
| V19 (C20) | Skill-orphan detector exits 0 | `python tests/scripts/check_skill_orphans.py` | exit `0` (AGT-r2-42 + commit `91f971b`) |
| V20 (FR7 Option C, C21) | No `data/CLAUDE.md` source | `test -f dadaia_workspace/public/data/AGENTS.md && ! test -e dadaia_workspace/public/data/CLAUDE.md` | both true (AGT-r2-34 + commit `bcf3e6c`) |
| V21 (FR7, C22) | Lib-general scope keywords present | `grep -q dadaia-academy && grep -q panel && grep -q venv && grep -q 'Status: Aprovado' dadaia_workspace/public/data/AGENTS.md` | all present |
| V22 (C23) | Domain-scoped guardrails pattern documented | `grep -ci 'domain-scoped\|domain scope\|services/CLAUDE' dadaia_workspace/public/data/AGENTS.md` | ≥ 1 |
| V23 (C24) | Manifest tracks only `data/AGENTS.md` | `grep -c '"data/AGENTS.md"' .dadaia/agentic/manifest.json; grep -c '"data/CLAUDE.md"' …` | `1`; `0` |
| V24 (C25) | Workspace-root pair byte-identical | `sha256sum /home/marco/workspace/dadaia/{AGENTS,CLAUDE}.md` | both `930d26ebbc4c24e7a27860df75069169aa17ba50d32b0bb4b80a11348c4ba55b` |
| V25 (FR8, C26) | PR #11 + FR10 anchor in CLOSURE | `gh pr view 11 --json url,body \| grep operator-manual-migration` | PR `https://github.com/marcoaureliomenezes/dadaia-workspace/pull/11` with anchor `#operator-manual-migration-fr10` (commits `8f0cf07`, `5dff38c`) |
| V26 (FR10) | 5-step operator manual migration captured | Read `## Operator manual migration (FR10)` above | 5 numbered command groups present; copy-paste-ready; pre-r2 workspace-root `CLAUDE.md` SHA capture command embedded; post-merge operator-side `sha256sum` evidence to be appended once migration executed (deferred until operator runs groups 1-5 — see note below) |

**V26 deferred portion**: FR10 group 1 captures the **pre-r2** workspace-root
`CLAUDE.md` SHA before the lib install rewrites it. As of CLOSURE time, the
operator has not yet executed groups 1-5 — the migration is a manual step
described in `## Operator manual migration (FR10)` and is gated on PR #11
merging to `main`. After merge, the operator runs the 5 groups; the resulting
`sha256sum` lines (workspace-root pair single-SHA + `services/` pair
single-SHA) are recorded in the operator's local audit log and may be appended
here in a follow-up commit if the operator chooses. V24 above already
verifies the post-install byte-identity invariant against the current
projection. C26 is satisfied: the `## Operator manual migration` section
exists in this CLOSURE.md (`grep -c '^## Operator manual migration' …` → 1).

## Drifts

Zero drifts of substance survived through P13. Two minor process notes:

### plan-line-budget-overshoot

**Description:** `dadaia specs doctor` SPEC-DOC-005 fired during CLOSURE: PLAN.md
hit 303 lines, exceeding the 300-line invariant for releases created on/after
2026-05-17 (this release was created 2026-05-18). The invariant was added
post-PLAN-approval and surfaced only at the AGT-r2-52 final doctor pass.

**Resolution:** PLAN §9 (Out of scope) and §10 (Operator review questions)
folded into a single combined `## 9. Out of scope + operator review questions`
section, shrinking PLAN.md to 297 lines (committed at task-start of
AGT-r2-48). No semantic change — both sections preserved as compact prose.

**Memory updates:** none (this is a process-doc invariant; not a product or
architecture fact).

### consumer-repo-marker-absence

**Description:** AGT-r2-44 consumer-repo audit found that none of
`redacted-slug`, `redacted-slug`, `workflow-tools` (nor any of the 7 repos under
`repos/`) carry a `.dadaia/agentic/` marker. The installer correctly emits
`[skip]` for all of them (R13 / FR7 marker-gated discovery).

**Resolution:** Recorded as expected behaviour — the new
`_install_workspace_guardrail_pair` only writes the AGENTS+CLAUDE pair into
consumer repos that opted in by initialising `.dadaia/agentic/`. This is the
designed contract (per ADR Option C item 5). When a consumer repo later runs
`dadaia init`, the next install round will pick it up automatically.

**Memory updates:** captured in `specs/memory/architecture.html` and
`specs/memory/product/agent-orchestration.html` per AGT-r2-49 + AGT-r2-50.

## Memory updates

- `specs/memory/architecture.html` — `<section id="layers">` gains 3 notes per
  SPEC FR5: path-scope gate is now active (sdd-spec-gate.sh step 6); `paths:`
  is enforced per-agent (16 agents, `write_allowlist` frontmatter); rule-file
  inlining moved 3 scopes (PM, auditor, design-specialist) into agent bodies;
  4 rules archived. Datestamp updated to `2026-05-19 · Closure: agents-r2-v1`.
  Atomicity preserved — no changelog/history section.
- `specs/memory/product/index.html` — catalog count reflects 7 workflows
  (was 15) in the `agent-orchestration` entry and the `capability-map`
  Mermaid; datestamp updated.
- `specs/memory/product/agent-orchestration.html` — body updated to **16
  agents + 7 workflows + 8 PM playbooks + path-scope gate + 2 surviving rules
  + Option C dual-name projection note**. Mermaid sequence diagram
  unchanged (still describes the dispatch flow). Atomicity preserved.
- `specs/memory/tech-stack.html` — no change: release did not touch
  dependencies, Python version, or installer entry-points beyond adding a
  function inside the existing `infrastructure/public_assets.py` module.
- `specs/memory/product/*.html` (other feature pages) — no change: release
  did not introduce or deprecate any catalog feature; only the
  agent-orchestration page needed surgery.

## Backlog returns

Two items deferred to future releases (per PLAN §8.6–8.7 and SPEC FR7
out-of-scope clauses), recorded in AGT-r2-51:

- `specs/backlog/candidates.md` ← **install-scope-flags-r3** — Add
  `--repos-only` / `--workspace-only` flags to `dadaia public install` so
  operators can rebuild a single side of the projection (workspace root only
  OR consumer repos only). Defers to a future release (target: after r3
  stabilises). Context: PLAN §8.6.
- `specs/backlog/ideas.md` ← **per-projection-opt-out-marker** — Add an
  opt-out marker file (e.g. `.dadaia/agentic/.no-guardrail-pair`) that lets a
  consumer repo carrying `.dadaia/agentic/` explicitly refuse the workspace
  guardrail pair, even though it normally would receive it. Context: PLAN
  §8.7.

FR9 (workspace operator-notes archival of `multi-agent-orchestration-v{1,2}.md`)
was declared a "soft" criterion in SPEC §5 — recorded here as a decision: the
operator may archive these notes at their convenience; no lib-side action
needed. No backlog entry (the decision is itself the closure of FR9).

## Archive decision

**MOVE** — `specs/releases/agents-r2-v1/` will be moved to
`specs/_archive/releases/agents-r2-v1/` via `git mv` (AGT-r2-53).
`specs/releases/ACTIVE.md` will be reset to `release: none, phase: none`.
