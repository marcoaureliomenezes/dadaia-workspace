# PLAN: v0.1.9 alpha-1 — Spec/Memory Fidelity Remediation

**Status:** Aprovado
**Release ID:** v0.1.9
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-09

---

## Strategy

Three parallel tracks by agent ownership. product-engineer executes all memory/spec
writes in the DEFINITION phase (gate §13). software-engineer executes code layering
under the standard `[ ] → [-] → [x]` protocol. ai-engineer edits `public/` source then
triggers reprojection. Tracks are independent and may proceed in parallel; the sole
coordination point is the final `dadaia public doctor` gate before CLOSURE.

---

## Phase 1 — product-engineer: Memory and spec atoms

All writes to `specs/memory/**` and `specs/constitution.md` are gated to
DEFINITION/CLOSURE per §13. product-engineer holds the write lease for this phase.

### Execution order within Phase 1

1. **HIGH first** — `workspace-doctor.md` (LEASE codes). Highest operational risk:
   any agent following the stale LEASE-1..4 codes wastes diagnostic effort.
2. **Architecture.md** — large file, many sub-changes; do once to avoid double edits.
3. **sdd-gate-v3.md + stale release_origin quartet** — all bash-era/stale-origin
   changes grouped; context is the same (0.1.8 Python hook transition).
4. **cross-platform-portability.md** — Phase 2/3 CI section update.
5. **specs-doctor.md** — check-ID correction.
6. **tech-stack.md** — PM model + CLI completions.
7. **constitution.md §7** — researcher removal.
8. **quality-assurance.md** — stale sentence removal.
9. **Skill count** — catalog.json + index.md update (last, because count may shift with
   AI-surface track outcomes).

### Validation for Phase 1

`dadaia specs doctor` exits 0 after all memory writes.

---

## Phase 2 — software-engineer: Code layering

Both tasks are gated by the standard SDD gate (TASKS `[-]` reservation).

### T-CODE-01: subprocess → infrastructure adapters

Three files: `features/import_/service.py`, `features/ci_preflight/service.py`,
`features/specs/doctor.py`. For each:
1. Identify subprocess usage pattern (Popen/run/check_output).
2. Create or extend the relevant `infrastructure/` adapter implementing a Protocol.
3. Replace direct subprocess calls with Protocol calls.
4. Add import-linter forbidden-import rule: `features.* -> subprocess`.
5. Run full pytest suite — must pass with 0 regressions.

### T-CODE-02: container.py PLATFORM singleton

`dadaia_workspace/core/container.py:134`. Replace `sys.platform` string comparison
with `PLATFORM` singleton method call. Run pytest — must pass.

### Validation for Phase 2

`pytest` full suite green. Import-linter passes.

---

## Phase 3 — ai-engineer: AI-surface (public/ source)

All changes in `dadaia_workspace/public/agents/` and
`dadaia_workspace/public/skills/`. After every edit, run:
```
dadaia public stage
dadaia public install --target all
dadaia public doctor
```
`dadaia public doctor` must exit 0 before CLOSURE.

### T-AI-01: dev-server-registry skill wired
Add a `SKILLS` or `skills:` reference to `dev-server-registry` in
`software-engineer.md` agent source.

### T-AI-02: [SCOPE ERROR] parity
Add the standard `[SCOPE ERROR]` block to 5 persona source files:
`code-reviewer.md`, `product-engineer.md`, `project-auditor.md`,
`project-manager.md`, `security-reviewer.md`.

### T-AI-03: ai-context-engineering I1 schema refresh
Edit `ai-context-engineering/SKILL.md` section I1 reference list to match current
persona frontmatter keys.

### T-AI-04: Report-emission dedup
Remove the verbatim "Report emission" block from each of the 9 persona bodies.
Confirm `workspace-protocol §4` coverage before removal.

### T-AI-05: opencode_model removal
Remove vestigial `opencode_model` key from the 2 persona files that carry it.

### Validation for Phase 3

`dadaia public doctor` exits 0. Spot-check projected `.claude/agents/*.md` and
`.codex/agents/*.toml` to confirm changes propagated.

---

## Technical risks

| Risk | Mitigation |
|------|-----------|
| Import-linter rule addition may collide with existing contracts | software-engineer reads `setup.cfg`/import-linter config first |
| Removing Report-emission from personas creates guidance gap if workspace-protocol is not projected | ai-engineer verifies projection before removing from persona bodies |
| Memory edits to architecture.md (large file) — edit collision risk | product-engineer edits architecture.md once in a single session |
| `dadaia public doctor` post-projection drift | ai-engineer runs `public stage && public install --target all` in one shot after all Phase 3 edits |

---

## Validation plan

1. `dadaia specs doctor` — 0 errors after Phase 1 memory writes.
2. `pytest` full suite — 0 failures after Phase 2 code changes.
3. `dadaia public doctor` — exit 0 after Phase 3 reprojection.
4. Spot audit: agent grep confirms no `sdd-spec-gate.sh` / `LEASE-1` / `researcher`
   in memory; grep confirms no `subprocess` direct import in `features/` except
   via adapter.
